"""
Authentication System Backup - Original Implementation
Created: April 5, 2025

This file contains a backup of the original authentication system before implementing Google OAuth.
It includes the relevant code from app.py, login routes, and session management.

To restore: Copy the relevant sections back to their original files.
"""

# =============== ORIGINAL LOGIN ROUTE FROM APP.PY ===============
"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basic validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('login.html')
        
        # Special case for demo account
        if username == 'demo' and password == 'demo':
            session['user_id'] = 'demo'
            flash('Logged in as demo user', 'success')
            return redirect(url_for('humanize'))
        
        # Verify user credentials
        success, result = verify_user(username, password)
        
        if success:
            # Store user info in session
            session['user_id'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('humanize'))
        else:
            flash(f'Login failed: {result}', 'danger')
            return render_template('login.html')
    
    # GET request - display login form
    return render_template('login.html')
"""

# =============== ORIGINAL REGISTER ROUTE FROM APP.PY ===============
"""
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email', '')
        
        # Basic validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('register.html')
        
        # Add user to database
        success, message = add_user(username, password, email)
        
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Registration failed: {message}', 'danger')
            return render_template('register.html')
    
    # GET request - display registration form
    return render_template('register.html')
"""

# =============== ORIGINAL LOGOUT ROUTE FROM APP.PY ===============
"""
@app.route('/logout')
def logout():
    """Handle user logout."""
    # Clear session data
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))
"""

# =============== ORIGINAL SESSION CHECK PATTERN ===============
"""
# Check if user is logged in
if 'user_id' not in session:
    flash('Please log in to access this feature', 'warning')
    return redirect(url_for('login'))
"""

# =============== ORIGINAL LOGIN.HTML TEMPLATE ===============
"""
{% extends 'base.html' %}

{% block title %}Login - Andikar AI{% endblock %}

{% block content %}
<div class="container mt-5">
  <div class="row">
    <div class="col-md-6 offset-md-3">
      <div class="card shadow-sm">
        <div class="card-header bg-primary text-white">
          <h2 class="mb-0">Login</h2>
        </div>
        <div class="card-body">
          <form method="POST" action="{{ url_for('login') }}">
            <div class="form-group">
              <label for="username">Username</label>
              <div class="input-group">
                <div class="input-group-prepend">
                  <span class="input-group-text"><i class="fas fa-user"></i></span>
                </div>
                <input type="text" class="form-control" id="username" name="username" required>
              </div>
            </div>
            
            <div class="form-group">
              <label for="password">Password</label>
              <div class="input-group">
                <div class="input-group-prepend">
                  <span class="input-group-text"><i class="fas fa-lock"></i></span>
                </div>
                <input type="password" class="form-control" id="password" name="password" required>
              </div>
            </div>
            
            <div class="form-group form-check">
              <input type="checkbox" class="form-check-input" id="remember">
              <label class="form-check-label" for="remember">Remember me</label>
            </div>
            
            <button type="submit" class="btn btn-primary btn-block">
              <i class="fas fa-sign-in-alt mr-2"></i> Login
            </button>
          </form>
          
          <hr>
          
          <div class="text-center">
            <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
            
            <div class="demo-login mt-4">
              <p class="text-muted">Try our demo account:</p>
              <form method="POST" action="{{ url_for('login') }}">
                <input type="hidden" name="username" value="demo">
                <input type="hidden" name="password" value="demo">
                <button type="submit" class="btn btn-outline-secondary">
                  <i class="fas fa-user-circle mr-2"></i> Login as Demo User
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
"""

# =============== ORIGINAL DATABASE USER SCHEMA ===============
"""
User schema:
{
    "username": str,
    "password_hash": str,
    "email": str,
    "joined_at": datetime,
    "usage": {
        "total_words": int,
        "monthly_words": int,
        "last_usage": datetime
    },
    "plan": {
        "name": str,
        "monthly_limit": int,
    }
}
"""

# Instructions to restore:
"""
To restore the original authentication system:

1. Replace the login, register, and logout routes in app.py with their original versions
2. Restore the login.html template
3. Make sure the database schema matches the original structure
4. Remove any OAuth-specific dependencies from requirements.txt
5. Remove any Google OAuth configuration files
"""
