"""
=============================================================================
ARQUIVO: app.py (ENTRY POINT)
DESCRIÇÃO:
    Este é o arquivo principal da aplicação.
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
from dash_iconify import DashIconify

# --- IMPORTAÇÃO DA NOVA LÓGICA DE AUTOMACAO ---
from src.analise_contratos import AutomacaoContratos

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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "Portal GGCI"

# Layout Base (Skeleton)
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),           # Ouve a URL do navegador
    dcc.Store(id='auth-store', storage_type='session'), # Mantém os dados do usuário na sessão
    html.Div(id='page-content')                      # Onde as páginas são renderizadas dinamicamente
])

# =============================================================================
# FUNÇÕES AUXILIARES GERAIS
# =============================================================================

def remove_acentos(texto):
    """Normaliza strings removendo acentuação."""
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# =============================================================================
# AUTOMAÇÃO DE REDE (WINDOWS / WSL)
# =============================================================================
def configurar_rede_automatica(port):
    """Detecta o ambiente e exibe os links corretos."""
    system_info = platform.release().lower()
    is_wsl = "microsoft" in system_info or "wsl" in system_info
    
    hostname = "localhost"
    windows_ip = "IP-NAO-DETECTADO"
    
    print("\n" + "="*70)
    
    try:
        if is_wsl:
            raw_host = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", "hostname"])
            hostname = raw_host.decode('utf-8', errors='ignore').strip()
            
            cmd_get_ip = r"(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address.IPAddress"
            raw_ip = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", cmd_get_ip])
            windows_ip = raw_ip.decode('utf-8', errors='ignore').strip()

            try:
                raw_wsl = subprocess.check_output(["hostname", "-I"])
                wsl_ip = raw_wsl.decode('utf-8', errors='ignore').strip().split()[0]
                ps_script = f"netsh interface portproxy add v4tov4 listenport={port} listenaddress=0.0.0.0 connectport={port} connectaddress={wsl_ip}"
                subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps_script], capture_output=True)
            except:
                pass 
        else:
            hostname = platform.node()
            import socket
            windows_ip = socket.gethostbyname(hostname)

    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível detectar IP externo automaticamente: {e}")

    print(f"🚀 INICIANDO PORTAL GGCI | HOST: {hostname}")
    print("-" * 70)
    print("📢 LINKS DE ACESSO:")
    print(f"   👉 Pelo Nome (PC/Intranet):   http://{hostname}.ovg.org.br:{port}")
    print(f"   👉 Pelo IP (Celular/Wi-Fi):   http://{windows_ip}:{port}")
    print("")
    print(f"   🏠 Acesso Local (Você):       http://localhost:{port}")
    print("="*70 + "\n")

# =============================================================================
# ROTEADOR (NAVIGATION CONTROLLER)
# =============================================================================
@callback(Output('page-content', 'children'), Input('url', 'pathname'), Input('auth-store', 'data'))
def router(pathname, auth_data):
    # 1. Rotas Públicas ou Logout
    if pathname == '/logout': return layout_login_principal()
    if pathname == '/' or not pathname: return layout_login_principal()
    
    # 2. Verificação de Segurança
    if not auth_data or not auth_data.get('is_authenticated'): return layout_login_principal()

    # 3. Rotas Privadas
    if pathname == '/home': return layout_home(auth_data)
    if pathname == '/softwares': return layout_menu_softwares(auth_data)
    if pathname == '/softwares/gerador-lista': return layout_ferramenta_inscricoes()
    if pathname == '/softwares/padronizador-ies': return layout_ferramenta_ies()
    if pathname == '/softwares/analise-contratos': return layout_ferramenta_analise_contratos()
    if pathname == '/documentacoes': return layout_documentacoes()
    if pathname == '/dashboards': return layout_dashboards()
    
    # 4. Rota Admin
    if pathname == '/gestao/dashboard': 
        return html.Div([layout_dashboard_admin(), componentes_modais_admin()]) if auth_data.get('is_admin') else layout_home(auth_data)

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
    if not n_clicks: return no_update
    if not username or not password: 
        return no_update, no_update, dbc.Alert("⚠️ Preencha todos os campos de login.", color="warning")
    
    dados, erro = autenticar_usuario(username, password)
    
    if dados: 
        session_data = {'id': dados[0], 'nome': dados[1], 'sobrenome': dados[2], 'is_admin': dados[3], 'is_authenticated': True}
        return session_data, "/home", ""
    
    return no_update, no_update, dbc.Alert(erro, color="danger")

@callback(Output('auth-store', 'data', allow_duplicate=True), Input('url', 'pathname'), prevent_initial_call=True)
def realizar_logout(path): 
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
    trig = ctx.triggered_id
    if trig == "btn-abrir-troca-senha": return True, "", "", "", ""
    if trig == "btn-cancelar-troca": return False, "", "", "", ""
    
    if trig == "btn-salvar-troca":
        if not all([atual, nova, confirma]): 
            return True, dbc.Alert("⚠️ Preencha todos os campos obrigatórios.", color="warning"), no_update, no_update, no_update
        if nova != confirma: 
            return True, dbc.Alert("⚠️ As novas senhas não coincidem.", color="danger"), no_update, no_update, no_update
        
        ok, msg = atualizar_senha_usuario(auth_data.get('id'), atual, nova)
        return (False, "", "", "", "") if ok else (True, dbc.Alert(msg, color="danger"), no_update, no_update, no_update)
    
    return no_update

@callback(Output("toast-acesso-negado", "is_open"), Input("btn-acesso-negado-gestao", "n_clicks"), prevent_initial_call=True)
def notificar_acesso_negado(_): 
    return True

# =============================================================================
# CALLBACKS: ADMINISTRAÇÃO (CRUD)
# =============================================================================

@callback(Output("tabela-usuarios-body", "children"), Input("input-pesquisa-usuario", "value"))
def filtrar_usuarios_tabela(termo_pesquisa):
    df = listar_todos_usuarios()
    if termo_pesquisa:
        termo = termo_pesquisa.lower()
        df = df[df['primeiro_nome'].str.lower().str.contains(termo) | df['ultimo_nome'].str.lower().str.contains(termo) | df['username'].str.lower().str.contains(termo) | df['email'].str.lower().str.contains(termo)]
    return gerar_linhas_usuarios(df)

@callback([Output("input-senha", "type"), Output("input-senha-confirma", "type")], Input("check-mostrar-senha-admin", "value"), prevent_initial_call=True)
def toggle_pwd_admin(show_password): 
    return ("text", "text") if show_password else ("password", "password")

@callback(
    [Output("modal-usuario", "is_open"), Output("modal-titulo-usuario", "children"), Output("store-edit-id", "data"), Output("input-primeiro-nome", "value"), Output("input-ultimo-nome", "value"), Output("input-email", "value"), Output("check-is-admin", "value"), Output("input-senha", "value"), Output("input-senha-confirma", "value"), Output("alert-modal-usuario", "children")], 
    [Input("btn-novo-usuario", "n_clicks"), Input({"type": "btn-edit-user", "index": ALL}, "n_clicks"), Input("btn-cancelar-modal", "n_clicks"), Input("btn-salvar-usuario", "n_clicks")], 
    [State("modal-usuario", "is_open"), State("store-edit-id", "data"), State("input-primeiro-nome", "value"), State("input-ultimo-nome", "value"), State("input-email", "value"), State("input-senha", "value"), State("input-senha-confirma", "value"), State("check-is-admin", "value")], 
    prevent_initial_call=True
)
def admin_gerenciar_usuario(btn_new, btn_edit, btn_cancel, btn_save, is_open, edit_id, nome, sobrenome, email, senha, senha2, is_admin):
    trigger = ctx.triggered_id
    if not trigger: return no_update
    
    if trigger == "btn-novo-usuario": 
        return True, "Cadastrar Usuário", None, "", "", "", False, "", "", ""
        
    if isinstance(trigger, dict) and trigger['type'] == 'btn-edit-user':
        if not btn_edit or not any(btn_edit): return no_update
        user_data = buscar_usuario_por_id(trigger['index'])
        if user_data: 
            return True, "Editar Usuário", trigger['index'], user_data['primeiro_nome'], user_data['ultimo_nome'], user_data['email'], bool(user_data['is_admin']), "", "", ""
        return no_update
        
    if trigger == "btn-cancelar-modal": 
        return False, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, ""
        
    if trigger == "btn-salvar-usuario":
        if not all([nome, sobrenome, email]): 
            return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("⚠️ Preencha todos os campos obrigatórios.", color="warning")
        if not edit_id and not senha: 
            return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("⚠️ A senha é obrigatória para novos usuários.", color="warning")
        if senha and senha != senha2: 
            return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("⚠️ As senhas digitadas não coincidem.", color="danger")
        
        sucesso, msg = persistir_usuario(nome, sobrenome, email, senha, bool(is_admin), user_id=edit_id)
        if sucesso: return False, no_update, None, "", "", "", False, "", "", ""
        return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert(msg, color="danger")
    
    return no_update

@callback(Output("url", "pathname", allow_duplicate=True), [Input("modal-usuario", "is_open"), Input("modal-delete", "is_open")], prevent_initial_call=True)
def admin_reload_table(m1_open, m2_open): 
    return "/gestao/dashboard" if not m1_open and not m2_open else no_update

@callback(
    [Output("modal-delete", "is_open"), Output("store-delete-id", "data")], 
    [Input({"type": "btn-delete-user", "index": ALL}, "n_clicks"), Input("btn-cancelar-delete", "n_clicks"), Input("btn-confirmar-delete", "n_clicks")], 
    [State("store-delete-id", "data")], 
    prevent_initial_call=True
)
def admin_delete_flow(btn_trash, btn_cancel, btn_confirm, del_id):
    trigger = ctx.triggered_id
    if not trigger: return no_update
    
    if isinstance(trigger, dict):
        if not btn_trash or not any(btn_trash): return no_update
        return True, trigger['index']
        
    if trigger == "btn-cancelar-delete": return False, None
    if trigger == "btn-confirmar-delete":
        if del_id: excluir_usuario(del_id)
        return False, None
    return no_update

# =============================================================================
# CALLBACKS CLIENTSIDE
# =============================================================================

# 1. Cópia do NORMALIZADOR DE DADOS
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
                try { document.execCommand('copy'); } catch (err) {}
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

# 2. Cópia do FORMATADOR DE LISTAS
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
                try { document.execCommand('copy'); } catch (err) {}
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

# 3. Lógica do NORMALIZADOR DE DADOS
@callback(
    [Output("output-ies", "value"), Output("badge-ies-entrada", "children"), Output("badge-ies-saida", "children"), Output("toast-ies", "children"), Output("toast-ies", "is_open"), Output("input-ies", "value"), Output("toast-ies", "header"), Output("toast-ies", "icon")], 
    [Input("btn-processar-ies", "n_clicks"), Input("btn-limpar-ies", "n_clicks")], 
    [State("input-ies", "value"), State("radio-case-ies", "value"), State("switch-accents-ies", "value"), State("radio-tipo-ies", "value"), State("input-remove-chars-ies", "value")]
)
def processar_normalizacao(n_process, n_clear, text, case, accent, out_type, rm_chars):
    if ctx.triggered_id == "btn-limpar-ies": return "", "0 itens", "0 itens", "", False, "", "Limpeza", "secondary"
    
    if not text: return no_update, no_update, no_update, no_update, False, no_update, no_update, no_update
    
    alerta, regex = False, ""
    if rm_chars:
        if " " in rm_chars: alerta, rm_chars = True, rm_chars.replace(" ", "")
        try: regex = f"[{re.escape(rm_chars)}]"
        except: pass
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    processed = []
    
    for item in lines:
        if regex: item = re.sub(regex, "", item)
        if accent: item = remove_acentos(item)
        if case == "upper": item = item.upper()
        elif case == "lower": item = item.lower()
        elif case == "title": item = item.title()
        item = " ".join(item.split())
        if item: processed.append(item)
    
    final = list(dict.fromkeys(processed)) if out_type == "unique" else processed
    
    msg_toast = "✅ Dados normalizados com sucesso!"
    if alerta: msg_toast = "Aviso: Espaços removidos."
    
    return "\n".join(final), f"{len(lines)} itens", f"{len(final)} itens", msg_toast, True, no_update, "Aviso" if alerta else "Concluído", "warning" if alerta else "success"

# 4. Lógica do FORMATADOR DE LISTAS
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
    
    if not text: return no_update

    raw_items = [item.strip() for item in text.replace(",", "\n").split("\n") if item.strip()]
    contagem = Counter(raw_items)
    itens_duplicados = [item for item, qtd in contagem.items() if qtd > 1]
    
    uniques = sorted(list(set(raw_items)))
    resultado_final = ",".join(uniques)
    
    tem_duplicata = False
    texto_duplicatas = ""
    texto_titulo = "Itens Duplicados Removidos"

    if itens_duplicados:
        tem_duplicata = True
        texto_duplicatas = ", ".join(itens_duplicados)
        texto_titulo = f"Itens Duplicados Removidos: {len(itens_duplicados)}"

    return resultado_final, no_update, f"{len(uniques)} únicos", f"{len(raw_items)} itens", "✅ Dados normalizados com sucesso!", True, tem_duplicata, texto_duplicatas, texto_titulo

# =============================================================================
# CALLBACKS CLIENTSIDE: AUTO-SCROLL DOS LOGS
# =============================================================================
app.clientside_callback(
    """
    function(children) {
        var terminal = document.getElementById('terminal-logs');
        if (terminal) { terminal.scrollTop = terminal.scrollHeight; }
        return window.dash_clientside.no_update;
    }
    """,
    Output("terminal-logs", "id"),
    Input("terminal-logs", "children"),
    prevent_initial_call=True
)

# =============================================================================
# CALLBACKS: FERRAMENTA DE CONTRATOS (INTEGRAÇÃO REAL)
# =============================================================================

# Instância Global do Robô (Singleton)
robo_contratos = AutomacaoContratos()

@callback(
    [Output("intervalo-simulacao", "disabled"),
     Output("btn-iniciar-robo", "disabled"),
     Output("btn-iniciar-robo", "children"),
     Output("btn-cancelar-robo", "disabled"),
     Output("btn-salvar-relatorio", "disabled"),
     
     # Outputs da Barra
     Output("barra-progresso-geral", "value", allow_duplicate=True), 
     Output("barra-progresso-geral", "label", allow_duplicate=True),
     Output("barra-progresso-geral", "color", allow_duplicate=True),
     
     # Output dos Logs (Limpar ao iniciar)
     Output("terminal-logs", "children", allow_duplicate=True)],
    [Input("btn-iniciar-robo", "n_clicks"),
     Input("btn-cancelar-robo", "n_clicks")],
    prevent_initial_call=True
)
def controlar_execucao_robo(n_iniciar, n_cancelar):
    ctx_id = ctx.triggered_id
    
    # 1. INICIAR
    if ctx_id == "btn-iniciar-robo":
        # Dispara a thread real
        robo_contratos.start()
        
        loading_ui = [
            DashIconify(icon="line-md:loading-loop", width=22, color="white", className="me-2"),
            html.Span("RODANDO...", style={"fontSize": "0.85rem"})
        ]
        
        return (
            False, # Intervalo ATIVADO
            True,  # Btn Iniciar DESATIVADO
            loading_ui,
            False, # Btn Cancelar ATIVADO
            True,  # Btn Salvar DESATIVADO
            0, "0%", "primary", # Barra Reset
            [html.Div(">> Inicializando sistema...", style={"color": "#F08EB3"})]
        )

    # 2. CANCELAR
    if ctx_id == "btn-cancelar-robo":
        robo_contratos.stop()
        # O estado visual será atualizado pelo intervalo na próxima batida
        return no_update

    return no_update


@callback(
    [Output("barra-progresso-geral", "value"), 
     Output("barra-progresso-geral", "label"),
     Output("barra-progresso-geral", "color"),
     Output("terminal-logs", "children"),
     
     # Controles de Estado
     Output("intervalo-simulacao", "disabled", allow_duplicate=True),
     Output("btn-iniciar-robo", "children", allow_duplicate=True),
     Output("btn-iniciar-robo", "disabled", allow_duplicate=True),
     Output("btn-cancelar-robo", "disabled", allow_duplicate=True),
     Output("btn-salvar-relatorio", "disabled", allow_duplicate=True)],
    Input("intervalo-simulacao", "n_intervals"),
    prevent_initial_call=True
)
def atualizar_status_robo(n):
    # Pega o estado real do objeto Python
    status = robo_contratos.get_status()
    
    progress = status['progress']
    logs_data = status['logs']
    is_running = status['is_running']
    arquivo_pronto = status['arquivo_gerado']
    
    # Renderiza Logs HTML
    log_elements = []
    for log in logs_data:
        log_elements.append(html.Div(
            html.Span(log['msg'], style={"color": log['color'], "fontFamily": "Consolas"})
        ))
    
    # Se ainda estiver rodando
    if is_running:
        return (
            progress, f"{progress}%", "", log_elements, no_update, no_update, no_update, no_update, no_update
        )
    
    # SE TERMINOU (Sucesso ou Erro)
    else:
        cor_final = "success" if status['status_final'] == 'success' else "danger"
        btn_label = [DashIconify(icon="lucide:rotate-cw", width=20, className="me-2"), "REINICIAR"]
        
        return (
            100 if status['status_final'] == 'success' else progress, 
            "CONCLUÍDO" if status['status_final'] == 'success' else "PARADO", 
            cor_final,
            log_elements,
            True,   # Intervalo PAUSADO
            btn_label, 
            False,  # Btn Iniciar LIBERADO
            True,   # Btn Cancelar TRAVADO
            False if arquivo_pronto else True # Btn Baixar LIBERADO se tiver arquivo
        )

# Callback para Download do Arquivo
@callback(
    Output("download-relatorio-component", "data"),
    Input("btn-salvar-relatorio", "n_clicks"),
    prevent_initial_call=True
)
def baixar_relatorio_final(n):
    if robo_contratos.arquivo_gerado and os.path.exists(robo_contratos.arquivo_gerado):
        return dcc.send_file(robo_contratos.arquivo_gerado)
    return no_update

# =============================================================================
# MAIN (EXECUÇÃO)
# =============================================================================
if __name__ == '__main__':
    is_wsl = "microsoft" in platform.release().lower() or "wsl" in platform.release().lower()
    PORT = 8051 if is_wsl else 8085
    
    if os.environ.get("WERKZEUG_RUN_MAIN") is None:
        try:
            configurar_rede_automatica(PORT)
        except:
            pass 

    # CORREÇÃO: dev_tools_hot_reload=False e use_reloader=False
    # Isso impede que a criação dos arquivos ZIP e XLSX reiniciem o servidor e recarreguem a página.
    app.run(host='0.0.0.0', port=PORT, debug=True, dev_tools_hot_reload=False, use_reloader=False)