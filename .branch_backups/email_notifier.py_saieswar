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
from email.utils import make_msgid
import os
from datetime import datetime, timedelta
import time
import csv
import hashlib
from email_rate_limiter import EmailRateLimiter


def load_email_config():
    """Load email configuration from email.yaml"""
    try:
        with open("email.yaml", 'r', encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
            return config['email_settings']
    except Exception as e:
        print(f"❌ Error loading email config: {e}")
        return None


def load_blocklist():
    """Load blocked emails and domains from blocklist/blocked_emails.txt"""
    blocklist = set()
    blocklist_file = "blocklist/blocked_emails.txt"
    
    if os.path.exists(blocklist_file):
        try:
            with open(blocklist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        blocklist.add(line.lower())
        except Exception as e:
            print(f"⚠️ Error loading blocklist: {e}")
    
    return blocklist


def add_to_blocklist(email_address, reason="Unreachable"):
    """Add an email address to the blocklist"""
    blocklist_file = "blocklist/blocked_emails.txt"
    
    # Check if already blocked
    if is_email_blocked(email_address):
        return False
    
    try:
        with open(blocklist_file, 'a', encoding='utf-8') as f:
            f.write(f"{email_address.lower()}  # Auto-blocked: {reason} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        print(f"🚫 Added to blocklist: {email_address} ({reason})")
        return True
    except Exception as e:
        print(f"⚠️ Error adding to blocklist: {e}")
        return False


def is_email_blocked(email_address):
    """Check if an email address is in the blocklist"""
    blocklist = load_blocklist()
    email_lower = email_address.lower()
    
    # Check exact match
    if email_lower in blocklist:
        return True
    
    # Check domain match (entries starting with @)
    for blocked in blocklist:
        if blocked.startswith('@') and email_lower.endswith(blocked):
            return True
        # Check if blocklist entry is a domain without @
        if not blocked.startswith('@') and '@' not in blocked:
            if email_lower.endswith('@' + blocked):
                return True
    
    return False


def generate_message_id(to_email, subject):
    """Generate a unique Message-ID for email threading"""
    # Create a deterministic message ID based on recipient and subject
    unique_string = f"{to_email}_{subject}_{datetime.now().strftime('%Y%m%d')}"
    hash_part = hashlib.md5(unique_string.encode()).hexdigest()[:16]
    return make_msgid(domain="gmail.com", idstring=hash_part)


def send_email(to_email, subject, body, attachment_path=None, message_id=None, in_reply_to=None, references=None):
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
        attachment_path: Optional path to file attachment
        message_id: Optional Message-ID for tracking
        in_reply_to: Optional In-Reply-To header for threading
        references: Optional References header for threading
    
    Returns:
        tuple: (success: bool, message_id: str)
    """
    config = load_email_config()
    if not config:
        print("❌ Failed to load email configuration")
        return False, None
    
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
        
        # Generate or use provided Message-ID
        if not message_id:
            message_id = generate_message_id(to_email, subject)
        msg['Message-ID'] = message_id
        
        # Add threading headers for follow-ups
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references
        
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
        return True, message_id
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False, None


def send_bulk_emails(email_list, subject, body, attachment_path=None):
    """
    Send the same email to multiple recipients with rate limiting.
    
    Args:
        email_list: List of recipient email addresses
        subject: Email subject
        body: Email body text
        attachment_path: Optional path to file attachment
    
    Returns:
        dict: Summary with 'sent' and 'failed' counts, plus message_ids
    """
    sent_count = 0
    failed_count = 0
    blocked_count = 0
    gmail_count = 0
    rate_limited_count = 0
    message_ids = {}  # Store message IDs for threading
    
    # Initialize rate limiter
    rate_limiter = EmailRateLimiter()
    
    # Filter blocked emails and Gmail addresses
    filtered_emails = []
    for email_addr in email_list:
        if is_email_blocked(email_addr):
            print(f"🚫 Blocked: {email_addr}")
            blocked_count += 1
        elif "@gmail.com" in email_addr.lower():
            print(f"📧 Skipped (Gmail): {email_addr}")
            gmail_count += 1
        else:
            filtered_emails.append(email_addr)
    
    print(f"\n📧 Starting rate-limited email sending to {len(filtered_emails)} recipient(s)...")
    if blocked_count > 0:
        print(f"🚫 Blocked {blocked_count} email(s) via blocklist")
    if gmail_count > 0:
        print(f"📧 Skipped {gmail_count} Gmail email(s)")
    
    # Display rate limiter status
    status = rate_limiter.get_status()
    print(f"📊 Rate Limiter Status: {status['daily_sent']}/{status['daily_limit']} daily | {status['hourly_sent']}/{status['hourly_limit']} hourly")
    
    for i, email_addr in enumerate(filtered_emails):
        try:
            # Check if we can send email
            can_send, reason = rate_limiter.can_send_email()
            
            if not can_send:
                print(f"\n⚠️  Rate limit reached: {reason}")
                
                if "Daily limit" in reason:
                    print(f"📅 Daily limit reached. Stopping for today.")
                    reset_info = rate_limiter.get_next_reset_time()
                    print(f"📅 Next reset in: {reset_info['daily_reset']}")
                    break
                    
                elif "Hourly limit" in reason:
                    print(f"⏰ Hourly limit reached. Waiting 1 hour...")
                    reset_info = rate_limiter.get_next_reset_time()
                    print(f"⏰ Next hourly reset in: {reset_info['hourly_reset']}")
                    time.sleep(3600)  # Wait 1 hour
                    continue
                    
                elif "Burst limit" in reason:
                    print(f"💥 Burst limit reached. Taking a 5-minute break...")
                    rate_limiter.wait_if_needed()  # This handles burst cooldown
                    continue
                    
                rate_limited_count += 1
                continue
            
            # Apply rate limiting delay
            rate_limiter.wait_if_needed()
            
            print(f"📧 [{i+1}/{len(filtered_emails)}] Sending to: {email_addr}")
            
            # Send the email
            success, msg_id = send_email(email_addr, subject, body, attachment_path)
            
            if success:
                sent_count += 1
                message_ids[email_addr] = msg_id
                rate_limiter.record_email_sent()
                
                # Show progress every 5 emails
                if sent_count % 5 == 0:
                    current_status = rate_limiter.get_status()
                    print(f"📈 Progress: {sent_count} sent | Daily: {current_status['daily_sent']}/{current_status['daily_limit']} | Hourly: {current_status['hourly_sent']}/{current_status['hourly_limit']}")
                    
            else:
                failed_count += 1
                # Add failed email to blocklist if it bounced
                add_to_blocklist(email_addr, "Send failed")
                
        except KeyboardInterrupt:
            print(f"\n⛔ Email sending interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error sending email to {email_addr}: {e}")
            failed_count += 1
            # Wait a bit on error to avoid rapid failures
            time.sleep(30)
    
    print(f"\n📊 Email Sending Summary:")
    print(f"  ✅ Sent: {sent_count}")
    print(f"  ❌ Failed: {failed_count}")
    if blocked_count > 0:
        print(f"  🚫 Blocked: {blocked_count}")
    if gmail_count > 0:
        print(f"  📧 Gmail skipped: {gmail_count}")
    if rate_limited_count > 0:
        print(f"  ⏱️  Rate limited: {rate_limited_count}")
    
    # Final rate limiter status
    final_status = rate_limiter.get_status()
    print(f"📊 Final Status: {final_status['daily_sent']}/{final_status['daily_limit']} daily emails used")
    
    # Save message IDs to file for threading
    save_message_ids(message_ids)
    
    return {
        'sent': sent_count, 
        'failed': failed_count, 
        'blocked': blocked_count, 
        'gmail_skipped': gmail_count, 
        'rate_limited': rate_limited_count,
        'message_ids': message_ids
    }


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

Applying for {position} - C2C.

# Visa: H1B
# Location: Dallas, TX
# Open to relocation
# Rate: ${pay_rate}/hr

Resume attached.

Best regards,
{full_name}"""
    
    return subject, body


def check_email_replies(hours=3):
    """
    Check Gmail inbox for replies to emails sent in the last X hours.
    Also checks for bounce-back/undeliverable messages and adds to blocklist.
    
    Args:
        hours: How many hours back to check for sent emails
    
    Returns:
        dict: {'replied': [emails], 'no_reply': [emails], 'bounced': [emails]}
    """
    config = load_email_config()
    if not config:
        print("❌ Failed to load email configuration")
        return {'replied': [], 'no_reply': [], 'bounced': []}
    
    sender_email = config['sender_email']
    sender_password = config['sender_password']
    
    try:
        # Connect to Gmail IMAP
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(sender_email, sender_password)
        
        # Select inbox
        imap.select('INBOX')
        
        # Get sent emails from CSV to check
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
        bounced_emails = []
        
        # Check for bounce-back emails
        print("\n🔍 Checking for bounce-back messages...")
        try:
            # Search for common bounce indicators
            bounce_searches = [
                'FROM "mailer-daemon"',
                'FROM "postmaster"',
                'SUBJECT "Undelivered"',
                'SUBJECT "Delivery Status Notification"',
                'SUBJECT "Mail delivery failed"',
                'SUBJECT "Returned mail"',
                'SUBJECT "Address not found"',
                'SUBJECT "Undeliverable"'
            ]
            
            for search_term in bounce_searches:
                _, bounce_ids = imap.search(None, search_term)
                if bounce_ids[0]:
                    for msg_id in bounce_ids[0].split():
                        try:
                            _, msg_data = imap.fetch(msg_id, '(RFC822)')
                            email_message = email.message_from_bytes(msg_data[0][1])
                            
                            # Get the email body
                            body = ""
                            if email_message.is_multipart():
                                for part in email_message.walk():
                                    if part.get_content_type() == "text/plain":
                                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                        break
                            else:
                                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                            
                            # Extract bounced email addresses from body
                            import re
                            # Look for email patterns in bounce message
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            found_emails = re.findall(email_pattern, body)
                            
                            for found_email in found_emails:
                                found_email_lower = found_email.lower()
                                # Check if this email is in our sent list
                                if found_email_lower in sent_emails and found_email_lower not in bounced_emails:
                                    bounced_emails.append(found_email_lower)
                                    print(f"  🔴 Bounced email detected: {found_email_lower}")
                                    
                                    # Add to blocklist
                                    reason = "Undeliverable"
                                    if "domain" in body.lower() and "couldn't be found" in body.lower():
                                        reason = "Domain not found"
                                    elif "address not found" in body.lower():
                                        reason = "Address not found"
                                    
                                    add_to_blocklist(found_email_lower, reason)
                        except Exception as e:
                            print(f"  ⚠️ Error processing bounce message: {e}")
        except Exception as e:
            print(f"  ⚠️ Error checking bounces: {e}")
        
        # Search for emails from the addresses we sent to
        for email_addr in sent_emails.keys():
            if email_addr in bounced_emails:
                continue  # Skip if already identified as bounced
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
        no_reply = [email for email in sent_emails.keys() 
                   if email not in replied_emails and email not in bounced_emails]
        
        imap.close()
        imap.logout()
        
        print(f"\n📊 Reply Summary:")
        print(f"  ✅ Replied: {len(replied_emails)}")
        print(f"  🔴 Bounced: {len(bounced_emails)}")
        print(f"  ⏳ No reply yet: {len(no_reply)}")
        
        return {'replied': replied_emails, 'no_reply': no_reply, 'bounced': bounced_emails}
        
    except Exception as e:
        print(f"❌ Error checking emails: {e}")
        return {'replied': [], 'no_reply': [], 'bounced': []}


def save_message_ids(message_ids):
    """Update emails_output.csv with message IDs for email threading"""
    output_file = "emails_output.csv"
    
    if not os.path.exists(output_file):
        return
    
    try:
        # Read all existing rows
        rows = []
        with open(output_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            
            # Ensure header has Message-ID column
            if header and "Message-ID" not in header:
                header.append("Message-ID")
            
            rows.append(header)
            
            # Read all rows and update message IDs
            for row in reader:
                # Ensure row has 4 columns
                while len(row) < 4:
                    row.append("")
                
                email_addr = row[0]
                # Update message ID if this email was just sent
                if email_addr in message_ids:
                    row[3] = message_ids[email_addr]  # Update Message-ID column
                
                rows.append(row)
        
        # Write back all rows
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
            
    except Exception as e:
        print(f"⚠️ Error saving message IDs: {e}")


def get_original_message_id(email_addr):
    """Get the original message ID for an email address for threading"""
    output_file = "emails_output.csv"
    
    if not os.path.exists(output_file):
        return None
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                # Check if email matches and has a message ID (column index 3)
                if len(row) >= 4 and row[0].lower() == email_addr.lower() and row[3]:
                    return row[3]  # Return the message ID
    except Exception as e:
        print(f"⚠️ Error reading message IDs: {e}")
    
    return None


def send_followup_emails(no_reply_emails, position, personal_info, resume_path=None):
    """
    Send follow-up emails to contacts who haven't replied with RATE LIMITING.
    Uses threading headers to reply in the same email thread.
    
    Args:
        no_reply_emails: List of email addresses
        position: Job position
        personal_info: Personal information dict
        resume_path: Optional path to resume file to attach
    """
    if not no_reply_emails:
        print("✅ No follow-up emails needed")
        return
    
    # Initialize rate limiter for follow-ups
    rate_limiter = EmailRateLimiter()
    
    first_name = personal_info.get('First Name', 'Your Name')
    last_name = personal_info.get('Last Name', '')
    full_name = f"{first_name} {last_name}".strip()
    pay_rate = personal_info.get('ExpectedPayPerHour', 0)
    
    subject = f"Re: Application for {position} - C2C"
    
    body = f"""Hi,

Following up on {position} - C2C.
# Visa: H1B
# Location: Dallas, TX
# Open to relocation
# Rate: ${pay_rate}/hr

Resume attached. Happy to discuss.

Best regards,
{full_name}"""
    
    # Filter blocked emails and Gmail addresses
    filtered_emails = []
    blocked_count = 0
    gmail_count = 0
    for email_addr in no_reply_emails:
        if is_email_blocked(email_addr):
            print(f"🚫 Blocked: {email_addr}")
            blocked_count += 1
        elif "@gmail.com" in email_addr.lower():
            print(f"📧 Skipped (Gmail): {email_addr}")
            gmail_count += 1
        else:
            filtered_emails.append(email_addr)
    
    print(f"\n📧 Sending RATE-LIMITED follow-up emails to {len(filtered_emails)} recipient(s)...")
    if blocked_count > 0:
        print(f"🚫 Blocked {blocked_count} email(s) via blocklist")
    if gmail_count > 0:
        print(f"📧 Skipped {gmail_count} Gmail email(s)")
    
    # Show initial rate limiter status
    status = rate_limiter.get_status()
    print(f"📊 Follow-up Rate Status: {status['daily_sent']}/{status['daily_limit']} daily | {status['hourly_sent']}/{status['hourly_limit']} hourly")
    
    sent_count = 0
    failed_count = 0
    rate_limited_count = 0
    
    for i, email_addr in enumerate(filtered_emails):
        try:
            # Check if we can send email
            can_send, reason = rate_limiter.can_send_email()
            
            if not can_send:
                print(f"\n⚠️  Follow-up rate limit reached: {reason}")
                
                if "Daily limit" in reason:
                    print(f"📅 Daily limit reached. Stopping follow-ups for today.")
                    reset_info = rate_limiter.get_next_reset_time()
                    print(f"📅 Next reset in: {reset_info['daily_reset']}")
                    break
                    
                elif "Hourly limit" in reason:
                    print(f"⏰ Hourly limit reached. Waiting 1 hour for follow-ups...")
                    reset_info = rate_limiter.get_next_reset_time()
                    print(f"⏰ Next hourly reset in: {reset_info['hourly_reset']}")
                    time.sleep(3600)  # Wait 1 hour
                    continue
                    
                elif "Burst limit" in reason:
                    print(f"💥 Burst limit reached. Taking a 5-minute follow-up break...")
                    rate_limiter.wait_if_needed()  # This handles burst cooldown
                    continue
                    
                rate_limited_count += 1
                continue
            
            # Apply rate limiting delay
            rate_limiter.wait_if_needed()
            
            print(f"📧 [{i+1}/{len(filtered_emails)}] Follow-up to: {email_addr}")
            
            # Get original message ID for threading
            original_msg_id = get_original_message_id(email_addr)
            
            # Send with threading headers and resume attachment
            success, _ = send_email(
                email_addr, 
                subject, 
                body,
                attachment_path=resume_path,
                in_reply_to=original_msg_id,
                references=original_msg_id
            )
            
            if success:
                sent_count += 1
                rate_limiter.record_email_sent()
                
                # Show progress every 3 follow-ups
                if sent_count % 3 == 0:
                    current_status = rate_limiter.get_status()
                    print(f"📈 Follow-up Progress: {sent_count} sent | Daily: {current_status['daily_sent']}/{current_status['daily_limit']} | Hourly: {current_status['hourly_sent']}/{current_status['hourly_limit']}")
                    
            else:
                failed_count += 1
                # Add failed email to blocklist
                add_to_blocklist(email_addr, "Follow-up failed")
                
        except KeyboardInterrupt:
            print(f"\n⛔ Follow-up sending interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error sending follow-up to {email_addr}: {e}")
            failed_count += 1
            time.sleep(30)  # Wait on error
    
    print(f"\n📊 Follow-up Email Summary:")
    print(f"  ✅ Sent: {sent_count}")
    print(f"  ❌ Failed: {failed_count}")
    if rate_limited_count > 0:
        print(f"  ⏱️ Rate limited: {rate_limited_count}")
    
    # Final status
    final_status = rate_limiter.get_status()
    print(f"📊 Final Follow-up Status: {final_status['daily_sent']}/{final_status['daily_limit']} total daily emails used")


if __name__ == '__main__':
    # Test the email functionality
    config = load_email_config()
    if config:
        print("✅ Email configuration loaded successfully")
        print(f"Sender: {config['sender_email']}")
        print(f"SMTP Server: {config['smtp_server']}:{config['smtp_port']}")
    else:
        print("❌ Failed to load email configuration")
