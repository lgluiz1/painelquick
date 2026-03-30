from django.urls import path
from . import views

urlpatterns = [
    path('api/attendance/', views.submit_attendance, name='api_attendance'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/meetings/', views.api_meetings, name='api_meetings'),
    path('api/meetings/<int:pk>/', views.api_meeting_detail, name='api_meeting_detail'),
    
    # NOVAS URLS DE CURSOS
    path('api/courses/', views.api_courses, name='api_courses'),
    path('api/courses/<slug:slug>/', views.api_course_detail, name='api_course_detail'),
    path('api/evaluations/<int:pk>/', views.api_evaluation_manage, name='api_evaluation_manage'),
    
    # URLS PÚBLICAS (ESTUDANTE)
    path('api/active-evaluation/<slug:course_slug>/', views.api_get_active_evaluation, name='api_get_active_evaluation'),
    path('api/submit-evaluation/', views.api_submit_evaluation, name='api_submit_evaluation'),
]
