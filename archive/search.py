import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# Load the same model we used for generating embeddings
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model loaded!\n")

def search_docs(query, limit=3):
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
    print(f"🔍 Searching for: {query}")
    query_embedding = model.encode(query).tolist()
    
    # Search for similar documents using cosine distance
    # <=> is the cosine distance operator in pgvector
    cur.execute(
        '''SELECT title, content, url, 
                  1 - (embedding <=> %s::vector) as similarity
           FROM sql_docs
           ORDER BY embedding <=> %s::vector
           LIMIT %s''',
        (query_embedding, query_embedding, limit)
    )
    
    results = cur.fetchall()
    
    print(f"\n📚 Found {len(results)} relevant documents:\n")
    
    for i, (title, content, url, similarity) in enumerate(results, 1):
        print(f"{i}. {title}")
        print(f"   Similarity: {similarity:.4f}")
        print(f"   {content[:150]}...")
        print(f"   URL: {url}\n")
    
    cur.close()
    conn.close()
    
    return results

if __name__ == "__main__":
    # Test queries
    test_queries = [
        "How do I improve query performance?",
        "What is memory configuration?",
        "How do indexes work?",
        "Troubleshoot slow database queries"
    ]
    
    for query in test_queries:
        print("="*70)
        search_docs(query, limit=2)
        print("\n")