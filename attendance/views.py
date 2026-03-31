import json
import string
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils.text import slugify
from django.shortcuts import render, redirect, get_object_or_404
from .models import (
    Company, Branch, Meeting, Attendance, Course, Evaluation, Question, 
    StudentResponse, StudentAnswer, Complaint, 
    ComplaintCategory, UrgencyLevel, ComplaintUpdate
)

# API KEYS (Legacy support or internal)
PUBLIC_API_KEY = "QuickAttendance2026!#"
ADMIN_TOKEN = "AdminQuickSession_f7e9a8b7c6d5e4f3a2b1" 

def check_admin_auth(request):
    auth_header = request.headers.get('Authorization')
    if auth_header == f"Bearer {ADMIN_TOKEN}":
        return True
    return False

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
        return JsonResponse({'error': 'Token de Empresa Inválido'}, status=401)

    try:
        data = json.loads(request.body)
        name = data.get('nome')
        branch_name = data.get('filial')
        reuniao_title = data.get('reuniaoId', 'Geral')
        signature = data.get('assinatura')

        if not all([name, branch_name, reuniao_title, signature]):
            return JsonResponse({'error': 'Dados incompletos'}, status=400)

        meeting, _ = Meeting.objects.get_or_create(company=company, title=reuniao_title)
        
        # Opcional: Registrar filial se não existir
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
            return JsonResponse({'error': 'Nenhuma avaliação ativa disponível para este curso.'}, status=404)
        
        data = {
            'id': eval_active.id,
            'title': eval_active.title,
            'course': course.title,
            'questions': [{
                'id': q.id,
                'text': q.text
            } for q in eval_active.questions.all()]
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
        
        response = StudentResponse.objects.create(
            evaluation=evaluation,
            name=name,
            branch=branch,
            email=email
        )
        
        for q_id, text in answers.items():
            question = Question.objects.get(pk=q_id, evaluation=evaluation)
            StudentAnswer.objects.create(
                response=response,
                question=question,
                answer_text=text
            )
            
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
        category_id = data.get('category_id')
        urgency_id = data.get('urgency_id')
        description = data.get('description')

        if not all([branch, description]):
            return JsonResponse({'error': 'Filial e Descrição são obrigatórios.'}, status=400)

        ticket = 'TK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        while Complaint.objects.filter(ticket_id=ticket).exists():
            ticket = 'TK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        category = ComplaintCategory.objects.filter(id=category_id, company=company).first()
        urgency = UrgencyLevel.objects.filter(id=urgency_id, company=company).first()

        Complaint.objects.create(
            company=company,
            ticket_id=ticket,
            is_anonymous=is_anon,
            name=data.get('name') if not is_anon else None,
            email=data.get('email') if not is_anon else None,
            branch=branch,
            category=category,
            urgency=urgency,
            description=description
        )

        return JsonResponse({'status': 'success', 'ticket_id': ticket})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_complaint_options(request):
    company = get_company_by_token(request)
    if not company:
        return JsonResponse({'error': 'Token de Empresa Inválido'}, status=401)

    categories = ComplaintCategory.objects.filter(company=company)
    urgencies = UrgencyLevel.objects.filter(company=company)
    branches = Branch.objects.filter(company=company)

    return JsonResponse({
        'categories': [{'id': c.id, 'name': c.name} for c in categories],
        'urgencies': [{'id': u.id, 'name': u.name, 'color': u.color} for u in urgencies],
        'branches': [{'id': b.id, 'name': b.name} for b in branches]
    })

# --- GESTÃO DE REUNIÕES E PRESENÇAS ---

def portal_meetings(request, slug):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_meeting':
            meeting = get_object_or_404(Meeting, id=request.POST.get('meeting_id'), company=company)
            meeting.delete()
        elif action == 'create_meeting':
            Meeting.objects.create(company=company, title=request.POST.get('title'))
        return redirect('portal_meetings', slug=slug)

    meetings = company.meetings.all().order_by('-created_at')
    return render(request, 'attendance/portal_meetings.html', {'company': company, 'meetings': meetings})

def portal_meeting_detail(request, slug, pk):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    meeting = get_object_or_404(Meeting, pk=pk, company=company)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_attendance':
            attendance = get_object_or_404(Attendance, id=request.POST.get('attendance_id'), meeting=meeting)
            attendance.delete()
        return redirect('portal_meeting_detail', slug=slug, pk=pk)

    attendances = meeting.attendances.all().order_by('-created_at')
    return render(request, 'attendance/portal_meeting_detail.html', {'company': company, 'meeting': meeting, 'attendances': attendances})

# --- GESTÃO DE CURSOS E AVALIAÇÕES ---

def portal_courses(request, slug):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_course':
            course = get_object_or_404(Course, id=request.POST.get('course_id'), company=company)
            course.delete()
        elif action == 'create_course':
            title = request.POST.get('title')
            Course.objects.create(company=company, title=title, slug=slugify(title))
        return redirect('portal_courses', slug=slug)

    courses = company.courses.all().order_by('-created_at')
    return render(request, 'attendance/portal_courses.html', {'company': company, 'courses': courses})

def portal_course_detail(request, slug, pk):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    course = get_object_or_404(Course, pk=pk, company=company)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_evaluation':
            Evaluation.objects.create(course=course, title=request.POST.get('title'))
        elif action == 'delete_evaluation':
            eval = get_object_or_404(Evaluation, id=request.POST.get('evaluation_id'), course=course)
            eval.delete()
        return redirect('portal_course_detail', slug=slug, pk=pk)

    evaluations = course.evaluations.all().order_by('-created_at')
    return render(request, 'attendance/portal_course_detail.html', {'company': company, 'course': course, 'evaluations': evaluations})

# --- GESTÃO DE DENÚNCIAS ---

def portal_complaints(request, slug):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_complaint':
            complaint = get_object_or_404(Complaint, id=request.POST.get('complaint_id'), company=company)
            complaint.delete()
        return redirect('portal_complaints', slug=slug)

    complaints = company.complaints.all().order_by('-created_at')
    return render(request, 'attendance/portal_complaints.html', {'company': company, 'complaints': complaints})

def portal_complaint_detail(request, slug, pk):
    if not request.user.is_authenticated: return redirect('portal_login')
    company = get_object_or_404(Company, slug=slug)
    complaint = get_object_or_404(Complaint, pk=pk, company=company)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_update':
            ComplaintUpdate.objects.create(complaint=complaint, message=request.POST.get('message'), is_from_admin=True)
        elif action == 'update_status':
            complaint.status = request.POST.get('status')
            complaint.save()
        return redirect('portal_complaint_detail', slug=slug, pk=pk)

    updates = complaint.updates.all().order_by('created_at')
    return render(request, 'attendance/portal_complaint_detail.html', {'company': company, 'complaint': complaint, 'updates': updates})

# --- PÁGINAS HOSPEDADAS (PÚBLICAS) ---

def hosted_form(request, company_slug, feature):
    company = get_object_or_404(Company, slug=company_slug)
    
    template_name = f'attendance/public_{feature}.html'
    context = {'company': company}
    
    if feature == 'presenca':
        context['reuniao_id'] = request.GET.get('reuniao', 'Geral')
    elif feature == 'denuncia':
        context['categories'] = company.complaint_categories.all()
        context['urgencies'] = company.urgency_levels.all()
        context['branches'] = company.branches.all()
        
    return render(request, template_name, context)
