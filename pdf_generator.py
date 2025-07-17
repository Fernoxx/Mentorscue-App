import os
from weasyprint import HTML, CSS
from flask import render_template_string
from datetime import datetime

def generate_student_invoice_pdf(invoice):
    """Generate PDF for student invoice"""
    try:
        student = invoice.student
        
        # HTML template for invoice
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
                .header { text-align: center; margin-bottom: 30px; }
                .company-name { font-size: 24px; font-weight: bold; color: #344e80; margin-bottom: 10px; }
                .invoice-title { font-size: 18px; margin-bottom: 20px; }
                .invoice-info { margin-bottom: 20px; }
                .student-info { margin-bottom: 20px; }
                .invoice-details { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                .invoice-details th, .invoice-details td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .invoice-details th { background-color: #344e80; color: white; }
                .total-row { font-weight: bold; background-color: #f9f9f9; }
                .payment-info { margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
                .footer { margin-top: 30px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">MENTORSCUE</div>
                <div class="invoice-title">Student Invoice</div>
            </div>
            
            <div class="invoice-info">
                <strong>Invoice Number:</strong> {{ invoice.invoice_number }}<br>
                <strong>Generated Date:</strong> {{ invoice.generated_at.strftime('%d/%m/%Y') }}<br>
                <strong>Billing Period:</strong> {{ invoice.start_date.strftime('%d/%m/%Y') }} to {{ invoice.end_date.strftime('%d/%m/%Y') }}
            </div>
            
            <div class="student-info">
                <h3>Student Information</h3>
                <strong>Student Name:</strong> {{ student.full_name }}<br>
                <strong>Class Level:</strong> {{ student.class_level }}<br>
                <strong>Subjects:</strong> {{ student.subjects }}<br>
                <strong>Parent Name:</strong> {{ student.parent_name }}<br>
                <strong>Parent WhatsApp:</strong> {{ student.parent_whatsapp }}
            </div>
            
            <table class="invoice-details">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Quantity</th>
                        <th>Rate (₹)</th>
                        <th>Amount (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Classes Attended</td>
                        <td>{{ invoice.total_classes }}</td>
                        <td>{{ "%.2f"|format(student.per_class_fee) }}</td>
                        <td>{{ "%.2f"|format(invoice.total_amount) }}</td>
                    </tr>
                    <tr class="total-row">
                        <td colspan="3"><strong>Total Amount Due</strong></td>
                        <td><strong>₹ {{ "%.2f"|format(invoice.total_amount) }}</strong></td>
                    </tr>
                </tbody>
            </table>
            
            <div class="payment-info">
                <h3>Payment Instructions</h3>
                <strong>GPay:</strong> 7994829844<br>
                <strong>UPI ID:</strong> Jafaraliva869@oksbi<br>
                <br>
                Please send payment confirmation screenshot to complete the payment process.
            </div>
            
            <div class="footer">
                Thank you for choosing MENTORSCUE for your educational needs.
            </div>
        </body>
        </html>
        """
        
        # Render HTML with data
        html_content = render_template_string(html_template, invoice=invoice, student=student)
        
        # Generate PDF
        html_doc = HTML(string=html_content)
        pdf_bytes = html_doc.write_pdf()
        
        return pdf_bytes
        
    except Exception as e:
        print(f"Error generating student invoice PDF: {str(e)}")
        return None

def generate_tutor_receipt_pdf(receipt):
    """Generate PDF for tutor receipt"""
    try:
        tutor = receipt.tutor
        
        # Get attendance details for the period
        from models import Attendance
        attendance_records = Attendance.query.filter(
            Attendance.tutor_id == tutor.id,
            Attendance.date_recorded >= receipt.start_date,
            Attendance.date_recorded <= receipt.end_date
        ).all()
        
        # Group by student
        student_summary = {}
        for record in attendance_records:
            student = record.student
            if student.id not in student_summary:
                student_summary[student.id] = {
                    'name': student.full_name,
                    'classes': 0,
                    'pay_rate': student.get_tutor_pay_rate(tutor.id),
                    'total_earning': 0.0
                }
            
            student_summary[student.id]['classes'] += 1
            student_summary[student.id]['total_earning'] += student_summary[student.id]['pay_rate']
        
        # HTML template for receipt
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
                .header { text-align: center; margin-bottom: 30px; }
                .company-name { font-size: 24px; font-weight: bold; color: #344e80; margin-bottom: 10px; }
                .receipt-title { font-size: 18px; margin-bottom: 20px; }
                .receipt-info { margin-bottom: 20px; }
                .tutor-info { margin-bottom: 20px; }
                .receipt-details { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                .receipt-details th, .receipt-details td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .receipt-details th { background-color: #344e80; color: white; }
                .total-row { font-weight: bold; background-color: #f9f9f9; }
                .payment-info { margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
                .footer { margin-top: 30px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">MENTORSCUE</div>
                <div class="receipt-title">Tutor Salary Receipt</div>
            </div>
            
            <div class="receipt-info">
                <strong>Receipt Number:</strong> {{ receipt.receipt_number }}<br>
                <strong>Generated Date:</strong> {{ receipt.generated_at.strftime('%d/%m/%Y') }}<br>
                <strong>Payment Period:</strong> {{ receipt.start_date.strftime('%d/%m/%Y') }} to {{ receipt.end_date.strftime('%d/%m/%Y') }}
            </div>
            
            <div class="tutor-info">
                <h3>Tutor Information</h3>
                <strong>Tutor Name:</strong> {{ tutor.full_name }}<br>
                <strong>Mobile Number:</strong> {{ tutor.mobile }}<br>
                {% if tutor.upi_id %}
                <strong>UPI ID:</strong> {{ tutor.upi_id }}<br>
                {% endif %}
            </div>
            
            <table class="receipt-details">
                <thead>
                    <tr>
                        <th>Student Name</th>
                        <th>Classes Taught</th>
                        <th>Pay per Class (₹)</th>
                        <th>Total Earning (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for student_id, details in student_summary.items() %}
                    <tr>
                        <td>{{ details.name }}</td>
                        <td>{{ details.classes }}</td>
                        <td>{{ "%.2f"|format(details.pay_rate) }}</td>
                        <td>{{ "%.2f"|format(details.total_earning) }}</td>
                    </tr>
                    {% endfor %}
                    <tr class="total-row">
                        <td colspan="3"><strong>Total Payout Due</strong></td>
                        <td><strong>₹ {{ "%.2f"|format(receipt.total_earnings) }}</strong></td>
                    </tr>
                </tbody>
            </table>
            
            <div class="payment-info">
                <h3>Contact Information</h3>
                <strong>Mobile:</strong> 8921378863<br>
                <br>
                Please contact for payment schedule and details.
            </div>
            
            <div class="footer">
                Thank you for your dedicated service to MENTORSCUE.
            </div>
        </body>
        </html>
        """
        
        # Render HTML with data
        html_content = render_template_string(html_template, receipt=receipt, tutor=tutor, student_summary=student_summary)
        
        # Generate PDF
        html_doc = HTML(string=html_content)
        pdf_bytes = html_doc.write_pdf()
        
        return pdf_bytes
        
    except Exception as e:
        print(f"Error generating tutor receipt PDF: {str(e)}")
        return None
