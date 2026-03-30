from django.contrib import admin
from django.urls import path, include
from attendance import views

urlpatterns = [
    path('admin/', admin.site.urls), # Standard admin
    path('', include('attendance.urls')), # Custom app urls
]
