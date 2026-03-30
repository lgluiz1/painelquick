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

# --- Novos modelos para Cursos e Avaliações ---

class Course(models.Model):
    title = models.CharField(max_length=255, unique=True, verbose_name="Título do Curso")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug (URL)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"

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
