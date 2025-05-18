#!/bin/bash

# Create virtual environment if it doesn't exist
python3 -m venv ~/file-converter/venv

# Activate virtual environment
source ~/file-converter/venv/bin/activate

# Clone or pull the latest code
if [ ! -d "~/file-converter" ]; then
    # First time: Clone the repository
    git clone https://github.com/your-username/doc-to-pdf-webapp.git ~/file-converter
else
    # Update existing repository
    cd ~/file-converter
    git pull origin main
fi

# Go to project directory
cd ~/file-converter

# Install requirements
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads converted

# Set up the WSGI file
cat > /var/www/crom36_pythonanywhere_com_wsgi.py << EOL
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
os.environ['UPLOAD_FOLDER'] = 'uploads'
os.environ['CONVERTED_FOLDER'] = 'converted'
os.environ['MAXIMUM_UPLOAD_FILE'] = '3'

from app import app as application
EOL

# Reload the web app
touch /var/www/crom36_pythonanywhere_com_wsgi.py

echo "Deployment completed! Don't forget to:"
echo "1. Go to Web tab"
echo "2. Set the virtual environment path to: /home/crom36/file-converter/venv"
echo "3. Set the project path to: /home/crom36/file-converter"
echo "4. Click the 'Reload' button" 