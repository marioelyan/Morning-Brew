import feedparser
import json
from datetime import datetime, timezone
from bs4 import BeautifulSoup

RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://fortune.com/feed/",
    "https://www.entrepreneur.com/latest.rss",
    "https://www.forbes.com/business/feed/",
    "https://news.crunchbase.com/feed/"
]

def clean_html(html, max_length=500):
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    return text[:max_length]

def collect_rss():
    articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title", feed_url)
            print(f"Collecting: {source_name}")
            for entry in feed.entries:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "source": source_name,
                    "published": entry.get("published", ""),
                    "collected_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            print(f"Error: {feed_url}\n{e}")
    return articles

def remove_duplicates(articles):
    unique = {}
    for article in articles:
        title = article["title"].strip().lower()
        if title not in unique:
            unique[title] = article
    return list(unique.values())

def save_json(articles, filename="news.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def run():
    print("Starting Scout...")
    articles = collect_rss()
    print(f"\nCollected: {len(articles)}")
    articles = remove_duplicates(articles)
    print(f"After Dedupe: {len(articles)}")
    save_json(articles)
    print("\nSaved to news.json")

if __name__ == "__main__":
    run()
