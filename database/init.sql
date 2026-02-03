-- MUDE AQUI PARA O NOVO NOME
\c ggci_database;

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    primeiro_nome VARCHAR(50) NOT NULL,
    ultimo_nome VARCHAR(50) NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    tentativas_falhas INT DEFAULT 0,
    bloqueio_ate TIMESTAMP DEFAULT NULL,
    bloqueado_permanente BOOLEAN DEFAULT FALSE,
    CONSTRAINT check_email_domain CHECK (email LIKE '%@ovg.org.br')
);

-- Inserindo o admin padrão
INSERT INTO usuarios (primeiro_nome, ultimo_nome, username, email, senha, is_admin)
VALUES ('Administrador', '', 'admin', 'admin@ovg.org.br', '4DMIN_0vg', TRUE)
ON CONFLICT (email) DO NOTHING;