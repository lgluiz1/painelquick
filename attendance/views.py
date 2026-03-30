import json
import secrets
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from .models import Meeting, Attendance

# API KEYS
PUBLIC_API_KEY = "QuickAttendance2026!#"
ADMIN_TOKEN = "AdminQuickSession_" + secrets.token_hex(16) # In a real app, use a DB-stored token

def check_admin_auth(request):
    auth_header = request.headers.get('Authorization')
    if auth_header == f"Bearer {ADMIN_TOKEN}":
        return True
    return False

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
        'created_at': m.created_at.strftime('%d/%m/%Y %H:%i'),
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
