from django.contrib import admin

from models import *
from managers import spawnSearch


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

def dispatch(modeladmin, request, queryset):
    for obj in queryset:
        task_id = spawnSearch(obj)
        task = Task(task_id=task_id)
        task.save()
        print 'asdf', obj, task, task.state()
        obj.search_task = task
        obj.dispatched = True
        obj.save()

dispatch.short_description = 'Dispatch selected search events'

class QueryEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'querystring', 'datetime', 'rangeStart', 'rangeEnd', 
                    'items', 'dispatched', 'searchstatus', 'thumbnailstatus')
    list_display_links = ('querystring',)
    actions = [dispatch]
    exclude = ['search_task', 'thumbnail_tasks']
    
    
    def get_readonly_fields(self, request, obj=None):
        """
        All fields should be readonly after creation.
        """

        if obj:
            return ('querystring', 'rangeStart', 'rangeEnd', 'engine', 'dispatched', 'queryresults') + self.readonly_fields
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Should not display :class:`.QueryResult` when adding.
        """
        
        if obj is None:
            self.exclude += ['queryresults', 'dispatched']

        return super(QueryEventAdmin, self).get_form(request, obj, **kwargs)

class QueryItemAdmin(admin.ModelAdmin):
    list_display = ('thumbimage','title', 'height','width', 'status', 'queryevents')

# Register your models here.
admin.site.register(QueryEvent, QueryEventAdmin)
admin.site.register(QueryResult)    # TODO: this should be removed eventually.
admin.site.register(QueryItem, QueryItemAdmin)
admin.site.register(QueryString, QueryStringAdmin)

admin.site.register(Task)


admin.site.register(Engine)