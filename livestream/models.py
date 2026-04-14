from django.db import models
from django.utils.text import slugify
from attendance.models import Company, Branch

class LiveEvent(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='live_events')
    title = models.CharField(max_length=255, verbose_name="Título da Live")
    description = models.TextField(null=True, blank=True, verbose_name="Descrição/Texto Base")
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    youtube_url = models.URLField(max_length=500, verbose_name="Link do YouTube")
    start_time = models.DateTimeField(verbose_name="Horário de Início")
    STATUS_CHOICES = [
        ('waiting', 'Sala de Espera'),
        ('live', 'Ao Vivo'),
        ('finished', 'Encerrada')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    likes_count = models.IntegerField(default=0, verbose_name="Curtidas")
    is_public = models.BooleanField(default=False, verbose_name="Exibir no Dashboard Público?")
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while LiveEvent.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.name} - {self.title}"

    class Meta:
        verbose_name = "Evento ao Vivo"
        verbose_name_plural = "Eventos ao Vivo"

class LiveAttendance(models.Model):
    event = models.ForeignKey(LiveEvent, on_delete=models.CASCADE, related_name='attendances')
    name = models.CharField(max_length=255, verbose_name="Nome completo")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name="Filial")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Entrada")
    last_heartbeat = models.DateTimeField(auto_now=True, verbose_name="Último Sinal")
    is_confirmed = models.BooleanField(default=False, verbose_name="Presença Confirmada (Oficial)")

    def duration_minutes(self):
        if self.last_heartbeat and self.timestamp:
            diff = self.last_heartbeat - self.timestamp
            return int(diff.total_seconds() / 60)
        return 0

    def is_online(self):
        if not self.last_heartbeat:
            return False
        from django.utils import timezone
        diff = timezone.now() - self.last_heartbeat
        return diff.total_seconds() < 120 # Se recebeu heartbeat nos últimos 2 minutos

    def __str__(self):
        return f"{self.name} - {self.event.title}"

    class Meta:
        verbose_name = "Presença em Live"
        verbose_name_plural = "Presenças em Live"

class LiveChatMessage(models.Model):
    event = models.ForeignKey(LiveEvent, on_delete=models.CASCADE, related_name='chat_messages')
    author_name = models.CharField(max_length=150)
    branch_name = models.CharField(max_length=100)
    message = models.TextField()
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem do Chat"
        verbose_name_plural = "Mensagens do Chat"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author_name}: {self.message[:20]}"

class YouTubeConfig(models.Model):
    # Removido vinculo com Company para ser Global (Capelão)
    credentials = models.JSONField(verbose_name="Credenciais Google (JSON)")
    channel_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="ID do Canal")
    channel_title = models.CharField(max_length=255, null=True, blank=True, verbose_name="Título do Canal")
    channel_thumbnail = models.URLField(max_length=500, null=True, blank=True, verbose_name="Thumbnail do Canal")
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config YouTube Global - {self.channel_title or 'Pendente'}"

    class Meta:
        verbose_name = "Configuração YouTube Global"
        verbose_name_plural = "Configurações YouTube Global"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1, defaults={'credentials': {}})
        return obj
