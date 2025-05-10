from django.contrib import admin
from .models import StudentCard

@admin.register(StudentCard)
class StudentCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'student_id', 'university', 'uploaded_at')
    search_fields = ('name', 'student_id')
    list_filter = ('university', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
