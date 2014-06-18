from django.contrib import admin

from models import QueryEvent, QueryResult, QueryItem, Engine, QueryString


class QueryEventInline(admin.TabularInline):
    model = QueryEvent
    readonly_fields = ('rangeStart', 'rangeEnd', 'datetime', 'engine', 'queryresults')

    extra = 0
    def has_delete_permission(self, request, obj=None):
        """
        :class:`.QueryEvent` should not be deletable.
        """
        return False

class QueryStringAdmin(admin.ModelAdmin):
    list_display = ('querystring', 'events', 'latest', 'items')
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

class QueryEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'querystring', 'datetime', 'rangeStart', 'rangeEnd', 'items')
    list_display_links = ('querystring',)
    
    def get_readonly_fields(self, request, obj=None):
        """
        All fields should be readonly after creation.
        """

        if obj:
            return ('querystring', 'rangeStart', 'rangeEnd', 'engine') + self.readonly_fields
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Should not display :class:`.QueryResult` when adding.
        """
        
        if obj is None:
            self.exclude = ['queryresults']

        return super(QueryEventAdmin, self).get_form(request, obj, **kwargs)

# Register your models here.
admin.site.register(QueryEvent, QueryEventAdmin)
admin.site.register(QueryResult)    # TODO: this should be removed eventually.
admin.site.register(QueryItem)
admin.site.register(QueryString, QueryStringAdmin)


admin.site.register(Engine)