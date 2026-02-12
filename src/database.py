"""
=============================================================================
ARQUIVO: database.py (CAMADA DE DADOS)
DESCRIÇÃO:
    Gerencia conexão PostgreSQL, CRUD e regras de autenticação.
=============================================================================
"""
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta

# Importa configurações e utilitários locais
from .config import DATABASE_URL
from .utils import validar_requisitos_senha

engine = create_engine(DATABASE_URL)

# =============================================================================
# SEÇÃO 1: AUTENTICAÇÃO E SEGURANÇA
# =============================================================================

def autenticar_usuario(username, password):
    """
    Realiza o login do usuário aplicando regras estritas de segurança.
    """
    try:
        query_busca = text("SELECT * FROM usuarios WHERE username = :u")
        
        with engine.connect() as conn:
            user = conn.execute(query_busca, {"u": username}).mappings().fetchone()
        
        # Caso 1: Usuário não existe
        if not user:
            return None, "🚫 Credenciais inválidas. Verifique usuário e senha."

        # Caso 2: Banido
        if user['bloqueado_permanente']:
            return None, "🚫 Acesso bloqueado permanentemente. Contate o Administrador."

        # Caso 3: Bloqueio Temporário
        if user['bloqueio_ate'] and datetime.now() < user['bloqueio_ate']:
            tempo_restante = int((user['bloqueio_ate'] - datetime.now()).total_seconds() / 60) + 1
            return None, f"⏳ Conta temporariamente bloqueada. Tente novamente em {tempo_restante} minutos."

        # Caso 4: Verifica a Senha
        if user['senha'] == password:
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE usuarios 
                    SET tentativas_falhas = 0, bloqueio_ate = NULL 
                    WHERE id = :id
                """), {"id": user['id']})
                conn.commit()
            
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
                msg_extra = " (Aviso: Conta pausada por 10 min)."
            
            # Nível 2: 8 erros -> Bloqueia +10 min
            elif novas_tentativas == 8:
                bloqueio_time = datetime.now() + timedelta(minutes=10)
                msg_extra = " (Aviso: Bloqueio estendido por +10 min)."

            # Nível 3: 11 erros -> Bloqueio Total
            elif novas_tentativas >= 11:
                bloqueado_perm = True
                msg_extra = " (Aviso: Conta bloqueada permanentemente)."

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

            return None, f"⚠️ Senha incorreta.{msg_extra}"

    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha na autenticação: {e}")
        return None, "🚫 Erro interno no servidor de banco de dados."

# =============================================================================
# SEÇÃO 2: GESTÃO DE USUÁRIOS (CRUD)
# =============================================================================

def listar_todos_usuarios():
    try:
        query = "SELECT id, primeiro_nome, ultimo_nome, username, email, is_admin, tentativas_falhas, bloqueado_permanente FROM usuarios ORDER BY id"
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return pd.DataFrame()

def buscar_usuario_por_id(user_id):
    try:
        query = text("SELECT * FROM usuarios WHERE id = :id")
        with engine.connect() as conn:
            res = conn.execute(query, {"id": int(user_id)}).mappings().fetchone()
        return res
    except Exception as e:
        print(f"Erro ao buscar ID {user_id}: {e}")
        return None

def persistir_usuario(primeiro, ultimo, email, senha, is_admin_val, user_id=None):
    # 1. Geração automática de login
    username = f"{primeiro.lower()}.{ultimo.lower()}"
    
    # 2. Validação de domínio corporativo
    if not email.endswith("@ovg.org.br"):
        return False, "⚠️ O e-mail deve ser corporativo (@ovg.org.br)."
    
    senha_para_salvar = senha
    
    # --- EDIÇÃO ---
    if user_id:
        usuario_atual = buscar_usuario_por_id(user_id)
        if not usuario_atual: return False, "🚫 Usuário não encontrado para edição."
        
        if not senha:
            senha_para_salvar = usuario_atual['senha']
        else:
            erros_senha = validar_requisitos_senha(senha)
            if erros_senha: return False, " | ".join(erros_senha)
            
        try:
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
            return True, "✅ Usuário atualizado e desbloqueado com sucesso!"
        except Exception as e:
            return False, f"🚫 Erro de banco ao atualizar: {str(e)}"
            
    # --- CRIAÇÃO ---
    else:
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
            return True, "✅ Usuário cadastrado com sucesso!"
        except Exception as e:
            return False, f"🚫 Erro de banco ao criar: {str(e)}"

def excluir_usuario(user_id):
    if int(user_id) == 1:
        return False
        
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": int(user_id)})
            conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao excluir: {e}")
        return False

def atualizar_senha_usuario(user_id, senha_atual, nova_senha):
    try:
        user = buscar_usuario_por_id(user_id)
        if not user: return False, "🚫 Usuário não encontrado."

        if user['senha'] != senha_atual:
            return False, "🚫 A senha atual informada está incorreta."

        erros = validar_requisitos_senha(nova_senha)
        if erros: return False, " | ".join(erros)

        with engine.connect() as conn:
            conn.execute(text("UPDATE usuarios SET senha = :s WHERE id = :id"), {
                "s": nova_senha, "id": int(user_id)
            })
            conn.commit()
        
        return True, "✅ Senha alterada com sucesso!"
    except Exception as e:
        return False, f"🚫 Erro ao trocar senha: {str(e)}"