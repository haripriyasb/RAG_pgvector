# RAG_vectorsearch

A Retrieval-Augmented Generation (RAG) system for semantic and hybrid search across SQL Server documentation, incidents, runbooks, and blog posts. 
Built with Python, Streamlit, PostgreSQL, pgvector and Claude.

## Features
- **Conversational Search UI**: Streamlit web app for multi-source, chat-based search.
- **Semantic & Hybrid Search**: Combines vector similarity (pgvector) and keyword search for best results.
- **Multi-source Knowledge**: Integrates Microsoft Docs, runbooks, ServiceNow incidents, and blogs.
- **Fast Embedding Search**: Uses SentenceTransformers for embeddings and HNSW index for fast retrieval.
- **Loader Scripts**: Scripts to ingest and embed documents from various sources.

## Folder Structure
```
RAG_vectorsearch/
├── agent_app.py               # CLI conversational agent
├── app_conversational.py      # Streamlit web UI
├── load_microsoft_docs.py     # Loader for Microsoft Docs
├── load_runbooks.py           # Loader for runbooks
├── load_servicenow_mock.py    # Loader for ServiceNow incidents
├── setup_db.py                # Database and table setup
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
```

## Quickstart
1. **Clone the repo**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment**
   - Copy `.env` to `RAG_vectorsearch/.env` and set DB/Claude API keys.
4. **Set up the database**
   ```bash
   python setup_db.py
   ```
5. **Load data**
   ```bash
   python load_microsoft_docs.py
   python load_runbooks.py
   python load_servicenow_mock.py
   ```
6. **Run the Streamlit app**
   ```bash
   streamlit run app_conversational.py
   ```
7. **(Optional) Run CLI agent**
   ```bash
   python agent_app.py
   ```

## Requirements
- Python 3.9+
- PostgreSQL 15+ with pgvector extension
- SentenceTransformers
- Streamlit
- anthropic (Claude API)

## Environment Variables (.env)
```
DB_HOST=localhost
DB_NAME=ai_learning
DB_USER=postgres
DB_PASSWORD=password
DB_PORT=5432
ANTHROPIC_API_KEY=sk-...your-key...
```

## Citation
If you use this project, please cite or link to this repository.

---
**Author:** Haripriya 
