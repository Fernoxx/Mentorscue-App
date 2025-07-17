from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import logging

# Association tables for many-to-many relationships
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

student_tutors = db.Table('student_tutors',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('tutor_id', db.Integer, db.ForeignKey('tutor.id'), primary_key=True),
    db.Column('pay_per_class', db.Float, nullable=False, default=0.0)
)

class Permission:
    """Permission constants using binary flags"""
    VIEW_STUDENTS = 1           # 00000001
    ADD_STUDENTS = 2            # 00000010
    EDIT_STUDENTS = 4           # 00000100
    DELETE_STUDENTS = 8         # 00001000
    VIEW_TUTORS = 16            # 00010000
    ADD_TUTORS = 32             # 00100000
    EDIT_TUTORS = 64            # 01000000
    DELETE_TUTORS = 128         # 10000000
    VIEW_ATTENDANCE = 256       # 100000000
    SUBMIT_ATTENDANCE = 512     # 1000000000
    VIEW_INVOICES = 1024        # 10000000000
    GENERATE_INVOICES = 2048    # 100000000000
    MARK_PAYMENTS = 4096        # 1000000000000
    DOWNLOAD_INVOICES = 8192    # 10000000000000
    ACCESS_SETTINGS = 16384     # 100000000000000
    MANAGE_USERS = 32768        # 1000000000000000
    MANAGE_ROLES = 65536        # 10000000000000000

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    full_name = db.Column(db.String(120), nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    remember_me = db.Column(db.Boolean, default=False)
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, backref='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission):
        return any(role.has_permission(permission) for role in self.roles)
    
    def is_admin(self):
        return self.has_role('Admin')
    
    def is_tutor_user(self):
        return self.has_role('Tutor')

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.Integer, default=0)
    is_default = db.Column(db.Boolean, default=False)
    is_custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm
    
    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm
    
    def reset_permissions(self):
        self.permissions = 0
    
    def has_permission(self, perm):
        return self.permissions & perm == perm

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    parent_name = db.Column(db.String(120), nullable=False)
    parent_whatsapp = db.Column(db.String(20), nullable=False)
    class_level = db.Column(db.String(20), nullable=False)
    subjects = db.Column(db.Text, nullable=False)  # Comma-separated subjects
    per_class_fee = db.Column(db.Float, nullable=False, default=0.0)
    billing_start_date = db.Column(db.Date, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, Graduated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tutors = db.relationship('Tutor', secondary=student_tutors, backref='students')
    attendance_records = db.relationship('Attendance', backref='student', lazy='dynamic')
    invoices = db.relationship('StudentInvoice', backref='student', lazy='dynamic')
    
    def get_next_billing_date(self):
        """Calculate next billing date (30 days from billing start)"""
        return self.billing_start_date + timedelta(days=30)
    
    def is_billing_due(self):
        """Check if billing is due today"""
        return self.get_next_billing_date() <= datetime.utcnow().date()
    
    def get_tutor_pay_rate(self, tutor_id):
        """Get pay rate for specific tutor"""
        result = db.session.execute(
            db.text("SELECT pay_per_class FROM student_tutors WHERE student_id = :sid AND tutor_id = :tid"),
            {"sid": self.id, "tid": tutor_id}
        ).fetchone()
        return result[0] if result else 0.0

class Tutor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    full_name = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    mobile = db.Column(db.String(20), nullable=False, unique=True)
    upi_id = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(20), nullable=False)  # Plain text for display
    billing_start_date = db.Column(db.Date, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='Active')  # Active, Inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attendance_records = db.relationship('Attendance', backref='tutor', lazy='dynamic')
    receipts = db.relationship('TutorReceipt', backref='tutor', lazy='dynamic')
    user = db.relationship('User', backref='tutor_profile', uselist=False)
    
    def get_next_payment_date(self):
        """Calculate next payment date (40 days from billing start)"""
        return self.billing_start_date + timedelta(days=40)
    
    def is_payment_due(self):
        """Check if payment is due today"""
        return self.get_next_payment_date() <= datetime.utcnow().date()
    
    def generate_username(self):
        """Generate username: FirstNameDDMM"""
        if self.date_of_birth and self.full_name:
            first_name = self.full_name.split()[0]
            day_month = self.date_of_birth.strftime("%d%m")
            return f"{first_name}{day_month}"
        return self.full_name.replace(" ", "").lower()

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey('tutor.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-10
    remarks = db.Column(db.Text, nullable=True)
    date_recorded = db.Column(db.Date, default=datetime.utcnow().date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_duration(self):
        """Calculate duration in minutes"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0

class StudentInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_classes = db.Column(db.Integer, default=0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='Due')  # Due, Partial, Paid
    amount_paid = db.Column(db.Float, default=0.0)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def generate_invoice_number(self):
        """Generate unique invoice number"""
        year_month = datetime.utcnow().strftime("%Y%m")
        return f"INV-{year_month}-{self.student_id}-{self.id}"

class TutorReceipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey('tutor.id'), nullable=False)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_classes = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='Due')  # Due, Paid
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def generate_receipt_number(self):
        """Generate unique receipt number"""
        year_month = datetime.utcnow().strftime("%Y%m")
        return f"REC-{year_month}-{self.tutor_id}-{self.id}"

def create_default_roles():
    """Create default roles with predefined permissions"""
    roles_config = {
        'Admin': {
            'description': 'Full access to all features',
            'permissions': [
                Permission.VIEW_STUDENTS, Permission.ADD_STUDENTS, Permission.EDIT_STUDENTS, Permission.DELETE_STUDENTS,
                Permission.VIEW_TUTORS, Permission.ADD_TUTORS, Permission.EDIT_TUTORS, Permission.DELETE_TUTORS,
                Permission.VIEW_ATTENDANCE, Permission.SUBMIT_ATTENDANCE,
                Permission.VIEW_INVOICES, Permission.GENERATE_INVOICES, Permission.MARK_PAYMENTS, Permission.DOWNLOAD_INVOICES,
                Permission.ACCESS_SETTINGS, Permission.MANAGE_USERS, Permission.MANAGE_ROLES
            ]
        },
        'Watcher': {
            'description': 'Read-only access across the dashboard',
            'permissions': [
                Permission.VIEW_STUDENTS, Permission.VIEW_TUTORS, Permission.VIEW_ATTENDANCE, Permission.VIEW_INVOICES
            ]
        },
        'Accountant': {
            'description': 'Can access dashboard but cannot add/edit students or tutors',
            'permissions': [
                Permission.VIEW_STUDENTS, Permission.VIEW_TUTORS, Permission.VIEW_ATTENDANCE,
                Permission.VIEW_INVOICES, Permission.GENERATE_INVOICES, Permission.MARK_PAYMENTS, Permission.DOWNLOAD_INVOICES
            ]
        },
        'Tutor': {
            'description': 'Can view own dashboard and submit attendance',
            'permissions': [
                Permission.VIEW_ATTENDANCE, Permission.SUBMIT_ATTENDANCE
            ]
        },
        'Manager': {
            'description': 'Can manage students but not tutors',
            'permissions': [
                Permission.VIEW_STUDENTS, Permission.ADD_STUDENTS, Permission.EDIT_STUDENTS, Permission.DELETE_STUDENTS,
                Permission.VIEW_TUTORS, Permission.VIEW_ATTENDANCE
            ]
        }
    }
    
    for role_name, config in roles_config.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=config['description'])
            db.session.add(role)
        
        # Reset and set permissions
        role.reset_permissions()
        for perm in config['permissions']:
            role.add_permission(perm)
    
    db.session.commit()
    logging.info("Default roles created successfully")

def create_admin_user():
    """Create default admin user if it doesn't exist"""
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_role = Role.query.filter_by(name='Admin').first()
        admin_user = User(
            username='admin',
            email='admin@mentorscue.com',
            full_name='System Administrator'
        )
        admin_user.set_password('admin123')  # Change this in production
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Default admin user created: username=admin, password=admin123")
