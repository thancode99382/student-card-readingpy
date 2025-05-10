from django.contrib import admin
from .models import BookCategory, Book, BorrowRecord, Reservation, LibrarySettings

@admin.register(BookCategory)
class BookCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'publication_year', 'available_copies', 'total_copies')
    list_filter = ('categories', 'publication_year')
    search_fields = ('title', 'author', 'isbn')
    filter_horizontal = ('categories',)
    readonly_fields = ('added_on',)

@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'book', 'borrowed_date', 'due_date', 'return_date', 'status', 'fine_amount')
    list_filter = ('status', 'borrowed_date')
    search_fields = ('student__name', 'student__student_id', 'book__title')
    readonly_fields = ('borrowed_date',)
    
    def save_model(self, request, obj, form, change):
        # Auto-update the fine amount when saving in admin
        if obj.status in ['borrowed', 'overdue'] and obj.is_overdue():
            obj.fine_amount = obj.calculate_fine()
            if obj.status == 'borrowed':
                obj.status = 'overdue'
        super().save_model(request, obj, form, change)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('student', 'book', 'reservation_date', 'expiry_date', 'status', 'notified')
    list_filter = ('status', 'reservation_date')
    search_fields = ('student__name', 'student__student_id', 'book__title')
    readonly_fields = ('reservation_date',)

@admin.register(LibrarySettings)
class LibrarySettingsAdmin(admin.ModelAdmin):
    list_display = ('setting_name', 'setting_value', 'description')
    search_fields = ('setting_name',)