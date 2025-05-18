# Document/Image to PDF Converter Web App

A Flask web application that converts various document formats (`.docx`, `.jpg`, `.jpeg`, `.png`) to PDF format. Features a user-friendly drag-and-drop interface using Dropzone.js.

## Features

- Convert Word documents (`.docx`) to PDF
- Convert images (`.jpg`, `.jpeg`, `.png`) to PDF
- Modern drag-and-drop upload interface
- File size limit: 16MB
- Automatic file cleanup
- Environment variable configuration support

## File Processing Flow

1. **Upload**: 
   - User drags & drops or selects a file
   - File is validated for type and size
   - Temporary storage in `uploads` folder

2. **Conversion**:
   - DOCX files: Converted using `docx2pdf`
   - Images: Converted using `img2pdf`
   - Output saved in `converted` folder

3. **Download**:
   - Success message shown with download link
   - PDF available for immediate download
   - Automatic cleanup of temporary files

## Prerequisites

- Python 3.x (Tested with Python 3.13)
- macOS, Linux, or Windows

## Installation Guide

### 1. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install python-dotenv first
pip install python-dotenv

# Install all other dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```plaintext
PORT=5005
UPLOAD_FOLDER=uploads
CONVERTED_FOLDER=converted
FLASK_DEBUG=False
```

Note: If `.env` file is not created, the application will use these default values.

## Running the Application

```bash
source venv/bin/activate && python app.py
```

The application will be available at:
- http://localhost:5005 (or your configured PORT)

## Common Issues and Solutions

### 1. "command not found: pip"
**Solution:**
- Make sure Python is installed
- Use `pip3` instead of `pip`
- Or activate the virtual environment first: `source venv/bin/activate`

### 2. "Address already in use" (Port 5000)
**Solution:**
- On macOS, port 5000 is often used by AirPlay
- Use a different port (e.g., 5005) in your `.env` file
- Or disable AirPlay in System Preferences

### 3. "ModuleNotFoundError: No module named 'dotenv'"
**Solution:**
```bash
pip install python-dotenv
```

### 4. "externally-managed-environment" Error
**Solution:**
- Always use a virtual environment
- Create: `python3 -m venv venv`
- Activate: `source venv/bin/activate`
- Then install packages

## Project Structure

```
doc-to-pdf-webapp/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── .env               # Environment configuration (optional)
├── uploads/           # Temporary storage for uploaded files
├── converted/         # Output directory for converted PDFs
└── templates/         # HTML templates
    └── upload.html    # Upload page template
```

## Development Notes

- The application creates `uploads` and `converted` directories automatically
- Files are temporarily stored in `uploads` during conversion
- Converted PDFs are saved in `converted` directory
- Automatic cleanup of old files on application startup
- Maximum file size: 16MB

## Production Deployment

For production deployment:

1. Use a production WSGI server:
```bash
pip install gunicorn  # Already in requirements.txt
gunicorn app:app
```

2. Set appropriate environment variables:
- Set `FLASK_DEBUG=False`
- Configure proper `PORT`
- Set up proper file permissions for upload/converted directories

3. Consider using a reverse proxy (nginx/apache) in production

## Security Notes

- The application performs basic file type validation
- Only allows specified file extensions (`.docx`, `.jpg`, `.jpeg`, `.png`)
- Uses `secure_filename` for uploaded files
- Implements separate directories for uploads and converted files

## Contributing

Feel free to submit issues and enhancement requests!
