import urllib.request
import xml.etree.ElementTree as ET
import re
from datetime import datetime

url = "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
res = urllib.request.urlopen(req, timeout=10)
tree = ET.fromstring(res.read())

stories = []
for item in tree.findall(".//item")[:10]:
    title = item.findtext("title", "")
    link = item.findtext("link", "")
    pub_date = item.findtext("pubDate", "")
    desc = item.findtext("description", "")
    
    sources = re.findall(r'<font color="#6f6f6f">(.*?)</font>', desc)
    cleaned_sources = [s.replace(".com", "").strip() for s in sources if s.strip()]
    
    headline = title
    if " - " in title:
        headline = title.rsplit(" - ", 1)[0]
        
    stories.append({
        "title": headline,
        "sources": cleaned_sources[:4],
        "sites_count": len(sources) if len(sources) > 0 else 1,
        "link": link,
        "date": pub_date
    })

print(f"Parsed {len(stories)} Google News clustered stories:")
for s in stories:
    sources_str = ", ".join(s['sources'])
    print(f"- {s['title']} [{sources_str}] ({s['sites_count']} sites)")
