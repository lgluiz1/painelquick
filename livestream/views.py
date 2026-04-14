from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from .models import LiveEvent, LiveAttendance, YouTubeConfig, LiveChatMessage
from .youtube_service import YouTubeService
import os

# Permitir HTTP para testes locais de OAuth (remover em produção se o site for HTTPS)
if settings.DEBUG:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from django.urls import reverse
from django.contrib.auth.decorators import login_required
from attendance.models import Company, Branch
import json
import re

def get_youtube_id(url):
    """
    Extracts the video ID from a YouTube URL.
    """
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def live_event_detail(request, company_slug, event_slug):
    company = get_object_or_404(Company, slug=company_slug)
    event = get_object_or_404(LiveEvent, slug=event_slug, company=company, is_active=True)
    
    user_data_key = f'user_data_event_{event.id}'
    session_key = f'attended_event_{event.id}'

    # Se evento já terminou, ainda permitimos assistir à gravação
    # mas pulamos o formulário de presença conforme solicitado.
    if event.status == 'finished':
        youtube_id = get_youtube_id(event.youtube_url)
        user_data = request.session.get(user_data_key, {})
        context = {
            'company': company,
            'event': event,
            'youtube_id': youtube_id,
            'user_name': user_data.get('name', 'Espectador'),
            'user_branch': user_data.get('branch_name', 'Gravação'),
            'now': timezone.now(),
        }
        return render(request, 'livestream/public_live_player.html', context)

    # 1. Verificar se o usuário já se identificou (Assinatura/Formulário)
    has_attended = request.session.get(session_key, False)
    
    if not has_attended:
        # Se não se identificou, mostra o formulário de entrada
        context = {
            'company': company,
            'event': event,
            'branches': company.branches.all().order_by('name'),
        }
        return render(request, 'livestream/event_attendance_form.html', context)

    # 2. Se já se identificou, verificar o STATUS da sala (Waiting vs Live)
    youtube_id = get_youtube_id(event.youtube_url)
    context = {
        'company': company,
        'event': event,
        'youtube_id': youtube_id,
        'user_name': user_data.get('name'),
        'user_branch': user_data.get('branch_name'),
        'now': timezone.now(),
    }

    if event.status == 'waiting':
        # Sala de Espera com contagem regressiva
        return render(request, 'livestream/public_waiting_room.html', context)
    
    # 3. Live Ativa: Mostra o Player Customizado
    return render(request, 'livestream/public_live_player.html', context)

@csrf_exempt
def register_live_attendance(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        name = data.get('name')
        branch_id = data.get('branch_id')
        
        if not all([event_id, name, branch_id]):
            return JsonResponse({'error': 'Dados incompletos'}, status=400)
            
        event = get_object_or_404(LiveEvent, id=event_id)
        branch = get_object_or_404(Branch, id=branch_id, company=event.company)
        
        # Register attendance
        attendance = LiveAttendance.objects.create(
            event=event,
            name=name,
            branch=branch
        )
        
        # Salva na sessão que este usuário já se registrou para este evento específico
        request.session[f'attended_event_{event.id}'] = True
        request.session[f'user_data_event_{event.id}'] = {
            'name': name,
            'branch_name': branch.name
        }
        
        return JsonResponse({'status': 'success', 'attendance_id': attendance.id, 'message': 'Presença confirmada! Aproveite a live.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def google_auth_init(request):
    # A URI de redirecionamento deve estar registrada no Google Console
    redirect_uri = request.build_absolute_uri(reverse('google_auth_callback'))
    flow = YouTubeService.get_flow(redirect_uri)
    
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Armazena o estado e o verificador do PKCE na sessão
    request.session['oauth_state'] = state
    if hasattr(flow, 'code_verifier'):
        request.session['oauth_code_verifier'] = flow.code_verifier
    
    return redirect(auth_url)

@login_required
def google_auth_callback(request):
    state = request.session.get('oauth_state')
    
    if not state:
        return render(request, 'attendance/error.html', {'message': 'Sessão expirada. Tente novamente.'})
        
    redirect_uri = request.build_absolute_uri(reverse('google_auth_callback'))
    flow = YouTubeService.get_flow(redirect_uri)
    
    # Restaura o verificador do PKCE da sessão
    if 'oauth_code_verifier' in request.session:
        flow.code_verifier = request.session['oauth_code_verifier']
    
    try:
        auth_response = request.build_absolute_uri()
        if 'http://' in auth_response and not settings.DEBUG:
            auth_response = auth_response.replace('http://', 'https://')
            
        flow.fetch_token(authorization_response=auth_response)
    except Exception as e:
        return render(request, 'attendance/error.html', {'message': f'Erro ao obter token: {str(e)}'})
        
    creds = flow.credentials
    
    # Salva ou atualiza as credenciais globais
    creds_dict = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    
    import json
    import os
    secrets_file = os.path.join(settings.BASE_DIR, 'client_secret_337151481642-jne3vmg96u3jnghcm30t68tb4q18os97.apps.googleusercontent.com.json')
    if os.path.exists(secrets_file):
        secrets_data = json.load(open(secrets_file)).get('web', {})
        creds_dict['client_id'] = creds_dict.get('client_id') or secrets_data.get('client_id')
        creds_dict['client_secret'] = creds_dict.get('client_secret') or secrets_data.get('client_secret')
        
    config = YouTubeConfig.get_solo()
    config.credentials = creds_dict
    config.save()
    
    # Após vincular, tenta buscar as informações do canal
    service = YouTubeService()
    service.refresh_service() # Garante que carregou as credenciais novas
    
    print("Tentando buscar canais do YouTube...")
    channels = service.list_channels()
    print(f"Canais retornados: {channels}")
    
    if channels:
        config.channel_id = channels[0]['id']
        config.channel_title = channels[0]['snippet']['title']
        print(f"Salvando canal: {config.channel_title} ({config.channel_id})")
        # Pega a thumbnail de maior resolução disponível
        thumbnails = channels[0]['snippet'].get('thumbnails', {})
        config.channel_thumbnail = thumbnails.get('high', thumbnails.get('default', {})).get('url')
        config.save()
    else:
        print("Nenhum canal localizado para essa conta do Google.")
        
    return redirect('portal_saas_settings')

@csrf_exempt
def live_heartbeat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        name = data.get('name')
        
        if not all([event_id, name]):
            return JsonResponse({'error': 'Incomplete data'}, status=400)
            
        # Update the last_heartbeat for this specific attendance
        attendance = LiveAttendance.objects.filter(
            event_id=event_id, 
            name=name
        ).order_by('-timestamp').first()
        
        if attendance:
            attendance.save() # auto_now will update last_heartbeat
            return JsonResponse({'status': 'ok', 'minutes': attendance.duration_minutes()})
        
        return JsonResponse({'error': 'Attendance not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def live_chat_api(request, event_id):
    event = get_object_or_404(LiveEvent, id=event_id)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            author_name = data.get('author_name', 'Anônimo')
            branch_name = data.get('branch_name', '')
            is_admin = data.get('is_admin', False)
            
            if message:
                msg = LiveChatMessage.objects.create(
                    event=event,
                    author_name=author_name,
                    branch_name=branch_name,
                    message=message,
                    is_admin=is_admin
                )
                return JsonResponse({'status': 'ok', 'id': msg.id})
            return JsonResponse({'error': 'Empty message'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    elif request.method == 'GET':
        last_id = request.GET.get('last_id', 0)
        messages = LiveChatMessage.objects.filter(event=event, id__gt=last_id).order_by('created_at')
        
        msgs_data = []
        for m in messages:
            msgs_data.append({
                'id': m.id,
                'author_name': m.author_name,
                'branch_name': m.branch_name,
                'message': m.message,
                'is_admin': m.is_admin,
                'time': m.created_at.strftime('%H:%M')
            })
            
        return JsonResponse({'status': 'ok', 'messages': msgs_data})

def company_live_dashboard(request, company_slug):
    company = get_object_or_404(Company, slug=company_slug)
    # Busca apenas eventos marcados como públicos e ativos
    lives = LiveEvent.objects.filter(company=company, is_public=True, is_active=True).order_by('-start_time')
    
    context = {
        'company': company,
        'lives': lives,
        'now': timezone.now(),
    }
    return render(request, 'livestream/public_company_dashboard.html', context)

@csrf_exempt
def live_like_api(request, event_id):
    if request.method == 'POST':
        event = get_object_or_404(LiveEvent, id=event_id)
        event.likes_count += 1
        event.save()
        return JsonResponse({'status': 'ok', 'likes': event.likes_count})
    return JsonResponse({'error': 'POST required'}, status=405)

def live_status_api(request, event_id):
    event = get_object_or_404(LiveEvent, id=event_id)
    return JsonResponse({'status': event.status})
