import urllib.request
import xml.etree.ElementTree as ET
import re
import email.utils
from datetime import datetime, timezone

def fetch_google_news_clusters(custom_query: str = None, max_items: int = 15):
    feeds = [
        # 1. Curated Google News Business/Markets Topic (User's URL topic)
        ("https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en", "MARKETS_TOPIC"),
        # 2. Dynamic Portfolio & Macro Search Feed
        ("https://news.google.com/rss/search?q=when:24h+(COIN+OR+NVDA+OR+INTC+OR+PLTR+OR+IBM+OR+GOOGL+OR+NEM+OR+markets+OR+inflation+OR+fed)&hl=en-US&gl=US&ceid=US:en", "PORTFOLIO_SEARCH")
    ]
    if custom_query:
        encoded_q = urllib.parse.quote(custom_query)
        feeds.insert(0, (f"https://news.google.com/rss/search?q=when:24h+({encoded_q})&hl=en-US&gl=US&ceid=US:en", "CUSTOM_SEARCH"))

    items = []
    seen_titles = set()
    now_utc = datetime.now(timezone.utc)

    for feed_url, feed_type in feeds:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=6) as response:
                root = ET.fromstring(response.read())
                for item in root.findall(".//item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub_date = item.findtext("pubDate", "")
                    desc = item.findtext("description", "")

                    if not title:
                        continue

                    # Extract headline and primary source
                    headline = title
                    primary_source = "Financial Wire"
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        headline = parts[0].strip()
                        primary_source = parts[1].strip()

                    # Deduplicate by normalized headline
                    norm_title = re.sub(r"[^\w\s]", "", headline).lower()
                    if norm_title in seen_titles:
                        continue
                    seen_titles.add(norm_title)

                    # Extract clustered source outlets from <font color="#6f6f6f">
                    sources_raw = re.findall(r'<font color="#6f6f6f">(.*?)</font>', desc)
                    clean_sources = []
                    for s in sources_raw:
                        clean_s = re.sub(r'\.com$', '', s.strip())
                        clean_s = re.sub(r'\s+-\s+.*$', '', clean_s)
                        if clean_s and clean_s not in clean_sources:
                            clean_sources.append(clean_s)

                    if not clean_sources and primary_source:
                        clean_sources = [primary_source]

                    sites_count = len(clean_sources)

                    # Calculate relative time
                    dt = None
                    rel_time = "Recent"
                    if pub_date:
                        try:
                            dt = email.utils.parsedate_to_datetime(pub_date)
                            diff_sec = max(0, int((now_utc - dt).total_seconds()))
                            diff_mins = diff_sec // 60
                            if diff_mins < 1:
                                rel_time = "Just now"
                            elif diff_mins < 60:
                                rel_time = f"{diff_mins}m ago"
                            elif diff_mins < 1440:
                                rel_time = f"{diff_mins // 60}h ago"
                            else:
                                rel_time = f"{diff_mins // 1440}d ago"
                        except Exception:
                            pass

                    # Determine thematic category & bias
                    h_lower = headline.lower()
                    if any(w in h_lower for w in ["crypto", "bitcoin", "btc", "eth", "ethereum", "coinbase", "solana"]):
                        cat = "Digital Assets / Crypto"
                        bias = "NEUTRAL_CALENDAR"
                    elif any(w in h_lower for w in ["oil", "crude", "energy", "opec", "gas", "brent"]):
                        cat = "Energy & Commodities"
                        bias = "BULLISH_CSP"
                    elif any(w in h_lower for w in ["inflation", "fed", "powell", "rate hike", "rate cut", "cpi", "pce", "yield", "treasury"]):
                        cat = "Federal Reserve & Rates"
                        bias = "NEUTRAL_YIELD"
                    elif any(w in h_lower for w in ["ai", "chips", "semiconductor", "nvidia", "software", "cloud", "oracle", "anthropic", "openai"]):
                        cat = "Tech & AI Capex"
                        bias = "BULLISH_CSP"
                    else:
                        cat = "Wall Street & Equities"
                        bias = "BULLISH_CSP"

                    items.append({
                        "headline": headline,
                        "primary_source": primary_source,
                        "sources": clean_sources[:5],
                        "sites_count": sites_count,
                        "link": link,
                        "pub_date": pub_date,
                        "time": rel_time,
                        "category": cat,
                        "bias": bias,
                        "_dt": dt
                    })

                    if len(items) >= max_items:
                        break
        except Exception as e:
            print(f"Feed error on {feed_type}: {e}")

        if len(items) >= max_items:
            break

    return items

results = fetch_google_news_clusters(max_items=8)
print(f"Successfully collected {len(results)} clustered stories:")
for r in results:
    print(f"- [{r['category']}] {r['headline']}")
    print(f"  Sources: {', '.join(r['sources'])} ({r['sites_count']} sites) | {r['time']}")
