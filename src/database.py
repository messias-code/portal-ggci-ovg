from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta
from .config import DATABASE_URL
from .utils import validar_senha

# Cria o motor de conexão
engine = create_engine(DATABASE_URL)

def verificar_login(username, password):
    """
    Verifica login com regras de bloqueio:
    - 5 erros: espera 10 min
    - +3 erros (total 8): espera +10 min
    - +3 erros (total 11): Bloqueio Permanente
    """
    try:
        # 1. Buscar usuário pelo username para checar status
        query_user = text("SELECT * FROM usuarios WHERE username = :u")
        with engine.connect() as conn:
            user = conn.execute(query_user, {"u": username}).mappings().fetchone()
        
        if not user:
            return None, "Usuário ou senha incorretos."

        # 2. Verificar Bloqueio Permanente
        if user['bloqueado_permanente']:
            return None, "Conta bloqueada permanentemente. Contate o administrador."

        # 3. Verificar Bloqueio Temporário
        if user['bloqueio_ate'] and datetime.now() < user['bloqueio_ate']:
            tempo_restante = int((user['bloqueio_ate'] - datetime.now()).total_seconds() / 60) + 1
            return None, f"Muitas tentativas. Tente novamente em {tempo_restante} minutos."

        # 4. Verificar Senha
        if user['senha'] == password:
            # SUCESSO: Zera contadores
            with engine.connect() as conn:
                conn.execute(text("UPDATE usuarios SET tentativas_falhas = 0, bloqueio_ate = NULL WHERE id = :id"), {"id": user['id']})
                conn.commit()
            
            # Retorna dados simplificados para sessão
            return (user['id'], user['primeiro_nome'], user['ultimo_nome'], user['is_admin']), None
        
        else:
            # FALHA: Incrementa erro e aplica regras
            novas_tentativas = (user['tentativas_falhas'] or 0) + 1
            bloqueio_time = None
            bloqueado_perm = False
            msg_extra = ""

            # Regra 1: 5 erros -> 10 min
            if novas_tentativas == 5:
                bloqueio_time = datetime.now() + timedelta(minutes=10)
                msg_extra = " Você errou 5 vezes. Aguarde 10 minutos."
            
            # Regra 2: 8 erros (5+3) -> +10 min
            elif novas_tentativas == 8:
                bloqueio_time = datetime.now() + timedelta(minutes=10)
                msg_extra = " Você errou mais 3 vezes. Aguarde 10 minutos."

            # Regra 3: 11 erros (5+3+3) -> Bloqueio Permanente
            elif novas_tentativas >= 11:
                bloqueado_perm = True
                msg_extra = " Conta bloqueada. Contate o admin."

            # Atualiza banco
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
        print(f"Erro no login: {e}")
        return None, "Erro interno no servidor."

def carregar_usuarios():
    try:
        # Adicionei as colunas novas para visualização do admin se quiser
        df = pd.read_sql("SELECT id, primeiro_nome, ultimo_nome, username, email, is_admin, tentativas_falhas, bloqueado_permanente FROM usuarios ORDER BY id", engine)
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
    
    if not email.endswith("@ovg.org.br"):
        return False, "O e-mail deve terminar com @ovg.org.br"
    
    senha_final = senha
    
    # --- MODO EDIÇÃO (ADMIN) ---
    if user_id:
        usuario_atual = get_usuario_by_id(user_id)
        if not usuario_atual: return False, "Usuário não encontrado."
        
        if not senha:
            senha_final = usuario_atual['senha']
        else:
            erros_senha = validar_senha(senha)
            if erros_senha: return False, " | ".join(erros_senha)
            
        try:
            # Admin desbloqueia usuário ao editar (zera falhas)
            query = text("""
                UPDATE usuarios 
                SET primeiro_nome=:p, ultimo_nome=:u, username=:user, email=:email, senha=:s, is_admin=:a,
                    tentativas_falhas=0, bloqueio_ate=NULL, bloqueado_permanente=FALSE
                WHERE id=:id
            """)
            with engine.connect() as conn:
                conn.execute(query, {
                    "p": primeiro, "u": ultimo, "user": username, "email": email, 
                    "s": senha_final, "a": is_admin_val, "id": int(user_id)
                })
                conn.commit()
            return True, "Usuário atualizado (e desbloqueado) com sucesso!"
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
    if int(user_id) == 1: return False
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": int(user_id)})
            conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao deletar: {e}")
        return False

# --- NOVA FUNÇÃO: USUÁRIO TROCAR A PRÓPRIA SENHA ---
def alterar_senha_propria(user_id, senha_atual, nova_senha):
    try:
        user = get_usuario_by_id(user_id)
        if not user: return False, "Usuário não encontrado."

        # 1. Verifica senha atual
        if user['senha'] != senha_atual:
            return False, "A senha atual está incorreta."

        # 2. Valida nova senha
        erros = validar_senha(nova_senha)
        if erros: return False, " | ".join(erros)

        # 3. Salva
        with engine.connect() as conn:
            conn.execute(text("UPDATE usuarios SET senha = :s WHERE id = :id"), {
                "s": nova_senha, "id": int(user_id)
            })
            conn.commit()
        
        return True, "Senha alterada com sucesso!"
    except Exception as e:
        return False, f"Erro: {str(e)}"