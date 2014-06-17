from django.contrib.auth.models import User
from django.db import models
import ast

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
    querystring = models.CharField(max_length=1000)

class Engine(models.Model):
    """
    A search engine.
    """
    parameters = ListField()
    manager = models.CharField(max_length=100, choices=engineManagers)


class QueryEvent(models.Model):
    """
    Generated whenever a user creates and dispatches a new query.
    """
    querystring = models.ForeignKey('QueryString')
    rangeStart = models.IntegerField()
    rangeEnd = models.IntegerField()
    datetime = models.DateTimeField(auto_now_add=True)

#    user = models.ForeignKey(User)
    queryresults = models.ManyToManyField('QueryResult', related_name='event', blank=True, null=True)
    engine = models.ForeignKey(Engine)

class QueryResult(models.Model):
    """
    Generated from a single response resulting from a :class:`.QueryEvent`\.
    """
    rangeStart = models.IntegerField()
    rangeEnd = models.IntegerField()
    result = models.TextField()     # Holds full JSON response.

    items = models.ManyToManyField('QueryItem')

class QueryItem(models.Model):
    """
    Generated from an individual item in a :class:`.QueryResult`\.
    """
    PENDING = 'PG'
    REJECTED = 'RJ'
    APPROVED = 'AP'
    statuses = (
        (PENDING, 'Pending'),
        (REJECTED, 'Rejected'),
        (APPROVED, 'Apprived')
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

