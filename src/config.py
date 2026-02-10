"""
=============================================================================
ARQUIVO: config.py (MÓDULO DE CONFIGURAÇÃO)
DESCRIÇÃO:
    Este arquivo centraliza todas as constantes e parâmetros globais do sistema.
    
    CONCEITO DE ENGENHARIA (The 12-Factor App):
    Uma boa aplicação deve ter uma separação estrita entre CÓDIGO e CONFIGURAÇÃO.
    - O Código (lógica) é o mesmo em desenvolvimento, teste e produção.
    - A Configuração (senhas, hosts, portas) muda dependendo de onde o app roda.
    
    POR QUE USAR OS.GETENV?
    Permite que o Docker (ou o Sistema Operacional) injete as configurações 
    de fora para dentro. Se não houver injeção externa, usamos um valor padrão
    (fallback) para que o projeto rode na máquina do desenvolvedor sem travar.
=============================================================================
"""
import os  # Biblioteca para interagir com o Sistema Operacional

# =============================================================================
# CREDENCIAIS DO BANCO DE DADOS (PostgreSQL)
# =============================================================================

# DICA DE SEGURANÇA:
# Jamais deixe senhas reais de produção "hardcoded" (escritas fixas) aqui.
# As strings abaixo ("4dmin_db", etc) são apenas valores padrão para 
# DESENVOLVIMENTO LOCAL. Em produção, isso virá das variáveis de ambiente.

# 1. Usuário do Banco
# Tenta ler a variável 'POSTGRES_USER' do ambiente. Se não achar, usa '4dmin_db'.
DB_USER = os.getenv("POSTGRES_USER", "4dmin_db")

# 2. Senha do Banco
# Tenta ler a variável 'POSTGRES_PASSWORD'. Se não achar, usa '4dmin_db'.
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "4dmin_db")

# 3. Host (Endereço do Servidor)
# 'localhost' funciona se o Python e o Banco estiverem na mesma máquina (sem Docker).
# Se estiver usando Docker Compose, o host geralmente é o nome do serviço (ex: 'db').
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")

# 4. Porta de Conexão
# A porta padrão interna do Postgres é 5432. 
# Aqui usamos 5433 como padrão local, pois muitas vezes a 5432 já está ocupada.
DB_PORT = os.getenv("POSTGRES_PORT", "5433") 

# 5. Nome do Banco de Dados
DB_NAME = os.getenv("POSTGRES_DB", "ggci_database")

# =============================================================================
# STRING DE CONEXÃO (DSN - Data Source Name)
# =============================================================================
# O SQLAlchemy (ORM) precisa de uma URL única para conectar.
# A estrutura padrão é: dialect+driver://username:password@host:port/database

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Debug (Opcional - Apenas para verificar no console se carregou certo)
# print(f"🔧 Configuração de Banco Carregada: {DB_HOST}:{DB_PORT}/{DB_NAME}")