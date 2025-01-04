import os
import pandas as pd
from datetime import datetime, timedelta
from itertools import cycle

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

def check_missing_data(folder_path, username, monthly_ranges):
    """
    Check if the data for any monthly range is missing in the folder.
    Returns a list of missing ranges.
    """
    missing_ranges = []
    for start, end in monthly_ranges:
        # Expected file name format: username_YYYY-MM-DD_YYYY-MM-DD.csv
        expected_file = f"{username}_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.csv"
        expected_path = os.path.join(folder_path, expected_file)
        if not os.path.exists(expected_path):
            missing_ranges.append((start, end))
    return missing_ranges

def run_scraper(username, password, target_user, start, end, folder_path, tweets_per_month=1000):
    """
    Run the scraper for a single query using the specified account.
    Save the results in the specified folder.
    """
    query = f'(from:{target_user}) until:{end.strftime("%Y-%m-%d")} since:{start.strftime("%Y-%m-%d")} -filter:replies'
    command = f'python3 scraper -t {tweets_per_month} --user={username} --password={password} --query="{query}"'
    print(f"Running: {command}")
    result = os.system(command)
    if result == 0:
        print(f"Scraping succeeded for {target_user} (Period: {start} to {end}).")
    else:
        print(f"Scraping failed for {target_user} (Period: {start} to {end}).")

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

def check_and_rescrape(account_file, folder_file, start_date, end_date):
    """
    Check for missing data in folders and re-run the scraper for missing months.
    """
    accounts = load_accounts(account_file)
    if not accounts:
        print("No accounts available for scraping. Exiting.")
        return

    try:
        folder_df = pd.read_excel(folder_file)
        if not {'folder_path', 'username'}.issubset(folder_df.columns):
            print("The folder file must have columns named 'folder_path' and 'username'.")
            return

        # Validate each folder and scrape missing data
        for _, row in folder_df.iterrows():
            folder_path = row['folder_path']
            username = row['username']

            # Check if folder exists
            if not os.path.exists(folder_path):
                print(f"Folder does not exist: {folder_path}")
                continue

            # Generate monthly ranges
            monthly_ranges = generate_monthly_ranges(start_date, end_date)

            # Check for missing data
            print(f"Checking for missing data in folder: {folder_path}")
            missing_ranges = check_missing_data(folder_path, username, monthly_ranges)

            # Scrape missing data
            if missing_ranges:
                print(f"Missing data found for {username}: {len(missing_ranges)} months.")
                for start, end in missing_ranges:
                    account_username, account_password = next(accounts)
                    print(f"Scraping missing data for {username} (Period: {start} to {end}) using account: {account_username}")
                    run_scraper(account_username, account_password, username, start, end, folder_path)
            else:
                print(f"All data is present for {username}.")
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

    # Check and re-scrape missing data
    check_and_rescrape(account_file_path, folder_file_path, start_date, end_date)
