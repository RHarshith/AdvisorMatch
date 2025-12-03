import json
import sqlite3
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DB_PATH = "app/advisormatch_openalex.db"
PROFESSORS_FILE = "app/professors.json"

def get_profile_image(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"  [!] Error fetching {url}: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the profile image container
        img_div = soup.find('div', class_='profile__image')
        if img_div:
            img_tag = img_div.find('img')
            if img_tag and img_tag.get('src'):
                src = img_tag['src']
                # Resolve relative URL
                full_url = urljoin(url, src)
                return full_url
                
        return None
    except Exception as e:
        print(f"  [!] Exception fetching {url}: {e}")
        return None

def main():
    # Load professors from JSON to get their URLs
    with open(PROFESSORS_FILE, 'r') as f:
        profs_json = json.load(f)
        
    # Create a map of name -> url
    prof_urls = {p['name']: p['url'] for p in profs_json if p.get('url')}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all professors from DB
    cursor.execute("SELECT id, name FROM professors")
    db_profs = cursor.fetchall()
    
    print(f"Scraping photos for {len(db_profs)} professors...")
    
    updated_count = 0
    skipped_count = 0
    
    for prof_id, name in db_profs:
        url = prof_urls.get(name)
        
        if not url:
            print(f"[-] No URL found for {name}")
            skipped_count += 1
            continue
            
        print(f"Processing {name}...")
        image_url = get_profile_image(url)
        
        if image_url:
            print(f"  [+] Found photo: {image_url}")
            cursor.execute("UPDATE professors SET image_url = ? WHERE id = ?", (image_url, prof_id))
            updated_count += 1
        else:
            print(f"  [-] No photo found on page.")
            # Keep the placeholder if no real photo found
            
        # Be polite
        time.sleep(0.5)
        
    conn.commit()
    conn.close()
    
    print(f"\nDone!")
    print(f"Updated: {updated_count}")
    print(f"Skipped (no URL): {skipped_count}")

if __name__ == "__main__":
    main()
