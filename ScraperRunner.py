import os
from datetime import datetime, timedelta

def generate_monthly_ranges(start_date, end_date):
    """
    Generate a list of start and end dates for each month in the range.
    """
    current_date = start_date
    ranges = []
    while current_date <= end_date:
        # Calculate the last day of the current month
        month_end = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        month_end = min(month_end, end_date)  # Ensure month_end does not exceed end_date
        ranges.append((current_date, month_end))
        # Move to the first day of the next month
        current_date = month_end + timedelta(days=1)
    return ranges

def run_scraper(username, start_date, end_date, tweets_per_month=1000):
    """
    Run the scraper for each month in the range.
    """
    monthly_ranges = generate_monthly_ranges(start_date, end_date)
    for start, end in monthly_ranges:
        query = f'(from:{username}) until:{end.strftime("%Y-%m-%d")} since:{start.strftime("%Y-%m-%d")}'
        command = f'python3 scraper -t {tweets_per_month} --user=@chengxihan1 --password=Shuaijerryshuai2448878048 --query="{query}"'
        print(f"Running: {command}")
        os.system(command)  # Executes the command

if __name__ == "__main__":
    # Inputs from the user
    twitter_username = input("Enter the Twitter username (without @): ").strip()
    start_date_input = input("Enter the start date (YYYY-MM-DD): ").strip()
    end_date_input = input("Enter the end date (YYYY-MM-DD): ").strip()

    # Convert inputs to datetime objects
    try:
        start_date = datetime.strptime(start_date_input, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_input, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD.")
        exit()

    if start_date > end_date:
        print("Start date cannot be after the end date. Please try again.")
        exit()

    # Run the scraper
    run_scraper(twitter_username, start_date, end_date)
