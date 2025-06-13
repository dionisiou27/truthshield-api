import requests
from bs4 import BeautifulSoup

# Test mit einer einfachen Webseite
url = "https://example.com"
response = requests.get(url)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.find('title').text
    print(f"✅ Scraping funktioniert! Title: {title}")
else:
    print(f"❌ Fehler: {response.status_code}")