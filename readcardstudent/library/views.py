from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse

from .models import Book, BorrowRecord, Reservation, BookCategory
from students.models import StudentCard
from .forms import BookSearchForm, BorrowBookForm, ReturnBookForm, ReservationForm

def is_staff_user(user):
    """Check if user is staff"""
    return user.is_staff

def library_admin_login(request):
    """View for library login - serves both admin and regular users"""
    # If user is already authenticated, redirect appropriately
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('library_admin_dashboard')
        else:
            return redirect('library_home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            
            # Redirect staff users to the admin dashboard, regular users to the library home
            if user.is_staff:
                return redirect('library_admin_dashboard')
            else:
                return redirect('library_home')
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, 'library/admin_login.html')

@login_required(login_url='library_admin_login')
@user_passes_test(is_staff_user, login_url='library_admin_login')
def library_admin_dashboard(request):
    """Admin dashboard for library management"""
    today = timezone.now().date()
    
    # Get statistics for the dashboard
    total_books = Book.objects.count()
    available_books = Book.objects.filter(available_copies__gt=0).count()
    total_students = StudentCard.objects.count()
    
    # Active students have at least one active borrow
    active_students = StudentCard.objects.filter(
        id__in=BorrowRecord.objects.filter(status__in=['borrowed', 'overdue']).values('student')
    ).distinct().count()
    
    # Borrow statistics
    borrowed_books = BorrowRecord.objects.filter(status__in=['borrowed', 'overdue']).count()
    borrowed_today = BorrowRecord.objects.filter(
        borrowed_date__date=today
    ).count()
    
    # Overdue statistics
    overdue_books = BorrowRecord.objects.filter(status='overdue').count()
    total_fines = BorrowRecord.objects.filter(status__in=['borrowed', 'overdue']).aggregate(
        total=Sum('fine_amount')
    )['total'] or 0
    
    # Recent borrows
    recent_borrows = BorrowRecord.objects.filter(
        status__in=['borrowed', 'overdue']
    ).select_related('book', 'student').order_by('-borrowed_date')[:5]
    
    # Overdue borrows with days calculation
    overdue_borrows = BorrowRecord.objects.filter(status='overdue').select_related('book', 'student')
    
    for borrow in overdue_borrows:
        # Calculate days overdue
        borrow.days_overdue = (timezone.now().date() - borrow.due_date).days
    
    context = {
        'total_books': total_books,
        'available_books': available_books,
        'total_students': total_students,
        'active_students': active_students,
        'borrowed_books': borrowed_books,
        'borrowed_today': borrowed_today,
        'overdue_books': overdue_books,
        'total_fines': total_fines,
        'recent_borrows': recent_borrows,
        'overdue_borrows': overdue_borrows[:10],  # Limit to 10 most overdue books
    }
    
    return render(request, 'library/admin_dashboard.html', context)

@login_required(login_url='library_admin_login')
def library_admin_logout(request):
    """Logout view for library admin"""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('library_home')

@login_required(login_url='library_admin_login')
def library_home(request):
    """Home page view for the library"""
    recent_books = Book.objects.filter(available_copies__gt=0).order_by('-added_on')[:6]
    popular_books = Book.objects.filter(available_copies__gt=0).order_by('?')[:6]  # Random selection for demo
    categories = BookCategory.objects.all()
    
    context = {
        'recent_books': recent_books,
        'popular_books': popular_books,
        'categories': categories,
        'total_books': Book.objects.count(),
        'available_books': Book.objects.filter(available_copies__gt=0).count(),
    }
    return render(request, 'library/home.html', context)

@login_required(login_url='library_admin_login')
def book_list(request):
    """View for displaying all books with search and filter options"""
    form = BookSearchForm(request.GET)
    books = Book.objects.all()
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        category = form.cleaned_data.get('category')
        availability = form.cleaned_data.get('availability')
        
        # Apply filters
        if query:
            books = books.filter(
                Q(title__icontains=query) | 
                Q(author__icontains=query) | 
                Q(isbn__icontains=query)
            )
        
        if category:
            books = books.filter(categories=category)
            
        if availability == 'available':
            books = books.filter(available_copies__gt=0)
        elif availability == 'unavailable':
            books = books.filter(available_copies=0)
    
    # Pagination
    paginator = Paginator(books.order_by('title'), 12)  # Show 12 books per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'categories': BookCategory.objects.all(),
    }
    return render(request, 'library/book_list.html', context)

@login_required(login_url='library_admin_login')
def book_detail(request, book_id):
    """View for displaying details of a specific book"""
    book = get_object_or_404(Book, id=book_id)
    
    # Check if there are any active borrowing records for this book
    active_borrows = BorrowRecord.objects.filter(
        book=book, 
        status__in=['borrowed', 'overdue']
    ).select_related('student')
    
    # Check if there are any pending reservations for this book
    pending_reservations = Reservation.objects.filter(
        book=book, 
        status='pending'
    ).select_related('student')
    
    context = {
        'book': book,
        'active_borrows': active_borrows,
        'pending_reservations': pending_reservations,
    }
    return render(request, 'library/book_detail.html', context)

@login_required(login_url='library_admin_login')
def student_detail(request, student_id):
    """View for displaying a student's library activities"""
    student = get_object_or_404(StudentCard, id=student_id)
    
    # Get active borrows
    active_borrows = BorrowRecord.objects.filter(
        student=student, 
        status__in=['borrowed', 'overdue']
    ).select_related('book')
    
    # Get borrow history
    borrow_history = BorrowRecord.objects.filter(
        student=student
    ).order_by('-borrowed_date')
    
    # Get active reservations
    active_reservations = Reservation.objects.filter(
        student=student, 
        status='pending'
    ).select_related('book')
    
    # Calculate total fine
    total_fine = sum(borrow.fine_amount for borrow in active_borrows if borrow.fine_amount > 0)
    
    context = {
        'student': student,
        'active_borrows': active_borrows,
        'borrow_history': borrow_history,
        'active_reservations': active_reservations,
        'total_fine': total_fine,
    }
    return render(request, 'library/student_detail.html', context)

@login_required(login_url='library_admin_login')
def scan_student_card(request):
    """View for scanning a student card to access library services"""
    if request.method == 'POST' and request.FILES.get('card_image'):
        # This will use the existing card reading functionality from the students app
        from students.views import upload_card  
        return upload_card(request, redirect_to='library_student_verification')
    
    return render(request, 'library/scan_card.html')

@login_required(login_url='library_admin_login')
def student_verification(request):
    """View for verifying a student after card scanning"""
    # Get the latest processed student card (assumes this was just created by scan_student_card)
    try:
        student = StudentCard.objects.latest('uploaded_at')
        
        if not student.student_id:
            messages.error(request, "Failed to extract student ID from the card. Please try again.")
            return redirect('library_scan_card')
        
        # Check if this student has any overdue books or unpaid fines
        overdue_books = BorrowRecord.objects.filter(
            student=student, 
            status__in=['borrowed', 'overdue'], 
            due_date__lt=timezone.now()
        )
        
        if overdue_books.exists():
            messages.warning(request, 
                f"You have {overdue_books.count()} overdue book(s). Please return them soon.")
            
        # Redirect to the student's detail page
        return redirect('library_student_detail', student_id=student.id)
        
    except StudentCard.DoesNotExist:
        messages.error(request, "No student card was found. Please scan your card again.")
        return redirect('library_scan_card')

@login_required(login_url='library_admin_login')
def borrow_book(request, book_id):
    """View for borrowing a book"""
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == 'POST':
        form = BorrowBookForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student_id']
            
            try:
                student = StudentCard.objects.get(student_id=student_id)
                
                # Check if book is available
                if book.available_copies <= 0:
                    messages.error(request, "This book is not available for borrowing.")
                    return redirect('library_book_detail', book_id=book.id)
                
                # Check if student already has this book
                if BorrowRecord.objects.filter(student=student, book=book, status__in=['borrowed', 'overdue']).exists():
                    messages.error(request, "This student already has this book.")
                    return redirect('library_book_detail', book_id=book.id)
                
                # Create borrowing record
                borrow = BorrowRecord(student=student, book=book, status='borrowed')
                borrow.save()
                
                messages.success(request, f"Book '{book.title}' has been borrowed successfully by {student.name}.")
                return redirect('library_student_detail', student_id=student.id)
                
            except StudentCard.DoesNotExist:
                messages.error(request, "Student ID not found. Please check the ID and try again.")
    else:
        form = BorrowBookForm()
    
    context = {
        'form': form,
        'book': book,
    }
    return render(request, 'library/borrow_book.html', context)

@login_required(login_url='library_admin_login')
def return_book(request, borrow_id=None):
    """View for returning a borrowed book"""
    if borrow_id:
        borrow_record = get_object_or_404(BorrowRecord, id=borrow_id)
        
        if request.method == 'POST':
            form = ReturnBookForm(request.POST, instance=borrow_record)
            if form.is_valid():
                # Update the borrow record
                borrow_record = form.save(commit=False)
                borrow_record.status = 'returned'
                borrow_record.return_date = timezone.now()
                borrow_record.save()
                
                # Check if there are any pending reservations for this book
                pending_reservations = Reservation.objects.filter(
                    book=borrow_record.book,
                    status='pending'
                ).order_by('reservation_date')
                
                if pending_reservations.exists():
                    # Mark the oldest reservation as fulfilled
                    reservation = pending_reservations.first()
                    reservation.status = 'fulfilled'
                    reservation.save()
                    messages.info(request, f"This book was reserved by another student ({reservation.student.name}).")
                
                messages.success(request, f"Book '{borrow_record.book.title}' has been returned successfully.")
                return redirect('library_student_detail', student_id=borrow_record.student.id)
        else:
            form = ReturnBookForm(instance=borrow_record)
            
        context = {
            'form': form,
            'borrow_record': borrow_record,
        }
        return render(request, 'library/return_book.html', context)
    
    # If no borrow_id is provided, show a form to search for a borrow record
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        student_id = request.POST.get('student_id')
        
        try:
            book = Book.objects.get(isbn=book_id)
            student = StudentCard.objects.get(student_id=student_id)
            
            borrow_record = BorrowRecord.objects.filter(
                book=book,
                student=student,
                status__in=['borrowed', 'overdue']
            ).first()
            
            if borrow_record:
                return redirect('library_return_book', borrow_id=borrow_record.id)
            else:
                messages.error(request, "No active borrowing record found for this book and student.")
        except (Book.DoesNotExist, StudentCard.DoesNotExist):
            messages.error(request, "Book or student not found. Please check the details and try again.")
    
    return render(request, 'library/find_borrowed_book.html')

@login_required(login_url='library_admin_login')
def reserve_book(request, book_id):
    """View for reserving a book"""
    book = get_object_or_404(Book, id=book_id)
    
    # Check if book is already available
    if book.available_copies > 0:
        messages.info(request, "This book is currently available. You can borrow it directly.")
        return redirect('library_borrow_book', book_id=book.id)
    
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data['student_id']
            
            try:
                student = StudentCard.objects.get(student_id=student_id)
                
                # Check if student already has a pending reservation for this book
                if Reservation.objects.filter(student=student, book=book, status='pending').exists():
                    messages.error(request, "You already have a pending reservation for this book.")
                    return redirect('library_book_detail', book_id=book.id)
                
                # Create reservation record
                reservation = Reservation(
                    student=student,
                    book=book,
                    status='pending',
                    expiry_date=timezone.now() + timezone.timedelta(days=3)
                )
                reservation.save()
                
                messages.success(request, f"Book '{book.title}' has been reserved successfully.")
                return redirect('library_student_detail', student_id=student.id)
                
            except StudentCard.DoesNotExist:
                messages.error(request, "Student ID not found. Please check the ID and try again.")
    else:
        form = ReservationForm()
    
    context = {
        'form': form,
        'book': book,
    }
    return render(request, 'library/reserve_book.html', context)

@login_required(login_url='library_admin_login')
def cancel_reservation(request, reservation_id):
    """View for cancelling a book reservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if request.method == 'POST':
        student_id = reservation.student.id
        book_title = reservation.book.title
        
        reservation.status = 'cancelled'
        reservation.save()
        
        messages.success(request, f"Reservation for '{book_title}' has been cancelled.")
        return redirect('library_student_detail', student_id=student_id)
    
    return render(request, 'library/cancel_reservation.html', {'reservation': reservation})