"""
EMAIL_NOTIFIER.PY - Email Sending Utility
==========================================
This file handles sending emails using SMTP.
Reads configuration from email.yaml and sends emails to recipients.
"""

import smtplib
import yaml
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime, timedelta
import time


def load_email_config():
    """Load email configuration from email.yaml"""
    try:
        with open("email.yaml", 'r', encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
            return config['email_settings']
    except Exception as e:
        print(f"❌ Error loading email config: {e}")
        return None


def send_email(to_email, subject, body, attachment_path=None):
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
        attachment_path: Optional path to file attachment
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    config = load_email_config()
    if not config:
        print("❌ Failed to load email configuration")
        return False
    
    sender_email = config['sender_email']
    sender_password = config['sender_password']
    smtp_server = config['smtp_server']
    smtp_port = config['smtp_port']
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(attachment_path)}'
                )
                msg.attach(part)
        
        # Connect to server and send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False


def send_bulk_emails(email_list, subject, body, attachment_path=None):
    """
    Send the same email to multiple recipients.
    
    Args:
        email_list: List of recipient email addresses
        subject: Email subject
        body: Email body text
        attachment_path: Optional path to file attachment
    
    Returns:
        dict: Summary with 'sent' and 'failed' counts
    """
    sent_count = 0
    failed_count = 0
    
    print(f"\n📧 Sending emails to {len(email_list)} recipient(s)...")
    
    for email in email_list:
        if send_email(email, subject, body, attachment_path):
            sent_count += 1
        else:
            failed_count += 1
    
    print(f"\n📊 Email Summary:")
    print(f"  ✅ Sent: {sent_count}")
    print(f"  ❌ Failed: {failed_count}")
    
    return {'sent': sent_count, 'failed': failed_count}


def create_email_template(position, personal_info):
    """
    Creates email subject and body template for job application.
    
    Args:
        position: Job position being applied for
        personal_info: Dictionary with personal information from config
    
    Returns:
        tuple: (subject, body)
    """
    first_name = personal_info.get('First Name', 'Your Name')
    last_name = personal_info.get('Last Name', '')
    full_name = f"{first_name} {last_name}".strip()
    pay_rate = personal_info.get('ExpectedPayPerHour', 0)
    
    # Create email subject
    subject = f"Application for {position} - C2C"
    
    # Create email body
    body = f"""Hi,

My name is {full_name}, and I am applying for the {position} position that you posted for C2C (Corp-to-Corp).

I am interested in this opportunity and would like to discuss the details further. My expected pay rate is ${pay_rate}/hour.

I have attached my resume for your review. Please let me know if you need any additional information.

Looking forward to hearing from you.

Best regards,
{full_name}"""
    
    return subject, body


def check_email_replies(hours=3):
    """
    Check Gmail inbox for replies to emails sent in the last X hours.
    
    Args:
        hours: How many hours back to check for sent emails
    
    Returns:
        dict: {'replied': [emails], 'no_reply': [emails]}
    """
    config = load_email_config()
    if not config:
        print("❌ Failed to load email configuration")
        return {'replied': [], 'no_reply': []}
    
    sender_email = config['sender_email']
    sender_password = config['sender_password']
    
    try:
        # Connect to Gmail IMAP
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(sender_email, sender_password)
        
        # Select inbox
        imap.select('INBOX')
        
        # Get sent emails from CSV to check
        import csv
        sent_emails = {}
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if os.path.exists('emails_output.csv'):
            with open('emails_output.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 3:
                        email_addr = row[0]
                        sent_time = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S')
                        if sent_time >= cutoff_time:
                            sent_emails[email_addr.lower()] = sent_time
        
        print(f"\n📬 Checking replies for {len(sent_emails)} email(s) sent in last {hours} hours...")
        
        replied_emails = []
        
        # Search for emails from the addresses we sent to
        for email_addr in sent_emails.keys():
            try:
                # Search for emails from this address
                _, message_ids = imap.search(None, f'FROM "{email_addr}"')
                
                if message_ids[0]:
                    # Found reply
                    replied_emails.append(email_addr)
                    print(f"  ✅ Reply received from: {email_addr}")
                    
                    # Star/flag the email
                    for msg_id in message_ids[0].split():
                        imap.store(msg_id, '+FLAGS', '\\Flagged')
                    
            except Exception as e:
                print(f"  ⚠️ Error checking {email_addr}: {e}")
        
        # Determine who didn't reply
        no_reply = [email for email in sent_emails.keys() if email not in replied_emails]
        
        imap.close()
        imap.logout()
        
        print(f"\n📊 Reply Summary:")
        print(f"  ✅ Replied: {len(replied_emails)}")
        print(f"  ⏳ No reply yet: {len(no_reply)}")
        
        return {'replied': replied_emails, 'no_reply': no_reply}
        
    except Exception as e:
        print(f"❌ Error checking emails: {e}")
        return {'replied': [], 'no_reply': []}


def send_followup_emails(no_reply_emails, position, personal_info):
    """
    Send follow-up emails to contacts who haven't replied.
    
    Args:
        no_reply_emails: List of email addresses
        position: Job position
        personal_info: Personal information dict
    """
    if not no_reply_emails:
        print("✅ No follow-up emails needed")
        return
    
    first_name = personal_info.get('First Name', 'Your Name')
    last_name = personal_info.get('Last Name', '')
    full_name = f"{first_name} {last_name}".strip()
    pay_rate = personal_info.get('ExpectedPayPerHour', 0)
    
    subject = f"Re: Application for {position} - C2C"
    
    body = f"""Hi,

I wanted to follow up on my previous email regarding the {position} position.

I'm very interested in this C2C opportunity and would appreciate the chance to discuss it further. My expected rate is ${pay_rate}/hour.

Please let me know if you need any additional information or would like to schedule a call.

Thank you for your time.

Best regards,
{full_name}"""
    
    print(f"\n📧 Sending follow-up emails to {len(no_reply_emails)} recipient(s)...")
    
    sent_count = 0
    for email_addr in no_reply_emails:
        if send_email(email_addr, subject, body):
            sent_count += 1
    
    print(f"✅ Sent {sent_count} follow-up email(s)")


if __name__ == '__main__':
    # Test the email functionality
    config = load_email_config()
    if config:
        print("✅ Email configuration loaded successfully")
        print(f"Sender: {config['sender_email']}")
        print(f"SMTP Server: {config['smtp_server']}:{config['smtp_port']}")
    else:
        print("❌ Failed to load email configuration")
