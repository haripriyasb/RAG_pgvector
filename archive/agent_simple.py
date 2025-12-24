import warnings
warnings.filterwarnings('ignore')

from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.chat_models import ChatAnthropic
from langchain_core.prompts import PromptTemplate
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# Load models
print("Loading models...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("[OK] Embedding model loaded")

llm = ChatAnthropic(
    model=os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
    temperature=0
)
print("[OK] Claude connected\n")

# ============================================
# TOOLS (using @tool decorator)
# ============================================

@tool
def search_blog(query: str) -> str:
    """Search blog posts for content. Input: search query like 'RCSI' or 'performance'."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    register_vector(conn)
    cur = conn.cursor()
    
    query_embedding = embedding_model.encode(query).tolist()
    
    cur.execute('''
        SELECT title, content, url
        FROM sql_docs
        ORDER BY embedding <=> %s::vector
        LIMIT 3
    ''', (query_embedding,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    if not results:
        return "No posts found."
    
    output = "Found:\n"
    for i, (title, content, url) in enumerate(results, 1):
        output += f"\n{i}. {title}\n   {content[:150]}...\n   {url}\n"
    
    return output

@tool
def count_posts(topic: str = "") -> str:
    """Count blog posts. Input: topic name or empty string for total count."""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    
    if topic:
        cur.execute("""
            SELECT COUNT(*) FROM sql_docs 
            WHERE title ILIKE %s OR content ILIKE %s
        """, (f'%{topic}%', f'%{topic}%'))
        count = cur.fetchone()[0]
        result = f"Found {count} posts about '{topic}'"
    else:
        cur.execute("SELECT COUNT(*) FROM sql_docs")
        count = cur.fetchone()[0]
        result = f"Total: {count} posts"
    
    cur.close()
    conn.close()
    return result

@tool
def list_recent(n: str = "5") -> str:
    """List recent posts. Input: number of posts like '5' or '10'."""
    try:
        limit = int(n)
    except:
        limit = 5
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT title, url, created_at 
        FROM sql_docs 
        ORDER BY created_at DESC 
        LIMIT %s
    """, (limit,))
    
    results = cur.fetchall()
    cur.close()
    conn.close