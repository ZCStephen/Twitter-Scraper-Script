import os
import pandas as pd
from datetime import datetime, timedelta

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

def run_scraper(username, start_date, end_date, tweets_per_month=1000):
    """
    Run the scraper for each month in the range.
    """
    monthly_ranges = generate_monthly_ranges(start_date, end_date)
    for start, end in monthly_ranges:
        query = f'(from:{username}) until:{end.strftime("%Y-%m-%d")} since:{start.strftime("%Y-%m-%d")} -filter:replies'
        command = f'python3 scraper -t {tweets_per_month} --user=@chengxihan1 --password=Shuaijerryshuai2448878048 --query="{query}"'
        print(f"Running: {command}")
        os.system(command)  # Executes the command

def run_scraper_from_excel(file_path, start_date, end_date):
    """
    Read the usernames from the Excel file and run the scraper for each user.
    """
    try:
        df = pd.read_excel(file_path)  # Load the Excel file
        if 'username' not in df.columns:
            print("The Excel file must have a column named 'username'.")
            return
        usernames = df['username'].dropna().unique()  # Get unique usernames
        for username in usernames:
            print(f"Starting scraper for user: {username}")
            run_scraper(username.strip(), start_date, end_date)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")

if __name__ == "__main__":
    # Inputs from the user
    excel_file_path = input("Enter the path to the Excel file containing usernames: ").strip()
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

    # Run the scraper for each username in the Excel file
    run_scraper_from_excel(excel_file_path, start_date, end_date)
