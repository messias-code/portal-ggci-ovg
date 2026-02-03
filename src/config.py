"""
=============================================================================
MÓDULO DE CONFIGURAÇÃO
=============================================================================
Centraliza as variáveis de ambiente e strings de conexão.
Garante que credenciais não fiquem "hardcoded" no meio do código.
"""
import os

# --- CREDENCIAIS DO BANCO DE DADOS (PostgreSQL) ---
# Tenta pegar das variáveis de ambiente (Docker), senão usa o padrão local
DB_USER = os.getenv("POSTGRES_USER", "4dmin_db")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "4dmin_db")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5433") # Porta externa mapeada no Docker Compose
DB_NAME = os.getenv("POSTGRES_DB", "ggci_database")

# --- STRING DE CONEXÃO (SQLAlchemy) ---
# Formato: postgresql://usuario:senha@host:porta/banco
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"