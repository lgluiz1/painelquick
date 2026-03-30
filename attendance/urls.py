from django.urls import path
from . import views

urlpatterns = [
    path('api/attendance/', views.submit_attendance, name='api_attendance'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/meetings/', views.api_meetings, name='api_meetings'),
    path('api/meetings/<int:pk>/', views.api_meeting_detail, name='api_meeting_detail'),
]
