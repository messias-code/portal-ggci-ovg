"""
=============================================================================
ARQUIVO: database.py (CAMADA DE DADOS)
DESCRIÇÃO:
    Este módulo atua como a 'Camada de Acesso a Dados' (DAL).
    
    RESPONSABILIDADES:
    1. Gerenciar a conexão com o banco PostgreSQL (via SQLAlchemy).
    2. Executar operações CRUD (Create, Read, Update, Delete).
    3. Aplicar regras de negócio críticas, como bloqueio de contas por 
       tentativas falhas de login.
    
    SEGURANÇA (SQL INJECTION):
    Observe que todas as queries SQL utilizam a sintaxe de parâmetros (:param).
    NUNCA concatenamos strings diretamente no SQL (ex: f"SELECT... {variavel}"),
    pois isso permitiria ataques de injeção de SQL.
=============================================================================
"""
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta

# Importa configurações e utilitários locais
from .config import DATABASE_URL
from .utils import validar_requisitos_senha

# --- CONFIGURAÇÃO DO MOTOR DE BANCO DE DADOS ---
# O 'engine' é o objeto central do SQLAlchemy. Ele gerencia um "Pool de Conexões".
# Em vez de abrir e fechar uma conexão nova para cada consulta (o que é lento),
# o pool mantém algumas conexões abertas e as reutiliza.
engine = create_engine(DATABASE_URL)

# =============================================================================
# SEÇÃO 1: AUTENTICAÇÃO E SEGURANÇA
# =============================================================================

def autenticar_usuario(username, password):
    """
    Realiza o login do usuário aplicando regras estritas de segurança (Brute-force protection).
    
    LÓGICA DE BLOQUEIO (STRIKE SYSTEM):
    Para evitar que hackers tentem adivinhar senhas infinitamente, aplicamos punições:
    - 5 erros seguidos: Bloqueio leve (10 minutos).
    - 8 erros seguidos: Bloqueio médio (+10 minutos).
    - 11 erros seguidos: Bloqueio CRÍTICO (Conta travada até intervenção do Admin).

    Args:
        username (str): Login fornecido.
        password (str): Senha fornecida.

    Returns:
        tuple: (dados_usuario, mensagem_erro). 
               Se sucesso: (dict, None). Se erro: (None, "Motivo").
    """
    try:
        # 1. Busca o usuário pelo login (independente da senha) para verificar o estado da conta
        query_busca = text("SELECT * FROM usuarios WHERE username = :u")
        
        # 'with engine.connect()' garante que a conexão abra e FECHE automaticamente (Context Manager)
        with engine.connect() as conn:
            # .mappings() transforma o resultado da linha em um dicionário Python amigável
            user = conn.execute(query_busca, {"u": username}).mappings().fetchone()
        
        # Caso 1: Usuário não existe no banco
        if not user:
            return None, "Usuário ou senha incorretos." # Msg genérica por segurança

        # Caso 2: Conta está banida permanentemente
        if user['bloqueado_permanente']:
            return None, "Conta bloqueada permanentemente por segurança. Contate o administrador."

        # Caso 3: Conta está em bloqueio temporário (Cool-down)
        if user['bloqueio_ate'] and datetime.now() < user['bloqueio_ate']:
            # Calcula quantos minutos faltam para liberar
            tempo_restante = int((user['bloqueio_ate'] - datetime.now()).total_seconds() / 60) + 1
            return None, f"Muitas tentativas falhas. Aguarde {tempo_restante} minutos."

        # Caso 4: Verifica a Senha (Se chegou aqui, a conta está ativa)
        # Nota: Em produção real, compararíamos HASHES, não texto plano.
        if user['senha'] == password:
            # SUCESSO!
            # É crucial zerar os contadores de erro agora, pois o usuário provou ser ele mesmo.
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE usuarios 
                    SET tentativas_falhas = 0, bloqueio_ate = NULL 
                    WHERE id = :id
                """), {"id": user['id']})
                conn.commit() # Efetiva a alteração no banco
            
            # Retorna apenas os dados necessários para a sessão (Tupla leve)
            dados_sessao = (user['id'], user['primeiro_nome'], user['ultimo_nome'], user['is_admin'])
            return dados_sessao, None
        
        else:
            # FALHA DE SENHA: Aplica a lógica de punição
            novas_tentativas = (user['tentativas_falhas'] or 0) + 1
            bloqueio_time = None
            bloqueado_perm = False
            msg_extra = ""

            # Nível 1: 5 erros -> Bloqueia 10 min
            if novas_tentativas == 5:
                bloqueio_time = datetime.now() + timedelta(minutes=10)
                msg_extra = " Você errou 5 vezes. A conta foi bloqueada por 10 minutos."
            
            # Nível 2: 8 erros -> Bloqueia +10 min
            elif novas_tentativas == 8:
                bloqueio_time = datetime.now() + timedelta(minutes=10)
                msg_extra = " Você errou mais 3 vezes. Aguarde mais 10 minutos."

            # Nível 3: 11 erros -> Bloqueio Total (Game Over)
            elif novas_tentativas >= 11:
                bloqueado_perm = True
                msg_extra = " Conta bloqueada permanentemente. Solicite desbloqueio ao Admin."

            # Persiste a punição no banco
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE usuarios 
                    SET tentativas_falhas = :t, bloqueio_ate = :b, bloqueado_permanente = :bp 
                    WHERE id = :id
                """), {
                    "t": novas_tentativas,
                    "b": bloqueio_time,
                    "bp": bloqueado_perm,
                    "id": user['id']
                })
                conn.commit()

            return None, f"Senha incorreta.{msg_extra}"

    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha na autenticação: {e}")
        return None, "Erro interno no servidor de banco de dados."

# =============================================================================
# SEÇÃO 2: GESTÃO DE USUÁRIOS (CRUD)
# =============================================================================

def listar_todos_usuarios():
    """
    Lista todos os usuários para exibição no Dashboard Administrativo.
    Usa Pandas para facilitar a criação da tabela no Front-end.
    """
    try:
        # Seleciona apenas colunas seguras (nunca trazer a senha aqui)
        query = "SELECT id, primeiro_nome, ultimo_nome, username, email, is_admin, tentativas_falhas, bloqueado_permanente FROM usuarios ORDER BY id"
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return pd.DataFrame() # Retorna DataFrame vazio para não quebrar a tela

def buscar_usuario_por_id(user_id):
    """Retorna dicionário com dados de um usuário específico (usado para edição)."""
    try:
        query = text("SELECT * FROM usuarios WHERE id = :id")
        with engine.connect() as conn:
            res = conn.execute(query, {"id": int(user_id)}).mappings().fetchone()
        return res
    except Exception as e:
        print(f"Erro ao buscar ID {user_id}: {e}")
        return None

def persistir_usuario(primeiro, ultimo, email, senha, is_admin_val, user_id=None):
    """
    Função Híbrida (Upsert Lógico): Cria (INSERT) ou Atualiza (UPDATE) um usuário.
    
    Args:
        user_id (int, optional): Se fornecido, é uma EDIÇÃO. Se None, é CRIAÇÃO.
    """
    # 1. Regra de Negócio: Geração automática de login (Padronização)
    username = f"{primeiro.lower()}.{ultimo.lower()}"
    
    # 2. Regra de Negócio: Validação de domínio corporativo
    if not email.endswith("@ovg.org.br"):
        return False, "O e-mail corporativo deve terminar com @ovg.org.br"
    
    senha_para_salvar = senha
    
    # --- FLUXO DE ATUALIZAÇÃO (EDITAR USUÁRIO EXISTENTE) ---
    if user_id:
        usuario_atual = buscar_usuario_por_id(user_id)
        if not usuario_atual: return False, "Usuário não encontrado para edição."
        
        # Lógica de Senha na Edição:
        # Se o campo senha vier vazio, significa que o admin não quis mudar a senha.
        # Mantemos a senha antiga.
        if not senha:
            senha_para_salvar = usuario_atual['senha']
        else:
            # Se veio senha nova, validamos a complexidade
            erros_senha = validar_requisitos_senha(senha)
            if erros_senha: return False, " | ".join(erros_senha)
            
        try:
            # Ao editar, assumimos que o problema da conta foi resolvido.
            # Portanto, zeramos 'tentativas_falhas' e removemos bloqueios (Unlock Account).
            sql_update = text("""
                UPDATE usuarios 
                SET primeiro_nome=:p, ultimo_nome=:u, username=:user, email=:email, senha=:s, is_admin=:a,
                    tentativas_falhas=0, bloqueio_ate=NULL, bloqueado_permanente=FALSE
                WHERE id=:id
            """)
            with engine.connect() as conn:
                conn.execute(sql_update, {
                    "p": primeiro, "u": ultimo, "user": username, "email": email, 
                    "s": senha_para_salvar, "a": is_admin_val, "id": int(user_id)
                })
                conn.commit()
            return True, "Usuário atualizado e desbloqueado com sucesso!"
        except Exception as e:
            return False, f"Erro de banco ao atualizar: {str(e)}"
            
    # --- FLUXO DE CRIAÇÃO (NOVO USUÁRIO) ---
    else:
        # Na criação, senha é obrigatória
        erros_senha = validar_requisitos_senha(senha)
        if erros_senha: return False, " | ".join(erros_senha)

        try:
            sql_insert = text("""
                INSERT INTO usuarios (primeiro_nome, ultimo_nome, username, email, senha, is_admin)
                VALUES (:p, :u, :user, :email, :senha, :admin)
            """)
            with engine.connect() as conn:
                conn.execute(sql_insert, {
                    "p": primeiro, "u": ultimo, "user": username, 
                    "email": email, "senha": senha, "admin": is_admin_val
                })
                conn.commit()
            return True, "Usuário criado com sucesso!"
        except Exception as e:
            return False, f"Erro de banco ao criar: {str(e)}"

def excluir_usuario(user_id):
    """
    Remove um usuário.
    Possui trava de segurança para impedir a exclusão do Super Admin (ID 1).
    """
    if int(user_id) == 1:
        return False # Hard-fail: Proteção do sistema
        
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": int(user_id)})
            conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao excluir: {e}")
        return False

def atualizar_senha_usuario(user_id, senha_atual, nova_senha):
    """
    Permite que o próprio usuário troque a senha (Self-Service).
    Diferente do Admin resetando a senha, aqui exigimos a confirmação da senha antiga.
    """
    try:
        user = buscar_usuario_por_id(user_id)
        if not user: return False, "Usuário não encontrado."

        # 1. Valida senha antiga (Prova de propriedade da conta)
        if user['senha'] != senha_atual:
            return False, "A senha atual informada está incorreta."

        # 2. Valida requisitos da nova senha (Complexidade)
        erros = validar_requisitos_senha(nova_senha)
        if erros: return False, " | ".join(erros)

        # 3. Salva no banco
        with engine.connect() as conn:
            conn.execute(text("UPDATE usuarios SET senha = :s WHERE id = :id"), {
                "s": nova_senha, "id": int(user_id)
            })
            conn.commit()
        
        return True, "Senha alterada com sucesso!"
    except Exception as e:
        return False, f"Erro ao trocar senha: {str(e)}"