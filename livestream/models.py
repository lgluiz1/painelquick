from django.db import models
from django.utils.text import slugify
from attendance.models import Company, Branch

class LiveEvent(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='live_events')
    title = models.CharField(max_length=255, verbose_name="Título da Live")
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    youtube_url = models.URLField(max_length=500, verbose_name="Link do YouTube")
    start_time = models.DateTimeField(verbose_name="Horário de Início")
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
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
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.event.title}"

    class Meta:
        verbose_name = "Presença em Live"
        verbose_name_plural = "Presenças em Live"
