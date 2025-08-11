# email_notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yaml

# Load email settings from config.yaml
with open("email.yaml", "r") as file:
    config = yaml.safe_load(file)

EMAIL_SETTINGS = config["email_settings"]

def send_email(subject, body):
    """
    Sends an email notification with the given subject and body.
    """
    sender_email = EMAIL_SETTINGS["sender_email"]
    sender_password = EMAIL_SETTINGS["sender_password"]
    receiver_email = EMAIL_SETTINGS["receiver_email"]
    smtp_server = EMAIL_SETTINGS["smtp_server"]
    smtp_port = EMAIL_SETTINGS["smtp_port"]

    # Create email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Establish connection to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"📩 Email sent successfully to {receiver_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
