import uuid
from models import *
from tasks import *

def reset(modeladmin, request, queryset):
    """
    Resets ``state`` of a :class:`.QueryEvent` and removes linked GroupTask.
    
    If :class:`.QueryEvent` instance is not dispatched, or has not failed or
    erred, nothing happens.
    """
    
    for obj in queryset:
        if obj.state in ['ERROR','FAILED'] and obj.dispatched:
            obj.state = 'PENDING'
            obj.dispatched = False
            obj.search_task = None
            obj.save()
reset.short_description = 'Reset selected (failed) query'

def dispatch(modeladmin, request, queryset):
    """
    Dispatches a :class:`.QueryEvent` for searching and thumbnail retrieval.
    
    Used as an action in the :class:`.QueryEventAdmin`\.
    """

    for obj in queryset:
        try_dispatch(obj)
dispatch.short_description = 'Dispatch selected query'    

def approve(modeladmin, request, queryset):
    """
    Approves all selected :class:`.Items`\.
    """
    
    contexts = []
    for obj in queryset:
        obj.status = 'AP'
        obj.save()
approve.short_description = 'Approve selected items'

def retrieve_content(modeladmin, request, queryset):
    """
    Retrieves content and contexts for a :class:`.Item`\.
    """
    
    for obj in queryset:
        if not obj.retrieved:
            try_retrieve(obj)
retrieve_content.short_description = 'Retrieve content for selected items'        
        
def reject(modeladmin, request, queryset):
    """
    Rejects all selected :class:`.Items`\.
    """
    
    for obj in queryset:
        obj.status = 'RJ'
        obj.save()        
reject.short_description = 'Reject selected items'        

def pend(modeladmin, request, queryset):
    """
    Rejects all selected :class:`.Items`\.
    """
    
    for obj in queryset:
        obj.status = 'PG'
        obj.save()        
pend.short_description = 'Set selected items to Pending' 

def retrieve_image(modeladmin, request, queryset):
    """
    Retrieves fullsize images for all selected :class:`.Image`\s.
    """
    
    result = spawnRetrieveImages(queryset)
retrieve_image.short_description = 'Retrieve content for selected images'
    
def retrieve_context(modeladmin, request, queryset):
    """
    Retrieves contexts for all selected :class:`.Context`\s.
    """
    
    result = spawnRetrieveContexts(queryset)
retrieve_context.short_description = 'Retrieve content for selected contexts'    

def _generateURI():
    identifier = str(uuid.uuid1())
    title = 'Merged item {0}'.format(identifier)
    url = 'http://roy.fulton.asu.edu/dolon/mergeditem/{0}'.format(identifier)
    
    return identifier, title, url
# end _generateURI

def _prepMerge(itemclass, type):
    identifier, title, url = _generateURI() # Fake URL and title.
    newItem = itemclass(    url = url,
                            title = title,
                            type = type )
    newItem.save()
    return newItem
# end _prepMerge

def _mergeItem(queryset, itemclass, type):
    """
    Performs merge operations common to all :class:`.Item` subclasses.
    """
    
    newItem = _prepMerge(itemclass, type)
    
    for obj in queryset:
        # If any one Item is approved, the new Item is approved.
        if obj.status == 'AP':  
            newItem.status = 'AP'
            newItem.save()                
                
        # Pool all of the contexts.
        for c in obj.context.all():
            newItem.context.add(c)
            
        # Pool all of the tags.
        for t in obj.tags.all():
            newItem.tags.add(t)
            
        # Link to QueryEvents
        for e in obj.events.all():
            newItem.events.add(e)
        
        # Set merged_with on old items.
        obj.merged_with = newItem
        obj.hide = True
        obj.save()
        
    newItem.save()
    return newItem
# end _mergeItem

def _mergeImage(queryset):
    """
    Merges multiple :class:`.ImageItem` objects into a single 
    :class:`.ImageItem`\.
    """
    logger.debug('Merging {0} ImageItems.'.format(len(queryset)))

    # General Item merge operations.
    newItem = _mergeItem(queryset, ImageItem, 'Image')

    # Image-specific operations.
    for obj in queryset:
        # Inherit any thumbnail.
        if newItem.thumbnail is None and obj.imageitem.thumbnail is not None:
            newItem.thumbnail = obj.imageitem.thumbnail
            newItem.save()

        # Pool all images.
        for i in obj.imageitem.images.all():
            newItem.images.add(i)
                    
    newItem.save() 
# end _mergeImage

def _mergeAudio(queryset):
    """
    Merges multiple :class:`.AudioItem` objects into a single 
    :class:`.AudioItem`\.
    """
    logger.debug('Merging {0} AudioItems.'.format(len(queryset)))
    
    # General Item merge operations.
    newItem = _mergeItem(queryset, AudioItem, 'Audio')    
    
    # Audio-specific operations.
    for obj in queryset:
        # Inherit any thumbnail.
        if newItem.thumbnail is None and obj.audioitem.thumbnail is not None:
            newItem.thumbnail = obj.audioitem.thumbnail
            newItem.save()        
        
        # Inherit all audio segments.
        for i in obj.audioitem.audio_segments.all():
            newItem.audio_segments.add(i)
            
    newItem.save()
# end _mergeAudio

def _mergeVideo(queryset):
    """
    Merges multiple :class:`.VideoItem` objects into a single 
    :class:`.VideoItem`\.
    """
    logger.debug('Merging {0} VideoItems.'.format(len(queryset)))    
    
    # General Item merge operations.
    newItem = _mergeItem(queryset, VideoItem, 'Video')

    # Video-specific operations.
    for obj in queryset:    
        # Pool all thumbnails.
        for i in obj.videoitem.thumbnails.all():
            newItem.thumbnails.add(i)
    
        # Pool all videos.
        for i in obj.videoitem.videos.all():
            newItem.videos.add(i)
    
    newItem.save()
# end _mergeVideo

def _mergeText(queryset):
    """
    Merges multiple :class:`.TextItem` objects into a single 
    :class:`.TextItem`\.
    """
    logger.debug('Merging {0} TextItems.'.format(len(queryset)))    
    
    # General Item merge operations.
    newItem = _mergeItem(queryset, TextItem, 'Text')
    
    # Text-specific operations.
    for obj in queryset:
        # Pool all original files.
        for i in obj.textitem.original_files.all():
            newItem.original_files.add(i)
            
    newItem.save()
# end _mergeText

def merge(modeladmin, request, queryset):
    """
    Merges two or more :class:`.Item` objects.
    
    A new :class:`.Item` is created, inheriting all contexts. Old :class:`.Item`
    objects set ``merged_with``.
    """

    lasttype = None
    for obj in queryset:
        if hasattr(obj, 'imageitem'):   thistype = 'image'
        elif hasattr(obj, 'videoitem'): thistype = 'video'
        elif hasattr(obj, 'audioitem'): thistype = 'audio'
        elif hasattr(obj, 'textitem'):  thistype = 'text'

        if lasttype is not None and thistype != lasttype:
            logger.debug('attempted to merge items of more than one type')
            # TODO: User should receive an informative error message.
            return

        lasttype = str(thistype)


    if thistype == 'image':
        _mergeImage(queryset)
    elif thistype == 'video':
        _mergeVideo(queryset)
    elif thistype == 'audio':
        _mergeAudio(queryset)
    elif thistype == 'text':
        _mergeText(queryset)
merge.short_description = 'Merge selected items'
# end merge

def doPerformDiffBotRequest(modeladmin, request, queryset):
    for obj in queryset:
        if obj.completed is None:
            performDiffbotRequest(obj)
doPerformDiffBotRequest.short_description = 'Perform selected requests'
