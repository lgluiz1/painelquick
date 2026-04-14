from django.urls import path
from . import views

urlpatterns = [
    path('google/login/', views.google_auth_init, name='google_auth_init'),
    path('google/callback/', views.google_auth_callback, name='google_auth_callback'),
    path('live/<slug:company_slug>/<slug:event_slug>/', views.live_event_detail, name='live_event_detail'),
    path('api/livestream/attendance/', views.register_live_attendance, name='register_live_attendance'),
    path('api/livestream/heartbeat/', views.live_heartbeat, name='live_heartbeat'),
    path('api/livestream/<int:event_id>/chat/', views.live_chat_api, name='live_chat_api'),
    path('api/livestream/<int:event_id>/like/', views.live_like_api, name='live_like_api'),
    path('status/<int:event_id>/', views.live_status_api, name='live_status_api'),
    path('l/<slug:company_slug>/', views.company_live_dashboard, name='company_live_dashboard'),
]
