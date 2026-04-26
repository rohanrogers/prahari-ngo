"""
News RSS feed parser for the Watcher Agent.
Monitors 5 Indian news sources for crisis-related keywords.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from xml.etree import ElementTree

import httpx

from ..schemas import Signal
from ..prompts import CRISIS_KEYWORDS

logger = logging.getLogger(__name__)

# RSS feeds from BLUEPRINT.md Section 7
RSS_FEEDS = [
    ("ndtv", "NDTV India", "https://www.ndtv.com/india-news/rss"),
    ("toi", "Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
    ("hindu", "The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
    ("mathrubhumi", "Mathrubhumi", "https://www.mathrubhumi.com/rss"),
    ("manorama", "Manorama Online", "https://english.manoramaonline.com/rss/news.rss"),
]

# Pre-compile crisis keyword pattern
_crisis_pattern = re.compile(
    '|'.join(re.escape(kw) for kw in CRISIS_KEYWORDS),
    re.IGNORECASE,
)

# Indian state/city names for location detection
INDIAN_LOCATIONS = [
    "Kerala", "Tamil Nadu", "Karnataka", "Maharashtra", "Delhi",
    "West Bengal", "Telangana", "Gujarat", "Assam", "Rajasthan",
    "Uttar Pradesh", "Madhya Pradesh", "Odisha", "Bihar", "Andhra Pradesh",
    "Thiruvananthapuram", "Kochi", "Alappuzha", "Chennai", "Bengaluru",
    "Mumbai", "Kolkata", "Hyderabad", "Pune", "Ahmedabad", "Guwahati",
    "Ernakulam", "Thrissur", "Kottayam", "Pathanamthitta", "Idukki",
    "Wayanad", "Kozhikode", "Malappuram", "Palakkad", "Kannur",
]

_location_pattern = re.compile(
    '|'.join(re.escape(loc) for loc in INDIAN_LOCATIONS),
    re.IGNORECASE,
)


async def fetch_rss_signals() -> list[Signal]:
    """
    Fetch and filter RSS feeds for crisis-related articles.
    Only returns articles from the last 2 hours that match crisis keywords.
    """
    signals = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    
    async with httpx.AsyncClient(timeout=15) as client:
        for feed_id, feed_name, feed_url in RSS_FEEDS:
            try:
                response = await client.get(feed_url, headers={
                    "User-Agent": "Prahari-NGO/1.0 (crisis-monitoring research project)",
                })
                
                if response.status_code != 200:
                    logger.warning(f"RSS fetch failed for {feed_name}: {response.status_code}")
                    continue
                
                feed_signals = _parse_rss(response.text, feed_id, feed_name, feed_url, cutoff)
                signals.extend(feed_signals)
                
            except Exception as e:
                logger.error(f"RSS fetch error for {feed_name}: {e}")
    
    logger.info(f"RSS check complete: {len(signals)} crisis articles from {len(RSS_FEEDS)} feeds")
    return signals


def _parse_rss(
    xml_text: str,
    feed_id: str,
    feed_name: str,
    feed_url: str,
    cutoff: datetime,
) -> list[Signal]:
    """Parse RSS XML and filter for crisis-relevant articles."""
    signals = []
    
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as e:
        logger.error(f"RSS parse error for {feed_name}: {e}")
        return signals
    
    # Handle both RSS 2.0 and Atom formats
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    
    for item in items[:50]:  # Limit to 50 most recent
        title = _get_text(item, "title") or _get_text(item, "{http://www.w3.org/2005/Atom}title") or ""
        description = _get_text(item, "description") or _get_text(item, "{http://www.w3.org/2005/Atom}summary") or ""
        link = _get_text(item, "link") or ""
        pub_date = _get_text(item, "pubDate") or _get_text(item, "{http://www.w3.org/2005/Atom}published") or ""
        
        # Combine title + description for keyword matching
        full_text = f"{title} {description}"
        
        # Check for crisis keywords
        if not _crisis_pattern.search(full_text):
            continue
        
        # Detect location
        location_match = _location_pattern.search(full_text)
        location_hint = location_match.group(0) if location_match else None
        
        # Infer crisis type
        crisis_type = _infer_crisis_type(full_text)
        
        # Parse publication date (best effort)
        timestamp = _parse_date(pub_date) or datetime.now(timezone.utc)
        
        signals.append(Signal(
            source_type="news_rss",
            source_name=feed_id,
            timestamp=timestamp,
            content=f"{title}. {description[:200]}",
            url=link,
            location_hint=location_hint,
            crisis_type_hint=crisis_type,
            raw_data={
                "title": title,
                "description": description[:500],
                "feed": feed_name,
            },
        ))
    
    return signals


def _get_text(element, tag: str) -> Optional[str]:
    """Safely get text content from an XML element."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


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
    else:
        return "other"


def _parse_date(date_str: str) -> Optional[datetime]:
    """Best-effort date parsing for RSS dates."""
    if not date_str:
        return None
    
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    
    return None
