import os
import pandas as pd
import subprocess

def run_scraper_for_keywords(account_file, user_file, start_date, end_date):
    """
    Run scraper for each user and their associated keywords from the input files within the specified date range.
    """
    # Load accounts
    try:
        accounts_df = pd.read_excel(account_file)
        if not {'username', 'password'}.issubset(accounts_df.columns):
            print("The accounts file must have columns named 'username' and 'password'.")
            return

        accounts = list(zip(accounts_df['username'].dropna(), accounts_df['password'].dropna()))
        if not accounts:
            print("No valid accounts found in the file.")
            return
    except Exception as e:
        print(f"Error reading the accounts file: {e}")
        return

    # Load target users and keywords
    try:
        user_df = pd.read_excel(user_file)
        if 'user_name' not in user_df.columns:
            print("The user file must have a column named 'user_name'.")
            return

        # Filter out rows where 'user_name' is missing
        user_df = user_df.dropna(subset=['user_name'])
    except Exception as e:
        print(f"Error reading the user file: {e}")
        return

    # Iterate through accounts and users
    account_index = 0
    for _, row in user_df.iterrows():
        target_user = row['user_name']
        keywords = [str(row[f'keyword{i}']).strip() for i in range(1, 9) if f'keyword{i}' in row and pd.notna(row[f'keyword{i}'])]

        # Run a scraper query for each keyword
        for keyword in keywords:
            # Get the current account credentials
            username, password = accounts[account_index % len(accounts)]
            account_index += 1

            # Construct the query and command
            query = f'{keyword}(from:{target_user}) until:{end_date} since:{start_date} -filter:replies'
            command = f'python scraper --user={username} --password={password} --query="{query}" -t 1000'

            print(f"Running query for keyword '{keyword}' and user '{target_user}' using account '{username}'")
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print("Query successful:")
                    print(result.stdout)
                else:
                    print("Query failed:")
                    print(result.stderr)
            except Exception as e:
                print(f"Error executing scraper command: {e}")

if __name__ == "__main__":
    # Input file paths
    account_file_path = input("Enter the path to the Excel file containing accounts (username and password): ").strip()
    user_file_path = input("Enter the path to the Excel file containing target users and keywords: ").strip()
    start_date = input("Enter the start date (YYYY-MM-DD): ").strip()
    end_date = input("Enter the end date (YYYY-MM-DD): ").strip()

    # Run the scraper
    run_scraper_for_keywords(account_file_path, user_file_path, start_date, end_date)
