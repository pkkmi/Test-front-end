// Main JavaScript for AndikarAI

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    
    // Setup word counter for text areas
    setupWordCounter();
    
    // Setup auto dismiss for flash messages
    setupFlashMessageDismiss();
    
    // Setup browser detection and warning
    detectBrowserCompatibility();
    
    // Fix for Edge browser redirects
    fixEdgeRedirects();
});

// Setup word counter for textarea inputs
function setupWordCounter() {
    const textareas = document.querySelectorAll('textarea[data-word-count]');
    
    textareas.forEach(textarea => {
        const counterId = textarea.dataset.wordCount;
        const counter = document.getElementById(counterId);
        
        if (counter) {
            // Count words initially
            updateWordCount(textarea, counter);
            
            // Update count on input
            textarea.addEventListener('input', function() {
                updateWordCount(textarea, counter);
            });
        }
    });
}

// Update word count for a textarea
function updateWordCount(textarea, counter) {
    const text = textarea.value.trim();
    const words = text ? text.split(/\s+/).length : 0;
    counter.textContent = words;
    
    // Also update any API endpoint for word counting
    const wordCountUrl = document.body.dataset.wordCountUrl;
    if (wordCountUrl && words > 0) {
        // Only send API requests for non-empty text and if feature is enabled
        fetch(wordCountUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text
            })
        })
        .then(response => response.json())
        .then(data => {
            // API might have a more accurate count
            if (data.word_count !== undefined) {
                counter.textContent = data.word_count;
            }
        })
        .catch(error => {
            console.error('Error counting words via API:', error);
        });
    }
}

// Auto-dismiss flash messages after a delay
function setupFlashMessageDismiss() {
    const flashMessages = document.querySelectorAll('.alert');
    
    flashMessages.forEach(message => {
        // Add click handler for manual dismiss
        const closeButton = message.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                message.remove();
            });
        }
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            if (message && message.parentNode) {
                message.classList.add('fade');
                setTimeout(() => message.remove(), 500);
            }
        }, 5000);
    });
}

// Detect browser compatibility
function detectBrowserCompatibility() {
    // Check if the browser supports required features
    const isCompatible = 
        'fetch' in window && 
        'Promise' in window &&
        'localStorage' in window;
    
    if (!isCompatible) {
        // Add a warning for incompatible browsers
        const header = document.querySelector('header');
        if (header) {
            const warning = document.createElement('div');
            warning.className = 'alert alert-warning text-center mb-0';
            warning.innerHTML = 'Your browser may not support all features. Please consider upgrading to a modern browser.';
            header.insertAdjacentElement('afterend', warning);
        }
    }
    
    // Add special handling for Microsoft Edge
    const isEdge = navigator.userAgent.indexOf("Edg") !== -1;
    if (isEdge) {
        console.log("Microsoft Edge detected - enabling compatibility mode");
        document.body.classList.add('browser-edge');
    }
}

// Fix for Edge browser redirects
function fixEdgeRedirects() {
    // Fix Edge browser's tendency to cache redirects incorrectly
    const isEdge = navigator.userAgent.indexOf("Edg") !== -1;
    if (isEdge) {
        // Prevent page not found errors after login on Edge
        if (window.location.pathname === '/' && document.querySelector('.alert-warning')) {
            // If we're on home page with a warning message, it might be the "page not found" error
            const warningMessages = document.querySelectorAll('.alert-warning');
            warningMessages.forEach(message => {
                if (message.textContent.includes('page you requested was not found')) {
                    // If logged in, redirect to humanize page
                    if (document.body.classList.contains('logged-in') || 
                        document.querySelector('[data-user-logged-in="true"]')) {
                        window.location.href = '/humanize';
                    }
                    // Remove the warning
                    message.remove();
                }
            });
        }
        
        // Check if the user is logged in but seeing the home page
        const isLoggedIn = document.body.classList.contains('logged-in') || 
                           document.querySelector('[data-user-logged-in="true"]');
        if (isLoggedIn && window.location.pathname === '/') {
            window.location.href = '/humanize';
        }
    }
}

// Handle login button interactions
document.addEventListener('click', function(event) {
    // Check for login button clicks
    if (event.target.matches('#login-button, .login-button')) {
        event.preventDefault();
        
        // Get the login URL from the button
        const loginUrl = event.target.getAttribute('href') || '/login';
        
        // For Edge browser, add a cache-busting parameter
        const isEdge = navigator.userAgent.indexOf("Edg") !== -1;
        if (isEdge) {
            const separator = loginUrl.includes('?') ? '&' : '?';
            const cacheBuster = `${separator}_=${Date.now()}`;
            window.location.href = loginUrl + cacheBuster;
        } else {
            window.location.href = loginUrl;
        }
    }
});
