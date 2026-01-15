"""
LINKEDINEASYAPPLY.PY - LinkedIn Login Handler
==============================================
This file contains the LinkedinEasyApply class that handles:
- LinkedIn login with session persistence
- Security checkpoint detection and handling  
- Browser initialization and configuration

The login() method attempts to restore a previous session from chrome_bot directory.
If no session exists or it's expired, it calls load_login_page_and_login() to perform
a fresh login using credentials from config.yaml.
"""

import time, random, os, re, csv
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from datetime import datetime
from email_notifier import send_bulk_emails, create_email_template


class LinkedinEasyApply:
    def __init__(self, parameters, driver):
        self.browser = driver
        
        self.email = parameters['email']
        self.password = parameters['password']
        self.disable_lock = parameters['disableAntiLock']
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.poster_blacklist = parameters.get('posterBlacklist', []) or []
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.residency = parameters.get('residentStatus', [])
        self.seen_jobs = []
        self.file_name = "output"
        self.unprepared_questions_file_name = "unprepared_questions"
        self.output_file_directory = parameters['outputFileDirectory']
        self.resume_dir = parameters['uploads']['resume']
        if 'coverLetter' in parameters['uploads']:
            self.cover_letter_dir = parameters['uploads']['coverLetter']
        else:
            self.cover_letter_dir = ''
        self.checkboxes = parameters.get('checkboxes', [])
        self.university_gpa = parameters['universityGpa']
        self.salary_minimum = parameters['salaryMinimum']
        self.notice_period = int(parameters['noticePeriod'])
        self.languages = parameters.get('languages', [])
        self.experience = parameters.get('experience', [])
        self.personal_info = parameters.get('personalInfo', [])
        self.eeo = parameters.get('eeo', [])
        self.experience_default = int(self.experience['default'])
        self.stop_processing = False
        self.titles = parameters.get('title', [])
        self.date = parameters.get('date', {})
        self.sort_by = parameters.get('sort_by', {})
        self.resume_mapping = parameters.get('resumeMapping', {})

        options = webdriver.ChromeOptions()

    def login(self):
        """
        Attempts to restore previous LinkedIn session or performs fresh login.
        Checks if chrome_bot session directory exists and tries to load LinkedIn feed.
        If session is invalid or doesn't exist, calls load_login_page_and_login().
        """
        try:
            # Check if the "chrome_bot" directory exists
            print("Attempting to restore previous session...")
            if os.path.exists("chrome_bot"):
                self.browser.get("https://www.linkedin.com/feed/")
                time.sleep(random.uniform(5, 10))

                # Check if the current URL is the feed page
                if self.browser.current_url != "https://www.linkedin.com/feed/":
                    print("Feed page not loaded, proceeding to login.")
                    self.load_login_page_and_login()
            else:
                print("No session found, proceeding to login.")
                self.load_login_page_and_login()

        except TimeoutException:
            print("Timeout occurred, checking for security challenges...")
            self.security_check()

    def security_check(self):
        """
        Detects LinkedIn security challenges and pauses for manual completion.
        Checks URL and page source for security checkpoint indicators.
        """
        current_url = self.browser.current_url
        page_source = self.browser.page_source

        if '/checkpoint/challenge/' in current_url or 'security check' in page_source or 'quick verification' in page_source:
            input("Please complete the security check and press enter on this console when it is done.")
            time.sleep(random.uniform(5.5, 10.5))

    def load_login_page_and_login(self):
        """
        Performs fresh LinkedIn login using credentials from config.yaml.
        Navigates to login page, enters email/password, clicks login button,
        and waits for successful redirect to feed page.
        """
        self.browser.get("https://www.linkedin.com/login")

        # Wait for the username field to be present
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        self.browser.find_element(By.ID, "username").send_keys(self.email)
        self.browser.find_element(By.ID, "password").send_keys(self.password)
        self.browser.find_element(By.CSS_SELECTOR, ".btn__primary--large").click()

        # Wait for the feed page to load after login
        WebDriverWait(self.browser, 10).until(
            EC.url_contains("https://www.linkedin.com/feed/")
        )

        time.sleep(random.uniform(5, 10))

    def search_posts(self):
        """
        Searches for LinkedIn posts using positions/keywords from config.yaml.
        Iterates through each position, constructs post search URL with date and sort filters,
        and navigates to filtered post results.
        """
        print("\n🔍 Starting post search...")
        
        # Determine date filter from config
        date_filter = ""
        if self.date.get('24 hours', False):
            date_filter = "past-24h"
        elif self.date.get('week', False):
            date_filter = "past-week"
        elif self.date.get('month', False):
            date_filter = "past-month"
        
        # Determine sort order from config
        sort_order = "relevance"  # default
        if self.sort_by.get('date_posted', False):
            sort_order = "date_posted"
        elif self.sort_by.get('relevance', False):
            sort_order = "relevance"
        
        # Iterate through positions from config (used as search keywords)
        for position in self.positions:
            print(f"\n📌 Searching posts for: {position}")
            
            # Build search URL with filters
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={position}"
            
            # Add date filter if configured
            if date_filter:
                search_url += f"&datePosted=%22{date_filter}%22"
            
            # Add sort order
            search_url += f"&sortBy=%22{sort_order}%22"
            
            # Add origin parameter
            search_url += "&origin=FACETED_SEARCH"
            
            print(f"🌐 URL: {search_url}")
            print(f"📅 Date filter: {date_filter if date_filter else 'all time'}")
            print(f"🔃 Sort by: {sort_order}")
            
            self.browser.get(search_url)
            time.sleep(random.uniform(3, 5))
            
            print(f"✅ Successfully navigated to post search page for '{position}'")
            
            # Scroll down to load more content
            print("\n📜 Scrolling to load more posts...")
            scroll_pause_time = 2
            scroll_increments = 15  # Number of times to scroll
            
            for i in range(scroll_increments):
                # Scroll down
                self.browser.execute_script("window.scrollBy(0, 800);")
                time.sleep(random.uniform(1.5, 2.5))
                print(f"  Scrolled {i+1}/{scroll_increments}")
            
            print("✅ Finished scrolling, content loaded")
            
            # Extract emails from page text
            print("\n📧 Extracting email addresses from page...")
            page_text = self.browser.page_source
            
            # Regex pattern to find emails (must contain @ and .com)
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.com\b'
            emails_found = re.findall(email_pattern, page_text)
            
            # Remove duplicates
            unique_emails = list(set(emails_found))
            
            print(f"✅ Found {len(unique_emails)} unique email(s)")
            
            # Save to output file
            if unique_emails:
                new_emails_logged = self.save_emails_to_file(unique_emails, position)
                # Generate email template and send emails
                if new_emails_logged:
                    self.send_emails_to_contacts(new_emails_logged, position)
            else:
                print("⚠️ No emails found on this page")
            
            # Pause after first position for now

    def save_emails_to_file(self, emails, position):
        """
        Saves extracted emails to CSV file with timestamp and position.
        Avoids duplicates: same email + same position on same day won't be re-logged.
        """
        output_file = "emails_output.csv"
        file_exists = os.path.isfile(output_file)
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        current_datetime = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Read existing entries to check for duplicates
        existing_entries = set()
        if file_exists:
            with open(output_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 3:
                        email = row[0]
                        pos = row[1]
                        date_str = row[2].split(' ')[0]  # Extract date only (YYYY-MM-DD)
                        existing_entries.add((email, pos, date_str))
        
        # Filter out duplicates
        new_emails = []
        skipped_count = 0
        for email in emails:
            entry_key = (email, position, current_date)
            if entry_key in existing_entries:
                print(f"  ⏭️  Skipped (already logged today): {email}")
                skipped_count += 1
            else:
                new_emails.append(email)
        
        # Write only new emails
        if new_emails:
            with open(output_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header if file doesn't exist
                if not file_exists:
                    writer.writerow(["Email", "Position", "Date/Time"])
                
                # Write each new email
                for email in new_emails:
                    writer.writerow([email, position, current_datetime])
                    print(f"  📝 Logged: {email}")
            
            print(f"\n✅ Saved {len(new_emails)} new email(s) to {output_file}")
        else:
            print(f"\n⚠️ No new emails to save")
        
        if skipped_count > 0:
            print(f"⏭️  Skipped {skipped_count} duplicate(s) from today")
        
        return new_emails  # Return list of new emails that were logged

    def send_emails_to_contacts(self, email_list, position):
        """
        Sends emails to all contacts using the email template.
        Uses position-specific resume from resumeMapping.
        """
        # Create email template using email_notifier
        subject, body = create_email_template(position, self.personal_info)
        
        # Get position-specific resume from mapping
        resume_filename = self.resume_mapping.get(position)
        resume_path = None
        
        if resume_filename:
            resume_path = os.path.join("resumes", resume_filename)
            if os.path.exists(resume_path):
                print(f"📎 Using resume: {resume_filename}")
            else:
                print(f"⚠️ Resume not found: {resume_path}")
                resume_path = None
        else:
            print(f"⚠️ No resume mapping found for position: {position}")
        
        # Send emails
        print(f"\n📧 Sending emails to {len(email_list)} recipient(s)...")
        send_bulk_emails(email_list, subject, body, resume_path)
