from django.urls import path
from . import views

urlpatterns = [
    # Login/Authentication URLs
    path('', views.library_admin_login, name='library_admin_login'),
    path('home/', views.library_home, name='library_home'),
    path('admin/dashboard/', views.library_admin_dashboard, name='library_admin_dashboard'),
    path('logout/', views.library_admin_logout, name='library_admin_logout'),
    
    # Book related URLs
    path('books/', views.book_list, name='library_book_list'),
    path('books/<int:book_id>/', views.book_detail, name='library_book_detail'),
    path('students/<int:student_id>/', views.student_detail, name='library_student_detail'),
    path('scan-card/', views.scan_student_card, name='library_scan_card'),
    path('verification/', views.student_verification, name='library_student_verification'),
    path('borrow/<int:book_id>/', views.borrow_book, name='library_borrow_book'),
    path('return/', views.return_book, name='library_return_book'),
    path('return/<int:borrow_id>/', views.return_book, name='library_return_specific_book'),
    path('reserve/<int:book_id>/', views.reserve_book, name='library_reserve_book'),
    path('cancel-reservation/<int:reservation_id>/', views.cancel_reservation, name='library_cancel_reservation'),
]