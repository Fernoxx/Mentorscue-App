# MENTORSCUE

## Overview

MENTORSCUE is a comprehensive tuition management system built with Flask. It provides a web-based platform for managing students, tutors, attendance tracking, billing, and user management with role-based access control. The system supports multiple user roles including Admin, Tutor, Accountant, and Watcher, each with specific permissions and access levels.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python) with SQLAlchemy ORM
- **Database**: SQLite for development, PostgreSQL for production
- **Authentication**: Flask-Login for session management
- **Security**: Werkzeug for password hashing and security utilities
- **WSGI Server**: Gunicorn for production deployment

### Frontend Architecture
- **Templates**: Jinja2 templating engine
- **CSS Framework**: Bootstrap 5 for responsive design
- **Icons**: Font Awesome for UI icons
- **JavaScript**: Vanilla JS for client-side interactions
- **No heavy frontend frameworks**: Pure HTML/CSS/JS approach

### Database Design
- **ORM**: SQLAlchemy with declarative base
- **Relationships**: Many-to-many relationships between users/roles and students/tutors
- **Connection Pooling**: Built-in SQLAlchemy connection pooling with pre-ping
- **Migrations**: Database schema managed through SQLAlchemy models

## Key Components

### Authentication & Authorization
- **User Management**: Multi-role user system with customizable permissions
- **Role-Based Access Control**: Binary permission flags for granular access control
- **Session Management**: Flask-Login with remember me functionality
- **Permission System**: Decorator-based permission checking

### Student Management
- **Student Profiles**: Comprehensive student information including parent details
- **Class Assignment**: Students can be assigned to multiple tutors
- **Billing Integration**: Per-class fee tracking and invoice generation
- **Status Tracking**: Active/inactive student status management

### Tutor Management
- **Tutor Profiles**: Complete tutor information with mobile-based login
- **Student Assignment**: Many-to-many relationship with students
- **Payment Tracking**: UPI integration for salary payments
- **Attendance Submission**: Tutors can submit attendance for their classes

### Attendance System
- **Class Tracking**: Date-based attendance recording
- **Multi-user Access**: Both admins and tutors can record attendance
- **Reporting**: Historical attendance viewing and analysis
- **Billing Integration**: Attendance data drives invoice generation

### Invoice & Receipt System
- **Automated Generation**: Periodic invoice and receipt generation
- **PDF Generation**: WeasyPrint for professional PDF documents
- **Payment Tracking**: Status management (Due, Partial, Paid)
- **Download Management**: Role-based download permissions

### User Interface
- **Responsive Design**: Bootstrap 5 for mobile-first responsive layout
- **Dashboard System**: Role-specific dashboards with relevant metrics
- **Navigation**: Context-aware navigation based on user permissions
- **Form Validation**: Client and server-side validation

## Data Flow

### User Authentication Flow
1. User submits login credentials
2. System validates against User model
3. Flask-Login creates session
4. Role-based redirection to appropriate dashboard
5. Permission checks on each request

### Student Management Flow
1. Admin/Manager creates student profile
2. Student assigned to tutors with per-class rates
3. Attendance recorded by tutors
4. System generates invoices based on attendance
5. Payment status tracked and updated

### Tutor Management Flow
1. Admin creates tutor profile
2. Tutor assigned to students
3. Tutor submits attendance
4. System generates payment receipts
5. Payment processed and tracked

### Invoice Generation Flow
1. System checks for billing cycles
2. Attendance data aggregated by student
3. Invoices generated automatically
4. PDF documents created
5. Payment status initialized as "Due"

## External Dependencies

### Python Packages
- **Flask**: Web framework
- **Flask-SQLAlchemy**: Database ORM
- **Flask-Login**: Authentication management
- **Werkzeug**: Security utilities
- **WeasyPrint**: PDF generation
- **Gunicorn**: WSGI server for production

### Frontend Dependencies
- **Bootstrap 5**: CSS framework (CDN)
- **Font Awesome**: Icon library (CDN)
- **Custom CSS**: Application-specific styling

### Development Dependencies
- **SQLite**: Development database
- **Python logging**: Application logging
- **Environment variables**: Configuration management

## Deployment Strategy

### Environment Configuration
- **Development**: SQLite database, debug mode enabled
- **Production**: PostgreSQL database, Gunicorn WSGI server
- **Environment Variables**: SESSION_SECRET, DATABASE_URL
- **Proxy Configuration**: ProxyFix for deployment behind reverse proxy

### Database Strategy
- **Development**: SQLite for rapid development
- **Production**: PostgreSQL for scalability and performance
- **Schema Management**: SQLAlchemy create_all() for initial setup
- **Connection Pooling**: Configured for production reliability

### Deployment Platforms
- **Railway**: Configured for easy deployment
- **Render**: Alternative deployment option
- **Docker**: Containerization ready
- **Traditional VPS**: Gunicorn + Nginx setup

### Security Considerations
- **Session Security**: Secure session key configuration
- **Password Hashing**: Werkzeug secure password storage
- **CSRF Protection**: Built-in Flask CSRF protection
- **SQL Injection Prevention**: SQLAlchemy ORM parameterized queries

### Performance Optimizations
- **Database Pooling**: Connection reuse and pre-ping
- **Static File Serving**: CDN for Bootstrap and Font Awesome
- **Minimal JavaScript**: Lightweight client-side code
- **Efficient Queries**: Optimized SQLAlchemy queries

### Monitoring & Logging
- **Application Logging**: Python logging module
- **Error Handling**: Custom error pages (404, 403)
- **Performance Tracking**: Database query optimization
- **User Activity**: Login and action tracking