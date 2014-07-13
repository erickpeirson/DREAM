from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
#from audit_log.models.fields import CreatingUserField, LastUserField
from django.db import models
from unidecode import unidecode

import ast

from celery.result import AsyncResult, TaskSetResult

from util import *

engineManagers = (( 'GoogleImageSearchManager', 'Google'),)

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
        return unicode(unidecode(self.querystring))

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
    parameters = ListField()
    manager = models.CharField(max_length=100, choices=engineManagers)
    
    class Meta:
        verbose_name_plural = 'Custom search engines'
        verbose_name = 'Custom search engine'

    def __unicode__(self):
        return unicode(unidecode(self.manager))


class QueryEvent(models.Model):
    """
    Generated whenever a user creates a new query.
    """
    
    class Meta:
        verbose_name = 'query'
        verbose_name_plural = 'queries'
    
    querystring = models.ForeignKey('QueryString', related_name='queryevents')
    rangeStart = models.IntegerField()
    rangeEnd = models.IntegerField()
    datetime = models.DateTimeField(auto_now=True)
    
    # Tasks and dispathing.
    dispatched = models.BooleanField(default=False)
    
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
                        
    engine = models.ForeignKey(Engine)

    def __unicode__(self):
        pattern = '"{0}", items {1}-{2}, dispatched {3}'
        date = pretty_date(self.datetime)
        repr = pattern.format(  self.querystring, self.rangeStart, 
                                self.rangeEnd, date )
        return unicode(unidecode(repr))

    def items(self):
        return unicode(len(QueryItem.objects.filter(result__event__id=self.id)))
    
    def search_status(self):
        if self.search_task is not None:
            return self.search_task.state()
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
    thumbnailURL = models.URLField(max_length=2000)
    
    title = models.CharField(max_length=400, blank=True, null=True)

    size = models.IntegerField(default=0)
    mime = models.CharField(max_length=50, null=True, blank=True)
    
    # Should be auto-populated.
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
    
    item = models.ForeignKey(
                    'Item', null=True, blank=True, 
                    related_name='query_result_item'    )
    
    def save(self, *args, **kwargs):
        """
        When a :class:`.QueryResultItem` is created, it should get or create
        a :class:`.Item`\.
        """
        
        i = Item.objects.get_or_create(url=self.url,
                defaults = {
                    'title': self.title,
                    'size': self.size,
                    'height': self.height,
                    'width': self.width,
                    'mime': self.mime,  }   )[0]

        # Associate thumbnail, image, and context.
        if i.thumbnail is None:
            i.thumbnail = Thumbnail.objects.get_or_create(url=self.thumbnailURL)[0]
        if i.image is None:
            i.image = Image.objects.get_or_create(url=self.url)[0]

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

    url = models.URLField(max_length=2000, unique=True)
    
    status = models.CharField(max_length=2, choices=statuses, default=PENDING)

    title = models.CharField(max_length=400, blank=True, null=True)

    size = models.IntegerField(default=0, null=True, blank=True)
    mime = models.CharField(max_length=50, null=True, blank=True)
    height = models.IntegerField(default=0, null=True, blank=True)
    width = models.IntegerField(default=0, null=True, blank=True)

    thumbnail = models.ForeignKey('Thumbnail', related_name='queryItems',
                                                          blank=True, null=True)
    image = models.ForeignKey('Image', related_name='queryItems',
                                                          blank=True, null=True)
    context = models.ManyToManyField('Context', related_name='items',
                                                          blank=True, null=True)
                                                          
    events = models.ManyToManyField('QueryEvent', related_name='items', 
                                                          blank=True, null=True)
    
    creationDate = models.DateTimeField(blank=True, null=True)
    """Unclear what this value should be."""
    
    tags = models.ManyToManyField(  'Tag', blank=True, null=True,
                                    related_name='tagged_items' )
                                    
    merged_with = models.ForeignKey(    'Item', blank=True, null=True,
                                        related_name='merged_from'  )
    """
    If this has a value, should not appear in any results (see property 
    ``hide``). Allows us to umerge items if necessary.
    """
    
    hide = models.BooleanField(default=False, verbose_name='hidden')

    def __unicode__(self):
        return unicode(self.title)

class GroupTask(models.Model):
    task_id = models.CharField(max_length=1000)
    subtask_ids = ListField()
    dispatched = models.DateTimeField(auto_now_add=True)
    
    def state(self):
        subtasks = [ AsyncResult(s) for s in self.subtask_ids ]
        result = TaskSetResult(self.task_id, subtasks)
        if result.successful():
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
        return unicode(unidecode(self.url))

class Tag(models.Model):
    """
    A user-added descriptor for an :class:`.Item`\.
    """
    
    text = models.CharField(max_length=200, unique=True)
    
    def __unicode__(self):
        return unicode(unidecode(self.text))
        
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
            return unicode(unidecode(self.title))
        return unicode(unidecode(self.url))
