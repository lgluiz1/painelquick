from django.contrib import admin
from .models import (
    Meeting, Attendance, Course, Evaluation, Question, 
    StudentResponse, StudentAnswer, ComplaintCategory, 
    UrgencyLevel, Complaint, ComplaintUpdate
)

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title',)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'meeting', 'created_at')
    list_filter = ('meeting', 'branch')
    search_fields = ('name', 'branch')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'is_active', 'created_at')
    list_filter = ('course', 'is_active')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'evaluation', 'order')
    list_filter = ('evaluation',)

class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0

@admin.register(StudentResponse)
class StudentResponseAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'branch', 'evaluation', 'created_at')
    list_filter = ('evaluation', 'branch')
    inlines = [StudentAnswerInline]

@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(UrgencyLevel)
class UrgencyLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')

class ComplaintUpdateInline(admin.TabularInline):
    model = ComplaintUpdate
    extra = 1

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'status', 'category', 'urgency', 'branch', 'created_at')
    list_filter = ('status', 'category', 'urgency', 'branch')
    search_fields = ('ticket_id', 'description', 'name')
    inlines = [ComplaintUpdateInline]
