import dash
from dash import dcc, html, Input, Output, State, callback, ctx, no_update, ALL
import dash_bootstrap_components as dbc
import unicodedata
import re
# IMPORTANDO A NOVA FUNÇÃO alterar_senha_propria
from src.database import salvar_usuario, deletar_usuario, get_usuario_by_id, verificar_login, alterar_senha_propria
# Layouts completos devem ser importados
from src.layouts import login_main_layout, home_layout, login_gestao_layout, dashboard_layout, get_modals, softwares_layout, gerador_lista_layout, padronizador_ies_layout

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], suppress_callback_exceptions=True)
app.title = "Portal GGCI"

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='auth-store', storage_type='session'),
    html.Div(id='page-content')
])

# ... (Função normalizar_ies e Roteamento MANTIDOS) ...
def normalizar_ies(texto):
    if not texto: return ""
    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.upper()
    texto = re.sub(r"[^A-Z0-9\s\(\)\-]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto

@callback(Output('page-content', 'children'), Input('url', 'pathname'), Input('auth-store', 'data'))
def router(pathname, auth_data):
    if pathname == '/logout': return login_main_layout()
    if pathname == '/' or not pathname: return login_main_layout()
    if not auth_data or not auth_data.get('is_authenticated'): return login_main_layout()

    if pathname == '/home': return home_layout(auth_data)
    if pathname == '/softwares': return softwares_layout(auth_data)
    if pathname == '/softwares/gerador-lista': return gerador_lista_layout()
    if pathname == '/softwares/padronizador-ies': return padronizador_ies_layout()

    if pathname == '/gestao/login': return login_gestao_layout()
    if pathname == '/gestao/dashboard': return html.Div([dashboard_layout(), get_modals()])

    return html.Div("Página não encontrada (404)", className="p-5")

# --- CALLBACK: LOGIN PRINCIPAL (ATUALIZADO) ---
@callback(
    [Output('auth-store', 'data', allow_duplicate=True), 
     Output('url', 'pathname', allow_duplicate=True), 
     Output('login-main-alert', 'children')], 
    Input('btn-login-main', 'n_clicks'), 
    [State('login-main-user', 'value'), State('login-main-password', 'value')], 
    prevent_initial_call=True
)
def login_principal(n_clicks, user, pwd):
    if not n_clicks: return no_update, no_update, no_update
    if not user or not pwd: return no_update, no_update, dbc.Alert("Preencha todos os campos.", color="warning")
    
    # verificar_login agora retorna (dados_user, mensagem_erro)
    res, erro_msg = verificar_login(user, pwd)
    
    if res: 
        return {'id': res[0], 'nome': res[1], 'sobrenome': res[2], 'is_admin': res[3], 'is_authenticated': True}, "/home", ""
    
    # Se falhou, mostra a mensagem específica (ex: "Aguarde 10 min")
    return no_update, no_update, dbc.Alert(erro_msg, color="danger")

# --- NOVO CALLBACK: TROCA DE SENHA PELO USUÁRIO ---
@callback(
    [Output("modal-troca-senha", "is_open"),
     Output("alert-troca-senha", "children"),
     Output("meu-senha-atual", "value"),
     Output("meu-nova-senha", "value"),
     Output("meu-nova-senha-confirma", "value")],
    [Input("btn-abrir-troca-senha", "n_clicks"),
     Input("btn-cancel-troca", "n_clicks"),
     Input("btn-save-troca", "n_clicks")],
    [State("modal-troca-senha", "is_open"),
     State("meu-senha-atual", "value"),
     State("meu-nova-senha", "value"),
     State("meu-nova-senha-confirma", "value"),
     State("auth-store", "data")],
    prevent_initial_call=True
)
def user_change_password(btn_open, btn_cancel, btn_save, is_open, atual, nova, confirma, auth_data):
    trigger = ctx.triggered_id
    
    # Abrir modal
    if trigger == "btn-abrir-troca-senha":
        return True, "", "", "", ""
        
    # Fechar modal
    if trigger == "btn-cancel-troca":
        return False, "", "", "", ""
        
    # Salvar senha
    if trigger == "btn-save-troca":
        if not atual or not nova or not confirma:
            return True, dbc.Alert("Preencha todos os campos.", color="warning"), no_update, no_update, no_update
            
        if nova != confirma:
            return True, dbc.Alert("A nova senha e a confirmação não conferem.", color="danger"), no_update, no_update, no_update
            
        # Chama função do banco
        user_id = auth_data.get('id')
        sucesso, msg = alterar_senha_propria(user_id, atual, nova)
        
        if sucesso:
            # Sucesso: Fecha modal (ou mostra msg verde e limpa campos)
            return False, "", "", "", "" 
        else:
            # Erro: Mantém aberto e mostra erro
            return True, dbc.Alert(msg, color="danger"), no_update, no_update, no_update

    return no_update, no_update, no_update, no_update, no_update

# ... (MANTENHA OS OUTROS CALLBACKS: padronizador IES, gerador lista, gestão admin, etc.) ...
# Callback Padronizador IES
@callback([Output("output-ies", "value"), Output("input-ies", "value"), Output("badge-ies", "children"), Output("badge-ies-input", "children"), Output("notify-ies", "children"), Output("notify-ies", "is_open")], [Input("btn-processar-ies", "n_clicks"), Input("btn-limpar-ies", "n_clicks")], [State("input-ies", "value"), State("radio-tipo-ies", "value")], prevent_initial_call=True)
def processar_padronizacao_ies(n_process, n_clear, texto_entrada, tipo_saida):
    trigger = ctx.triggered_id
    if trigger == "btn-limpar-ies": return "", "", "0 itens", "0 itens", "", False
    if trigger == "btn-processar-ies":
        if not texto_entrada: return no_update, no_update, no_update, no_update, no_update, no_update
        linhas = [l for l in texto_entrada.split("\n") if l.strip()]
        qtd_entrada = len(linhas)
        linhas_normalizadas = [normalizar_ies(linha) for linha in linhas]
        if tipo_saida == "unique":
            lista_final = sorted(list(set(linhas_normalizadas)))
            lista_final = [x for x in lista_final if x]
            texto_final = "\n".join(lista_final)
            qtd_saida = len(lista_final)
            msg_toast = f"Concluído! {qtd_saida} nomes únicos."
            badge_msg = f"{qtd_saida} únicos"
        else:
            texto_final = "\n".join(linhas_normalizadas)
            qtd_saida = len(linhas_normalizadas)
            msg_toast = f"Concluído! {qtd_saida} linhas."
            badge_msg = f"{qtd_saida} itens"
        return texto_final, no_update, badge_msg, f"{qtd_entrada} itens", msg_toast, True
    return no_update, no_update, no_update, no_update, no_update, no_update

# Callback Gerador Lista
@callback([Output("output-lista", "value"), Output("input-lista", "value"), Output("badge-contagem", "children"), Output("notify-toast", "children"), Output("notify-toast", "is_open")], [Input("btn-gerar-lista", "n_clicks"), Input("btn-limpar-lista", "n_clicks")], [State("input-lista", "value")], prevent_initial_call=True)
def processar_lista(n_gerar, n_limpar, texto_entrada):
    trigger = ctx.triggered_id
    if trigger == "btn-limpar-lista": return "", "", "0 itens", "", False 
    if trigger == "btn-gerar-lista":
        if not texto_entrada: return no_update, no_update, no_update, no_update, no_update
        linhas = [linha.strip() for linha in texto_entrada.split("\n") if linha.strip()]
        linhas_unicas = sorted(list(set(linhas)))
        resultado = ",".join(linhas_unicas)
        qtd = len(linhas_unicas)
        return resultado, no_update, f"{qtd} únicos", f"Gerado! {qtd} itens.", True
    return no_update, no_update, no_update, no_update, no_update

# Callback Login Gestão
@callback([Output('url', 'pathname', allow_duplicate=True), Output('login-gestao-alert', 'children')], Input('btn-login-gestao', 'n_clicks'), [State('login-gestao-user', 'value'), State('login-gestao-password', 'value')], prevent_initial_call=True)
def login_gestao(n_clicks, user, pwd):
    if not n_clicks: return no_update, no_update
    if not user or not pwd: return no_update, dbc.Alert("Preencha campos.", color="warning")
    res, erro = verificar_login(user, pwd) # Agora retorna tupla
    if res:
        if not res[3]: return no_update, dbc.Alert("Acesso negado. Não é admin.", color="danger")
        return "/gestao/dashboard", ""
    return no_update, dbc.Alert("Credenciais inválidas.", color="danger")

# Callbacks Admin (Modal, Save, Delete) - Mantidos
@callback(Output('auth-store', 'data', allow_duplicate=True), Input('url', 'pathname'), prevent_initial_call=True)
def logout_handler(path):
    if path == '/logout': return {}
    return no_update

@callback([Output("novo-senha", "type"), Output("novo-senha-confirma", "type")], Input("check-mostrar-senha", "value"), prevent_initial_call=True)
def toggle_pwd(val): return ("text", "text") if val else ("password", "password")

@callback([Output("modal-user", "is_open"), Output("modal-title", "children"), Output("editing-user-id", "data"), Output("novo-nome", "value"), Output("novo-sobrenome", "value"), Output("novo-email", "value"), Output("novo-admin", "value"), Output("novo-senha", "value"), Output("novo-senha-confirma", "value"), Output("modal-alert", "children")], [Input("btn-open-modal", "n_clicks"), Input({"type": "edit-btn", "index": ALL}, "n_clicks"), Input("btn-close-modal", "n_clicks"), Input("btn-save-user", "n_clicks")], [State("modal-user", "is_open"), State("editing-user-id", "data"), State("novo-nome", "value"), State("novo-sobrenome", "value"), State("novo-email", "value"), State("novo-senha", "value"), State("novo-senha-confirma", "value"), State("novo-admin", "value")], prevent_initial_call=True)
def manage_modal(btn_new, btn_edit, btn_close, btn_save, is_open, edit_id, nome, sobrenome, email, senha, senha2, is_admin):
    trigger = ctx.triggered_id
    if not trigger: return no_update
    if trigger == "btn-open-modal": return True, "Cadastrar Usuário", None, "", "", "", False, "", "", ""
    if isinstance(trigger, dict) and trigger['type'] == 'edit-btn':
        user_data = get_usuario_by_id(trigger['index'])
        if user_data: return True, "Editar Usuário", trigger['index'], user_data['primeiro_nome'], user_data['ultimo_nome'], user_data['email'], bool(user_data['is_admin']), "", "", ""
        return no_update
    if trigger == "btn-close-modal": return False, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, ""
    if trigger == "btn-save-user":
        if not all([nome, sobrenome, email]): return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Campos obrigatórios!", color="warning")
        if not edit_id and not senha: return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Senha obrigatória!", color="warning")
        if senha and senha != senha2: return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert("Senhas não conferem!", color="danger")
        sucesso, msg = salvar_usuario(nome, sobrenome, email, senha, bool(is_admin), user_id=edit_id)
        if sucesso: return False, no_update, None, "", "", "", False, "", "", ""
        return True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, dbc.Alert(msg, color="danger")
    return no_update

@callback(Output("url", "pathname", allow_duplicate=True), [Input("modal-user", "is_open"), Input("modal-delete", "is_open")], prevent_initial_call=True)
def reload_dash(m1, m2):
    if not m1 and not m2: return "/gestao/dashboard"
    return no_update

@callback([Output("modal-delete", "is_open"), Output("deleting-user-id", "data")], [Input({"type": "delete-btn", "index": ALL}, "n_clicks"), Input("btn-cancel-delete", "n_clicks"), Input("btn-confirm-delete", "n_clicks")], [State("deleting-user-id", "data")], prevent_initial_call=True)
def delete_flow(btn_trash, btn_cancel, btn_confirm, del_id):
    trigger = ctx.triggered_id
    if not trigger: return no_update
    if isinstance(trigger, dict): return True, trigger['index']
    if trigger == "btn-cancel-delete": return False, None
    if trigger == "btn-confirm-delete":
        if del_id: deletar_usuario(del_id)
        return False, None
    return no_update

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)