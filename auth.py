from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db
from datetime import datetime

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            user.last_login = datetime.utcnow()
            user.remember_me = remember_me
            db.session.commit()
            
            login_user(user, remember=remember_me)
            
            # Trigger invoice generation for non-tutor users
            if not user.is_tutor_user():
                from utils import check_and_generate_invoices
                check_and_generate_invoices()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Redirect based on role
            if user.is_tutor_user():
                return redirect(url_for('main.tutor_dashboard'))
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))
