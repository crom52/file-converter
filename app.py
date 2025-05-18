import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, jsonify, abort
from flask_cors import CORS
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv('UPLOAD_FOLDER', 'uploads'))
ALLOWED_EXTENSIONS = {'docx', 'jpg', 'jpeg', 'png'}
MAXIMUM_UPLOAD_FILE = int(os.getenv('MAXIMUM_UPLOAD_FILE', 3))
FILE_RETENTION_MINUTES = 5  # Reduced to 5 minutes for better memory management

# Detect environment
IS_PYTHONANYWHERE = 'PYTHONANYWHERE_SITE' in os.environ
IS_LOCAL = not IS_PYTHONANYWHERE and os.getenv('FLASK_ENV') != 'production'

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist and have proper permissions
def ensure_directories():
    """Ensure upload directory exists with proper permissions"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, mode=0o755, exist_ok=True)
    # Set proper permissions if directory already exists
    else:
        os.chmod(UPLOAD_FOLDER, 0o755)

# Call it when app starts
ensure_directories()

# We don't need CONVERTED_FOLDER anymore as we'll stream directly
# Remove tracking of converted files as we'll handle them immediately
converted_files = {}

def convert_docx_to_pdf(input_path):
    """Convert DOCX to PDF and return BytesIO object"""
    try:
        # Read the DOCX file
        doc = Document(input_path)
        
        # Create PDF in memory
        output_pdf = BytesIO()
        c = canvas.Canvas(output_pdf, pagesize=letter)
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
                if c.stringWidth(text, "Helvetica", 12) > (width - 2*inch):
                    words = text.split()
                    line = []
                    for word in words:
                        line.append(word)
                        test_line = ' '.join(line)
                        if c.stringWidth(test_line, "Helvetica", 12) > (width - 2*inch):
                            line.pop()
                            c.drawString(inch, y, ' '.join(line))
                            y -= 20
                            line = [word]
                    if line:
                        c.drawString(inch, y, ' '.join(line))
                else:
                    c.drawString(inch, y, text)
                y -= 20
        
        c.save()
        output_pdf.seek(0)
        return output_pdf
        
    except Exception as e:
        print(f"Error in convert_docx_to_pdf: {str(e)}")
        raise Exception(f"Error converting Word document: {str(e)}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def force_cleanup_folders():
    """Force cleanup of upload folder"""
    try:
        # Ensure directory exists before cleaning
        ensure_directories()
        
        # Clean upload folder
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER, mode=0o755)
            
    except Exception as e:
        print(f"Error during force cleanup: {str(e)}")

def clean_old_files():
    """Clean up files older than FILE_RETENTION_MINUTES"""
    current_time = datetime.now()
    files_to_delete = []
    
    try:
        # Ensure directory exists
        ensure_directories()
        
        # Identify old files
        for filename in os.listdir(UPLOAD_FOLDER):
            if current_time - datetime.fromtimestamp(os.path.getctime(os.path.join(UPLOAD_FOLDER, filename))) > timedelta(minutes=FILE_RETENTION_MINUTES):
                files_to_delete.append(filename)
        
        # Delete old files
        for filename in files_to_delete:
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                print(f"Cleaned up old file: {filename}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

        # Clean up any orphaned files in the folder
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename not in converted_files:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f"Cleaned up orphaned file: {filename}")
                except Exception as e:
                    print(f"Error deleting orphaned file {file_path}: {e}")
                            
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
    try:
        force_cleanup_folders()
        return jsonify({'message': 'Session reset successfully'}), 200
    except Exception as e:
        print(f"Error in reset_session: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
        
        # Create a temporary file
        filename = secure_filename(uploaded_file.filename)
        name, ext = os.path.splitext(filename)
        
        # Save uploaded file to memory
        file_content = uploaded_file.read()
        input_buffer = BytesIO(file_content)

        try:
            ext = ext.lower()
            if ext == ".docx":
                # Convert DOCX directly from memory
                doc = Document(input_buffer)
                pdf_buffer = convert_docx_to_pdf(input_buffer)
            elif ext in ['.jpg', '.jpeg', '.png']:
                # Convert image directly from memory
                image = Image.open(input_buffer)
                pdf_buffer = BytesIO()
                if image.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    background.save(pdf_buffer, format="PDF")
                else:
                    image.save(pdf_buffer, format="PDF")
                pdf_buffer.seek(0)

            # Save the PDF buffer to a temporary file
            temp_pdf_path = os.path.join(UPLOAD_FOLDER, f"{name}.pdf")
            with open(temp_pdf_path, 'wb') as f:
                f.write(pdf_buffer.getvalue())

            # Return success with filename
            return jsonify({'filename': f"{name}.pdf"}), 200

        except Exception as e:
            print(f"Error in conversion: {str(e)}")
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Handle file downloads"""
    try:
        # Ensure the filename is secure
        filename = secure_filename(filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        # Send the file
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        print(f"Error in download_file: {str(e)}")
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
    
    # Dynamic port handling
    if IS_LOCAL:
        # Local development - use port 5005
        port = int(os.getenv('PORT', 5005))
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Production (PythonAnywhere, etc) - let the WSGI server handle it
        app.run()
