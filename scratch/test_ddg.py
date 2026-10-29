import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

async def test_search(query):
    async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
        # Try html endpoint
        url_html = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        resp = await client.get(url_html)
        print(f"Query: {query}")
        print(f"HTML Endpoint status: {resp.status_code}, length: {len(resp.text)}")

        # Try lite endpoint
        url_lite = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
        resp_lite = await client.get(url_lite)
        print(f"Lite Endpoint status: {resp_lite.status_code}, length: {len(resp_lite.text)}")
        soup = BeautifulSoup(resp_lite.text, "html.parser")
        results = soup.select(".result-link")
        print(f"Lite results count: {len(results)}")
        for r in results[:3]:
            print(" -", r.get_text(strip=True))

asyncio.run(test_search("Tredence Inc Enterprise AI"))
print("---")
asyncio.run(test_search("jamsesbond news expansion hiring funding"))
