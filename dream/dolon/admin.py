from django.contrib import admin

from models import *
from util import *
from managers import spawnSearch
    
### Actions ###
def dispatch(modeladmin, request, queryset):
    """
    Dispatches a :class:`.QueryEvent` for searching and thumbnail retrieval.
    
    Used as an action in the :class:`.QueryEventAdmin`\.
    """

    for obj in queryset:
        task_id = spawnSearch(obj)
        task = GroupTask(task_id=task_id)
        task.save()
        obj.search_task = task
        obj.dispatched = True
        obj.save()
dispatch.short_description = 'Dispatch selected search events'    

### Inlines ###

class QueryEventInline(admin.TabularInline):
    model = QueryEvent
    readonly_fields = ('dispatched', 'range', 'engine', 'datetime', 'results')#, 'queryresults')
    exclude = ('rangeStart', 'rangeEnd', 'search_task', 'thumbnail_tasks', 'queryresults')
    ordering = ('datetime',)
    
    extra = 0
    def has_delete_permission(self, request, obj=None):
        """
        :class:`.QueryEvent` should not be deletable.
        """
        return False
        
    def range(self, obj):
        """
        Prettier representation of the start and end indices.
        """
        pattern = '{0}-{1}'
        return pattern.format(obj.rangeStart, obj.rangeEnd)
    range.allow_tags = True
    
    def results(self, obj):
        """
        Yields the number of :class:`.Item` associated with this 
        :class:`.QueryEvent`\, with a link to the filtered admin list view for
        :class:`.Item`\.
        """

        items = Item.objects.filter(events__id=obj.id)
        if len(items) > 0:
            pattern = '<a href="{0}?events__id__exact={1}">{2} items</a>'
            baseurl = '/'.join(get_admin_url(items[0]).split('/')[0:-2])
            
            return pattern.format(baseurl, obj.id, len(items))
        return None
    results.allow_tags = True
    
### ModelAdmins ###

class QueryStringAdmin(admin.ModelAdmin):
    list_display = ('querystring', 'events', 'last_used')#, 'items')
    inlines = (QueryEventInline,)
    
    def last_used(self, obj):
        print obj.latest()
        return pretty_date(obj.latest())
    
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

class QueryEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'querystring', 'datetime', 'range', 
                    'dispatched', 'search_status', 'thumbnail_status')
    list_display_links = ('querystring',)
    actions = [dispatch]
    exclude = ['search_task', 'thumbnail_tasks', 'queryresults']
    
    def change_view(self, request, obj, **kwargs):
        """
        Exclude rangeStart and rangeEnd in the change view.
        """
        
        self.exclude += ['rangeStart', 'rangeEnd']
        return super(QueryEventAdmin, self).change_view(request, obj, **kwargs)
    
    def result_sets(self, obj):
        """
        Generates a list of :class:`.QueryResult` instances associated with this
        :class:`.QueryEvent`\, with links to their respective admin change
        pages.
        """

        pattern = '<a href="{0}">{1}, s:{2}, e:{3}</a>'
        R = [ pattern.format(get_admin_url(r), obj.querystring.querystring, 
                 r.rangeStart, r.rangeEnd) for r in obj.queryresults.all() ]

        return '\n'.join(R)
    result_sets.allow_tags = True
    
    def results(self, obj):
        """
        Yields the number of :class:`.Item` associated with this 
        :class:`.QueryEvent`\, with a link to the filtered admin list view for
        :class:`.Item`\.
        """
            
        items = Item.objects.filter(events__id=obj.id)
        if len(items) > 0:
            pattern = '<a href="{0}?events__id__exact={1}">{2} items</a>'
            baseurl = '/'.join(get_admin_url(items[0]).split('/')[0:-2])
            
            return pattern.format(baseurl, obj.id, len(items))
        return None
    results.allow_tags = True
    
    def range(self, obj):
        """
        Prettier representation of the start and end indices.
        """
    
        pattern = '{0}-{1}'
        return pattern.format(obj.rangeStart, obj.rangeEnd)
    range.allow_tags = True
    
    def get_readonly_fields(self, request, obj=None):
        """
        All fields should be readonly after creation.
        """

        if obj:
            return ('querystring', 'datetime', 'engine', 'range', 'dispatched', 'results', 'search_status', 'thumbnail_status') + self.readonly_fields
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
        """
        Generates a thumbnail image element, for list display.
        """
        
        return self.item_image(obj, list=True)
    thumb_image.allow_tags = True
    
    def resource(self, obj):
        """
        Generates a link to the original image URL, opening in a new tab.
        """

        pattern = '<a href="{0}" target="_blank">{0}</a>'
        return pattern.format(obj.url)
    resource.allow_tags = True
    
    def contexts(self, obj):
        """
        Generates a list of associated :class:`.Context` instances, with links
        to their respective admin change pages.
        """

        pattern = '<li><a href="{0}">{1}</a></li>'
        repr = '\n'.join([ pattern.format(get_admin_url(c),c.url) 
                            for c in obj.context.all() ])
        return repr
    contexts.allow_tags = True
    
    def item_image(self, obj, list=False):
        """
        Generates a thumbnail image element, with a link to the fullsize
        :class:`.Image`\.
        """

        try:    # If something went wrong when downloading a thumbnail, 
                #  this will raise a ValueError.
            obj.thumbnail.image.url
        except ValueError:
            return None
        if obj.thumbnail is not None and obj.thumbnail.image is not None:
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
        """
        Generates a fullsize image element.
        
        TODO: constrain display size.
        """

        if obj.image is not None:
            pattern = '<img src="{0}"/>'
            return pattern.format(obj.image.url)
        return None
    fullsize_image.allow_tags = True      
    
### Registration ###

admin.site.register(QueryEvent, QueryEventAdmin)
admin.site.register(QueryString, QueryStringAdmin)

admin.site.register(Item, ItemAdmin)
admin.site.register(Image, ImageAdmin)

#admin.site.register(QueryResult)

admin.site.register(Engine)
admin.site.register(Context, ContextAdmin)