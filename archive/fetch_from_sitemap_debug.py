import requests
from bs4 import BeautifulSoup
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import time
from html2text import html2text
import xml.etree.ElementTree as ET

load_dotenv()

print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded!\n")

def get_all_post_urls_from_sitemap():
    """Get all post URLs from Substack sitemap"""
    
    print("Fetching sitemap...")
    sitemap_url = "https://gohigh.substack.com/sitemap.xml"
    
    try:
        response = requests.get(sitemap_url)
        print(f"Status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Could not fetch sitemap")
            return []
        
        print(f"Sitemap size: {len(response.content)} bytes")
        
        # Parse XML
        root = ET.fromstring(response.content)
        print("XML parsed successfully")
        
        # Extract all URLs
        post_urls = []
        
        # Try without namespace first
        for url_elem in root.findall('.//url/loc'):
            url_text = url_elem.text
            if url_text and '/p/' in url_text:
                post_urls.append(url_text)
        
        # If that didn't work, try with namespace
        if not post_urls:
            ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            for url_elem in root.findall('.//ns:url/ns:loc', ns):
                url_text = url_elem.text
                if url_text and '/p/' in url_text:
                    post_urls.append(url_text)
        
        print(f"✅ Found {len(post_urls)} posts in sitemap")
        
        # Show first 5
        print("\nFirst 5 posts:")
        for url in post_urls[:5]:
            print(f"  - {url}")
        
        return post_urls
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def fetch_post_content(url):
    """Fetch full content from a post URL"""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title_tag = soup.find('h1', class_='post-title')
        if not title_tag:
            title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        
        # Extract content
        content_div = (
            soup.find('div', class_='available-content') or
            soup.find('div', class_='body') or
            soup.find('div', class_='post-content') or
            soup.find('article')
        )
        
        if content_div:
            content = html2text(str(content_div))
            content = content.replace('\n\n\n', '\n\n').strip()
            if len(content) > 15000:
                content = content[:15000] + "..."
        else:
            content = ""
        
        return title, content
        
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return None, None

def store_in_database(title, content, url, embedding):
    """Store post in PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT')
        )
        register_vector(conn)
        cur = conn.cursor()
        
        # Check if exists
        cur.execute("SELECT id FROM sql_docs WHERE url = %s", (url,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return False
        
        # Insert
        cur.execute("""
            INSERT INTO sql_docs (title, content, url, embedding)
            VALUES (%s, %s, %s, %s)
        """, (title, content, url, embedding))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ⚠️  Database error: {e}")
        return False

def main():
    print("="*70)
    print("  Fetching ALL Blog Posts from Sitemap")
    print("="*70)
    print()
    
    # Get all URLs from sitemap
    post_urls = get_all_post_urls_from_sitemap()
    
    if not post_urls:
        print("\n❌ No posts found in sitemap!")
        return
    
    print(f"\nProcessing {len(post_urls)} posts...\n")
    
    successful = 0
    skipped = 0
    failed = 0
    
    for i, url in enumerate(post_urls, 1):
        print(f"[{i}/{len(post_urls)}] {url}")
        
        # Fetch content
        title, content = fetch_post_content(url)
        
        if not title or not content:
            print(f"  ❌ Failed to fetch")
            failed += 1
            continue
        
        display_title = title[:60] + "..." if len(title) > 60 else title
        print(f"  📝 {display_title}")
        
        # Generate embedding
        text = f"{title} {content}"
        embedding = model.encode(text).tolist()
        
        # Store
        if store_in_database(title, content, url, embedding):
            print(f"  ✅ Stored")
            successful += 1
        else:
            print(f"  ⏭️  Already exists")
            skipped += 1
        
        print()
        time.sleep(1)
    
    print("="*70)
    print(f"  COMPLETE!")
    print(f"  ✅ Successfully added: {successful}")
    print(f"  ⏭️  Already existed: {skipped}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total in database: {successful + skipped}")
    print("="*70)

if __name__ == "__main__":
    main()