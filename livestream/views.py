from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import LiveEvent, LiveAttendance
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
    
    # Check if user has already signed attendance for THIS session
    session_key = f'attended_event_{event.id}'
    has_attended = request.session.get(session_key, False)
    
    # Check if event has started
    now = timezone.now()
    has_started = now >= event.start_time
    
    youtube_id = get_youtube_id(event.youtube_url)
    
    context = {
        'company': company,
        'event': event,
        'has_attended': has_attended,
        'has_started': has_started,
        'youtube_id': youtube_id,
        'branches': company.branches.all().order_by('name'),
        'now': now,
    }
    
    return render(request, 'livestream/event_detail.html', context)

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
        LiveAttendance.objects.create(
            event=event,
            name=name,
            branch=branch
        )
        
        # Mark in session
        request.session[f'attended_event_{event.id}'] = True
        
        return JsonResponse({'status': 'success', 'message': 'Presença confirmada! Aproveite a live.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
