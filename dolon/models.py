from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.conf import settings
from audiofield.fields import AudioField
import os.path

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^dolon\.models\.ListField"])

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
    ( 'TwitterManager', 'Twitter'),
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
    
    name = models.CharField(max_length=100, null=True, blank=True)
    
    parameters = ListField()    # GET params.
    manager = models.CharField(max_length=100, choices=engineManagers)
    
    oauth_token = models.ForeignKey('OAuthAccessToken', null=True, blank=True,
                    help_text='Select an OAuth access token if required for ' +\
                              'this service.')
    
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
        if self.name is None:
            return unicode( [ label for value, label in engineManagers 
                            if value == self.manager ][0] + ' ' + str(self.id) )
        else:
            return unicode(self.name)
# end Engine class.

class QueryEvent(models.Model):
    """
    Generated whenever a user creates a new query.
    """
    
    class Meta:
        verbose_name = 'query'
        verbose_name_plural = 'queries'
        
    helptext = {}
    
    search_options = (
            ('ST','String'),
            ('UR','User'),
            ('TG','Tag'),
        )
    
    # Entered by user.
    search_by = models.CharField(
                    max_length=2, choices=search_options, default='ST'  )
    
    
    # Search by string.
    querystring = models.ForeignKey(    'QueryString',
                                        related_name='queryevents',
                                        verbose_name='search string',
                                        null=True, blank=True, default=-1    )
                                        
    rangeStart = models.IntegerField(   verbose_name='Starting at', 
                                        null=True, blank=True, default=1  )
                                        
    rangeEnd = models.IntegerField(     verbose_name='Ending at', 
                                        null=True, blank=True, default=10   )
    
    engine = models.ForeignKey(         'Engine',
                                        related_name='engine_events',
                                        verbose_name='Search engine'   )    

    # Search by User.
    user = models.ForeignKey(           'SocialUser', blank=True, null=True   )
    """Used for social media user searches."""
    
    # Search by Tag.
    tag = models.ForeignKey(            'HashTag', blank=True, null=True  )
    """e.g. a hastag"""
    
    
    # Temporal options.
    before = models.DateField(blank=True, null=True)
    after = models.DateField(blank=True, null=True)

    # Set automatically.
    datetime = models.DateTimeField(auto_now=True)
    
    # Set upon dispatch.
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

    def __unicode__(self):
        if self.search_by == 'ST':
            pattern = 'String "{0}" in {1}, items {2}-{3}'
            value = self.querystring.querystring
        elif self.search_by == 'UR':
            pattern = 'User {0} in {1}, items {2}-{3}'
            value = self.user.handle
        elif self.search_by == 'TG':
            pattern = 'Tag {0} in {1}, items {2}-{3}'
            value = self.tag.string
            
        repr = pattern.format(  value, self.engine, 
                                self.rangeStart, self.rangeEnd  )
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
            if state != 'PENDING' and self.state not in ['FAILED', 'ERROR']:
                self.state = state
                self.save()
        return self.state
# end QueryEvent class.        

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
        """
        Set type based on which subclass is instantiated.
        """
        
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

    images = models.ManyToManyField('Image', blank=True, null=True)

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

class TextItem(Item):
    """
    """

    class Meta:
        verbose_name = 'text'
        verbose_name_plural = 'texts'

    snippet = models.TextField(blank=True, null=True)
    length = models.IntegerField(default=0, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    original_files = models.ManyToManyField(  'Text', blank=True, null=True   )
    contents = models.TextField(blank=True, null=True)


class GroupTask(models.Model):
    task_id = models.CharField(max_length=1000)
    subtask_ids = ListField()
    dispatched = models.DateTimeField(auto_now_add=True)
    
    def state(self):
        result = AsyncResult(self.task_id)
        if not result.ready():
            return result.state
        if result.get() == 'ERROR':
            return 'FAILED'
        return result.state

class Thumbnail(models.Model):
    """
    A thumbnail image.
    """

    url = models.URLField(max_length=2000, unique=True)
    image = models.ImageField(  upload_to='thumbnails', height_field='height',
                                width_field='width', null=True, blank=True  )
    
    mime = models.CharField(max_length=50, null=True, blank=True)
    
    # Should be auto-populated.
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)

class Text(models.Model):
    """
    A text document.
    """

    url = models.URLField(max_length=2000, unique=True)

    text_file = models.FileField(upload_to='texts', null=True, blank=True)

    size = models.IntegerField( default=0, null=True, blank=True,
        help_text='File size in bytes.' )

    mime = models.CharField(max_length=50, null=True, blank=True)

class Image(models.Model):
    """
    A fullsize image.
    """

    url = models.URLField(max_length=2000, unique=True)
    
    image = models.ImageField(  upload_to='images', height_field='height',
                                width_field='width', null=True, blank=True  )

    size = models.IntegerField(default=0)
    mime = models.CharField(max_length=50, null=True, blank=True)
    
    # Should be auto-populated.
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
    
    def __unicode__(self):
        return unicode(self.url)

    def type(self):
        """
        Return mime-type if available, or try to guess based on filename.
        """
        
        known_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'tif': 'image/tiff',
            'tiff': 'image/tiff',
            'bmp': 'image/bmp'
        }
        
        if self.mime is not None:
            return self.mime
        else:
            ext = self.url.split('.')[-1].lower()
            if ext in known_types:
                return known_types[ext]
        return None

        
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

    def type(self):
        """
        Return mime-type if available, or try to guess based on filename.
        """
        
        known_types = {
            'm1v':  'video/mpeg',
            'm2v':  'video/mpeg',
            'mp2':  'video/mpeg',
            'mp4':  'video/mpeg',
            'mpeg': 'video/mpeg',
            'mpg':  'video/mpeg',
            'mpa':  'video/mpeg',
            'avi':  'video/avi',
            'ogv':  'video/ogg',
            'wmv':  'video/x-ms-wmv',
            '3gp':  'video/3gpp',
            'mov':  'video/quicktime'
        }
        
        if self.mime is not None:
            return self.mime
        else:
            ext = self.url.split('.')[-1].lower()
            if ext in known_types:
                return known_types[ext]
        return None
            
class Audio(models.Model):
    """
    An audio object.
    """
    
    url = models.URLField(max_length=2000, unique=True)
    
    size = models.IntegerField(default=0)
    length = models.IntegerField(default=0)    
    mime = models.CharField(max_length=50, null=True, blank=True)      

    audio_file = models.FileField(upload_to='audio', null=True, blank=True)

    def __unicode__(self):
        return unicode(self.url)

    def type(self):
        """
        Return mime-type if available, or try to guess based on filename.
        """
        
        known_types = {
            'oga':  'audio/ogg',
            'ogg':  'audio/ogg',
            'spx':  'audio/ogg',
            'flac': 'audio/flac',
            'm2a':  'audio/mpeg',
            'mp2':  'audio/mpeg',
            'mp3':  'audio/mpeg',
            'mpa':  'audio/mpeg',
            'mpg':  'audio/mpeg',
            'wav':  'audio/wav',
            'aif':  'audio/aiff',
            'aifc':  'audio/aiff',
            'aiff':  'audio/aiff',
        }
        
        if self.mime is not None:
            return self.mime
        else:
            ext = self.url.split('.')[-1].lower()
            if ext in known_types:
                return known_types[ext]
        return None
        

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
    retrieved = models.BooleanField(default=False)
    """Should be set True when retrieved."""
    
    title = models.CharField(max_length=400, null=True, blank=True)
    """Page title. Default is set by SearchManager, but updated by DiffBot."""
    
    content = models.TextField(null=True, blank=True)
    """Full content of the resource, including HTML, etc."""
    
    publicationDate = models.DateTimeField(blank=True, null=True)
    """If retrievable. We rely on DiffBot for this."""
    
    tags = models.ManyToManyField(  'Tag', blank=True, null=True,
                                    related_name='tagged_contexts' )

    # There should actually only be one of these, but using an M2M gives some
    # need flexibility in other places.
    diffbot_requests = models.ManyToManyField(  
                        'DiffBotRequest', related_name='requesting_context', 
                        blank=True, null=True   )
    use_diffbot = models.BooleanField(default=True)
    """Can set this to False to block DiffBotRequest creation."""
                            
    text_content = models.TextField(null=True, blank=True)
    """Main article or page content, stripped of any HTML."""
    
    author = models.CharField(max_length=1000, null=True, blank=True)
    """Freeform, may include names, e-mail addresses, etc."""
    
    language = models.CharField(max_length=100, null=True, blank=True)

    def __unicode__(self):
        if self.title is not None:
            return unicode(self.title)
        return unicode(self.url)
        
class SocialPlatform(models.Model):
    """
    e.g. Twitter, Facebook, Flickr
    """
    
    name = models.CharField(max_length=500)
    url = models.CharField(max_length=500)
    
    def __unicode__(self):
        return unicode(self.name)
        
class SocialUser(models.Model):
    """
    A user on a social media website.
    """
    
    handle = models.CharField(max_length=500)
    """username, email, whatever is used to identify the user."""
    
    platform = models.ForeignKey(SocialPlatform)
    """e.g. Twitter, Facebook, Flickr."""
    
    profile_url = models.CharField(max_length=500, null=True, blank=True)
    """for quick access"""
    
    description = models.TextField(null=True, blank=True)
    """could be a bio, or entered by a researcher."""
    
    user_id = models.CharField(max_length=50, blank=True, null=True)

    def content(self):
        """:class:`.Item`\s generated by this :class:`.SocialUser`\."""
        
        filt = '{0}:{1}:{2}'.format(self.platform, self.user_id, self.handle)
        items = Item.objects.filter(creator=filt)
        return items
    
class HashTag(models.Model):
    """
    A tag used on a social media site.
    """
    
    string = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    """Optional, entered by researcher if desired."""
    
    def __unicode__(self):
        return unicode(self.string)
        
    def save(self): 
        # Prepend hash if necessary.
        if self.string[0] != '#': self.string = '#' + self.string
        super(HashTag, self).save(self)
    
class DiffBotRequest(models.Model):
    """
    A job for the DiffBot!
    """
    
    type = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    attempted = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    
    parameters = ListField(default=[''])
    
    response = models.TextField(blank=True, null=True)


class OAuthAccessToken(models.Model):
    """
    
    """
    
    class Meta:
        verbose_name = "OAuth access token"
        verbose_name_plural = "OAuth access tokens"

    
    created = models.DateTimeField(auto_now_add=True)
    
    oauth_token = models.CharField(max_length=1000)
    oauth_token_secret = models.CharField(max_length=100)
    
    oauth_verifier = models.CharField(max_length=1000, blank=True, null=True)
    oauth_access_token = models.CharField(max_length=1000, blank=True, null=True)
    oauth_access_token_secret = models.CharField(max_length=1000, blank=True, null=True)
    
    
    user_id = models.CharField(max_length=50, blank=True, null=True)
    screen_name = models.CharField(max_length=200, blank=True, null=True,
                help_text="Some platforms won't provide a username; you can" + \
                          " enter one manually if you like.")
    
    creator = models.ForeignKey(User, blank=True, null=True)

    platform = models.ForeignKey(SocialPlatform, null=True, blank=True,
                help_text="If adding a token, you will be directed to this" + \
                          " platform's website to log in.")

    expires = models.DateTimeField(null=True, blank=True,
                help_text = "Some platforms expire access tokens after some" + \
                            " period of time. When a token expires, it will" + \
                            " no longer be usable.")                        
                    