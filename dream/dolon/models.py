from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.db import models
import ast

from celery.result import AsyncResult, TaskSetResult


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
                                                    help_text=qs_helptext)

    def __unicode__(self):
        return unicode(self.querystring)

    def _Nevents(self):
        return unicode(len(self.queryevents.all()) )
    
#    def _Nitems(self):
#        I = QueryItem.objects.filter(queryresult__event__querystring__id=self.id)
#        return unicode(len(I))
    
    def _latestEvent(self):
        E = self.queryevents.latest('datetime')
        return unicode(E.datetime)

    events = property(_Nevents)
    latest = property(_latestEvent)
#    items = property(_Nitems)

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
        return unicode(self.manager)


class QueryEvent(models.Model):
    """
    Generated whenever a user creates a new query.
    """
    
    class Meta:
        verbose_name = 'Search event'
        verbose_name_plural = 'Search events'
    
    querystring = models.ForeignKey('QueryString', related_name='queryevents')
    rangeStart = models.IntegerField()
    rangeEnd = models.IntegerField()
    datetime = models.DateTimeField(auto_now=True)
    
    # Tasks and dispathing.
    dispatched = models.BooleanField(default=False)
    search_task = models.ForeignKey('GroupTask', null=True, blank=True, related_name='searchtaskevent')
    thumbnail_tasks = models.ManyToManyField('GroupTask', related_name='thumbtaskevent')


#    user = models.ForeignKey(User)
    queryresults = models.ManyToManyField('QueryResult', related_name='event', blank=True, null=True)
    engine = models.ForeignKey(Engine)

    def __unicode__(self):
        return unicode(self.querystring)

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

class Task(models.Model):
    """
    Represents a Celery task.
    """

    task_id = models.CharField(max_length=100)
    dispatched = models.DateTimeField(auto_now_add=True)
    
    def state(self):
        """
        Get the task state. Possible values: PENDING, STARTED, RETRY, FAILURE,
        SUCCESS.
        """

        result = AsyncResult(self.task_id)
        return result.state
    
    def result(self):
        """
        Get the result of this task. If not ready, returns None.
        """
        
        result = AsyncResult(self.task_id)
#        if result.read():
        return result.result
#        return None

class GroupTask(models.Model):
    task_id = models.CharField(max_length=100)
    subtask_ids = ListField()
    dispatched = models.DateTimeField(auto_now_add=True)
    
    def state(self):
        result = TaskSetResult(self.task_id, [ AsyncResult(s) for s in self.subtask_ids ])
        if result.successful():
            return 'DONE'
        elif result.failed():
            return 'FAILED'
        elif result.waiting():
            return 'RUNNING'
        else:
            return 'PENDING'
    

class QueryResult(models.Model):
    """
    Generated from a single response resulting from a :class:`.QueryEvent`\.
    """
    rangeStart = models.IntegerField()
    rangeEnd = models.IntegerField()
    result = models.TextField()     # Holds full JSON response.

    items = models.ManyToManyField('QueryItem', related_name='result')

class QueryItem(models.Model):
    """
    Generated from an individual item in a :class:`.QueryResult`\.
    """
    
    class Meta:
        verbose_name = 'Search result'
        verbose_name_plural = 'Search results'
    
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

    title = models.CharField(max_length=400)
    size = models.IntegerField()
    height = models.IntegerField()
    width = models.IntegerField()
    mime = models.CharField(max_length=50)
    contextURL = models.URLField(max_length=2000)
    thumbnailURL = models.URLField(max_length=2000)

    thumbnail = models.ForeignKey('Thumbnail', related_name='queryItems',
                                                          blank=True, null=True)
    image = models.ForeignKey('Image', related_name='queryItems',
                                                          blank=True, null=True)
    context = models.ForeignKey('Context', related_name='queryItems',
                                                          blank=True, null=True)

    def thumbimage(self):
        if self.thumbnail is not None:
            return '<img src="{0}"/>'.format(self.thumbnail.image.url)
        return None
    thumbimage.allow_tags = True

    def queryevents(self):
        events = [ e for r in self.result.all() for e in r.event.all() ]
        pattern = '<a href="/admin/dolon/queryevent/{0}/"><li>{1}, {2}, {3}</li></a>'
        return '\n'.join( [ pattern.format(e.id, e.querystring.querystring, e.datetime, e.engine ) for e in events ] )
    queryevents.allow_tags = True

class Thumbnail(models.Model):
    """
    A thumbnail image.
    """

    image = models.ImageField(upload_to='thumbnails', height_field='height',
                                                      width_field='width')
    url = models.URLField(max_length=2000)
    
    size = models.IntegerField()
    mime = models.CharField(max_length=50)
    
    # Should be auto-populated.
    height = models.IntegerField(blank=True)
    width = models.IntegerField(blank=True)

class Image(models.Model):
    """
    A fullsize image.
    """

    image = models.ImageField(upload_to='images', height_field='height',
                                                  width_field='width')
    url = models.URLField(max_length=2000)

    size = models.IntegerField()
    mime = models.CharField(max_length=50)
    
    # Should be auto-populated.
    height = models.IntegerField(blank=True)
    width = models.IntegerField(blank=True)


class Context(models.Model):
    """
    Context (text extracted from a webpage) for image(s).
    """

    url = models.URLField(max_length=2000)
    title = models.CharField(max_length=400)
    content = models.TextField()

