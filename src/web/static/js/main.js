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
    
    // Sidebar toggle functionality
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    // Function to toggle sidebar
    function toggleSidebar() {
        sidebar.classList.toggle('active');
        content.classList.toggle('active');
        
        // Save sidebar state to localStorage
        const isSidebarActive = sidebar.classList.contains('active');
        localStorage.setItem('sidebarCollapsed', isSidebarActive);
    }
    
    // Add click event to sidebar toggle buttons
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', toggleSidebar);
    }
    
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    // Load saved sidebar state
    window.addEventListener('load', function() {
        const isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        
        // If on desktop and sidebar should be collapsed
        if (window.innerWidth > 768) {
            if (isSidebarCollapsed && sidebar) {
                sidebar.classList.add('active');
                if (content) content.classList.add('active');
            }
        } else {
            // On mobile, sidebar is always collapsed by default
            if (sidebar) {
                sidebar.classList.remove('active');
            }
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768) {
            // On mobile, adjust content and sidebar
            if (sidebar) {
                if (sidebar.classList.contains('active')) {
                    // If sidebar is visible on mobile
                    if (content) content.classList.remove('active');
                } else {
                    // If sidebar is hidden on mobile
                    if (content) content.classList.remove('active');
                }
            }
        } else {
            // On desktop
            const isSidebarCollapsed = sidebar.classList.contains('active');
            if (isSidebarCollapsed) {
                if (content) content.classList.add('active');
            } else {
                if (content) content.classList.remove('active');
            }
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
