import tweepy
import datetime
import pandas as pd
import time
import re
import sys
import os  # Added for env var suggestion

# Use env var for security (fallback to hardcoded if not set)
BEARER_TOKEN = os.getenv('X_BEARER_TOKEN', 'AAAAAAAAAAAAAAAAAAAAAMyM5gEAAAAACeFeifCdo7qjqiAUjAoigrPxetU%3D2Z8SECqO67ujAuJAOnthqylC798dk9zNI4pEXbAgvGeW4iSViG')

client = tweepy.Client(bearer_token=BEARER_TOKEN)

def extract_post_id(post_link):
    match = re.search(r'/status/(\d+)', post_link)
    if match:
        return match.group(1)
    print(f"Invalid post link: {post_link}")
    return None

def get_original_post(post_id):
    try:
        response = client.get_tweet(
            id=post_id,
            expansions=['author_id'],
            tweet_fields=['text', 'created_at'],
            user_fields=['name', 'username', 'verified', 'profile_image_url']
        )
        if response.data:
            tweet = response.data
            user = response.includes.get('users', [None])[0]
            return {
                'handle': f"@{user.username}" if user else '',
                'timestamp': tweet.created_at.replace(tzinfo=None),
                'content': tweet.text,
                'link': f"https://x.com/{user.username}/status/{tweet.id}" if user else f"https://x.com/i/status/{post_id}",
                'created_at_utc': tweet.created_at  # keep aware for filtering
            }
        print(f"Original post {post_id} not found.")
        return None
    except tweepy.TweepyException as e:
        print(f"Error fetching original post {post_id}: {e}")
        return None

def extract_emojis(text):
    emoji_pattern = re.compile(
        r'['
        r'\U0001F600-\U0001F64F'
        r'\U0001F300-\U0001F5FF'
        r'\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF'
        r'\U00002702-\U000027B0'
        r'\U000024C2-\U0001F251'
        r']+',
        flags=re.UNICODE
    )
    return ', '.join(emoji_pattern.findall(text)) if text else ''

def scrape_comments(post_id, conversation_start_time):
    """
    Fetch all replies in the conversation using search_all_tweets.
    Accumulates users across all pages.
    """
    all_comments = []
    user_map = {}  # Accumulate all users here
    next_token = None

    # Format times as RFC3339 with 'Z'
    start_time_str = conversation_start_time.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Buffer end_time (45s safe)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    end_time_safe = now_utc - datetime.timedelta(seconds=45)
    end_time_str = end_time_safe.strftime('%Y-%m-%dT%H:%M:%SZ')

    query = f"conversation_id:{post_id} is:reply -is:retweet"

    print(f"Searching replies to conversation_id:{post_id}")
    print(f"Time window: {start_time_str} → {end_time_str} (end_time buffered)")

    page = 0
    while True:
        page += 1
        try:
            response = client.search_all_tweets(
                query=query,
                start_time=start_time_str,
                end_time=end_time_str,
                max_results=500,
                next_token=next_token,
                expansions=['author_id'],
                tweet_fields=['id', 'text', 'created_at', 'public_metrics', 'entities'],
                user_fields=['name', 'username', 'verified', 'profile_image_url']
            )

            if response.data:
                print(f"  Page {page} → Fetched {len(response.data)} replies (total so far: {len(all_comments) + len(response.data)})")
                all_comments.extend(response.data)

            # Accumulate users from THIS response
            if hasattr(response, 'includes') and 'users' in response.includes:
                for user in response.includes['users']:
                    user_map[user.id] = user  # Overwrite if duplicate (fine)

            next_token = response.meta.get('next_token')
            if not next_token:
                print("→ No more pages")
                break

            time.sleep(2.2)  # Conservative delay

        except tweepy.errors.BadRequest as e:
            print(f"400 Bad Request: {e}")
            print("→ Double-check query syntax, time format, or academic access level.")
            break
        except tweepy.errors.Unauthorized:
            print("401 Unauthorized → invalid/expired token or missing academic access")
            break
        except tweepy.errors.Forbidden:
            print("403 Forbidden → almost certainly no Academic Research access approved")
            break
        except tweepy.TweepyException as e:
            print(f"Other API error: {e}")
            break

    return all_comments, user_map

def process_post(post_link):
    post_id = extract_post_id(post_link)
    if not post_id:
        return

    original = get_original_post(post_id)
    if not original:
        return

    comments, user_map = scrape_comments(post_id, original['created_at_utc'])

    data = []
    for comment in comments:
        user = user_map.get(comment.author_id)
        if not user:
            continue  # Skip if user info missing

        entities = comment.entities or {}
        tags = ', '.join(t.get('tag', '') for t in entities.get('hashtags', []))
        mentions = ', '.join(m.get('username', '') for m in entities.get('mentions', []))

        data.append({
            'Original_Post_Handle': original['handle'],
            'Original_Post_Timestamp': original['timestamp'],
            'Original_Post_Content': original['content'],
            'Original_Post_Link': original['link'],
            'Comment_Name': user.name,
            'Comment_Handle': f"@{user.username}",
            'Comment_Timestamp': comment.created_at.replace(tzinfo=None),
            'Verified': user.verified,
            'Content': comment.text,
            'Comments': comment.public_metrics.get('reply_count', 0),
            'Retweets': comment.public_metrics.get('retweet_count', 0),
            'Likes': comment.public_metrics.get('like_count', 0),
            'Analytics': comment.public_metrics.get('quote_count', 0),
            'Tags': tags,
            'Mentions': mentions,
            'Emojis': extract_emojis(comment.text),
            'Profile Image': user.profile_image_url or '',
            'Tweet Link': f"https://x.com/{user.username}/status/{comment.id}",
            'Tweet ID': comment.id,
            'Source_File': f"{original['handle'].lstrip('@')}_input"
        })

    if not data:
        print(f"No comments found (or access issue) for post {post_id}")
        return

    df = pd.DataFrame(data)
    # Optional: Sort by timestamp ascending
    df = df.sort_values('Comment_Timestamp')
    output_file = f"comments_{post_id}.xlsx"
    df.to_excel(output_file, index=False)
    print(f"Saved {len(df)} comments → {output_file}")

# Main execution
if __name__ == "__main__":
    # Input Excel file with column: 'post_link'
    input_file = 'CommentTest.xlsx'  # Adjust if needed

    try:
        df_input = pd.read_excel(input_file)
    except FileNotFoundError:
        print(f"Input file '{input_file}' not found.")
        sys.exit(1)

    # Ensure required column exists
    if 'post_link' not in df_input.columns:
        print("Input file must contain column: 'post_link'")
        sys.exit(1)

    # Process each row
    for _, row in df_input.iterrows():
        post_link = row['post_link']
        process_post(post_link)