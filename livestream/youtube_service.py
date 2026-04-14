import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from .models import YouTubeConfig

class YouTubeService:
    SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
    
    def __init__(self, company=None): # company agora é opcional, pois a config é global
        self.config = YouTubeConfig.get_solo()
        self.youtube = self._get_service() if self.config.credentials else None

    def refresh_service(self):
        """Recarrega a configuração do banco e reinicia o serviço."""
        self.config = YouTubeConfig.get_solo()
        self.youtube = self._get_service() if self.config.credentials else None

    def _get_service(self):
        if not self.config or not self.config.credentials:
            return None
        
        creds_data = self.config.credentials
        try:
            # Garante que os campos client_id e client_secret existam para não dar erro
            import json
            import os
            from django.conf import settings
            secrets_file = os.path.join(settings.BASE_DIR, 'client_secret_337151481642-jne3vmg96u3jnghcm30t68tb4q18os97.apps.googleusercontent.com.json')
            if os.path.exists(secrets_file):
                secrets_data = json.load(open(secrets_file)).get('web', {})
                creds_data['client_id'] = creds_data.get('client_id') or secrets_data.get('client_id')
                creds_data['client_secret'] = creds_data.get('client_secret') or secrets_data.get('client_secret')

            creds = google.oauth2.credentials.Credentials.from_authorized_user_info(creds_data, self.SCOPES)
            
            # Check if expired and refresh if necessary
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                # Save updated credentials
                self.config.credentials = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
                self.config.save()
                
            return build('youtube', 'v3', credentials=creds)
        except Exception as e:
            import traceback
            print(f"Erro Crítico no _get_service: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def get_flow(redirect_uri):
        # Path to the JSON file provided by the user
        client_secrets_file = os.path.join(settings.BASE_DIR, 'client_secret_337151481642-jne3vmg96u3jnghcm30t68tb4q18os97.apps.googleusercontent.com.json')
        
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            client_secrets_file,
            scopes=YouTubeService.SCOPES,
            redirect_uri=redirect_uri
        )
        return flow

    def create_live_broadcast(self, title, start_time, description=""):
        if not self.youtube:
            return None
        
        try:
            # 1. Create Broadcast
            broadcast_body = {
                'snippet': {
                    'title': title,
                    'scheduledStartTime': start_time.isoformat(),
                    'description': description,
                },
                'contentDetails': {
                    'enableEmbed': True,
                    'enableAutoStart': True,
                    'enableAutoStop': True,
                    'monitorStream': {
                        'enableMonitorStream': False
                    }
                },
                'status': {
                    'privacyStatus': 'unlisted',
                    'selfDeclaredMadeForKids': False,
                }
            }
            
            broadcast_response = self.youtube.liveBroadcasts().insert(
                part='snippet,status,contentDetails',
                body=broadcast_body
            ).execute()
            
            broadcast_id = broadcast_response['id']
            
            # 2. Create Stream
            stream_body = {
                'snippet': {
                    'title': f"Stream Central - {title}",
                },
                'cdn': {
                    'frameRate': 'variable',
                    'ingestionType': 'rtmp',
                    'resolution': 'variable',
                }
            }
            
            stream_response = self.youtube.liveStreams().insert(
                part='snippet,cdn',
                body=stream_body
            ).execute()
            
            stream_id = stream_response['id']
            stream_key = stream_response['cdn']['ingestionInfo']['streamName']
            
            # 3. Bind Broadcast to Stream
            self.youtube.liveBroadcasts().bind(
                id=broadcast_id,
                part='id,contentDetails',
                streamId=stream_id
            ).execute()
            
            return {
                'broadcast_id': broadcast_id,
                'stream_key': stream_key,
                'youtube_url': f"https://www.youtube.com/watch?v={broadcast_id}"
            }
            
        except HttpError as e:
            print(f"Erro na API do YouTube ao criar: {e}")
            return None

    def update_live_broadcast(self, broadcast_id, title, start_time, description=""):
        if not self.youtube:
            return False
        
        try:
            # Update Broadcast Snippet
            broadcast_body = {
                'id': broadcast_id,
                'snippet': {
                    'title': title,
                    'scheduledStartTime': start_time.isoformat(),
                    'description': description,
                }
            }
            
            self.youtube.liveBroadcasts().update(
                part='snippet',
                body=broadcast_body
            ).execute()
            
            return True
        except HttpError as e:
            print(f"Erro na API do YouTube ao atualizar: {e}")
            return False

    def list_channels(self):
        if not self.youtube: return []
        try:
            response = self.youtube.channels().list(
                part="snippet,contentDetails,statistics",
                mine=True
            ).execute()
            return response.get('items', [])
        except HttpError as e:
            print(f"Erro ao listar canais do YouTube: {e}")
            return []
