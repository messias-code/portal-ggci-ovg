"""
=============================================================================
ARQUIVO PRINCIPAL (ENTRY POINT) - ATUALIZADO
=============================================================================
"""
import dash
from dash import dcc, html, Input, Output, State, callback, ctx, no_update, ALL, callback_context
import dash_bootstrap_components as dbc
import unicodedata
import re

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
    layout_dashboard_admin,
    componentes_modais_admin,
    gerar_linhas_usuarios
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "Portal GGCI"

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='auth-store', storage_type='session'),
    html.Div(id='page-content')
])

# =============================================================================
# FUNÇÕES AUXILIARES GERAIS
# =============================================================================

def remove_acentos(texto):
    """Remove acentuação de uma string."""
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# =============================================================================
# ROTEADOR DE PÁGINAS (ROUTER)
# =============================================================================
@callback(Output('page-content', 'children'), Input('url', 'pathname'), Input('auth-store', 'data'))
def router(pathname, auth_data):
    if pathname == '/logout': return layout_login_principal()
    if pathname == '/' or not pathname: return layout_login_principal()
    
    if not auth_data or not auth_data.get('is_authenticated'): 
        return layout_login_principal()

    if pathname == '/home': return layout_home(auth_data)
    if pathname == '/softwares': return layout_menu_softwares(auth_data)
    if pathname == '/softwares/gerador-lista': return layout_ferramenta_inscricoes()
    if pathname == '/softwares/padronizador-ies': return layout_ferramenta_ies()

    # Rota Protegida de Gestão
    if pathname == '/gestao/dashboard': 
        if auth_data.get('is_admin'):
            return html.Div([layout_dashboard_admin(), componentes_modais_admin()])
        else:
            return layout_home(auth_data)

    return html.Div("Página não encontrada (404)", className="p-5 text-center text-muted")

# =============================================================================
# CALLBACKS: LOGIN E SEGURANÇA
# =============================================================================

@callback(
    [Output('auth-store', 'data', allow_duplicate=True), 
     Output('url', 'pathname', allow_duplicate=True), 
     Output('login-main-alert', 'children')], 
    Input('btn-login-main', 'n_clicks'), 
    [State('login-main-user', 'value'), State('login-main-password', 'value')], 
    prevent_initial_call=True
)
def realizar_login(n_clicks, user, pwd):
    if not n_clicks: return no_update, no_update, no_update
    if not user or not pwd: return no_update, no_update, dbc.Alert("Preencha todos os campos.", color="warning")
    
    dados_usuario, erro_msg = autenticar_usuario(user, pwd)
    
    if dados_usuario: 
        sessao = {
            'id': dados_usuario[0], 
            'nome': dados_usuario[1], 
            'sobrenome': dados_usuario[2], 
            'is_admin': dados_usuario[3], 
            'is_authenticated': True
        }
        return sessao, "/home", ""
    
    return no_update, no_update, dbc.Alert(erro_msg, color="danger")

@callback(Output('auth-store', 'data', allow_duplicate=True), Input('url', 'pathname'), prevent_initial_call=True)
def realizar_logout(path):
    if path == '/logout': return {}
    return no_update

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
    trigger = ctx.triggered_id
    
    if trigger == "btn-abrir-troca-senha": return True, "", "", "", ""
    if trigger == "btn-cancelar-troca": return False, "", "", "", ""
        
    if trigger == "btn-salvar-troca":
        if not atual or not nova or not confirma:
            return True, dbc.Alert("Preencha todos os campos.", color="warning"), no_update, no_update, no_update
        if nova != confirma:
            return True, dbc.Alert("As senhas não conferem.", color="danger"), no_update, no_update, no_update
            
        user_id = auth_data.get('id')
        sucesso, msg = atualizar_senha_usuario(user_id, atual, nova)
        
        if sucesso:
            return False, "", "", "", "" 
        else:
            return True, dbc.Alert(msg, color="danger"), no_update, no_update, no_update

    return no_update, no_update, no_update, no_update, no_update

@callback(Output("toast-acesso-negado", "is_open"), Input("btn-acesso-negado-gestao", "n_clicks"), prevent_initial_call=True)
def notificar_acesso_negado(n_clicks):
    return True

# =============================================================================
# CALLBACKS: FERRAMENTAS (NORMALIZADOR E FORMATADOR)
# =============================================================================

# --- 1. NORMALIZADOR DE DADOS (Lógica Corrigida: Remoção ANTES da Formatação) ---
@callback(
    [Output("output-ies", "value"),
     Output("badge-ies-entrada", "children"),
     Output("badge-ies-saida", "children"),
     Output("toast-ies", "children"),
     Output("toast-ies", "is_open"),
     Output("input-ies", "value"),
     Output("toast-ies", "header"),
     Output("toast-ies", "icon")],
    [Input("btn-processar-ies", "n_clicks"),
     Input("btn-limpar-ies", "n_clicks")],
    [State("input-ies", "value"),
     State("radio-case-ies", "value"),
     State("switch-accents-ies", "value"),
     State("radio-tipo-ies", "value"),
     State("input-remove-chars-ies", "value")]
)
def processar_normalizacao_avancada(n_processar, n_limpar, texto_entrada, case_type, remove_accents, output_type, remove_chars):
    ctx_trigger = callback_context
    if not ctx_trigger.triggered:
        return no_update, no_update, no_update, no_update, False, no_update, "Processado", "info"
        
    button_id = ctx_trigger.triggered[0]['prop_id'].split('.')[0]

    if button_id == "btn-limpar-ies":
        return "", "0 itens", "0 itens", "", False, "", "Limpeza", "secondary"

    if not texto_entrada:
        return "", "0 itens", "0 itens", "Nenhum dado inserido.", True, no_update, "Atenção", "warning"

    # --- VALIDAÇÃO ---
    alerta_espaco = False
    chars_to_remove_regex = ""
    
    if remove_chars:
        if " " in remove_chars:
            alerta_espaco = True
            remove_chars = remove_chars.replace(" ", "")
        
        if remove_chars:
            try:
                chars_to_remove_regex = f"[{re.escape(remove_chars)}]"
            except:
                pass

    # --- PROCESSAMENTO ---
    linhas = [line.strip() for line in texto_entrada.split('\n') if line.strip()]
    count_entrada = len(linhas)
    lista_processada = []

    for item in linhas:
        # 1. PRIMEIRO: Remove Caracteres Específicos (No texto original)
        # Isso garante que se eu mandar remover "A", ele remove só o maiúsculo antes de virar tudo maiúsculo.
        if chars_to_remove_regex:
            item = re.sub(chars_to_remove_regex, "", item)

        # 2. SEGUNDO: Remove Acentuação
        if remove_accents: 
            item = remove_acentos(item)

        # 3. TERCEIRO: Aplica a Formatação (Case)
        # Agora sim, o que sobrou é formatado.
        if case_type == "upper": 
            item = item.upper()
        elif case_type == "lower": 
            item = item.lower()
        elif case_type == "title": 
            item = item.title()
        
        # 4. QUARTO: Limpeza final de espaços
        item = " ".join(item.split())
        
        if item: 
            lista_processada.append(item)

    if output_type == "unique":
        lista_final = list(dict.fromkeys(lista_processada))
    else:
        lista_final = lista_processada

    resultado_texto = "\n".join(lista_final)
    count_saida = len(lista_final)
    
    if alerta_espaco:
        msg_toast = "Aviso: Espaços extras já são removidos automaticamente."
        header_toast = "Aviso"
        icon_toast = "warning"
    else:
        msg_toast = f"Sucesso! {count_saida} registros processados."
        header_toast = "Concluído"
        icon_toast = "success"

    return resultado_texto, f"{count_entrada} itens", f"{count_saida} itens", msg_toast, True, no_update, header_toast, icon_toast

# --- 2. FORMATADOR DE LISTAS (Antigo Inscrições) ---
@callback(
    [Output("output-inscricoes", "value"), 
     Output("input-inscricoes", "value"), 
     Output("badge-inscricoes-saida", "children"), 
     Output("badge-inscricoes-entrada", "children"), 
     Output("toast-inscricoes", "children"), 
     Output("toast-inscricoes", "is_open")],
    [Input("btn-processar-inscricoes", "n_clicks"), 
     Input("btn-limpar-inscricoes", "n_clicks")],
    [State("input-inscricoes", "value")], 
    prevent_initial_call=True
)
def processar_formatador_listas(n_gerar, n_limpar, texto_entrada):
    trigger = ctx.triggered_id
    
    if trigger == "btn-limpar-inscricoes": 
        return "", "", "0 itens", "0 itens", "", False 
        
    if trigger == "btn-processar-inscricoes":
        if not texto_entrada: 
            return no_update, no_update, no_update, no_update, no_update, no_update
            
        linhas = [linha.strip() for linha in texto_entrada.split("\n") if linha.strip()]
        qtd_entrada = len(linhas)
        
        # Remove duplicatas e ordena
        linhas_unicas = sorted(list(set(linhas)))
        
        # Formata com vírgula para SQL/Filtros
        resultado = ",".join(linhas_unicas)
        
        qtd_saida = len(linhas_unicas)
        duplicatas = qtd_entrada - qtd_saida
        
        msg_toast = f"Gerado! {qtd_saida} únicos. ({duplicatas} duplicatas removidas)" if duplicatas > 0 else f"Sucesso! {qtd_saida} itens processados."
        
        return resultado, no_update, f"{qtd_saida} únicos", f"{qtd_entrada} itens", msg_toast, True
        
    return no_update, no_update, no_update, no_update, no_update, no_update

# =============================================================================
# CALLBACKS: ADMINISTRAÇÃO (CRUD)
# =============================================================================

@callback(
    Output("tabela-usuarios-body", "children"),
    Input("input-pesquisa-usuario", "value")
)
def filtrar_usuarios_tabela(termo_pesquisa):
    df = listar_todos_usuarios()
    if termo_pesquisa:
        termo = termo_pesquisa.lower()
        df = df[
            df['primeiro_nome'].str.lower().str.contains(termo) |
            df['ultimo_nome'].str.lower().str.contains(termo) |
            df['username'].str.lower().str.contains(termo) |
            df['email'].str.lower().str.contains(termo)
        ]
    return gerar_linhas_usuarios(df)

@callback([Output("input-senha", "type"), Output("input-senha-confirma", "type")], Input("check-mostrar-senha-admin", "value"), prevent_initial_call=True)
def toggle_pwd_admin(val): return ("text", "text") if val else ("password", "password")

@callback([Output("modal-usuario", "is_open"), Output("modal-titulo-usuario", "children"), Output("store-edit-id", "data"), Output("input-primeiro-nome", "value"), Output("input-ultimo-nome", "value"), Output("input-email", "value"), Output("check-is-admin", "value"), Output("input-senha", "value"), Output("input-senha-confirma", "value"), Output("alert-modal-usuario", "children")], [Input("btn-novo-usuario", "n_clicks"), Input({"type": "btn-edit-user", "index": ALL}, "n_clicks"), Input("btn-cancelar-modal", "n_clicks"), Input("btn-salvar-usuario", "n_clicks")], [State("modal-usuario", "is_open"), State("store-edit-id", "data"), State("input-primeiro-nome", "value"), State("input-ultimo-nome", "value"), State("input-email", "value"), State("input-senha", "value"), State("input-senha-confirma", "value"), State("check-is-admin", "value")], prevent_initial_call=True)
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
        if not all([nome, sobrenome, email]): return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Campos obrigatórios!", color="warning")
        if not edit_id and not senha: return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Senha obrigatória para novos usuários.", color="warning")
        if senha and senha != senha2: return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Senhas não conferem!", color="danger")
        
        sucesso, msg = persistir_usuario(nome, sobrenome, email, senha, bool(is_admin), user_id=edit_id)
        if sucesso: return False, no_update, None, "", "", "", False, "", "", ""
        return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert(msg, color="danger")
    
    return no_update

@callback(Output("url", "pathname", allow_duplicate=True), [Input("modal-usuario", "is_open"), Input("modal-delete", "is_open")], prevent_initial_call=True)
def admin_reload_table(m1, m2):
    if not m1 and not m2: return "/gestao/dashboard"
    return no_update

@callback([Output("modal-delete", "is_open"), Output("store-delete-id", "data")], [Input({"type": "btn-delete-user", "index": ALL}, "n_clicks"), Input("btn-cancelar-delete", "n_clicks"), Input("btn-confirmar-delete", "n_clicks")], [State("store-delete-id", "data")], prevent_initial_call=True)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)