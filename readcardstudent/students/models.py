from django.db import models

# Create your models here.
class StudentCard(models.Model):
    image = models.ImageField(upload_to='student_cards/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    university = models.CharField(max_length=255, null=True, blank=True)
    student_card_type = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    dob = models.CharField(max_length=50, null=True, blank=True)
    student_id = models.CharField(max_length=50, null=True, blank=True)
    class_name = models.CharField(max_length=50, null=True, blank=True)
    cohort = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return f"StudentCard {self.id} - {self.name or 'Unknown'}"