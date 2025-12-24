import psycopg2
from pgvector.psycopg2 import register_vector
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import feedparser

load_dotenv()

# Initialize local embedding model
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded!\n")

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=os.getenv('DB_PORT')
)
register_vector(conn)
cur = conn.cursor()

def generate_embedding(text):
    """Generate embedding using local model"""
    embedding = model.encode(text)
    return embedding.tolist()

# Fetch posts from your Substack RSS feed
print("Fetching posts from gohigh.substack.com...")
feed = feedparser.parse('https://gohigh.substack.com/feed')

if not feed.entries:
    print("❌ Could not fetch RSS feed. Check the URL.")
    exit()

print(f"✅ Fetched {len(feed.entries)} posts from RSS feed\n")

# Clear existing data (optional - comment out if you want to keep old data)
cur.execute("DELETE FROM sql_docs")
conn.commit()
print("🗑️  Cleared existing documents\n")

# Process each blog post
for entry in feed.entries:  # Get all posts
    title = entry.title
    content = entry.summary  # RSS provides summary
    url = entry.link
    
    print(f"Processing: {title[:60]}...")
    
    # Generate embedding for title + content
    text = f"{title} {content}"
    embedding = generate_embedding(text)
    
    # Insert into database
    cur.execute(
        """
        INSERT INTO sql_docs (title, content, url, embedding)
        VALUES (%s, %s, %s, %s)
        """,
        (title, content, url, embedding)
    )
    print(f"✅ Stored\n")

conn.commit()
cur.close()
conn.close()

print(f"\n🎉 Processed {len(feed.entries)} blog posts!")