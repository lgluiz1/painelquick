from django.urls import path
from . import views

urlpatterns = [
    # --- PORTAL DO CAPELÃO (ADMIN CENTRAL) ---
    path('portal/login/', views.portal_login, name='portal_login'),
    path('portal/dashboard/', views.portal_dashboard, name='portal_dashboard'),
    path('portal/company/<slug:slug>/', views.portal_company_detail, name='portal_company_detail'),

    # --- PÁGINAS HOSPEDADAS (PÚBLICAS PARA EMPRESAS) ---
    path('p/<slug:company_slug>/<str:feature>/', views.hosted_form, name='hosted_form'),

    # --- APIs PÚBLICAS (COLETA - EXIGEM X-API-KEY NO HEADER) ---
    path('api/submit-attendance/', views.submit_attendance, name='api_submit_attendance'),
    path('api/active-evaluation/<slug:course_slug>/', views.api_get_active_evaluation, name='api_get_active_evaluation'),
    path('api/submit-evaluation/', views.api_submit_evaluation, name='api_submit_evaluation'),
    path('api/complaints/submit/', views.api_submit_complaint, name='api_submit_complaint'),
    path('api/complaints/options/', views.api_complaint_options, name='api_complaint_options'),
    
    # Obs: As APIs de gestão antigas foram desativadas em favor do novo Portal Centralizado.
]
