import os
import pandas as pd
from datetime import datetime, timedelta
from itertools import cycle
import time
import shutil  # To move files
import subprocess
import glob

def validate_date(date_str):
    """
    Validates the date format and checks if the date is valid.
    Returns a datetime object if valid, or None if invalid.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date format or invalid day: {date_str}. Please use a valid date in YYYY-MM-DD format.")
        return None

def generate_monthly_ranges(start_date, end_date):
    """
    Generate a list of start and end dates for each month in the range.
    """
    current_date = start_date
    ranges = []
    while current_date <= end_date:
        month_end = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        month_end = min(month_end, end_date)
        ranges.append((current_date, month_end))
        current_date = month_end + timedelta(days=1)
    return ranges

def parse_file_dates(file_name):
    """
    Extract start and end dates from the file name.
    """
    try:
        parts = file_name.split('_')
        start_date = validate_date(parts[1])
        end_date = validate_date(parts[2])
        return start_date, end_date
    except Exception as e:
        print(f"Error parsing dates from file name '{file_name}': {e}")
        return None, None

def get_existing_date_ranges(folder_path):
    """
    Get a list of existing start and end date ranges from the folder.
    """
    existing_ranges = []
    try:
        for file_name in os.listdir(folder_path):
            if file_name.endswith('.csv'):
                start_date, end_date = parse_file_dates(file_name)
                if start_date and end_date:
                    existing_ranges.append((start_date, end_date))
    except Exception as e:
        print(f"Error reading folder '{folder_path}': {e}")
    return existing_ranges

def run_scraper_with_retry(username, password, target_user, start, end, folder_path, tweets_per_month=1000, max_retries=3):
    """
    Run the scraper for a single query using the specified account.
    Retries up to max_retries times if login fails or scraping fails.
    Uses command output to determine success.
    """
    query = f'(from:{target_user}) until:{end.strftime("%Y-%m-%d")} since:{start.strftime("%Y-%m-%d")} -filter:replies'
    command = f'python3 scraper -t {tweets_per_month} --user="{username}" --password="{password}" --query="{query}"'

    attempts = 0
    while attempts < max_retries:
        print(f"\nAttempt {attempts + 1} for user {target_user} using account {username}")
        print(f"Running: {command}")
        
        # Run the scraper command and capture output
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = (result.stdout + result.stderr).lower()
        
        # Check if the scraper successfully ran and saved the CSV
        if "scraper ran successfully and csv was saved." in output:
            print("Scraper succeeded. No further retries needed.")
            return  # Exit after successful scraping
        else:
            print(f"Scraper failed on attempt {attempts + 1}. Output:\n{output}")
        
        # Retry logic
        if attempts < max_retries - 1:
            print("Retrying...")
            attempts += 1
            time.sleep(5)  # Optional: wait before retrying
        else:
            print("Max retries reached. Scraper failed to run successfully.")
            break
        
def load_accounts(file_path):
    """
    Load Twitter accounts from an Excel file.
    """
    try:
        df = pd.read_excel(file_path)
        if not {'username', 'password'}.issubset(df.columns):
            print("The Excel file must have columns named 'username' and 'password'.")
            return None
        accounts = list(zip(df['username'].dropna(), df['password'].dropna()))
        if not accounts:
            print("No valid accounts found in the file.")
            return None
        return cycle(accounts)  # Create a circular iterator of accounts
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return None

def find_missing_months(existing_ranges, monthly_ranges):
    """
    Identify the missing monthly ranges that are not present in the existing ranges.
    """
    missing_ranges = []
    for start, end in monthly_ranges:
        if not any(start == existing_start and end == existing_end for existing_start, existing_end in existing_ranges):
            missing_ranges.append((start, end))
    return missing_ranges

def check_and_scrape_missing_data(account_file, folder_excel, start_date, end_date):
    """
    Check for missing monthly data in folders and scrape the missing data.
    """
    accounts = load_accounts(account_file)
    if not accounts:
        print("No accounts available for scraping. Exiting.")
        return
    
    try:
        folder_df = pd.read_excel(folder_excel)
        if 'folder_path' not in folder_df.columns or 'username' not in folder_df.columns:
            print("The folder file must have columns named 'folder_path' and 'username'.")
            return

        # Iterate through each folder and target user
        for _, row in folder_df.iterrows():
            folder_path = row['folder_path']
            target_user = row['username']

            if not os.path.exists(folder_path):
                print(f"Folder '{folder_path}' does not exist. Skipping...")
                continue

            # Get existing date ranges and generate expected ranges
            existing_ranges = get_existing_date_ranges(folder_path)
            monthly_ranges = generate_monthly_ranges(start_date, end_date)
            missing_ranges = find_missing_months(existing_ranges, monthly_ranges)

            if not missing_ranges:
                print(f"No missing data for user '{target_user}' in folder '{folder_path}'.")
                continue

            print(f"Missing data found for user '{target_user}': {missing_ranges}")

            # Scrape missing ranges using rotating accounts
            for start, end in missing_ranges:
                account_username, account_password = next(accounts)
                run_scraper_with_retry(account_username, account_password, target_user, start, end, folder_path)
    except Exception as e:
        print(f"Error processing the folder file: {e}")

if __name__ == "__main__":
    # Inputs from the user
    account_file_path = input("Enter the path to the Excel file containing accounts (username and password): ").strip()
    folder_file_path = input("Enter the path to the Excel file containing folder paths and usernames: ").strip()
    start_date_input = input("Enter the start date (YYYY-MM-DD): ").strip()
    end_date_input = input("Enter the end date (YYYY-MM-DD): ").strip()

    # Validate dates
    start_date = validate_date(start_date_input)
    end_date = validate_date(end_date_input)

    if not start_date or not end_date:
        print("Invalid input dates. Please try again.")
        exit()

    if start_date > end_date:
        print("Start date cannot be after the end date. Please try again.")
        exit()

    # Check for missing data and scrape it
    check_and_scrape_missing_data(account_file_path, folder_file_path, start_date, end_date)
