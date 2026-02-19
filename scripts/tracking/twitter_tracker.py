"""Optional: Fetch ASR-related tweets from Twitter/X API v2.

This module is entirely optional and only activates when TWITTER_BEARER_TOKEN
is set. The Twitter API Basic tier costs $100/month for read access.
"""

import logging

from scripts.config import config

logger = logging.getLogger(__name__)


def fetch_tweets(lookback_hours: int = 24, max_results: int = 50) -> list[dict]:
    """Fetch recent ASR-related tweets.

    Returns an empty list if Twitter API is not configured.

    Args:
        lookback_hours: How far back to search.
        max_results: Maximum tweets to return.

    Returns:
        List of tweet dicts with keys: id, author, text, url, created_at.
    """
    if not config.twitter_enabled:
        logger.info("Twitter tracking disabled (no TWITTER_BEARER_TOKEN set)")
        return []

    try:
        import tweepy
    except ImportError:
        logger.warning("tweepy not installed — skipping Twitter tracking")
        return []

    from datetime import datetime, timedelta, timezone

    client = tweepy.Client(bearer_token=config.twitter_bearer_token)
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    query = (
        '"speech recognition" OR "ASR" OR "whisper model" OR "speech-to-text" '
        "-is:retweet lang:en"
    )

    try:
        response = client.search_recent_tweets(
            query=query,
            max_results=min(max_results, 100),
            start_time=since,
            tweet_fields=["created_at", "author_id", "text"],
            user_fields=["username"],
            expansions=["author_id"],
        )
    except Exception:
        logger.exception("Twitter API request failed")
        return []

    if not response.data:
        logger.info("No recent ASR tweets found")
        return []

    # Build author lookup
    users = {u.id: u.username for u in (response.includes.get("users") or [])}

    tweets = []
    for tweet in response.data:
        username = users.get(tweet.author_id, "unknown")
        tweets.append(
            {
                "id": str(tweet.id),
                "author": username,
                "text": tweet.text,
                "url": f"https://twitter.com/{username}/status/{tweet.id}",
                "created_at": (
                    tweet.created_at.strftime("%Y-%m-%d %H:%M")
                    if tweet.created_at
                    else None
                ),
            }
        )

    logger.info("Found %d recent ASR tweets", len(tweets))
    return tweets


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    results = fetch_tweets()
    print(json.dumps(results, indent=2))
