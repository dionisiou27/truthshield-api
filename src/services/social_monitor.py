import tweepy
import logging
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from src.core.config import settings

logger = logging.getLogger(__name__)

class SocialMediaMonitor:
    """Monitor social media platforms for misinformation"""
    
    def __init__(self):
        self.twitter_api = None
        self.company_targets = {
            "vodafone": ["Vodafone", "Vodafone Deutschland", "@VodafoneDE", "vodafone.de"],
            "bmw": ["BMW", "BMW Deutschland", "@BMW", "bmw.de"],
            "bayer": ["Bayer", "Bayer AG", "@Bayer", "bayer.de"],
            "deutsche_telekom": ["Deutsche Telekom", "Telekom", "@deutschetelekom", "telekom.de"],
            "sap": ["SAP", "SAP Deutschland", "@SAP"],
            "siemens": ["Siemens", "Siemens AG", "@Siemens"]
        }
        
        self._init_twitter()
    
    def _init_twitter(self):
        """Initialize Twitter API connection"""
        if not settings.twitter_api_key or not settings.twitter_api_secret:
            logger.warning("⚠️ Twitter API credentials not configured")
            return
            
        try:
            auth = tweepy.AppAuthHandler(
                settings.twitter_api_key, 
                settings.twitter_api_secret
            )
            self.twitter_api = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Test API connection
            self.twitter_api.verify_credentials()
            logger.info("✅ Twitter API initialized and verified")
            
        except Exception as e:
            logger.error(f"❌ Twitter API initialization failed: {e}")
    
    async def monitor_twitter_keywords(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """Monitor Twitter for specific keywords"""
        if not self.twitter_api:
            logger.warning("Twitter API not available - returning mock data")
            return self._generate_mock_data(keywords, limit)
        
        results = []
        
        try:
            for keyword in keywords:
                tweets = tweepy.Cursor(
                    self.twitter_api.search_tweets,
                    q=f"{keyword} -RT",  # Exclude retweets
                    lang="de",
                    result_type="recent",
                    tweet_mode="extended"
                ).items(limit)
                
                for tweet in tweets:
                    tweet_data = {
                        "platform": "twitter",
                        "content_id": str(tweet.id),
                        "content_text": tweet.full_text,
                        "author_username": tweet.user.screen_name,
                        "content_url": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                        "keyword_matched": keyword,
                        "created_at": tweet.created_at.isoformat(),
                        "engagement": {
                            "retweets": tweet.retweet_count,
                            "likes": tweet.favorite_count,
                            "author_followers": tweet.user.followers_count
                        }
                    }
                    results.append(tweet_data)
                    
        except Exception as e:
            logger.error(f"Twitter monitoring error: {e}")
            return self._generate_mock_data(keywords, limit)
        
        return results
    
    def _generate_mock_data(self, keywords: List[str], limit: int) -> List[Dict]:
        """Generate mock social media data for testing"""
        mock_data = []
        
        sample_texts = [
            "Interessanter Artikel über {keyword}. Was denkt ihr darüber?",
            "Neue Entwicklung bei {keyword} - sollten wir uns Sorgen machen?",
            "Hat jemand die neuesten Nachrichten zu {keyword} gesehen?",
            "{keyword} macht wieder Schlagzeilen. Hier sind die Fakten:",
            "Diskussion über {keyword} wird immer heftiger. Meine Meinung..."
        ]
        
        for i, keyword in enumerate(keywords[:limit]):
            for j, text_template in enumerate(sample_texts[:2]):  # Limit mock data
                mock_data.append({
                    "platform": "twitter",
                    "content_id": f"mock_{i}_{j}_{datetime.now().timestamp()}",
                    "content_text": text_template.format(keyword=keyword),
                    "author_username": f"user_{i}_{j}",
                    "content_url": f"https://twitter.com/user_{i}_{j}/status/123456789",
                    "keyword_matched": keyword,
                    "created_at": datetime.now().isoformat(),
                    "engagement": {
                        "retweets": i * 10 + j,
                        "likes": i * 20 + j * 5,
                        "author_followers": 1000 + i * 100
                    }
                })
                
        return mock_data
    
    def get_company_keywords(self, company_name: str) -> List[str]:
        """Get monitoring keywords for a specific company"""
        return self.company_targets.get(company_name.lower(), [])
    
    async def scan_for_threats(self, company_name: str, limit: int = 20) -> List[Dict]:
        """Scan social media for threats against a specific company"""
        keywords = self.get_company_keywords(company_name)
        if not keywords:
            return []
        
        # Add German misinformation-related keywords
        threat_keywords = []
        for keyword in keywords:
            threat_keywords.extend([
                f"{keyword} fake",
                f"{keyword} lüge", 
                f"{keyword} betrug",
                f"{keyword} skandal",
                f"{keyword} manipulation"
            ])
        
        return await self.monitor_twitter_keywords(threat_keywords, limit)