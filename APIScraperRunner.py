import tweepy
import datetime
import pandas as pd
import time
import re

# ────────────────────────────────────────────────
#  CONFIG
# ────────────────────────────────────────────────

BEARER_TOKEN = 'AAAAAAAAAAAAAAAAAAAAAMyM5gEAAAAAqPZHu0AoUvzKNEpJ7w%2BPkek0R0A%3DZj8hl1ui3BTvSikPsjQZhgGfib9LMLw61OvXL4dNRk4CTBaPd3'          # ← replace

# Initialize client (Pro tier – read-only is fine)
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# ────────────────────────────────────────────────
#  HELPERS
# ────────────────────────────────────────────────

def get_user_info(username):
    """Fetch basic user metadata once"""
    try:
        user = client.get_user(
            username=username,
            user_fields=['id', 'name', 'username', 'verified', 'profile_image_url']
        )
        if user.data:
            return {
                'id': user.data.id,
                'name': user.data.name,
                'username': user.data.username,
                'verified': user.data.verified,
                'profile_image_url': user.data.profile_image_url
            }
        return None
    except Exception as e:
        print(f"Error fetching user info for @{username}: {e}")
        return None


def extract_emojis(text):
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0" u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    emojis = emoji_pattern.findall(text)
    return ', '.join(emojis) if emojis else ''


def scrape_user_original_posts(username, start_date, end_date):
    """
    Uses FULL-ARCHIVE search_all_tweets → requires Academic Research access!
    Gets original posts (no retweets, no replies) from any date range.
    """
    all_tweets = []
    next_token = None

    start_time = start_date.isoformat() + 'Z'
    end_time   = end_date.isoformat()   + 'Z'

    query = f"from:{username} -is:retweet -is:reply"

    print(f"Full-archive query: {query}")
    print(f"Time range: {start_time} → {end_time}  (Academic access required)")

    page = 0
    while True:
        page += 1
        try:
            response = client.search_all_tweets(
                query=query,
                start_time=start_time,
                end_time=end_time,
                max_results=500,               # ↑ higher than recent search (up to 500 allowed)
                next_token=next_token,
                tweet_fields=[
                    'id', 'text', 'created_at', 'author_id',
                    'public_metrics', 'entities'
                ]
            )

            if response.data:
                all_tweets.extend(response.data)
                print(f"Page {page} → Fetched {len(response.data)} tweets (total: {len(all_tweets)})")

            next_token = response.meta.get('next_token')
            if not next_token:
                print("→ Reached end of results")
                break

            time.sleep(1.5)  # gentle delay – full-archive has 300 req / 15 min limit

        except tweepy.TooManyRequests:
            print("Rate limit (300 req/15min) → sleeping 15 minutes...")
            time.sleep(900)
        except tweepy.errors.Forbidden:
            print("403 Forbidden → most likely: no Academic Research access on this app/project")
            break
        except tweepy.Unauthorized:
            print("401 Unauthorized → invalid/revoked token")
            break
        except Exception as e:
            print(f"Full-archive search error: {e}")
            break

    return all_tweets


def process_user(username, start_date_str, end_date_str):
    try:
        start = pd.to_datetime(start_date_str).to_pydatetime()
        end   = pd.to_datetime(end_date_str).to_pydatetime()
    except Exception as e:
        print(f"Date parse error for {username}: {e}")
        return

    user = get_user_info(username)
    if not user:
        print(f"Cannot find user @{username}")
        return

    tweets = scrape_user_original_posts(username, start, end)

    if not tweets:
        print(f"No original posts found for @{username} in selected period (or access issue).")
        return

    data = []
    for t in tweets:
        created_naive = t.created_at.replace(tzinfo=None)

        entities = t.entities or {}
        hashtags  = ', '.join(h.get('tag', '')   for h in entities.get('hashtags',  []))
        mentions  = ', '.join(m.get('username','') for m in entities.get('mentions', []))

        row = {
            'Name':         user['name'],
            'Handle':       f"@{user['username']}",
            'Timestamp':    created_naive,
            'Verified':     user['verified'],
            'Content':      t.text,
            'Comments':     t.public_metrics.get('reply_count', 0),
            'Retweets':     t.public_metrics.get('retweet_count', 0),
            'Likes':        t.public_metrics.get('like_count', 0),
            'Analytics':    t.public_metrics.get('quote_count', 0),   # proxy for views/engagement
            'Tags':         hashtags,
            'Mentions':     mentions,
            'Emojis':       extract_emojis(t.text),
            'Profile Image':user['profile_image_url'],
            'Tweet Link':   f"https://x.com/{user['username']}/status/{t.id}",
            'Tweet ID':     t.id,
            'Source_File':  f"{username}_input"
        }
        data.append(row)

    df = pd.DataFrame(data)
    clean = username.lstrip('@')
    filename = f"{clean}_tweets.xlsx"
    df.to_excel(filename, index=False)

    print(f"\nSaved {len(df)} original posts → {filename}\n")


# ────────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────────

if __name__ == "__main__":
    input_file = 'Sample_Input (1).xlsx'

    try:
        df_input = pd.read_excel(input_file)
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        exit(1)

    required = {'username', 'TimeStart', 'TimeEnd'}
    if not required.issubset(df_input.columns):
        print(f"Missing columns. Need: {required}")
        exit(1)

    for _, row in df_input.iterrows():
        u = str(row['username']).strip().lstrip('@')
        start = row['TimeStart']
        end   = row['TimeEnd']
        print(f"\nProcessing @{u}  ({start} → {end})")
        process_user(u, start, end)