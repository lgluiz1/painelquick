from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls), # Standard admin
    path('', include('attendance.urls')), # Custom app urls
    path('', include('livestream.urls')), # Livestream app urls
]

# Habilita o servidor de arquivos estáticos e mídia (Importante para o Logo carregar)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
