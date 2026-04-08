from django.contrib import admin
from .models import LiveEvent, LiveAttendance

@admin.register(LiveEvent)
class LiveEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'start_time', 'is_active')
    list_filter = ('company', 'is_active', 'start_time')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(LiveAttendance)
class LiveAttendanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'branch', 'timestamp')
    list_filter = ('event', 'branch', 'timestamp')
    search_fields = ('name', 'event__title', 'branch__name')
    readonly_fields = ('timestamp',)
