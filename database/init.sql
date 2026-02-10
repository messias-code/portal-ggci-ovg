/*
=============================================================================
ARQUIVO: init.sql
DESCRIÇÃO: Script de Inicialização (Bootstrap) do Banco de Dados.

CONTEXTO DOCKER:
Este arquivo é mapeado para dentro do container na pasta:
/docker-entrypoint-initdb.d/

O PostgreSQL executa automaticamente qualquer .sql nesta pasta na primeira
vez que o volume é criado.
=============================================================================
*/

-- 1. CONEXÃO AO BANCO CORRETO
-- Garante que estamos criando as tabelas dentro do banco 'ggci_database'
-- definido no docker-compose.yml (POSTGRES_DB).
\c ggci_database;

-- 2. CRIAÇÃO DA TABELA DE USUÁRIOS
-- Estrutura robusta com constraints de segurança.
CREATE TABLE IF NOT EXISTS usuarios (
    -- Identificador único auto-incrementável (1, 2, 3...)
    id SERIAL PRIMARY KEY,

    -- Dados Pessoais
    primeiro_nome VARCHAR(50) NOT NULL,
    ultimo_nome VARCHAR(50) NOT NULL,
    
    -- Dados de Login
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE, -- UNIQUE impede e-mails duplicados
    
    -- SEGURANÇA:
    -- Em produção real, armazenaríamos o HASH da senha (ex: bcrypt), nunca o texto plano.
    -- Para este projeto interno, usaremos texto plano, mas validado por Regex no Python.
    senha VARCHAR(255) NOT NULL,
    
    -- Controle de Acesso (RBAC Simplificado)
    is_admin BOOLEAN DEFAULT FALSE,

    -- SISTEMA DE STRIKES (Proteção contra Brute-Force):
    -- Estas colunas permitem que o Python controle quantas vezes o usuário errou
    -- e por quanto tempo ele deve ficar bloqueado.
    tentativas_falhas INT DEFAULT 0,
    bloqueio_ate TIMESTAMP DEFAULT NULL,
    bloqueado_permanente BOOLEAN DEFAULT FALSE,

    -- REGRA DE NEGÓCIO (CONSTRAINT):
    -- O banco rejeitará qualquer inserção de e-mail que não seja corporativo.
    -- Isso é uma camada extra de segurança caso o Python falhe.
    CONSTRAINT check_email_domain CHECK (email LIKE '%@ovg.org.br')
);

-- 3. SEED (SEMEADURA) DO ADMIN MESTRE
-- Inserimos o primeiro usuário para que o sistema não nasça "vazio".
-- A senha '4DMIN_0vg' atende aos requisitos do Regex (Maiúscula, Número, Símbolo).
INSERT INTO usuarios (primeiro_nome, ultimo_nome, username, email, senha, is_admin)
VALUES ('Administrador', 'Sistema', 'admin', 'admin@ovg.org.br', '4DMIN_0vg', TRUE)
ON CONFLICT (email) DO NOTHING; -- Se já existir (container reiniciado), não faz nada.