from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import os
import zipfile
import tempfile

from app import app, db
from models import (User, Role, Student, Tutor, Attendance, StudentInvoice, 
                   TutorReceipt, Permission, student_tutors, Announcement, Settings)
from utils import permission_required, admin_required
from pdf_generator import generate_student_invoice_pdf, generate_tutor_receipt_pdf
from auth import auth

# Register blueprints
app.register_blueprint(auth)

# Make Permission class available in templates
@app.context_processor
def inject_permissions():
    return dict(Permission=Permission, User=User, Role=Role, Student=Student, Tutor=Tutor, 
                Attendance=Attendance, StudentInvoice=StudentInvoice, 
                TutorReceipt=TutorReceipt, Announcement=Announcement, Settings=Settings,
                datetime=datetime, db=db, timedelta=timedelta)

# Main routes
@app.route('/')
@login_required
def dashboard():
    if current_user.is_tutor_user():
        return redirect(url_for('tutor_dashboard'))
    
    # Prepare dashboard data
    if current_user.is_admin():
        # Admin Dashboard Data
        total_users = User.query.count()
        total_roles = Role.query.count()
        active_users = User.query.filter(User.last_login.isnot(None)).count()
        total_documents = StudentInvoice.query.count() + TutorReceipt.query.count()
        
        # Financial summary
        total_revenue = db.session.query(db.func.sum(StudentInvoice.total_amount)).filter_by(status='Paid').scalar() or 0
        pending_revenue = db.session.query(db.func.sum(StudentInvoice.total_amount)).filter_by(status='Due').scalar() or 0
        total_expenses = db.session.query(db.func.sum(TutorReceipt.total_earnings)).filter_by(status='Paid').scalar() or 0
        pending_expenses = db.session.query(db.func.sum(TutorReceipt.total_earnings)).filter_by(status='Due').scalar() or 0
        
        # System alerts
        inactive_users = User.query.filter_by(is_active=False).count()
        overdue_invoices = StudentInvoice.query.filter_by(status='Due').count()
        pending_receipts = TutorReceipt.query.filter_by(status='Due').count()
        
        # User role distribution
        user_roles = {}
        for user in User.query.all():
            for role in user.roles:
                user_roles[role.name] = user_roles.get(role.name, 0) + 1
        
        # Recent activity (last 10 logins)
        recent_users = User.query.filter(User.last_login.isnot(None)).order_by(User.last_login.desc()).limit(10).all()
        
        return render_template('admin_dashboard.html',
                             total_users=total_users,
                             total_roles=total_roles,
                             active_users=active_users,
                             total_documents=total_documents,
                             total_revenue=total_revenue,
                             pending_revenue=pending_revenue,
                             total_expenses=total_expenses,
                             pending_expenses=pending_expenses,
                             inactive_users=inactive_users,
                             overdue_invoices=overdue_invoices,
                             pending_receipts=pending_receipts,
                             user_roles=user_roles,
                             recent_users=recent_users)
    else:
        return render_template('dashboard.html')

@app.route('/tutor-dashboard')
@login_required
def tutor_dashboard():
    if not current_user.is_tutor_user():
        return redirect(url_for('dashboard'))
    
    # Get tutor profile
    tutor = Tutor.query.filter_by(mobile=current_user.mobile).first()
    if not tutor:
        flash('Tutor profile not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Get recent attendance
    recent_attendance = Attendance.query.filter_by(tutor_id=tutor.id)\
        .order_by(Attendance.created_at.desc()).limit(10).all()
    
    # Get assigned students
    assigned_students = tutor.students
    
    return render_template('tutor_dashboard.html', 
                         tutor=tutor, 
                         recent_attendance=recent_attendance,
                         assigned_students=assigned_students)

# Student management routes
@app.route('/students')
@login_required
@permission_required(Permission.VIEW_STUDENTS)
def students_list():
    students = Student.query.all()
    return render_template('students_list.html', students=students)

@app.route('/students/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADD_STUDENTS)
def add_student():
    if request.method == 'POST':
        try:
            student = Student(
                full_name=request.form['full_name'],
                parent_name=request.form['parent_name'],
                parent_whatsapp=request.form['parent_whatsapp'],
                class_level=request.form['class_level'],
                subjects=request.form['subjects'],
                per_class_fee=float(request.form['per_class_fee'])
            )
            
            db.session.add(student)
            db.session.flush()  # Get the student ID
            
            # Handle tutor assignments
            tutor_ids = request.form.getlist('tutor_ids')
            for tutor_id in tutor_ids:
                if tutor_id:
                    pay_rate = float(request.form.get(f'pay_rate_{tutor_id}', 0))
                    # Insert into association table with pay rate
                    db.session.execute(
                        student_tutors.insert().values(
                            student_id=student.id,
                            tutor_id=int(tutor_id),
                            pay_per_class=pay_rate
                        )
                    )
            
            db.session.commit()
            flash('Student added successfully', 'success')
            return redirect(url_for('students_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'error')
    
    tutors = Tutor.query.filter_by(status='Active').all()
    return render_template('add_student.html', tutors=tutors)

@app.route('/students/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.EDIT_STUDENTS)
def edit_student(id):
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            student.full_name = request.form['full_name']
            student.parent_name = request.form['parent_name']
            student.parent_whatsapp = request.form['parent_whatsapp']
            student.class_level = request.form['class_level']
            student.subjects = request.form['subjects']
            student.per_class_fee = float(request.form['per_class_fee'])
            
            # Clear existing tutor assignments
            db.session.execute(
                student_tutors.delete().where(student_tutors.c.student_id == id)
            )
            
            # Add new tutor assignments
            tutor_ids = request.form.getlist('tutor_ids')
            for tutor_id in tutor_ids:
                if tutor_id:
                    pay_rate = float(request.form.get(f'pay_rate_{tutor_id}', 0))
                    db.session.execute(
                        student_tutors.insert().values(
                            student_id=student.id,
                            tutor_id=int(tutor_id),
                            pay_per_class=pay_rate
                        )
                    )
            
            db.session.commit()
            flash('Student updated successfully', 'success')
            return redirect(url_for('students_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating student: {str(e)}', 'error')
    
    tutors = Tutor.query.filter_by(status='Active').all()
    
    # Get current tutor assignments with pay rates
    current_assignments = db.session.execute(
        db.text("SELECT tutor_id, pay_per_class FROM student_tutors WHERE student_id = :sid"),
        {"sid": id}
    ).fetchall()
    
    assigned_tutors = {row[0]: row[1] for row in current_assignments}
    
    return render_template('edit_student.html', 
                         student=student, 
                         tutors=tutors, 
                         assigned_tutors=assigned_tutors)

@app.route('/students/<int:id>')
@login_required
@permission_required(Permission.VIEW_STUDENTS)
def student_profile(id):
    student = Student.query.get_or_404(id)
    
    # Get attendance records
    attendance_records = Attendance.query.filter_by(student_id=id)\
        .order_by(Attendance.date_recorded.desc()).limit(50).all()
    
    # Get invoices
    invoices = StudentInvoice.query.filter_by(student_id=id)\
        .order_by(StudentInvoice.generated_at.desc()).limit(6).all()
    
    # Get assigned tutors with pay rates
    tutor_assignments = db.session.execute(
        db.text("""
            SELECT t.id, t.full_name, st.pay_per_class 
            FROM tutor t 
            JOIN student_tutors st ON t.id = st.tutor_id 
            WHERE st.student_id = :sid
        """),
        {"sid": id}
    ).fetchall()
    
    return render_template('student_profile.html', 
                         student=student, 
                         attendance_records=attendance_records,
                         invoices=invoices,
                         tutor_assignments=tutor_assignments)

# Tutor management routes
@app.route('/tutors')
@login_required
@permission_required(Permission.VIEW_TUTORS)
def tutors_list():
    tutors = Tutor.query.all()
    return render_template('tutors_list.html', tutors=tutors)

@app.route('/tutors/add', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ADD_TUTORS)
def add_tutor():
    if request.method == 'POST':
        try:
            # Create tutor
            tutor = Tutor(
                full_name=request.form['full_name'],
                date_of_birth=datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date(),
                mobile=request.form['mobile'],
                upi_id=request.form.get('upi_id', '')
            )
            
            # Generate username and password
            tutor.username = tutor.generate_username()
            tutor.password = tutor.mobile  # Default password is mobile number
            
            db.session.add(tutor)
            db.session.flush()
            
            # Create user account for tutor
            tutor_role = Role.query.filter_by(name='Tutor').first()
            user = User(
                username=tutor.username,
                full_name=tutor.full_name,
                mobile=tutor.mobile
            )
            user.set_password(tutor.password)
            user.roles.append(tutor_role)
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'Tutor added successfully. Username: {tutor.username}, Password: {tutor.password}', 'success')
            return redirect(url_for('tutors_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding tutor: {str(e)}', 'error')
    
    return render_template('add_tutor.html')

@app.route('/tutors/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.EDIT_TUTORS)
def edit_tutor(id):
    tutor = Tutor.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            tutor.full_name = request.form['full_name']
            tutor.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()
            tutor.mobile = request.form['mobile']
            tutor.upi_id = request.form.get('upi_id', '')
            
            # Update username if needed
            new_username = tutor.generate_username()
            if new_username != tutor.username:
                tutor.username = new_username
            
            db.session.commit()
            flash('Tutor updated successfully', 'success')
            return redirect(url_for('tutors_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating tutor: {str(e)}', 'error')
    
    return render_template('edit_tutor.html', tutor=tutor)

@app.route('/tutors/<int:id>')
@login_required
@permission_required(Permission.VIEW_TUTORS)
def tutor_profile(id):
    tutor = Tutor.query.get_or_404(id)
    
    # Get attendance records
    attendance_records = Attendance.query.filter_by(tutor_id=id)\
        .order_by(Attendance.date_recorded.desc()).limit(50).all()
    
    # Get receipts
    receipts = TutorReceipt.query.filter_by(tutor_id=id)\
        .order_by(TutorReceipt.generated_at.desc()).limit(6).all()
    
    # Get assigned students
    assigned_students = tutor.students
    
    return render_template('tutor_profile.html', 
                         tutor=tutor, 
                         attendance_records=attendance_records,
                         receipts=receipts,
                         assigned_students=assigned_students)

# Attendance routes
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.SUBMIT_ATTENDANCE)
def attendance():
    if request.method == 'POST':
        try:
            start_time = datetime.strptime(
                f"{request.form['date']} {request.form['start_time']}", 
                '%Y-%m-%d %H:%M'
            )
            end_time = datetime.strptime(
                f"{request.form['date']} {request.form['end_time']}", 
                '%Y-%m-%d %H:%M'
            )
            
            attendance_record = Attendance(
                student_id=int(request.form['student_id']),
                tutor_id=int(request.form['tutor_id']),
                subject=request.form['subject'],
                start_time=start_time,
                end_time=end_time,
                duration_minutes=int((end_time - start_time).total_seconds() / 60),
                rating=int(request.form['rating']),
                remarks=request.form.get('remarks', ''),
                date_recorded=start_time.date()
            )
            
            db.session.add(attendance_record)
            db.session.commit()
            
            flash('Attendance recorded successfully', 'success')
            return redirect(url_for('attendance'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error recording attendance: {str(e)}', 'error')
    
    # Get students and tutors for form
    if current_user.is_tutor_user():
        tutor = Tutor.query.filter_by(mobile=current_user.mobile).first()
        students = tutor.students if tutor else []
        tutors = [tutor] if tutor else []
    else:
        students = Student.query.filter_by(status='Active').all()
        tutors = Tutor.query.filter_by(status='Active').all()
    
    return render_template('attendance.html', students=students, tutors=tutors)

# Invoice routes
@app.route('/invoices')
@login_required
@permission_required(Permission.VIEW_INVOICES)
def invoices():
    # Get student invoices
    student_invoices = StudentInvoice.query.order_by(StudentInvoice.generated_at.desc()).all()
    
    # Get tutor receipts
    tutor_receipts = TutorReceipt.query.order_by(TutorReceipt.generated_at.desc()).all()
    
    return render_template('invoices.html', 
                         student_invoices=student_invoices,
                         tutor_receipts=tutor_receipts)

@app.route('/invoices/student/<int:id>/download')
@login_required
@permission_required(Permission.DOWNLOAD_INVOICES)
def download_student_invoice(id):
    invoice = StudentInvoice.query.get_or_404(id)
    
    pdf_bytes = generate_student_invoice_pdf(invoice)
    if pdf_bytes:
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice.invoice_number}.pdf'
        return response
    else:
        flash('Error generating PDF', 'error')
        return redirect(url_for('invoices'))

@app.route('/invoices/tutor/<int:id>/download')
@login_required
@permission_required(Permission.DOWNLOAD_INVOICES)
def download_tutor_receipt(id):
    receipt = TutorReceipt.query.get_or_404(id)
    
    pdf_bytes = generate_tutor_receipt_pdf(receipt)
    if pdf_bytes:
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=receipt_{receipt.receipt_number}.pdf'
        return response
    else:
        flash('Error generating PDF', 'error')
        return redirect(url_for('invoices'))

@app.route('/invoices/student/<int:id>/mark-paid', methods=['POST'])
@login_required
@permission_required(Permission.MARK_PAYMENTS)
def mark_student_invoice_paid(id):
    invoice = StudentInvoice.query.get_or_404(id)
    
    amount_paid = float(request.form.get('amount_paid', invoice.total_amount))
    
    invoice.amount_paid = amount_paid
    if amount_paid >= invoice.total_amount:
        invoice.status = 'Paid'
    elif amount_paid > 0:
        invoice.status = 'Partial'
    else:
        invoice.status = 'Due'
    
    db.session.commit()
    flash('Payment status updated successfully', 'success')
    return redirect(url_for('invoices'))

# Admin routes
@app.route('/admin/users')
@login_required
@permission_required(Permission.MANAGE_USERS)
def user_management():
    users = User.query.all()
    roles = Role.query.all()
    return render_template('user_management.html', users=users, roles=roles)

@app.route('/admin/users/add', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def add_user():
    try:
        user = User(
            username=request.form['username'],
            full_name=request.form.get('full_name', ''),
            email=request.form.get('email', ''),
            mobile=request.form.get('mobile', ''),
            is_active=bool(request.form.get('is_active'))
        )
        user.set_password(request.form['password'])
        
        # Assign roles
        role_ids = request.form.getlist('role_ids')
        for role_id in role_ids:
            role = Role.query.get(int(role_id))
            if role:
                user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()
        
        flash('User added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding user: {str(e)}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/admin/users/<int:id>/edit', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def edit_user(id):
    user = User.query.get_or_404(id)
    
    try:
        user.username = request.form['username']
        user.full_name = request.form.get('full_name', '')
        user.email = request.form.get('email', '')
        user.mobile = request.form.get('mobile', '')
        user.is_active = bool(request.form.get('is_active'))
        
        # Update roles
        user.roles.clear()
        role_ids = request.form.getlist('role_ids')
        for role_id in role_ids:
            role = Role.query.get(int(role_id))
            if role:
                user.roles.append(role)
        
        db.session.commit()
        flash('User updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/admin/users/<int:id>/reset-password', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def reset_user_password(id):
    user = User.query.get_or_404(id)
    
    try:
        new_password = request.form['new_password']
        user.set_password(new_password)
        db.session.commit()
        
        flash(f'Password reset successfully for user {user.username}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'error')
    
    return redirect(url_for('user_management'))

@app.route('/admin/roles')
@login_required
@permission_required(Permission.MANAGE_ROLES)
def roles_permissions():
    roles = Role.query.all()
    return render_template('roles_permissions.html', roles=roles)

@app.route('/admin/roles/add', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_ROLES)
def add_role():
    try:
        role = Role(
            name=request.form['name'],
            description=request.form.get('description', ''),
            is_custom=True,
            is_default=bool(request.form.get('is_default'))
        )
        
        # Calculate permissions
        permissions = request.form.getlist('permissions')
        total_permissions = sum(int(p) for p in permissions)
        role.permissions = total_permissions
        
        # If this is set as default, remove default from other roles
        if role.is_default:
            Role.query.filter_by(is_default=True).update({'is_default': False})
        
        db.session.add(role)
        db.session.commit()
        
        flash('Role created successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating role: {str(e)}', 'error')
    
    return redirect(url_for('roles_permissions'))

@app.route('/admin/roles/<int:id>/edit', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_ROLES)
def edit_role(id):
    role = Role.query.get_or_404(id)
    
    # Prevent editing system roles
    if not role.is_custom:
        flash('Cannot edit system roles', 'error')
        return redirect(url_for('roles_permissions'))
    
    try:
        role.name = request.form['name']
        role.description = request.form.get('description', '')
        
        # Calculate permissions
        permissions = request.form.getlist('permissions')
        total_permissions = sum(int(p) for p in permissions)
        role.permissions = total_permissions
        
        db.session.commit()
        flash('Role updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating role: {str(e)}', 'error')
    
    return redirect(url_for('roles_permissions'))

@app.route('/admin/roles/<int:id>/delete', methods=['POST'])
@login_required
@permission_required(Permission.MANAGE_ROLES)
def delete_role(id):
    role = Role.query.get_or_404(id)
    
    # Prevent deleting system roles
    if not role.is_custom:
        flash('Cannot delete system roles', 'error')
        return redirect(url_for('roles_permissions'))
    
    # Check if role has users
    if role.users:
        flash('Cannot delete role that has users assigned', 'error')
        return redirect(url_for('roles_permissions'))
    
    try:
        db.session.delete(role)
        db.session.commit()
        flash('Role deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting role: {str(e)}', 'error')
    
    return redirect(url_for('roles_permissions'))

# AJAX routes
@app.route('/api/tutors/search')
@login_required
def search_tutors():
    query = request.args.get('q', '')
    tutors = Tutor.query.filter(
        Tutor.full_name.contains(query),
        Tutor.status == 'Active'
    ).limit(10).all()
    
    return jsonify([{
        'id': tutor.id,
        'name': tutor.full_name,
        'mobile': tutor.mobile
    } for tutor in tutors])

@app.route('/api/students/subjects/<int:student_id>')
@login_required
def get_student_subjects(student_id):
    student = Student.query.get_or_404(student_id)
    subjects = [s.strip() for s in student.subjects.split(',')]
    return jsonify({'subjects': subjects})

# Error handlers
@app.errorhandler(403)
def forbidden(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Settings routes
@app.route('/settings')
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def settings():
    theme_settings = Settings.get_theme_settings()
    dues_colors = Settings.query.filter_by(category='dues_colors').all()
    general_settings = Settings.query.filter_by(category='general').all()
    
    return render_template('settings.html', 
                         theme_settings=theme_settings,
                         dues_colors=dues_colors,
                         general_settings=general_settings)

@app.route('/settings/update', methods=['POST'])
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def update_settings():
    try:
        # Update theme settings
        theme_keys = ['primary_color', 'secondary_color', 'background_color', 'text_color', 'title_font', 'body_font']
        for key in theme_keys:
            if key in request.form:
                Settings.set_setting(f'theme_{key}', request.form[key], 'theme')
        
        # Update dues colors
        dues_keys = ['just_joined', 'first_5_days', 'next_5_days', 'after_10_days', 'partial_payment', 'paid_attended', 'paid_no_class']
        for key in dues_keys:
            if key in request.form:
                Settings.set_setting(f'dues_colors_{key}', request.form[key], 'dues_colors')
        
        # Update general settings
        if 'invoice_prefix' in request.form:
            Settings.set_setting('general_invoice_prefix', request.form['invoice_prefix'], 'general')
        if 'receipt_prefix' in request.form:
            Settings.set_setting('general_receipt_prefix', request.form['receipt_prefix'], 'general')
        
        flash('Settings updated successfully', 'success')
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/settings/reset', methods=['POST'])
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def reset_settings():
    try:
        # Delete all settings and recreate defaults
        Settings.query.delete()
        db.session.commit()
        
        from models import create_default_settings
        create_default_settings()
        
        flash('Settings reset to default values', 'success')
    except Exception as e:
        flash(f'Error resetting settings: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

# Dues routes
@app.route('/dues')
@login_required
@permission_required(Permission.VIEW_STUDENTS)
def dues():
    return render_template('dues.html')

@app.route('/dues/students')
@login_required
@permission_required(Permission.VIEW_STUDENTS)
def dues_students():
    students = Student.query.filter_by(status='Active').all()
    student_dues = []
    
    for student in students:
        # Calculate dues status
        latest_invoice = StudentInvoice.query.filter_by(student_id=student.id).order_by(StudentInvoice.generated_at.desc()).first()
        
        if not latest_invoice:
            status = 'just_joined'
        elif latest_invoice.status == 'Paid':
            # Check if attended after payment
            last_attendance = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date_recorded.desc()).first()
            if last_attendance and last_attendance.date_recorded > latest_invoice.generated_at.date():
                status = 'paid_attended'
            else:
                status = 'paid_no_class'
        elif latest_invoice.status == 'Partial':
            status = 'partial_payment'
        else:
            # Calculate days overdue
            days_overdue = (datetime.utcnow().date() - latest_invoice.generated_at.date()).days
            if days_overdue <= 5:
                status = 'first_5_days'
            elif days_overdue <= 10:
                status = 'next_5_days'
            else:
                status = 'after_10_days'
        
        student_dues.append({
            'student': student,
            'status': status,
            'latest_invoice': latest_invoice
        })
    
    return jsonify({'students': [
        {
            'id': item['student'].id,
            'name': item['student'].full_name,
            'parent_name': item['student'].parent_name,
            'parent_whatsapp': item['student'].parent_whatsapp,
            'status': item['status'],
            'total_amount': item['latest_invoice'].total_amount if item['latest_invoice'] else 0,
            'amount_paid': item['latest_invoice'].amount_paid if item['latest_invoice'] else 0
        } for item in student_dues
    ]})

@app.route('/dues/tutors')
@login_required
@permission_required(Permission.VIEW_TUTORS)
def dues_tutors():
    tutors = Tutor.query.filter_by(status='Active').all()
    tutor_dues = []
    
    for tutor in tutors:
        # Calculate dues status
        latest_receipt = TutorReceipt.query.filter_by(tutor_id=tutor.id).order_by(TutorReceipt.generated_at.desc()).first()
        
        if not latest_receipt:
            status = 'just_joined'
        elif latest_receipt.status == 'Paid':
            # Check if attended after payment
            last_attendance = Attendance.query.filter_by(tutor_id=tutor.id).order_by(Attendance.date_recorded.desc()).first()
            if last_attendance and last_attendance.date_recorded > latest_receipt.generated_at.date():
                status = 'paid_attended'
            else:
                status = 'paid_no_class'
        else:
            # Calculate days overdue
            days_overdue = (datetime.utcnow().date() - latest_receipt.generated_at.date()).days
            if days_overdue <= 5:
                status = 'first_5_days'
            elif days_overdue <= 10:
                status = 'next_5_days'
            else:
                status = 'after_10_days'
        
        tutor_dues.append({
            'tutor': tutor,
            'status': status,
            'latest_receipt': latest_receipt
        })
    
    return jsonify({'tutors': [
        {
            'id': item['tutor'].id,
            'name': item['tutor'].full_name,
            'mobile': item['tutor'].mobile,
            'status': item['status'],
            'total_earnings': item['latest_receipt'].total_earnings if item['latest_receipt'] else 0
        } for item in tutor_dues
    ]})

@app.route('/dues/update-status', methods=['POST'])
@login_required
@permission_required(Permission.MARK_PAYMENTS)
def update_dues_status():
    try:
        entity_type = request.form['entity_type']  # 'student' or 'tutor'
        entity_id = int(request.form['entity_id'])
        new_status = request.form['new_status']
        
        if entity_type == 'student':
            invoice = StudentInvoice.query.filter_by(student_id=entity_id).order_by(StudentInvoice.generated_at.desc()).first()
            if invoice:
                if new_status == 'paid':
                    invoice.status = 'Paid'
                    invoice.amount_paid = invoice.total_amount
                elif new_status == 'partial':
                    invoice.status = 'Partial'
                    invoice.amount_paid = float(request.form.get('amount_paid', 0))
                else:
                    invoice.status = 'Due'
                    invoice.amount_paid = 0
        else:
            receipt = TutorReceipt.query.filter_by(tutor_id=entity_id).order_by(TutorReceipt.generated_at.desc()).first()
            if receipt:
                if new_status == 'paid':
                    receipt.status = 'Paid'
                else:
                    receipt.status = 'Due'
        
        db.session.commit()
        flash('Status updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'error')
    
    return redirect(url_for('dues'))

# Data Flush routes
@app.route('/data-flush')
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def data_flush():
    return render_template('data_flush.html')

@app.route('/data-flush/backup', methods=['POST'])
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def create_backup():
    try:
        # Create temporary directory for backup
        temp_dir = tempfile.mkdtemp()
        backup_file = os.path.join(temp_dir, 'mentorscue_backup.zip')
        
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Export attendance records
            attendance_records = Attendance.query.all()
            attendance_data = []
            for record in attendance_records:
                attendance_data.append({
                    'student_id': record.student_id,
                    'tutor_id': record.tutor_id,
                    'subject': record.subject,
                    'start_time': record.start_time.isoformat(),
                    'end_time': record.end_time.isoformat(),
                    'duration_minutes': record.duration_minutes,
                    'rating': record.rating,
                    'remarks': record.remarks,
                    'date_recorded': record.date_recorded.isoformat()
                })
            
            # Export invoices
            invoices = StudentInvoice.query.all()
            invoice_data = []
            for invoice in invoices:
                invoice_data.append({
                    'student_id': invoice.student_id,
                    'invoice_number': invoice.invoice_number,
                    'start_date': invoice.start_date.isoformat(),
                    'end_date': invoice.end_date.isoformat(),
                    'total_classes': invoice.total_classes,
                    'total_amount': invoice.total_amount,
                    'status': invoice.status,
                    'amount_paid': invoice.amount_paid,
                    'generated_at': invoice.generated_at.isoformat()
                })
            
            # Export receipts
            receipts = TutorReceipt.query.all()
            receipt_data = []
            for receipt in receipts:
                receipt_data.append({
                    'tutor_id': receipt.tutor_id,
                    'receipt_number': receipt.receipt_number,
                    'start_date': receipt.start_date.isoformat(),
                    'end_date': receipt.end_date.isoformat(),
                    'total_classes': receipt.total_classes,
                    'total_earnings': receipt.total_earnings,
                    'status': receipt.status,
                    'generated_at': receipt.generated_at.isoformat()
                })
            
            # Write data to JSON files in ZIP
            zipf.writestr('attendance.json', json.dumps(attendance_data, indent=2))
            zipf.writestr('invoices.json', json.dumps(invoice_data, indent=2))
            zipf.writestr('receipts.json', json.dumps(receipt_data, indent=2))
        
        # Send file to user
        with open(backup_file, 'rb') as f:
            backup_data = f.read()
        
        # Clean up
        os.remove(backup_file)
        os.rmdir(temp_dir)
        
        response = make_response(backup_data)
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename=mentorscue_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        return response
        
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'error')
        return redirect(url_for('data_flush'))

@app.route('/data-flush/execute', methods=['POST'])
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def execute_data_flush():
    try:
        flush_type = request.form['flush_type']
        
        if flush_type == '3_months':
            cutoff_date = datetime.utcnow() - timedelta(days=90)
        elif flush_type == '6_months':
            cutoff_date = datetime.utcnow() - timedelta(days=180)
        elif flush_type == 'custom':
            cutoff_date = datetime.strptime(request.form['custom_date'], '%Y-%m-%d')
        else:
            flash('Invalid flush type', 'error')
            return redirect(url_for('data_flush'))
        
        # Delete old attendance records
        deleted_attendance = Attendance.query.filter(Attendance.created_at < cutoff_date).delete()
        
        # Delete old invoices (keep core structure)
        deleted_invoices = StudentInvoice.query.filter(StudentInvoice.generated_at < cutoff_date).delete()
        
        # Delete old receipts (keep core structure)
        deleted_receipts = TutorReceipt.query.filter(TutorReceipt.generated_at < cutoff_date).delete()
        
        db.session.commit()
        
        flash(f'Data flush completed: {deleted_attendance} attendance records, {deleted_invoices} invoices, {deleted_receipts} receipts deleted', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error during data flush: {str(e)}', 'error')
    
    return redirect(url_for('data_flush'))

# Announcements routes
@app.route('/announcements')
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def announcements():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('announcements.html', announcements=announcements)

@app.route('/announcements/add', methods=['POST'])
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def add_announcement():
    try:
        announcement = Announcement(
            title=request.form['title'],
            content=request.form['content'],
            created_by=current_user.id
        )
        
        if request.form.get('expiry_date'):
            announcement.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding announcement: {str(e)}', 'error')
    
    return redirect(url_for('announcements'))

@app.route('/announcements/<int:id>/edit', methods=['POST'])
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def edit_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    
    try:
        announcement.title = request.form['title']
        announcement.content = request.form['content']
        announcement.is_active = bool(request.form.get('is_active'))
        
        if request.form.get('expiry_date'):
            announcement.expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
        else:
            announcement.expiry_date = None
        
        db.session.commit()
        flash('Announcement updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating announcement: {str(e)}', 'error')
    
    return redirect(url_for('announcements'))

@app.route('/announcements/<int:id>/delete', methods=['POST'])
@login_required
@permission_required(Permission.ACCESS_SETTINGS)
def delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    
    try:
        db.session.delete(announcement)
        db.session.commit()
        flash('Announcement deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting announcement: {str(e)}', 'error')
    
    return redirect(url_for('announcements'))

@app.route('/api/announcements/active')
@login_required
def get_active_announcements():
    """Get active announcements for tutors"""
    if not current_user.is_tutor_user():
        return jsonify({'announcements': []})
    
    announcements = Announcement.query.filter_by(is_active=True).all()
    active_announcements = []
    
    for announcement in announcements:
        if not announcement.is_expired():
            active_announcements.append({
                'id': announcement.id,
                'title': announcement.title,
                'content': announcement.content,
                'created_at': announcement.created_at.isoformat(),
                'expiry_date': announcement.expiry_date.isoformat() if announcement.expiry_date else None
            })
    
    return jsonify({'announcements': active_announcements})
