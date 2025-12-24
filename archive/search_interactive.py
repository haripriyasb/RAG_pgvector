import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import time

load_dotenv()

# Load the model once
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded!\n")

def search_docs(query, limit=5):
    """Search SQL Server docs using vector similarity"""
    
    # Connect to database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    register_vector(conn)
    cur = conn.cursor()
    
    # Generate embedding for the search query
    print(f"🔍 Searching for: {query}\n")
    query_embedding = model.encode(query).tolist()
    
    # Search for similar documents
    cur.execute(
        '''SELECT title, content, url, 
                  1 - (embedding <=> %s::vector) as similarity
           FROM sql_docs
           ORDER BY embedding <=> %s::vector
           LIMIT %s''',
        (query_embedding, query_embedding, limit)
    )
    
    results = cur.fetchall()
    
    # Filter by minimum similarity threshold
    MIN_SIMILARITY = 0.3  # Only show docs above 30% similarity
    filtered_results = [(t, c, u, s) for t, c, u, s in results if s >= MIN_SIMILARITY]
    
    if filtered_results:
        print(f"📚 Found {len(filtered_results)} relevant documents:\n")
        
        for i, (title, content, url, similarity) in enumerate(filtered_results, 1):
            # Color-code by relevance
            if similarity >= 0.7:
                relevance = "🟢 Excellent"
            elif similarity >= 0.5:
                relevance = "🟡 Good"
            else:
                relevance = "🟠 Moderate"
                
            print(f"{i}. {title}")
            print(f"   Similarity: {similarity:.4f} ({relevance})")
            print(f"   {content[:200]}...")
            print(f"   URL: {url}\n")
    else:
        print("❌ No sufficiently relevant results found.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("=" * 70)
    print("    SQL Server Documentation Search (Semantic)")
    print("=" * 70)
    
    while True:
        print("\n" + "-" * 70)
        query = input("🔍 Enter your search query (or 'quit' to exit): ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
            
        if not query:
            print("⚠️  Please enter a search query.")
            continue
        
        print()
        search_docs(query, limit=5)



start_time = time.time()
results = search_docs(query)
elapsed = time.time() - start_time
print(f"⏱️  Search completed in {elapsed:.3f} seconds")