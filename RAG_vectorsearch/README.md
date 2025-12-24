# RAG_vectorsearch
RAG Vector Search System  

This project provides a Retrieval-Augmented Generation (RAG) system for searching ServiceNow incidents, runbooks and SQL Server documentation using vector search and conversational AI (Claude API).

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

- Ensure you have PostgreSQL installed and running.
- Create a `.env` file in this folder with your database credentials:
  ```
  DB_HOST=localhost
  DB_NAME=ai_learning
  DB_USER=postgres
  DB_PASSWORD=yourpassword
  DB_PORT=5432
  ANTHROPIC_API_KEY=your_claude_api_key
  ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
  ```
- Run the database setup script:
  ```
  python setup_db.py
  ```
  This will create the `ai_learning` database, enable the `pgvector` extension, and set up the `sql_docs` table and indexes.

### 2. Python Environment & Libraries

- Create and activate a Python virtual environment (recommended):
  ```
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```
- Install required libraries:
  ```
  pip install psycopg2-binary pgvector python-dotenv sentence-transformers streamlit anthropic
  ```

### 3. Load Document Files

- Use the loader scripts to ingest documents into the database:
  - `load_microsoft_docs.py`: Loads Microsoft documentation articles.
  - `load_runbooks.py`: Loads runbook documents.
  - `load_servicenow_mock.py`: Loads mock ServiceNow incidents.

  Run each script as needed:
  ```
  python load_microsoft_docs.py
  python load_runbooks.py
  python load_servicenow_mock.py
  ```

### 4. Setup Claude API

- Get your Claude API key from Anthropic and add it to your `.env` file as `ANTHROPIC_API_KEY`.
- Set the model name (e.g., `claude-3-5-sonnet-20241022`) as `ANTHROPIC_MODEL` in `.env`.

### 5. Run the Application

- For the command-line agent:
  ```
  python agent_app.py
  ```
- For the Streamlit web interface:
  ```
  streamlit run app_conversational.py
  ```

## Notes
- Do NOT commit your `.env` file to git (contains secrets).
- The archive folder is ignored by git and contains old scripts for reference.
- For troubleshooting, check your database connection and API keys.

---

For questions or issues, contact the project maintainer.
