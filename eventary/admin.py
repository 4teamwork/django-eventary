from django.contrib import admin
from django.contrib.admin import ModelAdmin

from .models import Calendar, Event, EventTimeDate
from .models import GroupingType, Grouping, Group

admin.site.register(Calendar)
admin.site.register(Event)
admin.site.register(EventTimeDate)

admin.site.register(GroupingType)


@admin.register(Grouping)
class GroupingAdmin(ModelAdmin):
    list_display = ["id", "title", "order"]
    list_display_links = ["title"]
    list_editable = ["order"]


admin.site.register(Group)
