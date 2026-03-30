import json
import secrets
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.utils.text import slugify
from .models import Meeting, Attendance, Course, Evaluation, Question, StudentResponse, StudentAnswer

# API KEYS
PUBLIC_API_KEY = "QuickAttendance2026!#"
# Persistent Token for active session (simplified for this case)
ADMIN_TOKEN = "AdminQuickSession_f7e9a8b7c6d5e4f3a2b1" # Simplified fixed token for testing 

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
        
        if request.method == 'POST': # Update status or Add Question
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'toggle_active':
                # Desativa todas as outras do mesmo curso primeiro
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

# --- API PÚBLICA (ESTUDANTE) ---

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
        answers = data.get('answers', {}) # Dict { question_id: answer_text }
        
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
