from django import forms
from django.contrib import admin
from django.conf.urls import patterns, url
from django.http import HttpResponse
from django.shortcuts import render_to_response


import autocomplete_light
from models import *
from util import *
from tasks import *
from admin_actions import *
import uuid

from django.db.models.signals import pre_delete
from django.dispatch import receiver

import logging
logging.basicConfig(filename=None, format='%(asctime)-6s: %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

iconpath = "/media/static/"

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
        
    def clean(self):
        cleaned_data = super(QueryEventForm, self).clean()
        searchtype = cleaned_data.get("search_by")
        
        if searchtype == 'ST':
            querystring = cleaned_data.get("querystring")
            if querystring is None:
                raise forms.ValidationError(
                    'Must select a QueryString to perform a string query.'  )
        elif searchtype == 'UR':
            user = cleaned_data.get("user")
            if user is None:
                raise forms.ValidationError(
                    'Must select a User to perform a user query.'   )
        elif searchtype == 'TG':
            tag = cleaned_data.get("tag")
            if tag is None:
                raise forms.ValidationError(
                    'Must select a Tag to perform tag query.'   )

        return cleaned_data

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
        pattern = u'{0}-{1}'
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
            pattern = u'<a href="{0}?events__id__exact={1}">{2} items</a>'
            baseurl = '/'.join(get_admin_url(items[0]).split('/')[0:-2])
            
            return pattern.format(baseurl, obj.id, len(items))
        return None
    results.allow_tags = True
    

### ModelAdmins ###

class QueryStringAdmin(admin.ModelAdmin):
    list_display = ('querystring', 'events', 'last_used')#, 'items')
    inlines = (QueryEventInline,)
    
    def get_urls(self):
        urls = super(QueryStringAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^distribution/$', self.admin_site.admin_view(self.engine_matrix))
        )
        return my_urls + urls
        
    def engine_matrix(self, request):
        """
        should be able to see a matrix of querystrings versus engines.
        """
        
        querystrings = { q.id:q.querystring for q in QueryString.objects.all() }

        engines = { e.id:unicode(e) for e in Engine.objects.all() }

        values = { q:{ g:0 for g in engines.keys() } for q in querystrings.keys() }
        events = QueryEvent.objects.all()
        for e in events:
            items = Item.objects.filter(events__id=e.id).exclude(hide=True)
            q = e.querystring.id
            g = e.engine.id

            values[q][g] += len(items)
        
        pattern = "/admin/dolon/item/?events__engine__id__exact={0}&events__querystring__id__exact={1}"
        
        values_ = [ (querystrings[k], [ 
                          (pattern.format(g,k), vals[g], g, k ) for g in engines
                    ]) for k,vals in values.iteritems() ]
        
        context = {
            'title': 'Distribution of items across search terms and search engines',
            'values': values_,
            'engines': engines.values(),
            'iconpath': iconpath,
        }
        
        return render_to_response('querystring_matrix.html',context)
    
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
    
    fieldsets = (
            (None, {
                'fields': ('search_by','engine')
            }),
            ('Search by string', {
                'classes': ('collapse',),
                'fields': ('querystring', 'rangeStart', 'rangeEnd'),
            }),
            ('Search by user', {
                'classes': ('collapse',),
                'fields': ('user',),
            }),
            ('Search by tag', {
                'classes': ('collapse',),
                'fields': ('tag',),
            }),            
        )
    
    def result_sets(self, obj):
        """
        Generates a list of :class:`.QueryResult` instances associated with this
        :class:`.QueryEvent`\, with links to their respective admin change
        pages.
        """

        pattern = u'<a href="{0}">{1}, s:{2}, e:{3}</a>'
        R = [ pattern.format(get_admin_url(r), obj.querystring.querystring, 
                 r.rangeStart, r.rangeEnd) for r in obj.queryresults.all() ]

        return u'\n'.join(R)
    result_sets.allow_tags = True
    
    def results(self, obj):
        """
        Yields the number of :class:`.Item` associated with this 
        :class:`.QueryEvent`\, with a link to the filtered admin list view for
        :class:`.Item`\.
        """
            
        items = Item.objects.filter(events__id=obj.id).exclude(hide=True)
        if len(items) > 0:
            pattern = u'<a href="{0}?events__id__exact={1}">{2} items</a>'
            baseurl = u'/'.join(get_admin_url(items[0]).split('/')[0:-2])
            
            return pattern.format(baseurl, obj.id, len(items))
        return None
    results.allow_tags = True
    
    def range(self, obj):
        """
        Prettier representation of the start and end indices.
        """
    
        pattern = u'{0}-{1}'
        return pattern.format(obj.rangeStart, obj.rangeEnd)
    range.allow_tags = True
    
    def get_readonly_fields(self, request, obj=None):
        """
        All fields should be readonly after creation.
        """

        if obj:
            read_only = (   
                'querystring', 'datetime', 'engine', 'range', 'dispatched', 
                'results', 'search_status', 'creator', 'rangeStart', 
                'rangeEnd' ) + self.readonly_fields
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
            pass
        form = super(QueryEventAdmin, self).get_form(request, obj, **kwargs)
        
        # List for initial form values in GET request.
        if request.method == 'GET':
            for key in request.GET:
                try:
                    form.__dict__[key].initial = request.GET[key]
                except KeyError:    # Unexpected parameter; ignore.
                    pass

        return form
    
    def save_model(self, request, obj, form, change):
        
        if not hasattr(obj, 'creator'):
            obj.creator = request.user
        obj.save()

class ItemAdmin(admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(Item)
    list_display = ('icon', 'preview','title', 'status','retrieved', 'type' )
    readonly_fields = ( 'preview', 'contents', 'creator', 'resource',
                        'status', 'retrieved', 'type', 'query_events',
                        'contexts', 'creationDate',  'children', 'parent',  )
    exclude = ( 'image', 'thumbnail', 'events', 'merged_with', 'url',
                'hide', 'context'  )
    list_filter = ('status','events__querystring', 'events__engine', 'tags', 'type','events')
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
        
        pattern = u'<a href="{0}">{1}</a>'
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
        
        pattern = u'<li><a href="{0}">{1}</a></li>'
        
        html = u'<ul>'
        for c in obj.merged_from.all():
            html += pattern.format(get_admin_url(c), c.title)
        html += u'</ul>'
        return html
    children.allow_tags = True
    
    def preview(self, obj):
        """
        Generates a thumbnail, or player.
        """
        
        return self._item_image(obj, list=True)
    preview.allow_tags = True
    
    def resource(self, obj):
        """
        Generates a link to the original image URL, opening in a new tab.
        """

        pattern = u'<a href="{0}" target="_blank">{0}</a>'
        return pattern.format(obj.url)
    resource.allow_tags = True
    
    def contexts(self, obj):
        """
        Generates a list of associated :class:`.Context` instances, with links
        to their respective admin change pages.
        """

        pattern = u'<li><a href="{0}">{1}</a></li>'
        repr = u''.join([ pattern.format(get_admin_url(c),c.url) 
                            for c in obj.context.all() ])
        return u'<ul>{0}</ul>'.format(repr)
    contexts.allow_tags = True
    
    def icon(self, obj, list=False):
        """
        Display a media type icon.
        """
        
        return self._format_type_icon(obj.type)
    icon.allow_tags = True
    
    def contents(self, obj, list=False):
        """
        Display the content objects associated with an Item.
        """

        pattern = u'<a href="{0}">{1}</a>'

        if obj.type == 'Audio':
            formatted = []
            for seg in obj.audioitem.audio_segments.all():
                icon = self._format_mime_icon(seg.type(), 'audio')
                _url = get_admin_url(seg)
                formatted.append(pattern.format(_url, icon))

            return u''.join(formatted)
            
        elif obj.type == 'Video':
            formatted = []
            for vid in obj.videoitem.videos.all():
                icon = self._format_mime_icon(vid.type(), 'video')
                _url = get_admin_url(vid)
                formatted.append(pattern.format(_url, icon))
            return u''.join(formatted)
            
        elif obj.type == 'Image':
            formatted = []
            for img in obj.imageitem.images.all():
                icon = self._format_mime_icon(img.type(), 'image')
                _url = get_admin_url(img)
                formatted.append(pattern.format(_url, icon))
            return u''.join(formatted)        
        
        elif obj.type == 'Text':
            icon = self._format_mime_icon(obj.textitem.text.type(), 'text')
            _url = get_admin_url(obj.textitem.text)
            return pattern.format(_url, icon)
    contents.allow_tags = True

    def _format_mime_icon(self, mime, alt=None):
        """
        Get an icon according to mime type.
        """
        known_types = {
            'image/png':        '/media/static/png-by-Hopstarter.png',
            'image/jpeg':       '/media/static/jpeg-by-Hopstarter.png',
            'image/gif':        '/media/static/gif-by-Hopstarter.png',
            'image/tiff':       '/media/static/tiff-by-Hopstarter.png',
            'image/bmp':        '/media/static/bmp-by-Hopstarter.png',
            'audio/flac':       '/media/static/flac-by-Hopstarter.png',
            'audio/mpeg':       '/media/static/mp3-by-Hopstarter.png',
            'audio/wav':        '/media/static/wav-by-Hopstarter.png',
            'audio/aiff':       '/media/static/aiff-by-Hopstarter.png',
            'video/mpeg':       '/media/static/mpeg-by-Hopstarter.png',
            'video/avi':        '/media/static/avi-by-Hopstarter.png',
            'video/x-ms-wmv':   '/media/static/wmv-by-Hopstarter.png',
            'video/3gpp':       '/media/static/3gp-by-Hopstarter.png',
            'video/quicktime':  '/media/static/mov-by-Hopstarter.png',
        }
        
        alt_types = {
            'image':        '/media/static/jpeg-by-Hopstarter.png',
            'audio':        '/media/static/audio-by-Hopstarter.png',
            'video':        '/media/static/video-by-Hopstarter.png',
            'text':         '/media/static/text-by-Hopstarter.png',
        }
        
        pattern = u'<img src="{0}" height="{1}" />'
        if mime in known_types:
            icon_path = known_types[mime]
            return pattern.format(icon_path, 50)
        elif alt in alt_types:
            icon_path = alt_types[alt]
            return pattern.format(icon_path, 50)
        return None

    def _format_type_icon(self, type):
        """
        Get an icon according to file type.
        """
        pattern = u'<img src="{0}" height="{1}" />'
        if type == 'Audio':
            iconpath = u'/media/static/audio-by-Hopstarter.png'
        elif type == 'Video':
            iconpath = u'/media/static/video-by-Hopstarter.png'
        elif type == 'Image':
            iconpath = u'/media/static/jpeg-by-Hopstarter.png'
        elif type == 'Text':
            iconpath = u'/media/static/text-by-Hopstarter.png'
        else:
            return None
        return pattern.format(iconpath, 50)
    
    def _format_thumb(self, obj, thumb, list):
        pattern = u'<a href="{0}"><img src="{1}"/></a>'
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
        return pattern.format(fullsize_url, u'/media/static/file-by-Gurato.png')
        
    def _format_embed(self, videos):
        if len(videos) == 0:
            return None
            
        pattern = u'<video width="320" controls>\t{0}</video>'
        spattern = u'<source src="{0}" />'
        
        # Sort videos so that .MOV format is last.
        videos_ = []
        _mov = None
        for video in videos:
            if hasattr(video.video, 'url'): # May not have downloaded video
                _url = video.video.url       #  content yet.
            else:   
                _url = video.url
                
            fmt = _url.split('.')[-1].lower()   # Not using MIME type, since we 
            if fmt == 'mov':                    # may not have that at hand.
                _mov = _url
                continue    # Wait to add this video until the end.
            videos_.append(_url)
        if _mov is not None:    # Add the .MOV file, if there was one.
            videos_.append(_mov)
                    
        vformatted = []
        for _url in videos_:
            vformatted.append(spattern.format(_url))
        
        return pattern.format(u''.join(vformatted))

    def _format_audio_embed(self, audios):
        if len(audios) == 0:
            return None
        pattern = u'<audio controls>{0}</audio>'
        spattern = u'<source src="{0}" type="{1}" />'

        aformatted = []
        for audio in audios:
            try:
                aformatted.append(spattern.format(audio.audio_file.url, audio.mime))
            except ValueError:
                aformatted.append(spattern.format(audio.url, ''))
        return pattern.format(u'\n'.join(aformatted))

    def _item_image(self, obj, list=False):
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
            audios = obj.audioitem.audio_segments.all()
            return self._format_audio_embed(audios)
        elif hasattr(obj, 'videoitem'):
            videos = obj.videoitem.videos.all()
            icon = self._format_type_icon('video')

            return self._format_embed(videos)
    _item_image.allow_tags = True

    def query_events(self, obj):
        """
        Generates a list of :class:`QueryEvent` instances associated with this
        :class:`.Item`\, with links to their respective admin change pages.
        """

        pattern = u'<li><a href="{0}">{1}</a></li>'
            
        repr = u''.join([ pattern.format(get_admin_url(e), e) 
                        for e in obj.events.all() ])
        return u'<ul>{0}</ul>'.format(repr)
    query_events.allow_tags = True
    
class ContextAdmin(admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(Context)
    list_display = ('status', 'diffbot', 'url')
    list_display_links = ('status', 'url')
    readonly_fields = ( 'resource', 'title', 'diffbot', 'publicationDate', 
                        'author', 'language', 'text_content',  )
    exclude = ('url','diffbot_requests', 'content')
    actions = (retrieve_context,)
    
    def diffbot(self, obj):
        request = obj.diffbot_requests.all()[0]
        if request.completed is not None:
            return '<img src="/static/admin/img/icon-yes.gif" />'
        return '<img src="/static/admin/img/icon-no.gif" />'
    diffbot.allow_tags = True
    
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
        pattern = u'<a href="{0}" target="_blank">{0}</a>'
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
        pattern = u'<li><a href="{0}">{1}</a></li>'
        html = u''.join( [ pattern.format(get_admin_url(i),unidecode(i.title)) for i in obj.items() ] )
        return u'<ul>{0}</ul>'.format(html)
    items.allow_tags = True
    
    def contexts(self, obj):
        pattern = u'<li><a href="{0}">{1}</a></li>'
        for i in obj.contexts():
            print i
        html = u''.join( [ pattern.format(get_admin_url(i),i) for i in obj.contexts() ] )
        return u'<ul>{0}</ul>'.format(html)
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
        pattern = u'<a href="{0}" target="_blank">{0}</a>'
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
            pattern = u'<img src="{0}"/>'
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
            return u'Unlimited'
        else:
            return u'{0}%'.format(100*float(obj.dayusage)/float(obj.daylimit))
    
    def monthly_usage(self, obj):
        if obj.monthlimit is None:
            return u'{0} of unlimited'.format(obj.monthusage)
        else:
            return u'{0}%'.format(100*float(obj.monthusage)/float(obj.monthlimit))    
            
            
    def get_form(self, request, obj=None, **kwargs):
        """
        manager should be readonly when editing.
        """

        readonly_fields = ['dayusage', 'monthusage']
        if obj is not None:
            self.readonly_fields = readonly_fields + ['manager']
            
        return super(EngineAdmin, self).get_form(request, obj, **kwargs)
        
class AudioAdmin(admin.ModelAdmin):
    readonly_fields = ['preview', 'url', 'size', 'length', 'mime']
    exclude = ['audio_file']

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}

    def preview(self, obj, *args, **kwargs):
        return self._format_audio_embed(obj)
    preview.allow_tags = True

    def _format_audio_embed(self, audio):
        pattern = u'<audio controls>{0}</audio>'
        source = u'<source src="{0}" />'.format(audio.url)

        return pattern.format(source)


        
class ThumbnailAdmin(admin.ModelAdmin):
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}
        
class VideoAdmin(admin.ModelAdmin):
    readonly_fields = ['preview', 'url', 'size', 'length', 'mime']
    exclude = ['video']

    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}

    def preview(self, obj, *args, **kwargs):
        return self._format_embed(obj)
    preview.allow_tags = True

    def _format_embed(self, video):
            
        pattern = u'<video width="320" height="240" controls>{0}</video>'
        source = u'<source src="{0}" />'.format(video.url)#, video.type())
        return pattern.format(source)

class DiffBotRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'created', 'attempted', 'completed', 'type']
    actions = [performDiffBotRequest]

### Registration ###

admin.site.register(DiffBotRequest, DiffBotRequestAdmin)


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

