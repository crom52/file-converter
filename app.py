import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import img2pdf
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import threading
import time
from datetime import datetime, timedelta
import shutil

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables with defaults
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
CONVERTED_FOLDER = os.getenv('CONVERTED_FOLDER', 'converted')
ALLOWED_EXTENSIONS = {'docx', 'jpg', 'jpeg', 'png'}
PORT = int(os.getenv('PORT', 5005))
MAXIMUM_UPLOAD_FILE = int(os.getenv('MAXIMUM_UPLOAD_FILE', 3))
FILE_RETENTION_MINUTES = 5  # Reduced to 5 minutes for better memory management

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# Track converted files and their creation times
converted_files = {}

def convert_docx_to_pdf(input_path, output_path):
    """Convert DOCX to PDF using pure Python libraries"""
    try:
        # Read the DOCX file
        doc = Document(input_path)
        
        # Create PDF
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        y = height - inch  # Start from top of page
        
        for para in doc.paragraphs:
            if y < inch:  # If near bottom of page
                c.showPage()  # New page
                y = height - inch  # Reset to top
            
            # Handle different paragraph styles
            if para.style.name.startswith('Heading'):
                c.setFont("Helvetica-Bold", 14)
            else:
                c.setFont("Helvetica", 12)
            
            # Write text
            text = para.text
            if text.strip():  # Only process non-empty paragraphs
                # Handle text that might be too long for the page width
                if c.stringWidth(text, "Helvetica", 12) > (width - 2*inch):
                    words = text.split()
                    line = []
                    for word in words:
                        line.append(word)
                        test_line = ' '.join(line)
                        if c.stringWidth(test_line, "Helvetica", 12) > (width - 2*inch):
                            line.pop()  # Remove last word
                            c.drawString(inch, y, ' '.join(line))
                            y -= 20
                            line = [word]  # Start new line with the word that didn't fit
                    if line:  # Draw any remaining text
                        c.drawString(inch, y, ' '.join(line))
                else:
                    c.drawString(inch, y, text)
                y -= 20  # Move down for next line
        
        # Ensure we save the last page
        if c.getPageNumber() > 0:
            c.save()
        return True
        
    except Exception as e:
        print(f"Error in convert_docx_to_pdf: {str(e)}")  # Debug logging
        raise Exception(f"Error converting Word document: {str(e)}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def force_cleanup_folders():
    """Force cleanup of both upload and converted folders"""
    try:
        # Clean upload folder
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER)
            
        # Clean converted folder
        if os.path.exists(CONVERTED_FOLDER):
            shutil.rmtree(CONVERTED_FOLDER)
            os.makedirs(CONVERTED_FOLDER)
            
        # Reset tracking
        converted_files.clear()
        
    except Exception as e:
        print(f"Error during force cleanup: {str(e)}")

def clean_old_files():
    """Clean up files older than FILE_RETENTION_MINUTES"""
    current_time = datetime.now()
    files_to_delete = []
    
    try:
        # Identify old files
        for filename, creation_time in list(converted_files.items()):
            if current_time - creation_time > timedelta(minutes=FILE_RETENTION_MINUTES):
                files_to_delete.append(filename)
        
        # Delete old files
        for filename in files_to_delete:
            file_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                converted_files.pop(filename, None)
                print(f"Cleaned up old file: {filename}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

        # Clean up any orphaned files in both folders
        for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER]:
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    if filename not in converted_files:
                        file_path = os.path.join(folder, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                                print(f"Cleaned up orphaned file: {filename}")
                        except Exception as e:
                            print(f"Error deleting orphaned file {file_path}: {e}")
                            
        # If converted_files is empty, force cleanup to ensure fresh state
        if not converted_files:
            force_cleanup_folders()
            
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

@app.route('/')
def upload_form():
    # Clean old files before serving the upload form
    clean_old_files()
    return render_template('upload.html', max_files=MAXIMUM_UPLOAD_FILE)

@app.route('/reset', methods=['POST'])
def reset_session():
    """Reset the conversion session"""
    force_cleanup_folders()
    return jsonify({'message': 'Session reset successfully'}), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    uploaded_file = request.files['file']
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(uploaded_file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # Clean old files before processing new ones
        clean_old_files()
        
        # Get current number of files (excluding expired ones)
        current_time = datetime.now()
        active_files = {f: t for f, t in converted_files.items() 
                       if current_time - t <= timedelta(minutes=FILE_RETENTION_MINUTES)}
        
        # Check if we've reached the maximum number of files
        if len(active_files) >= MAXIMUM_UPLOAD_FILE:
            return jsonify({'error': 'Maximum number of files exceeded'}), 400

        # Secure the filename and create paths
        filename = secure_filename(uploaded_file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        name, ext = os.path.splitext(filename)
        output_pdf = os.path.join(app.config['CONVERTED_FOLDER'], name + ".pdf")

        # Save the uploaded file
        uploaded_file.save(input_path)
        print(f"File saved to: {input_path}")  # Debug logging

        try:
            ext = ext.lower()
            if ext == ".docx":
                success = convert_docx_to_pdf(input_path, output_pdf)
                if not success:
                    raise Exception("Failed to convert document")
            elif ext in ['.jpg', '.jpeg', '.png']:
                # Fix image to PDF conversion
                image = Image.open(input_path)
                image_bytes = BytesIO()
                if image.mode in ("RGBA", "LA"):
                    # Convert RGBA images to RGB
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    background.save(image_bytes, format="PDF")
                else:
                    image.save(image_bytes, format="PDF")
                
                with open(output_pdf, "wb") as f:
                    f.write(image_bytes.getvalue())

            # Verify the PDF was created
            if not os.path.exists(output_pdf):
                raise Exception("PDF file was not created")

            print(f"PDF created at: {output_pdf}")  # Debug logging

            # Track the converted file
            converted_files[name + '.pdf'] = datetime.now()

        finally:
            # Clean up the uploaded file immediately after conversion
            if os.path.exists(input_path):
                os.remove(input_path)
                print(f"Cleaned up uploaded file: {input_path}")
        
        return jsonify({
            'message': 'File converted successfully',
            'filename': name + '.pdf'
        }), 200

    except Exception as e:
        print(f"Error in upload_file: {str(e)}")  # Debug logging
        # Clean up any uploaded file in case of error
        if 'input_path' in locals() and os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Check if file exists and is tracked
        if filename not in converted_files:
            return jsonify({'error': 'File not found or expired'}), 404
            
        file_path = os.path.join(app.config['CONVERTED_FOLDER'], filename)
        print(f"Attempting to download: {file_path}")  # Debug logging
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")  # Debug logging
            converted_files.pop(filename, None)  # Remove from tracking if file doesn't exist
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"Error in download_file: {str(e)}")  # Debug logging
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File is too large. Maximum size is 16MB'}), 413

def cleanup_thread_function():
    """Background thread function for cleaning up files"""
    while True:
        try:
            time.sleep(60)  # Check every minute
            clean_old_files()
        except Exception as e:
            print(f"Error in cleanup thread: {str(e)}")

if __name__ == "__main__":
    # Force cleanup on startup
    force_cleanup_folders()
    
    # Start the cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_thread_function, daemon=True)
    cleanup_thread.start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
