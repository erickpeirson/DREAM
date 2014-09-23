from __future__ import absolute_import

import logging
logging.basicConfig(filename=None, format='%(asctime)-6s: %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

from django.core.files import File
from django.http import HttpRequest
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist

import tempfile
import urllib2
from urllib2 import HTTPError
import cPickle as pickle

import os
import math
import warnings

# Parsing
from BeautifulSoup import BeautifulSoup
from unidecode import unidecode
import json

# Time and timezones.
from datetime import datetime
from pytz import timezone
import pytz
import time

import dolon.search_managers as M
from dolon.models import *
from dolon.services import DiffBotManager
from dream.settings import DIFFBOT_TOKEN, TIME_ZONE


from celery import shared_task, group, task, chain
from celery.exceptions import MaxRetriesExceededError

engineManagers = {
    'GoogleImageSearchManager': M.GoogleImageSearchManager,
    'InternetArchiveManager': M.InternetArchiveManager,
}

def _get_params(resultitem):
    """
    Reads standardized result parameters from a :class:`.QueryResultItem`\.
    
    """
    params = pickle.loads(str(resultitem.params))
    if 'length' in params: length = params['length']
    else: length = 0
        
    if 'size' in params: size = params['size']
    else: size = 0
    
    if 'creator' in params: creator = params['creator']
    else: creator = ''  # Case not tested.
    
    if 'date' in params: date = params['date']
    else:   date = None
    
    return params, length, size, creator, date
# end _get_params

def _get_default(itemclass, resultitem):
    """
    Generates a :class:`.Item` and populates subtype-independent fields using
    params from :class:`.QueryResultItem`\.
    
    """
    params, length, size, creator, date = _get_params(resultitem)

    try:
        i, created = itemclass.objects.get_or_create(url = resultitem.url,
                        defaults = {
                                'title': resultitem.title,
                                'creator': creator,
                                'creationDate': date
                            })
    # An IntegrityError is raised when an Item with resultitem.url exist, but                            
    # itemclass is the wrong subtype (e.g. matching item is an AudioItem, but
    # itemclass is ImageItem).
    except IntegrityError:
        # We should bail here. We ought to already know what kind of item we're
        # working with, since the methods that use _get_default are item-type
        # specific.
        raise ValueError('An item exists with that URL, but itemclass is the '+\
                         'wrong Item subclass.')
            
    if itemclass is not ImageItem:  # Images don't have lengths.
        i.length = length
    
    # Return both the Item and the QueryResultItem parameters, to avoid
    #  redundant calls to _get_params.
    return i, (params, length, size, creator, date)
# end _get_default

def _create_image_item(resultitem):
    i, parameters = _get_default(ImageItem, resultitem)
    params, length, size, creator, date = parameters

    # Associate thumbnail, image, and context.
    if i.thumbnail is None and len(params['thumbnailURL']) > 0:
        i.thumbnail = Thumbnail.objects.get_or_create(
                            url=params['thumbnailURL'][0]   )[0]
        
        spawnThumbnails([i.thumbnail.id])

    if len(i.images.all()) == 0 and len(params['files']) > 0:
        for url in params['files']:
            image = Image.objects.get_or_create(url=url)[0]
            i.images.add(image)

    return i, params
# end _create_image_item

def _create_video_item(resultitem):
    i, parameters = _get_default(VideoItem, resultitem)
    params, length, size, creator, date = parameters

    # Only add thumbnails to this VideoItem if it has none, and (naturally) if
    #  the search process yielded thumbnails to be had.
    if len(i.thumbnails.all()) == 0 and len(params['thumbnailURL']) > 0:
        thumb_ids = []  # Keep these for spawnThumbnails.
        for url in params['thumbnailURL']:
            thumb = Thumbnail.objects.get_or_create(url=url)[0]                        
            i.thumbnails.add(thumb)
            thumb_ids.append(thumb.id)
        
        # Creates Celery chains for retrieving thumbnail images.
        spawnThumbnails(thumb_ids)

    # If this VideoItem doesn't already have Videos attached, get/create them.
    if len(i.videos.all()) == 0 and len(params['files']) > 0:
        for url in params['files']:
            video = Video.objects.get_or_create(url=url)[0]
            i.videos.add(video)

    return i, params
# end _create_video_item

def _create_audio_item(resultitem):    
    i, parameters = _get_default(AudioItem, resultitem)    
    params, length, size, creator, date = parameters
                
    # If AudioItem lacks a thumbnail, and one was found (in search), create it
    #  and trigger retrieval.
    if i.thumbnail is None and len(params['thumbnailURL']) > 0:
        i.thumbnail = Thumbnail.objects.get_or_create(  # Case not tested.
                            url=params['thumbnailURL'][0]   )[0]     

        # Creates a Celery chain for retrieving thumbnail image.
        spawnThumbnails(i.thumbnail.id)                                                                  

    # If no Audio exist for this AudioItem, get/create them.
    if len(i.audio_segments.all()) == 0 and len(params['files']) > 0:
        for url in params['files']:
            seg = Audio.objects.get_or_create(url=url)[0]
            i.audio_segments.add(seg)

    return i, params
# end _create_audio_item

def _create_text_item(resultitem):
    i, parameters = _get_default(TextItem, resultitem)
    params, length, size, creator, date = parameters    

    if len(i.original_files.all()) == 0 and len(params['files']) > 0:
        for url in params['files']:
            txt,created = Text.objects.get_or_create(url=url)
            logger.debug('Text: {0}'.format(txt))
            i.original_files.add(txt)

    if 'contents' in params:
        i.contents = params['contents'].decode('utf-8')
        i.snippet = params['contents'].decode('utf-8')[0:500]

    return i, params
# end _create_text_item

def create_item(resultitem):
    """
    Generate an :class:`.Item` from a :class:`.QueryResultItem`\.
    
    Called from :func:`.QueryResultItem.save`\.
    
    Parameters
    ----------
    resultitem : :class:`.QueryResultItem`
    
    Returns
    -------
    i : :class:`.Item`
    
    """
    logger.debug('Creating item for {0} with mtype {1}'
                                           .format(resultitem, resultitem.type))
    
    if resultitem.type == 'image':
        i, params = _create_image_item(resultitem)
    elif resultitem.type == 'video':
        i, params = _create_video_item(resultitem)
    elif resultitem.type == 'audio':
        i, params = _create_audio_item(resultitem)
    elif resultitem.type == 'texts':        # Case not tested.
        i, params = _create_text_item(resultitem)

    if 'retrieved' in params:
        i.retrieved = params['retrieved']
    if 'creationDate' in params:
        i.creationDate = params['creationDate']

    context, created = Context.objects.get_or_create(url=resultitem.contextURL)
    if 'context' in params:
        for key, value in params['context'].iteritems():
            setattr(context, key, value)
        context.save()

    i.context.add(context)
    i.save()
    
    logger.debug('Generated item {0}'.format(i))

    return i

### Scheduled Tasks ###

@shared_task
def trigger_diffbot_requests(*args, **kwargs):
    """
    Try to perform any pending :class:`.DiffBotRequest`\s.
    """

    requests = DiffBotRequest.objects.filter(completed=None)
    
    logger.debug('Found {0} pending DiffBotRequests'.format(len(requests)))
    
    for req in requests:
        performDiffBotRequest(req)
        time.sleep(0.5)

    logger.debug('Performed {0} DiffBotRequests'.format(len(requests)))
    
    return requests

@shared_task    # Scheduled.
def trigger_dispatchers(*args, **kwargs):
    """
    Try to dispatch all pending :class:`.QueryEvent`\s.
    
    Returns
    -------
    dispatched : list
        IDs of dispatched :class:`.QueryEvents`\.
    """

    # Get all pending QueryEvents.
    queryevents = QueryEvent.objects.filter(dispatched=False)

    logger.info('Found {0} pending QueryEvents.'.format(len(queryevents)))
    dispatched = []
    for qe in queryevents:
        try_dispatch(qe)
        dispatched.append(qe.id)
        
    return dispatched
    
@shared_task    # Scheduled.
def trigger_retrieve(*args, **kwargs):  # Case not tested.
    """
    Try to retrieve content and contexts for all :class:`.Item` objects that
    are approved (but not already retrieved).
    
    Returns
    -------
    retrieved : list
        IDs of retrieved :class:`Item`\s.
    """
    
    # Get all approved, non-retrieved Items.
    items = Item.objects.filter(status='AP').filter(retrieved=False)
    
    logger.info('Found {0} approved Items.'.format(len(items)))
    
    retrieved = []
    for item in items:
        try_retrieve(item)
        retrieved.append(item.id)
        
    return retrieved
    
def try_retrieve(obj, *args, **kwargs): # Case not tested.
    """
    Attempt to retrieve content for an :class:`.Item` instance.
    
    Parameters
    ----------
    obj : :class:`.Item`
    """
    
    images = []
    videos = []
    audio = []
    contexts = []
    if hasattr(obj, 'imageitem'):
        images += obj.imageitem.images.all()
        contexts += [ c for c in obj.imageitem.context.all() ]
    elif hasattr(obj, 'videoitem'):
        videos += obj.videoitem.videos.all()
        contexts += [ c for c in obj.videoitem.context.all() ]            
    elif hasattr(obj, 'audioitem'):
        audio += obj.audioitem.audio_segments.all()
        contexts += [ c for c in obj.audioitem.context.all() ]            
    
    spawnRetrieveImages(images)
    spawnRetrieveAudio(audio)
    spawnRetrieveVideo(videos)
    spawnRetrieveContexts(contexts)
    
    obj.retrieved = True
    obj.save()
        
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
    
    # Calculate remaining daily and monthly usage. If there are no limits, then
    #  set remaining values unreasonably high.
    if engine.daylimit is None:
        remaining_today = 4000000000000     # Case not tested.
    else:
        remaining_today = engine.daylimit - engine.dayusage
    
    if engine.monthlimit is None:           # Case not tested.
        remaining_month = 4000000000000
    else:
        remaining_month = engine.monthlimit - engine.monthusage
    
    logger.debug('Remaining today: {0}, remaining this month: {1}'
                                      .format(remaining_today, remaining_month))

    # Get the page limit for this engine.
    if engine.pagelimit is not None:        # Case not tested.
        pagelimit = engine.pagelimit
    else:
        pagelimit = 400000000000    # Is this high enough?

    # Make sure that the resulting queries won't exceed limits, and that the
    #  starting and ending indices are sensical.
    pagesize = engine.pagesize
    start = queryevent.rangeStart
    end = min(queryevent.rangeEnd, pagelimit*pagesize)

    if start >= end:    # Search range out of bounds.
        logger.debug('Search range out of bounds, aborting.') # Case not tested.
        return

    # Maximum number of requests.
    Nrequests = math.ceil(float(end-start)/pagesize)

    # Only dispatch if within daily and monthly limits.
    day_remains = Nrequests < remaining_today or engine.daylimit is None
    month_remains = Nrequests < remaining_month or engine.monthlimit is None
    if day_remains and month_remains:
        logger.debug('Attempting dispatch.')
        dispatchQueryEvent(queryevent.id)   
        engine.dayusage += Nrequests
        engine.monthusage += Nrequests
        engine.save()
        
        # Success!
        logging.info('Dispatched QueryEvent {0}.'.format(queryevent.id))
    else:   # Case not tested.
        # Over limits. Hold off until next time.
        logger.debug('Search quota for {0} depleted. Aborting.'.format(engine))
        pass

    return None

@shared_task
def reset_dayusage(*args, **kwargs):
    """
    Set dayusage to 0 for all :class:`.Engine`\s.
    """
    
    for engine in Engine.objects.all():
        engine.dayusage = 0
        engine.save()

@shared_task
def reset_monthusage(*args, **kwargs):
    """
    Set monthusage to 0 for all :class:`.Engine`\s.
    """

    for engine in Engine.objects.all():
        engine.monthusage = 0
        engine.save()
        
### End Scheduled Tasks ###

@shared_task(rate_limit="1/s", ignore_result=False, max_retries=0)
def search(queryevent_id, manager_name, **kwargs):
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
            results = manager.search( queryevent_id )
        except Exception as exc:    # Case not tested.
            try:
                search.retry(exc=exc)
            except (IOError, HTTPError) as exc:
                logger.info((exc.code, exc.read()))
                return 'ERROR'
        
    else:   # When testing we don't want to make remote calls.
        import cPickle as pickle
        with open('./dolon/testdata/searchresult.pickle', 'r') as f:
            result = pickle.load(f)
        with open('./dolon/testdata/searchresponse.pickle', 'r') as f:
            response = pickle.load(f)
        
    return results
    
@shared_task
def processSearch(searchresults, queryeventid, **kwargs):
    """
    Create a :class:`.QueryResult` and a set of :class:`.Item` from a
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
        A list of IDs for :class:`.` instances.
    """
    
    if searchresults == 'ERROR': # Case not tested.
        return 'ERROR'
    
    results = []
    for searchresult in searchresults:
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
                            params = pickle.dumps(item),
                            contextURL = item['contextURL'],
                            type = item['type']
                        )
            queryItem.save()
            queryItem.item = create_item(queryItem)
            queryItem.save()
            
            queryResult.resultitems.add(queryItem)
            queryItems.append(queryItem.id)

        queryResult.save()

        if not kwargs.get('testing', False):    # TODO: get rid of this.
            queryevent = QueryEvent.objects.get(id=queryeventid)
            queryevent.queryresults.add(queryResult)
            queryevent.save()
            
        # Attach event to items.
        for item in queryItems:
            qi = QueryResultItem.objects.get(id=item)
            i = Item.objects.get(id=qi.item.id)
            i.events.add(queryevent)
            i.save()      
         
        results.append((queryResult.id, queryItems))

    return results
    
@shared_task
def spawnThumbnails(thumb_ids, **kwargs):
    """
    Dispatch tasks to retrieve and store thumbnails. 
    
    Parameters
    ----------
    thumb_ids : list
        IDs of :class:`.Thumbnail` objects for which remote images should be
        retrieved.
    
    Returns
    -------
    None

    """
 
    logger.debug('Spawn chains for {0} thumbnails.'.format(len(thumb_ids)))
    
    thumbs = [ Thumbnail.objects.get(pk=id) for id in thumb_ids ]

    for thumb in thumbs:    # Create a Celery chain for each thumbnail.
        job = chain(    getFile.s(thumb.url)
                        | storeThumbnail.s(thumb.id)    )

        # readResult will clear the result in RabbitMQ.
        result = job.apply_async(link=readResult.s())

    return

@shared_task(rate_limit='4/s', max_retries=0)
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
    except Exception as exc:    # Case not tested.
        try:
            getFile.retry(exc=exc)
        except (IOError, HTTPError) as exc:
            logger.info((exc.code, exc.read()))
    
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
    
@shared_task
def storeAudio(result, audioid):
    
    url, filename, fpath, mime, size = result
    
    audio = Audio.objects.get(pk=audioid)
    audio.size = size
    audio.mime = mime
    
    with open(fpath, 'rb') as f:
        file = File(f)
        audio.audio_file.save(filename, file, True)
        audio.save()
        
    return audio.id
    
@shared_task
def storeVideo(result, videoid):
    
    url, filename, fpath, mime, size = result
    
    video = Video.objects.get(pk=videoid)
    video.size = size
    video.mime = mime
    
    with open(fpath, 'rb') as f:
        file = File(f)
        video.video.save(filename, file, True)
        video.save()
        
    return video.id    
    
@shared_task(rate_limit='4/s', max_retries=3)
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

    except Exception as exc:    # Case not tested.
        try:
            getStoreContext.retry(exc=exc)
        except (IOError, HTTPError) as exc:
            logger.info((exc.code, exc.read()))        

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
    
    task_id = spawnSearch(queryevent)
    task = GroupTask(   task_id=task_id,
                        subtask_ids=[''] )
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

    result = job.apply_async(link=readResult.s())

    return result.id, [ r.id for r in result.results ]    
    
def spawnRetrieveAudio(queryset):
    """
    Generates a set of tasks to retrieve audio files.
    """
    
    job = group( ( getFile.s(i.url) | storeAudio.s(i.id) ) for i in queryset )

    result = job.apply_async(link=readResult.s())

    return result.id, [ r.id for r in result.results ]  
    
def spawnRetrieveVideo(queryset):
    """
    Generates a set of tasks to retrieve audio files.
    """
    
    job = group( ( getFile.s(i.url) | storeVideo.s(i.id) ) for i in queryset )

    result = job.apply_async(link=readResult.s())

    return result.id, [ r.id for r in result.results ]      
    
def spawnRetrieveContexts(queryset):
    """
    Generates a group of tasks to retrieve contexts.
    """
    
    # Create retrieval tasks.
    job = group( ( getStoreContext.s(i.url, i.id) ) for i in queryset if not i.retrieved )
    result = job.apply_async(link=readResult.s())

    # Create DiffBotRequests, and update Contexts.
    for i in queryset:
        if i.use_diffbot:
            rq = createDiffBotRequest('article', i.url)
            i.diffbot_requests.add(rq)
            i.save()

    return result.id, [ r.id for r in result.results ]    
# end spawnRetrieveContexts
    
def createDiffBotRequest(type, url, opt_params=[]):
    manager = DiffBotManager()
    params = manager.prep_request(type, url, opt_params)
    
    request = DiffBotRequest(
                type = type,
                parameters = params
                )
    request.save()
                
    return request
# end createDiffBotRequests    

@shared_task
def performDiffBotRequest(rq):
    manager = DiffBotManager(DIFFBOT_TOKEN)
    
    this_timezone = timezone(TIME_ZONE)
    this_datetime = this_timezone.localize(datetime.now())
    
    # Note performance attempt.
    rq.attempted = this_datetime
    rq.save()
    
    try:    # Perform the request, and store the result.
        result = manager.get(rq.parameters)
        rq.response = pickle.dumps(result)
        rq.completed = this_datetime
        rq.save()
    except Exception as E: # If something goes wrong, completed will not be set.
        logger.debug('Uh-oh: {0}'.format(E))    # Case not tested.
        return

    # Update context.
    try:
        context = rq.requesting_context.all()[0]
    except IndexError:
        return
    
    dtformat = '%a, %d %b %Y %X GMT'
    date = this_timezone.localize(
            datetime.strptime(result['objects'][0]['date'], dtformat)   )

    robject = result['objects'][0]
    if context.publicationDate is None:
        context.publicationDate = date
    if 'text' in robject:
        context.text_content = result['objects'][0]['text']
    if 'author' in robject:
        context.author = result['objects'][0]['author']
    if 'title' in robject:
        context.title = result['objects'][0]['title']   # Case not tested.
    if 'language' in robject:
        context.language = result['objects'][0]['humanLanguage']
    context.save()
# end performDiffBotRequest    

@shared_task
def readResult(*args, **kwargs):    # Case not tested.
    """
    Reads the result of a task, so as to clear the queue.
    """
    
    pass
    
@shared_task
def completeQueryEvent(result, queryeventid):   # Case not tested.
    queryevent = QueryEvent.objects.get(pk=queryeventid)
    queryevent.state = 'DONE'
    queryevent.save()
    
    logging.debug('completed QueryEvent {0}'.format(queryeventid))

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

    if queryevent.dispatched:   # Case not tested.
        warnings.warn('QueryEvent {0} has already been dispatched.'
                                                            .format(queryevent))
        return queryevent

    logger.debug('QueryEvent {0}, using Engine {1}'
                                         .format(queryevent, queryevent.engine))
                                         
    start = queryevent.rangeStart
    end = queryevent.rangeEnd                                         
    
    # Dispatch a group of search chains to Celery:
    #
    #   * search() performs the image search,
    #   |
    #   * processSearch() parses the search results and creates QueryResult 
    #     and QueryItem instances.
    #   
    # QueryEvent.id gets passed around so that the various tasks can attach
    #  the resulting objects to it.
    logger.debug('creating jobs for QueryEvent {0}'.format(queryevent.id))

    job = chain( search.s(   queryevent.id, 
                                queryevent.engine.manager, 
                                **kwargs   )
                    | processSearch.s(queryevent.id, **kwargs) 
                )
                    

    logger.debug('dispatching jobs for QueryEvent {0}'.format(queryevent.id))
    result = job.apply_async(link=completeQueryEvent.s(queryevent.id))
    
    logger.debug('jobs dispatched for QueryEvent {0}'.format(queryevent.id))
    
    return result.id
