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
from email_notifier import check_email_replies, send_followup_emails
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

def validate_yaml():
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
                        'positions',
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
    assert len(parameters['positions']) > 0
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

    assert len(parameters['personalInfo'])
    personal_info = parameters.get('personalInfo', [])
    for info in personal_info:
        assert personal_info[info] != ''

    assert len(parameters['eeo'])
    eeo = parameters.get('eeo', [])
    for survey_question in eeo:
        assert eeo[survey_question] != ''

    return parameters

def space_before_next():
    """Function to keep the program running and wait before next iteration"""
    print("\n⏸️  Waiting 5 minutes before next attempt...")
    print(f"Current time: {datetime.now()}")
    time.sleep(300)  # Wait 5 minutes

if __name__ == '__main__':
    while True:  # Run indefinitely, restart on any error
        try:
            parameters = validate_yaml()
            
            # Check for replies to emails sent in last 3 hours
            print("\n" + "="*60)
            print("CHECKING EMAIL REPLIES")
            print("="*60)
            reply_status = check_email_replies(hours=3)
            
            # Send follow-up emails to those who didn't reply
            if reply_status['no_reply']:
                print("\n📤 Sending follow-up emails...")
                # Group by position from CSV
                import csv
                from datetime import datetime, timedelta
                
                no_reply_by_position = {}
                cutoff_time = datetime.now() - timedelta(hours=3)
                
                if os.path.exists('emails_output.csv'):
                    with open('emails_output.csv', 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        next(reader, None)
                        for row in reader:
                            if len(row) >= 3:
                                email_addr = row[0].lower()
                                position = row[1]
                                sent_time = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S')
                                
                                if email_addr in reply_status['no_reply'] and sent_time >= cutoff_time:
                                    if position not in no_reply_by_position:
                                        no_reply_by_position[position] = []
                                    no_reply_by_position[position].append(email_addr)
                
                # Send follow-ups grouped by position
                for position, emails in no_reply_by_position.items():
                    print(f"\n📋 Position: {position}")
                    send_followup_emails(emails, position, parameters['personalInfo'])
            
            print("\n" + "="*60)
            print("STARTING JOB SEARCH")
            print("="*60)
            
            browser = init_browser()

            bot = LinkedinEasyApply(parameters, browser)
            bot.login()
            bot.security_check()
            bot.search_posts()  # Search for posts using keywords from positions list
            
            current_line = inspect.currentframe().f_lineno
            print("\n✅ Job search completed successfully!")
            print(f"📄 File: {__file__} | Line: {current_line}")
            print("Program finished. Exiting...")
            
            # Close browser and exit
            browser.quit()
            break  # Exit the outer while loop
                
        except KeyboardInterrupt:
            print("\n\n⛔ Program stopped by user.")
            break
        except Exception as e:
            print(f"\n\n❌ Error occurred: {e}")
            print("Restarting...\n")
            space_before_next()