import asyncio
from src.services.tiktok_scraper import tiktok_scraper

async def test():
    # Test video URL abrufen
    videos = await tiktok_scraper.get_influencer_videos("testuser")
    print(f"✅ Found {len(videos)} videos")
    
    # Test Kommentare abrufen
    if videos:
        comments = await tiktok_scraper.scrape_comments_mock(videos[0])
        print(f"✅ Found {len(comments)} comments")
        print(f"First comment: {comments[0]['text']}")

asyncio.run(test())