import os

# Definição das credenciais do banco
DB_USER = os.getenv("POSTGRES_USER", "4dmin_db")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "4dmin_db")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")
DB_NAME = os.getenv("POSTGRES_DB", "ggci_database")

# String de Conexão (URL)
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"