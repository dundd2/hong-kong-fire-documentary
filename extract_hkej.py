import bs4
from bs4 import BeautifulSoup
import re
import sys

# We have files hkej_instant.html and hkej_page2..15.html
# We want to produce a list categorized by date.

all_entries = []

files = ['hkej_instant.html'] + [f'hkej_page{i}.html' for i in range(2, 16)]

def extract_date_from_image_url(url):
    match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None

def extract_id(link):
    match = re.search(r'/article/(\d+)/', link)
    if match:
        return int(match.group(1))
    return 0

for filepath in files:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        continue

    soup = BeautifulSoup(content, 'html.parser')
    # Update: Include 'hkej_toc_content_wrapper_2014' to catch the Top Story
    items = soup.find_all('div', class_=['hkej_toc_listingAll_news2_2014', 'hkej_toc_content_wrapper_2014'])

    for item in items:
        h3 = item.find('h3')
        if not h3: continue
        a_tag = h3.find('a')
        if not a_tag: continue

        title = a_tag.get_text(strip=True)
        link = a_tag.get('href')

        # Check relevance
        summary_text = ""
        # Update: Check both classes for summary
        summary_p = item.find('p', class_=['hkej_toc_listingAll_news2_recap_2014', 'hkej_toc_cat_top_content'])
        if summary_p:
            summary_text = summary_p.get_text()

        # Search content
        search_content = title + " " + summary_text

        # Refined Filtering Logic
        is_relevant = False
        # 1. Direct mention of "Wang Fuk" (English or Chinese)
        if "宏福" in search_content or "Wang Fuk" in search_content:
            is_relevant = True
        # 2. "Tai Po" AND ("Fire" in Chinese or English)
        elif "大埔" in search_content and ("火" in search_content or "Fire" in search_content):
            # Exclude unrelated "fire" like "Ceasefire" (停火) if it doesn't mention Tai Po (already checked Tai Po)
            # But "Tai Po" + "Ceasefire" is unlikely.
            # However, ensure "火" is not just part of "火炬" (Torch) if unrelated, but "Tai Po" context makes it likely relevant.
            # Let's stick to the reviewed logic.
            is_relevant = True

        if not is_relevant:
            continue

        # Date extraction
        date_str = None
        img = item.find('img')
        if img:
            src = img.get('src')
            date_str = extract_date_from_image_url(src)

        full_link = link
        if not link.startswith('http'):
            full_link = f"https://www.hkej.com{link}"

        all_entries.append({
            'title': title,
            'link': full_link,
            'date': date_str,
            'id': extract_id(link)
        })

# Sort by ID descending (newest first)
all_entries.sort(key=lambda x: x['id'], reverse=True)

# Date Inference
current_date = "2025-11-29" # Start with today (simulation date)

final_list = []
for entry in all_entries:
    if entry['date']:
        current_date = entry['date']
    else:
        entry['date'] = current_date
    final_list.append(entry)

# Group by date
grouped = {}
for entry in final_list:
    d = entry['date']
    if d not in grouped:
        grouped[d] = []
    # Avoid duplicates
    if not any(x['link'] == entry['link'] for x in grouped[d]):
        grouped[d].append(entry)

# Output in Markdown format
dates = sorted(grouped.keys(), reverse=True)
for d in dates:
    print(f"### {d}")
    for item in grouped[d]:
        print(f"- [{item['title']}]({item['link']})")
    print("")
