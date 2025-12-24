import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize models
print("Loading models...")
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
claude_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
print("✅ Models loaded!\n")

def search_docs(query, limit=3):
    """Search for relevant blog posts"""
    
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
    
    # Generate query embedding
    query_embedding = sentence_model.encode(query).tolist()
    
    # Search for similar documents
    cur.execute('''
        SELECT title, content, url, 
               1 - (embedding <=> %s::vector) as similarity
        FROM sql_docs
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    ''', (query_embedding, query_embedding, limit))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return results

def ask_claude(question, blog_posts):
    """Ask Claude to answer using blog posts as context"""
    
    # Format blog posts as context
    context = "\n\n---\n\n".join([
        f"Blog Post Title: {title}\n\nContent: {content}\n\nURL: {url}"
        for title, content, url, _ in blog_posts
    ])
    
    # Create prompt for Claude
    prompt = f"""You are a helpful SQL Server expert assistant. Answer the user's question based on the following blog posts from Haripriya's SQL Server blog.

BLOG POSTS:
{context}

USER QUESTION: {question}

Please provide a helpful answer based on the blog posts above. If the blog posts contain relevant information, use it to answer. If they don't fully answer the question, say so and provide what information is available. Include references to specific blog posts when relevant."""

    # Call Claude API
    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text

def conversational_search(question):
    """Main function: Search + Generate answer"""
    
    print(f"🔍 Searching for: {question}\n")
    
    # Step 1: Search blog posts
    blog_posts = search_docs(question, limit=3)
    
    if not blog_posts:
        return "I couldn't find any relevant blog posts for that question."
    
    print(f"📚 Found {len(blog_posts)} relevant posts:")
    for i, (title, _, _, similarity) in enumerate(blog_posts, 1):
        print(f"   {i}. {title} (similarity: {similarity:.2%})")
    
    print("\n🤖 Generating answer with Claude...\n")
    
    # Step 2: Ask Claude to answer
    answer = ask_claude(question, blog_posts)
    
    return answer

# Interactive mode
if __name__ == "__main__":
    print("=" * 70)
    print("   SQL Server Blog - Conversational Q&A (Powered by Claude)")
    print("=" * 70)
    print()
    
    conversation_history = []
    
    while True:
        print("\n" + "-" * 70)
        question = input("💬 Ask a question (or 'quit' to exit): ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
            
        if not question:
            print("⚠️  Please enter a question.")
            continue
        
        print()
        
        # Get answer
        answer = conversational_search(question)
        
        # Display answer
        print("🎯 ANSWER:")
        print("-" * 70)
        print(answer)
        print("-" * 70)
        
        # Save to history
        conversation_history.append({
            'question': question,
            'answer': answer
        })