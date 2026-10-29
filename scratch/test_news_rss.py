import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def test_google_news(query):
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    resp = httpx.get(url, headers=headers, timeout=10.0)
    print(f"Query: {query} -> Status: {resp.status_code}")
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        print(f"Items found: {len(items)}")
        for item in items[:3]:
            print(" - Title:", item.title.text if item.title else "")
            print("   Link:", item.link.text if item.link else "")
            print("   PubDate:", item.pubDate.text if item.pubDate else "")

print("=== Test 1: Real Company ===")
test_google_news("Tredence Inc")

print("\n=== Test 2: Fake/Gibberish Company ===")
test_google_news("jamsesbond")
