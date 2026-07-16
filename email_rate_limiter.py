"""
EMAIL_RATE_LIMITER.PY - Gmail Rate Limiting System
=================================================
This module prevents Gmail from blocking your account by implementing
intelligent email sending limits and delays.
"""

import time
import random
from datetime import datetime, timedelta
import logging

class EmailRateLimiter:
    def __init__(self):
        self.emails_sent_today = 0
        self.last_reset = datetime.now().date()
        self.last_email_time = None
        
        # Gmail limits - Conservative to avoid blocks
        self.DAILY_LIMIT = 400      # Gmail's limit is 500, we use 400 to be safe
        self.HOURLY_LIMIT = 50      # Conservative hourly limit
        self.BURST_LIMIT = 15       # Emails per burst before longer delay
        self.MIN_DELAY = 10         # Minimum seconds between emails
        self.MAX_DELAY = 25         # Maximum seconds between emails
        self.BURST_DELAY = 120      # 2 minutes between bursts
        
        self.emails_this_hour = []
        self.emails_this_burst = 0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    def can_send_email(self):
        """Check if we can send an email now"""
        now = datetime.now()
        
        # Reset daily counter at midnight
        if now.date() > self.last_reset:
            self.emails_sent_today = 0
            self.last_reset = now.date()
            logging.info("Daily email counter reset")
            
        # Remove emails older than 1 hour from tracking
        hour_ago = now - timedelta(hours=1)
        self.emails_this_hour = [t for t in self.emails_this_hour if t > hour_ago]
        
        # Check daily limit
        if self.emails_sent_today >= self.DAILY_LIMIT:
            return False, f"Daily limit reached ({self.emails_sent_today}/{self.DAILY_LIMIT})"
            
        # Check hourly limit
        if len(self.emails_this_hour) >= self.HOURLY_LIMIT:
            return False, f"Hourly limit reached ({len(self.emails_this_hour)}/{self.HOURLY_LIMIT})"
            
        # Check burst limit
        if self.emails_this_burst >= self.BURST_LIMIT:
            return False, f"Burst limit reached ({self.emails_this_burst}/{self.BURST_LIMIT})"
            
        return True, "OK to send"
        
    def wait_if_needed(self):
        """Wait appropriate time before sending next email"""
        now = datetime.now()
        
        if self.last_email_time:
            time_since_last = (now - self.last_email_time).total_seconds()
            
            # If we've hit burst limit, wait longer and reset burst counter
            if self.emails_this_burst >= self.BURST_LIMIT:
                wait_time = self.BURST_DELAY
                self.emails_this_burst = 0  # Reset burst counter
                print(f"🔄 Burst limit reached. Cooling down for {int(wait_time//60)} minutes {int(wait_time%60)} seconds...")
                time.sleep(wait_time)
            else:
                # Calculate random delay between min and max, minus time already passed
                required_delay = random.randint(self.MIN_DELAY, self.MAX_DELAY)
                wait_time = max(0, required_delay - time_since_last)
                
                if wait_time > 0:
                    print(f"⏱️  Rate limiting: waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                
    def record_email_sent(self):
        """Record that an email was sent successfully"""
        now = datetime.now()
        self.last_email_time = now
        self.emails_sent_today += 1
        self.emails_this_hour.append(now)
        self.emails_this_burst += 1
        
        # Log progress every 10 emails
        if self.emails_sent_today % 10 == 0:
            status = self.get_status()
            print(f"📊 Progress: {status['daily_sent']}/{status['daily_limit']} daily | {status['hourly_sent']}/{status['hourly_limit']} hourly | {status['burst_sent']}/{status['burst_limit']} burst")
        
    def get_status(self):
        """Get current rate limiting status"""
        return {
            'daily_sent': self.emails_sent_today,
            'daily_limit': self.DAILY_LIMIT,
            'hourly_sent': len(self.emails_this_hour),
            'hourly_limit': self.HOURLY_LIMIT,
            'burst_sent': self.emails_this_burst,
            'burst_limit': self.BURST_LIMIT
        }
        
    def get_next_reset_time(self):
        """Get time until next reset"""
        now = datetime.now()
        
        # Time until daily reset (midnight)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        daily_reset = tomorrow - now
        
        # Time until hourly reset
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        hourly_reset = next_hour - now
        
        return {
            'daily_reset': str(daily_reset).split('.')[0],  # Remove microseconds
            'hourly_reset': str(hourly_reset).split('.')[0]
        }
        
    def should_pause_for_hour(self):
        """Check if we should pause sending for an hour"""
        return len(self.emails_this_hour) >= self.HOURLY_LIMIT
        
    def should_pause_for_day(self):
        """Check if we should pause sending for the day"""
        return self.emails_sent_today >= self.DAILY_LIMIT