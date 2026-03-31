from django.db import models
import secrets

class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome da Empresa")
    slug = models.SlugField(max_length=255, unique=True)
    api_token = models.CharField(max_length=100, unique=True, blank=True)
    
    # Customização
    logo_url = models.URLField(max_length=500, null=True, blank=True)
    primary_color = models.CharField(max_length=20, default="#e63946")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.api_token:
            self.api_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100, verbose_name="Nome da Filial")

    def __str__(self):
        return f"{self.company.name} - {self.name}"

    class Meta:
        verbose_name = "Filial"
        verbose_name_plural = "Filiais"
        unique_together = ('company', 'name')

class Meeting(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='meetings', null=True)
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Reunião"
        verbose_name_plural = "Reuniões"

class Attendance(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='attendances')
    name = models.CharField(max_length=255)
    branch = models.CharField(max_length=100) # Mantido como texto para compatibilidade, mas pode vir do model Branch
    signature = models.TextField()  # Store Base64 string
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.meeting.title}"

    class Meta:
        verbose_name = "Presença"
        verbose_name_plural = "Presenças"

# --- Novos modelos para Cursos e Avaliações ---

class Course(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='courses', null=True)
    title = models.CharField(max_length=255, verbose_name="Título do Curso")
    slug = models.SlugField(max_length=255, verbose_name="Slug (URL)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        unique_together = ('company', 'slug')

class Evaluation(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='evaluations')
    title = models.CharField(max_length=255, verbose_name="Título da Avaliação/Módulo")
    is_active = models.BooleanField(default=False, verbose_name="Ativo?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    class Meta:
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"

class Question(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField(verbose_name="Texto da Pergunta")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordem")

    def __str__(self):
        return f"Q: {self.text[:50]}"

    class Meta:
        ordering = ['order']
        verbose_name = "Pergunta"
        verbose_name_plural = "Perguntas"

class StudentResponse(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='student_responses')
    name = models.CharField(max_length=255)
    branch = models.CharField(max_length=100)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.evaluation.title}"

    class Meta:
        verbose_name = "Resposta de Aluno"
        verbose_name_plural = "Respostas de Alunos"

class StudentAnswer(models.Model):
    response = models.ForeignKey(StudentResponse, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()

    def __str__(self):
        return f"Ans for {self.question.id}"

    class Meta:
        verbose_name = "Resposta da Pergunta"
        verbose_name_plural = "Respostas das Perguntas"

# --- Novos modelos para Ouvidoria (Denúncias) ---

class ComplaintCategory(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='complaint_categories', null=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Categoria de Denúncia"
        verbose_name_plural = "Categorias de Denúncias"
        unique_together = ('company', 'name')

class UrgencyLevel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='urgency_levels', null=True)
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default="#6c757d") # CSS Color (Ex: #dc3545)

    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ('company', 'name')

class Complaint(models.Model):
    STATUS_CHOICES = [
        ('novo', 'Novo'),
        ('em_analise', 'Em Análise'),
        ('resolvido', 'Resolvido'),
        ('arquivado', 'Arquivado'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='complaints', null=True)
    ticket_id = models.CharField(max_length=20, unique=True) # Ex: QUICK-XXXXX
    category = models.ForeignKey(ComplaintCategory, on_delete=models.SET_NULL, null=True, blank=True)
    urgency = models.ForeignKey(UrgencyLevel, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Identificação opcional
    is_anonymous = models.BooleanField(default=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    branch = models.CharField(max_length=100) # Filial (sempre obrigatório para saber onde resolver)
    
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='novo')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket {self.ticket_id} - {self.status}"

    class Meta:
        verbose_name = "Denúncia"
        verbose_name_plural = "Denúncias"

class ComplaintUpdate(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='updates')
    message = models.TextField()
    is_from_admin = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Update on {self.complaint.ticket_id}"

    class Meta:
        verbose_name = "Atualização de Denúncia"
        verbose_name_plural = "Atualizações de Denúncias"
