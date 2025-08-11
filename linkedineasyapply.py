import time, random, csv, pyautogui, pdb, traceback, sys, os, re
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from datetime import date, datetime
from itertools import product
import logging
from email_notifier import send_email




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
        self.base_search_url = self.get_base_search_url(parameters)
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
        self.date = parameters.get('date', {})  # ✅ Store `date` setting from config file



        options = webdriver.ChromeOptions()

    def login(self):
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
            # raise Exception("Could not login!")

    def security_check(self):
        current_url = self.browser.current_url
        page_source = self.browser.page_source

        if '/checkpoint/challenge/' in current_url or 'security check' in page_source or 'quick verification' in page_source:
            input("Please complete the security check and press enter on this console when it is done.")
            time.sleep(random.uniform(5.5, 10.5))

    def load_login_page_and_login(self):
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

    def start_applying(self):
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)

        for (position, location) in searches:
            location_url = "&location=" + location
            job_page_number = 0

            print(f"Starting the search for '{position}' in '{location}'.")

            while True:
                print(f"Navigating to job page number {job_page_number} for '{position}' in '{location}'.")
                try:
                    self.next_job_page(position, location_url, job_page_number)
                    time.sleep(random.uniform(1.0, 2.0))  # brief wait for page load
                    
                    print("Extracting and logging jobs on this page...")
                    self.apply_jobs(location)

                    print(f"Completed logging jobs from page {job_page_number} for '{position}' in '{location}'.\n")
                    job_page_number += 1  # proceed to next page

                except Exception as e:
                    print(f"No more job pages found or an error occurred: {e}")
                    traceback.print_exc()
                    break  # Exit while loop if there's no next page or any error occurs


    def apply_jobs(self, location):
        jobs_data = []

        # Check for explicit "no jobs" messages
        page_source_lower = self.browser.page_source.lower()

        if 'no matching jobs found' in page_source_lower:
            print("🚫 No matching jobs found on this page.")
            raise Exception("No more jobs available.")
        if 'unfortunately, things are' in page_source_lower:
            print("🚫 LinkedIn error detected.")
            raise Exception("No more jobs available due to LinkedIn error.")
        if 'jobs you may be interested in' in page_source_lower:
            print("🚫 No specific jobs, only recommendations shown.")
            raise Exception("Only recommended jobs available, exiting.")

        # Dynamically find the job list container
        try:
            child_element = self.browser.find_element(By.CLASS_NAME, "scaffold-layout__list-item")
            parent_element = child_element.find_element(By.XPATH, "..")
            parent_class_name = parent_element.get_attribute("class").split()[0]

            job_results_by_class = self.browser.find_element(By.CSS_SELECTOR, f".{parent_class_name}")
            self.scroll_slow(job_results_by_class)
            self.scroll_slow(job_results_by_class, step=300, reverse=True)

            job_list = self.browser.find_elements(By.CLASS_NAME, parent_class_name)[0].find_elements(
                By.CLASS_NAME, 'scaffold-layout__list-item')

            if not job_list:
                print("🚫 No job elements found on page.")
                raise Exception("No job elements found.")
        except Exception as e:
            print(f"🚫 Exception during job extraction: {e}")
            raise Exception("Exiting due to extraction issue.")

        # Extract and log details for each job
        for job_tile in job_list:
            job_title = company = poster = job_location = apply_method = link = ""

            try:
                job_title_element = job_tile.find_element(By.CLASS_NAME, 'job-card-container__link')
                job_title = job_title_element.find_element(By.TAG_NAME, 'strong').text
                link = job_title_element.get_attribute('href').split('?')[0]
            except:
                continue

            try:
                company = job_tile.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
            except:
                pass
            try:
                hiring_line = job_tile.find_element(By.XPATH, './/span[contains(., "is hiring for this")]')
                poster = hiring_line.text.split(' is hiring for this')[0]
            except:
                pass
            try:
                job_location = job_tile.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
            except:
                pass
            try:
                apply_method = job_tile.find_element(By.CLASS_NAME, 'job-card-container__apply-method').text
            except:
                pass

            contains_blacklisted_keywords = any(word.lower() in job_title.lower() for word in self.title_blacklist)

            if (company.lower() not in map(str.lower, self.company_blacklist) and
                poster.lower() not in map(str.lower, self.poster_blacklist) and
                not contains_blacklisted_keywords and
                link not in self.seen_jobs and
                self.is_valid_job(job_title)):

                print(f"✅ Logging valid job: {job_title} at {company}")
                jobs_data.append([
                    job_title, company, poster, job_location, apply_method, link, location, datetime.now()
                ])
                self.seen_jobs.append(link)
            else:
                print(f"❌ Skipped job: {job_title} at {company}")

        self.write_jobs_to_csv(jobs_data)

        
    def write_jobs_to_csv(self, jobs_data):
            file_path = f"{self.file_name}.csv"
            header = ["Job Title", "Company", "Poster", "Job Location", "Apply Method", "Job Link", "Search Location", "Timestamp"]

            existing_links = set()
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader, None)  # Skip header
                    for row in reader:
                        if len(row) >= 6:
                            existing_links.add(row[5])

            # Filter out jobs already logged
            new_jobs_data = []
            email_body = "📢 New Jobs Logged:\n\n"

            for job in jobs_data:
                if job[5] in existing_links:
                    print(f"⚠️ Job already present, skipping: {job[0]} at {job[1]}")
                else:
                    print(f"✅ New job log added: {job[0]} at {job[1]}")
                    new_jobs_data.append(job)
                    # Add details to email body
                    email_body += f"🔹 **{job[0]}** at **{job[1]}**\n"
                    email_body += f"📍 Location: {job[3]}\n"
                    email_body += f"📝 Apply Method: {job[4]}\n"
                    email_body += f"🔗 Job Link: {job[5]}\n"
                    email_body += f"🔎 Search Location: {job[6]}\n"
                    email_body += f"⏳ Timestamp: {job[7]}\n"
                    email_body += "-" * 50 + "\n"

            # Write only new jobs to CSV
            if new_jobs_data:
                file_exists = os.path.isfile(file_path)
                with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    if not file_exists:
                        writer.writerow(header)
                    writer.writerows(new_jobs_data)

                print(f"Successfully logged {len(new_jobs_data)} new jobs to {file_path}.")

                # Send email notification
                email_subject = f"📌 {len(new_jobs_data)} New Jobs Logged"
                send_email(email_subject, email_body)

            else:
                print("No new jobs to log.")

    def unfollow(self):
        try:
            follow_checkbox = self.browser.find_element(By.XPATH,
                                                        "//label[contains(.,\'to stay up to date with their page.\')]").click()
            follow_checkbox.click()
        except:
            pass

  

    def enter_text(self, element, text):
        element.clear()
        element.send_keys(text)

    def select_dropdown(self, element, text):
        select = Select(element)
        select.select_by_visible_text(text)

    # Radio Select
    def radio_select(self, element, label_text, clickLast=False):
        label = element.find_element(By.TAG_NAME, 'label')
        if label_text in label.text.lower() or clickLast == True:
            label.click()

    # Contact info fill-up
    def contact_info(self, form):
        print("Trying to fill up contact info fields")
        frm_el = form.find_elements(By.TAG_NAME, 'label')
        if len(frm_el) > 0:
            for el in frm_el:
                text = el.text.lower()
                if 'email address' in text:
                    continue
                elif 'phone number' in text:
                    try:
                        country_code_picker = el.find_element(By.XPATH,
                                                              '//select[contains(@id,"phoneNumber")][contains(@id,"country")]')
                        self.select_dropdown(country_code_picker, self.personal_info['Phone Country Code'])
                    except Exception as e:
                        print("Country code " + self.personal_info[
                            'Phone Country Code'] + " not found. Please make sure it is same as in LinkedIn.")
                        print(e)
                    try:
                        phone_number_field = el.find_element(By.XPATH,
                                                             '//input[contains(@id,"phoneNumber")][contains(@id,"nationalNumber")]')
                        self.enter_text(phone_number_field, self.personal_info['Mobile Phone Number'])
                    except Exception as e:
                        print("Could not enter phone number:")
                        print(e)

 

    def write_to_file(self, company,no_applicants, job_title, link, location, search_location):
        to_write = [company,no_applicants, job_title, link, location, search_location,datetime.now()]
        file_path = self.file_name + ".csv"
        print(f'updated {file_path}.')

        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(to_write)


    def scroll_slow(self, scrollable_element, start=0, end=3600, step=100, reverse=False):
        try:
            # Check if the element is scrollable
            is_scrollable = self.browser.execute_script(
                "return arguments[0].scrollHeight > arguments[0].clientHeight", scrollable_element
            )
            if not is_scrollable:
                print("The element is not scrollable.")
                return

            # Adjust parameters for reverse scrolling
            if reverse:
                start, end = end, start
                step = -step

            # Get the scrollable height
            element_height = self.browser.execute_script("return arguments[0].scrollHeight", scrollable_element)
            print(f"Element scrollable height: {element_height}")
            end = min(end, element_height)

            # Perform scrolling
            for i in range(start, end, step):
                try:
                    self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollable_element)
                    time.sleep(random.uniform(1.0, 2.6))
                except StaleElementReferenceException:
                    print("Scrollable element became stale during scrolling.")
                    break
        except Exception as e:
            print(f"An error occurred while scrolling: {e}")
    
    
    def is_valid_job(self, job_title):
        keywords = ['front', 'full', 'ui', 'ux', 'web', 'react', 'angular', 'data']
        cleaned_title = job_title.replace(" ", "").replace("-", "").lower()

        for keyword in keywords:
            if self.keyword_in_title(cleaned_title, keyword):
                return True
        return False

    def keyword_in_title(self, title, keyword):
        title_len = len(title)
        keyword_len = len(keyword)

        for i in range(title_len - keyword_len + 1):
            match_found = True
            for j in range(keyword_len):
                if title[i + j] != keyword[j]:
                    match_found = False
                    break
            if match_found:
                return True
        return False


    def avoid_lock(self):
        if self.disable_lock:
            return

        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(1.0)
        pyautogui.press('esc')


    def get_base_search_url(self, parameters):
        remote_url = ""
        lessthanTenApplicants_url = ""

        if parameters.get('remote'):
            remote_url = "&f_WT=2"  # Filter for remote jobs
        else:
            remote_url = ""  # Adjust for hybrid/onsite options

        if parameters['lessthanTenApplicants']:
            lessthanTenApplicants_url = "&f_EA=true"  # Filter for jobs with <10 applicants

        level = 1
        experience_level = parameters.get('experienceLevel', [])
        experience_url = "f_E="
        for key in experience_level.keys():
            if experience_level[key]:
                experience_url += "%2C" + str(level)
            level += 1

        distance_url = "?distance=" + str(parameters['distance'])

        job_types_url = "f_JT="
        job_types = parameters.get('jobTypes', [])
        for key in job_types:
            if job_types[key]:
                job_types_url += "%2C" + key[0].upper()

        # **🔹 Toggle 24-hour filter based on config**
        enable_24_hour_filter = parameters.get('date', {}).get('24 hours', False)  # Read setting
        date_url = "&f_TPR=r86400" if enable_24_hour_filter else ""  # Apply if enabled

        easy_apply_url = "&f_AL=false"  # Prevents Easy Apply-only filtering issues

        # **Combine all filters into one query**
        extra_search_terms = [
            distance_url, remote_url, lessthanTenApplicants_url, job_types_url, experience_url
        ]
        extra_search_terms_str = '&'.join(
            term for term in extra_search_terms if len(term) > 0
        ) + easy_apply_url + date_url  # ✅ Append the forced 24-hour filter (if enabled)

        return extra_search_terms_str

    def next_job_page(self, position, location, job_page):
        # **Step 1: Perform a dummy search for a common job to refresh LinkedIn's cache**
        # dummy_url = "https://www.linkedin.com/jobs/search/?keywords=iOS%20Developer"
        # print("🔍 Performing dummy search for 'iOS Developer' before actual search...")
        # self.browser.get(dummy_url)

        # # **Step 2: Wait briefly**
        # time.sleep(10)

        # **Step 3: Read 24-hour filter setting using instance variable**
        enable_24_hour_filter = self.date.get('24 hours', False)  # ✅ Use `self.date` instead of `self.parameters`

        # **Step 4: Construct the actual job search URL**
        actual_url = f"https://www.linkedin.com/jobs/search/{self.base_search_url}&keywords={position}{location}&start={job_page * 25}"

        # **Apply 24-hour filter if enabled**
        if enable_24_hour_filter:
            actual_url += "&f_TPR=r3600"

        print(f"🔍 Performing actual job search for '{position}' in '{location}', Page {job_page}")
        self.browser.get(actual_url)
        time.sleep(30)

        self.avoid_lock()

    # def get_base_search_url(self, parameters):
    #         remote_url = ""
    #         lessthanTenApplicants_url = ""

    #         if parameters.get('remote'):
    #             remote_url = "&f_WT=2"
    #         else:
    #             remote_url = ""  # TO DO: Other &f_WT= options { WT=1 onsite, WT=2 remote, WT=3 hybrid, f_WT=1%2C2%2C3 }

    #         if parameters['lessthanTenApplicants']:
    #             lessthanTenApplicants_url = "&f_EA=true"

    #         level = 1
    #         experience_level = parameters.get('experienceLevel', [])
    #         experience_url = "f_E="
    #         for key in experience_level.keys():
    #             if experience_level[key]:
    #                 experience_url += "%2C" + str(level)
    #             level += 1

    #         distance_url = "?distance=" + str(parameters['distance'])

    #         job_types_url = "f_JT="
    #         job_types = parameters.get('jobTypes', [])
    #         for key in job_types:
    #             if job_types[key]:
    #                 job_types_url += "%2C" + key[0].upper()

    #         # Apply the 24-hour filter by default
            
    #         # date_url = "&f_TPR=r86400"
    #         date_url = ""
    #         easy_apply_url = "&f_AL=false"

    #         # Combine all parts of the URL
    #         extra_search_terms = [distance_url, remote_url, lessthanTenApplicants_url, job_types_url, experience_url]
    #         extra_search_terms_str = '&'.join(
    #             term for term in extra_search_terms if len(term) > 0) + easy_apply_url + date_url

    #         return extra_search_terms_str


    # def next_job_page(self, position, location, job_page):
    #     # Step 1: Perform a dummy search for "iOS Developer"
    #     dummy_url = "https://www.linkedin.com/jobs/search/?keywords=iOS%20Developer"
    #     print("🔍 Performing dummy search for 'iOS Developer' before actual search...")
    #     self.browser.get(dummy_url)

    #     # Step 2: Wait for 10 seconds before proceeding
    #     time.sleep(10)

    #     # Step 3: Perform the actual job search
    #     actual_url = f"https://www.linkedin.com/jobs/search/{self.base_search_url}&keywords={position}{location}&start={job_page * 25}"
    #     print(f"🔍 Performing actual job search for '{position}' in '{location}', Page {job_page}")
    #     self.browser.get(actual_url)
    #     time.sleep(30)

    #     self.avoid_lock()