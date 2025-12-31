# RAG Search System with PostgreSQL + pgvector + Claude

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


# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL with pgvector

```bash
   python setup_db.py
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

### Load Sample ServiceNow Incidents and runbooks

```bash
   python load_microsoft_docs.py
   python load_runbooks.py
   python load_servicenow_mock.py
```

The system will:
1. Extract text from documents
2. Generate embeddings using Sentence Transformers
3. Store in PostgreSQL with vector embeddings

## 🎮 Usage

### Command Line Interface

```bash
   # Run CLI agent 
   python agent_app.py


# Example queries:
# "transaction log growing"
# "AlwaysOn availability issues"
# "tempdb performance problems"
```

### Web Interface (Streamlit)

```bash
   # Start the Streamlit app
   streamlit run app_conversational.py


# Open browser to http://localhost:8501
```

### Example Queries

```bash
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
**Read the full blog post:** [Building a RAG Search System](https://gohigh.substack.com) 

## 📝 License

MIT License - Feel free to use this for your own projects!

## 👤 Author

**Haripriya Naidu**
- Blog: [gohigh.substack.com](https://gohigh.substack.com)
- GitHub: [@haripriyasb](https://github.com/haripriyasb)
- Microsoft MVP - Data Platform

---

**Questions or Issues?** Reach out via [Substack](https://gohigh.substack.com)


