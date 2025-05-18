// Alert functions
function showAlert() {
    const overlay = document.getElementById('alertOverlay');
    overlay.classList.add('show');
}

function closeAlert() {
    const overlay = document.getElementById('alertOverlay');
    overlay.classList.remove('show');
}

// Download function
function downloadFile(event, filename) {
    event.preventDefault();
    
    fetch(`/download/${filename}`)
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.error || 'Download failed');
                });
            }
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            alert(`Download error: ${error.message}`);
        });
}

// Dropzone configuration
Dropzone.options.pdfDropzone = {
    paramName: "file",
    maxFilesize: 16,
    maxFiles: window.MAX_FILES,
    acceptedFiles: ".docx,.jpg,.jpeg,.png",
    dictDefaultMessage: "",
    parallelUploads: 3,
    autoProcessQueue: false,
    createImageThumbnails: true,
    thumbnailWidth: 120,
    thumbnailHeight: 120,
    addRemoveLinks: false,

    init: function() {
        const dropzone = this;
        const convertedFilesSection = document.querySelector('.converted-files-section');
        const filesList = document.querySelector('.converted-files-list');
        const fileCounter = document.querySelector('.file-counter');
        const downloadAllSection = document.querySelector('.download-all-section');
        const convertAllBtn = document.getElementById('convertAllBtn');
        const clearAllBtn = document.getElementById('clearAllBtn');
        const processingOverlay = document.getElementById('processingOverlay');
        let convertedFiles = [];

        function updateFileCounter() {
            const count = dropzone.files.length;
            fileCounter.textContent = `${count}/${window.MAX_FILES}`;
            fileCounter.style.display = count > 0 ? 'flex' : 'none';
            
            convertAllBtn.disabled = count === 0;
            convertAllBtn.style.display = count > 0 ? 'block' : 'none';
            clearAllBtn.style.display = count > 0 ? 'block' : 'none';
        }

        function updateDownloadAllVisibility() {
            if (convertedFiles.length > 0) {
                downloadAllSection.style.display = 'block';
                convertedFilesSection.style.display = 'block';
            } else {
                downloadAllSection.style.display = 'none';
                convertedFilesSection.style.display = 'none';
            }
        }

        // Add Download All functionality
        const downloadAllBtn = document.querySelector('.download-all-btn');
        downloadAllBtn.addEventListener('click', function() {
            // Download each file in sequence
            convertedFiles.forEach(filename => {
                downloadFile(new Event('click'), filename);
            });
        });

        function createFileCard(filename) {
            const card = document.createElement('div');
            card.className = 'converted-file-card';
            card.innerHTML = `
                <div class="file-name-display">${filename}</div>
                <div class="hover-download-btn" onclick="downloadFile(event, '${filename}')">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" width="20" height="20">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                </div>
            `;
            return card;
        }

        function clearAll() {
            // Call reset endpoint to clear server-side state
            return fetch('/reset', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                }
            }).then(response => {
                if (!response.ok) {
                    console.error('Failed to reset session');
                    return Promise.reject('Failed to reset session');
                }
                dropzone.removeAllFiles(true);
                convertedFiles = [];
                filesList.innerHTML = '';
                updateFileCounter();
                updateDownloadAllVisibility();
            }).catch(error => {
                console.error('Error resetting session:', error);
                return Promise.reject(error);
            });
        }

        // Clear files only when Clear All button is clicked
        clearAllBtn.addEventListener('click', function() {
            clearAll();
        });

        // Handle drag enter with new file count check
        this.on("dragenter", function(event) {
            // Get the number of files being dragged
            const draggedFiles = event.dataTransfer ? event.dataTransfer.items.length : 0;
            // Only clear if current files + new files would exceed the limit
            if ((dropzone.files.length + draggedFiles) > window.MAX_FILES) {
                clearAll();
            }
        });

        // Handle click on dropzone with new file count check
        dropzone.element.addEventListener('click', function(e) {
            // Don't clear files unless we're already at the limit
            if (dropzone.files.length >= window.MAX_FILES) {
                clearAll();
            }
        });

        this.on("addedfile", function(file) {
            // If this new file would exceed the limit
            if (this.files.length > window.MAX_FILES) {
                // If we're already at the limit, remove all files and keep only this new one
                if (this.files.length === (window.MAX_FILES + 1) && this.files[0] === file) {
                    clearAll().then(() => {
                        this.addFile(file); // Re-add the new file after clearing
                    }).catch(() => {
                        showAlert();
                    });
                } else {
                    // Otherwise just remove the excess file
                    this.removeFile(file);
                    showAlert();
                    return;
                }
            }
            updateFileCounter();

            // Add remove button to the file preview
            const removeButton = document.createElement('div');
            removeButton.className = 'remove-button-wrapper';
            removeButton.innerHTML = '<div class="custom-remove-button"></div>';
            removeButton.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                dropzone.removeFile(file);
            });
            file.previewElement.appendChild(removeButton);
        });

        this.on("success", function(file, response) {
            file.previewElement.classList.add('dz-upload-success');
            convertedFiles.push(response.filename);
            const fileCard = createFileCard(response.filename);
            filesList.appendChild(fileCard);
            updateDownloadAllVisibility();

            // Add conversion success class to show the green border
            file.previewElement.classList.add('dz-convert-success');
        });

        this.on("error", function(file, errorMessage) {
            console.error('Upload error:', errorMessage);
            this.removeFile(file);
            
            const errorNotification = document.createElement('div');
            errorNotification.className = 'error-notification';
            errorNotification.textContent = typeof errorMessage === 'object' ? 
                errorMessage.error || 'Upload failed' : 
                errorMessage;
            document.body.appendChild(errorNotification);
            
            setTimeout(() => {
                errorNotification.remove();
            }, 3000);
        });

        this.on("removedfile", function(file) {
            updateFileCounter();
        });

        convertAllBtn.addEventListener('click', function() {
            if (dropzone.files.length > 0) {
                // First ensure we have a clean server state
                fetch('/reset', {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                    }
                }).then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to reset session');
                    }
                    // After reset, show processing overlay and start conversion
                    processingOverlay.style.display = 'flex';
                    convertAllBtn.disabled = true;
                    dropzone.processQueue();
                }).catch(error => {
                    console.error('Error before conversion:', error);
                    alert('Error preparing for conversion. Please try again.');
                });
            }
        });

        this.on("queuecomplete", function() {
            processingOverlay.style.display = 'none';
            convertAllBtn.disabled = true;
        });
    }
}; 