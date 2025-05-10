from django.db import models
from students.models import StudentCard
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

class BookCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Book Categories"

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField("ISBN", max_length=20, unique=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publication_year = models.IntegerField(blank=True, null=True)
    categories = models.ManyToManyField(BookCategory, related_name="books")
    description = models.TextField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    location_shelf = models.CharField(max_length=50, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} by {self.author}"
    
    def is_available(self):
        return self.available_copies > 0
    
    def save(self, *args, **kwargs):
        # Ensure available copies doesn't exceed total copies
        if self.available_copies > self.total_copies:
            self.available_copies = self.total_copies
        super().save(*args, **kwargs)

class BorrowRecord(models.Model):
    STATUS_CHOICES = (
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
    )
    
    student = models.ForeignKey(StudentCard, on_delete=models.CASCADE, related_name='borrow_records')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrow_records')
    borrowed_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='borrowed')
    fine_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.book.title} - {self.student.name} ({self.status})"
    
    def clean(self):
        # Check if the book is available for borrowing
        if self.status == 'borrowed' and self.book.available_copies <= 0:
            raise ValidationError("This book is not available for borrowing.")
    
    def save(self, *args, **kwargs):
        # Set default due date if not provided (14 days from borrowing)
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=14)
            
        # If this is a new record (borrowing), decrease available copies
        if not self.pk and self.status == 'borrowed':
            self.book.available_copies -= 1
            self.book.save()
            
        # If status changed to returned, increase available copies
        if self.pk:
            old_record = BorrowRecord.objects.get(pk=self.pk)
            if old_record.status != 'returned' and self.status == 'returned':
                self.return_date = timezone.now()
                self.book.available_copies += 1
                self.book.save()
                
        super().save(*args, **kwargs)
    
    def is_overdue(self):
        if self.status == 'borrowed' and timezone.now() > self.due_date:
            return True
        return False
    
    def calculate_fine(self, fine_rate=0.50):
        """Calculate fine based on overdue days (default 50 cents per day)"""
        if self.status != 'returned' and timezone.now() > self.due_date:
            overdue_days = (timezone.now() - self.due_date).days
            if overdue_days > 0:
                return round(overdue_days * fine_rate, 2)
        return 0.00

class Reservation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    
    student = models.ForeignKey(StudentCard, on_delete=models.CASCADE, related_name='reservations')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reservations')
    reservation_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.book.title} reserved by {self.student.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Set default expiry date if not provided (3 days from reservation)
        if not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=3)
        super().save(*args, **kwargs)

class LibrarySettings(models.Model):
    setting_name = models.CharField(max_length=100, unique=True)
    setting_value = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.setting_name
    
    class Meta:
        verbose_name_plural = "Library Settings"