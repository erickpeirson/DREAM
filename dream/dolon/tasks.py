from __future__ import absolute_import

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

from BeautifulSoup import BeautifulSoup

from django.core.files import File
import tempfile
import urllib2
import json
import os
import math
from unidecode import unidecode
import warnings
from BeautifulSoup import BeautifulSoup

import dolon.search_managers as M
from dolon.models import *

from celery import shared_task, group, task, chain

engineManagers = {
    'GoogleImageSearchManager': M.GoogleImageSearchManager,
}

@shared_task
def trigger_dispatchers(*args, **kwargs):
    """
    Try to dispatch all pending :class:`.QueryEvent`\s.
    
    
    Returns
    -------
    dispatched : list
        IDs of dispatched QueryEvents.
    """

    # Get all pending QueryEvents.
    queryevents = QueryEvent.objects.filter(dispatched=False)

    logger.info('tasks.trigger_dispatchers: Found {0} pending QueryEvents.'
                                                      .format(len(queryevents)))
    dispatched = []
    for qe in queryevents:
        try_dispatch(qe)
        dispatched.append(qe.id)
        
    return dispatched
        
def try_dispatch(queryevent):
    """
    Try to dispatch a :class:`.QueryEvent`\. 
    
    Only dispatched if within daily and monthly usage limits for its respective
    :class:`.Engine`\.
    
    Parameters
    ----------
    queryevent : :class:`.QueryEvent`
    
    Returns
    -------
    None
    """

    logger.debug('Trying to dispatch queryevent {0}'.format(queryevent.id))
    
    engine = queryevent.engine
    remaining_today = engine.daylimit - engine.dayusage
    remaining_month = engine.monthlimit - engine.monthusage
    
    logger.debug('Remaining today: {0}, remaining this month: {1}'
                                      .format(remaining_today, remaining_month))

    if engine.pagelimit is not None:
        pagelimit = engine.pagelimit
    else:
        pagelimit = 400000000000    # Is this high enough?

    pagesize = engine.pagesize
    start = queryevent.rangeStart
    end = min(queryevent.rangeEnd, pagelimit*pagesize)

    if start >= end:    # Search range out of bounds.
        logger.debug('Search range out of bounds, aborting.')
        return

    # Maximum number of requests.
    Nrequests = math.ceil(float(end-start)/pagesize)

    # Only dispatch if within daily and monthly limits.
    if Nrequests < remaining_today and Nrequests < remaining_month:
        logger.debug('Attempting dispatch.')
        dispatchQueryEvent(queryevent.id)   
        engine.dayusage += Nrequests
        engine.monthusage += Nrequests
        engine.save()
    else:
        logger.debug('Search quota for {0} depleted. Aborting.'.format(engine))

    return None

def reset_dayusage(*args, **kwargs):
    """
    Set dayusage to 0 for all :class:`.Engine`\s.
    """
    
    for engine in Engine.objects.all():
        engine.dayusage = 0
        engine.save()

def reset_monthusage(*args, **kwargs):
    """
    Set monthusage to 0 for all :class:`.Engine`\s.
    """

    for engine in Engine.objects.all():
        engine.monthusage = 0
        engine.save()

@shared_task(rate_limit="2/s", ignore_result=False, max_retries=4)
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
        try:
            result, response = manager.imageSearch( params, qstring,
                                                    start=start, end=end )
        except Exception as exc:
            search.retry(exc=exc)
        
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

@shared_task(rate_limit='2/s', max_retries=5)
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
    try:
        response = urllib2.urlopen(url)
    except Exception as exc:
        getFile.retry(exc=exc)
    
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
    thumbnail.mime = mime
    
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
    
@shared_task(rate_limit='2/s', max_retries=5)
def getStoreContext(url, contextid):
    """
    Retrieve the HTML contents of a resource and update :class:`.Context` 
    corresponding to ``contextid``.
    
    Parameters
    ----------
    url : str
        Location of resource.
        
    Returns
    -------
    context.id : int
        ID for the :class:`.Context`
    """

    try:
        response = urllib2.urlopen(url)
        response_content = response.read()
    except Exception as exc:
        getStoreContext.retry(exc=exc)

    soup = BeautifulSoup(response_content)
    title = soup.title.getText()

    context = Context.objects.get(pk=contextid)
    context.content = soup.html()
    context.title = str(title)
    context.save()
    
    return context.id



#### Was dolon.managers #####


def dispatchQueryEvent(queryevent_id):
    queryevent = QueryEvent.objects.get(pk=queryevent_id)
    
    task_id, subtask_ids = spawnSearch(queryevent)
    task = GroupTask(   task_id=task_id,
                        subtask_ids=subtask_ids )
    task.save()
    queryevent.search_task = task
    queryevent.dispatched = True
    queryevent.save()        

    return queryevent.id

def spawnRetrieveImages(queryset):
    """
    Generates a set of tasks to retrieve images.
    """
    
    job = group( ( getFile.s(i.url) | storeImage.s(i.id) ) for i in queryset )

    result = job.apply_async()

    return result.id, [ r.id for r in result.results ]    
    
def spawnRetrieveContexts(queryset):
    """
    Generates a group of tasks to retrieve contexts.
    """
    
    job = group( ( getStoreContext.s(i.url, i.id) ) for i in queryset )

    result = job.apply_async()

    return result.id, [ r.id for r in result.results ]       

def spawnSearch(queryevent, **kwargs):
    """
    Executes a series of searches based on the parameters of a 
    :class:`.QueryEvent` and updates it accordingly.
    
    Parameters
    ----------
    queryevent : :class:`.QueryEvent`
        
    Returns
    -------
    result.id : str
        UUID for the Celery search task group.
    """

    if queryevent.dispatched:
        warnings.warn('Attempting to spawnSearch() for QueryEvent that has ' + \
                      ' already been dispatched.', RuntimeWarning)
        return queryevent

    qstring = queryevent.querystring.querystring
    start = queryevent.rangeStart
    end = queryevent.rangeEnd
    engine = engineManagers[queryevent.engine.manager]()

    logger.debug('spawnSearch() for QueryEvent {0},'.format(queryevent.id)    +\
        ' with term "{0}", start: {1}, end: {2},'.format(qstring, start, end) +\
        ' using Engine: {0}'.format(engine.name))

    params = [ p for p in queryevent.engine.parameters ]
    
    # Dispatch a group of search chains to Celery, divided into 10-item pages.
    #
    #   * search() performs the image search for a 10-item page,
    #   |
    #   * processSearch() parses the search results and creates QueryResult 
    #   | and QueryItem instances.
    #   * spawnThumbnails() launches tasks to retrieve and store Thumbnail
    #     instances. 
    #   
    # QueryEvent.id gets passed around so that the various tasks can attach
    #  the resulting objects to it.
    logger.debug('spawnSearch: creating jobs')

    job = group(  ( search.s(qstring, s, min(s+9, end), 
                        queryevent.engine.manager, params, **kwargs) 
                    | processSearch.s(queryevent.id, **kwargs) 
                    | spawnThumbnails.s(queryevent.id, **kwargs)
                    ) for s in xrange(start, end+1, 10) )
                    

    logger.debug('spawnSearch: dispatching jobs')
    result = job.apply_async()
    
    logger.debug('spawnSearch: jobs dispatched')
    
    return result.id, [ r.id for r in result.results ]