"""
Reddit JSON connector for the Watcher Agent.
Monitors Indian subreddits for crisis-related posts using anonymous JSON endpoints.
"""

import re
import logging
from datetime import datetime, timezone, timedelta

import httpx

from ..schemas import Signal
from ..prompts import CRISIS_KEYWORDS

logger = logging.getLogger(__name__)

# Subreddits from BLUEPRINT.md Section 7
SUBREDDITS = [
    "india", "kerala", "chennai", "bangalore", "mumbai",
    "kochi", "IndiaSpeaks", "KeralaNews",
]

# Pre-compile crisis keyword pattern
_crisis_pattern = re.compile(
    '|'.join(re.escape(kw) for kw in CRISIS_KEYWORDS),
    re.IGNORECASE,
)

# User-Agent required for Reddit JSON endpoints
HEADERS = {
    "User-Agent": "Prahari-NGO/1.0 (crisis monitoring research; contact: solutionchallengesupport@hack2skill.com)",
}


async def fetch_reddit_signals() -> list[Signal]:
    """
    Fetch recent posts from Indian subreddits.
    Filters: posts < 2 hours old, matching crisis keywords, score > 3.
    """
    signals = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for subreddit in SUBREDDITS:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=50"
                response = await client.get(url, headers=HEADERS)
                
                if response.status_code == 429:
                    logger.warning(f"Reddit rate limited on r/{subreddit}")
                    continue
                
                if response.status_code != 200:
                    logger.warning(f"Reddit fetch failed for r/{subreddit}: {response.status_code}")
                    continue
                
                data = response.json()
                sub_signals = _parse_reddit(data, subreddit, cutoff)
                signals.extend(sub_signals)
                
            except Exception as e:
                logger.error(f"Reddit fetch error for r/{subreddit}: {e}")
    
    logger.info(f"Reddit check complete: {len(signals)} crisis posts from {len(SUBREDDITS)} subreddits")
    return signals


def _parse_reddit(data: dict, subreddit: str, cutoff: datetime) -> list[Signal]:
    """Parse Reddit JSON response and filter for crisis-relevant posts."""
    signals = []
    
    posts = data.get("data", {}).get("children", [])
    
    for post_wrapper in posts:
        post = post_wrapper.get("data", {})
        
        # Filter by score
        score = post.get("score", 0)
        if score < 3:
            continue
        
        # Filter by age
        created_utc = post.get("created_utc", 0)
        post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        if post_time < cutoff:
            continue
        
        # Combine title + selftext for keyword matching
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        full_text = f"{title} {selftext}"
        
        # Check for crisis keywords
        if not _crisis_pattern.search(full_text):
            continue
        
        # Determine crisis type
        crisis_type = _infer_crisis_type(full_text)
        
        # Build permalink
        permalink = post.get("permalink", "")
        url = f"https://reddit.com{permalink}" if permalink else None
        
        signals.append(Signal(
            source_type="reddit",
            source_name=f"r/{subreddit}",
            timestamp=post_time,
            content=f"r/{subreddit}: {title}. {selftext[:200]}",
            url=url,
            location_hint=_extract_location(full_text, subreddit),
            crisis_type_hint=crisis_type,
            raw_data={
                "subreddit": subreddit,
                "title": title,
                "body": selftext[:500],
                "score": score,
                "num_comments": post.get("num_comments", 0),
                "author": post.get("author", ""),
            },
        ))
    
    return signals


def _infer_crisis_type(text: str) -> str:
    """Infer crisis type from text content."""
    text_lower = text.lower()
    
    if any(kw in text_lower for kw in ["flood", "flooding", "waterlogging", "heavy rain", "cloudburst"]):
        return "flood"
    elif any(kw in text_lower for kw in ["fire", "blaze", "explosion"]):
        return "fire"
    elif any(kw in text_lower for kw in ["earthquake", "tremor"]):
        return "earthquake"
    elif any(kw in text_lower for kw in ["cyclone", "storm surge"]):
        return "cyclone"
    elif any(kw in text_lower for kw in ["landslide"]):
        return "landslide"
    elif any(kw in text_lower for kw in ["stampede", "collapse"]):
        return "stampede"
    return "other"


def _extract_location(text: str, subreddit: str) -> str:
    """Extract location hint from text or subreddit name."""
    # Subreddit → state mapping
    sub_locations = {
        "kerala": "Kerala",
        "chennai": "Chennai, Tamil Nadu",
        "bangalore": "Bengaluru, Karnataka",
        "mumbai": "Mumbai, Maharashtra",
        "kochi": "Kochi, Kerala",
        "KeralaNews": "Kerala",
    }
    
    return sub_locations.get(subreddit, "India")
