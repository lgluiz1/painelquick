from django.db import models

class Meeting(models.Model):
    title = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Reunião"
        verbose_name_plural = "Reuniões"

class Attendance(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='attendances')
    name = models.CharField(max_length=255)
    branch = models.CharField(max_length=100)
    signature = models.TextField()  # Store Base64 string
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.meeting.title}"

    class Meta:
        verbose_name = "Presença"
        verbose_name_plural = "Presenças"
