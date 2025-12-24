import psycopg2
from pgvector.psycopg2 import register_vector
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=os.getenv('DB_PORT')
)

# Enable pgvector extension
cur = conn.cursor()
cur.execute('CREATE EXTENSION IF NOT EXISTS vector')
conn.commit()

# Register vector type
register_vector(conn)

# Create table for documents
cur.execute('''
    CREATE TABLE IF NOT EXISTS sql_docs (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        url TEXT,
        embedding vector(1536),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
print("✅ Database setup complete!")

# Create index for similarity search
cur.execute('''
    CREATE INDEX IF NOT EXISTS sql_docs_embedding_idx 
    ON sql_docs 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
''')

conn.commit()
print("✅ Vector index created!")

cur.close()
conn.close()