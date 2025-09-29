import os
from dotenv import load_dotenv

load_dotenv()

print("=== LOCAL ENV TEST ===")
print(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
print(f"GOOGLE_API_KEY: {'SET' if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}")  
print(f"NEWS_API_KEY: {'SET' if os.getenv('NEWS_API_KEY') else 'NOT SET'}")

# Test the AI engine
from src.core.ai_engine import ai_engine
print(f"\nOpenAI Client: {'INITIALIZED' if ai_engine.openai_client else 'NOT INITIALIZED'}")