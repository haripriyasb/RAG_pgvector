# RAG Search System with PostgreSQL + pgvector

A smart semantic search system for internal documentation, incident tickets, runbooks, and knowledge base articles using RAG (Retrieval-Augmented Generation) architecture.

**Read the full blog post:** [Building a RAG Search System](https://gohigh.substack.com) 

## 🎯 Problem Statement

On-call engineers often face the challenge of finding solutions to recurring incidents. Information is scattered across:
- ServiceNow tickets
- Teams messages  
- Emails
- Confluence documentation
- RCA reports

This system eliminates the need to hunt through multiple systems by providing instant, conversational access to your incident history and internal documentation.

## ✨ Features

- **Semantic Search**: Find relevant documents based on meaning, not just keywords
- **Conversational AI**: Ask questions in natural language and get contextual answers
- **Multi-Source Integration**: Search across incident tickets, runbooks, knowledge base articles, and Confluence docs
- **Concise Responses**: Get 2-3 sentence answers first, with option to elaborate
- **Source Attribution**: Direct links to original documentation
- **Web Interface**: Clean Streamlit UI for easy interaction

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Vector Database** | PostgreSQL + pgvector extension |
| **Embeddings** | Sentence Transformers (all-MiniLM-L6-v2) |
| **LLM** | Claude API (Anthropic) |
| **Web Interface** | Streamlit |
| **Language** | Python 3.8+ |
| **Database Adapter** | psycopg2 |

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL 12+ (with pgvector extension)
- Claude API key ([Get one here](https://console.anthropic.com))
- Basic understanding of SQL and Python

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/haripriyasb/RAG_pgvector.git
cd RAG_pgvector/RAG_vectorsearch
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL with pgvector

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE vector_search;

-- Connect to the database
\c vector_search

-- Enable pgvector extension
CREATE EXTENSION vector;

-- Create table for documents
CREATE TABLE public.sql_docs
(
    id SERIAL PRIMARY KEY,
    title text NOT NULL,
    content text NOT NULL,
    url text,
    source text,
    embedding vector(384)
);

-- Create HNSW index for faster similarity search
CREATE INDEX sql_docs_embedding_idx
    ON public.sql_docs USING hnsw
    (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vector_search
DB_USER=postgres
DB_PASSWORD=your_password

# Claude API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key

# Embedding Model Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
```

## 📊 Loading Data

### Load Sample ServiceNow Incidents

```bash
python load_servicenow_mock.py
```

### Load Your Own Documents

Modify the data loading scripts to point to your:
- ServiceNow incident exports (JSON/CSV)
- Confluence page exports (HTML/Markdown)
- Runbook documents (PDF/TXT/Markdown)
- RCA reports (TXT/DOCX)

The system will:
1. Extract text from documents
2. Generate embeddings using Sentence Transformers
3. Store in PostgreSQL with vector embeddings

## 🎮 Usage

### Command Line Interface

```bash
# Run the search from command line
python search_cli.py

# Example queries:
# "transaction log growing"
# "AlwaysOn availability issues"
# "tempdb performance problems"
```

### Web Interface (Streamlit)

```bash
# Start the Streamlit app
streamlit run app.py

# Open browser to http://localhost:8501
```

### Example Queries

```
Q: "Any incidents on AlwaysOn?"
A: There was an incident on Nov 15 where the AlwaysOn replica went into 
   "Not Synchronizing" state. Root cause was network latency between replicas. 
   Mitigated by increasing the session timeout value.
   [ServiceNow Link]

Q: "How many times have we had tempdb issues?"
A: There were 6 tempdb-related incidents:
   - 3 for tempdb full issues
   - 2 for tempdb contention
   - 1 for version store growth
   [See all ServiceNow links]

Q: "How is DR environment setup for SQLPROD01?"
A: SQLPROD01 uses log shipping to DR site with 15-minute RPO. 
   Primary: East datacenter, Secondary: West datacenter.
   Automatic failover is not configured.
   [Link to DR runbook]
```

## 📁 Project Structure

```
RAG_vectorsearch/
├── app.py                      # Streamlit web interface
├── search_cli.py               # Command-line search interface
├── load_servicenow_mock.py     # Load sample incident data
├── load_confluence.py          # Load confluence documents
├── load_runbooks.py            # Load runbook documents
├── config.py                   # Configuration management
├── embeddings/
│   └── encoder.py             # Sentence transformer embedding logic
├── database/
│   ├── connection.py          # PostgreSQL connection
│   └── vector_ops.py          # Vector similarity operations
├── llm/
│   └── claude_client.py       # Claude API integration
├── requirements.txt           # Python dependencies
└── .env.example              # Example environment variables
```

## 🔧 How It Works

### Architecture Overview

```
User Query
    ↓
1. RETRIEVAL
   Query → Sentence Transformer → Query Embedding (384 dimensions)
   PostgreSQL + pgvector searches for similar document embeddings
   Returns top 5 most relevant documents
    ↓
2. AUGMENTATION  
   Query + Retrieved Documents → Formatted Prompt for Claude
    ↓
3. GENERATION
   Claude API generates natural language response
   Includes source attribution
    ↓
Final Response to User
```

### Semantic Search Explained

Traditional keyword search:
```
Query: "performance"
Matches: Only documents with exact word "performance"
```

Semantic search with pgvector:
```
Query: "performance" 
Embedding: [0.234, -0.891, 0.456, ...]

Matches documents with embeddings for:
- "optimization" 
- "tuning"
- "speed improvements"
- Related concepts, not just exact keywords
```

### Vector Similarity Search Query

```sql
SELECT title, content, url, 
       1 - (embedding <=> %s::vector) as similarity
FROM sql_docs
ORDER BY embedding <=> %s::vector
LIMIT 5;
```

**Key operators:**
- `<=>` : Cosine distance operator (smaller = more similar)
- `1 - distance` : Convert to similarity score (higher = more relevant)
- `vector_cosine_ops` : Use cosine similarity for text embeddings

## 💡 Customization

### Using Different Embedding Models

```python
# In config.py, change the model:
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"  # 768 dimensions
# or
EMBEDDING_MODEL = "sentence-transformers/paraphrase-MiniLM-L6-v2"  # 384 dimensions

# Remember to update the table schema:
ALTER TABLE sql_docs ALTER COLUMN embedding TYPE vector(768);
```

### Adjusting HNSW Index Parameters

```sql
-- For larger datasets (>100K documents)
CREATE INDEX sql_docs_embedding_idx
    ON public.sql_docs USING hnsw
    (embedding vector_cosine_ops)
    WITH (m = 32, ef_construction = 128);

-- m = neighbors per layer (higher = better recall, slower build)
-- ef_construction = candidates explored during build (higher = better quality, slower)
```

### Using Different LLMs

Replace Claude API with:
- **OpenAI**: Use `openai` Python SDK
- **Local LLMs**: Use Ollama, llama.cpp
- **Other APIs**: Gemini, Mistral, etc.

## 💰 Cost Considerations

**Claude API Costs** (as of January 2025):
- Claude Haiku: ~$0.25 per 1M input tokens
- Claude Sonnet: ~$3 per 1M input tokens

**For this demo:**
- Embedding generation: FREE (local Sentence Transformers)
- Vector storage: FREE (PostgreSQL)
- LLM calls: ~$0.50-2.00 for extensive testing (100+ queries)

**Note:** Claude API does not use your data for model training.

## 🔒 Security Considerations

⚠️ **Important Security Notes:**

1. **API Keys**: Never commit `.env` file to Git
2. **Sensitive Data**: This demo uses mock data. For production:
   - Ensure Claude API meets your compliance requirements
   - Consider on-premise LLMs for highly sensitive data
   - Implement proper access controls
3. **Database**: Use encrypted connections for production
4. **SQL Injection**: All queries use parameterized statements

## 📈 Performance Optimization

### For Large Document Collections (>10K docs)

1. **Increase HNSW parameters:**
   ```sql
   WITH (m = 32, ef_construction = 128)
   ```

2. **Tune search parameters:**
   ```sql
   SET hnsw.ef_search = 100;  -- Default is 40
   ```

3. **Use connection pooling:**
   ```python
   from psycopg2 import pool
   connection_pool = pool.SimpleConnectionPool(1, 20, dsn)
   ```

4. **Batch embed documents:**
   ```python
   # Instead of encoding one at a time
   embeddings = model.encode(batch_texts, batch_size=32)
   ```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

Areas for improvement:
- Support for more document formats (DOCX, Excel)
- Advanced chunking strategies
- Hybrid search (keyword + semantic)
- Re-ranking algorithms
- Multi-language support
- Evaluation metrics

## 📚 Resources

### Learning Materials
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Sentence Transformers](https://www.sbert.net/)
- [Claude API Docs](https://docs.anthropic.com)
- [RAG Guide](https://www.promptingguide.ai/research/rag)
- [HNSW Algorithm](https://www.pinecone.io/learn/series/faiss/hnsw/)

### Related Blog Posts
- **Full Tutorial**: [Read on Substack](https://gohigh.substack.com)

### API Resources
- [Claude API Console](https://console.anthropic.com)
- [Check API Credits](https://console.anthropic.com/settings/billing)
- [View API Logs](https://console.anthropic.com/logs)

## 📝 License

MIT License - Feel free to use this for your own projects!

## 👤 Author

**Haripriya Naidu**
- Blog: [gohigh.substack.com](https://gohigh.substack.com)
- GitHub: [@haripriyasb](https://github.com/haripriyasb)
- Microsoft MVP - Data Platform

## 🙏 Acknowledgments

- Anthropic for Claude API
- Hugging Face for Sentence Transformers
- pgvector team for the excellent PostgreSQL extension
- Streamlit for the web framework

---

**Questions or Issues?** Open an issue on GitHub or reach out via [Substack](https://gohigh.substack.com)

⭐ If you find this useful, please star the repository!
