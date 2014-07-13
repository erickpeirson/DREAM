from django import forms
from django.contrib import admin
import autocomplete_light
from models import *
from util import *
from managers import spawnSearch
import uuid

### Forms ###

class QueryEventForm(forms.ModelForm):
    class Meta:
        model = QueryEvent
        
    def clean_creator(self):
        if not self.cleaned_data['creator']:
            return User()
        return self.cleaned_data['creator']

### Actions ###
def dispatch(modeladmin, request, queryset):
    """
    Dispatches a :class:`.QueryEvent` for searching and thumbnail retrieval.
    
    Used as an action in the :class:`.QueryEventAdmin`\.
    """

    for obj in queryset:
        task_id, subtask_ids = spawnSearch(obj)
        task = GroupTask(   task_id=task_id,
                            subtask_ids=subtask_ids )
        task.save()
        obj.search_task = task
        obj.dispatched = True
        obj.save()
dispatch.short_description = 'Dispatch selected search events'    

def approve(modeladmin, request, queryset):
    """
    Approves all selected :class:`.Items`\.
    """
    
    for obj in queryset:
        obj.status = 'AP'
        obj.save()
approve.short_description = 'Approve selected items'
        
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

def merge(modeladmin, request, queryset):
    """
    Merges two or more :class:`.Item` objects.
    
    A new :class:`.Item` is created, inheriting all contexts. Old :class:`.Item`
    objects set ``merged_with``.
    """
    
    largest = 0
    image = None
    
    largestThumb = 0
    thumbnail = None
    
    # Fake URL and title.
    identifier = str(uuid.uuid1())
    title = 'Merged item {0}'.format(identifier)
    url = 'http://roy.fulton.asu.edu/dolon/mergeditem/{0}'.format(identifier)
    
    newItem = Item( url = url,
                    title = title   )
    newItem.save()
    
    contexts = set([])
    for obj in queryset:
        # If any one Item is approved, they all are.
        if obj.status == 'AP':  
            newItem.status = 'AP'
            newItem.save()
        
        # Inherit any thumbnail.
        if newItem.thumbnail is None and obj.thumbnail is not None:
            newItem.thumbnail = obj.thumbnail
            newItem.save()
        
        # The new Item inherits the largest image, if there are any.
        if hasattr(obj, 'image'):
            if obj.size > largest:
                newItem.image = obj.image
                newItem.size = obj.size
                newItem.height = obj.height
                newItem.width = obj.width
                newItem.mime = obj.mime
                
                largest = obj.image.size
                newItem.save()
                
        # Pool all of the contexts.
        for c in obj.context.all():
            newItem.context.add(c)
            
        # Set merged_with on old items.
        obj.merged_with = newItem
        obj.hide = True
        obj.save()
    
    newItem.save()
merge.short_description = 'Merge selected items'

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
    form = QueryEventForm
    
    list_display = ('id', 'querystring', 'datetime', 'range', 
                    'dispatched', 'search_status', 'thumbnail_status')
    list_display_links = ('querystring',)
    actions = [dispatch]
    
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
            read_only = (   
                'querystring', 'datetime', 'engine', 'range', 'dispatched', 
                'results', 'search_status', 'thumbnail_status', 'creator'
                ) + self.readonly_fields
            return read_only
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Should not display :class:`.QueryResult` when adding.
        """
        
        exclude = [ 'search_task', 'thumbnail_tasks', 'queryresults' ]
        print obj, self.exclude
        if obj is None:
            self.exclude = exclude + ['dispatched', 'creator']
        else:
            self.exclude = exclude + ['rangeStart', 'rangeEnd']
        return super(QueryEventAdmin, self).get_form(request, obj, **kwargs)
    
    def save_model(self, request, obj, form, change):
        
        if not hasattr(obj, 'creator'):
            obj.creator = request.user
        obj.save()

class ItemAdmin(admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(Item)
    list_display = ('thumb_image','title', 'height','width', 'status',)
    readonly_fields = ( 'item_image', 'resource', 'status', 'size', 
                        'height', 'width', 'mime', 'query_events', 'contexts',
                        'creationDate',  'children', 'parent', 'hide')
    exclude = ('image', 'context', 'thumbnail', 'events', 'merged_with', 'url')
    list_filter = ('status','events','tags')
    list_editable = ['title',]
    list_select_related = True
    search_fields = ['title',]
    
    actions = [approve, reject, pend, merge]
    
    def parent(self, obj):
        """
        Display the item into which this item has been merged.
        """
        
        pattern = '<a href="{0}">{1}</a>'
        if obj.merged_with is not None:
            href = get_admin_url(obj.merged_with)
            title = obj.merged_with.title
            return pattern.format(href, title)
        return None
    parent.allow_tags = True
    
    def children(self, obj):
        """
        Display merged items from whence this item originated.
        """
        
        pattern = '<li><a href="{0}">{1}</a></li>'
        
        html = '<ul>'
        for c in obj.merged_from.all():
            html += pattern.format(get_admin_url(c), c.title)
        html += '</ul>'
        return html
    children.allow_tags = True
    
    def queryset(self, request):
        qs = super(ItemAdmin, self).queryset(request)
        if request.path.split('/')[-2] == 'item':   # Only filter changelist.
            return qs.exclude(hide=True)
        return qs
    
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
        repr = ''.join([ pattern.format(get_admin_url(c),c.url) 
                            for c in obj.context.all() ])
        return '<ul>{0}</ul>'.format(repr)
    contexts.allow_tags = True
    
    def item_image(self, obj, list=False):
        """
        Generates a thumbnail image element, with a link to the fullsize
        :class:`.Image`\.
        """

        try:    # If something went wrong when downloading a thumbnail, 
                #  this will raise a ValueError.
            obj.thumbnail.image.url
        except:# ValueError, AttributeError:
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
            
        repr = ''.join([ pattern.format(get_admin_url(e), e) 
                        for e in obj.events.all() ])
        return '<ul>{0}</ul>'.format(repr)
    query_events.allow_tags = True
    
class ContextAdmin(admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(Context)
    list_display = ('status', 'url')
    list_display_links = ('status', 'url')
    readonly_fields = ('resource', 'title', 'content', 'publicationDate')
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

class TagAdmin(admin.ModelAdmin):
#    readonly_fields = ('text', 'items', 'contexts')
    list_display = ('text', 'items', 'contexts')
    search_fields = ['text',]

    
    def items(self, obj):
        pattern = '<li><a href="{0}">{1}</a></li>'
        html = ''.join( [ pattern.format(get_admin_url(i),unidecode(i.title)) for i in obj.items() ] )
        return '<ul>{0}</ul>'.format(html)
    items.allow_tags = True
    
    def contexts(self, obj):
        pattern = '<li><a href="{0}">{1}</a></li>'
        for i in obj.contexts():
            print i
        html = ''.join( [ pattern.format(get_admin_url(i),i) for i in obj.contexts() ] )
        return '<ul>{0}</ul>'.format(html)
    contexts.allow_tags = True
    
        
    def get_readonly_fields(self, request, obj=None):
        """
        """

        if obj:
            read_only = ('text', 'items', 'contexts') + self.readonly_fields
            return read_only
        return self.readonly_fields        

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
    
class GroupTaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'state')
    
### Registration ###

admin.site.register(QueryEvent, QueryEventAdmin)
admin.site.register(QueryString, QueryStringAdmin)

admin.site.register(Item, ItemAdmin)
admin.site.register(Image, ImageAdmin)

#admin.site.register(QueryResult)

admin.site.register(Engine)
admin.site.register(Context, ContextAdmin)

admin.site.register(Tag, TagAdmin)

admin.site.register(Thumbnail)
admin.site.register(GroupTask, GroupTaskAdmin)