import os
from dotenv import load_dotenv
import openai

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key exists: {bool(api_key)}")
print(f"API Key starts with: {api_key[:7] if api_key else 'NOT SET'}...")

if api_key:
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API working'"}],
            max_tokens=10
        )
        print(f"✅ OpenAI API is working! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ OpenAI API error: {e}")
else:
    print("❌ No OpenAI API key found in .env file")