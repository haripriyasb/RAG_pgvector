# RAG Vector Search System  


This project provides a Retrieval-Augmented Generation (RAG) system for searching ServiceNow incidents, runbooks and SQL Server documentation all in one place, using vector search and conversational AI (Claude API).

## Setup Instructions

### 0. Install Python

- Download and install Python 3.11 or newer from the official website: https://www.python.org/downloads/
- During installation, check the box to "Add Python to PATH".
- Verify installation by running:
  ```
  python --version
  ```
  You should see the installed Python version.

### 1. Database Setup

- Download PostgreSQL 3.11 here - https://www.python.org/downloads/
- Ensure you have PostgreSQL installed and running.
  
- Run the database setup script:
  ```
  python setup_db.py
  ```
  This will create the `ai_learning` database, enable the `pgvector` extension, and set up the `sql_docs` table and indexes.

###  2. Configure Environment Variables

Create a `.env` file in the project root:
```env
# Database Configuration
DB_HOST=localhost
DB_NAME=ai_learning
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_PORT=5432

# Claude API Configuration
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
 Set the model name (e.g., `claude-3-5-sonnet-20241022`) as `ANTHROPIC_MODEL` in `.env`.
```
### 3. Get Claude API key

1. Sign up at https://console.anthropic.com/
2. Navigate to API Keys
3. Create new key
4. Copy to `.env` file
   
### 4. Python Environment & Libraries

- Create and activate a Python virtual environment:
  ```
  python -m venv venv
  venv\Scripts\activate
  ```
- Install required libraries:
  ```
  pip install psycopg2-binary pgvector python-dotenv sentence-transformers streamlit anthropic
  ```

### 5. Load Document Files

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

-

### 5. Run the Application

- For the command-line agent:
  ```
  python agent_app.py
  ```
- For the Streamlit web interface:
  ```
  streamlit run app_conversational.py
  ```


