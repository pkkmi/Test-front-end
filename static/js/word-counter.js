/**
 * Word Counter Script for Andikar AI
 * Provides real-time word counting and validation against user tier limits
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get references to the text area and counter elements
    const textArea = document.getElementById('original_text');
    const wordCountElement = document.getElementById('word-count');
    const wordLimitElement = document.getElementById('word-limit');
    const submitButton = document.querySelector('button[type="submit"]');
    const progressBar = document.getElementById('word-count-progress');
    
    // Get the word limit from the page
    let wordLimit = wordLimitElement ? parseInt(wordLimitElement.getAttribute('data-limit')) : 0;
    
    // Function to count words in text
    function countWords(text) {
        // Remove extra whitespace and split by whitespace
        return text.trim().split(/\s+/).filter(word => word.length > 0).length;
    }
    
    // Function to update the word count display
    function updateWordCount() {
        if (!textArea || !wordCountElement) return;
        
        const text = textArea.value;
        const count = countWords(text);
        
        // Update word count display
        wordCountElement.textContent = count;
        
        // Update progress bar if it exists
        if (progressBar && wordLimit > 0) {
            const percentage = Math.min((count / wordLimit) * 100, 100);
            progressBar.style.width = percentage + '%';
            
            // Change progress bar color based on word count
            if (percentage < 70) {
                progressBar.className = 'progress-bar bg-success';
            } else if (percentage < 90) {
                progressBar.className = 'progress-bar bg-warning';
            } else {
                progressBar.className = 'progress-bar bg-danger';
            }
        }
        
        // Disable submit button if word count exceeds limit
        if (submitButton && wordLimit > 0) {
            if (count > wordLimit) {
                submitButton.disabled = true;
                submitButton.title = `Text exceeds your word limit of ${wordLimit} words`;
                
                // Add warning message if it doesn't exist
                if (!document.getElementById('word-limit-warning')) {
                    const warningDiv = document.createElement('div');
                    warningDiv.id = 'word-limit-warning';
                    warningDiv.className = 'alert alert-danger mt-2';
                    warningDiv.innerHTML = `
                        <strong>Word limit exceeded!</strong> 
                        Your current plan allows a maximum of ${wordLimit} words per request.
                        Please reduce your text or <a href="/upgrade">upgrade your plan</a>.
                    `;
                    textArea.parentNode.appendChild(warningDiv);
                }
            } else {
                submitButton.disabled = false;
                submitButton.title = '';
                
                // Remove warning message if it exists
                const warningDiv = document.getElementById('word-limit-warning');
                if (warningDiv) {
                    warningDiv.remove();
                }
            }
        }
    }
    
    // Add event listener for text input
    if (textArea) {
        textArea.addEventListener('input', updateWordCount);
        
        // Initialize word count on page load
        updateWordCount();
    }
    
    // Add event listener for paste events to catch large text pastes
    if (textArea) {
        textArea.addEventListener('paste', function() {
            // Use setTimeout to ensure the pasted content is in the textarea
            setTimeout(updateWordCount, 10);
        });
    }
});
