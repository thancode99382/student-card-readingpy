from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
import os
import uuid

from .models import StudentCard
from .utils import StudentCardProcessor

def home(request):
    """Home page view"""
    return render(request, 'students/home.html')

def upload_card(request, redirect_to=None):
    """View for handling card uploads
    
    Args:
        request: HttpRequest object
        redirect_to: Optional name of URL to redirect to after processing
    """
    if request.method == 'POST' and request.FILES.get('card_image'):
        # Get the uploaded image
        image_file = request.FILES['card_image']
        
        # Save the model with image
        student_card = StudentCard(image=image_file)
        student_card.save()
        
        # Get the file path of the saved image
        image_path = student_card.image.path
        
        # Process the student card image
        processor = StudentCardProcessor()
        info, original, processed, visualization = processor.process_student_card(image_path)
        
        if info:
            # Update the model with extracted information
            student_card.university = info.get('university')
            student_card.student_card_type = info.get('student_card')
            student_card.name = info.get('name')
            student_card.dob = info.get('dob')
            student_card.student_id = info.get('student_id')
            student_card.class_name = info.get('class')
            student_card.cohort = info.get('cohort')
            student_card.save()
            
            # Generate unique filename for visualizations
            base_filename = f"card_{student_card.id}_{uuid.uuid4().hex[:8]}"
            vis_paths = processor.save_visualization(original, processed, visualization, base_filename)
            
            # Handle custom redirect if provided
            if redirect_to:
                return redirect(redirect_to)
            
            # Default behavior - render result template
            context = {
                'student_card': student_card,
                'visualizations': vis_paths,
                'success': True
            }
            
            return render(request, 'students/result.html', context)
        else:
            # If processing failed, show error
            messages.error(request, "Failed to process the student card. Please try again with a clearer image.")
            student_card.delete()  # Delete the failed record
            
    return render(request, 'students/upload.html')

def card_list(request):
    """View for displaying all processed cards"""
    cards = StudentCard.objects.all().order_by('-uploaded_at')
    return render(request, 'students/card_list.html', {'cards': cards})

def card_detail(request, card_id):
    """View for displaying details of a specific card"""
    try:
        card = StudentCard.objects.get(id=card_id)
        return render(request, 'students/card_detail.html', {'card': card})
    except StudentCard.DoesNotExist:
        messages.error(request, "Student card not found.")
        return redirect('card_list')
