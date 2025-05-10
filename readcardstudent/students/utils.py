import cv2
import numpy as np
import pytesseract
import re
import os
from django.conf import settings
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use Agg backend to avoid GUI dependency

class StudentCardProcessor:
    def __init__(self):
        """Initialize the processor with multiple OCR configurations"""
        # Configure pytesseract path if running on Windows
        # Uncomment and modify this if needed
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # Configure pytesseract for Vietnamese language with various PSM modes
        self.config_default = r'--oem 3 --psm 6 -l vie'  # Default - Assume a single uniform block of text
        self.config_sparse = r'--oem 3 --psm 11 -l vie'  # Sparse text - Find as much text as possible without assuming structure
        self.config_single_line = r'--oem 3 --psm 7 -l vie'  # Single line - Treat the image as a single text line
    
    def apply_preprocessing_methods(self, image):
        """Apply multiple preprocessing techniques and return results
        
        Returns:
            List of preprocessed images with different techniques
        """
        # Make a copy of the original image
        img = image.copy()
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Method 2: Otsu's thresholding
        _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Method 3: Histogram equalization
        equalized = cv2.equalizeHist(gray)
        _, equalized_thresh = cv2.threshold(equalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Method 4: Bilateral filtering to reduce noise while preserving edges
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        _, bilateral_thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Method 5: Morphological operations
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(otsu_thresh, cv2.MORPH_CLOSE, kernel)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
        
        # Method 6: Edge enhancement
        edges = cv2.Canny(gray, 100, 200)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        edge_enhanced = cv2.bitwise_and(gray, gray, mask=dilated_edges)
        _, edge_thresh = cv2.threshold(edge_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Return the processed images
        return [
            adaptive_thresh,
            otsu_thresh,
            equalized_thresh,
            bilateral_thresh,
            morph,
            edge_thresh
        ]
    
    def detect_text_regions(self, image):
        """Detect potential text regions in the image"""
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours based on area and aspect ratio
        text_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            aspect_ratio = w / float(h)
            
            # Filter out very small or very large regions
            if area > 200 and area < gray.shape[0] * gray.shape[1] * 0.5:
                # Filter based on aspect ratio (typical text regions aren't too wide or too tall)
                if 0.1 < aspect_ratio < 10:
                    text_regions.append((x, y, w, h))
        
        return text_regions
    
    def apply_ocr_with_multiple_configs(self, image):
        """Apply OCR with multiple configurations and combine results"""
        # Apply OCR with different configurations
        text_default = pytesseract.image_to_string(image, config=self.config_default)
        text_sparse = pytesseract.image_to_string(image, config=self.config_sparse)
        text_single_line = pytesseract.image_to_string(image, config=self.config_single_line)
        
        # Combine all texts for comprehensive analysis
        combined_text = text_default + "\n" + text_sparse + "\n" + text_single_line
        
        return combined_text
    
    def extract_card_info(self, image):
        """Extract student information from ID card using multiple techniques"""
        # Get preprocessed images
        processed_images = self.apply_preprocessing_methods(image)
        
        # Apply OCR on each preprocessed image and combine results
        all_text = ""
        for processed in processed_images:
            text = self.apply_ocr_with_multiple_configs(processed)
            all_text += text + "\n"
        
        # Detect text regions for targeted OCR
        text_regions = self.detect_text_regions(image)
        
        # Extract text from specific regions
        for x, y, w, h in text_regions:
            roi = image[y:y+h, x:x+w]
            # Check if ROI is valid
            if roi.size > 0:
                roi_text = pytesseract.image_to_string(roi, config=self.config_default)
                all_text += roi_text + "\n"
        
        # Initialize dictionary for student information
        student_info = {
            'university': None,
            'student_card': None,
            'name': None,
            'dob': None,
            'student_id': None,
            'class': None,
            'cohort': None
        }
        
        # Extract university name - looking for Dong A University in various formats
        univ_patterns = [
            r'(ĐẠI HỌC ĐÔNG Á|DONG A UNIVERSITY|ĐAI HOC ĐÔNG Á|DAI HOC DONG A)',
            r'ĐÔNG Á', 
            r'DONG A'
        ]
        
        for pattern in univ_patterns:
            univ_match = re.search(pattern, all_text, re.IGNORECASE)
            if univ_match:
                student_info['university'] = univ_match.group(0)
                break
        
        # Extract card type - looking for student card in various formats
        card_patterns = [
            r'(THẺ SINH VIÊN|STUDENT CARD|THE SINH VIEN)', 
            r'THẺ\s+SINH\s+VIÊN',
            r'THE\s+SINH\s+VIEN'
        ]
        
        for pattern in card_patterns:
            card_match = re.search(pattern, all_text, re.IGNORECASE)
            if card_match:
                student_info['student_card'] = card_match.group(0)
                break
        
        # Extract student name using multiple patterns
        name_patterns = [
            # After "THE SINH VIEN"
            r'(?:THẺ SINH VIÊN|THE SINH VIEN)[^\n]*\n+([^\n:]+)',
            # Vietnamese names (capital first letters with diacritics)
            r'([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯĂẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỮỰỲỴỶỸ][a-zàáâãèéêìíòóôõùúăđĩũơưăạảấầẩẫậắằẳẵặẹẻẽềềểễệỉịọỏốồổỗộớờởỡợụủứừữựỳỵỷỹ\s]+\s+[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯĂẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỮỰỲỴỶỸ][a-zàáâãèéêìíòóôõùúăđĩũơưăạảấầẩẫậắằẳẵặẹẻẽềềểễệỉịọỏốồổỗộớờởỡợụủứừữựỳỵỷỹ\s]+)',
            # Vietnamese names without diacritics
            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)'
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, all_text, re.IGNORECASE)
            if name_match:
                student_info['name'] = name_match.group(1).strip()
                break
        
        # Extract date of birth with multiple patterns
        dob_patterns = [
            r'Ngày sinh\s*:\s*(\d{2}/\d{2}/\d{4})',
            r'Ngay sinh\s*:\s*(\d{2}/\d{2}/\d{4})',
            r'DOB\s*:\s*(\d{2}/\d{2}/\d{4})',
            r'(\d{2}/\d{2}/\d{4})'
        ]
        
        for pattern in dob_patterns:
            dob_match = re.search(pattern, all_text)
            if dob_match:
                student_info['dob'] = dob_match.group(1)
                break
        
        # Extract student ID (typically 5-6 digits)
        id_patterns = [
            r'(?<!\d)(\d{5,6})(?!\d)',
            r'ID\s*:\s*(\d{5,6})',
            r'Student ID\s*:\s*(\d{5,6})'
        ]
        
        for pattern in id_patterns:
            id_match = re.search(pattern, all_text)
            if id_match:
                student_info['student_id'] = id_match.group(1)
                break
        
        # Extract class code with multiple patterns
        class_patterns = [
            r'Lớp\s*:\s*([A-Z0-9]+)',
            r'Lop\s*:\s*([A-Z0-9]+)',
            r'Class\s*:\s*([A-Z0-9]+)'
        ]
        
        for pattern in class_patterns:
            class_match = re.search(pattern, all_text)
            if class_match:
                student_info['class'] = class_match.group(1)
                break
        
        # Extract cohort years with multiple patterns
        cohort_patterns = [
            r'Khóa\s*:\s*(\d{4}\s*-\s*\d{4})',
            r'Khoa\s*:\s*(\d{4}\s*-\s*\d{4})',
            r'Course\s*:\s*(\d{4}\s*-\s*\d{4})'
        ]
        
        for pattern in cohort_patterns:
            cohort_match = re.search(pattern, all_text)
            if cohort_match:
                student_info['cohort'] = cohort_match.group(1).strip()
                break
        
        # Return the extracted information and the best processed image
        return student_info, processed_images[0]  # Return first processed image for visualization
    
    def visualize_text_regions(self, image, regions):
        """Visualize detected text regions on the image"""
        visualization = image.copy()
        
        for i, (x, y, w, h) in enumerate(regions):
            # Draw rectangle around the text region
            cv2.rectangle(visualization, (x, y), (x+w, y+h), (0, 255, 0), 2)
            # Add region number
            cv2.putText(visualization, str(i+1), (x, y-5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        return visualization
    
    def save_visualization(self, original, processed, visualization, base_filename):
        """Save visualization images to Django's media folder"""
        # Create directory if it doesn't exist
        vis_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations')
        os.makedirs(vis_dir, exist_ok=True)
        
        # Generate unique filenames
        original_path = os.path.join(vis_dir, f"{base_filename}_original.jpg")
        processed_path = os.path.join(vis_dir, f"{base_filename}_processed.jpg")
        regions_path = os.path.join(vis_dir, f"{base_filename}_regions.jpg")
        combined_path = os.path.join(vis_dir, f"{base_filename}_combined.jpg")
        
        # Save individual images
        cv2.imwrite(original_path, original)
        cv2.imwrite(processed_path, processed)
        cv2.imwrite(regions_path, visualization)
        
        # Create combined visualization using matplotlib
        plt.figure(figsize=(15, 5))
        
        plt.subplot(1, 3, 1)
        plt.title("Original Image")
        plt.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        
        plt.subplot(1, 3, 2)
        plt.title("Processed Image")
        plt.imshow(processed, cmap='gray')
        plt.axis('off')
        
        plt.subplot(1, 3, 3)
        plt.title("Detected Text Regions")
        plt.imshow(cv2.cvtColor(visualization, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        
        plt.tight_layout()
        plt.savefig(combined_path)
        plt.close()
        
        # Return paths relative to MEDIA_URL for template rendering
        return {
            'original': os.path.join('visualizations', f"{base_filename}_original.jpg"),
            'processed': os.path.join('visualizations', f"{base_filename}_processed.jpg"),
            'regions': os.path.join('visualizations', f"{base_filename}_regions.jpg"),
            'combined': os.path.join('visualizations', f"{base_filename}_combined.jpg")
        }
    
    def process_student_card(self, image_path):
        """Main function to process student ID card"""
        # Load image
        image = cv2.imread(image_path)
        
        # If no image is provided, return empty results
        if image is None:
            return None, None, None, None
        
        # Get a copy of the original image
        original = image.copy()
        
        # Extract information using enhanced techniques
        info, processed = self.extract_card_info(image)
        
        # Detect text regions for visualization
        text_regions = self.detect_text_regions(original)
        
        # Create visualization with detected text regions
        visualization = self.visualize_text_regions(original, text_regions)
        
        return info, original, processed, visualization