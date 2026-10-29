import httpx
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

with httpx.Client(headers=headers, timeout=10.0) as client:
    resp = client.get("https://html.duckduckgo.com/html/?q=Tredence+Inc")
    print("Status:", resp.status_code)
    soup = BeautifulSoup(resp.text, "html.parser")
    print("Title:", soup.title)
    forms = soup.find_all("form")
    print("Forms:", len(forms))
    for f in forms:
        print("Form action:", f.get("action"))
        for inp in f.find_all("input"):
            print(" Input:", inp.get("name"), inp.get("value"))
