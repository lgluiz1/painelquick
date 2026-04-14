from django.urls import path
from . import views

urlpatterns = [
    # --- PÁGINA INICIAL PÚBLICA (LANDING PAGE) ---
    path('', views.home, name='home'),

    # --- PORTAL DO CAPELÃO (ADMIN CENTRAL) ---
    path('portal/login/', views.portal_login, name='portal_login'),
    path('portal/logout/', views.portal_logout, name='portal_logout'),
    path('portal/dashboard/', views.portal_dashboard, name='portal_dashboard'),
    path('portal/empresas/', views.portal_companies, name='portal_companies'),
    path('portal/global-report/', views.export_global_report_excel, name='export_global_report_excel'),
    path('portal/users/', views.portal_users, name='portal_users'),
    path('portal/company/<slug:slug>/', views.portal_company_detail, name='portal_company_detail'),
    path('portal/saas-settings/', views.portal_saas_settings, name='portal_saas_settings'),
    
    # Detalhes de Gestão Scoped por Empresa
    path('portal/company/<slug:slug>/meetings/', views.portal_meetings, name='portal_meetings'),
    path('portal/company/<slug:slug>/meetings/<int:pk>/', views.portal_meeting_detail, name='portal_meeting_detail'),
    path('portal/company/<slug:slug>/meetings/<int:pk>/export/excel/', views.export_meeting_excel, name='export_meeting_excel'),
    path('portal/company/<slug:slug>/meetings/<int:pk>/export/pdf/', views.export_meeting_pdf, name='export_meeting_pdf'),
    path('portal/company/<slug:slug>/courses/', views.portal_courses, name='portal_courses'),
    path('portal/company/<slug:slug>/courses/<int:pk>/', views.portal_course_detail, name='portal_course_detail'),
    path('portal/company/<slug:slug>/courses/evaluation/<int:pk>/', views.portal_evaluation_detail, name='portal_evaluation_detail'),
    path('portal/company/<slug:slug>/courses/evaluation/<int:pk>/export/excel/', views.export_evaluation_excel, name='export_evaluation_excel'),
    path('portal/company/<slug:slug>/courses/evaluation/<int:pk>/export/pdf/', views.export_evaluation_pdf, name='export_evaluation_pdf'),
    path('portal/company/<slug:slug>/complaints/', views.portal_complaints, name='portal_complaints'),
    path('portal/company/<slug:slug>/complaints/<int:pk>/', views.portal_complaint_detail, name='portal_complaint_detail'),
    path('portal/company/<slug:slug>/download/<str:feature>/', views.download_template, name='download_template'),

    # --- PÁGINAS HOSPEDADAS (PÚBLICAS PARA EMPRESAS) ---
    path('p/<slug:company_slug>/<str:feature>/', views.hosted_form, name='hosted_form'),

    # --- APIs PÚBLICAS (COLETA - EXIGEM X-API-KEY NO HEADER) ---
    path('api/submit-attendance/', views.submit_attendance, name='api_submit_attendance'),
    path('api/active-evaluation/<slug:course_slug>/', views.api_get_active_evaluation, name='api_get_active_evaluation'),
    path('api/submit-evaluation/', views.api_submit_evaluation, name='api_submit_evaluation'),
    path('api/complaints/submit/', views.api_submit_complaint, name='api_submit_complaint'),
    path('api/complaints/status/', views.api_get_complaint_status, name='api_get_complaint_status'),
    path('api/complaints/options/', views.api_complaint_options, name='api_complaint_options'),
    path('api/branches/', views.api_get_branches, name='api_get_branches'),
    
    # Obs: As APIs de gestão antigas foram desativadas em favor do novo Portal Centralizado.
]
