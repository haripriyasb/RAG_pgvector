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
print("[OK] Claude API connected\n")

# ============================================
# TOOLS (using @tool decorator)
# ============================================

@tool
def search_blog(query: str) -> str:
    """Search blog posts for relevant content. Input should be a search query like 'SQL Server performance' or 'RCSI'."""
    
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
        return "No relevant blog posts found."
    
    output = "Found these blog posts:\n\n"
    for i, (title, content, url) in enumerate(results, 1):
        output += f"{i}. {title}\n"
        output += f"   Summary: {content[:200]}...\n"
        output += f"   URL: {url}\n\n"
    
    return output

@tool
def count_posts(topic: str = "") -> str:
    """Count blog posts. Input can be a topic (e.g. 'RCSI') or leave empty for total count."""
    
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
            SELECT COUNT(*) 
            FROM sql_docs 
            WHERE title ILIKE %s OR content ILIKE %s
        """, (f'%{topic}%', f'%{topic}%'))
        count = cur.fetchone()[0]
        result = f"Found {count} blog posts about '{topic}'."
    else:
        cur.execute("SELECT COUNT(*) FROM sql_docs")
        count = cur.fetchone()[0]
        result = f"Total blog posts: {count}"
    
    cur.close()
    conn.close()
    return result

@tool
def list_recent(limit: str = "5") -> str:
    """List recent blog posts. Input should be number of posts like '5' or '10'."""
    
    try:
        limit_int = int(limit)
    except:
        limit_int = 5
    
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
    """, (limit_int,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    if not results:
        return "No posts found."
    
    output = f"Most recent {len(results)} posts:\n\n"
    for i, (title, url, created_at) in enumerate(results, 1):
        output += f"{i}. {title}\n   Date: {created_at}\n   URL: {url}\n\n"
    
    return output

@tool
def get_stats() -> str:
    """Get blog statistics: total posts, date range, and top topics. No input needed."""
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM sql_docs")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT MIN(created_at), MAX(created_at) FROM sql_docs")
    min_date, max_date = cur.fetchone()
    
    cur.execute("SELECT title FROM sql_docs")
    titles = [row[0].lower() for row in cur.fetchall()]
    
    keywords = {
        'sql server': 0, 'performance': 0, 'index': 0, 
        'query': 0, 'tempdb': 0, 'rcsi': 0, 
        'mvp': 0, 'career': 0, 'postgresql': 0
    }
    
    for title in titles:
        for keyword in keywords:
            if keyword in title:
                keywords[keyword] += 1
    
    top_topics = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
    
    cur.close()
    conn.close()
    
    output = f"📊 Blog Statistics:\n\n"
    output += f"Total Posts: {total}\n"
    output += f"Date Range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}\n\n"
    output += f"Top Topics:\n"
    for topic, count in top_topics:
        if count > 0:
            output += f"  • {topic.title()}: {count} posts\n"
    
    return output

# ============================================
# Create Agent
# ============================================

tools = [search_blog, count_posts, list_recent, get_stats]

template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

prompt = PromptTemplate.from_template(template)

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5
)

# ============================================
# Interactive Loop
# ============================================

if __name__ == "__main__":
    print("=" * 70)
    print("   Blog Agent - Conversational AI with Multiple Tools")
    print("=" * 70)
    print("\nThe agent can:")
    print("  1. Search blog posts by topic")
    print("  2. Count posts about specific topics")
    print("  3. List recent posts")
    print("  4. Provide blog statistics")
    print("\nTry asking:")
    print("  - 'How many posts do I have about RCSI?'")
    print("  - 'Search for performance optimization'")
    print("  - 'Show me my 5 most recent posts'")
    print("  - 'What are my blog statistics?'")
    print("=" * 70)
    print()
    
    while True:
        print("\n" + "-" * 70)
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not user_input:
            continue
        
        print("\n🤖 Agent is thinking...\n")
        
        try:
            response = agent_executor.invoke({"input": user_input})
            print(f"\n✅ Agent: {response['output']}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()