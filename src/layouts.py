"""
=============================================================================
ARQUIVO: layouts.py
DESCRIÇÃO:
    Contém a interface visual (Front-end) da aplicação Dash.
=============================================================================
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
from .database import listar_todos_usuarios
from dash import html, dcc

# =============================================================================
# CONSTANTES DE ESTILIZAÇÃO
# =============================================================================
OVG_PINK = "#FF6B8B"
OVG_PURPLE = "#8E44AD"
OVG_YELLOW = "#FFCE54"
OVG_BLUE = "#4FC1E9"
OVG_GREEN = "#A0D468"
OVG_ORANGE = "#FA8231"

def estilo_card_menu(cor_borda):
    return {
        "backgroundColor": "rgba(255, 255, 255, 0.03)", 
        "borderRadius": "24px",
        "padding": "20px",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "height": "220px",
        "width": "280px",
        "cursor": "pointer",
        "transition": "all 0.3s ease",
        "border": f"1px solid {cor_borda}",
        "boxShadow": f"0 0 15px {cor_borda}20",
        "textDecoration": "none"
    }

# =============================================================================
# 1. TELA DE LOGIN PRINCIPAL
# =============================================================================
def layout_login_principal():
    return html.Div(className="login-container", children=[
        html.Div(className="main-container login-box", style={"border": f"1px solid {OVG_PINK}"}, children=[
            html.Img(src="/assets/logo.png", className="logo-img"),
            html.H3("Portal GGCI", className="text-center mb-2 font-weight-bold"),
            html.P("Gerência de Gestão e Controle de Informações", className="text-center text-muted mb-4", style={"fontSize": "0.9rem"}),
            dbc.Alert("Caso não possua acesso, contate o administrador do sistema.", color="info", className="mb-4 py-3", style={"fontSize": "0.85rem", "borderRadius": "10px"}),
            html.Div(id="login-main-alert"),
            dbc.Label("Usuário", className="fw-bold", style={"color": OVG_PINK}),
            dbc.Input(id="login-main-user", type="text", className="mb-3", style={"borderColor": "var(--border)"}),
            dbc.Label("Senha", className="fw-bold", style={"color": OVG_PINK}),
            dbc.Input(id="login-main-password", type="password", className="mb-4", style={"borderColor": "var(--border)"}),
            dbc.Button("ENTRAR", id="btn-login-main", className="fw-bold", style={
                "background": f"linear-gradient(90deg, {OVG_PINK}, {OVG_PURPLE})", 
                "color": "white", "border": "none", "width": "100%", "padding": "12px", "borderRadius": "10px"
            }),
        ])
    ])

# =============================================================================
# 2. TELA INICIAL (HOME)
# =============================================================================
def layout_home(dados_usuario):
    is_admin = dados_usuario.get('is_admin', False)
    OVG_ROSA_CLARO = "#F08EB3"
    OVG_ROSA_MEDIO = "#D45694"
    OVG_ROXO_REAL = "#8E6AB3"
    OVG_VERDE_REAL = "#A0D468"
    OVG_AMARELO_REAL = "#FFCE54"

    conteudo_card_gestao = html.Div(className="app-card-hover", children=[
        DashIconify(icon="lucide:shield-check", width=60, color=OVG_ROSA_CLARO), 
        html.H5("Gestão de Acessos", className="mt-4 text-center fw-bold", style={"color": "white"})
    ], style=estilo_card_menu(OVG_ROSA_CLARO))

    if is_admin:
        card_gestao = dcc.Link(conteudo_card_gestao, href="/gestao/dashboard", style={"textDecoration": "none"})
    else:
        card_gestao = html.Div(conteudo_card_gestao, id="btn-acesso-negado-gestao")

    modal_troca_senha = dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Alterar Minha Senha", className="fw-bold"), close_button=True, style={"borderBottom": f"2px solid {OVG_AMARELO_REAL}"}),
        dbc.ModalBody([
            html.Div([
                DashIconify(icon="lucide:fingerprint", width=50, color=OVG_AMARELO_REAL, className="mb-3"),
                html.P("Para sua segurança, atualize sua senha periodicamente.", className="text-muted small")
            ], className="text-center mb-4"),
            dbc.Label("Senha Atual", className="fw-bold", style={"color": OVG_AMARELO_REAL}),
            dbc.Input(id="input-senha-atual", type="password", placeholder="Digite sua senha atual", className="mb-3"),
            dbc.Label("Nova Senha", className="fw-bold", style={"color": OVG_AMARELO_REAL}),
            dbc.Input(id="input-nova-senha", type="password", placeholder="Nova senha", className="mb-2"),
            dbc.Input(id="input-nova-senha-confirma", type="password", placeholder="Confirme a nova senha", className="mb-3"),
            html.Div(id="feedback-troca-senha", className="mt-3")
        ], className="px-4 py-4"),
        dbc.ModalFooter([
            dbc.Button("CANCELAR", id="btn-cancelar-troca", color="light", className="px-4 fw-bold me-2"),
            dbc.Button("SALVAR NOVA SENHA", id="btn-salvar-troca", style={"backgroundColor": OVG_AMARELO_REAL, "border": "none", "color": "#333"}, className="px-4 fw-bold")
        ], style={"borderTop": "1px solid var(--border)"})
    ], id="modal-troca-senha", is_open=False, size="md", centered=True, backdrop="static")

    return html.Div(className="container-fluid p-4", children=[
        html.Div(className="main-container", style={"minHeight": "80vh", "maxWidth": "1400px", "margin": "40px auto 0 auto"}, children=[          
            dbc.Row([
                dbc.Col(html.Img(src="/assets/logo.png", style={"height": "85px"}), width="auto"),
                dbc.Col([
                    html.H3("Portal GGCI", className="m-0 fw-bold"),
                    html.Span("Central de Aplicações", className="text-muted", style={"fontSize": "1.1rem"})
                ], className="ps-3"),
                dbc.Col([
                    html.Span(f"Olá, {dados_usuario.get('nome', '')} {dados_usuario.get('sobrenome', '')}".strip().title() or "Olá, Usuário", className="me-3 text-muted fw-bold", style={"fontSize": "1.2rem"}),
                    dbc.Button([DashIconify(icon="lucide:power", width=20, className="me-2"), "Sair"], href="/logout", color="danger", outline=True, className="btn-nav")
                ], width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-5 align-items-center border-bottom pb-4", style={"borderColor": "var(--border)"}),

            dbc.Row([
                dbc.Col([card_gestao], width="100%", md="auto", className="m-3 d-flex justify-content-center"),
                dbc.Col([dcc.Link(html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:files", width=60, color=OVG_ROSA_MEDIO), 
                            html.H5("Documentações", className="mt-4 text-center fw-bold", style={"color": "white"})
                        ], style=estilo_card_menu(OVG_ROSA_MEDIO)), href="/documentacoes", style={"textDecoration": "none"})
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),
                dbc.Col([dcc.Link(html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:component", width=60, color=OVG_ROXO_REAL), 
                            html.H5("Dashboards", className="mt-4 text-center fw-bold", style={"color": "white"})
                        ], style=estilo_card_menu(OVG_ROXO_REAL)), href="/dashboards", style={"textDecoration": "none"})
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),
                dbc.Col([dcc.Link(html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:layers", width=60, color=OVG_VERDE_REAL), 
                            html.H5("Ferramentas", className="mt-4 text-center fw-bold", style={"color": "white"})
                        ], style=estilo_card_menu(OVG_VERDE_REAL)), href="/softwares", style={"textDecoration": "none"})
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),
                dbc.Col([html.Div(className="app-card-hover", id="btn-abrir-troca-senha", children=[
                            DashIconify(icon="lucide:fingerprint", width=60, color=OVG_AMARELO_REAL), 
                            html.H5("Alterar Senha", className="mt-4 text-center fw-bold", style={"color": "white"})
                        ], style=estilo_card_menu(OVG_AMARELO_REAL))
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),
            ], justify="center", className="mt-4"),

            modal_troca_senha,
            dbc.Toast("🔒 Funcionalidade exclusiva para Administradores.", id="toast-acesso-negado", header="Acesso Restrito", icon="danger", duration=4000, is_open=False, dismissable=True, style={"position": "fixed", "bottom": 20, "right": 20, "width": 350, "zIndex": 1050}),
        ])
    ])

# =============================================================================
# 3. MENU DE SOFTWARES
# =============================================================================
def layout_menu_softwares(user_data):
    OVG_ROSA_CLARO = "#F08EB3"
    OVG_ROSA_MEDIO = "#D45694"
    OVG_ROXO_REAL = "#8E6AB3"

    return html.Div(className="container-fluid p-4", children=[
        html.Div(className="main-container", style={"minHeight": "80vh", "maxWidth": "1400px", "margin": "40px auto 0 auto"}, children=[
            dbc.Row([
                dbc.Col(html.Img(src="/assets/logo.png", style={"height": "50px"}), width="auto"),
                dbc.Col([
                    html.H3("Ferramentas", className="m-0 fw-bold"), 
                    html.Span("Otimização de Rotinas Administrativas", className="text-muted", style={"fontSize": "1.1rem"})
                ], className="ps-3"),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left-circle", width=22, className="me-2"), "Voltar"], href="/home", color="light", outline=True, className="btn-nav"), width="auto", className="ms-auto")
            ], className="mb-5 align-items-center border-bottom pb-4", style={"borderColor": "var(--border)"}),
            
            dbc.Row([
                dbc.Col([dcc.Link(html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:brain-circuit", width=65, color=OVG_ROSA_CLARO), 
                            html.H5("Formatador de Listas", className="mt-4 text-center fw-bold", style={"color": "white", "marginBottom": "5px"}),
                            html.Span("Padronização de listas para consultas", className="text-center small text-muted", style={"fontSize": "0.85rem"})
                        ], style=estilo_card_menu(OVG_ROSA_CLARO)), href="/softwares/gerador-lista", style={"textDecoration": "none"})
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),
                
                dbc.Col([dcc.Link(html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:graduation-cap", width=65, color=OVG_ROSA_MEDIO), 
                            html.H5("Formatador de Dados", className="mt-4 text-center fw-bold", style={"color": "white", "marginBottom": "5px"}),
                            html.Span("Padronização e correção de registros", className="text-center small text-muted", style={"fontSize": "0.85rem"})
                        ], style=estilo_card_menu(OVG_ROSA_MEDIO)), href="/softwares/padronizador-ies", style={"textDecoration": "none"})
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),

                dbc.Col([dcc.Link(html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:bot", width=65, color=OVG_ROXO_REAL), 
                            html.H5("Analise de Documentações IA", className="mt-4 text-center fw-bold", style={"color": "white", "marginBottom": "5px"}),
                            html.Span("Extrator de dados processados", className="text-center small text-muted", style={"fontSize": "0.85rem"})
                        ], style=estilo_card_menu(OVG_ROXO_REAL)), href="/softwares/analise-contratos", style={"textDecoration": "none"})
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),

            ], justify="center", className="mt-5"),
        ])
    ])

# =============================================================================
# 4. FERRAMENTA: FORMATADOR DE LISTAS
# =============================================================================
def layout_ferramenta_inscricoes():
    OVG_ROSA_CLARO = "#F08EB3"
    return html.Div(className="container-fluid p-3 p-md-4", children=[ 
        html.Div(className="main-container d-flex flex-column", style={"minHeight": "85vh", "maxWidth": "1400px", "margin": "20px auto 0 auto"}, children=[
            dbc.Row([
                dbc.Col([
                    html.H3([DashIconify(icon="lucide:brain-circuit", className="me-2", color=OVG_ROSA_CLARO), "Formatador de Listas"], className="m-0 fw-bold"), 
                    html.Span("Limpeza automática para filtros SQL e Planilhas", className="text-muted", style={"fontSize": "1.1rem"})
                ]),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left-circle", width=25, className="me-2"), "Voltar"], href="/softwares", color="light", outline=True, className="btn-nav"), width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-4 pb-3 border-bottom align-items-center flex-grow-0", style={"borderColor": "var(--border)"}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Label("Lista Original (Excel/Texto):", className="fw-bold text-muted mb-0"), 
                        dbc.Badge("0 itens", id="badge-inscricoes-entrada", color="secondary", className="ms-2")
                    ], className="d-flex align-items-center mb-2"),
                    dbc.Textarea(id="input-inscricoes", className="mb-3 flex-grow-1", style={"backgroundColor": "rgba(0,0,0,0.2)", "color": "white", "border": "1px solid var(--border)", "fontSize": "0.95rem", "resize": "none", "height": "100%"}, placeholder="Cole a coluna de inscrições aqui..."),
                    dbc.Row([
                        dbc.Col(dbc.Button("LIMPAR", id="btn-limpar-inscricoes", color="secondary", className="w-100 fw-bold py-2"), width=12, md=3),
                        dbc.Col(dbc.Button("NORMALIZAR DADOS", id="btn-processar-inscricoes", className="w-100 fw-bold py-2", style={"backgroundColor": OVG_ROSA_CLARO, "border": "none"}), width=12, md=9),
                    ], className="g-2 flex-grow-0")
                ], md=6, className="d-flex flex-column mb-4 mb-md-0"), 
                
                dbc.Col([
                    html.Div([
                        dbc.Label("Lista Formatada (Pronta para Filtro):", className="fw-bold text-muted mb-0"), 
                        dbc.Badge("0 itens", id="badge-inscricoes-saida", style={"backgroundColor": OVG_ROSA_CLARO}, className="ms-2")
                    ], className="d-flex align-items-center mb-2 flex-grow-0"),
                    html.Div([
                        dbc.Textarea(
                            id="output-inscricoes", readonly=True, 
                            style={"backgroundColor": "rgba(0,0,0,0.4)", "color": OVG_ROSA_CLARO, "border": f"1px solid {OVG_ROSA_CLARO}", "fontFamily": "monospace", "fontSize": "1rem", "resize": "none", "width": "100%", "height": "100%", "padding": "15px"},
                            className="flex-grow-1"
                        ),
                        dbc.Button(
                            [DashIconify(icon="lucide:copy", width=22, color="white")], id="btn-copiar-lista",
                            style={"position": "absolute", "top": "15px", "right": "15px", "width": "45px", "height": "45px", "borderRadius": "8px", "padding": "0", "display": "flex", "alignItems": "center", "justifyContent": "center", "backgroundColor": OVG_ROSA_CLARO, "border": "none", "zIndex": "100", "boxShadow": "0 4px 10px rgba(0,0,0,0.3)"}
                        )
                    ], className="d-flex flex-column flex-grow-1 position-relative h-100"), 
                ], md=6, className="d-flex flex-column"),
            ], className="flex-grow-1 align-items-stretch"), 
            
            dbc.Collapse(
                dbc.Alert([
                    html.H5([DashIconify(icon="lucide:alert-circle", className="me-2"), html.Span("Itens Duplicados Removidos", id="titulo-qtd-duplicatas")], className="alert-heading fw-bold mb-1", style={"fontSize": "1rem"}),
                    html.Div("Valores duplicados são removidos por padrão", className="small mb-2", style={"opacity": "0.9"}),
                    html.Hr(className="my-2"), 
                    html.Div(id="conteudo-duplicatas", className="small", style={"fontFamily": "monospace", "maxHeight": "100px", "overflowY": "auto"})
                ], color="warning", className="mt-3", style={"backgroundColor": "rgba(255, 193, 7, 0.1)", "color": "#ffc107", "border": "1px solid #ffc107"}),
                id="collapse-duplicatas", is_open=False
            ),
            dbc.Toast("✅ Dados normalizados com sucesso!", id="toast-inscricoes", header="Concluído", icon="success", duration=4000, is_open=False, style={"position": "fixed", "bottom": 20, "right": 20, "width": 300}),
            dbc.Toast("📋 Conteúdo copiado para a área de transferência.", id="toast-copy-lista-success", header="Copiado", icon="success", duration=3000, is_open=False, style={"position": "fixed", "bottom": 20, "right": 20, "width": 350, "zIndex": 1060}),
        ])
    ])

# =============================================================================
# 5. FERRAMENTA: NORMALIZADOR DE DADOS
# =============================================================================
def layout_ferramenta_ies():
    OVG_ROSA_MEDIO = "#D45694" 
    return html.Div(className="container-fluid p-3 p-md-4", children=[ 
        html.Div(className="main-container d-flex flex-column", style={"minHeight": "85vh", "maxWidth": "1400px", "margin": "20px auto 0 auto"}, children=[
            dbc.Row([
                dbc.Col([
                    html.H3([DashIconify(icon="lucide:graduation-cap", className="me-2", color=OVG_ROSA_MEDIO), "Formatador de Dados"], className="m-0 fw-bold"), 
                    html.Span("Limpeza e Padronização de Textos", className="text-muted", style={"fontSize": "1.1rem"})
                ]),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left-circle", width=25, className="me-2"), "Voltar"], href="/softwares", color="light", outline=True, className="btn-nav"), width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-4 pb-3 border-bottom align-items-center flex-grow-0", style={"borderColor": "var(--border)"}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Label("Dados Originais (Coluna do Excel):", className="fw-bold text-muted mb-0"), 
                        dbc.Badge("0 itens", id="badge-ies-entrada", color="secondary", className="ms-2")
                    ], className="d-flex align-items-center mb-2"),
                    dbc.Textarea(id="input-ies", className="mb-3", style={"backgroundColor": "rgba(0,0,0,0.2)", "color": "white", "border": "1px solid var(--border)", "fontSize": "0.95rem", "resize": "none", "height": "200px"}, placeholder="Cole sua lista aqui...\n\nExemplo:\nFaculdade Unip\nPUC Goias\nUFG - Campus 1"),
                    dbc.Card([
                        dbc.CardHeader("Configurações de Padronização", className="fw-bold small text-white py-2", style={"backgroundColor": "rgba(255,255,255,0.05)", "borderBottom": "1px solid rgba(255,255,255,0.1)"}),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("Formatação de Texto:", className="fw-bold text-muted small mb-1"),
                                    dbc.RadioItems(
                                        options=[{"label": "Original", "value": "original"}, {"label": "MAIÚSCULO", "value": "upper"}, {"label": "minúsculo", "value": "lower"}, {"label": "Capitalize", "value": "title"}],
                                        value="original", id="radio-case-ies", inline=True, style={"color": "white", "fontSize": "0.85rem"}, className="d-flex justify-content-between gap-2"
                                    )
                                ], width=12, className="mb-3"),
                            ]),
                            html.Hr(style={"borderColor": "rgba(255,255,255,0.1)", "margin": "5px 0 15px 0"}),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Switch(id="switch-accents-ies", label="Remover Acentuação", value=False, style={"color": "white", "fontSize": "0.9rem"}, className="mb-3"),
                                    dbc.Label("Tipo de Lista (Saída):", className="fw-bold text-muted small mb-1"),
                                    dbc.RadioItems(options=[{"label": "Valores Correspondentes (Mesma ordem)", "value": "full"}, {"label": "Valores Únicos (Remove repetidos)", "value": "unique"}], value="full", id="radio-tipo-ies", style={"color": "white", "fontSize": "0.85rem"}, labelStyle={"marginBottom": "5px"}),
                                ], width=6, className="border-end border-secondary pe-3"), 
                                dbc.Col([
                                    dbc.Label("Remover Caracteres Específicos:", className="fw-bold text-muted small mb-1"),
                                    dbc.Input(id="input-remove-chars-ies", placeholder="Digite aqui... Ex: - . / ( ) A 1", type="text", style={"backgroundColor": "rgba(0,0,0,0.3)", "color": "white", "borderColor": "var(--border)", "fontSize": "0.9rem", "height": "38px"}),
                                    dbc.FormText(["Insira caracteres, letras ou números.", html.Br(), "Por padrão espaçamentos extras já são removidos."], color="muted", style={"fontSize": "0.75rem"}),
                                ], width=6, className="ps-3"),
                            ]),
                        ], className="p-3")
                    ], className="mb-3 flex-grow-0", style={"backgroundColor": "rgba(255,255,255,0.02)", "border": "1px solid var(--border)"}),
                    dbc.Row([
                        dbc.Col(dbc.Button("LIMPAR", id="btn-limpar-ies", color="secondary", className="w-100 fw-bold py-2"), width=12, md=3),
                        dbc.Col(dbc.Button("NORMALIZAR DADOS", id="btn-processar-ies", className="w-100 fw-bold py-2", style={"backgroundColor": OVG_ROSA_MEDIO, "border": "none"}), width=12, md=9),
                    ], className="g-2 mt-auto")
                ], md=6, className="d-flex flex-column mb-4 mb-md-0"),

                dbc.Col([
                    html.Div([
                        dbc.Label("Dados Normalizados:", className="fw-bold text-muted mb-0"), 
                        dbc.Badge("0 itens", id="badge-ies-saida", style={"backgroundColor": OVG_ROSA_MEDIO}, className="ms-2")
                    ], className="d-flex align-items-center mb-2 flex-grow-0"),
                    html.Div([
                        dbc.Textarea(
                            id="output-ies", readonly=True, 
                            style={"backgroundColor": "rgba(0,0,0,0.4)", "color": OVG_ROSA_MEDIO, "border": f"1px solid {OVG_ROSA_MEDIO}", "fontFamily": "monospace", "fontSize": "1rem", "resize": "none", "width": "100%", "height": "100%", "padding": "15px", "display": "block"},
                            className="flex-grow-1"
                        ),
                        dbc.Button(
                            [DashIconify(icon="lucide:copy", width=22, color="white")], id="btn-copiar-manual",
                            style={"position": "absolute", "top": "15px", "right": "15px", "width": "45px", "height": "45px", "borderRadius": "8px", "padding": "0", "display": "flex", "alignItems": "center", "justifyContent": "center", "backgroundColor": OVG_ROSA_MEDIO, "border": "none", "zIndex": "100", "boxShadow": "0 4px 10px rgba(0,0,0,0.3)"}
                        )
                    ], className="d-flex flex-column flex-grow-1 position-relative"), 
                ], md=6, className="d-flex flex-column"), 
            ], className="flex-grow-1 align-items-stretch"), 
            
            dbc.Toast(id="toast-ies", header="Processado", icon="info", duration=5000, is_open=False, dismissable=True, style={"position": "fixed", "bottom": 20, "right": 20, "width": 350, "zIndex": 1050}),
            dbc.Toast("📋 Conteúdo copiado para a área de transferência.", id="toast-copy-success", header="Copiado", icon="success", duration=3000, is_open=False, style={"position": "fixed", "bottom": 20, "right": 20, "width": 350, "zIndex": 1060}),
        ])
    ])

# =============================================================================
# 6. FERRAMENTA: ANÁLISE DE CONTRATOS IA (INTERFACE VISUAL COMPACTA)
# =============================================================================
def layout_ferramenta_analise_contratos():
    OVG_ROXO_REAL = "#8E6AB3"
    OVG_ROSA_CLARO = "#F08EB3"

    estilo_switch = {
        "fontSize": "0.85rem", 
        "marginBottom": "0.3rem", 
        "whiteSpace": "nowrap", 
        "overflow": "hidden", 
        "textOverflow": "ellipsis"
    }
    
    estilo_barra = {
        "height": "20px", 
        "fontSize": "0.8rem", 
        "fontWeight": "bold", 
        "backgroundColor": "rgba(255,255,255,0.1)", 
        "--bs-progress-bar-bg": OVG_ROSA_CLARO,
        "borderRadius": "6px",
        "width": "100%"
    }

    # MODAL DE DOWNLOAD COM CORES INVERTIDAS
    modal_download = dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Opções de Download", className="fw-bold"), close_button=True, style={"borderBottom": f"1px solid {OVG_ROSA_CLARO}"}),
        dbc.ModalBody([
            html.P("Como você deseja baixar os resultados?", className="text-muted text-center mb-4"),
            dbc.Row([
                dbc.Col(dbc.Button(
                    [DashIconify(icon="lucide:file-spreadsheet", width=30, className="mb-2", style={"display": "block", "margin": "0 auto"}), "Planilha Principal", html.Br(), html.Span("(Apenas relatório final)", style={"fontSize": "0.75rem", "fontWeight": "normal"})], 
                    id="btn-baixar-principal", className="w-100 fw-bold py-3 h-100", style={"backgroundColor": OVG_ROXO_REAL, "border": "none", "color": "white", "borderRadius": "12px", "boxShadow": "0 4px 10px rgba(142, 68, 173, 0.4)"}
                ), width=6),
                dbc.Col(dbc.Button(
                    [DashIconify(icon="lucide:folder-archive", width=30, className="mb-2", style={"display": "block", "margin": "0 auto"}), "Pacote Completo", html.Br(), html.Span("(Bases, ZIP e Temporários)", style={"fontSize": "0.75rem", "fontWeight": "normal"})], 
                    id="btn-baixar-completo", className="w-100 fw-bold py-3 h-100", outline=True, color="light", style={"borderRadius": "12px", "borderWidth": "2px"}
                ), width=6),
            ], className="g-3")
        ], className="p-4")
    ], id="modal-download-contratos", is_open=False, size="lg", centered=True)

    return html.Div(className="container-fluid p-3 p-md-4", children=[ 
        html.Div(className="main-container d-flex flex-column", style={"height": "90vh", "maxWidth": "1400px", "margin": "20px auto 0 auto", "overflow": "hidden"}, children=[
            
            dcc.Download(id="download-relatorio-component"),
            # --- CABEÇALHO ---
            dbc.Row([
                dbc.Col([
                    html.H3([DashIconify(icon="lucide:bot", className="me-2", color=OVG_ROXO_REAL), "Analise de Documentações IA"], className="m-0 fw-bold"), 
                    html.Span("Automação para Análise Contratos Processados (Selenium + SQL)", className="text-muted", style={"fontSize": "1.1rem"})
                ]),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left-circle", width=24, className="me-2"), "Voltar"], href="/softwares", color="light", outline=True, className="btn-nav"), width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-4 pb-3 border-bottom align-items-center flex-grow-0", style={"borderColor": "var(--border)"}),
            
            # --- CONFIGURAÇÕES (CARD COMPACTO) ---
            dbc.Card([
                dbc.CardHeader("Configurações de Extração", className="fw-bold small text-white py-2", style={"backgroundColor": "rgba(255,255,255,0.05)", "borderBottom": "1px solid rgba(255,255,255,0.1)"}),
                dbc.CardBody([
                    dbc.Row([
                        # COLUNA ESQUERDA - DOCUMENTOS (TRAVADOS NA LÓGICA REAL)
                        dbc.Col([
                            dbc.Label("TIPOS DE DOCUMENTOS", className="fw-bold text-muted small mb-2"),
                            
                            dbc.Switch(id="sw-docs-todos", label="TODOS", value=True, style=estilo_switch),
                            dbc.Switch(id="sw-contratos", label="CONTRATO DE PRESTAÇÃO DE SERVIÇOS EDUCACIONAIS OU COMPROVANTE DE MATRÍCULA", value=False, style=estilo_switch),
                            dbc.Switch(id="sw-financeiro", label="COMPROVANTE DE FINANCIAMENTO", value=False, style=estilo_switch),
                            dbc.Switch(id="sw-beneficios", label="COMPROVANTE OUTROS BENEFÍCIOS", value=False, style=estilo_switch),
                            dbc.Switch(id="sw-riaf", label="RIAF – RESUMO DE INFORMAÇÕES ACADÊMICAS E FINANCEIRAS", value=False, style=estilo_switch),
                        ], md=6, className="border-end border-secondary pe-3"),                        
                        # COLUNA DIREITA
                        dbc.Col([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Label("ANOS LETIVOS", className="fw-bold text-muted small mb-2"),
                                    dbc.Switch(id="sw-ano-todos", label="TODOS", value=True, style=estilo_switch),
                                    dbc.Switch(id="sw-ano-2025", label="2025", value=False, style=estilo_switch),
                                    dbc.Switch(id="sw-ano-2026", label="2026", value=False, style=estilo_switch),
                                ], width=4),
                                
                                dbc.Col([
                                    dbc.Label("SEMESTRES", className="fw-bold text-muted small mb-2"),
                                    dbc.Switch(id="sw-sem-todos", label="TODOS", value=True, style=estilo_switch),
                                    dbc.Switch(id="sw-sem-1", label="1º Semestre", value=False, style=estilo_switch),
                                    dbc.Switch(id="sw-sem-2", label="2º Semestre", value=False, style=estilo_switch),
                                ], width=4),
                                
                                dbc.Col([
                                    dbc.Label("FORMATO", className="fw-bold text-muted small mb-2"),
                                    dbc.RadioItems(
                                        options=[
                                            {"label": "Excel (.xlsx)", "value": "excel"}, 
                                            {"label": "CSV (.csv)", "value": "csv", "disabled": True} # CSV TRAVADO
                                        ],
                                        value="excel", # Padrão Excel
                                        id="radio-saida-contratos",
                                        style={"fontSize": "0.85rem"}, labelStyle={"marginBottom": "5px"}
                                    ),
                                ], width=4),
                            ])
                        ], md=6, className="ps-3"),
                    ])
                ], className="p-3")
            ], className="mb-3 flex-grow-0", style={"backgroundColor": "rgba(255,255,255,0.02)", "border": "1px solid var(--border)"}),

            # --- ÁREA DE CONTROLE E LOGS (Mantida igual) ---
            html.Div([
                dbc.Row([
                    dbc.Col(dbc.Button(
                        [DashIconify(icon="lucide:play", width=18, className="me-2"), "INICIAR"], 
                        id="btn-iniciar-robo", className="btn-sm fw-bold d-flex align-items-center justify-content-center shadow-lg",
                        style={"backgroundColor": OVG_ROXO_REAL, "border": "none", "height": "38px", "minWidth": "110px"}
                    ), width="auto"),
                    
                    dbc.Col(dbc.Button(
                        [DashIconify(icon="lucide:circle-stop", width=18, className="me-2"), "PARAR"], 
                        id="btn-cancelar-robo", color="danger", outline=True, disabled=True, 
                        className="btn-sm fw-bold d-flex align-items-center justify-content-center shadow-lg",
                        style={"height": "38px"}
                    ), width="auto"),
                    
                    dbc.Col([
                        dbc.Progress(id="barra-progresso-geral", value=0, label="0%", striped=True, animated=True, style=estilo_barra)
                    ], width=True, className="d-flex align-items-center px-3"),
                    
                    dbc.Col(dbc.Button(
                        [DashIconify(icon="lucide:download", width=18, className="me-2"), "BAIXAR"], 
                        id="btn-salvar-relatorio", disabled=True, 
                        className="btn-sm fw-bold d-flex align-items-center justify-content-center shadow-lg",
                        style={"backgroundColor": OVG_ROXO_REAL, "border": "none", "color": "white", "height": "38px"}
                    ), width="auto"),
                ], className="mb-3 align-items-center g-2"),

                html.Div(
                    id="terminal-logs",
                    children=[html.Div(">> Aguardando comando...", className="text-muted")],
                    style={
                        "backgroundColor": "#0c0c0c",
                        "border": "1px solid #333",
                        "borderRadius": "5px",
                        "fontFamily": "Consolas, 'Courier New', monospace",
                        "fontSize": "0.9rem",
                        "color": OVG_ROSA_CLARO,
                        "padding": "15px",
                        "overflowY": "auto",
                        "display": "flex",
                        "flexDirection": "column",
                        "boxShadow": "inset 0 0 10px #000"
                    },
                    className="flex-grow-1"
                ),

            ], style={"flex": "1", "display": "flex", "flexDirection": "column", "overflow": "hidden"}),
            
            modal_download,
            dcc.Interval(id="intervalo-simulacao", interval=800, n_intervals=0, disabled=True),
            dcc.Store(id="store-simulacao-estado", data={"progress": 0, "logs": []})
        ])
    ])

# =============================================================================
# 7. DOCUMENTAÇÕES (PLACEHOLDER)
# =============================================================================
def layout_documentacoes():
    OVG_ROSA_MEDIO = "#D45694"
    return html.Div(className="container-fluid p-3 p-md-4", children=[ 
        html.Div(className="main-container d-flex flex-column", style={"minHeight": "85vh", "maxWidth": "1400px", "margin": "20px auto 0 auto"}, children=[
            dbc.Row([
                dbc.Col([
                    html.H3([DashIconify(icon="lucide:files", className="me-2", color=OVG_ROSA_MEDIO), "Documentações"], className="m-0 fw-bold"), 
                    html.Span("Central de Manuais e Procedimentos", className="text-muted", style={"fontSize": "1.1rem"})
                ]),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left-circle", width=25, className="me-2"), "Voltar"], href="/home", color="light", outline=True, className="btn-nav"), width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-4 pb-3 border-bottom align-items-center flex-grow-0", style={"borderColor": "var(--border)"}),
            
            html.Div([
                html.Div([
                    DashIconify(icon="lucide:construction", width=80, color="rgba(255,255,255,0.2)"),
                    html.H4("Módulo em Desenvolvimento", className="mt-3 text-muted"),
                    html.P("A central de documentos está sendo estruturada.", className="text-muted small")
                ], className="d-flex flex-column align-items-center justify-content-center h-100")
            ], style={"flex": "1", "backgroundColor": "rgba(255,255,255,0.02)", "borderRadius": "20px", "border": "1px dashed rgba(255,255,255,0.1)", "minHeight": "400px"})
        ])
    ])

# =============================================================================
# 8. DASHBOARDS (PLACEHOLDER)
# =============================================================================
def layout_dashboards():
    OVG_ROXO_REAL = "#8E6AB3"
    return html.Div(className="container-fluid p-3 p-md-4", children=[ 
        html.Div(className="main-container d-flex flex-column", style={"minHeight": "85vh", "maxWidth": "1400px", "margin": "20px auto 0 auto"}, children=[
            dbc.Row([
                dbc.Col([
                    html.H3([DashIconify(icon="lucide:component", className="me-2", color=OVG_ROXO_REAL), "Dashboards"], className="m-0 fw-bold"), 
                    html.Span("Indicadores e Métricas", className="text-muted", style={"fontSize": "1.1rem"})
                ]),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left-circle", width=25, className="me-2"), "Voltar"], href="/home", color="light", outline=True, className="btn-nav"), width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-4 pb-3 border-bottom align-items-center flex-grow-0", style={"borderColor": "var(--border)"}),
            
            html.Div([
                html.Div([
                    DashIconify(icon="lucide:construction", width=80, color="rgba(255,255,255,0.2)"),
                    html.H4("Módulo em Desenvolvimento", className="mt-3 text-muted"),
                    html.P("Os painéis de indicadores estão sendo construídos.", className="text-muted small")
                ], className="d-flex flex-column align-items-center justify-content-center h-100")
            ], style={"flex": "1", "backgroundColor": "rgba(255,255,255,0.02)", "borderRadius": "20px", "border": "1px dashed rgba(255,255,255,0.1)", "minHeight": "400px"})
        ])
    ])

# =============================================================================
# 9. GESTÃO DE ACESSOS (Dashboard Admin)
# =============================================================================

def gerar_linhas_usuarios(df):
    rows = []
    for index, row in df.iterrows():
        is_main_admin = (row['id'] == 1) 
        
        rows.append(html.Tr([
            html.Td(row['id'], style={"verticalAlign": "middle"}), 
            html.Td(f"{row['primeiro_nome']} {row['ultimo_nome']}", style={"verticalAlign": "middle"}), 
            html.Td(row['username'], style={"verticalAlign": "middle"}), 
            html.Td(row['email'], style={"verticalAlign": "middle"}), 
            html.Td("Admin" if row['is_admin'] else "Usuário", style={"verticalAlign": "middle"}),
            html.Td([
                dbc.Button(
                    DashIconify(icon="lucide:user-cog", width=18), 
                    id={"type": "btn-edit-user", "index": row['id']}, 
                    style={"backgroundColor": "#FFCE54", "border": "none", "color": "#333", "display": "inline-flex", "alignItems": "center", "justifyContent": "center", "padding": "8px"}, 
                    size="sm", className="me-2", n_clicks=0
                ),
                dbc.Button(
                    DashIconify(icon="lucide:user-minus", width=18), 
                    id={"type": "btn-delete-user", "index": row['id']}, 
                    color="danger", size="sm", n_clicks=0, disabled=is_main_admin,
                    style={"display": "inline-flex", "alignItems": "center", "justifyContent": "center", "padding": "8px"}
                )
            ], style={"textAlign": "center", "verticalAlign": "middle"})
        ]))
    return rows

def layout_dashboard_admin():
    OVG_ROSA_CLARO = "#F08EB3"
    df = listar_todos_usuarios()
    rows = gerar_linhas_usuarios(df)
    style_th = {"color": OVG_ROSA_CLARO, "borderBottom": f"1px solid {OVG_ROSA_CLARO}", "borderTop": "none", "verticalAlign": "middle", "fontWeight": "bold"}
    
    tabela_header = [html.Thead(html.Tr([
        html.Th("ID", style=style_th), html.Th("Nome", style=style_th), html.Th("Login", style=style_th), 
        html.Th("Email", style=style_th), html.Th("Perfil", style=style_th), html.Th("Ações", style={**style_th, "textAlign": "center"}) 
    ]))] 
    
    return html.Div(className="container-fluid p-4", children=[
        html.Div(className="main-container", style={"minHeight": "80vh", "maxWidth": "1400px", "margin": "20px auto 0 auto"}, children=[
            dbc.Row([
                dbc.Col(html.Img(src="/assets/logo.png", style={"height": "60px"}), width="auto"),
                dbc.Col([
                    html.H3("Gestão de Acessos", className="m-0 fw-bold", style={"lineHeight": "1.2", "color": "white"}), 
                    html.Span("Controle de permissões e usuários", className="text-muted", style={"fontSize": "1rem", "display": "block"})
                ], className="ps-3 d-flex flex-column justify-content-center"),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left-circle", width=22, className="me-2"), "Voltar"], href="/home", color="light", outline=True, className="btn-nav"), width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-4 pb-3 border-bottom align-items-center", style={"borderColor": "var(--border)"}),
            
            dbc.Row([
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText(DashIconify(icon="lucide:user-search", width=20, color=OVG_ROSA_CLARO)),
                        dbc.Input(id="input-pesquisa-usuario", placeholder="Buscar por nome, login ou email...", type="text"),
                    ], className="mb-3", style={"backgroundColor": "transparent", "maxWidth": "800px"}),
                ], width=12, md=8),
                dbc.Col([
                    dbc.Button([DashIconify(icon="lucide:user-plus-2", className="me-2", width=20), "Novo Usuário"], id="btn-novo-usuario", className="w-100 fw-bold d-flex align-items-center justify-content-center", 
                       style={"backgroundColor": OVG_ROSA_CLARO, "border": "none", "color": "white", "borderRadius": "10px", "height": "40px", "marginTop": "1px"}, n_clicks=0),
                ], width=12, md=4, className="mb-3") 
            ], className="align-items-start"),

            dbc.Table(tabela_header + [html.Tbody(rows, id="tabela-usuarios-body")], bordered=True, hover=True, responsive=True, striped=True, className="table-dark", style={"--bs-table-border-color": "var(--border)"}),
            html.Div(id="container-modais") 
        ])
    ])

def componentes_modais_admin():
    OVG_ROSA_CLARO = "#F08EB3"
    return html.Div([
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="modal-titulo-usuario", className="fw-bold"), close_button=True, style={"borderBottom": f"2px solid {OVG_ROSA_CLARO}"}),
            dbc.ModalBody([
                html.Div([DashIconify(icon="lucide:user-cog", width=50, color=OVG_ROSA_CLARO, className="mb-3"), html.P("Preencha os dados abaixo para gerenciar o acesso do colaborador.", className="text-muted small")], className="text-center mb-4"),
                dbc.Row([dbc.Col([dbc.Checkbox(id="check-is-admin", label="Privilégios de Administrador", style={"fontWeight": "bold", "color": OVG_ROSA_CLARO})], className="d-flex justify-content-end mb-3")]),
                dbc.Row([dbc.Col([dbc.Label("Primeiro Nome", className="fw-bold small"), dbc.Input(id="input-primeiro-nome", placeholder="Ex: João")], width=6), dbc.Col([dbc.Label("Último Nome", className="fw-bold small"), dbc.Input(id="input-ultimo-nome", placeholder="Ex: Silva")], width=6)], className="mb-3"),
                dbc.Label("E-mail Corporativo (@ovg.org.br)", className="fw-bold small"), dbc.Input(id="input-email", type="email", placeholder="email@ovg.org.br", className="mb-3"),
                html.Div([dbc.Label("Senha do Sistema", className="fw-bold small"), dbc.Input(id="input-senha", type="password", placeholder="Digite a senha", className="mb-2"), dbc.Input(id="input-senha-confirma", type="password", placeholder="Confirme a senha", className="mb-2"), dbc.Checkbox(id="check-mostrar-senha-admin", label="Mostrar caracteres da senha", className="small text-muted")], className="mb-2"),
                html.Div(id="alert-modal-usuario", className="mt-3")
            ], className="px-4 py-4"),
            dbc.ModalFooter([dbc.Button("CANCELAR", id="btn-cancelar-modal", color="light", className="px-4 fw-bold me-2", style={"opacity": "0.8"}), dbc.Button("SALVAR ALTERAÇÕES", id="btn-salvar-usuario", style={"backgroundColor": OVG_ROSA_CLARO, "border": "none", "color": "white"}, className="px-4 fw-bold")], style={"borderTop": "1px solid var(--border)"})
        ], id="modal-usuario", is_open=False, size="lg", centered=True, backdrop="static"),
        
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão", className="fw-bold text-danger")),
            dbc.ModalBody([html.Div([DashIconify(icon="lucide:alert-triangle", width=50, color="#dc3545", className="mb-3"), html.H5("Você tem certeza?", className="fw-bold"), html.P("⚠️ Atenção: Esta ação é irreversível. Deseja continuar?", className="text-muted")], className="text-center p-3")]),
            dbc.ModalFooter([dbc.Button("NÃO, CANCELAR", id="btn-cancelar-delete", color="light", className="fw-bold me-2"), dbc.Button("SIM, EXCLUIR", id="btn-confirmar-delete", color="danger", className="fw-bold")])
        ], id="modal-delete", is_open=False, centered=True),
        
        dcc.Store(id="store-edit-id", data=None), 
        dcc.Store(id="store-delete-id", data=None)
    ])