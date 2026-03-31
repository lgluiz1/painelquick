import json
import secrets
import string
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils.text import slugify
from .models import (
    Meeting, Attendance, Course, Evaluation, Question, 
    StudentResponse, StudentAnswer, Complaint, 
    ComplaintCategory, UrgencyLevel, ComplaintUpdate
)

# API KEYS
PUBLIC_API_KEY = "QuickAttendance2026!#"
# Persistent Token for active session (simplified for this case)
ADMIN_TOKEN = "AdminQuickSession_f7e9a8b7c6d5e4f3a2b1" 

def check_admin_auth(request):
    auth_header = request.headers.get('Authorization')
    if auth_header == f"Bearer {ADMIN_TOKEN}":
        return True
    return False

# --- API PRESENÇA ---
@csrf_exempt
def submit_attendance(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    key = request.headers.get('X-Api-Key')
    if key != PUBLIC_API_KEY:
        return JsonResponse({'error': 'Unauthorized Public Key'}, status=401)

    try:
        data = json.loads(request.body)
        name = data.get('nome')
        branch = data.get('filial')
        reuniao_title = data.get('reuniaoId', 'Geral')
        signature = data.get('assinatura')

        if not all([name, branch, reuniao_title, signature]):
            return JsonResponse({'error': 'Dados incompletos'}, status=400)

        meeting, _ = Meeting.objects.get_or_create(title=reuniao_title)
        Attendance.objects.create(
            meeting=meeting,
            name=name,
            branch=branch,
            signature=signature
        )
        return JsonResponse({'status': 'success', 'message': 'Presença registrada!'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        user = data.get('username')
        passw = data.get('password')
        
        authenticated_user = authenticate(username=user, password=passw)
        if authenticated_user:
            return JsonResponse({
                'status': 'success',
                'token': ADMIN_TOKEN,
                'username': authenticated_user.username
            })
        else:
            return JsonResponse({'error': 'Usuário ou senha inválidos.'}, status=401)
    except Exception as e:
        return JsonResponse({'error': 'Erro ao processar login.'}, status=400)

def api_meetings(request):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    meetings = Meeting.objects.all().order_by('-created_at')
    data = [{
        'id': m.id,
        'title': m.title,
        'created_at': m.created_at.strftime('%d/%m/%Y %H:%M'),
        'count': m.attendances.count()
    } for m in meetings]
    return JsonResponse(data, safe=False)

def api_meeting_detail(request, pk):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    try:
        meeting = Meeting.objects.get(pk=pk)
        attendances = meeting.attendances.all().order_by('-created_at')
        data = {
            'title': meeting.title,
            'attendances': [{
                'name': a.name,
                'branch': a.branch,
                'created_at': a.created_at.strftime('%d/%m/%Y %H:%M'),
                'signature': a.signature
            } for a in attendances]
        }
        return JsonResponse(data)
    except Meeting.DoesNotExist:
        return JsonResponse({'error': 'Reunião não encontrada'}, status=404)

# --- API CURSOS E AVALIAÇÕES (ADMIN) ---

@csrf_exempt
def api_courses(request):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    if request.method == 'GET':
        courses = Course.objects.all().order_by('title')
        data = [{
            'id': c.id,
            'title': c.title,
            'slug': c.slug,
            'eval_count': c.evaluations.count()
        } for c in courses]
        return JsonResponse(data, safe=False)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title')
        if not title: return JsonResponse({'error': 'Título obrigatório'}, status=400)
        
        slug = slugify(title)
        Course.objects.create(title=title, slug=slug)
        return JsonResponse({'status': 'success'})

@csrf_exempt
def api_course_detail(request, slug):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    try:
        course = Course.objects.get(slug=slug)
        if request.method == 'GET':
            evaluations = course.evaluations.all().order_by('-created_at')
            data = {
                'id': course.id,
                'title': course.title,
                'evaluations': [{
                    'id': e.id,
                    'title': e.title,
                    'is_active': e.is_active,
                    'resp_count': e.student_responses.count()
                } for e in evaluations]
            }
            return JsonResponse(data)
        
        if request.method == 'POST':
            data = json.loads(request.body)
            Evaluation.objects.create(course=course, title=data.get('title'))
            return JsonResponse({'status': 'success'})

    except Course.DoesNotExist:
        return JsonResponse({'error': 'Curso não encontrado'}, status=404)

@csrf_exempt
def api_evaluation_manage(request, pk):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    try:
        evaluation = Evaluation.objects.get(pk=pk)
        if request.method == 'GET':
            questions = evaluation.questions.all()
            responses = evaluation.student_responses.all().order_by('-created_at')
            
            data = {
                'title': evaluation.title,
                'course': evaluation.course.title,
                'is_active': evaluation.is_active,
                'questions': [{
                    'id': q.id,
                    'text': q.text,
                    'order': q.order
                } for q in questions],
                'responses': [{
                    'name': r.name,
                    'branch': r.branch,
                    'email': r.email,
                    'created_at': r.created_at.strftime('%d/%m/%Y %H:%M'),
                    'answers': [{
                        'q': a.question.text,
                        'a': a.answer_text
                    } for a in r.answers.all()]
                } for r in responses]
            }
            return JsonResponse(data)
        
        if request.method == 'POST':
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'toggle_active':
                if not evaluation.is_active:
                    evaluation.course.evaluations.update(is_active=False)
                    evaluation.is_active = True
                else:
                    evaluation.is_active = False
                evaluation.save()
                
            elif action == 'add_question':
                Question.objects.create(
                    evaluation=evaluation,
                    text=data.get('text'),
                    order=evaluation.questions.count() + 1
                )
            return JsonResponse({'status': 'success'})
            
    except Evaluation.DoesNotExist:
        return JsonResponse({'error': 'Avaliação não encontrada'}, status=404)

# --- API PÚBLICA (ALUNOS) ---

def api_get_active_evaluation(request, course_slug):
    try:
        course = Course.objects.get(slug=course_slug)
        eval_active = course.evaluations.filter(is_active=True).first()
        
        if not eval_active:
            return JsonResponse({'error': 'Nenhuma avaliação ativa disponível'}, status=404)
        
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
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        eval_id = data.get('evaluation_id')
        name = data.get('nome')
        branch = data.get('filial')
        email = data.get('email')
        answers = data.get('answers', {}) 
        
        evaluation = Evaluation.objects.get(pk=eval_id)
        
        response = StudentResponse.objects.create(
            evaluation=evaluation,
            name=name,
            branch=branch,
            email=email
        )
        
        for q_id, text in answers.items():
            question = Question.objects.get(pk=q_id)
            StudentAnswer.objects.create(
                response=response,
                question=question,
                answer_text=text
            )
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# --- API OUVIDORIA / DENÚNCIAS ---

@csrf_exempt
def api_submit_complaint(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        is_anon = data.get('is_anonymous', True)
        name = data.get('name') if not is_anon else None
        email = data.get('email') if not is_anon else None
        branch = data.get('branch')
        category_id = data.get('category_id')
        urgency_id = data.get('urgency_id')
        description = data.get('description')

        if not all([branch, description]):
            return JsonResponse({'error': 'Filial e Descrição são obrigatórios.'}, status=400)

        # Gerar Ticket ID único: QUICK-XXXXX
        ticket = 'QUICK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        while Complaint.objects.filter(ticket_id=ticket).exists():
            ticket = 'QUICK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        category = ComplaintCategory.objects.filter(id=category_id).first() if category_id else None
        urgency = UrgencyLevel.objects.filter(id=urgency_id).first() if urgency_id else None

        complaint = Complaint.objects.create(
            ticket_id=ticket,
            is_anonymous=is_anon,
            name=name,
            email=email,
            branch=branch,
            category=category,
            urgency=urgency,
            description=description
        )

        return JsonResponse({
            'status': 'success',
            'ticket_id': ticket,
            'message': 'Denúncia enviada com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def api_check_complaint(request, ticket_id):
    try:
        complaint = Complaint.objects.get(ticket_id=ticket_id)
        updates = complaint.updates.all().order_by('created_at')
        
        return JsonResponse({
            'ticket_id': complaint.ticket_id,
            'status': complaint.get_status_display(),
            'category': complaint.category.name if complaint.category else 'Não definida',
            'urgency': complaint.urgency.name if complaint.urgency else 'Não definida',
            'created_at': complaint.created_at.strftime('%d/%m/%Y %H:%M'),
            'description': complaint.description,
            'updates': [{
                'message': u.message,
                'created_at': u.created_at.strftime('%d/%m/%Y %H:%M'),
                'is_admin': u.is_from_admin
            } for u in updates]
        })
    except Complaint.DoesNotExist:
        return JsonResponse({'error': 'Ticket não encontrado'}, status=404)

@csrf_exempt
def api_admin_complaints(request):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    complaints = Complaint.objects.all().order_by('-created_at')
    data = [{
        'id': c.id,
        'ticket_id': c.ticket_id,
        'status': c.status,
        'status_display': c.get_status_display(),
        'branch': c.branch,
        'category': c.category.name if c.category else '---',
        'urgency_color': c.urgency.color if c.urgency else '#6c757d',
        'is_anonymous': c.is_anonymous,
        'created_at': c.created_at.strftime('%d/%m/%Y %H:%M')
    } for c in complaints]
    return JsonResponse(data, safe=False)

@csrf_exempt
def api_admin_complaint_detail(request, pk):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    try:
        complaint = Complaint.objects.get(pk=pk)
        if request.method == 'GET':
            updates = complaint.updates.all().order_by('created_at')
            return JsonResponse({
                'id': complaint.id,
                'ticket_id': complaint.ticket_id,
                'name': complaint.name if not complaint.is_anonymous else 'Anônimo',
                'email': complaint.email if not complaint.is_anonymous else '---',
                'branch': complaint.branch,
                'description': complaint.description,
                'status': complaint.status,
                'category': complaint.category.name if complaint.category else '---',
                'updates': [{
                    'message': u.message,
                    'created_at': u.created_at.strftime('%d/%m/%Y %H:%M'),
                    'is_admin': u.is_from_admin
                } for u in updates]
            })
        
        if request.method == 'POST':
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'add_update':
                ComplaintUpdate.objects.create(
                    complaint=complaint,
                    message=data.get('message'),
                    is_from_admin=True
                )
            elif action == 'update_status':
                complaint.status = data.get('status')
                complaint.save()
                
            return JsonResponse({'status': 'success'})
            
    except Complaint.DoesNotExist:
        return JsonResponse({'error': 'Denúncia não encontrada'}, status=404)

@csrf_exempt
def api_complaint_options(request):
    categories = ComplaintCategory.objects.all().order_by('name')
    urgencies = UrgencyLevel.objects.all().order_by('id')
    return JsonResponse({
        'categories': [{'id': c.id, 'name': c.name} for c in categories],
        'urgencies': [{'id': u.id, 'name': u.name, 'color': u.color} for u in urgencies]
    })

@csrf_exempt
def api_admin_complaint_config(request):
    if not check_admin_auth(request):
        return JsonResponse({'error': 'Não autorizado'}, status=401)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        target = data.get('target')
        if target == 'category':
            ComplaintCategory.objects.create(name=data.get('name'))
        elif target == 'urgency':
            UrgencyLevel.objects.create(name=data.get('name'), color=data.get('color', '#6c757d'))
        return JsonResponse({'status': 'success'})
