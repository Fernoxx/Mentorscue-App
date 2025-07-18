// MENTORSCUE Main JavaScript Functions

// Global variables
let currentUser = null;
let searchTimeout = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Main initialization function
function initializeApp() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validations
    initializeFormValidations();
    
    // Initialize search functionality
    initializeSearchFeatures();
    
    // Initialize auto-refresh for time-sensitive data
    initializeAutoRefresh();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Form validation enhancements
function initializeFormValidations() {
    // Real-time validation for forms
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Phone number validation
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function() {
            validatePhoneNumber(this);
        });
    });
    
    // Email validation
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateEmail(this);
        });
    });
}

// Search functionality
function initializeSearchFeatures() {
    // Live search for tables
    const searchInputs = document.querySelectorAll('.table-search');
    searchInputs.forEach(input => {
        input.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const tableId = this.getAttribute('data-table');
            filterTable(tableId, searchTerm);
        });
    });
    
    // Tutor search in student forms
    const tutorSearchInput = document.getElementById('tutorSearch');
    if (tutorSearchInput) {
        tutorSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchTutors(this.value);
            }, 300);
        });
    }
}

// Auto-refresh functionality
function initializeAutoRefresh() {
    // Refresh dashboard statistics every 5 minutes
    if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
        setInterval(refreshDashboardStats, 300000); // 5 minutes
    }
    
    // Refresh attendance data every 2 minutes on attendance page
    if (window.location.pathname === '/attendance') {
        setInterval(refreshAttendanceData, 120000); // 2 minutes
    }
}

// Keyboard shortcuts
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Alt + N = New (context-dependent)
        if (event.altKey && event.key === 'n') {
            event.preventDefault();
            handleNewAction();
        }
        
        // Alt + S = Search
        if (event.altKey && event.key === 's') {
            event.preventDefault();
            focusSearchInput();
        }
        
        // Escape = Close modals
        if (event.key === 'Escape') {
            closeAllModals();
        }
    });
}

// Utility Functions

// Phone number validation
function validatePhoneNumber(input) {
    const phonePattern = /^[\+]?[1-9][\d]{0,15}$/;
    const isValid = phonePattern.test(input.value.replace(/\s+/g, ''));
    
    if (input.value && !isValid) {
        input.setCustomValidity('Please enter a valid phone number');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
    }
}

// Email validation
function validateEmail(input) {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const isValid = emailPattern.test(input.value);
    
    if (input.value && !isValid) {
        input.setCustomValidity('Please enter a valid email address');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
    }
}

// Table filtering
function filterTable(tableId, searchTerm) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const shouldShow = text.includes(searchTerm);
        row.style.display = shouldShow ? '' : 'none';
    });
    
    // Update visible count
    const visibleRows = Array.from(rows).filter(row => row.style.display !== 'none');
    updateTableCount(tableId, visibleRows.length, rows.length);
}

// Update table count display
function updateTableCount(tableId, visible, total) {
    const countElement = document.querySelector(`[data-table-count="${tableId}"]`);
    if (countElement) {
        countElement.textContent = visible === total ? 
            `(${total})` : `(${visible} of ${total})`;
    }
}

// Tutor search with AJAX
function searchTutors(query) {
    if (query.length < 2) {
        showAllTutors();
        return;
    }
    
    // Show loading indicator
    showSearchLoading();
    
    fetch(`/api/tutors/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            updateTutorList(data);
        })
        .catch(error => {
            console.error('Error searching tutors:', error);
            showSearchError();
        });
}

// Update tutor list display
function updateTutorList(tutors) {
    const tutorList = document.getElementById('tutorList');
    if (!tutorList) return;
    
    const tutorItems = tutorList.querySelectorAll('.tutor-item');
    
    tutorItems.forEach(item => {
        const tutorId = item.querySelector('input[type="checkbox"]').value;
        const tutorData = tutors.find(t => t.id == tutorId);
        item.style.display = tutorData ? 'block' : 'none';
    });
}

// Show all tutors
function showAllTutors() {
    const tutorItems = document.querySelectorAll('.tutor-item');
    tutorItems.forEach(item => {
        item.style.display = 'block';
    });
}

// Loading and error states
function showSearchLoading() {
    // Implementation for loading state
    const searchInput = document.getElementById('tutorSearch');
    if (searchInput) {
        searchInput.classList.add('loading');
    }
}

function showSearchError() {
    showNotification('Error searching tutors. Please try again.', 'error');
}

// Dashboard functions
function refreshDashboardStats() {
    // Check if we're on the admin dashboard
    if (!document.getElementById('total-students')) {
        return;
    }
    
    // Refresh statistics cards
    fetch('/api/admin/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => {
            console.error('Error refreshing dashboard:', error);
        });
}

function updateDashboardStats(data) {
    // Update statistic cards with new data
    const statsElements = {
        'students-count': data.students_count,
        'tutors-count': data.tutors_count,
        'today-classes': data.today_classes,
        'pending-invoices': data.pending_invoices
    };
    
    Object.entries(statsElements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            animateCountUp(element, value);
        }
    });
}

// Attendance functions
function refreshAttendanceData() {
    const attendanceTable = document.getElementById('attendanceTable');
    if (attendanceTable) {
        // Refresh attendance table data
        fetch('/api/attendance/recent')
            .then(response => response.json())
            .then(data => {
                updateAttendanceTable(data);
            })
            .catch(error => {
                console.error('Error refreshing attendance:', error);
            });
    }
}

// Animation functions
function animateCountUp(element, targetValue) {
    const currentValue = parseInt(element.textContent) || 0;
    const increment = Math.ceil((targetValue - currentValue) / 20);
    
    if (currentValue < targetValue) {
        element.textContent = currentValue + increment;
        setTimeout(() => animateCountUp(element, targetValue), 50);
    } else {
        element.textContent = targetValue;
    }
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 350px;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    `;
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

// Modal functions
function closeAllModals() {
    const modals = document.querySelectorAll('.modal.show');
    modals.forEach(modal => {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
            modalInstance.hide();
        }
    });
}

// Keyboard shortcut handlers
function handleNewAction() {
    const currentPage = window.location.pathname;
    
    if (currentPage.includes('/students')) {
        window.location.href = '/students/add';
    } else if (currentPage.includes('/tutors')) {
        window.location.href = '/tutors/add';
    } else if (currentPage.includes('/attendance')) {
        focusFirstFormInput();
    }
}

function focusSearchInput() {
    const searchInputs = document.querySelectorAll('input[type="search"], input[placeholder*="search" i]');
    if (searchInputs.length > 0) {
        searchInputs[0].focus();
    }
}

function focusFirstFormInput() {
    const firstInput = document.querySelector('form input:not([type="hidden"]), form select, form textarea');
    if (firstInput) {
        firstInput.focus();
    }
}

// Form helper functions
function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        form.classList.remove('was-validated');
        
        // Clear custom validations
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.classList.remove('is-invalid', 'is-valid');
            input.setCustomValidity('');
        });
        
        // Reset dynamic elements
        const dynamicElements = form.querySelectorAll('.pay-rate-container');
        dynamicElements.forEach(element => {
            element.style.display = 'none';
        });
    }
}

// Copy to clipboard function
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard!', 'success', 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showNotification('Copied to clipboard!', 'success', 2000);
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        showNotification('Failed to copy to clipboard', 'error');
    }
    
    document.body.removeChild(textArea);
}

// Date and time utilities
function formatDate(date, format = 'dd/mm/yyyy') {
    const d = new Date(date);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    
    switch (format) {
        case 'dd/mm/yyyy':
            return `${day}/${month}/${year}`;
        case 'yyyy-mm-dd':
            return `${year}-${month}-${day}`;
        default:
            return d.toLocaleDateString();
    }
}

function formatTime(time) {
    return new Date(`1970-01-01T${time}:00`).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

// Currency formatting
function formatCurrency(amount, currency = '₹') {
    const formatted = parseFloat(amount).toFixed(2);
    return `${currency}${formatted}`;
}

// Form data helpers
function serializeForm(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        if (data[key]) {
            if (Array.isArray(data[key])) {
                data[key].push(value);
            } else {
                data[key] = [data[key], value];
            }
        } else {
            data[key] = value;
        }
    }
    
    return data;
}

// Local storage helpers
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
        console.error('Error saving to localStorage:', error);
    }
}

function loadFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    } catch (error) {
        console.error('Error loading from localStorage:', error);
        return null;
    }
}

// Theme and preferences
function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.body.setAttribute('data-theme', newTheme);
    saveToLocalStorage('theme', newTheme);
    
    showNotification(`Switched to ${newTheme} theme`, 'info', 2000);
}

// Initialize theme from localStorage
function initializeTheme() {
    const savedTheme = loadFromLocalStorage('theme');
    if (savedTheme) {
        document.body.setAttribute('data-theme', savedTheme);
    }
}

// Performance monitoring
function measurePageLoadTime() {
    window.addEventListener('load', function() {
        const loadTime = performance.now();
        console.log(`Page loaded in ${loadTime.toFixed(2)}ms`);
        
        // Log to analytics if needed
        if (loadTime > 3000) {
            console.warn('Page load time is over 3 seconds');
        }
    });
}

// Error handling
window.addEventListener('error', function(event) {
    console.error('JavaScript error:', event.error);
    
    // Show user-friendly error message
    showNotification('An error occurred. Please refresh the page.', 'error');
});

// Initialize performance monitoring
measurePageLoadTime();

// Export functions for use in other scripts
window.MentorscueApp = {
    copyToClipboard,
    showNotification,
    formatDate,
    formatTime,
    formatCurrency,
    resetForm,
    saveToLocalStorage,
    loadFromLocalStorage,
    toggleTheme
};
