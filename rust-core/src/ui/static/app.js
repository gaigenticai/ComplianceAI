// KYC Automation Platform - JavaScript Application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize application
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Initialize form handlers
    initializeFormHandlers();
    
    // Initialize UI components
    initializeUIComponents();
    
    // Initialize real-time updates
    initializeRealTimeUpdates();
    
    // Initialize accessibility features
    initializeAccessibility();
    
    console.log('KYC Automation Platform initialized');
}

/**
 * Initialize form handlers
 */
function initializeFormHandlers() {
    // KYC submission form
    const kycForm = document.getElementById('kycForm');
    if (kycForm) {
        kycForm.addEventListener('submit', handleKycSubmission);
    }
    
    // Feedback form
    const feedbackForm = document.getElementById('feedbackForm');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', handleFeedbackSubmission);
    }
    
    // File input validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', validateFileInput);
    });
}

/**
 * Handle KYC form submission
 */
async function handleKycSubmission(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = document.getElementById('submitBtn');
    const processingModal = new bootstrap.Modal(document.getElementById('processingModal'));
    const successModal = new bootstrap.Modal(document.getElementById('successModal'));
    
    // Validate form
    if (!validateKycForm(form)) {
        return;
    }
    
    // Show processing state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';
    
    try {
        // Create form data
        const formData = new FormData(form);
        
        // Show processing modal
        processingModal.show();
        
        // Submit form
        const response = await fetch('/submit', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        // Hide processing modal
        processingModal.hide();
        
        if (result.success) {
            // Show success modal
            document.getElementById('successRequestId').textContent = result.request_id;
            document.getElementById('requestId').textContent = result.request_id;
            
            successModal.show();
            
            // Set up result viewing
            document.getElementById('viewResultsBtn').addEventListener('click', function() {
                window.location.href = `/result/${result.request_id}`;
            });
            
            // Auto-redirect after 5 seconds
            setTimeout(() => {
                window.location.href = `/result/${result.request_id}`;
            }, 5000);
            
        } else {
            throw new Error(result.error || 'Submission failed');
        }
        
    } catch (error) {
        console.error('Submission error:', error);
        
        // Hide processing modal
        processingModal.hide();
        
        // Show error message
        showErrorAlert('Submission failed: ' + error.message);
        
    } finally {
        // Reset submit button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit KYC Request';
    }
}

/**
 * Handle feedback form submission
 */
async function handleFeedbackSubmission(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Submitting...';
    
    try {
        const formData = new FormData(form);
        
        const response = await fetch('/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccessAlert('Feedback submitted successfully. Thank you for helping us improve!');
            form.reset();
        } else {
            throw new Error(result.error || 'Feedback submission failed');
        }
        
    } catch (error) {
        console.error('Feedback submission error:', error);
        showErrorAlert('Failed to submit feedback: ' + error.message);
        
    } finally {
        // Reset submit button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane me-1"></i>Submit Feedback';
    }
}

/**
 * Validate KYC form
 */
function validateKycForm(form) {
    const requiredFiles = ['file_id', 'file_selfie'];
    const errors = [];
    
    // Check required files
    requiredFiles.forEach(fieldName => {
        const fileInput = form.querySelector(`input[name="${fieldName}"]`);
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            errors.push(`${fieldName.replace('file_', '').replace('_', ' ')} is required`);
        }
    });
    
    // Check file sizes
    const fileInputs = form.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        if (input.files && input.files.length > 0) {
            const file = input.files[0];
            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                errors.push(`${input.name} file size exceeds 10MB limit`);
            }
        }
    });
    
    if (errors.length > 0) {
        showErrorAlert('Please fix the following errors:\n• ' + errors.join('\n• '));
        return false;
    }
    
    return true;
}

/**
 * Validate file input
 */
function validateFileInput(event) {
    const input = event.target;
    const file = input.files[0];
    
    if (!file) return;
    
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
    
    // Check file size
    if (file.size > maxSize) {
        showErrorAlert(`File "${file.name}" is too large. Maximum size is 10MB.`);
        input.value = '';
        return;
    }
    
    // Check file type
    if (!allowedTypes.includes(file.type)) {
        showErrorAlert(`File "${file.name}" has an unsupported format. Please use JPG, PNG, or PDF.`);
        input.value = '';
        return;
    }
    
    // Show file preview for images
    if (file.type.startsWith('image/')) {
        showImagePreview(input, file);
    }
    
    // Update UI to show file selected
    updateFileInputUI(input, file);
}

/**
 * Show image preview
 */
function showImagePreview(input, file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        // Create or update preview
        let preview = input.parentNode.querySelector('.file-preview');
        if (!preview) {
            preview = document.createElement('div');
            preview.className = 'file-preview mt-2';
            input.parentNode.appendChild(preview);
        }
        
        preview.innerHTML = `
            <div class="d-flex align-items-center">
                <img src="${e.target.result}" alt="Preview" class="img-thumbnail me-2" style="width: 60px; height: 60px; object-fit: cover;">
                <div>
                    <small class="text-muted d-block">${file.name}</small>
                    <small class="text-muted">${formatFileSize(file.size)}</small>
                </div>
            </div>
        `;
    };
    reader.readAsDataURL(file);
}

/**
 * Update file input UI
 */
function updateFileInputUI(input, file) {
    // Add success styling
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
    
    // Update label or add status
    const label = input.parentNode.querySelector('label');
    if (label) {
        const originalText = label.dataset.originalText || label.textContent;
        label.dataset.originalText = originalText;
        label.innerHTML = `${originalText} <i class="fas fa-check text-success ms-1"></i>`;
    }
}

/**
 * Initialize UI components
 */
function initializeUIComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize risk score circles
    initializeRiskScoreCircles();
    
    // Initialize progress bars
    initializeProgressBars();
    
    // Initialize copy-to-clipboard functionality
    initializeCopyToClipboard();
}

/**
 * Initialize risk score circles
 */
function initializeRiskScoreCircles() {
    const riskCircles = document.querySelectorAll('.risk-score-circle');
    riskCircles.forEach(circle => {
        const score = parseFloat(circle.dataset.score) || 0;
        
        // Update circle color based on score
        let color;
        if (score <= 30) {
            color = '#198754'; // Green
        } else if (score <= 60) {
            color = '#ffc107'; // Yellow
        } else {
            color = '#dc3545'; // Red
        }
        
        // Create gradient based on score
        const percentage = (score / 100) * 360;
        circle.style.background = `conic-gradient(
            from 0deg,
            ${color} 0deg,
            ${color} ${percentage}deg,
            #e9ecef ${percentage}deg,
            #e9ecef 360deg
        )`;
    });
}

/**
 * Initialize progress bars
 */
function initializeProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width || bar.getAttribute('aria-valuenow') + '%';
        bar.style.width = '0%';
        
        // Animate to target width
        setTimeout(() => {
            bar.style.width = width;
        }, 500);
    });
}

/**
 * Initialize copy-to-clipboard functionality
 */
function initializeCopyToClipboard() {
    // Add copy buttons to code blocks
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach(code => {
        const button = document.createElement('button');
        button.className = 'btn btn-sm btn-outline-secondary position-absolute top-0 end-0 m-2';
        button.innerHTML = '<i class="fas fa-copy"></i>';
        button.title = 'Copy to clipboard';
        
        code.parentNode.style.position = 'relative';
        code.parentNode.appendChild(button);
        
        button.addEventListener('click', () => {
            navigator.clipboard.writeText(code.textContent).then(() => {
                button.innerHTML = '<i class="fas fa-check text-success"></i>';
                setTimeout(() => {
                    button.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            });
        });
    });
}

/**
 * Initialize real-time updates
 */
function initializeRealTimeUpdates() {
    // Check if we're on a result page that might need updates
    const requestId = getRequestIdFromUrl();
    if (requestId && window.location.pathname.includes('/result/')) {
        // Poll for updates every 10 seconds if result is not complete
        const isProcessing = document.querySelector('.processing-animation');
        if (isProcessing) {
            setInterval(() => {
                window.location.reload();
            }, 10000);
        }
    }
}

/**
 * Initialize accessibility features
 */
function initializeAccessibility() {
    // Add keyboard navigation for custom components
    const interactiveElements = document.querySelectorAll('.step-item, .timeline-item');
    interactiveElements.forEach(element => {
        element.setAttribute('tabindex', '0');
        element.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                element.click();
            }
        });
    });
    
    // Add screen reader announcements for dynamic content
    const announcer = document.createElement('div');
    announcer.setAttribute('aria-live', 'polite');
    announcer.setAttribute('aria-atomic', 'true');
    announcer.className = 'sr-only';
    document.body.appendChild(announcer);
    
    window.announceToScreenReader = function(message) {
        announcer.textContent = message;
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    };
}

/**
 * Utility Functions
 */

/**
 * Show success alert
 */
function showSuccessAlert(message) {
    showAlert(message, 'success');
}

/**
 * Show error alert
 */
function showErrorAlert(message) {
    showAlert(message, 'danger');
}

/**
 * Show alert
 */
function showAlert(message, type = 'info') {
    const alertContainer = getOrCreateAlertContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
    
    // Announce to screen readers
    if (window.announceToScreenReader) {
        window.announceToScreenReader(message);
    }
}

/**
 * Get or create alert container
 */
function getOrCreateAlertContainer() {
    let container = document.getElementById('alert-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'alert-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Get request ID from URL
 */
function getRequestIdFromUrl() {
    const pathParts = window.location.pathname.split('/');
    const resultIndex = pathParts.indexOf('result');
    if (resultIndex !== -1 && pathParts[resultIndex + 1]) {
        return pathParts[resultIndex + 1];
    }
    return null;
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

/**
 * Validate email format
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Validate phone format
 */
function isValidPhone(phone) {
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    return phoneRegex.test(phone.replace(/[\s\-\(\)]/g, ''));
}

/**
 * Export functions for testing
 */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateKycForm,
        formatFileSize,
        isValidEmail,
        isValidPhone,
        formatDate
    };
}
