"""
RSS News Aggregator
Live-News von vertrauenswürdigen Quellen via RSS Feeds

Quellen:
- BBC News
- The Guardian
- NPR
- Deutsche Welle
- NYTimes
- Reuters

Alle RSS-Feeds sind KOSTENLOS und brauchen keinen API-Key!
"""

import asyncio
import logging
import re
import os
import certifi
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import httpx
from html import unescape

# Check if SSL verification should be disabled (for dev environments with proxies)
DISABLE_SSL = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"
SSL_VERIFY = False if DISABLE_SSL else certifi.where()

logger = logging.getLogger(__name__)


@dataclass
class RSSFeed:
    """RSS Feed Configuration"""
    name: str
    url: str
    language: str
    category: str
    credibility: float


# Vertrauenswürdige News-Quellen mit RSS-Feeds
NEWS_FEEDS: Dict[str, List[RSSFeed]] = {
    # International (English)
    "international": [
        RSSFeed("BBC News", "http://feeds.bbci.co.uk/news/rss.xml", "en", "general", 0.92),
        RSSFeed("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml", "en", "world", 0.92),
        RSSFeed("The Guardian", "https://www.theguardian.com/world/rss", "en", "world", 0.88),
        RSSFeed("The Guardian - Europe", "https://www.theguardian.com/world/europe-news/rss", "en", "europe", 0.88),
        RSSFeed("NPR News", "https://feeds.npr.org/1001/rss.xml", "en", "general", 0.90),
        RSSFeed("NPR World", "https://feeds.npr.org/1004/rss.xml", "en", "world", 0.90),
        RSSFeed(
            "Reuters World",
            "https://www.reutersagency.com/feed/?taxonomy=best-regions&post_type=best",
            "en",
            "world",
            0.94),
    ],

    # German
    "german": [
        RSSFeed("Deutsche Welle", "https://rss.dw.com/xml/rss-de-all", "de", "general", 0.90),
        RSSFeed("DW Politik", "https://rss.dw.com/xml/rss-de-pol", "de", "politics", 0.90),
        RSSFeed("DW Wissen", "https://rss.dw.com/xml/rss-de-wissenschaft", "de", "science", 0.90),
        RSSFeed("Tagesschau", "https://www.tagesschau.de/xml/rss2/", "de", "general", 0.93),
        RSSFeed("SPIEGEL", "https://www.spiegel.de/schlagzeilen/index.rss", "de", "general", 0.85),
        RSSFeed("ZEIT Online", "https://newsfeed.zeit.de/index", "de", "general", 0.87),
    ],

    # Topic-specific (English)
    "science": [
        RSSFeed("BBC Science", "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "en", "science", 0.92),
        RSSFeed("Guardian Science", "https://www.theguardian.com/science/rss", "en", "science", 0.88),
        RSSFeed("NPR Science", "https://feeds.npr.org/1007/rss.xml", "en", "science", 0.90),
    ],

    "health": [
        RSSFeed("BBC Health", "http://feeds.bbci.co.uk/news/health/rss.xml", "en", "health", 0.92),
        RSSFeed("Guardian Health", "https://www.theguardian.com/society/health/rss", "en", "health", 0.88),
        RSSFeed("NPR Health", "https://feeds.npr.org/1128/rss.xml", "en", "health", 0.90),
    ],

    "technology": [
        RSSFeed("BBC Technology", "http://feeds.bbci.co.uk/news/technology/rss.xml", "en", "tech", 0.92),
        RSSFeed("Guardian Tech", "https://www.theguardian.com/technology/rss", "en", "tech", 0.88),
        RSSFeed("NPR Technology", "https://feeds.npr.org/1019/rss.xml", "en", "tech", 0.90),
    ],

    "politics": [
        RSSFeed("Guardian Politics", "https://www.theguardian.com/politics/rss", "en", "politics", 0.88),
        RSSFeed("NPR Politics", "https://feeds.npr.org/1014/rss.xml", "en", "politics", 0.90),
        RSSFeed("BBC Politics", "http://feeds.bbci.co.uk/news/politics/rss.xml", "en", "politics", 0.92),
    ]
}


class RSSNewsAggregator:
    """RSS News Aggregator für Live-News"""

    def __init__(self):
        self.timeout = 10.0
        self.cache: Dict[str, Dict] = {}
        self.cache_duration = timedelta(minutes=15)

    async def search_news(self, query: str, language: str = "en",
                          max_results: int = 5, category: str = "all") -> List[Dict[str, Any]]:
        """
        Suche nach relevanten News-Artikeln

        Args:
            query: Suchbegriff
            language: "en" oder "de"
            max_results: Maximale Anzahl Ergebnisse
            category: "all", "science", "health", "technology", "politics"
        """
        all_articles = []

        # Wähle Feeds basierend auf Sprache und Kategorie
        feeds_to_search = []

        if language == "de":
            feeds_to_search.extend(NEWS_FEEDS.get("german", []))
        else:
            feeds_to_search.extend(NEWS_FEEDS.get("international", []))

        # Füge kategorie-spezifische Feeds hinzu
        if category != "all" and category in NEWS_FEEDS:
            feeds_to_search.extend(NEWS_FEEDS.get(category, []))

        # Auto-detect category from query
        query_lower = query.lower()
        if any(kw in query_lower for kw in ["vaccine", "impfung", "covid", "health", "gesundheit", "disease"]):
            feeds_to_search.extend(NEWS_FEEDS.get("health", []))
        elif any(kw in query_lower for kw in ["climate", "klima", "study", "research", "scientist"]):
            feeds_to_search.extend(NEWS_FEEDS.get("science", []))
        elif any(kw in query_lower for kw in ["election", "wahl", "government", "regierung", "politik"]):
            feeds_to_search.extend(NEWS_FEEDS.get("politics", []))
        elif any(kw in query_lower for kw in ["ai", "tech", "google", "facebook", "meta", "apple"]):
            feeds_to_search.extend(NEWS_FEEDS.get("technology", []))

        # Remove duplicates
        seen_urls = set()
        unique_feeds = []
        for feed in feeds_to_search:
            if feed.url not in seen_urls:
                seen_urls.add(feed.url)
                unique_feeds.append(feed)

        # Fetch feeds in parallel
        tasks = [self._fetch_and_search_feed(feed, query) for feed in unique_feeds[:10]]  # Max 10 feeds
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        # Sort by relevance (match score) and date
        all_articles.sort(key=lambda x: (x.get("relevance_score", 0), x.get("pub_date", "")), reverse=True)

        # Remove duplicates by title similarity
        unique_articles = self._deduplicate_articles(all_articles)

        logger.info(f"📰 RSS: Found {len(unique_articles)} relevant articles for '{query[:30]}...'")
        return unique_articles[:max_results]

    async def _fetch_and_search_feed(self, feed: RSSFeed, query: str) -> List[Dict[str, Any]]:
        """Fetch RSS feed and search for relevant articles"""
        try:
            # Check cache
            cache_key = feed.url
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                if datetime.now() - cached["timestamp"] < self.cache_duration:
                    return self._search_articles(cached["articles"], query, feed)

            # Fetch fresh feed with SSL configuration
            async with httpx.AsyncClient(timeout=self.timeout, verify=SSL_VERIFY) as client:
                response = await client.get(feed.url, follow_redirects=True)

                if response.status_code != 200:
                    return []

                articles = self._parse_rss(response.text, feed)

                # Cache results
                self.cache[cache_key] = {
                    "articles": articles,
                    "timestamp": datetime.now()
                }

                return self._search_articles(articles, query, feed)

        except Exception as e:
            logger.warning(f"RSS fetch failed for {feed.name}: {e}")
            return []

    def _parse_rss(self, xml_content: str, feed: RSSFeed) -> List[Dict[str, Any]]:
        """Parse RSS XML content"""
        articles = []

        try:
            root = ET.fromstring(xml_content)

            # Handle both RSS 2.0 and Atom formats
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items[:30]:  # Max 30 articles per feed
                article = self._parse_item(item, feed)
                if article:
                    articles.append(article)

        except ET.ParseError as e:
            logger.warning(f"RSS parse error for {feed.name}: {e}")

        return articles

    def _parse_item(self, item: ET.Element, feed: RSSFeed) -> Optional[Dict[str, Any]]:
        """Parse single RSS item"""
        try:
            # RSS 2.0 format
            title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or ""
            link = item.findtext("link") or ""
            description = item.findtext("description") or item.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            pub_date = item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}published") or ""

            # For Atom feeds, get link from href attribute
            if not link:
                link_elem = item.find("{http://www.w3.org/2005/Atom}link")
                if link_elem is not None:
                    link = link_elem.get("href", "")

            # Clean HTML from description
            description = self._clean_html(description)

            if title and link:
                return {
                    "title": unescape(title.strip()),
                    "url": link.strip(),
                    "snippet": description[:300] + "..." if len(description) > 300 else description,
                    "pub_date": pub_date,
                    "source": feed.name,
                    "language": feed.language,
                    "category": feed.category,
                    "credibility_score": feed.credibility
                }

        except Exception as e:
            logger.warning(f"Item parse error: {e}")

        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        clean = re.sub(r'<[^>]+>', '', text)
        clean = unescape(clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def _search_articles(self, articles: List[Dict], query: str, feed: RSSFeed) -> List[Dict[str, Any]]:
        """Search articles for query matches"""
        results = []
        query_terms = query.lower().split()

        for article in articles:
            title_lower = article["title"].lower()
            snippet_lower = article["snippet"].lower()
            content = title_lower + " " + snippet_lower

            # Calculate relevance score
            matches = sum(1 for term in query_terms if term in content)
            if matches > 0:
                relevance = matches / len(query_terms)
                article["relevance_score"] = relevance
                article["type"] = "news_article"
                results.append(article)

        return results

    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity"""
        unique = []
        seen_titles = set()

        for article in articles:
            # Normalize title for comparison
            title_norm = re.sub(r'[^\w\s]', '', article["title"].lower())
            title_words = set(title_norm.split()[:5])  # First 5 words

            # Check if similar title already seen
            is_duplicate = False
            for seen in seen_titles:
                overlap = len(title_words & seen) / max(len(title_words), 1)
                if overlap > 0.6:  # 60% overlap = duplicate
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_titles.add(frozenset(title_words))
                unique.append(article)

        return unique

    async def get_latest_headlines(self, language: str = "en", count: int = 10) -> List[Dict[str, Any]]:
        """Get latest headlines without search query"""
        feeds = NEWS_FEEDS.get("german" if language == "de" else "international", [])

        all_articles = []
        tasks = [self._fetch_feed_articles(feed) for feed in feeds[:5]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        # Sort by date (newest first)
        all_articles.sort(key=lambda x: x.get("pub_date", ""), reverse=True)

        return all_articles[:count]

    async def _fetch_feed_articles(self, feed: RSSFeed) -> List[Dict[str, Any]]:
        """Fetch all articles from a feed"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=SSL_VERIFY) as client:
                response = await client.get(feed.url, follow_redirects=True)
                if response.status_code == 200:
                    articles = self._parse_rss(response.text, feed)
                    for article in articles:
                        article["type"] = "news_article"
                    return articles
        except Exception as e:
            logger.warning(f"Feed fetch failed: {e}")
        return []


# Convenience functions
async def search_rss_news(query: str, language: str = "en", max_results: int = 5) -> List[Dict[str, Any]]:
    """Convenience function für News-Suche"""
    aggregator = RSSNewsAggregator()
    return await aggregator.search_news(query, language, max_results)


async def get_headlines(language: str = "en", count: int = 10) -> List[Dict[str, Any]]:
    """Convenience function für aktuelle Headlines"""
    aggregator = RSSNewsAggregator()
    return await aggregator.get_latest_headlines(language, count)
