from __future__ import absolute_import

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')


from BeautifulSoup import BeautifulSoup


from django.core.files import File
import tempfile
import urllib2
import os
from unidecode import unidecode


import dolon.search_managers as M
from dolon.models import *

from celery import shared_task, group

@shared_task(rate_limit="25/s", ignore_result=False)
def search(qstring, start, end, manager_name, params, **kwargs):
    """
    Perform a search for ``string`` using a provided ``manager`` instance.
    
    Parameters
    ----------
    qstring : str
        Search query.
    start : int
        Start index for results.
    end : int
        End index for results.
    manager : __name__ of a manager in :mod:`.search_managers`
    params : list
        A list of parameters to pass to the remote search service.
    
    Returns
    -------
    result : dict
        Contains structured search results amenable to :class:`.QueryItem`
    response : dict
        Full parsed JSON response.
    """
    
    if not kwargs.get('testing', False):
        manager = getattr(M, manager_name)()
        result, response = manager.imageSearch( params, qstring, 
                                                start=start, end=end    )
        
    else:   # When testing we don't want to make remote calls.
        import cPickle as pickle
        with open('./dolon/testdata/searchresult.pickle', 'r') as f:
            result = pickle.load(f)
        with open('./dolon/testdata/searchresponse.pickle', 'r') as f:
            response = pickle.load(f)
        
    return result, response
    
@shared_task
def processSearch(searchresult, queryeventid, **kwargs):
    """
    Create a :class:`.QueryResult` and a set of :class:`.QueryItem` from a
    search result.
    
    Parameters
    ----------
    searchresult : tuple
        ( result(dict), response(dict) ) from :func:`.search`
    
    Returns
    -------
    queryResult : int
        ID for a :class:`.QueryResult`
    queryItems : list
        A list of IDs for :class:`.QueryItem` instances.
    """

    
    result, response = searchresult
    
    queryResult = QueryResult(  rangeStart=result['start'],
                                rangeEnd=result['end'],
                                result=response )
    queryResult.save()

    queryItems = []
    for item in result['items']:
        queryItem = QueryResultItem(
                        url = item['url'],
                        title = unidecode(item['title']),
                        size = item['size'],
                        height = item['height'],
                        width = item['width'],
                        mime = item['mime'],
                        contextURL = item['contextURL'],
                        thumbnailURL = item['thumbnailURL']
                    )
        queryItem.save()

        queryResult.resultitems.add(queryItem)
        queryItems.append(queryItem.id)

    queryResult.save()

    if not kwargs.get('testing', False):
        queryevent = QueryEvent.objects.get(id=queryeventid)
        queryevent.queryresults.add(queryResult)
        queryevent.save()
        
    # Attach event to items.
    for item in queryItems:
        qi = QueryResultItem.objects.get(id=item)
        i = Item.objects.get(id=qi.item.id)
        i.events.add(queryevent)
        i.save()       

    return queryResult.id, queryItems   
    
@shared_task
def spawnThumbnails(processresult, queryeventid, **kwargs):
    """
    Dispatch tasks to retrieve and store thumbnails. Updates the corresponding
    :class:`.QueryEvent` `thumbnail_task` property with task id.
    
    Parameters
    ----------
    processresult : tuple
        Output from :func:`.processSearch`
    """
    
    queryresultid, queryitemsid = processresult
    queryresult = QueryResult.objects.get(id=queryresultid)
    queryitems = [ QueryResultItem.objects.get(id=id) for id in queryitemsid ]
    
    logger.debug('spawnThumbnails: creating jobs')    
    job = group( ( getFile.s(item.thumbnailURL) 
                    | storeThumbnail.s(item.item.thumbnail.id) 
                    ) for item in queryitems )

    logger.debug('spawnThumbnails: dispatching jobs')
    result = job.apply_async()    
    
    logger.debug('spawnThumbnails: jobs dispatched')

    task = GroupTask(   task_id=result.id,
                        subtask_ids=[r.id for r in result.results ] )
    task.save()
    
    logger.debug('created new Task object')

    queryevent = QueryEvent.objects.get(id=queryeventid)
    queryevent.thumbnail_tasks.add(task)
    queryevent.save()
    
    logger.debug('updated QueryEvent')

    return task    

@shared_task(rate_limit='2/s')
def getFile(url):
    """
    Retrieve a resource from `URL`.
    
    Parameters
    ----------
    url : str
        Resource location.
    
    Returns
    -------
    url : str
    filename : str
        Best guess at the resource's local filename.
    fpath : str
        Path to a temporary file containing retrieved data.
    mime : str
        MIME type.
    size : int
        Filesize.
    """

    filename = url.split('/')[-1]
    response = urllib2.urlopen(url)
    
    mime = dict(response.info())['content-type']
    size = int(dict(response.info())['content-length'])
    
    f_,fpath = tempfile.mkstemp()
    with open(fpath, 'w') as f:
        f.write(response.read())

    return url, filename, fpath, mime, size
    
@shared_task
def storeThumbnail(result, thumbnailid):
    """
    Update a :class:`.Thumbnail` with image data.
    
    Parameters
    ----------
    result : tuple
        ( url, filename, fpath, mime, size ) from :func:`.getFile`
    thumbnailid : int
        ID of a :class:`.Thumbnail`
    
    Returns
    -------
    thumbnailid : int
        ID for the :class:`.Thumbnail`
    """
    
    url, filename, fpath, mime, size = result
    
    thumbnail = Thumbnail.objects.get(id=thumbnailid)
    
    with open(fpath, 'rb') as f:
        file = File(f)
        thumbnail.image.save(filename, file, True)
        thumbnail.save()

    os.remove(fpath)

    return thumbnail.id
    
@shared_task
def storeImage(result, imageid):
    """
    Updates an :class:`.Image`\.
    
    Parameters
    ----------
    result : tuple
        ( url, filename, fpath, mime, size ) from :func:`.getFile`
    itemid : int
        ID of a :class:`.Item` instance associated with the :class:`.Image`
    
    Returns
    -------
    image.id : int
        ID for the class:`.Image`
    """
    
    url, filename, fpath, mime, size = result
    
    image = Image.objects.get(pk=imageid)
    image.size = size
    image.mime = mime

    with open(fpath, 'rb') as f:
        file = File(f)
        image.image.save(filename, file, True)
        image.save()
        
    return image.id
    
@shared_task(rate_limit='2/s')
def getStoreContext(url, contextid):
    """
    Retrieve the HTML contents of a resource and attach it to an :class:`.Item`
    
    Parameters
    ----------
    url : str
        Location of resource.
        
    Returns
    -------
    context.id : int
        ID for the :class:`.Context`
    """

    response = urllib2.urlopen(url).read()
    soup = BeautifulSoup(response)
    title = soup.title.getText()

    context = Context.objects.get(pk=contextid)
    context.content = unidecode(response)
    context.title = unidecode(title)
    context.save()
    
    return context.id



