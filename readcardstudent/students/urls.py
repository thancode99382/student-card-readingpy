from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_card, name='upload_card'),
    path('cards/', views.card_list, name='card_list'),
    path('cards/<int:card_id>/', views.card_detail, name='card_detail'),
]