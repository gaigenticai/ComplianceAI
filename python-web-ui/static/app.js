/**
 * KYC Automation Platform - Frontend JavaScript
 * Handles form submission, file uploads, and real-time status updates
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupFileUploads();
    setupFormSubmission();
    setupDragAndDrop();
    checkSystemHealth();
}

/**
 * Setup file upload handlers
 */
function setupFileUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            handleFileSelection(e.target);
        });
    });
}

/**
 * Handle file selection and validation
 */
function handleFileSelection(input) {
    const file = input.files[0];
    if (!file) return;

    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
        showAlert(validation.message, 'danger');
        input.value = '';
        return;
    }

    // Show file info
    const infoElement = document.getElementById(input.id.replace('file_', '') + '-file-info');
    if (infoElement) {
        infoElement.innerHTML = `
            <i class="fas fa-check-circle me-2"></i>
            <strong>${file.name}</strong> (${formatFileSize(file.size)})
        `;
        infoElement.style.display = 'block';
    }

    // Update upload area appearance
    const uploadArea = input.closest('.upload-area');
    if (uploadArea) {
        uploadArea.style.borderColor = '#198754';
        uploadArea.style.background = '#e8f5e8';
    }
}

/**
 * Validate uploaded file
 */
function validateFile(file) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.pdf'];

    // Check file size
    if (file.size > maxSize) {
        return {
            valid: false,
            message: 'File size must be less than 10MB'
        };
    }

    // Check file type
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
        return {
            valid: false,
            message: 'Only PDF, JPG, and PNG files are allowed'
        };
    }

    return { valid: true };
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Setup drag and drop functionality
 */
function setupDragAndDrop() {
    const uploadAreas = document.querySelectorAll('.upload-area');
    
    uploadAreas.forEach(area => {
        const input = area.querySelector('input[type="file"]');
        
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            area.classList.add('dragover');
        });
        
        area.addEventListener('dragleave', function(e) {
            e.preventDefault();
            area.classList.remove('dragover');
        });
        
        area.addEventListener('drop', function(e) {
            e.preventDefault();
            area.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                handleFileSelection(input);
            }
        });
    });
}

/**
 * Setup form submission
 */
function setupFormSubmission() {
    const form = document.getElementById('kycForm');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        await submitKYCForm(form);
    });
}

/**
 * Submit KYC form
 */
async function submitKYCForm(form) {
    const submitBtn = document.getElementById('submitBtn');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    
    try {
        // Validate form
        if (!validateForm(form)) {
            return;
        }

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';
        loadingModal.show();

        // Prepare form data
        const formData = new FormData(form);

        // Submit form
        const response = await fetch('/submit', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Success - redirect to processing page
            window.location.href = `/processing/${result.request_id}`;
        } else {
            // Error
            throw new Error(result.detail || 'Submission failed');
        }

    } catch (error) {
        console.error('Submission error:', error);
        showAlert(error.message || 'An error occurred while submitting your request', 'danger');
        
        // Reset button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit for Verification';
        
        // Hide loading modal
        const loadingModal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (loadingModal) {
            loadingModal.hide();
        }
    }
}

/**
 * Validate form before submission
 */
function validateForm(form) {
    const email = form.querySelector('#customer_email').value;
    const fileId = form.querySelector('#file_id').files[0];
    const fileSelfie = form.querySelector('#file_selfie').files[0];
    const consent = form.querySelector('#privacy_consent').checked;

    // Validate email
    if (!email || !isValidEmail(email)) {
        showAlert('Please enter a valid email address', 'danger');
        return false;
    }

    // Validate files
    if (!fileId) {
        showAlert('Please upload your ID document', 'danger');
        return false;
    }

    if (!fileSelfie) {
        showAlert('Please upload your selfie', 'danger');
        return false;
    }

    // Validate consent
    if (!consent) {
        showAlert('Please consent to data processing', 'danger');
        return false;
    }

    return true;
}

/**
 * Validate email format
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert-dismissible');
    existingAlerts.forEach(alert => alert.remove());

    // Create new alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        <i class="fas fa-${getAlertIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

/**
 * Get icon for alert type
 */
function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * Check system health
 */
async function checkSystemHealth() {
    try {
        const response = await fetch('/health');
        const health = await response.json();
        
        updateHealthIndicator(health);
    } catch (error) {
        console.error('Health check failed:', error);
        updateHealthIndicator({ status: 'unhealthy' });
    }
}

/**
 * Update health indicator in UI
 */
function updateHealthIndicator(health) {
    const healthLinks = document.querySelectorAll('a[href="/health"]');
    
    healthLinks.forEach(link => {
        const icon = link.querySelector('i');
        if (icon) {
            icon.className = health.status === 'healthy' 
                ? 'fas fa-heartbeat me-1 text-success' 
                : 'fas fa-exclamation-triangle me-1 text-warning';
        }
    });
}

/**
 * Utility function to get query parameter
 */
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

/**
 * Utility function to format timestamp
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showAlert('Copied to clipboard!', 'success');
    } catch (error) {
        console.error('Failed to copy:', error);
        showAlert('Failed to copy to clipboard', 'danger');
    }
}

/**
 * Download results as JSON
 */
function downloadResults(requestId, result) {
    const dataStr = JSON.stringify(result, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `kyc-results-${requestId}.json`;
    link.click();
    
    URL.revokeObjectURL(link.href);
}

/**
 * Print current page
 */
function printPage() {
    window.print();
}

// Global functions for inline event handlers
window.copyToClipboard = copyToClipboard;
window.downloadResults = downloadResults;
window.printPage = printPage;
