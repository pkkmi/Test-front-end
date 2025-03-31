/**
 * Andikar AI - Main JavaScript File
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    setTimeout(function() {
        const flashMessages = document.querySelectorAll('.alert');
        flashMessages.forEach(function(message) {
            // Create close button if it doesn't exist
            if (!message.querySelector('.close')) {
                const closeButton = document.createElement('button');
                closeButton.className = 'close';
                closeButton.setAttribute('type', 'button');
                closeButton.setAttribute('data-dismiss', 'alert');
                closeButton.setAttribute('aria-label', 'Close');
                closeButton.innerHTML = '<span aria-hidden="true">&times;</span>';
                message.prepend(closeButton);
            }
            
            // Add fade out class
            message.classList.add('fade');
            
            // Use Bootstrap's alert dismiss
            $(message).alert('close');
        });
    }, 5000);
    
    // Add active class to current nav item
    const currentLocation = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentLocation) {
            link.classList.add('active');
        }
    });
    
    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('button[onclick*="clipboard"]');
    
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check mr-2"></i> Copied!';
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-success');
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-secondary');
            }, 2000);
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });
});
