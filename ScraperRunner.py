import os
import pandas as pd
from datetime import datetime, timedelta
from itertools import cycle
import time

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

def run_scraper_with_retry(username, password, target_user, start, end, tweets_per_month=1000, max_retries=3):
    """
    Run the scraper for a single query using the specified account with retry logic.
    """
    query = f'(from:{target_user}) until:{end.strftime("%Y-%m-%d")} since:{start.strftime("%Y-%m-%d")} -filter:replies'
    command = f'python3 scraper -t {tweets_per_month} --user={username} --password={password} --query="{query}"'

    for attempt in range(max_retries):
        try:
            print(f"Running (Attempt {attempt + 1}/{max_retries}): {command}")
            result = os.system(command)  # Executes the command
            if result == 0:  # Success
                print(f"Scraping succeeded for {target_user} (Period: {start} to {end})")
                return
            else:
                print(f"Scraping failed (Attempt {attempt + 1}/{max_retries}) for {target_user}. Retrying...")
        except Exception as e:
            print(f"Error during scraping: {e}")
        time.sleep(5)  # Wait before retrying
    print(f"Failed to scrape {target_user} (Period: {start} to {end}) after {max_retries} attempts.")

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

def run_scraper_from_excel(account_file, user_file, start_date, end_date):
    """
    Rotate accounts for each query and run the scraper for all users and all months.
    """
    accounts = load_accounts(account_file)
    if not accounts:
        print("No accounts available for scraping. Exiting.")
        return
    
    try:
        user_df = pd.read_excel(user_file)
        if 'username' not in user_df.columns:
            print("The user file must have a column named 'username'.")
            return
        target_users = user_df['username'].dropna().unique()

        # Generate monthly ranges
        monthly_ranges = generate_monthly_ranges(start_date, end_date)

        # Iterate over each target user, then rotate accounts for each month
        for target_user in target_users:
            for start, end in monthly_ranges:
                # Get the next account in rotation
                account_username, account_password = next(accounts)
                print(f"Scraping for {target_user} (Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}) using account: {account_username}")
                run_scraper_with_retry(account_username, account_password, target_user.strip(), start, end)
    except Exception as e:
        print(f"Error reading the user file: {e}")

if __name__ == "__main__":
    # Inputs from the user
    account_file_path = input("Enter the path to the Excel file containing accounts (username and password): ").strip()
    user_file_path = input("Enter the path to the Excel file containing target usernames: ").strip()
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

    # Run the scraper for each target user using rotating accounts
    run_scraper_from_excel(account_file_path, user_file_path, start_date, end_date)

