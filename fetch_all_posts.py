import requests
from bs4 import BeautifulSoup
import feedparser
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import time
from html2text import html2text

load_dotenv()

# Load model
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded!\n")

def get_all_post_urls():
    """Scrape archive page to get all post URLs"""
    
    print("Fetching archive page...")
    url = "https://gohigh.substack.com/archive"
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all post links (Substack uses specific classes)
    # This might need adjustment based on actual HTML structure
    post_links = []
    
    # Method 1: Try finding post title links
    for link in soup.find_all('a', class_='post-preview-title'):
        href = link.get('href')
        if href and href.startswith('https://gohigh.substack.com/p/'):
            post_links.append(href)
    
    # Method 2: If method 1 doesn't work, try this
    if not post_links:
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/p/' in href and 'gohigh.substack.com' in href:
                full_url = href if href.startswith('http') else f"https://gohigh.substack.com{href}"
                if full_url not in post_links:
                    post_links.append(full_url)
    
    print(f"✅ Found {len(post_links)} posts on archive page\n")
    return post_links

def fetch_post_content(url):
    """Fetch full content from a post URL"""
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title_tag = soup.find('h1', class_='post-title')
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        
        # Extract content
        # Substack uses 'available-content' or 'body' class
        content_div = soup.find('div', class_='available-content')
        if not content_div:
            content_div = soup.find('div', class_='body')
        
        if content_div:
            # Convert HTML to text
            content = html2text(str(content_div))
            # Clean up
            content = content.replace('\n\n\n', '\n\n').strip()
        else:
            content = ""
        
        return title, content
        
    except Exception as e:
        print(f"  ⚠️  Error fetching {url}: {e}")
        return None, None

def store_in_database(title, content, url, embedding):
    """Store post in PostgreSQL"""
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    register_vector(conn)
    cur = conn.cursor()
    
    # Check if already exists
    cur.execute("SELECT id FROM sql_docs WHERE url = %s", (url,))
    if cur.fetchone():
        print(f"  ⏭️  Already exists: {title}")
        cur.close()
        conn.close()
        return False
    
    # Insert new post
    cur.execute("""
        INSERT INTO sql_docs (title, content, url, embedding)
        VALUES (%s, %s, %s, %s)
    """, (title, content, url, embedding))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return True

def main():
    """Main function to fetch and store all posts"""
    
    print("="*70)
    print("  Fetching ALL Blog Posts from Substack")
    print("="*70)
    print()
    
    # Get all post URLs
    post_urls = get_all_post_urls()
    
    if not post_urls:
        print("❌ No posts found! Check the scraping logic.")
        return
    
    print(f"Processing {len(post_urls)} posts...\n")
    
    successful = 0
    skipped = 0
    failed = 0
    
    for i, url in enumerate(post_urls, 1):
        print(f"[{i}/{len(post_urls)}] Fetching: {url}")
        
        # Fetch content
        title, content = fetch_post_content(url)
        
        if not title or not content:
            print(f"  ❌ Failed to fetch content")
            failed += 1
            continue
        
        # Truncate title for display
        display_title = title[:60] + "..." if len(title) > 60 else title
        print(f"  📝 {display_title}")
        
        # Generate embedding
        text = f"{title} {content}"
        embedding = model.encode(text).tolist()
        
        # Store in database
        if store_in_database(title, content, url, embedding):
            print(f"  ✅ Stored")
            successful += 1
        else:
            skipped += 1
        
        print()
        
        # Be nice to Substack servers - wait between requests
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