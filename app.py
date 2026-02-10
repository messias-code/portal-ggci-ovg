"""
=============================================================================
ARQUIVO: app.py (ENTRY POINT)
DESCRIÇÃO:
    Este é o arquivo principal da aplicação. Ele é responsável por:
    1. Inicializar o Servidor Dash.
    2. Configurar o Roteamento de URL (Navegação entre páginas).
    3. Gerenciar o Estado de Autenticação (Login/Logout).
    4. Centralizar os Callbacks (Lógica de interação).
    5. Configurar a Rede (Automação para rodar em WSL/Windows).

    PADRÃO DE PROJETO:
    Utilizamos um padrão de "Single Page Application" (SPA). O layout base 
    nunca recarrega; apenas o conteúdo da div 'page-content' é trocado.
=============================================================================
"""
import dash
from dash import dcc, html, Input, Output, State, callback, ctx, no_update, ALL, callback_context
import dash_bootstrap_components as dbc
import unicodedata
import re
import os
import sys
import subprocess
import platform
from collections import Counter

# --- IMPORTAÇÕES LOCAIS (MÓDULOS DO PROJETO) ---
from src.database import (
    autenticar_usuario,
    persistir_usuario,
    excluir_usuario,
    atualizar_senha_usuario,
    buscar_usuario_por_id,
    listar_todos_usuarios
)

from src.layouts import (
    layout_login_principal,
    layout_home,
    layout_menu_softwares,
    layout_ferramenta_inscricoes,
    layout_ferramenta_ies,
    layout_ferramenta_analise_contratos,
    layout_documentacoes,
    layout_dashboards,
    layout_dashboard_admin,
    componentes_modais_admin,
    gerar_linhas_usuarios
)

# Inicialização do App
# suppress_callback_exceptions=True: Essencial em apps multi-páginas. 
# Evita erros quando o Dash tenta buscar callbacks de componentes que ainda não foram renderizados na tela.
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "Portal GGCI"

# Layout Base (Skeleton)
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),           # Ouve a URL do navegador
    dcc.Store(id='auth-store', storage_type='session'), # Mantém os dados do usuário na sessão do browser (f5 não desloga)
    html.Div(id='page-content')                      # Onde as páginas são renderizadas dinamicamente
])

# =============================================================================
# FUNÇÕES AUXILIARES GERAIS
# =============================================================================

def remove_acentos(texto):
    """
    Normaliza strings removendo acentuação (ex: 'João' -> 'Joao').
    Útil para padronização de dados e buscas.
    """
    if not isinstance(texto, str): return str(texto)
    # Normaliza para formulário NFD (separa letra do acento) e filtra caracteres não-espaçados (Mn)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# =============================================================================
# AUTOMAÇÃO DE REDE (WINDOWS / WSL)
# =============================================================================
def configurar_rede_automatica(port):
    """
    Script de Infraestrutura (DevOps).
    
    Problema: O WSL2 (Linux no Windows) tem um IP próprio, diferente do Windows.
    Para que outros computadores na rede acessem o Dash rodando no WSL, precisamos
    criar uma "Ponte" (Proxy) no Windows que redireciona o tráfego da porta X 
    do Windows para a porta X do WSL.
    
    Esta função detecta o ambiente e executa comandos PowerShell via Python.
    """
    system_info = platform.release().lower()
    is_wsl = "microsoft" in system_info or "wsl" in system_info
    
    hostname = "localhost"
    try:
        if is_wsl:
            # Pega o hostname do Windows (pai) através do WSL
            hostname = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", "hostname"], text=True).strip()
        else:
            hostname = platform.node()
    except:
        pass

    print("\n" + "="*70)
    print(f"🚀 INICIANDO PORTAL GGCI | HOST: {hostname}")
    
    if is_wsl:
        print("🔧 Ambiente WSL detectado. Iniciando configuração automática de rede...")
        try:
            # 1. Descobre o IP interno do Linux (WSL)
            wsl_ip = subprocess.check_output(["hostname", "-I"], text=True).strip().split()[0]
            print(f"   👉 IP Interno WSL: {wsl_ip}")

            # 2. Monta o script PowerShell
            # Remove regras antigas -> Cria nova regra de Proxy -> Libera Firewall -> Reinicia serviço de IP
            ps_script = f"""
            Write-Host '1. Limpando regras antigas...'
            netsh interface portproxy delete v4tov4 listenport={port} | Out-Null
            netsh interface portproxy delete v4tov4 listenport=8050 | Out-Null
            
            Write-Host '2. Criando novas pontes de rede...'
            netsh interface portproxy add v4tov4 listenport={port} listenaddress=0.0.0.0 connectport={port} connectaddress={wsl_ip}
            netsh interface portproxy add v4tov4 listenport=8050 listenaddress=0.0.0.0 connectport={port} connectaddress={wsl_ip}
            
            Write-Host '3. Liberando Firewall...'
            Remove-NetFirewallRule -DisplayName 'Portal GGCI Auto' -ErrorAction SilentlyContinue | Out-Null
            New-NetFirewallRule -DisplayName 'Portal GGCI Auto' -Direction Inbound -LocalPort {port},8050 -Protocol TCP -Action Allow | Out-Null
            
            Write-Host '4. Reiniciando serviço IP Helper (Essencial)...'
            Restart-Service iphlpsvc -Force | Out-Null
            """
            
            # 3. Executa o script no Windows via subprocesso
            result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("   ✅ Ponte Windows -> WSL configurada e serviço reiniciado!")
            else:
                print("   ⚠️  AVISO: Ocorreu um erro na configuração automática.")
                print(f"   Erro: {result.stderr[:200]}...") 
                
        except Exception as e:
            print(f"   ❌ Erro crítico ao configurar rede: {e}")
    
    print("-" * 70)
    print(f"🌍 ACESSO: http://{hostname}:{port}/ (Principal)")
    print(f"           http://{hostname}:8050/ (Alternativo)")
    print("="*70 + "\n")

# =============================================================================
# ROTEADOR (NAVIGATION CONTROLLER)
# =============================================================================
@callback(Output('page-content', 'children'), Input('url', 'pathname'), Input('auth-store', 'data'))
def router(pathname, auth_data):
    """
    Controla qual página é exibida baseada na URL e na Autenticação.
    Atua como um 'Guard' de segurança.
    """
    # 1. Rotas Públicas ou Logout
    if pathname == '/logout': return layout_login_principal()
    if pathname == '/' or not pathname: return layout_login_principal()
    
    # 2. Verificação de Segurança (Redireciona para login se não autenticado)
    if not auth_data or not auth_data.get('is_authenticated'): return layout_login_principal()

    # 3. Rotas Privadas
    if pathname == '/home': return layout_home(auth_data)
    if pathname == '/softwares': return layout_menu_softwares(auth_data)
    if pathname == '/softwares/gerador-lista': return layout_ferramenta_inscricoes()
    if pathname == '/softwares/padronizador-ies': return layout_ferramenta_ies()
    if pathname == '/softwares/analise-contratos': return layout_ferramenta_analise_contratos()
    if pathname == '/documentacoes': return layout_documentacoes()
    if pathname == '/dashboards': return layout_dashboards()
    
    # 4. Rota Admin (Proteção extra: verifica flag is_admin)
    if pathname == '/gestao/dashboard': 
        return html.Div([layout_dashboard_admin(), componentes_modais_admin()]) if auth_data.get('is_admin') else layout_home(auth_data)

    # 404 Not Found
    return html.Div("Página não encontrada (404)", className="p-5 text-center text-muted")

# =============================================================================
# CALLBACKS GERAIS (Login, Senha, Logout)
# =============================================================================

@callback(
    [Output('auth-store', 'data', allow_duplicate=True), 
     Output('url', 'pathname', allow_duplicate=True), 
     Output('login-main-alert', 'children')], 
    Input('btn-login-main', 'n_clicks'), 
    [State('login-main-user', 'value'), 
     State('login-main-password', 'value')], 
    prevent_initial_call=True
)
def realizar_login(n_clicks, username, password):
    """Processa a tentativa de login."""
    if not n_clicks: return no_update
    
    # Validação Básica
    if not username or not password: 
        return no_update, no_update, dbc.Alert("Preencha campos.", color="warning")
    
    # Validação no Banco
    dados, erro = autenticar_usuario(username, password)
    
    if dados: 
        # Sucesso: Salva sessão e redireciona
        session_data = {'id': dados[0], 'nome': dados[1], 'sobrenome': dados[2], 'is_admin': dados[3], 'is_authenticated': True}
        return session_data, "/home", ""
    
    # Falha
    return no_update, no_update, dbc.Alert(erro, color="danger")

@callback(Output('auth-store', 'data', allow_duplicate=True), Input('url', 'pathname'), prevent_initial_call=True)
def realizar_logout(path): 
    """Limpa a sessão ao acessar /logout."""
    return {} if path == '/logout' else no_update

@callback(
    [Output("modal-troca-senha", "is_open"), 
     Output("feedback-troca-senha", "children"), 
     Output("input-senha-atual", "value"), 
     Output("input-nova-senha", "value"), 
     Output("input-nova-senha-confirma", "value")], 
    [Input("btn-abrir-troca-senha", "n_clicks"), 
     Input("btn-cancelar-troca", "n_clicks"), 
     Input("btn-salvar-troca", "n_clicks")], 
    [State("modal-troca-senha", "is_open"), 
     State("input-senha-atual", "value"), 
     State("input-nova-senha", "value"), 
     State("input-nova-senha-confirma", "value"), 
     State("auth-store", "data")], 
    prevent_initial_call=True
)
def usuario_trocar_senha(btn_open, btn_cancel, btn_save, is_open, atual, nova, confirma, auth_data):
    """Gerencia o Modal de Troca de Senha do próprio usuário."""
    trig = ctx.triggered_id
    
    # Lógica de Abrir/Fechar sem salvar
    if trig == "btn-abrir-troca-senha": return True, "", "", "", ""
    if trig == "btn-cancelar-troca": return False, "", "", "", ""
    
    # Lógica de Salvar
    if trig == "btn-salvar-troca":
        if not all([atual, nova, confirma]): return True, dbc.Alert("Preencha tudo.", color="warning"), no_update, no_update, no_update
        if nova != confirma: return True, dbc.Alert("Senhas diferem.", color="danger"), no_update, no_update, no_update
        
        ok, msg = atualizar_senha_usuario(auth_data.get('id'), atual, nova)
        
        # Se OK, fecha modal. Se Erro, mantém aberto e mostra alerta.
        return (False, "", "", "", "") if ok else (True, dbc.Alert(msg, color="danger"), no_update, no_update, no_update)
    
    return no_update

@callback(Output("toast-acesso-negado", "is_open"), Input("btn-acesso-negado-gestao", "n_clicks"), prevent_initial_call=True)
def notificar_acesso_negado(_): 
    """Exibe Toast se usuário comum tentar clicar no card de Admin."""
    return True

# =============================================================================
# CALLBACKS: ADMINISTRAÇÃO (CRUD) - BLINDADO
# =============================================================================

@callback(Output("tabela-usuarios-body", "children"), Input("input-pesquisa-usuario", "value"))
def filtrar_usuarios_tabela(termo_pesquisa):
    """Filtro dinâmico da tabela de usuários (Search bar)."""
    df = listar_todos_usuarios()
    if termo_pesquisa:
        termo = termo_pesquisa.lower()
        # Filtra em várias colunas (Nome, Login, Email)
        df = df[df['primeiro_nome'].str.lower().str.contains(termo) | df['ultimo_nome'].str.lower().str.contains(termo) | df['username'].str.lower().str.contains(termo) | df['email'].str.lower().str.contains(termo)]
    return gerar_linhas_usuarios(df)

@callback([Output("input-senha", "type"), Output("input-senha-confirma", "type")], Input("check-mostrar-senha-admin", "value"), prevent_initial_call=True)
def toggle_pwd_admin(show_password): 
    """Mostra/Esconde senha no formulário admin."""
    return ("text", "text") if show_password else ("password", "password")

# --- LÓGICA DE GERENCIAMENTO DE USUÁRIO (CRIAR/EDITAR) ---
# Aqui usamos Pattern Matching (ALL) para identificar qual botão de edição foi clicado na tabela
@callback(
    [Output("modal-usuario", "is_open"), Output("modal-titulo-usuario", "children"), Output("store-edit-id", "data"), Output("input-primeiro-nome", "value"), Output("input-ultimo-nome", "value"), Output("input-email", "value"), Output("check-is-admin", "value"), Output("input-senha", "value"), Output("input-senha-confirma", "value"), Output("alert-modal-usuario", "children")], 
    [Input("btn-novo-usuario", "n_clicks"), Input({"type": "btn-edit-user", "index": ALL}, "n_clicks"), Input("btn-cancelar-modal", "n_clicks"), Input("btn-salvar-usuario", "n_clicks")], 
    [State("modal-usuario", "is_open"), State("store-edit-id", "data"), State("input-primeiro-nome", "value"), State("input-ultimo-nome", "value"), State("input-email", "value"), State("input-senha", "value"), State("input-senha-confirma", "value"), State("check-is-admin", "value")], 
    prevent_initial_call=True
)
def admin_gerenciar_usuario(btn_new, btn_edit, btn_cancel, btn_save, is_open, edit_id, nome, sobrenome, email, senha, senha2, is_admin):
    trigger = ctx.triggered_id
    if not trigger: return no_update
    
    # 1. Abrir Modal para NOVO Usuário
    if trigger == "btn-novo-usuario": 
        # Limpa todos os campos e define edit_id como None
        return True, "Cadastrar Usuário", None, "", "", "", False, "", "", ""
        
    # 2. Abrir Modal para EDITAR Usuário (Pattern Matching)
    # Detecta se o trigger foi um dicionário (ex: {'type': 'btn-edit-user', 'index': 5})
    if isinstance(trigger, dict) and trigger['type'] == 'btn-edit-user':
        if not btn_edit or not any(btn_edit): 
            return no_update
            
        # Busca dados atuais para preencher o modal
        user_data = buscar_usuario_por_id(trigger['index'])
        if user_data: 
            return True, "Editar Usuário", trigger['index'], user_data['primeiro_nome'], user_data['ultimo_nome'], user_data['email'], bool(user_data['is_admin']), "", "", ""
        return no_update
        
    # 3. Cancelar/Fechar Modal
    if trigger == "btn-cancelar-modal": 
        return False, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, ""
        
    # 4. Salvar (Insert ou Update)
    if trigger == "btn-salvar-usuario":
        # Validações
        if not all([nome, sobrenome, email]): return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Campos obrigatórios!", color="warning")
        if not edit_id and not senha: return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Senha obrigatória.", color="warning")
        if senha and senha != senha2: return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Senhas não conferem!", color="danger")
        
        # Persistência no Banco
        sucesso, msg = persistir_usuario(nome, sobrenome, email, senha, bool(is_admin), user_id=edit_id)
        if sucesso: return False, no_update, None, "", "", "", False, "", "", ""
        return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert(msg, color="danger")
    
    return no_update

@callback(Output("url", "pathname", allow_duplicate=True), [Input("modal-usuario", "is_open"), Input("modal-delete", "is_open")], prevent_initial_call=True)
def admin_reload_table(m1_open, m2_open): 
    """Recarrega a página (e a tabela) quando um modal é fechado."""
    return "/gestao/dashboard" if not m1_open and not m2_open else no_update

# --- LÓGICA DE EXCLUSÃO ---
@callback(
    [Output("modal-delete", "is_open"), Output("store-delete-id", "data")], 
    [Input({"type": "btn-delete-user", "index": ALL}, "n_clicks"), Input("btn-cancelar-delete", "n_clicks"), Input("btn-confirmar-delete", "n_clicks")], 
    [State("store-delete-id", "data")], 
    prevent_initial_call=True
)
def admin_delete_flow(btn_trash, btn_cancel, btn_confirm, del_id):
    trigger = ctx.triggered_id
    if not trigger: return no_update
    
    # Detecta clique no botão de lixeira (Dictionary ID)
    if isinstance(trigger, dict):
        if not btn_trash or not any(btn_trash): 
            return no_update
        # Abre modal e guarda o ID a ser deletado na Store
        return True, trigger['index']
        
    if trigger == "btn-cancelar-delete": return False, None
    if trigger == "btn-confirmar-delete":
        if del_id: excluir_usuario(del_id)
        return False, None
    return no_update

# =============================================================================
# CALLBACKS CLIENTSIDE (JAVASCRIPT INJETADO)
# =============================================================================
# Usamos Clientside Callbacks para operações que rodam melhor no navegador do cliente,
# como acessar a área de transferência (Clipboard).

# 1. Cópia do NORMALIZADOR DE DADOS
app.clientside_callback(
    """
    function(n_clicks, text) {
        if (n_clicks > 0 && text) {
            // Tenta usar API moderna de Clipboard
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text);
            } else {
                // Fallback para navegadores antigos: cria textarea invisível, seleciona e copia
                let textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {
                    document.execCommand('copy');
                } catch (err) {
                    console.error('Erro ao copiar fallback', err);
                }
                document.body.removeChild(textArea);
            }
            return true;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("toast-copy-success", "is_open"),
    Input("btn-copiar-manual", "n_clicks"),
    State("output-ies", "value"),
    prevent_initial_call=True
)

# 2. Cópia do FORMATADOR DE LISTAS (Mesma lógica JS)
app.clientside_callback(
    """
    function(n_clicks, text) {
        if (n_clicks > 0 && text) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text);
            } else {
                let textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {
                    document.execCommand('copy');
                } catch (err) {
                    console.error('Erro ao copiar fallback', err);
                }
                document.body.removeChild(textArea);
            }
            return true;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("toast-copy-lista-success", "is_open"),
    Input("btn-copiar-lista", "n_clicks"),
    State("output-inscricoes", "value"),
    prevent_initial_call=True
)

# 3. Lógica do NORMALIZADOR DE DADOS (Python)
@callback(
    [Output("output-ies", "value"), Output("badge-ies-entrada", "children"), Output("badge-ies-saida", "children"), Output("toast-ies", "children"), Output("toast-ies", "is_open"), Output("input-ies", "value"), Output("toast-ies", "header"), Output("toast-ies", "icon")], 
    [Input("btn-processar-ies", "n_clicks"), Input("btn-limpar-ies", "n_clicks")], 
    [State("input-ies", "value"), State("radio-case-ies", "value"), State("switch-accents-ies", "value"), State("radio-tipo-ies", "value"), State("input-remove-chars-ies", "value")]
)
def processar_normalizacao(n_process, n_clear, text, case, accent, out_type, rm_chars):
    # Botão Limpar
    if ctx.triggered_id == "btn-limpar-ies": return "", "0 itens", "0 itens", "", False, "", "Limpeza", "secondary"
    
    if not text: return no_update, no_update, no_update, no_update, False, no_update, no_update, no_update
    
    alerta, regex = False, ""
    
    # Tratamento de Regex para caracteres customizados
    if rm_chars:
        if " " in rm_chars: alerta, rm_chars = True, rm_chars.replace(" ", "")
        try: regex = f"[{re.escape(rm_chars)}]"
        except: pass
    
    # Processamento linha a linha
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    processed = []
    
    for item in lines:
        if regex: item = re.sub(regex, "", item) # Remove chars proibidos
        if accent: item = remove_acentos(item)   # Remove acentos
        # Normaliza Case (Maiúsculo/Minúsculo)
        if case == "upper": item = item.upper()
        elif case == "lower": item = item.lower()
        elif case == "title": item = item.title()
        
        item = " ".join(item.split()) # Remove espaços duplos internos
        if item: processed.append(item)
    
    # Remove duplicatas se solicitado
    final = list(dict.fromkeys(processed)) if out_type == "unique" else processed
    
    # Retornos múltiplos para atualizar toda a interface
    return "\n".join(final), f"{len(lines)} itens", f"{len(final)} itens", "Aviso: Espaços removidos." if alerta else f"Gerado com sucesso!", True, no_update, "Aviso" if alerta else "Concluído", "warning" if alerta else "success"

# 4. Lógica do FORMATADOR DE LISTAS (Python)
@callback(
    [Output("output-inscricoes", "value"), 
     Output("input-inscricoes", "value"), 
     Output("badge-inscricoes-saida", "children"), 
     Output("badge-inscricoes-entrada", "children"), 
     Output("toast-inscricoes", "children"), 
     Output("toast-inscricoes", "is_open"),
     Output("collapse-duplicatas", "is_open"), 
     Output("conteudo-duplicatas", "children"),
     Output("titulo-qtd-duplicatas", "children")], 
    [Input("btn-processar-inscricoes", "n_clicks"), 
     Input("btn-limpar-inscricoes", "n_clicks")], 
    [State("input-inscricoes", "value")], 
    prevent_initial_call=True
)
def processar_lista(n_process, n_clear, text):
    if ctx.triggered_id == "btn-limpar-inscricoes": 
        return "", "", "0 itens", "0 itens", "", False, False, "", "Itens Duplicados Removidos"
    
    if not text: 
        return no_update

    # 1. Normaliza e separa (Troca vírgula por quebra de linha para aceitar CSV)
    raw_items = [item.strip() for item in text.replace(",", "\n").split("\n") if item.strip()]
    
    # 2. Identifica duplicatas usando Counter (ferramenta eficiente de contagem)
    contagem = Counter(raw_items)
    itens_duplicados = [item for item, qtd in contagem.items() if qtd > 1]
    
    # 3. Cria lista única e ordena alfabeticamente
    uniques = sorted(list(set(raw_items)))
    resultado_final = ",".join(uniques)
    
    # 4. Estatísticas
    qtd_entrada = len(raw_items)
    qtd_saida = len(uniques)
    
    # 5. Monta saídas
    msg_toast = f"Gerado com sucesso!"
    
    # Configura alerta visual de duplicatas
    tem_duplicata = False
    texto_duplicatas = ""
    texto_titulo = "Itens Duplicados Removidos"

    if itens_duplicados:
        tem_duplicata = True
        texto_duplicatas = ", ".join(itens_duplicados)
        texto_titulo = f"Itens Duplicados Removidos: {len(itens_duplicados)}"

    return resultado_final, no_update, f"{qtd_saida} únicos", f"{qtd_entrada} itens", msg_toast, True, tem_duplicata, texto_duplicatas, texto_titulo

# =============================================================================
# MAIN (EXECUÇÃO)
# =============================================================================
if __name__ == '__main__':
    is_wsl = "microsoft" in platform.release().lower() or "wsl" in platform.release().lower()
    
    # MUDANÇA AQUI:
    # Se for WSL usa 8051. Se for Windows (PowerShell) usa 8085.
    PORT = 8051 if is_wsl else 8085
    
    if os.environ.get("WERKZEUG_RUN_MAIN") is None:
        try:
            configurar_rede_automatica(PORT)
        except:
            pass 

    app.run(host='0.0.0.0', port=PORT, debug=True)