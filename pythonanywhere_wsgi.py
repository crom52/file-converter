"""
This is a template WSGI configuration file for PythonAnywhere.
Copy this content to your PythonAnywhere WSGI file (usually at /var/www/crom36_pythonanywhere_com_wsgi.py)
"""

import sys
import os
import site

# Add your project directory to the sys.path
project_home = '/home/crom36/file-converter'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Add the site-packages of the virtual environment
site.addsitedir('/home/crom36/file-converter/venv/lib/python3.13/site-packages')

# Set environment variables
os.environ['UPLOAD_FOLDER'] = 'uploads'  # Will be relative to the app directory
os.environ['CONVERTED_FOLDER'] = 'converted'  # Will be relative to the app directory
os.environ['MAXIMUM_UPLOAD_FILE'] = '3'

# Import your Flask app
from app import app as application