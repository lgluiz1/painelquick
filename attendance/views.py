import json
import string
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.utils.text import slugify
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
import os
from .models import (
    Company, Branch, Meeting, Attendance, Course, Evaluation, Question, 
    StudentResponse, StudentAnswer, Complaint, 
    ComplaintCategory, UrgencyLevel, ComplaintUpdate
)

# --- UTILITÁRIOS ---

def get_company_by_token(request):
    token = request.headers.get('X-Api-Key')
    if not token:
        return None
    return Company.objects.filter(api_token=token, is_active=True).first()

# --- API PÚBLICA (COLETA DE DADOS - MULTI-TENANT) ---

@csrf_exempt
def submit_attendance(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    company = get_company_by_token(request)
    if not company:
        return JsonResponse({'error': 'Token de Empresa Inválido ou Inativa'}, status=401)

    try:
        data = json.loads(request.body)
        name = data.get('nome')
        branch_name = data.get('filial')
        reuniao_title = data.get('reuniaoId', 'Geral')
        signature = data.get('assinatura')

        if not all([name, branch_name, reuniao_title, signature]):
            return JsonResponse({'error': 'Dados incompletos'}, status=400)

        meeting, _ = Meeting.objects.get_or_create(company=company, title=reuniao_title)
        Branch.objects.get_or_create(company=company, name=branch_name)

        Attendance.objects.create(
            meeting=meeting,
            name=name,
            branch=branch_name,
            signature=signature
        )
        return JsonResponse({'status': 'success', 'message': 'Presença registrada!'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def api_get_active_evaluation(request, course_slug):
    company = get_company_by_token(request)
    if not company:
        return JsonResponse({'error': 'Token de Empresa Inválido'}, status=401)
        
    try:
        course = Course.objects.get(company=company, slug=course_slug)
        eval_active = course.evaluations.filter(is_active=True).first()
        
        if not eval_active:
            return JsonResponse({'error': 'Nenhuma avaliação ativa disponível'}, status=404)
        
        data = {
            'id': eval_active.id,
            'title': eval_active.title,
            'course': course.title,
            'questions': [{'id': q.id, 'text': q.text} for q in eval_active.questions.all()]
        }
        return JsonResponse(data)
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Curso não encontrado'}, status=404)

@csrf_exempt
def api_submit_evaluation(request):
    company = get_company_by_token(request)
    if not company:
        return JsonResponse({'error': 'Token de Empresa Inválido'}, status=401)

    try:
        data = json.loads(request.body)
        eval_id = data.get('evaluation_id')
        name = data.get('nome')
        branch = data.get('filial')
        email = data.get('email')
        answers = data.get('answers', {}) 
        
        evaluation = Evaluation.objects.get(pk=eval_id, course__company=company)
        response = StudentResponse.objects.create(evaluation=evaluation, name=name, branch=branch, email=email)
        
        for q_id, text in answers.items():
            question = Question.objects.get(pk=q_id, evaluation=evaluation)
            StudentAnswer.objects.create(response=response, question=question, answer_text=text)
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_submit_complaint(request):
    company = get_company_by_token(request)
    if not company:
        return JsonResponse({'error': 'Token de Empresa Inválido'}, status=401)

    try:
        data = json.loads(request.body)
        is_anon = data.get('is_anonymous', True)
        branch = data.get('branch')
        description = data.get('description')

        if not all([branch, description]):
            return JsonResponse({'error': 'Dados incompletos'}, status=400)

        ticket = 'TK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        category = ComplaintCategory.objects.filter(id=data.get('category_id'), company=company).first()
        urgency = UrgencyLevel.objects.filter(id=data.get('urgency_id'), company=company).first()

        Complaint.objects.create(
            company=company, ticket_id=ticket, is_anonymous=is_anon,
            name=data.get('name') if not is_anon else None,
            email=data.get('email') if not is_anon else None,
            branch=branch, category=category, urgency=urgency, description=description
        )
        return JsonResponse({'status': 'success', 'ticket_id': ticket})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_get_branches(request):
    company = get_company_by_token(request)
    if not company:
        return JsonResponse({'error': 'Token Inválido'}, status=401)
    
    branches = company.branches.all().order_by('name')
    return JsonResponse({
        'branches': [{'id': b.id, 'name': b.name} for b in branches]
    })

@csrf_exempt
def api_complaint_options(request):
    company = get_company_by_token(request)
    if not company: return JsonResponse({'error': 'Invalid Token'}, status=401)
    return JsonResponse({
        'categories': [{'id': c.id, 'name': c.name} for c in company.complaint_categories.all()],
        'urgencies': [{'id': u.id, 'name': u.name, 'color': u.color} for u in company.urgency_levels.all()],
        'branches': [{'id': b.id, 'name': b.name} for b in company.branches.all()]
    })

# --- PORTAL DO CAPELÃO (VISTAS PRINCIPAIS) ---

@csrf_exempt
def portal_login(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('portal_dashboard')
        return render(request, 'attendance/portal_login.html', {'error': 'Acesso negado.'})
    return render(request, 'attendance/portal_login.html')

def portal_dashboard(request):
    if not request.user.is_authenticated: return redirect('portal_login')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_company':
            name = request.POST.get('name')
            Company.objects.create(name=name, slug=request.POST.get('slug') or slugify(name))
        elif action == 'update_company':
            c = get_object_or_404(Company, id=request.POST.get('company_id'))
            c.name = request.POST.get('name')
            c.logo_url = request.POST.get('logo_url')
            c.primary_color = request.POST.get('primary_color')
            c.is_active = request.POST.get('is_active') == 'on'
            c.save()
        elif action == 'delete_company':
            get_object_or_404(Company, id=request.POST.get('company_id')).delete()
        return redirect('portal_dashboard')
    return render(request, 'attendance/portal_dashboard.html', {
        'companies': Company.objects.all().order_by('name'),
        'active_companies_count': Company.objects.filter(is_active=True).count()
    })

def portal_company_detail(request, slug):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_branch':
            Branch.objects.create(company=company, name=request.POST.get('branch_name'))
        elif action == 'update_settings':
            company.logo_url = request.POST.get('logo_url')
            company.primary_color = request.POST.get('primary_color')
            company.save()
        return redirect('portal_company_detail', slug=slug)
    return render(request, 'attendance/portal_company.html', {
        'company': company, 'meetings': company.meetings.all(),
        'courses': company.courses.all(), 'complaints': company.complaints.all(),
        'branches': company.branches.all()
    })

# --- GESTÃO DETALHADA ---

def portal_meetings(request, slug):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    if request.method == 'POST':
        if request.POST.get('action') == 'delete_meeting':
            get_object_or_404(Meeting, id=request.POST.get('meeting_id'), company=company).delete()
        elif request.POST.get('action') == 'create_meeting':
            Meeting.objects.create(company=company, title=request.POST.get('title'))
        return redirect('portal_meetings', slug=slug)
    return render(request, 'attendance/portal_meetings.html', {'company': company, 'meetings': company.meetings.all().order_by('-created_at')})

def portal_meeting_detail(request, slug, pk):
    if not request.user.is_authenticated: return redirect('portal_login')
    meeting = get_object_or_404(Meeting, pk=pk, company__slug=slug)
    if request.method == 'POST' and request.POST.get('action') == 'delete_attendance':
        get_object_or_404(Attendance, id=request.POST.get('attendance_id'), meeting=meeting).delete()
        return redirect('portal_meeting_detail', slug=slug, pk=pk)
    return render(request, 'attendance/portal_meeting_detail.html', {'company': meeting.company, 'meeting': meeting, 'attendances': meeting.attendances.all().order_by('-created_at')})

def portal_courses(request, slug):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    if request.method == 'POST':
        if request.POST.get('action') == 'delete_course':
            get_object_or_404(Course, id=request.POST.get('course_id'), company=company).delete()
        elif request.POST.get('action') == 'create_course':
            t = request.POST.get('title')
            Course.objects.create(company=company, title=t, slug=slugify(t))
        return redirect('portal_courses', slug=slug)
    return render(request, 'attendance/portal_courses.html', {'company': company, 'courses': company.courses.all().order_by('-created_at')})

def portal_course_detail(request, slug, pk):
    if not request.user.is_authenticated: return redirect('portal_login')
    course = get_object_or_404(Course, pk=pk, company__slug=slug)
    if request.method == 'POST':
        if request.POST.get('action') == 'add_evaluation':
            Evaluation.objects.create(course=course, title=request.POST.get('title'))
        elif request.POST.get('action') == 'delete_evaluation':
            get_object_or_404(Evaluation, id=request.POST.get('evaluation_id'), course=course).delete()
        return redirect('portal_course_detail', slug=slug, pk=pk)
    return render(request, 'attendance/portal_course_detail.html', {'company': course.company, 'course': course, 'evaluations': course.evaluations.all().order_by('-created_at')})

def portal_complaints(request, slug):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    if request.method == 'POST' and request.POST.get('action') == 'delete_complaint':
        get_object_or_404(Complaint, id=request.POST.get('complaint_id'), company=company).delete()
        return redirect('portal_complaints', slug=slug)
    return render(request, 'attendance/portal_complaints.html', {'company': company, 'complaints': company.complaints.all().order_by('-created_at')})

def portal_complaint_detail(request, slug, pk):
    if not request.user.is_authenticated: return redirect('portal_login')
    complaint = get_object_or_404(Complaint, pk=pk, company__slug=slug)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_update':
            ComplaintUpdate.objects.create(complaint=complaint, message=request.POST.get('message'), is_from_admin=True)
        elif action == 'update_status':
            complaint.status = request.POST.get('status')
            complaint.save()
        return redirect('portal_complaint_detail', slug=slug, pk=pk)
    return render(request, 'attendance/portal_complaint_detail.html', {'company': complaint.company, 'complaint': complaint, 'updates': complaint.updates.all().order_by('created_at')})

def download_template(request, slug, feature):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    
    # Caminho do arquivo na raiz do projeto (fora da pasta backend)
    # No Docker, a raiz pode estar em caminhos diferentes, mas tentaremos os padrões
    file_map = {
        'presenca': 'presenca.html',
        'denuncia': 'denuncia.html',
        'avaliacao': 'avaliacao.html'
    }
    
    filename = file_map.get(feature)
    if not filename: return HttpResponse("Tipo inválido", status=400)
    
    # Tenta localizar o arquivo
    possible_paths = [
        f"/app/../{filename}", # Docker path (assuming backend is in /app)
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), filename) # Local path
    ]
    
    content = ""
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            break
            
    if not content:
        return HttpResponse(f"Arquivo base {filename} não encontrado no servidor.", status=404)
    
    # SUBSTITUIÇÕES MÁGICAS:
    # 1. Token da Empresa
    content = content.replace('YOUR_X_API_KEY_HERE', company.api_token)
    content = content.replace('TOKEN_AQUI', company.api_token) # Variável comum que podemos ter usado
    
    # 2. URL do Servidor (Baseado no seu domínio atual)
    content = content.replace('http://localhost:8000', 'https://quickdelivery.luizgustavo.tech')
    content = content.replace('https://seu-servidor.com', 'https://quickdelivery.luizgustavo.tech')
    
    # 3. Branding (Opcional, se o HTML suportar)
    content = content.replace('#e63946', company.primary_color)
    
    response = HttpResponse(content, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="{feature}_{company.slug}.html"'
    return response

# --- PÁGINAS HOSPEDADAS ---

def hosted_form(request, company_slug, feature):
    company = get_object_or_404(Company, slug=company_slug)
    context = {'company': company}
    if feature == 'presenca': context['reuniao_id'] = request.GET.get('reuniao', 'Geral')
    elif feature == 'denuncia':
        context.update({'categories': company.complaint_categories.all(), 'urgencies': company.urgency_levels.all(), 'branches': company.branches.all()})
    return render(request, f'attendance/public_{feature}.html', context)
