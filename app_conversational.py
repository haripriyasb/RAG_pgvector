# Web interface for conversational search
import streamlit as st
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic
import os
from dotenv import load_dotenv
import httpx

load_dotenv()

# Page config
st.set_page_config(
    page_title="Haripriya's Blog Search",
    page_icon="💬",
    layout="wide"
)

# Load models (cached)
@st.cache_resource
def load_models():
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    # Fix proxy issue by providing custom httpx client
    try:
        claude_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    except TypeError:
        claude_client = Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            http_client=httpx.Client()
        )
    return sentence_model, claude_client

sentence_model, claude_client = load_models()

# Search function
# Search function with hybrid search (semantic + keyword)
def search_docs(query, limit=6):
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    register_vector(conn)
    cur = conn.cursor()
    
    # Extract keywords - preserve technical terms
    keywords = query.lower().split()
    stop_words = {'any', 'the', 'and', 'or', 'have', 'we', 'seen', 'about', 'with', 'for', 'from', 'recently', 'latest', 'show', 'me', 'get', 'find', 'how', 'many', 'what', 'when', 'where', 'why', 'is', 'are', 'be', 'been', 'do', 'does', 'dont', 'can', 'could', 'should', 'would', 'may', 'might', 'must', 'will', 'shall', 'in', 'on', 'at', 'to', 'by', 'as', 'of', 'if', 'that', 'this', 'it', 'it\'s', 'you', 'we', 'they', 'them', 'their', 'your', 'our'}
    keywords = [k.strip('?,;:.!') for k in keywords if k.strip('?,;:.!') not in stop_words and len(k) > 2]
    
    # DEBUG
    print(f"DEBUG: Query: {query}")
    print(f"DEBUG: Keywords extracted: {keywords}")
    
    results_dict = {}
    
    # Semantic search
    query_embedding = sentence_model.encode(query).tolist()
    
    cur.execute('''
        SELECT title, content, url, source,
               1 - (embedding <=> %s::vector) as similarity
        FROM sql_docs
        ORDER BY embedding <=> %s::vector
        LIMIT 10
    ''', (query_embedding, query_embedding))
    
    semantic_results = cur.fetchall()
    
    print(f"DEBUG: Semantic results count: {len(semantic_results)}")
    for title, _, _, source, sim in semantic_results[:3]:
        print(f"  - {source}: {title[:50]}... (sim: {sim:.2f})")
    
    for title, content, url, source, similarity in semantic_results:
        results_dict[url] = {
            'title': title,
            'content': content,
            'url': url,
            'source': source,
            'similarity': float(similarity),
            'method': 'semantic'
        }
    
    # Keyword search - prioritize documents that match keywords
    if keywords:
        keyword_conditions = []
        for keyword in keywords[:3]:
            keyword_conditions.append(f"(title ILIKE '%{keyword}%' OR content ILIKE '%{keyword}%')")
        
        if keyword_conditions:
            keyword_query = f"""
                SELECT title, content, url, source,
                       1.0 as similarity
                FROM sql_docs
                WHERE {' OR '.join(keyword_conditions)}
                LIMIT 15
            """
            
            print(f"DEBUG: Keyword query: {keyword_query}")
            
            cur.execute(keyword_query)
            keyword_results = cur.fetchall()
            
            print(f"DEBUG: Keyword results count: {len(keyword_results)}")
            for title, _, _, source, _ in keyword_results[:3]:
                print(f"  - {source}: {title[:50]}...")
            
            # Prioritize keyword matches over pure semantic
            for title, content, url, source, _ in keyword_results:
                if url in results_dict:
                    results_dict[url]['similarity'] = 1.0  # Boost to 1.0 if keyword matched
                    results_dict[url]['method'] = 'keyword-match'
                else:
                    results_dict[url] = {
                        'title': title,
                        'content': content,
                        'url': url,
                        'source': source,
                        'similarity': 1.0,  # Keyword matches get highest priority
                        'method': 'keyword'
                    }
    
    cur.close()
    conn.close()
    
    sorted_results = sorted(results_dict.values(), key=lambda x: x['similarity'], reverse=True)
    
    # Diversify by source - get at least one from each source type
    final_results = []
    urls_used = set()
    sources_used = set()
    
    # First pass: take best match from each source type
    for r in sorted_results:
        if r['source'] not in sources_used:
            final_results.append(r)
            urls_used.add(r['url'])
            sources_used.add(r['source'])
    
    # Fill remaining slots with best overall matches
    for r in sorted_results:
        if len(final_results) >= limit:
            break
        if r['url'] not in urls_used:
            final_results.append(r)
            urls_used.add(r['url'])
    
    print(f"DEBUG: Final results count: {len(final_results)}")
    for r in final_results:
        print(f"  - {r['source']}: {r['title'][:50]}... ({r['similarity']:.2f}, {r['method']})")
    
    return [(r['title'], r['content'], r['url'], r['source'], r['similarity']) for r in final_results]


# Ask Claude
def ask_claude(question, results):
    # Map source to label
    source_labels = {
        'blog': '📚 Blog Post',
        'documentation': '📗 Runbook',
        'microsoft': '📘 Microsoft Docs',
        'servicenow': '🎫 ServiceNow Incident'
    }
    
    context = "\n\n---\n\n".join([
        f"{source_labels.get(source, source)}: {title}\n\nContent: {content}\n\nURL: {url}"
        for title, content, url, source, _ in results
    ])
    
    prompt = f"""You are a helpful SQL Server expert. Answer the user's question based on these resources.

RESOURCES:
{context}

QUESTION: {question}

Keep your answer to 2-3 sentences max. Be concise and direct. End with "Elaborate?" if more detail would help."""

    message = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return message.content[0].text

# UI
st.title("⭐ Incident & Knowledge Search")
st.markdown("""
**Multi-source RAG search** across incidents, blog posts, and runbooks

📊 Powered by pgvector, Claude API""")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "example_clicked" not in st.session_state:
    st.session_state.example_clicked = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle example button clicks
if st.session_state.example_clicked:
    prompt = st.session_state.example_clicked
    st.session_state.example_clicked = None  # Reset
else:
    prompt = None

# Chat input
if user_input := st.chat_input("Ask a question about SQL Server..."):
    prompt = user_input

if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Searching resources and thinking..."):
            # Search
            results = search_docs(prompt)
            
            # Show which resources were found
            with st.expander("📚 Found relevant resources"):
                source_labels = {
                    'blog': '📚 Blog Post',
                    'microsoft': '📘 Microsoft Docs',
                    'servicenow': '🎫 ServiceNow Incident'
                }
                
                for title, _, url, source, similarity in results:
                    label = source_labels.get(source, source)
                    st.markdown(f"- **{label}**: {title} (relevance: {similarity:.1%}) - [Read]({url})")
            
            # Get answer from Claude
            answer = ask_claude(prompt, results)
            st.markdown(answer)
            
            # Show sources with URLs
            st.markdown("---")
            st.markdown("**📖 Sources:**")
            for title, _, url, source, _ in results:
                source_labels = {
                    'blog': '📚',
                    'microsoft': '📘',
                    'servicenow': '🎫'
                }
                icon = source_labels.get(source, '📄')
                st.markdown(f"{icon} [{title}]({url})")
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": answer})

# Sidebar
with st.sidebar:
    st.markdown("## 📊 Data Sources")
    st.markdown("""
    - **📚 Knowledge Base** (66 articles)
    - **📗 Runbooks** (7 documents)
    - **📘 Microsoft Docs** (14 articles)
    - **🎫 ServiceNow** (17 incidents/RCAs)
    """)
    
    st.divider()
    
    st.markdown("## 💡 Example Queries")
    
    st.markdown("### 🎫 Incident Troubleshooting")
    incident_examples = [
        "How many times have we had tempdb issues?",
        "Show me past incidents about high CPU",
        "Have we seen deadlock issues before?",
        "What was the Always On failover incident?"
    ]
    
    for i, example in enumerate(incident_examples):
        if st.button(example, key=f"example_{i}", use_container_width=True):
            st.session_state.example_clicked = example
    
    st.markdown("### 📚 Blog Search")
    blog_examples = [
        "How do I optimize SQL Server?",
        "What is RCSI and when should I use it?",
        "How do I troubleshoot slow queries?",
        "Explain tempdb optimization",
        "What are the best practices for indexes?"
    ]
    
    for i, example in enumerate(blog_examples):
        if st.button(example, key=f"blog_example_{i}", use_container_width=True):
            st.session_state.example_clicked = example
    
    st.divider()
    
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    st.caption("Powered by Claude Sonnet 4 + pgvector")