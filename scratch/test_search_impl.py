import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

async def test_live_search(company_name, domain=""):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    discovered = []

    # 1. Google News RSS
    url = f"https://news.google.com/rss/search?q={quote_plus(company_name)}&hl=en-US&gl=US&ceid=US:en"
    async with httpx.AsyncClient(headers=headers, timeout=8.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "xml")
                for item in soup.find_all("item")[:6]:
                    title = item.title.text if item.title else ""
                    link = item.link.text if item.link else ""
                    pub = item.pubDate.text if item.pubDate else ""
                    if title:
                        discovered.append({
                            "title": title,
                            "snippet": f"Published: {pub}. Live article: {title}",
                            "url": link,
                            "source": "Google News Index"
                        })
        except Exception as e:
            print("News error:", e)

        # 2. Direct domain scrape if provided
        if domain:
            try:
                d_url = f"https://{domain.replace('http://', '').replace('https://', '').strip('/')}"
                resp = await client.get(d_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string.strip() if soup.title else f"{company_name} Portal"
                    desc = ""
                    meta = soup.find("meta", attrs={"name": "description"})
                    if meta and meta.get("content"):
                        desc = meta["content"].strip()
                    discovered.insert(0, {
                        "title": title,
                        "snippet": desc or f"Official corporate domain for {company_name}",
                        "url": d_url,
                        "source": domain
                    })
            except Exception as e:
                print("Domain error:", e)

    print(f"Company '{company_name}': Discovered {len(discovered)} items.")
    for d in discovered[:3]:
        print(" -", d["title"][:70], "|", d["url"][:50])
    return discovered

async def main():
    print("=== Tredence Inc ===")
    await test_live_search("Tredence Inc", "tredence.com")
    print("\n=== jamsesbond ===")
    await test_live_search("jamsesbond", "")

asyncio.run(main())
