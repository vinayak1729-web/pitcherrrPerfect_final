import os
from email.message import EmailMessage
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from signupEmailBody import Sign_up_email_body_template
from dotenv import load_dotenv
load_dotenv()
email_sender = os.getenv('EMAIL_USER')
sender_password = os.getenv('EMAIL_PASS')

def send_sign_up_email(recipient_email, username, sender_email, sender_password):
    """Sends a formatted HTML email."""

    subject = "Welcome to Pitcher Perfect!"
    body = Sign_up_email_body_template(username)

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "html"))  # This line is key: content type is specified as "html"


    try:
        # Use smtplib with SSL/TLS for secure email sending (Gmail specific)
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, recipient_email, message.as_string())
        print(f"Email sent successfully! to {username}")

    except Exception as e:
        print(f"Error sending email: {e}")

