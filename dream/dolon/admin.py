from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from models import *
from managers import spawnSearch
from django.core import urlresolvers

def get_admin_url(obj):
    content_type = ContentType.objects.get_for_model(obj.__class__)
    url = urlresolvers.reverse('admin:%s_%s_change' % (content_type.app_label, content_type.model), args=(obj.id,))
    return url

class QueryEventInline(admin.TabularInline):
    model = QueryEvent
    readonly_fields = ('rangeStart', 'rangeEnd', 'datetime', 'engine')#, 'queryresults')

    extra = 0
    def has_delete_permission(self, request, obj=None):
        """
        :class:`.QueryEvent` should not be deletable.
        """
        return False

class QueryStringAdmin(admin.ModelAdmin):
    list_display = ('querystring', 'events', 'latest')#, 'items')
    inlines = (QueryEventInline,)
    
    def get_readonly_fields(self, request, obj=None):
        """
        Value of ``querystring`` should not be editable after creation.
        """

        if obj:
            return ('querystring',) + self.readonly_fields
        return self.readonly_fields

    def get_inline_instances(self, request, obj=None):
        """
        Should only display related :class:`.QueryEvent` instances when editing.
        """

        if obj:
            return super(QueryStringAdmin, self).get_inline_instances(request, obj)
        return []

def dispatch(modeladmin, request, queryset):
    for obj in queryset:
        task_id = spawnSearch(obj)
        task = GroupTask(task_id=task_id)
        task.save()
        print 'asdf', obj, task, task.state()
        obj.search_task = task
        obj.dispatched = True
        obj.save()

dispatch.short_description = 'Dispatch selected search events'

class QueryEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'querystring', 'datetime', 'rangeStart', 'rangeEnd', 
                    'items', 'dispatched', 'search_status', 'thumbnail_status')
    list_display_links = ('querystring',)
    actions = [dispatch]
    exclude = ['search_task', 'thumbnail_tasks']
    readonly_fields = ('items',)
    
    
    def get_readonly_fields(self, request, obj=None):
        """
        All fields should be readonly after creation.
        """

        if obj:
            return ('querystring', 'rangeStart', 'rangeEnd', 'engine', 'dispatched', 'queryresults', 'search_status', 'thumbnail_status') + self.readonly_fields
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Should not display :class:`.QueryResult` when adding.
        """
        
        if obj is None:
            self.exclude += ['queryresults', 'dispatched']

        return super(QueryEventAdmin, self).get_form(request, obj, **kwargs)

class ItemAdmin(admin.ModelAdmin):
    list_display = ('thumb_image','title', 'height','width', 'status', )#,'result',)
    readonly_fields = ('item_image', 'title', 'resource', 'status', 'size', 'height', 'width', 'mime', 'query_events', 'contexts')#'list_events',)
    exclude = ('image', 'context', 'thumbnail', 'events', 'url')
    list_filter = ('status','events')
    list_select_related = True
    search_fields = ['title',]
    
    def thumb_image(self, obj):
        return self.item_image(obj, list=True)
    thumb_image.allow_tags = True
    
    def item_image(self, obj, list=False):
        if obj.thumbnail is not None:
            pattern = '<a href="{0}"><img src="{1}"/></a>'
            if list:
                fullsize_url = get_admin_url(obj)
            else:
                if obj.image is not None:
                    fullsize_url = get_admin_url(obj.image)
                else:
                    fullsize_url = '#'
            return pattern.format(fullsize_url, obj.thumbnail.image.url)
        return None
    item_image.allow_tags = True
    
    def query_events(self, obj):
        """
        Generates a list of :class:`QueryEvent` instances associated with this
        :class:`.Item`\, with links to their respective admin change pages.
        """

        pattern = '<li><a href="{0}">{1}</a></li>'
            
        repr = '\n'.join([ pattern.format(get_admin_url(e), e) 
                        for e in obj.events.all() ])
        return repr
    query_events.allow_tags = True
    
class ContextAdmin(admin.ModelAdmin):
    list_display = ('status', 'url')
    list_display_links = ('status', 'url')
    readonly_fields = ('resource', 'title', 'content')
    exclude = ('url',)
    
    def resource(self, obj):
        """
        Generates a link to the original context URL, opening in a new tab.
        """
        pattern = '<a href="{0}" target="_blank">{0}</a>'
        return pattern.format(obj.url)
    resource.allow_tags = True

    def status(self, obj):
        """
        Returns True if data for this :class:`.Context` has been retrieved.
        """
        if obj.title is None and obj.content is None:
            return False
        return True
    status.boolean = True
    
class ImageAdmin(admin.ModelAdmin):
    list_display = ('status', 'url')
    list_display_links = ('status', 'url')    
    readonly_fields = ('fullsize_image', 'resource', 'size', 'mime', 'height', 'width')
    exclude = ('url','image')

    def resource(self, obj):
        """
        Generates a link to the original image URL, opening in a new tab.
        """
        pattern = '<a href="{0}" target="_blank">{0}</a>'
        return pattern.format(obj.url)
    resource.allow_tags = True

    def status(self, obj):
        """
        Returns True if data for this :class:`.Image` has been retrieved.
        """
        if obj.size == 0:# and obj.content is None:
            return False
        return True
    status.boolean = True
    
    def fullsize_image(self, obj):
        if obj.image is not None:
            pattern = '<img src="{0}"/>'
            return pattern.format(obj.image.url)
        return None
    fullsize_image.allow_tags = True
    
# Register your models here.
admin.site.register(QueryEvent, QueryEventAdmin)
admin.site.register(QueryString, QueryStringAdmin)

admin.site.register(Item, ItemAdmin)
admin.site.register(Image, ImageAdmin)


admin.site.register(Engine)