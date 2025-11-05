import os
import pandas as pd
from datetime import datetime, timedelta
from itertools import cycle
import tweepy
import csv
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

def run_api_scraper(bearer_token, target_user, start, end, tweets_per_month=1000, max_retries=3):
    """
    Run the API scraper for a single query using the specified bearer token.
    Retries up to max_retries times if authentication fails.
    Assumes elevated API access (e.g., Pro) for full-archive search.
    Saves results to a CSV file named {target_user}_{start_date}_{end_date}.csv.
    """
    client = tweepy.Client(bearer_token=bearer_token)
    output_file = f"{target_user}_{start.strftime('%Y-%m-%d')}_{end.strftime('%Y-%m-%d')}.csv"
    
    query = f"from:{target_user} -is:reply"
    
    attempts = 0
    while attempts < max_retries:
        print(f"\nAttempt {attempts + 1} for user {target_user} (Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}) using token ending in {bearer_token[-4:]}")
        
        try:
            # Removed get_me() test as it causes TypeError with bearer auth
            
            # Fetch tweets using full-archive search (requires Pro/Academic access)
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'text', 'created_at', 'author_id', 'retweet_count', 'like_count'])
                
                paginator = tweepy.Paginator(
                    client.search_all_tweets,
                    query=query,
                    start_time=start.isoformat() + 'Z',
                    end_time=end.isoformat() + 'Z',
                    tweet_fields=['id', 'text', 'created_at', 'author_id', 'public_metrics'],
                    max_results=100
                ).flatten(limit=tweets_per_month)
                
                for tweet in paginator:
                    metrics = tweet.public_metrics
                    writer.writerow([
                        tweet.id,
                        tweet.text,
                        tweet.created_at,
                        tweet.author_id,
                        metrics['retweet_count'],
                        metrics['like_count']
                    ])
            
            print(f"Data saved to {output_file}")
            break
        
        except tweepy.errors.Unauthorized as e:
            print(f"Authentication failed on attempt {attempts + 1}: {e}")
            attempts += 1
            if attempts < max_retries:
                print("Retrying with same token...")
                time.sleep(2)
            else:
                print("Max retries reached. Skipping this period.")
                break
        
        except tweepy.errors.TooManyRequests as e:
            print(f"Rate limit hit: {e}. Waiting 15 minutes...")
            time.sleep(900)  # 15 minutes
            continue  # Retry the same attempt
        
        except Exception as e:
            print(f"Error during scraping: {e}")
            attempts += 1
            if attempts < max_retries:
                print("Retrying...")
                time.sleep(2)
            else:
                print("Max retries reached. Skipping this period.")
                break

def load_tokens(file_path):
    """
    Load bearer tokens from an Excel file.
    """
    try:
        df = pd.read_excel(file_path)
        if 'bearer_token' not in df.columns:
            print("The Excel file must have a column named 'bearer_token'.")
            return None
        tokens = df['bearer_token'].dropna().tolist()
        if not tokens:
            print("No valid bearer tokens found in the file.")
            return None
        return cycle(tokens)  # Create a circular iterator of tokens
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return None

def run_scraper_from_excel(token_file, user_file, start_date, end_date):
    """
    Rotate bearer tokens for each query and run the API scraper for all users and all months.
    """
    tokens = load_tokens(token_file)
    if not tokens:
        print("No bearer tokens available for scraping. Exiting.")
        return

    try:
        user_df = pd.read_excel(user_file)
        if 'username' not in user_df.columns:
            print("The user file must have a column named 'username'.")
            return
        target_users = user_df['username'].dropna().unique()

        # Generate monthly ranges
        monthly_ranges = generate_monthly_ranges(start_date, end_date)

        # Iterate over each target user, then rotate tokens for each month
        for target_user in target_users:
            for start, end in monthly_ranges:
                # Get the next token in rotation
                bearer_token = next(tokens).strip()
                print(f"\nScraping for {target_user} (Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}) using token ending in {bearer_token[-4:]}")
                run_api_scraper(bearer_token, target_user.strip(), start, end)
    except Exception as e:
        print(f"Error reading the user file: {e}")

if __name__ == "__main__":
    # Inputs from the user
    token_file_path = input("Enter the path to the Excel file containing bearer tokens (column: bearer_token): ").strip()
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

    # Run the scraper for each target user using rotating tokens
    run_scraper_from_excel(token_file_path, user_file_path, start_date, end_date)