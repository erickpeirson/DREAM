# Django imports.
from django import forms
from django.contrib import admin
from django.conf.urls import patterns, url
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import autocomplete_light

# Dolon imports.
from models import *
from util import *
from tasks import *
from admin_actions import *
from oauth_managers import TwitterOAuthManager, FacebookOAuthManager
from dream import settings

# General imports.
from datetime import datetime
import uuid

# Logging.
import logging
logging.basicConfig(filename=None, format=settings.LOGGING_FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

iconpath = "/media/static/"     # TODO: this should be in settings.py

### Receivers ###

@receiver(pre_delete, sender=Item)
def itemDeleteReceiver(sender, **kwargs):
    """
    Handles deletion of :class:`.Item` objects. 
    
    If an :class:`.Item` is comprised of multiple merged :class:`.Item` objects, 
    then those will be unhidden before the parent :class:`.Item` is deleted.
    """
    
    obj = kwargs.get('instance')
    if obj.merged_from is not None:
        for i in obj.merged_from.all():
            i.hide = False
            i.save()
# end itemDeleteReceiver

### Forms ###

class QueryEventForm(forms.ModelForm):
    """
    Custom :class:`django.forms.ModelForm` for :class:`.QueryEvent` objects.
    """
    
    def __init__(self, *args, **kwargs):
        super(QueryEventForm, self).__init__(*args, **kwargs)
        
        try:    # Limit QueryStrings to those not hidden.
            not_hidden = QueryString.objects.filter(hidden=False)
            self.fields['querystring'].queryset = not_hidden
        except KeyError:    # In case we exclude this field in certain cases.
            pass
        
    class Meta:
        model = QueryEvent
    # end QueryEventForm.Meta class

    def clean_creator(self):
        if not self.cleaned_data['creator']:
            return User()
        return self.cleaned_data['creator']
    # end QueryEventForm.clean_creator

    def clean(self):
        """
        Enforces field requirements based on search type.
        
        For example, if searchtype is 'ST' (by string), then a 
        :class:`.QueryString` must be selected in the ``querystring`` field.
        """
        
        cleaned_data = super(QueryEventForm, self).clean()
        searchtype = cleaned_data.get("search_by")

        # String search: 'querystring' is required.
        if searchtype == 'ST':
            querystring = cleaned_data.get("querystring")
            if querystring is None:
                raise forms.ValidationError(
                    'Must select a QueryString to perform a string query.'  )
        # User search:  'user' is required.
        elif searchtype == 'UR':
            user = cleaned_data.get("user")
            if user is None:
                raise forms.ValidationError(
                    'Must select a User to perform a user query.'   )
        # Tag search:   'tag' is required.
        elif searchtype == 'TG':
            tag = cleaned_data.get("tag")
            if tag is None:
                raise forms.ValidationError(
                    'Must select a Tag to perform tag query.'   )
        return cleaned_data
    # end QueryEventForm.clean
# end QueryEventForm class

### Inlines ###

class QueryEventInline(admin.TabularInline):
    """
    Provides inline access to :class:`.QueryEvent` from the 
    :class:`.QueryString` change view.
    """
    model = QueryEvent
    readonly_fields = ( 'dispatched', 'range', 'engine', 'datetime', 'results' )
    exclude = ( 'rangeStart', 'rangeEnd', 'search_task', 'thumbnail_tasks', 
                'queryresults'  )
    ordering = ('datetime',)

    extra = 0
    
    def has_delete_permission(self, request, obj=None):
        """
        Prevents :class:`.QueryEvent` objects from being deleted via this
        inline form.
        """
        
        return False
    # end QueryEventInline.has_delete_permission

    def range(self, obj):
        """
        Provides a prettier representation of the start and end indices.
        """
        
        pattern = u'{0}-{1}'
        return pattern.format(obj.rangeStart, obj.rangeEnd)
    range.allow_tags = True
    # end QueryEventInline.range

    def results(self, obj):
        """
        Yields an HTML anchor to the :class:`.Item` list view filtered by the
        :class:`.QueryEvent` ``obj``. 
        
        Anchor text is the number of :class:`.Item` associated with this
        :class:`.QueryEvent`\.
        
        Parameters
        ----------
        obj : :class:`.QueryEvent`
        
        Returns
        -------
        str : HTML anchor tag.
        
        """

        items = Item.objects.filter(events__id=obj.id)
        if len(items) > 0:
            pattern = u'<a href="{0}?events__id__exact={1}">{2} items</a>'
            baseurl = '/'.join(get_admin_url(items[0]).split('/')[0:-2])

            return pattern.format(baseurl, obj.id, len(items))
        return None
    results.allow_tags = True
    # end QueryEventInline.results
# end QueryEventInline class

### ModelAdmins ###

class QueryStringAdmin(admin.ModelAdmin):
    """
    :class:`.ModelAdmin` for :class:`.QueryString`\.
    """
    
    list_display = ('querystring', 'events', 'last_used')#, 'items')
    inlines = (QueryEventInline,)

    def get_urls(self):
        """
        URLs for custom admin views onto :class:`.QueryString`\.
        """
        
        urls = super(QueryStringAdmin, self).get_urls()
        my_urls = patterns('',
            (r'^distribution/$', self.admin_site.admin_view(self.engine_matrix))
        )
        return my_urls + urls
    # end QueryStringAdmin.get_urls

    def engine_matrix(self, request):
        """
        Displays the number of :class:`.Item`\s retrieved for each 
        :class:`.QueryString` across each :class:`.Engine`\s. Searches by string
        only.
        """

        # Retrieve only non-hidden QueryStrings.
        querystrings = { q.id:q.querystring for q
                            in QueryString.objects.filter(hidden=False) }

        # Retrieve only non-hidden Engines.
        engines = { e.id:unicode(e) for e
                            in Engine.objects.filter(hidden=False) }
        
        # Create a counter for the QueryString x Engine matrix.
        values = { q:{ g:0 for g in engines.keys() } 
                            for q in querystrings.keys() }
        
        # Retrieve all non-hidden QueryEvents.
        events = QueryEvent.objects.filter(hidden=False)
        for e in events:
            if e.search_by == 'ST': # Consider only string searches.
                # Get non-hidden Items associated with this QueryEvent.
                items = Item.objects.filter(events__id=e.id).exclude(hide=True)
                
                # Get indices into the matrix.
                q = e.querystring.id
                g = e.engine.id
                
                # Count the number of Items in this cell.
                values[q][g] += len(items)

        # Now generate context values for the template. Each cell should get a
        #  4-tuple containing:
        #   - A URL for the filtered Item changelist,
        #   - A cell value (number of Items),
        #   - An Engine ID, and
        #   - A QueryString ID.
        #
        values_ = []
        for k, vals in values.iteritems():
            for g in engines:
                url = reverse(  "admin:dolon_item_changelist",
                                kwargs={
                                    'events__engine__id__exact': g,
                                     'events__querystring__id__exact': k
                                }   )
                values_.append((url, vals[g], g, k))

        context = {
            'title': 'Items across search terms and engines',
            'values': values_,
            'engines': engines.values(),    # Engine names.
            'iconpath': iconpath,
        }

        return render_to_response('querystring_matrix.html', context)
    # end QueryStringAdmin.engine_matrix

    def last_used(self, obj):
        """
        Returns the prettified date on which a :class:`.QueryString` was last
        used in a :class:`.QueryEvent`\.
        
        Parameters
        ----------
        obj : :class:`.QueryString`
        
        Returns
        -------
        str : Prettified date of last use.
        """
        
        return pretty_date(obj.latest())
    # end QueryStringAdmin.last_used

    def get_readonly_fields(self, request, obj=None):
        """
        Ensures that the ``querystring`` attribute is only editable upon 
        creation of the :class:`.QueryString`\.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.QueryString`
        
        Returns
        -------
        readonly_fields : list
        """

        if obj:
            return ('querystring',) + self.readonly_fields
        return self.readonly_fields
    # end QueryStringAdmin.get_readonly_fields

    def get_inline_instances(self, request, obj=None):
        """
        Ensures that the :class:`.QueryEventInline` is only displayed on the
        :class:`.QueryString`\s edit view (not the add view).
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.QueryString`
        
        Returns
        -------
        inlines : list
            If not edit view, empty.
        """

        if not obj:     # Edit view should execute the default method.
            return []
        return super(QueryStringAdmin, self).get_inline_instances(request, obj)
    # end QueryStringAdmin.get_inline_instances
    
    def queryset(self, request):
        """
        Removes any hidden :class:`.QueryString`\s from the list display.

        Parameters
        ----------
        request : :class:`django.http.HttpRequest`

        Returns
        -------
        queryset : :class:`django.db.models.query.QuerySet`
        
        """
        
        qs = super(QueryStringAdmin, self).queryset(request)
        return qs.filter(hidden=False)    
# end QueryStringAdmin class

class QueryEventAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.QueryEvent`\.
    """
    form = QueryEventForm   # Uses a custom ModelForm.

    list_display = (    'id', 'query', 'engine', 'created', 'range',
                        'dispatched', 'search_status', 'results'    )
    list_display_links = (  'query',    )
    list_filter = ( 'engine',   )
    actions = ( dispatch, reset )

    # Break the add/edit view up into fieldsets based on search type.
    fieldsets = (
            (None, {
                'fields': ('search_by','engine', 'hidden')
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

    def query(self, obj):
        """
        Generates a string representation of the :class:`.QueryEvent` based on
        search type and search parameter.
        
        Parameters
        ----------
        obj : :class:`.QueryEvent`
        
        Returns
        -------
        query : str
        """
        if obj.search_by == 'ST':   # String search.
            param = obj.querystring.querystring
            method = 'String'
        elif obj.search_by == 'UR': # User search.
            param = '{0} ({1})'.format(obj.user.handle, obj.user.platform.name)
            method = 'User'
        elif obj.search_by == 'TG': # Tag search.
            param = obj.tag.string
            method = 'Tag'
        query = '{0}: {1}'.format(method, param)
        return query
    # end QueryEventAdmin.query

    def created(self, obj):
        return obj.datetime
    # end QueryEventAdmin.created

    def result_sets(self, obj):
        """
        Generates a list of :class:`.QueryResult` instances associated with this
        :class:`.QueryEvent`\, with links to their respective admin change
        pages.
        
        Parameters
        ----------
        obj : :class:`.QueryEvent`
        
        Returns
        -------
        html : str
            Linebreak-delimited list of anchor tags.
        """

        pattern = u'<a href="{0}">{1}, s:{2}, e:{3}</a>'
        R = [ pattern.format(get_admin_url(r), obj.querystring.querystring,
                 r.rangeStart, r.rangeEnd) for r in obj.queryresults.all() ]

        return u'\n'.join(R)
    result_sets.allow_tags = True
    # end QueryEventAdmin.result_sets

    def results(self, obj):
        """
        Yields the number of :class:`.Item` associated with this
        :class:`.QueryEvent`\, with a link to the filtered admin list view for
        :class:`.Item`\.
        
        Parameters
        ----------
        obj : :class:`.QueryEvent`
        
        Returns
        -------
        html : str
            Anchor tag pointing to :class:`.Item` change list.
        """

        # Ignore hidden items.
        items = Item.objects.filter(events__id=obj.id).exclude(hide=True)
        if len(items) > 0:
            pattern = u'<a href="{0}?events__id__exact={1}">{2} items</a>'
            baseurl = u'/'.join(get_admin_url(items[0]).split('/')[0:-2])

            return pattern.format(baseurl, obj.id, len(items))
        return None
    results.allow_tags = True
    # end QueryEventAdmin.results

    def range(self, obj):
        """
        Prettier representation of the start and end indices.

        Parameters
        ----------
        obj : :class:`.QueryEvent`
        
        Return
        ------
        range : str
        """

        pattern = u'{0}-{1}'
        return pattern.format(obj.rangeStart, obj.rangeEnd)
    range.allow_tags = True
    # end QueryEventAdmin.range

    def get_readonly_fields(self, request, obj=None):
        """
        Ensures that all fields are read-only after creation.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.QueryEvent` or None
        
        Returns
        -------
        readonly_fields : list
        """

        if obj:
            read_only = (
                'querystring', 'datetime', 'engine', 'range', 'dispatched',
                'results', 'search_status', 'creator', 'rangeStart',
                'rangeEnd' ) + self.readonly_fields
            return read_only
        return self.readonly_fields
    # end QueryEventAdmin.get_readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Customizes field exclusion, and pre-populates form based on GET 
        parameters.
        
        TODO: Make sure that this is not a security liability.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.QueryEvent` or None
        kwargs        
        
        Returns
        -------
        form : :class:`django.forms.ModelForm`
        """

        exclude = [ 'search_task', 'thumbnail_tasks', 'queryresults', 'state' ]
        if obj is None:
            self.exclude = exclude + [ 'dispatched', 'creator' ]
        else:
            pass

        form = super(QueryEventAdmin, self).get_form(request, obj, **kwargs)

        # Sometimes there will be initial form values in the GET params.
        if request.method == 'GET':
            # Apply initial form values from GET request.
            for key in request.GET:
                try:
                    form.__dict__[key].initial = request.GET[key]
                except KeyError:    # Unexpected parameter; ignore.
                    pass

        return form
    # end QueryEventAdmin.get_form

    def save_model(self, request, obj, form, change):
        """
        Adds the creating :class:`django.contrib.auth.User` to the
        :class:`.QueryEvent` upon saving.

        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.QueryEvent` or None
        form : :class:`django.forms.ModelForm`
        change : boolean
        
        Returns
        -------
        None
        """
        
        if not hasattr(obj, 'creator'):
            obj.creator = request.user
        obj.save()
    # end QueryEventAdmin.save_model
    
    def queryset(self, request):
        """
        Removes any hidden :class:`.QueryEvent`\s from the list display.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        
        Returns
        -------
        queryset : :class:`django.db.models.query.QuerySet`
        """
        
        qs = super(QueryEventAdmin, self).queryset(request)
        return qs.filter(hidden=False)
# end QueryEventAdmin class

class QueryStringListFilter(admin.SimpleListFilter):
    """
    Primarily used to hide 'hidden' QueryStrings from the filter options.
    """
    
    title = _('search string')
    
    parameter_name = 'search_string'
    
    def lookups(self, request, model_admin):
        """
        Excludes hidden :class:`.QueryString`\s from list of filter options.

        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        model_admin : :class:`django.contrib.admin.ModelAdmin`
        
        Returns
        -------
        options : tuple
        """
        
        querystrings = QueryString.objects.filter(hidden=False)
        options = ( (q.id, q.querystring) for q in querystrings )
        return options
        
    def queryset(self, request, queryset):
        """
        Filters by :class:`.QueryString` ID, if a filter option is selected.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        queryset : :class:`django.db.models.query.QuerySet`
        
        Returns
        -------
        queryset : :class:`django.db.models.query.QuerySet`
        """
        
        if self.value() is None:
            return queryset
        return queryset.filter(events__querystring__id=self.value())
# end QueryStringListFilter class

class QueryEventListFilter(admin.SimpleListFilter):
    """
    Primarily used to hide 'hidden' QueryEvents from the filter options.
    """
    
    title = _('search event')
    parameter_name = 'search_event'
    
    def lookups(self, request, model_admin):
        """
        Excludes hidden :class:`.QueryEvent`\s from list of filter options.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        model_admin : :class:`django.contrib.admin.ModelAdmin`
        
        Returns
        -------
        options : tuple
        """
        
        queryevents = QueryEvent.objects.filter(hidden=False)
        options = ( (qe.id, qe.__unicode__()) for qe in queryevents )
        return options
        
    def queryset(self, request, queryset):
        """
        Filters by :class:`.QueryEvent` ID, if a filter option is selected.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        queryset : :class:`django.db.models.query.QuerySet`
        
        Returns
        -------
        queryset : :class:`django.db.models.query.QuerySet`
        """
        
        if self.value() is None:
            return queryset
        return queryset.filter(events__id=self.value())
# end QueryEventListFilter class

class ItemAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.Item`\.
    """
    
    # Use autocomplete_light for autocomplete on tag field.
    form = autocomplete_light.modelform_factory(Item)
    
    list_display = (    'icon', 'list_preview','title', 'status','retrieved',
                        'type'  )
    readonly_fields = ( 'item_preview', 'contents', 'creator', 'resource',
                        'status', 'retrieved', 'type', 'query_events',
                        'contexts', 'creationDate',  'children', 'parent',  )
    exclude = ( 'image', 'thumbnail', 'events', 'merged_with', 'url',
                'hide', 'context'  )
    list_filter = ( 'status', QueryStringListFilter, 'events__engine', 'tags',
                    'type', QueryEventListFilter    )
                    
    list_editable = ('title',)
    list_select_related = True
    search_fields = ('title',)
    list_per_page = 5

    actions = ( approve, reject, pend, merge, retrieve_content )

    def save_model(self, request, obj, form, change):
        """
        On save, should also updated the target of ``merged_with``.

        Passes "upward" the :class:`.Context`\s and :class:`.Tag`\s of the child
        :class:`.Item`\s.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.Item`
        form : :class:`django.forms.ModelForm`
        change : boolean
        
        Returns
        -------
        None
        """
        
        obj.save()  # Save first.

        # Do nothing for non-merged Items.
        if obj.merged_with is not None:

            # Pass Contexts to parent.
            for c in request.POST.getlist('context'):
                obj.merged_with.context.add(Context.objects.get(pk=int(c)))

            # Pass Tags to parent.
            for t in request.POST.getlist('tags'):
                obj.merged_with.tags.add(Tag.objects.get(pk=int(t)))

            # Save the parent.
            obj.merged_with.save()
    # end ItemAdmin.save_model

    def queryset(self, request):
        """
        Filter the queryset to exclude hidden items.

        Parameters
        ----------
        request : :class:`django.http.HttpRequest`

        Returns
        -------
        queryset : :class:`django.db.models.query.QuerySet`
        """

        qs = super(ItemAdmin, self).queryset(request)
        if request.path.split('/')[-2] == 'item':   # Only filter changelist.
            return qs.exclude(hide=True)
        return qs
    # end ItemAdmin.queryset

    ## Custom fields...
    def parent(self, obj):
        """
        Display the item into which this item has been merged.
        
        Parameters
        ----------
        obj : :class:`.Item`
        
        Returns
        -------
        html : str
            Anchor pointing to parent :class:`.Item`\.
        """

        pattern = u'<a href="{0}">{1}</a>'
        if obj.merged_with is not None:
            href = get_admin_url(obj.merged_with)
            title = obj.merged_with.title
            return pattern.format(href, title)
        return None
    parent.allow_tags = True
    # end ItemAdmin.parent

    def children(self, obj):
        """
        Display merged items from whence this item originated.

        Parameters
        ----------
        obj : :class:`.Item`
        
        Returns
        -------
        html : str
            Anchor pointing to children :class:`.Item`\s.
        """

        pattern = u'<li><a href="{0}">{1}</a></li>'

        html = u'<ul>'
        for c in obj.merged_from.all():
            html += pattern.format(get_admin_url(c), c.title)
        html += u'</ul>'
        return html
    children.allow_tags = True
    # end ItemAdmin.children

    def list_preview(self, obj, **kwargs):
        """
        Generate a preview for display in the changelist view.
        
        Parameters
        ----------
        obj : :class:`.Item`
        **kwargs
        
        Returns
        -------
        html : str
        """

        return self._item_image(obj, True)
    list_preview.allow_tags = True
    # end ItemAdmin.list_preview

    def item_preview(self, obj, **kwargs):
        """
        Generate a preview for display in the add/edit views.
        
        Parameters
        ----------
        obj : :class:`.Item`
        **kwargs
        
        Returns
        -------
        html : str
        """
        return self._item_image(obj, False)
    item_preview.allow_tags = True
    # end ItemAdmin.item_preview

    def resource(self, obj):
        """
        Generates a link to the original (external) image URL, opening in a new
        tab.
        
        Parameters
        ----------
        obj : :class:`.Item`
        
        Returns
        -------
        html : str
        """

        pattern = u'<a href="{0}" target="_blank">{0}</a>'
        return pattern.format(obj.url)
    resource.allow_tags = True
    # end ItemAdmin.resource

    def contexts(self, obj):
        """
        Generates a list of associated :class:`.Context` instances, with links
        to their respective admin change pages.
        
        Parameters
        ----------
        obj : :class:`.Item`
        
        Returns
        -------
        html : str
            Unordered list.
        """

        pattern = u'<li><a href="{0}">{1}</a></li>'
        repr = u''.join([ pattern.format(get_admin_url(c),c.url)
                            for c in obj.context.all() ])
        return u'<ul>{0}</ul>'.format(repr)
    contexts.allow_tags = True
    # end ItemAdmin.contexts

    def icon(self, obj, list=False):
        """
        Generates an icon based on media type.
        
        Parameters
        ----------
        obj : :class:`.Item`
        list : boolean
        
        Returns
        -------
        html : str
        """

        return self._format_type_icon(obj.type)
    icon.allow_tags = True
    # end ItemAdmin.icon

    def contents(self, obj, list=True):
        """
        Generates a list of content objects associated with an :class:`.Item`\.

        Parameters
        ----------
        obj : :class:`.Item`
        list : boolean
        
        Returns
        -------
        html : str
            Media type-based icons, in anchors pointing to content objects.
        """

        logger.debug(obj.type)
        logger.debug(obj.type == 'Text')

        pattern = u'<a href="{0}">{1}</a>'

        if obj.type == 'Audio':
            logger.debug('Display contents of AudioItem.')
            formatted = []
            for seg in obj.audioitem.audio_segments.all():
                icon = self._format_mime_icon(seg.type(), 'audio')
                _url = get_admin_url(seg)
                formatted.append(pattern.format(_url, icon))

            return u''.join(formatted)
        elif obj.type == 'Video':
            logger.debug('Display contents of VideoItem.')
            formatted = []
            for vid in obj.videoitem.videos.all():
                icon = self._format_mime_icon(vid.type(), 'video')
                _url = get_admin_url(vid)
                formatted.append(pattern.format(_url, icon))
            return u''.join(formatted)

        elif obj.type == 'Image':
            logger.debug('Display contents of ImageItem.')
            formatted = []
            for img in obj.imageitem.images.all():
                icon = self._format_mime_icon(img.type(), 'image')
                _url = get_admin_url(img)
                formatted.append(pattern.format(_url, icon))
            return u''.join(formatted)
        elif obj.type == 'Text':
            logger.debug('Display contents of TextItem.')
            formatted = []
            for txt in obj.textitem.original_files.all():
                icon = self._format_mime_icon(txt.mime, 'text')
                _url = get_admin_url(txt)
                formatted.append(pattern.format(_url, icon))
            return u''.join(formatted)
    contents.allow_tags = True
    # end ItemAdmin.contents

    def _format_mime_icon(self, mime, alt=None):
        """
        Generates an icon according to mime type.
        
        TODO: Is there a better way to define icons? A config file somewhere?
        
        Parameters
        ----------
        mime : str
            MIME type.
        alt : str
            Type ('image', 'audio', 'video', 'text') to use if an icon can't be
            located for the MIME type ``mime``.
            
        Returns
        -------
        html : str
        """
        known_types = {
            'image/png':        '/dolon/media/static/png-by-Hopstarter.png',
            'image/jpeg':       '/dolon/media/static/jpeg-by-Hopstarter.png',
            'image/gif':        '/dolon/media/static/gif-by-Hopstarter.png',
            'image/tiff':       '/dolon/media/static/tiff-by-Hopstarter.png',
            'image/bmp':        '/dolon/media/static/bmp-by-Hopstarter.png',
            'audio/flac':       '/dolon/media/static/flac-by-Hopstarter.png',
            'audio/mpeg':       '/dolon/media/static/mp3-by-Hopstarter.png',
            'audio/wav':        '/dolon/media/static/wav-by-Hopstarter.png',
            'audio/aiff':       '/dolon/media/static/aiff-by-Hopstarter.png',
            'video/mpeg':       '/dolon/media/static/mpeg-by-Hopstarter.png',
            'video/avi':        '/dolon/media/static/avi-by-Hopstarter.png',
            'video/x-ms-wmv':   '/dolon/media/static/wmv-by-Hopstarter.png',
            'video/3gpp':       '/dolon/media/static/3gp-by-Hopstarter.png',
            'video/quicktime':  '/dolon/media/static/mov-by-Hopstarter.png',
        }

        alt_types = {
            'image':        '/dolon/media/static/jpeg-by-Hopstarter.png',
            'audio':        '/dolon/media/static/audio-by-Hopstarter.png',
            'video':        '/dolon/media/static/video-by-Hopstarter.png',
            'text':         '/dolon/media/static/text-by-Hopstarter.png',
        }

        pattern = u'<img src="{0}" height="{1}" />'
        if mime in known_types:
            icon_path = known_types[mime]
            return pattern.format(icon_path, 50)
        elif alt in alt_types:
            icon_path = alt_types[alt]
            return pattern.format(icon_path, 50)
        return None
    # end ItemAdmin._format_mime_icon

    def _format_type_icon(self, type):
        """
        Generates an icon according to file type.
        
        TODO: Find a better way to define icons for each type. Config file?
        
        Parameters
        ----------
        type : str
            ('image', 'audio', 'video', 'text')
            
        Returns
        -------
        html : str
        """
        
        type = type.lower() # In case a capitalized type is used.
        
        pattern = u'<img src="{0}" height="{1}" />'
        if type == 'audio':
            iconpath = u'/dolon/media/static/audio-by-Hopstarter.png'
        elif type == 'video':
            iconpath = u'/dolon/media/static/video-by-Hopstarter.png'
        elif type == 'image':
            iconpath = u'/dolon/media/static/jpeg-by-Hopstarter.png'
        elif type == 'text':
            iconpath = u'/dolon/media/static/text-by-Hopstarter.png'
        else:
            return None
        return pattern.format(iconpath, 50)
    # end ItemAdmin._format_type_icon

    def _format_thumb(self, obj, thumb, list):
        """
        Generate a thumbnail image for display in the changelist and add/edit
        views.
        
        Parameters
        ----------
        obj : :class:`.Item`
        thumb : :class:`.Thumbnail`
        list : boolean
        
        Returns
        -------
        html : str
        """
        pattern = u'<a href="{0}"><img src="{1}" class="thumbnail" /></a>'

        # In the list view, the thumbnail shoud link to the Item change view.
        if list:  fullsize_url = get_admin_url(obj)
        else:     fullsize_url = '#'

        # Sometimes a Thumbnail image is not downloaded (for whatever reason). 
        #  In that case, thumb.image.name should be blank (u'')...
        if thumb is not None and thumb.image.name != u'':
            thumb_url = thumb.image.url
        
        # ...and we will use a generic file icon instead.
        else:        # TODO: change the way that this URL gets generated.
            thumb_url = u'/dolon/media/static/file-by-Gurato.png'

        return pattern.format(fullsize_url, thumb_url)
    # end ItemAdmin._format_thumb

    def _format_embed(self, videos):
        """
        Generate an embedded video player for display in the changelist and
        add/edit views.
        
        Parameters
        ----------
        videos : list
            A list of :class:`.Video`\s.
            
        Returns
        -------
        html : str
        """
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
    # end ItemAdmin._format_embed

    def _format_audio_embed(self, audios):
        """
        Generate an embedded audio player for display in the changelist and
        add/edit views.
        
        Parameters
        ----------
        audios : list
            A list of :class:`.Audio`\s.
            
        Returns
        -------
        html : str
        """
        if len(audios) == 0:
            return 'No audio file available.'
        pattern = u'<audio controls>{0}</audio>'
        spattern = u'<source src="{0}" type="{1}" />'

        aformatted = []
        for audio in audios:
            try:
                aformatted.append(spattern.format(audio.audio_file.url, audio.mime))
            except ValueError:
                aformatted.append(spattern.format(audio.url, ''))
        return pattern.format(u'\n'.join(aformatted))
    # end ItemAdmin._format_audio_embed

    def _item_image(self, obj, list=False):
        """
        Generates a preview for the :class:`.Item` ``obj``, with a link to the 
        full content (e.g. an :class:`.Image` object).
        
        Parameters
        ----------
        obj : :class:`.Item`
        lsit : boolean
        
        Returns
        -------
        html : str or None
        """

#        try:    # If something went wrong when downloading a thumbnail,
#                #  this will raise a ValueError.
#            if hasattr(obj, 'imageitem'):
#                obj.imageitem.thumbnail.image.url
#        except:# ValueError, AttributeError:
#            return None

        # Determine which subclass of :class:`.Item` obj is an instance of,
        #  and generate a preview accordingly.
        
        if hasattr(obj, 'imageitem'):   # obj is an ImageItem.
            return self._format_thumb(obj, obj.imageitem.thumbnail, list)
        
        elif hasattr(obj, 'audioitem'): # obj is an AudioItem.
            audios = obj.audioitem.audio_segments.all()
            return self._format_audio_embed(audios)
        
        elif hasattr(obj, 'videoitem'): # obj is a VideoItem.
            videos = obj.videoitem.videos.all()
            icon = self._format_type_icon('video')
            return self._format_embed(videos)
        
        elif hasattr(obj, 'textitem'):  # obj is a TextItem.
            if obj.textitem.snippet is not None:
            
                # For changelist, only show the first 50 characters.
                if list:
                    return obj.textitem.snippet[0:50]

            # Returns even if None.
            return obj.textitem.snippet

        return None     # ...just in case there are other subclasses.
    _item_image.allow_tags = True
    # end ItemAdmin._item_image

    def query_events(self, obj):
        """
        Generates a list of :class:`QueryEvent` instances associated with this
        :class:`.Item`\, with links to their respective admin change pages.
        
        Parameters
        ----------
        obj : :class:`.Item`
        
        Returns
        -------
        html : str
        """

        pattern = u'<li><a href="{0}">{1}</a></li>'

        repr = u''.join([ pattern.format(get_admin_url(e), e)
                        for e in obj.events.all() ])
        return u'<ul>{0}</ul>'.format(repr)
    query_events.allow_tags = True
    # end ItemAdmin.query_events
# end ItemAdmin class

class HiddenAdmin(admin.ModelAdmin):
    """
    Subclasses of the :class:`.HiddenAdmin` will not be visible in the list of
    admin changelist views, but individual objects will be accessible directly.
    """
    
    def get_model_perms(self, request):
        """
        Return empty perms dict thus hiding the model from admin index.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        
        Returns
        -------
        perms : dict
            An empty dict.
        """
        
        return {}
    # end HiddenAdmin.get_model_perms
# end HiddenAdmin class

class ContextAdmin(HiddenAdmin):
    """
    ModelAdmin for :class:`.Context`\.
    """
    
    # Provide autocomplete for tags.
    form = autocomplete_light.modelform_factory(Context)
    
    list_display = (    'status', 'diffbot', 'url'  )
    list_display_links = (  'status', 'url' )
    readonly_fields = ( 'resource', 'title', 'retrieved', 'diffbot',
                        'use_diffbot', 'publicationDate', 'author', 'language',
                        'text_content',  )
    exclude = ( 'url', 'diffbot_requests', 'content'    )
    actions = ( retrieve_context,   )

    def diffbot(self, obj):
        """
        Provides a boolean-like widget for the ``use_diffbot`` field.
        
        Parameters
        ----------
        obj : :class:`.Context`
        
        Returns
        -------
        diffbot : boolean
        """
        try:
            request = obj.diffbot_requests.all()[0]
            if request.completed is not None:
                return True
            return False
        except IndexError:
            return False
    diffbot.boolean = True
    # end ContextAdmin.diffbot

    def queryset(self, request):
        """
        Only return :class:`.Context`\s for approved items in changelist.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`

        Returns
        -------
        queryset : :class:`django.db.models.query.QuerySet`
        """

        if request.path.split('/')[-2] == 'context':   # Only filter changelist.
            return Context.objects.filter(items__status='AP')
        return super(ContextAdmin, self).queryset(request)
    # end ContextAdmin.queryset

    def resource(self, obj):
        """
        Generates a link to the original (external) context URL, opening in a 
        new tab.
                
        Parameters
        ----------
        obj : :class:`.Context`
        
        Returns
        -------
        html : str
        """
        pattern = u'<a href="{0}" target="_blank">{0}</a>'
        return pattern.format(obj.url)
    resource.allow_tags = True
    # end ContextAdmin.resource

    def status(self, obj):
        """
        Returns True if data for this :class:`.Context` has been retrieved.
        
        Parameters
        ----------
        obj : :class:`.Context`
        
        Returns
        -------
        status : boolean
        """
        if obj.title is None and obj.content is None:
            return False
        return True
    status.boolean = True
    # end ContextAdmin.status
# end ContextAdmin class

class TagAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.Tag`\.
    """
#    readonly_fields = ('text', 'items', 'contexts')
    list_display = (    'text', 'items', 'contexts' )
    search_fields = (   'text', )

    def items(self, obj):
        """
        Generates a list of :class:`.Item`\s to which this Tag has been applied.
        
        Parameters
        ----------
        obj : :class:`.Tag`
        
        Returns
        -------
        html : str
        """

        pattern = u'<li><a href="{0}">{1}</a></li>'
        hdata = [ pattern.format(get_admin_url(i),unidecode(i.title))
                    for i in obj.items() ]
        return u'<ul>{0}</ul>'.format(u''.join( hdata ))
    items.allow_tags = True
    # end TagAdmin.items

    def contexts(self, obj):
        """
        Generates a list of :class:`.Context`\s to which this Tag has been 
        applied.
        
        Parameters
        ----------
        obj : :class:`.Tag`
        
        Returns
        -------
        html : str
        """
        pattern = u'<li><a href="{0}">{1}</a></li>'

        hdata = [ pattern.format(get_admin_url(i),i) for i in obj.contexts() ]
        return u'<ul>{0}</ul>'.format(u''.join( hdata ))
    contexts.allow_tags = True
    # end TagAdmin.contexts

    def get_readonly_fields(self, request, obj=None):
        """
        Ensures that ``text``, ``items``, and ``contexts`` are readonly on the
        edit view.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.Tag` or None
        
        Returns
        -------
        html : str
        """

        if obj:
            read_only = ('text', 'items', 'contexts') + self.readonly_fields
            return read_only
        return self.readonly_fields
    # end TagAdmin.get_readonly_fields
# end TagAdmin class

class ImageAdmin(HiddenAdmin):
    """
    ModelAdmin for :class:`.Image`\.
    """
    
    list_display = (    'status', 'url' )
    list_display_links = (  'status', 'url' )
    readonly_fields = ( 'fullsize_image', 'resource', 'size', 'mime', 'height',
                        'width' )
    exclude = ( 'url','image'   )
    actions = ( retrieve_image, )

    def queryset(self, request):
        """
        Only return Images for approved items in changelist.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`

        Returns
        -------
        queryset : :class:`django.db.models.query.QuerySet`
        """

        if request.path.split('/')[-2] == 'image':   # Only filter changelist.
            return Image.objects.filter(queryItems__status='AP')
        return super(ImageAdmin, self).queryset(request)
    # end ImageAdmin.queryset

    def resource(self, obj):
        """
        Generates a link to the original image (external) URL, opening in a new 
        tab.
        
        Parameters
        ----------
        obj : :class:`.Image`
        
        Returns
        -------
        html : str
        """
        pattern = u'<a href="{0}" target="_blank">{0}</a>'
        return pattern.format(obj.url)
    resource.allow_tags = True
    # end ImageAdmin.resource

    def status(self, obj):
        """
        Returns True if data for this :class:`.Image` has been retrieved.
        
        Parameters
        ----------
        obj : :class:`.Image`
        
        Returns
        -------
        status : boolean
        """
        if obj.size == 0:# and obj.content is None:
            return False
        return True
    status.boolean = True
    # end ImageAdmin.status

    def fullsize_image(self, obj):
        """
        Generates a fullsize image element.

        TODO: constrain display size.
        
        Parameters
        ----------
        obj : :class:`.Image`
        
        Returns
        -------
        html : str
        """

        if obj.image is not None:
            pattern = u'<img src="{0}"/>'
            return pattern.format(obj.image.url)
        return None
    fullsize_image.allow_tags = True
    # end ImageAdmin.fullsize_image
# end ImageAdmin class

class GroupTaskAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.GroupTask`\.
    
    TODO: phase this out?
    """
    list_display = (    'task_id', 'state'  )
# end GroupTaskAdmin class

class EngineAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.Engine`\.
    """
    readonly_fields = ( 'dayusage', 'monthusage'    )
    list_display = (    'engine_name', 'daily_usage', 'monthly_usage'   )

    def engine_name(self, obj):
        """
        Yields the name of the :class:`.Engine` for display in the changelist.
        
        Parameters
        ----------
        obj : :class:`.Engine`
        
        Returns
        -------
        name : unicode
        """
        
        return obj.__unicode__()
    # end EngineAdmin.name

    def daily_usage(self, obj):
        """
        Generates a string representation of daily :class:`.Engine` usage.
        
        Parameters
        ----------
        obj : :class:`.Engine`
        
        Returns
        -------
        usage : unicode
        """
        
        if obj.daylimit is None:
            usage = obj.dayusage
            return u'{0} of unlimited'.format(usage)
        else:
            usage = 100*float(obj.dayusage)/float(obj.daylimit)
            return u'{0}%'.format(usage)
    # end EngineAdmin.daily_usage

    def monthly_usage(self, obj):
        """
        Generates a string representation of monthly :class:`.Engine` usage.
        
        Parameters
        ----------
        obj : :class:`.Engine`
        
        Returns
        -------
        usage : unicode
        """
        
        if obj.monthlimit is None:
            usage = obj.monthusage
            return u'{0} of unlimited'.format(usage)
        else:
            usage = 100*float(obj.monthusage)/float(obj.monthlimit)
            return u'{0}%'.format(usage)
    # end EngineAdmin.monthly_usage

    def get_form(self, request, obj=None, **kwargs):
        """
        Ensures that the ``manager`` field is readonly on the edit view.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.Engine`
        **kwargs
        
        Returns
        -------
        readonly_fields : list
        """

        readonly_fields = ['dayusage', 'monthusage']
        if obj is not None:
            self.readonly_fields = readonly_fields + ['manager']

        return super(EngineAdmin, self).get_form(request, obj, **kwargs)
    # end EngineAdmin.get_form
# end EngineAdmin class

class AudioAdmin(HiddenAdmin):
    """
    ModelAdmin for :class:`.Audio`\.
    """
    
    readonly_fields = ( 'preview', 'url', 'size', 'length', 'mime'  )
    exclude = ( 'audio_file' ,   )

    def preview(self, obj, *args, **kwargs):
        """
        Generates an embedded audio player.
        
        Parameters
        ----------
        obj : :class:`.Audio`
        *args
        **kwargs
        
        Returns
        -------
        html : str
        """
        
        pattern = u'<audio controls>{0}</audio>'
        source = u'<source src="{0}" />'.format(obj.url)

        return pattern.format(source)
    preview.allow_tags = True
    # end AudioAdmin.preview
# end AudioAdmin class

class TextAdmin(HiddenAdmin):
    """
    ModelAdmin for :class:`.Text`\.
    """
    
    readonly_fields = ( 'text_file', 'url', 'size', 'mime'  )
# end TextAdmin class

class ThumbnailAdmin(HiddenAdmin):
    pass
# end ThumbnailAdmin class

class VideoAdmin(HiddenAdmin):
    """
    ModelAdmin for :class:`.Video`\.
    """
    
    readonly_fields = ( 'preview', 'url', 'size', 'length', 'mime'  )
    exclude = ( 'video', )

    def preview(self, obj, *args, **kwargs):
        """
        Generates an embedded video player.
        
        Parameters
        ----------
        obj : :class:`.Video`
        *args
        **kwargs
        
        Returns
        -------
        html : str
        """
        
        pattern = u'<video width="320" height="240" controls>{0}</video>'
        source = u'<source src="{0}" />'.format(obj.url)
        return pattern.format(source)
    preview.allow_tags = True
    # end VideoAdmin.preview
# end VideoAdmin class

class DiffBotRequestAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.DiffBotRequest`\.
    """
    
    list_display = (    'id', 'created', 'attempted', 'completed', 'type'   )
    actions = ( doPerformDiffBotRequest )
# end DiffBotRequestAdmin class

class OAuthAccessTokenAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.OAuthAccessToken`\.
    """
    
    list_display = (    'user_id', 'screen_name', 'platform', 'access_verified',
                        'created', 'expires'   )
    list_display_links = (  'screen_name', 'user_id'    )

    def access_verified(self, obj):
        """
        Indicate whether OAuth authentication was successful.
        
        Parameters
        ----------
        obj : :class:`.OAuthAccessToken`
        
        Returns
        -------
        verified : boolean
        """
        now = localize_datetime(datetime.now())
        
        if obj.oauth_access_token is not None:
            if obj.expires is not None:
                if now >= obj.expires:
                    return False
            return True
        return False
    access_verified.boolean = True

    def get_urls(self):
        """
        Adds the callback view for the OAuth authentication process.
        """
        urls = super(OAuthAccessTokenAdmin, self).get_urls()
        my_urls = patterns('',
            (   r'^callback/(?P<platform>[a-zA-Z]+)/$',
                    self.admin_site.admin_view(self.callback)   ),
        )
        return my_urls + urls
    # end OAuthAccessTokenAdmin.get_urls

    def callback(self, request, platform):
        """
        View that receives a verifier from OAuth service, and gets an access
        token.
        
        TODO: Should create a more flexible way of handling different platforms
        here.
        
        TODO: Change the way that URLs get generated.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        platform : str
            e.g. 'Twitter' or 'Facebook'
            
        Returns
        -------
        response : :class:`django.http.HttpResponse`
        """
        
        logger.debug('Yield callback for platform {0}.'.format(platform))
                               
        if platform == 'Twitter':
            manager = TwitterOAuthManager(
                        consumer_key=settings.TWITTER_KEY,
                        consumer_secret=settings.TWITTER_SECRET
                        )
            _ptoken_id = manager.get_access_token(request)
            ptoken = OAuthAccessToken.objects.get(pk=_ptoken_id)

        elif platform == 'Facebook':
            manager = FacebookOAuthManager(
                        consumer_key=settings.FACEBOOK_ID,
                        consumer_secret=settings.FACEBOOK_SECRET
                        )
            callback_url = 'http://{0}{1}admin/dolon/'.format(request.get_host(), settings.APP_DIR)   +\
                       'oauthaccesstoken/callback/{0}/'.format(platform)                        
            _ptoken_id = manager.get_access_token(request, redirect=callback_url)
            ptoken = OAuthAccessToken.objects.get(pk=_ptoken_id)

        else:
            return

        return redirect(get_admin_url(ptoken))
            
    # end OAuthAccessTokenAdmin.callback

    def response_add(self, request, obj, *args, **kwargs):
        """
        Redirect user to an access url for OAuth authentication.
        
        TODO: Change the way that URLs get generated.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.OAuthAccessToken`
        *args
        **kwargs
        
        Returns
        -------
        response : :class:`django.http.HttpResponse`
        """
        
        pattern = 'http://{0}{1}admin/dolon/oauthaccesstoken/callback/{2}/'
        callback_url = pattern.format(
                        request.get_host(), settings.APP_DIR, obj.platform  )

        logger.debug(callback_url)
        
        if obj.platform.name == 'Twitter':
            manager = TwitterOAuthManager(
                        consumer_key=settings.TWITTER_KEY,
                        consumer_secret=settings.TWITTER_SECRET,
                        callback_url = callback_url
                        )
        elif obj.platform.name == 'Facebook':
            manager = FacebookOAuthManager(
                        consumer_key=settings.FACEBOOK_ID,
                        consumer_secret=settings.FACEBOOK_SECRET,
                        callback_url = callback_url
                        )            
        else:
            return
            
        redirect_url = manager.get_access_url(callback_url)            
        return redirect(redirect_url)

    def get_form(self, request, obj=None, **kwargs):
        """
        Modifies readonly and exclude fields based on whether an
        :class:`.OAuthAccessToken` is being created or edited.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.OAuthAccessToken` or None
        **kwargs
        
        Returns
        -------
        form : :class:`django.forms.ModelForm`
        """

        exclude = [     'oauth_token_secret', 'oauth_access_token_secret',
                        'oauth_token', 'oauth_verified', 'oauth_access_token',
                        'oauth_verifier'    ]
        if obj is None:
            self.exclude = exclude + [ 'user_id', 'screen_name',
                                       'access_verified', 'creator', 'created' ]
            self.readonly_fields = []
        else:
            self.readonly_fields = [ 'platform',  'user_id', 'access_verified', 
                                     'creator', 'created', ]
            self.exclude = exclude

        form = super(OAuthAccessTokenAdmin, self).get_form( request, obj,
                                                            **kwargs    )

        return form
# end OAuthAccessTokenAdmin class

class SocialUserAdmin(admin.ModelAdmin):
    """
    ModelAdmin for :class:`.SocialUser`\.
    """
    
    list_display = (    'handle', 'platform', 'user_id', 'profile'  )

    def get_form(self, request, obj=None, **kwargs):
        """
        Modifies fields based on whether a :class:`.SocialUser` is being created
        or edited.
        
        Parameters
        ----------
        request : :class:`django.http.HttpRequest`
        obj : :class:`.SocialUser` or None
        **kwargs
        
        Returns
        -------
        form : :class:`django.forms.ModelForm`
        """

        if obj is not None:
            self.readonly_fields = [ 'handle', 'platform', 'profile_url',
                                     'user_id', 'content_by_this_user' ]
            self.fields = [ 'handle', 'platform', 'profile_url', 'user_id',
                            'description', 'content_by_this_user' ]                                     
        else:
            self.readonly_fields = []
            self.fields = []
        form = super(SocialUserAdmin, self).get_form(request, obj, **kwargs)
        return form

    def profile(self, obj):
        """
        Generate a link to the user's profile.
        
        Parameters
        ----------
        obj : :class:`.SocialUser`
        
        Returns
        -------
        html : str
        """

        if obj.profile_url is None:
            return None

        link = '<a href="{0}">Profile</a>'.format(obj.profile_url)
        return link
    profile.allow_tags = True

    def content_by_this_user(self, obj):
        """
        Generate a list of :class:`.Item`\s generated by this
        :class:`.SocialUser`\.
        
        TODO: There must be a better way to do this, using templates.
        
        Parameters
        ----------
        obj : :class:`.SocialUser`
        
        Returns
        -------
        html : str
        """

        items = obj.content()

        pattern = '<tr class="row{0}">' + \
                        '<td>{1}</td>' + \
                        '<td>{2}</td>' + \
                        '<td><a href="{3}">{4}</a></td>' + \
                    '</tr>'

        lpattern = '<table id="result_list" width="100%"> ' + \
                        '<thead>' + \
                            '<tr>' + \
                                '<td scope="col">Type</td>' + \
                                '<td scope="col">Date</td>' + \
                                '<td scope="col" width="50%">Preview</td>' + \
                            '</tr>' + \
                        '</thead>' + \
                        '<tbody>{0}</tbody>' + \
                    '</table>'

        formatted = []
        row = 2     # Alternating row number.
        for i in items:
            url = get_admin_url(i)
            if i.type == 'Text':
                content = i.textitem.snippet.encode('utf-8')
            else:   # TODO: add support for previewing other content types.
                content = i.title
            formatted.append(
                pattern.format(row, i.type, i.creationDate, url, content)   )

            if row == 1: row = 2
            else: row = 1
        return lpattern.format(''.join(formatted))
    content_by_this_user.allow_tags = True


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
admin.site.register(Text, TextAdmin)
admin.site.register(Thumbnail, ThumbnailAdmin)
admin.site.register(SocialPlatform)
admin.site.register(SocialUser, SocialUserAdmin)
admin.site.register(HashTag)
admin.site.register(OAuthAccessToken, OAuthAccessTokenAdmin)