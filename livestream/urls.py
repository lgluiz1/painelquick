from django.urls import path
from . import views

urlpatterns = [
    path('live/<slug:company_slug>/<slug:event_slug>/', views.live_event_detail, name='live_event_detail'),
    path('api/livestream/attendance/', views.register_live_attendance, name='register_live_attendance'),
]
