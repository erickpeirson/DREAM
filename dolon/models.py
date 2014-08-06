from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.conf import settings
from audiofield.fields import AudioField
import os.path

import logging
logging.basicConfig(filename=None, format='%(asctime)-6s: %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

import ast
import cPickle as pickle

from celery.result import AsyncResult, TaskSetResult

from util import *

engineManagers = (
    ( 'GoogleImageSearchManager', 'Google Image Search'),
    ( 'InternetArchiveManager', 'Internet Archive'),
)

# Create your models here.

class ListField(models.TextField):
    """
    For storing lists.
    """
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            value = []

        if isinstance(value, list):
            return value
        return ast.literal_eval(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return unicode(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_db_prep_value(value)

class QueryString(models.Model):
    class Meta:
        verbose_name = 'Search term'
        verbose_name_plural = 'Search terms'

    qs_helptext = 'Enter some search terms to use in your queries.'
    querystring = models.CharField(max_length=1000, verbose_name='Search terms',
                                    help_text=qs_helptext, unique=True)

    def __unicode__(self):
        return unicode(self.querystring)

    def _Nevents(self):
        return len(self.queryevents.all()) 
    
    def latest(self):
        E = self.queryevents.latest('datetime')
        return E.datetime

    events = property(_Nevents)

class Engine(models.Model):
    """
    A search engine.
    """
    
    parameters = ListField()    # GET params.
    manager = models.CharField(max_length=100, choices=engineManagers)
    
    ## Limits ##
    
    # Number of requests per second.
    ratelimit = models.IntegerField(blank=True, null=True,
                    verbose_name='max calls per second')
    
   # Number of requests per day.   
    daylimit = models.IntegerField(blank=True, null=True, 
                    verbose_name='max calls per day')
    #   Counter for daily requests.                    
    dayusage = models.IntegerField(default=0, verbose_name='calls made today')
    
    # Number of requests per month.
    monthlimit = models.IntegerField(blank=True, null=True,
                    verbose_name='max calls per month')
    #   Counter for monthly requests.
    monthusage = models.IntegerField(default=0, 
                    verbose_name='calls made this month') 
    
    # Pages.
    pagesize = models.IntegerField(default=10,  # Max no. items per page.
                    verbose_name='max results per page')  
    pagelimit = models.IntegerField(blank=True, null=True, 
                    verbose_name='max number of pages') # Max no. pages.
        
    class Meta:
        verbose_name_plural = 'Custom search engines'
        verbose_name = 'Custom search engine'

    def __unicode__(self):
        return unicode( [ label for value, label in engineManagers 
                            if value == self.manager ][0] + ' ' + str(self.id) )

class QueryEvent(models.Model):
    """
    Generated whenever a user creates a new query.
    """
    
    class Meta:
        verbose_name = 'query'
        verbose_name_plural = 'queries'
    
    querystring = models.ForeignKey('QueryString', related_name='queryevents',
                                                verbose_name='search string')
    rangeStart = models.IntegerField(verbose_name='Starting at')
    rangeEnd = models.IntegerField(verbose_name='Ending at')

    datetime = models.DateTimeField(auto_now=True)
    
    # Tasks and dispathing.
    dispatched = models.BooleanField(default=False)
    state = models.CharField(max_length=50, blank=True, null=True)
    
    search_task = models.ForeignKey(    
                        'GroupTask', null=True, blank=True, 
                        related_name='searchtaskevent'  )
    thumbnail_tasks = models.ManyToManyField(   
                        'GroupTask', 
                        related_name='thumbtaskevent'  )

    creator = models.ForeignKey(User, related_name='created_events', blank=True)

    queryresults = models.ManyToManyField(
                        'QueryResult', blank=True, null=True,
                        related_name='event_instance'   )
                        
                        
    engine = models.ForeignKey(Engine, related_name='engine_events',
                                        verbose_name='Search engine'    )

    def __unicode__(self):
        pattern = '"{0}", items {1}-{2}, created {3}'
        date = pretty_date(self.datetime)
        repr = pattern.format(  self.querystring, self.rangeStart, 
                                self.rangeEnd, date )
        return unicode(repr)

    def items(self):
        qs = Item.objects.filter(events__id=obj.id).exclude(hide=True)
        return unicode(len(qs))
    
    def search_status(self):
        """
        Checks associated :class:`.GroupTask` for status.
        
        If the :class:`.GroupTask` has state 'ERROR', 'FAILED', or 'DONE', then
        ``state`` should record that state permanently. Otherwise, ``state``
        is updated.
        
        If there is no associated :class:`.GroupTask`\, returns 'PENDING'.
        """
        
        if self.search_task is not None:
            state = self.search_task.state()
            if self.state not in ['ERROR','FAILED','DONE']:
                self.state = state
                self.save()
            return self.state
        return 'PENDING'

    def thumbnail_status(self):
        alltasks = self.thumbnail_tasks.all()
        Ntasks = len(alltasks)
        if Ntasks > 0:
            done = float(len([ t for t in alltasks if t.state() == 'DONE' ]))
            comp = int(round(done*100/Ntasks, 0))
            if comp == 100:
                return 'DONE'
            return '{0}% COMPLETE'.format(comp)
        return 'PENDING'

class QueryResult(models.Model):
    """
    Generated from a single response resulting from a :class:`.QueryEvent`\.
    """
    rangeStart = models.IntegerField()
    rangeEnd = models.IntegerField()
    result = models.TextField()     # Holds full JSON response.

    resultitems = models.ManyToManyField(
                    'QueryResultItem', 
                     related_name='queryresult_instance'    )

class QueryResultItem(models.Model):
    url = models.URLField(max_length=2000)
    contextURL = models.URLField(max_length=2000)
    
    title = models.CharField(max_length=400, blank=True, null=True)

    params = models.CharField(max_length=50000, blank=True, null=True)
    
    item = models.ForeignKey(
                    'Item', null=True, blank=True, 
                    related_name='query_result_item'    )
    
    type = models.CharField(max_length=50)
    
    def save(self, *args, **kwargs):
        """
        When a :class:`.QueryResultItem` is created, it should get or create
        a :class:`.Item`\.
        """

        params = pickle.loads(self.params)
        if 'length' in params: length = params['length']
        else: length = 0
            
        if 'size' in params: size = params['size']
        else: size = 0
        
        if 'creator' in params: creator = params['creator']
        else: creator = ''
                    
        ### Images ###
        if self.type == 'image':
            i = ImageItem.objects.get_or_create(url=self.url,
                    defaults = {
                        'title': self.title,
                        'creator': params['creator']  }   )[0]

            # Associate thumbnail, image, and context.
            if i.thumbnail is None and len(params['thumbnailURL']) > 0:
                print params['thumbnailURL']
                i.thumbnail = Thumbnail.objects.get_or_create(
                                    url=params['thumbnailURL'][0]   )[0]
            if i.image is None:
                i.image = Image.objects.get_or_create(url=self.url)[0]
        
        ### Videos ###
        elif self.type == 'video':
            i = VideoItem.objects.get_or_create(url=self.url,
                    defaults = {
                        'title': self.title,
                        'length': length,
                        'creator': creator  }   )[0]
                        
            if len(i.thumbnails.all()) == 0 and len(params['thumbnailURL']) > 0:
                for url in params['thumbnailURL']:
                    thumb = Thumbnail.objects.get_or_create(url=url)[0]                        
                    i.thumbnails.add(thumb)
                    
            if len(i.videos.all()) == 0 and len(params['files']) > 0:
                for url in params['files']:
                    video = Video.objects.get_or_create(url=url)[0]
                    i.videos.add(video)
                      
        ### Audio ###
        elif self.type == 'audio':
            i = AudioItem.objects.get_or_create(url=self.url,
                    defaults = {
                        'title': self.title,
                        'length': length,
                        'creator': creator  }   )[0]     
                        
            if i.thumbnail is None and len(params['thumbnailURL']) > 0:
                i.thumbnail = Thumbnail.objects.get_or_create(
                                    url=params['thumbnailURL'][0]   )[0]                                           
                                    
            if len(i.audio_segments.all()) == 0 and len(params['files']) > 0:
                for url in params['files']:
                    seg = Audio.objects.get_or_create(url=url)[0]
                    i.audio_segments.add(seg)                                    

        context  = Context.objects.get_or_create(url=self.contextURL)[0]
        i.context.add(context)
        i.save()

        self.item = i
        
        # Go ahead and save.
        super(QueryResultItem, self).save(*args, **kwargs)

class Item(models.Model):
    """
    Generated from an individual item in a :class:`.QueryResult`\.
    """
    
    class Meta:
        verbose_name = 'media item'
        verbose_name_plural = 'media items'
    
    PENDING = 'PG'
    REJECTED = 'RJ'
    APPROVED = 'AP'
    statuses = (
        (PENDING, 'Pending'),
        (REJECTED, 'Rejected'),
        (APPROVED, 'Approved')
    )
    
    types = (
        ('Audio', 'Audio'),
        ('Video', 'Video'),
        ('Text', 'Text'),
        ('Image', 'Image')
    )

    url = models.URLField(max_length=2000, unique=True)
    
    status = models.CharField(max_length=2, choices=statuses, default=PENDING)

    title = models.CharField(max_length=400, blank=True, null=True)

    context = models.ManyToManyField('Context', related_name='items',
                                                          blank=True, null=True)
                                                          
    events = models.ManyToManyField('QueryEvent', related_name='items', 
                                                          blank=True, null=True)
                                                          
    creator = models.CharField(max_length=400, blank=True, null=True)
    
    creationDate = models.DateTimeField(blank=True, null=True)
    """Unclear what this value should be."""
    
    tags = models.ManyToManyField(  'Tag', blank=True, null=True,
                                    related_name='tagged_items' )
                                    
    merged_with = models.ForeignKey(    'Item', blank=True, null=True,
                                        related_name='merged_from', 
                                        on_delete=models.SET_NULL )
    """
    If this has a value, should not appear in any results (see property 
    ``hide``). Allows us to umerge items if necessary.
    """



    type = models.CharField(max_length=50, choices=types, blank=True, null=True)
    """
    Audio, Video,
    """

    hide = models.BooleanField(default=False, verbose_name='hidden')
    retrieved = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.title)

    def save(self, *args, **kwargs):
        if not self.pk:
            if hasattr(self, 'audioitem'):   self.type = 'Audio'
            elif hasattr(self, 'videoitem'): self.type = 'Video'
            elif hasattr(self, 'imageitem'): self.type = 'Image'
            elif hasattr(self, 'textitem'):  self.type = 'Text'
        
        super(Item, self).save(*args, **kwargs)


        
class ImageItem(Item):
    """
    """
    
    class Meta:
        verbose_name = 'image'
        verbose_name_plural = 'images'
        
    height = models.IntegerField(default=0, null=True, blank=True)
    width = models.IntegerField(default=0, null=True, blank=True)        
        
    thumbnail = models.ForeignKey(  'Thumbnail', blank=True, null=True,
                                    related_name='imageitem_thumbnail'   )
    image = models.ForeignKey('Image', blank=True, null=True,
                                    related_name='imageitem_fullsize'   )


class VideoItem(Item):
    """
    """
    
    class Meta:
        verbose_name = 'video'
        verbose_name_plural = 'videos'

    thumbnails = models.ManyToManyField(    'Thumbnail', blank=True, null=True,
                                            related_name='video_items'  )

    videos = models.ManyToManyField(    'Video', blank=True, null=True,
                                        related_name='videoitem'   )

    length = models.IntegerField(   default=0, null=True, blank=True    )
    
class AudioItem(Item):
    """
    """
    
    class Meta:
        verbose_name = 'audio recording'
        verbose_name_plural = 'audio recordings'
    
    thumbnail = models.ForeignKey(  'Thumbnail', blank=True, null=True,
                                    related_name='audioitem_thumbnail'   )
                                    
    audio_segments = models.ManyToManyField(    'Audio', blank=True, null=True,
                                                related_name='segment'  )

    length = models.IntegerField(   default=0, null=True, blank=True    )
    
    description = models.TextField( null=True, blank=True   )

class GroupTask(models.Model):
    task_id = models.CharField(max_length=1000)
    subtask_ids = ListField()
    dispatched = models.DateTimeField(auto_now_add=True)
    
    def state(self):
        subtasks = [ AsyncResult(s) for s in self.subtask_ids ]
        result = TaskSetResult(self.task_id, subtasks)

        if result.ready():
            r = result.get()[0]
            if r == 'ERROR':
                return r
            elif result.successful():
                return 'DONE'
            elif result.failed():
                return 'FAILED'
        elif result.waiting():
            return 'RUNNING'
        else:
            return 'PENDING'

class Thumbnail(models.Model):
    """
    A thumbnail image.
    """

    url = models.URLField(max_length=2000, unique=True)
    image = models.ImageField(upload_to='thumbnails', height_field='height',
                                                      width_field='width',
                                                      null=True, blank=True)
    
    mime = models.CharField(max_length=50, null=True, blank=True)
    
    # Should be auto-populated.
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)

class Image(models.Model):
    """
    A fullsize image.
    """

    url = models.URLField(max_length=2000, unique=True)
    
    image = models.ImageField(upload_to='images', height_field='height',
                                                  width_field='width',
                                                  null=True, blank=True)

    size = models.IntegerField(default=0)
    mime = models.CharField(max_length=50, null=True, blank=True)
    
    # Should be auto-populated.
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
    
    def __unicode__(self):
        return unicode(self.url)
        
class Video(models.Model):
    """
    A video object.
    """
    
    url = models.URLField(max_length=2000, unique=True)
    
    video = models.FileField(upload_to='videos', null=True, blank=True)

    size = models.IntegerField(default=0)
    length = models.IntegerField(default=0)    
    mime = models.CharField(max_length=50, null=True, blank=True)    
    
    def __unicode__(self):
        return unicode(self.url)
            
class Audio(models.Model):
    """
    An audio object.
    """
    
    url = models.URLField(max_length=2000, unique=True)
    
    size = models.IntegerField(default=0)
    length = models.IntegerField(default=0)    
    mime = models.CharField(max_length=50, null=True, blank=True)      

    audio_file = models.FileField(upload_to='audio', null=True, blank=True)
#    audio_file = AudioField(    upload_to='audio', blank=True,
#                                ext_whitelist=(".mp3", ".wav", ".ogg"),
#                                help_text=("Allowed type - .mp3, .wav, .ogg")  )        

    def __unicode__(self):
        return unicode(self.url) 
                
    def audio_file_player(self):
        """audio player tag for admin"""
        if self.audio_file:
            file_url = settings.MEDIA_URL + str(self.audio_file)
            player_string = '<ul class="playlist"><li style="width:250px;">\
            <a href="%s">%s</a></li></ul>' % (file_url, os.path.basename(self.audio_file.name))
            return player_string
    audio_file_player.allow_tags = True
    audio_file_player.short_description = ('Audio file player')
        

class Tag(models.Model):
    """
    A user-added descriptor for an :class:`.Item`\.
    """
    
    text = models.CharField(max_length=200, unique=True)
    
    def __unicode__(self):
        return unicode(self.text)
        
    def items(self):
        return self.tagged_items.all()
    
    def contexts(self):
        return self.tagged_contexts.all()
    

class Context(models.Model):
    """
    Context (text extracted from a webpage) for image(s).
    """

    url = models.URLField(max_length=2000, unique=True)
    title = models.CharField(max_length=400, null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    
    publicationDate = models.DateTimeField(blank=True, null=True)
    
    tags = models.ManyToManyField(  'Tag', blank=True, null=True,
                                    related_name='tagged_contexts' )

    def __unicode__(self):
        if self.title is not None:
            return unicode(self.title)
        return unicode(self.url)
