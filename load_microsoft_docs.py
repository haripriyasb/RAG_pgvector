import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import time

load_dotenv()

# Load model
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded\n")

# Curated list of important Microsoft SQL Server docs
MICROSOFT_DOCS = [
    # Indexes
    "https://learn.microsoft.com/en-us/sql/relational-databases/indexes/indexes",
    "https://learn.microsoft.com/en-us/sql/relational-databases/indexes/clustered-and-nonclustered-indexes-described",
    "https://learn.microsoft.com/en-us/sql/relational-databases/indexes/create-indexes-with-included-columns",
    
    # Performance
    "https://learn.microsoft.com/en-us/sql/relational-databases/performance/query-processing-architecture-guide",
    "https://learn.microsoft.com/en-us/sql/relational-databases/performance/execution-plans",
    "https://learn.microsoft.com/en-us/sql/relational-databases/performance/monitor-and-tune-for-performance",
    
    # TempDB
    "https://learn.microsoft.com/en-us/sql/relational-databases/databases/tempdb-database",
    
    # Memory
    "https://learn.microsoft.com/en-us/sql/database-engine/configure-windows/server-memory-server-configuration-options",
    
    # Locking & Transactions
    "https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide",
    
    # High Availability
    "https://learn.microsoft.com/en-us/sql/database-engine/availability-groups/windows/overview-of-always-on-availability-groups-sql-server",
    
    # Backup
    "https://learn.microsoft.com/en-us/sql/relational-databases/backup-restore/backup-overview-sql-server",
    
    # Security
    "https://learn.microsoft.com/en-us/sql/relational-databases/security/security-center-for-sql-server-database-engine-and-azure-sql-database",
    
    # Statistics
    "https://learn.microsoft.com/en-us/sql/relational-databases/statistics/statistics",
    
    # T-SQL
    "https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql",
]

def scrape_microsoft_doc(url):
    """Scrape Microsoft Learn page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"  📥 Downloading page...")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"  ❌ HTTP {response.status_code}")
            return None, None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('h1')
        if not title:
            title = soup.find('title')
        title_text = title.get_text(strip=True) if title else "Untitled"
        
        # Extract main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'role': 'main'})
        
        if main_content:
            # Remove unwanted elements
            for tag in main_content.find_all(['nav', 'aside', 'script', 'style', 'footer', 'header', 'button', 'form']):
                tag.decompose()
            
            # Get text content
            content = main_content.get_text(separator='\n', strip=True)
            
            # Clean up multiple newlines
            content = '\n'.join(line for line in content.split('\n') if line.strip())
            
            # Limit size
            if len(content) > 15000:
                content = content[:15000] + "..."
            
            print(f"  ✅ Extracted {len(content)} characters")
        else:
            content = ""
            print(f"  ⚠️  No main content found")
        
        return title_text, content
        
    except requests.Timeout:
        print(f"  ❌ Timeout")
        return None, None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None, None

def store_in_database(title, content, url, source='microsoft'):
    """Store document in database"""
    
    if not content or len(content) < 100:
        print(f"  ⚠️  Content too short, skipping")
        return False
    
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
    
    # Generate embedding
    print(f"  🔢 Generating embedding...")
    text = f"{title} {content}"
    embedding = model.encode(text).tolist()
    
    # Insert
    print(f"  💾 Storing in database...")
    cur.execute("""
        INSERT INTO sql_docs (title, content, url, embedding, source)
        VALUES (%s, %s, %s, %s, %s)
    """, (title, content, url, embedding, source))
    
    conn.commit()
    cur.close()
    conn.close()
    return True

def main():
    print("="*70)
    print("  Loading Microsoft SQL Server Documentation")
    print("="*70)
    print()
    
    # Check if source column exists
    print("Checking database schema...")
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    
    # Check if source column exists
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='sql_docs' AND column_name='source'
    """)
    
    if not cur.fetchone():
        print("⚠️  Adding 'source' column to database...")
        cur.execute("ALTER TABLE sql_docs ADD COLUMN source VARCHAR(50) DEFAULT 'blog'")
        cur.execute("UPDATE sql_docs SET source = 'blog' WHERE source IS NULL")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_source ON sql_docs(source)")
        conn.commit()
        print("✅ Database updated\n")
    else:
        print("✅ Database schema OK\n")
    
    cur.close()
    conn.close()
    
    successful = 0
    skipped = 0
    failed = 0
    
    for i, url in enumerate(MICROSOFT_DOCS, 1):
        print(f"[{i}/{len(MICROSOFT_DOCS)}] Processing: {url}")
        
        title, content = scrape_microsoft_doc(url)
        
        if not title or not content:
            print(f"  ❌ Failed to fetch\n")
            failed += 1
            continue
        
        display_title = title[:60] + "..." if len(title) > 60 else title
        print(f"  📝 Title: {display_title}")
        
        if store_in_database(title, content, url, source='microsoft'):
            print(f"  ✅ Successfully stored\n")
            successful += 1
        else:
            print(f"  ⏭️  Already exists or skipped\n")
            skipped += 1
        
        # Be respectful to Microsoft servers
        time.sleep(3)
    
    print("="*70)
    print(f"  COMPLETE!")
    print(f"  ✅ Successfully added: {successful}")
    print(f"  ⏭️  Already existed/skipped: {skipped}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total Microsoft docs: {successful + skipped}")
    print("="*70)
    
    # Show final counts
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    cur.execute("SELECT source, COUNT(*) FROM sql_docs GROUP BY source")
    print("\nDatabase contents:")
    for source, count in cur.fetchall():
        print(f"  {source}: {count} documents")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()