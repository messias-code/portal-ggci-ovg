# 🏛️ Portal GGCI - Gerência de Gestão e Controle de Informações

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)![Dash](https://img.shields.io/badge/dash-000000?style=for-the-badge&logo=plotly&logoColor=white)![Docker](https://img.shields.io/badge/docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)![PostgreSQL](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)

> **Central Unificada de Ferramentas e Dados.** > Este projeto é uma aplicação *Full Stack* em Python projetada para automatizar rotinas administrativas, padronizar dados e gerenciar acessos de forma segura e escalável.

---

## 🚀 Funcionalidades Principais

### 🔐 **Segurança & Gestão**
* **Autenticação Robusta:** Sistema de login com proteção contra *Brute-Force* (bloqueio temporário e permanente).
* **Controle de Acesso (RBAC):** Painel administrativo exclusivo para gestão de usuários (CRUD completo).
* **Auditabilidade:** Logs de tentativas de falha e gestão de sessões.

### 🛠️ **Ferramentas Utilitárias**
* **Formatador de Listas SQL:** Limpa e formata listas brutas do Excel para uso em cláusulas `IN (...)` do SQL.
* **Normalizador de Dados (IES):** Padroniza nomes de instituições, remove acentos e caracteres especiais via Regex.
* **Análise de Contratos (IA):** *[Em Desenvolvimento]* Módulo para extração automática de dados contratuais.

### 📊 **Visualização**
* **Dashboards Interativos:** Gráficos dinâmicos usando Plotly Dash.
* **Interface Moderna:** Layout responsivo baseado em Bootstrap 5 (Dark Theme).

---

## 🏗️ Arquitetura do Projeto

O projeto segue uma arquitetura modular, separando responsabilidades de infraestrutura, dados e interface.

```plaintext
PORTAL-GGCI/
│
├── 📂 database/              # Scripts de Inicialização do Banco
│   └── init.sql              # Cria tabelas e Admin padrão ao subir o Docker
│
├── 📂 src/                   # Código Fonte da Aplicação
│   ├── __init__.py           # Torna a pasta um pacote Python
│   ├── config.py             # Variáveis de Ambiente e Conexão (12-Factor App)
│   ├── database.py           # Camada de Dados (CRUD e Regras de Negócio)
│   ├── layouts.py            # Camada Visual (Front-end Dash)
│   └── utils.py              # Funções auxiliares e Validações (Regex)
│
├── .gitignore                # Arquivos ignorados pelo Git
├── app.py                    # Entry Point (Roteamento e Server)
├── docker-compose.yml        # Orquestração do Banco de Dados
├── README.md                 # Documentação do Projeto
└── requirements.txt          # Dependências do Python

```

---

## ⚡ Guia de Instalação (Passo a Passo)

### 1. Pré-requisitos

* **Python 3.10+** instalado.
* **Docker Desktop** (ou Engine) instalado e rodando.
* *(Opcional)* Git para clonar o repositório.

### 2. Clonar o Repositório

```bash
git clone https://seu-repositorio/portal-ggci.git
cd portal-ggci

```

### 3. Subir o Banco de Dados (Docker) 🐳

Não é necessário instalar o PostgreSQL na sua máquina. Usamos Docker para garantir que todos tenham o mesmo ambiente.

```bash
docker-compose up -d

```

> **Nota:** Na primeira execução, o script `database/init.sql` será rodado automaticamente, criando a tabela `usuarios` e o usuário **Admin**.

### 4. Configurar Ambiente Python 🐍

Recomendamos usar um ambiente virtual (`venv`) para isolar as dependências.

**Windows:**

```powershell
python -m venv venv
.\venv\Scripts\activate

```

**Linux / Mac / WSL:**

```bash
python3 -m venv venv
source venv/bin/activate

```

### 5. Instalar Dependências

```bash
pip install -r requirements.txt

```

---

## ▶️ Como Rodar

Com o banco de dados rodando (passo 3) e o ambiente ativado (passo 4), execute:

```bash
python app.py

```

### 🌐 Acesso ao Portal

Abra seu navegador e acesse:

* **URL:** `http://localhost:8050` (ou 8051 se estiver no WSL)

### 🔑 Credenciais Padrão (Primeiro Acesso)

O sistema já nasce com um super-usuário criado via SQL:

| Usuário | Senha | Perfil |
| --- | --- | --- |
| **admin** | `4DMIN_0vg` | Administrador |

> ⚠️ **Importante:** Altere esta senha imediatamente após o primeiro login ou crie um novo usuário administrador.

---

## 🔧 Detalhes Técnicos Importantes

### Automação de Rede (WSL 🐧)

Se você desenvolve usando **WSL 2 (Windows Subsystem for Linux)**, sabe que acessar o `localhost` do Linux pelo Windows pode ser complicado.

O arquivo `app.py` possui um script inteligente (`configurar_rede_automatica`) que detecta se está rodando no WSL e configura automaticamente o **Port Proxy** do Windows via PowerShell.

* **Benefício:** Permite que colegas na mesma rede Wi-Fi acessem seu portal localmente para testes.

### Banco de Dados (Portas)

* **Interna (Docker):** 5432
* **Externa (Host):** 5433 (Para evitar conflito com Postgres local)
* **Conexão:** Definida em `src/config.py` via Variáveis de Ambiente.

---

## 🤝 Contribuindo

1. Crie uma Branch para sua feature (`git checkout -b feature/nova-ferramenta`).
2. Mantenha o padrão de código (comentários e docstrings).
3. Teste as validações de segurança em `utils.py`.
4. Abra um Pull Request.