"""
=============================================================================
MÓDULO DE BANCO DE DADOS
=============================================================================
Gerencia todas as interações com o PostgreSQL usando SQLAlchemy.
Contém as regras de negócio de autenticação, bloqueio e gestão de usuários.
"""
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import datetime, timedelta
from .config import DATABASE_URL
from .utils import validar_requisitos_senha

# Inicializa o motor de conexão global
engine = create_engine(DATABASE_URL)

# =============================================================================
# AUTENTICAÇÃO E SEGURANÇA
# =============================================================================

def autenticar_usuario(username, password):
    """
    Valida as credenciais e aplica a política de bloqueio de conta.
    
    Política de Bloqueio:
    - 5 erros consecutivos: Bloqueio temporário de 10 minutos.
    - +3 erros (Total 8): Novo bloqueio de 10 minutos.
    - +3 erros (Total 11): Bloqueio PERMANENTE (apenas admin desbloqueia).

    Args:
        username (str): Login do usuário.
        password (str): Senha (hash ou plain, conforme implementação atual).

    Returns:
        tuple: (dados_usuario_dict, mensagem_erro_str)
               Se sucesso, erro é None. Se falha, dados é None.
    """
    try:
        # 1. Busca o usuário pelo login (independente da senha) para verificar status
        query_busca = text("SELECT * FROM usuarios WHERE username = :u")
        with engine.connect() as conn:
            user = conn.execute(query_busca, {"u": username}).mappings().fetchone()
        
        # Usuário inexistente
        if not user:
            return None, "Usuário ou senha incorretos."

        # 2. Verifica Bloqueio Permanente
        if user['bloqueado_permanente']:
            return None, "Conta bloqueada permanentemente por segurança. Contate o administrador."

        # 3. Verifica Bloqueio Temporário
        if user['bloqueio_ate'] and datetime.now() < user['bloqueio_ate']:
            tempo_restante = int((user['bloqueio_ate'] - datetime.now()).total_seconds() / 60) + 1
            return None, f"Muitas tentativas falhas. Aguarde {tempo_restante} minutos."

        # 4. Verifica a Senha
        if user['senha'] == password:
            # SUCESSO: Zera todos os contadores de erro e libera bloqueios antigos
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE usuarios 
                    SET tentativas_falhas = 0, bloqueio_ate = NULL 
                    WHERE id = :id
                """), {"id": user['id']})
                conn.commit()
            
            # Retorna tupla limpa com dados essenciais para a sessão
            dados_sessao = (user['id'], user['primeiro_nome'], user['ultimo_nome'], user['is_admin'])
            return dados_sessao, None
        
        else:
            # FALHA: Incrementa contador e aplica regras de tempo
            novas_tentativas = (user['tentativas_falhas'] or 0) + 1
            bloqueio_time = None
            bloqueado_perm = False
            msg_extra = ""

            # Nível 1: 5 erros -> 10 min
            if novas_tentativas == 5:
                bloqueio_time = datetime.now() + timedelta(minutes=10)
                msg_extra = " Você errou 5 vezes. A conta foi bloqueada por 10 minutos."
            
            # Nível 2: 8 erros -> +10 min
            elif novas_tentativas == 8:
                bloqueio_time = datetime.now() + timedelta(minutes=10)
                msg_extra = " Você errou mais 3 vezes. Aguarde mais 10 minutos."

            # Nível 3: 11 erros -> Bloqueio Total
            elif novas_tentativas >= 11:
                bloqueado_perm = True
                msg_extra = " Conta bloqueada permanentemente. Solicite desbloqueio ao Admin."

            # Persiste o erro e o bloqueio no banco
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
# GESTÃO DE USUÁRIOS (CRUD)
# =============================================================================

def listar_todos_usuarios():
    """Retorna um DataFrame com todos os usuários para o Dashboard Admin."""
    try:
        query = "SELECT id, primeiro_nome, ultimo_nome, username, email, is_admin, tentativas_falhas, bloqueado_permanente FROM usuarios ORDER BY id"
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return pd.DataFrame()

def buscar_usuario_por_id(user_id):
    """Retorna um dicionário com os dados de um único usuário."""
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
    Cria ou Atualiza um usuário.
    Gera o username automaticamente (nome.sobrenome).
    Se for atualização (user_id presente), zera bloqueios e falhas.
    """
    # Normalização básica
    username = f"{primeiro.lower()}.{ultimo.lower()}"
    
    if not email.endswith("@ovg.org.br"):
        return False, "O e-mail corporativo deve terminar com @ovg.org.br"
    
    senha_para_salvar = senha
    
    # --- FLUXO DE ATUALIZAÇÃO ---
    if user_id:
        usuario_atual = buscar_usuario_por_id(user_id)
        if not usuario_atual: return False, "Usuário não encontrado para edição."
        
        # Se a senha vier vazia, mantemos a antiga. Se vier preenchida, validamos.
        if not senha:
            senha_para_salvar = usuario_atual['senha']
        else:
            erros_senha = validar_requisitos_senha(senha)
            if erros_senha: return False, " | ".join(erros_senha)
            
        try:
            # Ao editar, o Admin automaticamente desbloqueia a conta (zera falhas)
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
            
    # --- FLUXO DE CRIAÇÃO ---
    else:
        # Na criação, a senha é obrigatória e deve ser válida
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
    """Remove um usuário do sistema (exceto o ID 1)."""
    if int(user_id) == 1:
        return False # Proteção contra deletar o Admin Mestre
        
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
    Permite que o próprio usuário troque sua senha.
    Exige validação da senha atual.
    """
    try:
        user = buscar_usuario_por_id(user_id)
        if not user: return False, "Usuário não encontrado."

        # 1. Valida senha antiga
        if user['senha'] != senha_atual:
            return False, "A senha atual informada está incorreta."

        # 2. Valida requisitos da nova senha
        erros = validar_requisitos_senha(nova_senha)
        if erros: return False, " | ".join(erros)

        # 3. Atualiza no banco
        with engine.connect() as conn:
            conn.execute(text("UPDATE usuarios SET senha = :s WHERE id = :id"), {
                "s": nova_senha, "id": int(user_id)
            })
            conn.commit()
        
        return True, "Senha alterada com sucesso!"
    except Exception as e:
        return False, f"Erro ao trocar senha: {str(e)}"