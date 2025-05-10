from django import forms
from .models import BookCategory, BorrowRecord, Reservation

class BookSearchForm(forms.Form):
    query = forms.CharField(required=False, label="Search",
                           widget=forms.TextInput(attrs={'placeholder': 'Search by title, author, or ISBN...', 
                                                       'class': 'form-control'}))
    category = forms.ModelChoiceField(
        queryset=BookCategory.objects.all(),
        required=False,
        label="Category",
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    AVAILABILITY_CHOICES = (
        ('', 'All Books'),
        ('available', 'Available Books'),
        ('unavailable', 'Unavailable Books'),
    )
    availability = forms.ChoiceField(
        choices=AVAILABILITY_CHOICES,
        required=False,
        label="Availability",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class BorrowBookForm(forms.Form):
    student_id = forms.CharField(
        max_length=20, 
        label="Student ID",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter student ID'})
    )
    days = forms.IntegerField(
        initial=14,
        min_value=1,
        max_value=30,
        label="Borrowing Period (days)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add any notes here...'}),
        label="Notes"
    )

class ReturnBookForm(forms.ModelForm):
    class Meta:
        model = BorrowRecord
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add any notes about the condition of the returned book...'}),
        }

class ReservationForm(forms.Form):
    student_id = forms.CharField(
        max_length=20, 
        label="Student ID",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter student ID'})
    )
    notes = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add any notes here...'}),
        label="Notes"
    )