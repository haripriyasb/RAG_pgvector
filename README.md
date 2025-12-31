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

An AI-powered search that lets you ask questions in natural language and find answers based on meaning, not just keywords.
It searches across incidents, runbooks, knowledge bases, and Confluence, and returns concise 2–3 sentence answers with links to the original sources through a simple web UI.


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

### 0. Install Python

- Download and install Python 3.11 or newer from the official website: https://www.python.org/downloads/
- During installation, check the box to "Add Python to PATH".
- Verify installation by running:
  ```
  python --version
  ```
  You should see the installed Python version.

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

### 3. Get Claude API key

1. Sign up at https://console.anthropic.com/
2. Navigate to API Keys
3. Create new key and save it in a secure file
4. This will be needed in .env file

### 4. Set Up PostgreSQL with pgvector

- Download PostgreSQL 3.11 here - https://www.python.org/downloads/
- Ensure you have PostgreSQL installed and running.

```bash
   python setup_db.py
```

 This will create the `ai_learning` database, enable the `pgvector` extension, and set up the `sql_docs` table and indexes.

### 5. Configure Environment Variables

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

### 6. Load Document Files

- These are the loader scripts to ingest documents into the database:
  
  - `load_runbooks.py`: Loads runbook documents.
  - `load_servicenow_mock.py`: Loads mock ServiceNow incidents.
  - `load_microsoft_docs.py`: Loads Microsoft documentation articles.
  

  Run each script:
  ```
  python load_microsoft_docs.py
  python load_runbooks.py
  python load_servicenow_mock.py
  ```
  Verify data loaded:
 
  ```
   psql -U postgres -d ai_learning -c "SELECT source, COUNT(*) FROM sql_docs GROUP BY source;"
  ```


### 6. Run the Application

 ```
  # Example queries:
    # "transaction log growing"
    # "AlwaysOn availability issues"
    # "tempdb performance problems"

  # Run from command line, without web interface:
  
  python agent_app.py
 
  # For the Streamlit web interface:
  
  streamlit run app_conversational.py

  # This opens browser to http://localhost:8501
````





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


