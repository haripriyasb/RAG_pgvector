
import psycopg2
from pgvector.psycopg2 import register_vector
import os
from dotenv import load_dotenv

load_dotenv()

def create_database_if_not_exists():
    # Connect to default 'postgres' database to create ai_learning if needed
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database='postgres',
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'ai_learning'")
    exists = cur.fetchone()
    if not exists:
        print('Creating database ai_learning...')
        cur.execute("""
            CREATE DATABASE ai_learning
                WITH OWNER = postgres
                ENCODING = 'UTF8'
                LC_COLLATE = 'English_United States.1252'
                LC_CTYPE = 'English_United States.1252'
                LOCALE_PROVIDER = 'libc'
                TABLESPACE = pg_default
                CONNECTION LIMIT = -1
                IS_TEMPLATE = False;
        """)
        print('✅ Database ai_learning created!')
    else:
        print('Database ai_learning already exists.')
    cur.close()
    conn.close()

def setup_ai_learning():
    # Connect to ai_learning database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database='ai_learning',
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Enable pgvector extension
    cur.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Register vector type
    register_vector(conn)

    # Create table for documents
    cur.execute('''
        CREATE TABLE IF NOT EXISTS public.sql_docs
        (
            id integer NOT NULL DEFAULT nextval('sql_docs_id_seq'::regclass),
            title text COLLATE pg_catalog."default" NOT NULL,
            content text COLLATE pg_catalog."default" NOT NULL,
            url text COLLATE pg_catalog."default",
            embedding vector(384),
            created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
            source character varying(50) COLLATE pg_catalog."default" DEFAULT 'blog'::character varying,
            CONSTRAINT sql_docs_pkey PRIMARY KEY (id)
        )
        TABLESPACE pg_default;
    ''')

    # Set table owner
    cur.execute('ALTER TABLE IF EXISTS public.sql_docs OWNER to postgres;')

    # Create index on source
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_source
            ON public.sql_docs USING btree
            (source COLLATE pg_catalog."default" ASC NULLS LAST)
            WITH (fillfactor=100, deduplicate_items=True)
            TABLESPACE pg_default;
    ''')

    # Create vector index for similarity search
    cur.execute('''
        CREATE INDEX IF NOT EXISTS sql_docs_embedding_idx
            ON public.sql_docs USING hnsw
            (embedding vector_cosine_ops)
            TABLESPACE pg_default;
    ''')

    print("✅ ai_learning database, table, and indexes are set up!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_database_if_not_exists()
    setup_ai_learning()