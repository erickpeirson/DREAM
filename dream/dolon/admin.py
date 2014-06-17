from django.contrib import admin

from models import QueryEvent, QueryResult, QueryItem, Engine


# Register your models here.
admin.site.register(QueryEvent)
admin.site.register(QueryResult)
admin.site.register(QueryItem)

admin.site.register(Engine)