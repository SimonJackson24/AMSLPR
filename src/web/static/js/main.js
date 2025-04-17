/**
 * AMSLPR - Main JavaScript File
 */

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Add event listener for plate number input to enforce uppercase
    var plateNumberInputs = document.querySelectorAll('input[name="plate_number"]');
    plateNumberInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
        });
    });
    
    // Add fade-in animation to cards
    // document.querySelectorAll('.card').forEach(function(card, index) {
    //     card.classList.add('fade-in');
    //     card.style.animationDelay = (index * 0.1) + 's';
    // });
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add active class to table rows when clicked
    document.querySelectorAll('table.table-hover tr').forEach(row => {
        row.addEventListener('click', function() {
            const isActive = this.classList.contains('table-active');
            
            // Remove active class from all rows
            this.closest('table').querySelectorAll('tr').forEach(r => {
                r.classList.remove('table-active');
            });
            
            // Add active class to clicked row if it wasn't active before
            if (!isActive) {
                this.classList.add('table-active');
            }
        });
    });
    
    // Initialize any DataTables
    if (typeof $.fn.DataTable !== 'undefined') {
        $('.datatable').DataTable({
            responsive: true,
            language: {
                search: "<i class='fas fa-search'></i> Search:",
                paginate: {
                    first: "<i class='fas fa-angle-double-left'></i>",
                    last: "<i class='fas fa-angle-double-right'></i>",
                    next: "<i class='fas fa-angle-right'></i>",
                    previous: "<i class='fas fa-angle-left'></i>"
                }
            }
        });
    }
    
    // Create overlay for mobile sidebar
    var overlay = document.createElement('div');
    overlay.id = 'sidebar-overlay';
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);
    
    // Make overlay close the sidebar when clicked
    overlay.addEventListener('click', function() {
        var sidebar = document.getElementById('sidebar');
        var content = document.getElementById('content');
        if (sidebar) {
            sidebar.classList.remove('active');
            if (content) content.classList.remove('active');
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
    
    /**
     * Format date and time for display
     * @param {string} dateTimeString - ISO date time string
     * @returns {string} - Formatted date time string
     */
    function formatDateTime(dateTimeString) {
        if (!dateTimeString) return '-';
        
        const date = new Date(dateTimeString);
        return date.toLocaleString();
    }

    /**
     * Format currency
     * @param {number} amount - Amount to format
     * @param {string} currency - Currency code (default: USD)
     * @returns {string} - Formatted currency string
     */
    function formatCurrency(amount, currency = 'USD') {
        if (amount === null || amount === undefined) return '-';
        
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    /**
     * Confirm deletion of an item
     * @param {string} message - Confirmation message
     * @returns {boolean} - True if confirmed, false otherwise
     */
    function confirmDelete(message) {
        return confirm(message || 'Are you sure you want to delete this item?');
    }

    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type of toast (success, error, warning, info)
     */
    function showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        // Create toast content
        const toastContent = document.createElement('div');
        toastContent.className = 'd-flex';
        
        const toastBody = document.createElement('div');
        toastBody.className = 'toast-body';
        toastBody.textContent = message;
        
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close btn-close-white me-2 m-auto';
        closeButton.setAttribute('data-bs-dismiss', 'toast');
        closeButton.setAttribute('aria-label', 'Close');
        
        // Assemble toast
        toastContent.appendChild(toastBody);
        toastContent.appendChild(closeButton);
        toastEl.appendChild(toastContent);
        toastContainer.appendChild(toastEl);
        
        // Initialize and show toast
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        
        // Remove toast after it's hidden
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    }

    // AMSLPR Main JavaScript
    
    // Sidebar toggle - get sidebar elements once
    var sidebar = document.getElementById('sidebar');
    var content = document.getElementById('content');
    var sidebarCollapse = document.getElementById('sidebarCollapse');
    var sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
    var overlay = document.getElementById('sidebar-overlay');
    
    function toggleSidebar() {
        if (sidebar) {
            sidebar.classList.toggle('active');
            
            if (content) {
                content.classList.toggle('active');
            }
            
            // For mobile, handle overlay
            if (window.innerWidth <= 768) {
                if (sidebar.classList.contains('active')) {
                    if (overlay) overlay.classList.add('active');
                    document.body.style.overflow = 'hidden'; // Prevent scrolling
                } else {
                    if (overlay) overlay.classList.remove('active');
                    document.body.style.overflow = ''; // Allow scrolling
                }
            }
        }
    }
    
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', toggleSidebar);
    }
    
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', toggleSidebar);
    }

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation
    (function() {
        'use strict';
        window.addEventListener('load', function() {
            var forms = document.getElementsByClassName('needs-validation');
            Array.prototype.filter.call(forms, function(form) {
                form.addEventListener('submit', function(event) {
                    if (form.checkValidity() === false) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                    form.classList.add('was-validated');
                }, false);
            });
        }, false);
    })();

    // Update current time
    function updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        const timeElement = document.getElementById('currentTime');
        if (timeElement) {
            timeElement.textContent = timeString;
        }
    }

    // Update time every second
    setInterval(updateTime, 1000);
    updateTime();
})
