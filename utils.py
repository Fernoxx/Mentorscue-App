from datetime import datetime, timedelta
from models import Student, Tutor, StudentInvoice, TutorReceipt, Attendance, db
import logging

def check_and_generate_invoices():
    """Check and generate invoices/receipts that are due"""
    try:
        # Generate student invoices
        students_due = Student.query.filter(
            Student.status == 'Active'
        ).all()
        
        for student in students_due:
            if student.is_billing_due():
                generate_student_invoice(student)
        
        # Generate tutor receipts
        tutors_due = Tutor.query.filter(
            Tutor.status == 'Active'
        ).all()
        
        for tutor in tutors_due:
            if tutor.is_payment_due():
                generate_tutor_receipt(tutor)
                
    except Exception as e:
        logging.error(f"Error generating invoices: {str(e)}")

def generate_student_invoice(student):
    """Generate invoice for a student"""
    try:
        # Check if invoice already exists for current cycle
        end_date = student.get_next_billing_date() - timedelta(days=1)
        start_date = student.billing_start_date
        
        existing_invoice = StudentInvoice.query.filter_by(
            student_id=student.id,
            start_date=start_date,
            end_date=end_date
        ).first()
        
        if existing_invoice:
            return existing_invoice
        
        # Count classes attended in the billing period
        total_classes = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.date_recorded >= start_date,
            Attendance.date_recorded <= end_date
        ).count()
        
        # Calculate total amount
        total_amount = total_classes * student.per_class_fee
        
        # Create invoice
        invoice = StudentInvoice(
            student_id=student.id,
            start_date=start_date,
            end_date=end_date,
            total_classes=total_classes,
            total_amount=total_amount
        )
        
        db.session.add(invoice)
        db.session.flush()  # To get the ID
        
        invoice.invoice_number = invoice.generate_invoice_number()
        
        # Update student's billing start date for next cycle
        student.billing_start_date = end_date + timedelta(days=1)
        
        db.session.commit()
        logging.info(f"Generated invoice for student {student.full_name}: {invoice.invoice_number}")
        
        return invoice
        
    except Exception as e:
        logging.error(f"Error generating student invoice: {str(e)}")
        db.session.rollback()
        return None

def generate_tutor_receipt(tutor):
    """Generate receipt for a tutor"""
    try:
        # Check if receipt already exists for current cycle
        end_date = tutor.get_next_payment_date() - timedelta(days=1)
        start_date = tutor.billing_start_date
        
        existing_receipt = TutorReceipt.query.filter_by(
            tutor_id=tutor.id,
            start_date=start_date,
            end_date=end_date
        ).first()
        
        if existing_receipt:
            return existing_receipt
        
        # Calculate earnings from all students taught
        total_earnings = 0.0
        total_classes = 0
        
        attendance_records = Attendance.query.filter(
            Attendance.tutor_id == tutor.id,
            Attendance.date_recorded >= start_date,
            Attendance.date_recorded <= end_date
        ).all()
        
        for record in attendance_records:
            pay_rate = record.student.get_tutor_pay_rate(tutor.id)
            total_earnings += pay_rate
            total_classes += 1
        
        # Create receipt
        receipt = TutorReceipt(
            tutor_id=tutor.id,
            start_date=start_date,
            end_date=end_date,
            total_classes=total_classes,
            total_earnings=total_earnings
        )
        
        db.session.add(receipt)
        db.session.flush()  # To get the ID
        
        receipt.receipt_number = receipt.generate_receipt_number()
        
        # Update tutor's billing start date for next cycle
        tutor.billing_start_date = end_date + timedelta(days=1)
        
        db.session.commit()
        logging.info(f"Generated receipt for tutor {tutor.full_name}: {receipt.receipt_number}")
        
        return receipt
        
    except Exception as e:
        logging.error(f"Error generating tutor receipt: {str(e)}")
        db.session.rollback()
        return None

def permission_required(permission):
    """Decorator to check if user has specific permission"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            from flask import abort
            
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from flask import abort
        
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin():
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function
