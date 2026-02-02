from sqlalchemy import create_engine, text
import pandas as pd
from .config import DATABASE_URL
from .utils import validar_senha

# Cria o motor de conexão
engine = create_engine(DATABASE_URL)

def verificar_login(username, password):
    """Verifica se usuário e senha batem no banco"""
    # MUDANÇA AQUI: Adicionado ultimo_nome no SELECT
    query = text("SELECT id, primeiro_nome, ultimo_nome, is_admin FROM usuarios WHERE username = :u AND senha = :p")
    try:
        with engine.connect() as conn:
            res = conn.execute(query, {"u": username, "p": password}).fetchone()
        return res # Agora retorna (id, nome, sobrenome, is_admin)
    except Exception as e:
        print(f"Erro no login: {e}")
        return None

def carregar_usuarios():
    try:
        df = pd.read_sql("SELECT id, primeiro_nome, ultimo_nome, username, email, is_admin FROM usuarios ORDER BY id", engine)
        return df
    except Exception as e:
        print(f"Erro ao carregar: {e}")
        return pd.DataFrame()

def get_usuario_by_id(user_id):
    try:
        query = text("SELECT * FROM usuarios WHERE id = :id")
        with engine.connect() as conn:
            res = conn.execute(query, {"id": int(user_id)}).mappings().fetchone()
        return res
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return None

def salvar_usuario(primeiro, ultimo, email, senha, is_admin_val, user_id=None):
    # Gera username automático
    username = f"{primeiro.lower()}.{ultimo.lower()}"
    
    # Validação de E-mail
    if not email.endswith("@ovg.org.br"):
        return False, "O e-mail deve terminar com @ovg.org.br"
    
    senha_final = senha
    
    # --- MODO EDIÇÃO ---
    if user_id:
        usuario_atual = get_usuario_by_id(user_id)
        if not usuario_atual: return False, "Usuário não encontrado."
        
        # Se senha vazia, mantém a antiga
        if not senha:
            senha_final = usuario_atual['senha']
        else:
            # Se trocou a senha, valida
            erros_senha = validar_senha(senha)
            if erros_senha: return False, " | ".join(erros_senha)
            
        try:
            query = text("""
                UPDATE usuarios 
                SET primeiro_nome=:p, ultimo_nome=:u, username=:user, email=:email, senha=:s, is_admin=:a
                WHERE id=:id
            """)
            with engine.connect() as conn:
                conn.execute(query, {
                    "p": primeiro, "u": ultimo, "user": username, "email": email, 
                    "s": senha_final, "a": is_admin_val, "id": int(user_id)
                })
                conn.commit()
            return True, "Usuário atualizado com sucesso!"
        except Exception as e:
            return False, f"Erro ao atualizar: {str(e)}"
            
    # --- MODO CRIAÇÃO ---
    else:
        erros_senha = validar_senha(senha)
        if erros_senha: return False, " | ".join(erros_senha)

        try:
            query = text("""
                INSERT INTO usuarios (primeiro_nome, ultimo_nome, username, email, senha, is_admin)
                VALUES (:p, :u, :user, :email, :senha, :admin)
            """)
            with engine.connect() as conn:
                conn.execute(query, {
                    "p": primeiro, "u": ultimo, "user": username, 
                    "email": email, "senha": senha, "admin": is_admin_val
                })
                conn.commit()
            return True, "Usuário criado com sucesso!"
        except Exception as e:
            return False, f"Erro ao salvar: {str(e)}"

def deletar_usuario(user_id):
    # Regra de Segurança ID 1
    if int(user_id) == 1:
        return False

    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": int(user_id)})
            conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao deletar: {e}")
        return False