from django.db import models
from django.contrib.auth.models import User
import secrets

class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrador Master'),
        ('OUVIDOR', 'Analista de Ouvidoria'),
        ('CONTEUDISTA', 'Gestor de Conteúdo'),
        ('AUDITOR', 'Auditor de Relatórios'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='OUVIDOR')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    class Meta:
        verbose_name = "Perfil de Equipe"
        verbose_name_plural = "Perfis de Equipe"

class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome da Empresa")
    slug = models.SlugField(max_length=255, unique=True)
    api_token = models.CharField(max_length=100, unique=True, blank=True)
    
    # Customização
    logo_url = models.URLField(max_length=500, null=True, blank=True)
    primary_color = models.CharField(max_length=20, default="#e63946")
    is_active = models.BooleanField(default=True)
    
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
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="Horário da Reunião")
    is_youtube_live = models.BooleanField(default=False, verbose_name="Agendar no YouTube?")
    youtube_broadcast_id = models.CharField(max_length=100, null=True, blank=True)
    youtube_stream_key = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True, verbose_name="Descrição (Suporta Emojis)")
    
    # Vincular ao evento de live para monitoramento de heartbeat
    live_event = models.OneToOneField('livestream.LiveEvent', on_delete=models.SET_NULL, null=True, blank=True, related_name='reunion_meeting')
    
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
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Data/Hora de Fechamento")
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
    is_read = models.BooleanField(default=False, verbose_name="Lida?")
    
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
class Lead(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Nome")
    last_name = models.CharField(max_length=100, verbose_name="Sobrenome")
    email = models.EmailField(verbose_name="E-mail")
    phone = models.CharField(max_length=20, verbose_name="Telefone")
    company = models.CharField(max_length=255, verbose_name="Empresa")
    message = models.TextField(verbose_name="Mensagem")
    is_read = models.BooleanField(default=False, verbose_name="Lida?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company}"

    class Meta:
        verbose_name = "Lead / Contato Site"
        verbose_name_plural = "Leads / Contatos Site"

class GalleryImage(models.Model):
    image = models.ImageField(upload_to='gallery/', verbose_name="Imagem")
    caption = models.CharField(max_length=255, blank=True, verbose_name="Legenda")
    is_active = models.BooleanField(default=True, verbose_name="Ativa?")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            from PIL import Image
            img = Image.open(self.image.path)
            
            # Tamanho padrão do site: 800x600 (4:3) para manter harmonia
            target_width = 800
            target_height = 600
            
            # Redimensionamento inteligente (Crop & Resize)
            width, height = img.size
            target_ratio = target_width / target_height
            current_ratio = width / height

            if current_ratio > target_ratio:
                # Muito largo, corta as laterais
                new_width = int(target_ratio * height)
                offset = (width - new_width) / 2
                img = img.crop((offset, 0, width - offset, height))
            elif current_ratio < target_ratio:
                # Muito alto, corta o topo/fundo
                new_height = int(width / target_ratio)
                offset = (height - new_height) / 2
                img = img.crop((0, offset, width, height - offset))
            
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            img.save(self.image.path, quality=85, optimize=True)

    class Meta:
        verbose_name = "Foto da Galeria"
        verbose_name_plural = "Fotos da Galeria"
        ordering = ['order', '-created_at']

class Testimonial(models.Model):
    company_related = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_testimonials')
    name = models.CharField(max_length=150, verbose_name="Nome do Colaborador")
    role = models.CharField(max_length=150, verbose_name="Cargo")
    company_name = models.CharField(max_length=150, verbose_name="Empresa")
    message = models.TextField(verbose_name="Depoimento")
    photo = models.ImageField(upload_to='testimonials/', null=True, blank=True, verbose_name="Foto de Perfil")
    is_approved = models.BooleanField(default=False, verbose_name="Aprovado?")
    show_on_home = models.BooleanField(default=False, verbose_name="Exibir na Home?")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.photo:
            from PIL import Image
            img = Image.open(self.photo.path)
            if img.height > 300 or img.width > 300:
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                img.save(self.photo.path, quality=85)

    def __str__(self):
        return f"{self.name} ({self.company_name})"

    class Meta:
        verbose_name = "Depoimento"
        verbose_name_plural = "Depoimentos"

class FAQItem(models.Model):
    question = models.CharField(max_length=255, verbose_name="Pergunta")
    answer = models.TextField(verbose_name="Resposta")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = "Item de FAQ"
        verbose_name_plural = "Itens de FAQ"
        ordering = ['order']

class GlobalConfig(models.Model):
    whatsapp_number = models.CharField(max_length=20, default="5543996404350", verbose_name="WhatsApp do Capelão")
    contact_email = models.EmailField(default="contato@exemplo.com", verbose_name="E-mail de Contato Exibido")
    notify_email = models.EmailField(default="admin@exemplo.com", verbose_name="E-mail que recebe notificações")
    
    # Campo para endereço ou outra info que queira dinamizar
    
    address = models.TextField(default="Av. Des. Mário da Silva Nunes, 717 - Jardim Limoeiro, Serra - ES, 29164-044", verbose_name="Endereço no Rodapé")
    formation_year = models.IntegerField(default=2004, verbose_name="Ano de Formação na Capelania")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Configurações Globais do Portal"

    class Meta:
        verbose_name = "Configuração Global"
        verbose_name_plural = "Configurações Globais"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj
