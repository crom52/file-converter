"""
This is a template WSGI configuration file for PythonAnywhere.
Copy this content to your PythonAnywhere WSGI file (usually at /var/www/yourusername_pythonanywhere_com_wsgi.py)
"""

import sys
import os

# Add your project directory to the sys.path
# Replace 'yourusername' with your PythonAnywhere username
# Replace 'doc-to-pdf-webapp' with your project directory name
path = '/home/yourusername/doc-to-pdf-webapp'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['UPLOAD_FOLDER'] = 'uploads'
os.environ['CONVERTED_FOLDER'] = 'converted'
os.environ['MAXIMUM_UPLOAD_FILE'] = '3'

# Import your Flask app
from app import app as application 