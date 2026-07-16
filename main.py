"""
MAIN.PY - LinkedIn Job Application Bot Entry Point
===================================================
This is the main entry point for an automated LinkedIn job application bot.
It performs the following tasks:

1. Validates configuration from config.yaml (email, password, job preferences, etc.)
2. Initializes a Chrome browser instance with session persistence (chrome_bot directory)
3. Creates a LinkedinEasyApply bot instance that:
   - Logs into LinkedIn
   - Continuously searches for and applies to jobs based on your criteria
   - Handles security checks and application forms
4. Runs indefinitely in a loop - applies to jobs, then waits 10 minutes if no jobs found

Key Features:
- Session restoration to avoid repeated logins
- Automated form filling for LinkedIn Easy Apply jobs
- Configurable job filters (experience, location, remote, etc.)
- Continuous monitoring and application submission
"""

import yaml, os, time, inspect
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from datetime import datetime
from validate_email import validate_email
from webdriver_manager.chrome import ChromeDriverManager
from linkedineasyapply import LinkedinEasyApply
from email_notifier import check_email_replies, send_followup_emails, get_positions, get_resume_mapping, get_personal_info

def load_users():
    """Load user configurations from users.yaml"""
    try:
        with open("users.yaml", 'r', encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
            return config.get('users', [])
    except Exception as e:
        print(f"❌ Error loading users config: {e}")
        return []

def get_enabled_users():
    """Get list of enabled users from users.yaml"""
    users = load_users()
    enabled = [user for user in users if user.get('enabled', False)]
    return enabled

def init_browser():
    browser_options = Options()
    options = [
        '--disable-blink-features',
        '--no-sandbox',
        '--start-maximized',
        '--disable-extensions',
        '--ignore-certificate-errors',
        '--disable-blink-features=AutomationControlled',
        '--remote-debugging-port=9222'
    ]

    # Restore session if possible (avoids login everytime)
    user_data_dir = os.path.join(os.getcwd(), "chrome_bot")
    browser_options.add_argument(f"user-data-dir={user_data_dir}")

    for option in options:
        browser_options.add_argument(option)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=browser_options)
    driver.implicitly_wait(1)  # Wait time in seconds to allow loading of elements
    driver.set_window_position(0, 0)
    driver.maximize_window()
    return driver

def validate_yaml(config_file="users/email1.yaml"):
    """
    Validates config.yaml and loads positions/resumeMapping from user config file
    
    Args:
        config_file: Path to user-specific config file (e.g., users/email1.yaml)
    """
    with open("config.yaml", 'r', encoding='utf-8') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    mandatory_params = ['email',
                        'password',
                        'disableAntiLock',
                        'remote',
                        'lessthanTenApplicants',
                        'experienceLevel',
                        'jobTypes',
                        'date',
                        'locations',
                        'residentStatus',
                        'distance',
                        'outputFileDirectory',
                        'checkboxes',
                        'universityGpa',
                        'languages',
                        'experience',
                        'personalInfo',
                        'eeo',
                        'uploads',
                        'title']

    for mandatory_param in mandatory_params:
        if mandatory_param not in parameters:
            raise Exception(mandatory_param + ' is not defined in the config.yaml file!')

    assert validate_email(parameters['email'])
    assert len(str(parameters['password'])) > 0
    assert isinstance(parameters['disableAntiLock'], bool)
    assert isinstance(parameters['remote'], bool)
    assert isinstance(parameters['lessthanTenApplicants'], bool)
    assert isinstance(parameters['residentStatus'], bool)
    assert isinstance(parameters['title'], list) and len(parameters['title']) > 0
    assert len(parameters['experienceLevel']) > 0
    experience_level = parameters.get('experienceLevel', [])
    at_least_one_experience = False

    for key in experience_level.keys():
        if experience_level[key]:
            at_least_one_experience = True
    assert at_least_one_experience

    assert len(parameters['jobTypes']) > 0
    job_types = parameters.get('jobTypes', [])
    at_least_one_job_type = False
    for key in job_types.keys():
        if job_types[key]:
            at_least_one_job_type = True

    assert at_least_one_job_type
    assert len(parameters['date']) > 0
    date = parameters.get('date', [])
    at_least_one_date = False

    for key in date.keys():
        if date[key]:
            at_least_one_date = True
    assert at_least_one_date

    approved_distances = {0, 5, 10, 25, 50, 100}
    assert parameters['distance'] in approved_distances
    assert len(parameters['locations']) > 0
    assert len(parameters['uploads']) >= 1 and 'resume' in parameters['uploads']
    assert len(parameters['checkboxes']) > 0

    checkboxes = parameters.get('checkboxes', [])
    assert isinstance(checkboxes['driversLicence'], bool)
    assert isinstance(checkboxes['requireVisa'], bool)
    assert isinstance(checkboxes['legallyAuthorized'], bool)
    assert isinstance(checkboxes['certifiedProfessional'], bool)
    assert isinstance(checkboxes['urgentFill'], bool)
    assert isinstance(checkboxes['commute'], bool)
    assert isinstance(checkboxes['backgroundCheck'], bool)
    assert isinstance(checkboxes['securityClearance'], bool)
    assert 'degreeCompleted' in checkboxes
    assert isinstance(parameters['universityGpa'], (int, float))

    languages = parameters.get('languages', [])
    language_types = {'none', 'conversational', 'professional', 'native or bilingual'}
    for language in languages:
        assert languages[language].lower() in language_types

    experience = parameters.get('experience', [])
    for tech in experience:
        assert isinstance(experience[tech], int)
    assert 'default' in experience

    assert len(parameters['eeo'])
    eeo = parameters.get('eeo', [])
    for survey_question in eeo:
        assert eeo[survey_question] != ''

    # Load positions, resumeMapping, and personalInfo from user-specific config
    positions = get_positions(config_file)
    resume_mapping = get_resume_mapping(config_file)
    personal_info = get_personal_info(config_file)
    
    assert len(positions) > 0, f"At least one position must be defined in {config_file}"
    assert len(personal_info) > 0, f"Personal info must be defined in {config_file}"
    
    # Override config.yaml personalInfo with user-specific personalInfo
    parameters['positions'] = positions
    parameters['resumeMapping'] = resume_mapping
    parameters['personalInfo'] = personal_info

    return parameters

def space_before_next():
    """Function to keep the program running and wait before next iteration"""
    print("\n⏸️  Waiting 5 minutes before next attempt...")
    print(f"Current time: {datetime.now()}")
    time.sleep(300)  # Wait 5 minutes

if __name__ == '__main__':
    while True:  # Run indefinitely, restart on any error
        try:
            # Load enabled users from users.yaml
            enabled_users = get_enabled_users()
            
            if not enabled_users:
                print("❌ No enabled users found in users.yaml!")
                print("⏸️  Waiting 5 minutes before retrying...")
                time.sleep(300)
                continue
            
            print(f"\n🎯 Found {len(enabled_users)} enabled user(s)")
            
            # Process each enabled user
            for user in enabled_users:
                user_name = user.get('name', 'Unknown')
                config_file = user.get('config_file', 'users/email1.yaml')
                
                print("\n" + "="*70)
                print(f"👤 PROCESSING USER: {user_name}")
                print(f"📁 Config: {config_file}")
                print("="*70)
                
                # Validate configuration for this user
                parameters = validate_yaml(config_file)
                
                # Check for replies to emails sent in last 3 hours
                print("\n" + "="*60)
                print(f"CHECKING EMAIL REPLIES FOR {user_name}")
                print("="*60)
                
                # Re-check if user is still enabled (in case users.yaml changed during execution)
                current_enabled_users = get_enabled_users()
                user_still_enabled = any(u.get('config_file') == config_file for u in current_enabled_users)
                
                if not user_still_enabled:
                    print(f"⚠️ User {user_name} is now disabled in users.yaml, skipping email checks")
                else:
                    reply_status = check_email_replies(hours=3, config_file=config_file)
                    
                    # Process unsent and no-reply emails
                    print("\n📤 Processing unsent and follow-up emails...")
                    import csv
                    from datetime import datetime, timedelta
                    
                    unsent_by_position = {}  # Emails that were logged but never sent
                    no_reply_by_position = {}  # Emails that were sent but got no reply
                    cutoff_time = datetime.now() - timedelta(hours=3)
                    
                    # Get sender email from current user's config
                    from email_notifier import load_email_config, create_email_template, send_bulk_emails
                    user_email_config = load_email_config(config_file)
                    current_sender_email = user_email_config['sender_email'].lower() if user_email_config else 'unknown'
                    
                    if os.path.exists('emails_output.csv'):
                        with open('emails_output.csv', 'r', encoding='utf-8') as f:
                            reader = csv.reader(f)
                            next(reader, None)
                            for row in reader:
                                if len(row) >= 7:  # New format with Sent column
                                    email_addr = row[0].lower()
                                    position = row[1]
                                    sent_time = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S')
                                    row_sender = row[5].lower() if len(row) > 5 else ''
                                    was_sent = row[6].lower() == 'true' if len(row) > 6 else True  # Default true for old entries
                                    
                                    # Only process emails from THIS user for their positions
                                    if (row_sender == current_sender_email and
                                        position in parameters.get('positions', []) and
                                        sent_time >= cutoff_time):
                                        
                                        # Separate unsent vs no-reply
                                        if not was_sent:
                                            # Email was logged but never sent (program crashed)
                                            if position not in unsent_by_position:
                                                unsent_by_position[position] = []
                                            unsent_by_position[position].append(email_addr)
                                        elif email_addr in reply_status['no_reply']:
                                            # Email was sent but got no reply
                                            if position not in no_reply_by_position:
                                                no_reply_by_position[position] = []
                                            no_reply_by_position[position].append(email_addr)
                    
                    resume_mapping = parameters.get('resumeMapping', {})
                    
                    # First, resend unsent emails as ORIGINAL emails (not follow-ups)
                    if unsent_by_position:
                        print("\n🔄 Re-sending emails that failed to send previously...")
                        for position, emails in unsent_by_position.items():
                            print(f"\n📋 Position: {position} - {len(emails)} unsent email(s)")
                            
                            # Get resume
                            resume_filename = resume_mapping.get(position)
                            resume_path = os.path.join("resumes", resume_filename) if resume_filename else None
                            
                            if resume_path and os.path.exists(resume_path):
                                print(f"📎 Using resume: {resume_filename}")
                                
                                # Send as ORIGINAL email (not follow-up)
                                subject, body = create_email_template(position, parameters['personalInfo'], config_file)
                                send_bulk_emails(emails, subject, body, resume_path, config_file)
                            else:
                                print(f"⚠️ Resume not found, skipping: {position}")
                    
                    # Add delay between unsent and follow-up batches
                    if unsent_by_position and no_reply_by_position:
                        print("\n⏸️  Taking a 1-minute break between unsent and follow-up emails...")
                        time.sleep(60)
                    
                    # Then, send follow-ups for emails that were sent but got no reply
                    if no_reply_by_position:
                        print("\n📤 Sending follow-up emails...")
                        for position, emails in no_reply_by_position.items():
                            print(f"\n📋 Position: {position} - {len(emails)} follow-up(s)")
                            
                            # Get resume
                            resume_filename = resume_mapping.get(position)
                            resume_path = os.path.join("resumes", resume_filename) if resume_filename else None
                            
                            if resume_path and os.path.exists(resume_path):
                                print(f"📎 Using resume for follow-up: {resume_filename}")
                                send_followup_emails(emails, position, parameters['personalInfo'], resume_path, config_file)
                            else:
                                print(f"⚠️ Resume not found for follow-up: {position}")
                
                print("\n" + "="*60)
                print(f"STARTING JOB SEARCH FOR {user_name}")
                print("="*60)
                
                browser = init_browser()

                bot = LinkedinEasyApply(parameters, browser, config_file)
                bot.login()
                bot.security_check()
                bot.search_posts()
                
                current_line = inspect.currentframe().f_lineno
                print(f"\n✅ Job search completed for {user_name}!")
                print(f"📄 File: {__file__} | Line: {current_line}")
                
                # Close browser for this user
                browser.quit()
                
                print(f"\n✅ Completed processing for {user_name}")
                print("="*70)
                
                # Add delay between users to avoid being flagged as spam
                if user != enabled_users[-1]:  # Not the last user
                    print("\n⏸️  Taking a 1-minute break before processing next user...")
                    time.sleep(60)
            
            print("\n✅ All enabled users processed successfully!")
            print("Program finished. Exiting...")
            break  # Exit the outer while loop
                
        except KeyboardInterrupt:
            print("\n\n⛔ Program stopped by user.")
            break
        except Exception as e:
            print(f"\n\n❌ Error occurred: {e}")
            print("Restarting...\n")
            space_before_next()