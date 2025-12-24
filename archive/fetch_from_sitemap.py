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
    
    response = requests.get(sitemap_url)
    
    if response.status_code != 200:
        print(f"❌ Could not fetch sitemap (status {response.status_code})")
        return []
    
    # Parse XML
    root = ET.fromstring(response.content)
    
    # Substack sitemap namespace
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    # Extract all URLs that are blog posts
    post_urls = []
    for url in root.findall('.//ns:url/ns:loc', ns):
        url_text = url.text
        if '/p/' in url_text:
            post_urls.append(url_text)
    
    print(f"✅ Found {len(post_urls)} posts in sitemap\n")
    return post_urls

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
            # Limit to reasonable size
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

def main():
    print("="*70)