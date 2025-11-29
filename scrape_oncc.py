from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup
import re
import argparse
import sys

def scrape(query="宏福苑", target_date_prefix="202511"):
    """
    Scrapes on.cc for news related to a query, focusing on a specific date prefix (YYYYMM).
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        links = []

        # Strategy 1: Search
        print(f"--- Strategy 1: Search for '{query}' ---")
        try:
            page.goto("https://hk.on.cc/search/index.html", timeout=30000, wait_until="commit")
            # Wait for search input to be ready
            try:
                page.wait_for_selector("#center-searchSubject", timeout=10000)
            except:
                print("Search input not found immediately, page might be slow.")

            selector = "#center-searchSubject"

            if page.is_visible(selector):
                print(f"Found search input: {selector}")
                page.fill(selector, query)
                page.press(selector, "Enter")

                print("Submitted search, waiting for results...")
                time.sleep(10) # Dynamic loading wait

                # Extract links from search result
                soup = BeautifulSoup(page.content(), 'html.parser')
                found = soup.find_all('a', href=True)

                count = 0
                for a in found:
                    href = a['href']
                    text = a.get_text(strip=True)
                    if 'bkn/cnt/news' in href:
                        links.append({'title': text, 'url': href, 'source': 'search'})
                        count += 1
                print(f"Found {count} news links via search.")
            else:
                print("Search input not found/visible.")

        except Exception as e:
            print(f"Search strategy failed: {e}")

        # Strategy 2: Crawl specific related article (Fallback/Augmentation)
        # This is useful because search engines on news sites are often strictly indexed and might miss breaking news clusters.
        # We target a known 'anchor' article if available, or just rely on search.
        # For this specific task, we know the event is around Nov 26.

        print("\n--- Strategy 2: Augmented Crawl (Related News) ---")
        # In a real general tool, we might skip this or make it an argument.
        # But for the requested task, ensuring we get the 'chain' of stories is critical.
        # We will try to visit the first valid link found in search to get its 'related news'.

        anchor_url = None
        if links:
             # Pick the first one that matches our date prefix if possible
             for link in links:
                 if target_date_prefix in link['url']:
                     anchor_url = link['url']
                     # Fix URL if relative
                     if anchor_url.startswith('//'):
                         anchor_url = 'https:' + anchor_url
                     elif anchor_url.startswith('/'):
                         anchor_url = 'https://hk.on.cc' + anchor_url
                     break

        # If search failed entirely, we might hardcode a fallback entry point for this specific request context
        # but for a general script, we just proceed.
        if not anchor_url and "宏福苑" in query:
             # Fallback for the specific task context if search returns 0 (e.g. anti-bot on search page)
             anchor_url = "https://hk.on.cc/hk/bkn/cnt/news/20251129/bkn-20251129033525667-1129_00822_001.html"

        if anchor_url:
            try:
                print(f"Visiting anchor article for related news: {anchor_url}")
                page.goto(anchor_url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(5)

                soup = BeautifulSoup(page.content(), 'html.parser')

                # Add the anchor itself if not present
                title_tag = soup.find('h1')
                if title_tag:
                    links.append({'title': title_tag.get_text(strip=True), 'url': anchor_url, 'source': 'direct'})

                # Find related news
                all_links = soup.find_all('a', href=True)
                for a in all_links:
                    href = a['href']
                    text = a.get_text(strip=True)
                    if 'bkn/cnt/news' in href:
                        # Simple keyword relevance check
                        if any(k in text for k in query.split()):
                            links.append({'title': text, 'url': href, 'source': 'related'})

            except Exception as e:
                print(f"Crawl strategy failed: {e}")

        browser.close()

        # Process and Clean Data
        print("\n--- Processing Results ---")
        unique_articles = {}
        for item in links:
            url = item['url']
            # Normalize URL
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://hk.on.cc' + url

            if url not in unique_articles:
                # Extract date from URL
                # Pattern: /yyyymmdd/
                date_match = re.search(r'/(\d{8})/', url)
                if date_match:
                    date_str = date_match.group(1)
                    # Filter by requested prefix
                    if date_str.startswith(target_date_prefix):
                        unique_articles[url] = {
                            'date': date_str,
                            'title': item['title'],
                            'url': url
                        }

        # Sort by date
        sorted_articles = sorted(unique_articles.values(), key=lambda x: x['date'])

        # Output
        if not sorted_articles:
            print("No relevant articles found.")
        else:
            print(f"Found {len(sorted_articles)} articles:")
            current_date = ""
            for art in sorted_articles:
                # Print header for new dates
                if art['date'] != current_date:
                    print(f"\n[{art['date']}]")
                    current_date = art['date']
                print(f"- {art['title']} ({art['url']})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape on.cc news.')
    parser.add_argument('--query', type=str, default="宏福苑", help='Search query')
    parser.add_argument('--date', type=str, default="202511", help='Date prefix (YYYYMM) to filter')
    args = parser.parse_args()

    scrape(query=args.query, target_date_prefix=args.date)
