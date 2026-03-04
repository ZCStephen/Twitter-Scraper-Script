import tweepy
import datetime
import pandas as pd
import time
import re

# ────────────────────────────────────────────────
#  CONFIG – Assumes Academic Research access for full-archive search
# ────────────────────────────────────────────────

BEARER_TOKEN = 'AAAAAAAAAAAAAAAAAAAAAMyM5gEAAAAACeFeifCdo7qjqiAUjAoigrPxetU%3D2Z8SECqO67ujAuJAOnthqylC798dk9zNI4pEXbAgvGeW4iSViG'          # ← replace with your academic-approved token

# Initialize client
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# ────────────────────────────────────────────────
#  HELPERS
# ────────────────────────────────────────────────

def extract_emojis(text):
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0" u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    emojis = emoji_pattern.findall(text)
    return ', '.join(emojis) if emojis else ''


def get_user_map_from_includes(includes):
    """Map author_id → user details from API includes"""
    user_map = {}
    if 'users' in includes:
        for u in includes['users']:
            user_map[u.id] = {
                'name': u.name,
                'username': u.username,
                'verified': u.verified,
                'profile_image_url': u.profile_image_url
            }
    return user_map


def scrape_hashtag_original_posts(hashtag, start_date, end_date):
    """
    Uses FULL-ARCHIVE search_all_tweets → requires Academic Research access!
    Gets original posts (no retweets, no replies) with the hashtag from any date range.
    """
    all_tweets = []
    next_token = None

    start_time = start_date.isoformat() + 'Z'
    end_time   = end_date.isoformat()   + 'Z'

    # Query for hashtag (exact match) + exclusions
    query = f"#{hashtag} -is:retweet -is:reply"

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
                max_results=500,               # ↑ higher limit allowed
                next_token=next_token,
                expansions=['author_id'],      # ← to get user details
                tweet_fields=[
                    'id', 'text', 'created_at', 'author_id',
                    'public_metrics', 'entities'
                ],
                user_fields=[
                    'name', 'username', 'verified', 'profile_image_url'
                ]
            )

            if response.data:
                all_tweets.extend(response.data)
                print(f"Page {page} → Fetched {len(response.data)} tweets (total: {len(all_tweets)})")

            next_token = response.meta.get('next_token')
            if not next_token:
                print("→ Reached end of results")
                break

            time.sleep(1.5)  # rate-limit cushion (300 req/15 min)

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

    return all_tweets, response.includes if hasattr(response, 'includes') else {}


def process_hashtag(hashtag, start_date_str, end_date_str):
    try:
        start = pd.to_datetime(start_date_str).to_pydatetime()
        end   = pd.to_datetime(end_date_str).to_pydatetime()
    except Exception as e:
        print(f"Date parse error for #{hashtag}: {e}")
        return

    tweets, includes = scrape_hashtag_original_posts(hashtag, start, end)

    if not tweets:
        print(f"No original posts found for #{hashtag} in selected period (or access issue).")
        return

    user_map = get_user_map_from_includes(includes)

    data = []
    for t in tweets:
        author_id = t.author_id
        user = user_map.get(author_id, {
            'name': 'Unknown',
            'username': 'unknown',
            'verified': False,
            'profile_image_url': ''
        })  # Fallback if user not in includes

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
            'Analytics':    t.public_metrics.get('quote_count', 0),   # proxy
            'Tags':         hashtags,
            'Mentions':     mentions,
            'Emojis':       extract_emojis(t.text),
            'Profile Image':user['profile_image_url'],
            'Tweet Link':   f"https://x.com/{user['username']}/status/{t.id}",
            'Tweet ID':     t.id,
            'Source_File':  f"{hashtag}_input"
        }
        data.append(row)

    df = pd.DataFrame(data)
    filename = f"{hashtag}_posts.xlsx"
    df.to_excel(filename, index=False)

    print(f"\nSaved {len(df)} original posts → {filename}\n")


# ────────────────────────────────────────────────
#  MAIN – Input Excel with 'hashtag', 'TimeStart', 'TimeEnd'
# ────────────────────────────────────────────────

if __name__ == "__main__":
    input_file = 'hashtag.xlsx'  # ← adjust if needed

    try:
        df_input = pd.read_excel(input_file)
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        exit(1)

    required = {'hashtag', 'TimeStart', 'TimeEnd'}
    if not required.issubset(df_input.columns):
        print(f"Missing columns. Need: {required}")
        exit(1)

    for _, row in df_input.iterrows():
        h = str(row['hashtag']).strip().lstrip('#')  # remove leading '#' if present
        start = row['TimeStart']
        end   = row['TimeEnd']
        print(f"\nProcessing #{h}  ({start} → {end})")
        process_hashtag(h, start, end)