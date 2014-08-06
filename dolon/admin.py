from django import forms
from django.contrib import admin
import autocomplete_light
from models import *
from util import *
from tasks import *
import uuid

from django.db.models.signals import pre_delete
from django.dispatch import receiver

import logging
logging.basicConfig(filename=None, format='%(asctime)-6s: %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel('INFO')

### Receivers ###

@receiver(pre_delete, sender=Item)
def itemDeleteReceiver(sender, **kwargs):
    obj = kwargs.get('instance')
    if obj.merged_from is not None:
        for i in obj.merged_from.all():
            i.hide = False
            i.save()

### Forms ###

class QueryEventForm(forms.ModelForm):
    class Meta:
        model = QueryEvent
        
    def clean_creator(self):
        if not self.cleaned_data['creator']:
            return User()
        return self.cleaned_data['creator']

### Actions ###

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
            if obj.image.size > largest:
                newItem.image = obj.image
                newItem.height = obj.height
                newItem.width = obj.width
                newItem.mime = obj.mime
                
                largest = obj.image.size
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
        
merge.short_description = 'Merge selected items'

### Inlines ###

class QueryEventInline(admin.TabularInline):
    model = QueryEvent
    readonly_fields = ('dispatched', 'range', 'engine', 'datetime', 'results')
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
                    'dispatched', 'search_status', 'results')
    list_display_links = ('querystring',)
    actions = [dispatch, reset]
    
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
            
        items = Item.objects.filter(events__id=obj.id).exclude(hide=True)
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
                'results', 'search_status', 'creator' ) + self.readonly_fields
            return read_only
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Should not display :class:`.QueryResult` when adding.
        """
        
        exclude = [ 'search_task', 'thumbnail_tasks', 'queryresults', 'state' ]
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
    list_display = ('icon', 'thumb_image','title', 'status','retrieved', 'type' )
    readonly_fields = ( 'item_image', 'resource', 'status', 'retrieved', 
                        'query_events', 'contexts', 'creationDate',  'children',
                        'parent', 'hide',    )
    exclude = ('image', 'context', 'thumbnail', 'events', 'merged_with', 'url')
    list_filter = ('status','events','tags')
    list_editable = ['title',]
    list_select_related = True
    search_fields = ['title',]
    list_per_page = 5
    
    actions = [ approve, reject, pend, merge, retrieve_content ]
        
    def save_model(self, request, obj, form, change):
        """
        On save, should also updated the target of ``merged_with``.
        
        Updates:
        * Contexts
        * Tags
        """
        obj.save()
        if obj.merged_with is not None:
            'ok'
            for c in request.POST.getlist('context'):
                obj.merged_with.context.add(Context.objects.get(pk=int(c)))
        
            for t in request.POST.getlist('tags'):
                obj.merged_with.tags.add(Tag.objects.get(pk=int(t)))
            
            obj.merged_with.save()
            
    def queryset(self, request):
        """
        Filter the queryset to exclude hidden items.
        """

        qs = super(ItemAdmin, self).queryset(request)
        if request.path.split('/')[-2] == 'item':   # Only filter changelist.
            return qs.exclude(hide=True)
        return qs
        
    ## Custom fields...
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
    
    def type(self, obj, list=False):
        if hasattr(obj, 'audioitem'):   return 'Audio'
        elif hasattr(obj, 'videoitem'): return 'Video'
        elif hasattr(obj, 'textitem'):  return 'Text'
        elif hasattr(obj, 'imageitem'): return 'Image'
    
    def icon(self, obj, list=False):
        return self._format_type_icon(self.type(obj))

    def _format_type_icon(self, type):
        """
        Get an icon according to file type.
        """
        pattern = '<img src="{0}" height="{1}" />'
        if type == 'Audio':
            iconpath = '/media/static/audio-by-Hopstarter.png'
        if type == 'Video':
            iconpath = '/media/static/video-by-Hopstarter.png'
        return pattern.format(iconpath, 50)


    
    def _format_thumb(self, obj, thumb, list):
        pattern = '<a href="{0}"><img src="{1}"/></a>'
        if thumb is not None and thumb.image is not None:

            if list:
                fullsize_url = get_admin_url(obj)
            else:   
                if hasattr(obj, 'imageitem'):
                    if obj.imageitem.image is not None:
                        fullsize_url = get_admin_url(obj.imageitem.image)
                    else:
                        fullsize_url = '#'
                else:
                    fullsize_url = '#'
            return pattern.format(fullsize_url, thumb.image.url)
        if list:
            fullsize_url = get_admin_url(obj)
        else:
            fullsize_url = '#'
        return pattern.format(fullsize_url, '/media/static/file-by-Gurato.png')
        
    def _format_embed(self, videos):
        if len(videos) == 0:
            return None
            
        pattern = '<video width="320" height="240" controls>\n\t{0}\n</video>'
        spattern = '<source src="{0}" type="{1}" />'
        
        vformatted = []
        for video in videos:
            try:
                vformatted.append(spattern.format(video.video.url, video.mime))
            except ValueError:
                vformatted.append(spattern.format(video.url, ''))
        
        return pattern.format('\n'.join(vformatted))

    def _format_audio_embed(self, audios):
        if len(audios) == 0:
            return None
        pattern = '<audio controls>{0}</audio>'
        spattern = '<source src="{0}" type="{1}" />'

        aformatted = []
        for audio in audios:
            try:
                aformatted.append(spattern.format(audio.audio_file.url, audio.mime))
            except ValueError:
                aformatted.append(spattern.format(audio.url, ''))
        return pattern.format('\n'.join(aformatted))

    def item_image(self, obj, list=False):
        """
        Generates a thumbnail image element, with a link to the fullsize
        :class:`.Image`\.
        """

        try:    # If something went wrong when downloading a thumbnail, 
                #  this will raise a ValueError.
            if hasattr(obj, 'imageitem'):
                obj.imageitem.thumbnail.image.url
        except:# ValueError, AttributeError:
            return None

        if hasattr(obj, 'imageitem'):
            return self._format_thumb(obj, obj.imageitem.thumbnail, list)            
        elif hasattr(obj, 'audioitem'):
#            return self._format_thumb(obj, obj.audioitem.thumbnail, list)
            audios = obj.audioitem.audio_segments.all()
            return self._format_audio_embed(audios)
        elif hasattr(obj, 'videoitem'):
            videos = obj.videoitem.videos.all()
            icon = self._format_type_icon('video')

            return self._format_embed(videos)
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
    actions = (retrieve_context,)
    
    def queryset(self, request):
        """
        Only return Contexts for approved items in changelist.
        """
        
        if request.path.split('/')[-2] == 'context':   # Only filter changelist.
            return Context.objects.filter(items__status='AP')
        return super(ContextAdmin, self).queryset(request)
    
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
    
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}    

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
    actions = (retrieve_image,)

    def queryset(self, request):
        """
        Only return Images for approved items in changelist.
        """
        
        if request.path.split('/')[-2] == 'image':   # Only filter changelist.
            return Image.objects.filter(queryItems__status='AP')
        return super(ImageAdmin, self).queryset(request)

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
    
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}    
    
class GroupTaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'state')
    
class EngineAdmin(admin.ModelAdmin):
    readonly_fields = ['dayusage', 'monthusage']
    list_display = ['name', 'daily_usage', 'monthly_usage']
    
    def name(self, obj):
        return obj.__unicode__()
    
    def daily_usage(self, obj):
        if obj.daylimit is None:
            return 'Unlimited'
        else:
            return '{0}%'.format(100*float(obj.dayusage)/float(obj.daylimit))
    
    def monthly_usage(self, obj):
        if obj.monthlimit is None:
            return '{0} of unlimited'.format(obj.monthusage)
        else:
            return '{0}%'.format(100*float(obj.monthusage)/float(obj.monthlimit))    
            
            
    def get_form(self, request, obj=None, **kwargs):
        """
        manager should be readonly when editing.
        """

        readonly_fields = ['dayusage', 'monthusage']
        if obj is not None:
            self.readonly_fields = readonly_fields + ['manager']
            
        return super(EngineAdmin, self).get_form(request, obj, **kwargs)
        
class AudioAdmin(admin.ModelAdmin):
    list_display = ('audio_file_player',)
    actions = ['custom_delete_selected']

    def custom_delete_selected(self, request, queryset):
        n = queryset.count()
        for i in queryset:
            if i.audio_file:
                if os.path.exists(i.audio_file.path):
                    os.remove(i.audio_file.path)
            i.delete()
        self.message_user(request, _("Successfully deleted %d audio files.") % n)
    custom_delete_selected.short_description = "Delete selected items"

    def get_actions(self, request):
        actions = super(AudioFileAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions
        
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}        
        
class ThumbnailAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}
        
class VideoAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}
            
### Registration ###

admin.site.register(QueryEvent, QueryEventAdmin)
admin.site.register(QueryString, QueryStringAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Engine, EngineAdmin)
admin.site.register(Tag, TagAdmin)

admin.site.register(Context, ContextAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(Audio, AudioAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(Thumbnail, ThumbnailAdmin)
