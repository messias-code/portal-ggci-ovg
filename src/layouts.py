"""
=============================================================================
MÓDULO DE LAYOUTS (FRONT-END)
=============================================================================
Contém a estrutura visual de todas as páginas da aplicação.
Utiliza Dash Bootstrap Components para responsividade e consistência.

Padrão de Cores (Identidade Visual OVG):
- Rosa:   #FF6B8B
- Roxo:   #8E44AD
- Amarelo:#FFCE54
- Azul:   #4FC1E9
- Verde:  #A0D468
- Laranja:#FA8231
=============================================================================
"""
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash_iconify import DashIconify
# Importação com nome refatorado
from .database import listar_todos_usuarios

# --- CONSTANTES DE ESTILO ---
OVG_PINK = "#FF6B8B"
OVG_PURPLE = "#8E44AD"
OVG_YELLOW = "#FFCE54"
OVG_BLUE = "#4FC1E9"
OVG_GREEN = "#A0D468"
OVG_ORANGE = "#FA8231"

def estilo_card_menu(cor_borda):
    """
    Gera o estilo CSS padrão para os cartões de navegação do menu.
    Cria um efeito de vidro translúcido com borda colorida.
    """
    return {
        "backgroundColor": "rgba(255, 255, 255, 0.03)",
        "borderRadius": "16px",
        "padding": "40px",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "height": "240px",
        "width": "240px",
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
        html.Div(className="main-container login-box", style={"border": f"1px solid {OVG_PURPLE}"}, children=[
            html.Img(src="/assets/logo.png", className="logo-img"),
            html.H3("Portal GGCI", className="text-center mb-2 font-weight-bold"),
            html.P("Gerência de Gestão e Controle de Informações", className="text-center text-muted mb-4", style={"fontSize": "0.9rem"}),
            
            dbc.Alert("Entre em contato com o administrador caso não possua acesso.", color="info", className="mb-4 py-3", style={"fontSize": "0.85rem", "borderRadius": "10px"}),
            html.Div(id="login-main-alert"),
            
            dbc.Label("Usuário", className="fw-bold", style={"color": OVG_PINK}),
            dbc.Input(id="login-main-user", type="text", className="mb-3", style={"borderColor": "var(--border)"}),
            
            dbc.Label("Senha", className="fw-bold", style={"color": OVG_PINK}),
            dbc.Input(id="login-main-password", type="password", className="mb-4", style={"borderColor": "var(--border)"}),
            
            dbc.Button("ENTRAR", id="btn-login-main", className="btn-login"),
        ])
    ])

# =============================================================================
# 2. TELA INICIAL (HOME)
# =============================================================================
def layout_home(dados_usuario):
    """Renderiza o menu principal e o modal de troca de senha."""
    
    # Modal para Troca de Senha
    modal_troca_senha = dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Alterar Minha Senha")),
        dbc.ModalBody([
            dbc.Label("Senha Atual", className="fw-bold"),
            dbc.Input(id="input-senha-atual", type="password", className="mb-3"),
            
            dbc.Label("Nova Senha", className="fw-bold"),
            dbc.Input(id="input-nova-senha", type="password", placeholder="Mín. 8 caracteres | 1 Maiúscula | 2 Números | 1 Símbolo", className="mb-2"),
            dbc.Input(id="input-nova-senha-confirma", type="password", placeholder="Confirme a nova senha", className="mb-3"),
            
            html.Div(id="feedback-troca-senha", className="mt-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="btn-cancelar-troca", color="secondary"),
            dbc.Button("Salvar Nova Senha", id="btn-salvar-troca", style={"backgroundColor": OVG_ORANGE, "border": "none"})
        ])
    ], id="modal-troca-senha", is_open=False, size="lg", backdrop="static")

    return html.Div(className="container-fluid p-4", children=[
        html.Div(className="main-container", style={"minHeight": "80vh"}, children=[
            
            # Cabeçalho
            dbc.Row([
                dbc.Col(html.Img(src="/assets/logo.png", style={"height": "55px"}), width="auto"),
                dbc.Col([
                    html.H4("Portal GGCI", className="m-0 fw-bold"),
                    html.Span("Central de Aplicações", className="text-muted small")
                ], className="ps-3"),
                
                # Saudação e Logout
                dbc.Col([
                    html.Span(f"Olá, {dados_usuario.get('nome', 'Usuário')}", className="me-3 text-muted fw-bold"),
                    dbc.Button([DashIconify(icon="lucide:log-out", width=22), "Sair"], 
                               href="/logout", color="danger", outline=True, className="btn-nav")
                ], width="auto", className="ms-auto d-flex align-items-center")
            ], className="mb-5 align-items-center border-bottom pb-4", style={"borderColor": "var(--border)"}),

            # Menu de Cards
            dbc.Row([
                # Gestão (Admin)
                dbc.Col([
                    dcc.Link(
                        html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:settings", width=55, color=OVG_PINK), 
                            html.H5("Gestão de Acessos", className="mt-4 text-center fw-bold", style={"color": "white"})
                        ], style=estilo_card_menu(OVG_PINK)),
                        href="/gestao/login", style={"textDecoration": "none"}
                    )
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),

                # Softwares
                dbc.Col([
                    dcc.Link(
                        html.Div(className="app-card-hover", children=[
                            DashIconify(icon="mdi:language-python", width=65, color=OVG_YELLOW), 
                            html.H5("Softwares GGCI", className="mt-4 text-center fw-bold", style={"color": "white"})
                        ], style=estilo_card_menu(OVG_YELLOW)),
                        href="/softwares", style={"textDecoration": "none"}
                    )
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),

                # Troca de Senha
                dbc.Col([
                    html.Div(className="app-card-hover", id="btn-abrir-troca-senha", children=[
                        DashIconify(icon="lucide:lock-keyhole", width=55, color=OVG_ORANGE), 
                        html.H5("Alterar Minha Senha", className="mt-4 text-center fw-bold", style={"color": "white"})
                    ], style=estilo_card_menu(OVG_ORANGE))
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),

            ], justify="center", className="mt-5"),
            
            modal_troca_senha
        ])
    ])

# =============================================================================
# 3. MENU DE SOFTWARES
# =============================================================================
def layout_menu_softwares(user_data):
    return html.Div(className="container-fluid p-4", children=[
        html.Div(className="main-container", style={"minHeight": "80vh"}, children=[
            # Cabeçalho Interno
            dbc.Row([
                dbc.Col(html.Img(src="/assets/logo.png", style={"height": "50px"}), width="auto"),
                dbc.Col([
                    html.H4("Softwares GGCI", className="m-0 fw-bold"),
                    html.Span("Automação e Análise de Dados", className="text-muted small")
                ], className="ps-3"),
                dbc.Col(
                    dbc.Button([DashIconify(icon="lucide:arrow-left", width=22), "Voltar"], 
                               href="/home", color="light", outline=True, className="btn-nav"), 
                    width="auto", className="ms-auto"
                )
            ], className="mb-5 align-items-center border-bottom pb-4", style={"borderColor": "var(--border)"}),

            # Grid de Ferramentas
            dbc.Row([
                # Padronizador de Inscrições
                dbc.Col([
                    dcc.Link(
                        html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:brain-circuit", width=65, color=OVG_GREEN), 
                            html.H5("Padronizador de Inscrições", className="mt-4 text-center fw-bold", style={"color": "white", "marginBottom": "5px"}),
                            html.Span("Gestão ProBem", className="text-center small text-muted", style={"fontSize": "0.85rem"})
                        ], style=estilo_card_menu(OVG_GREEN)),
                        href="/softwares/gerador-lista", style={"textDecoration": "none"}
                    )
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),

                # Padronizador de IES
                dbc.Col([
                    dcc.Link(
                        html.Div(className="app-card-hover", children=[
                            DashIconify(icon="lucide:graduation-cap", width=65, color=OVG_BLUE), 
                            html.H5("Padronizador de IES", className="mt-4 text-center fw-bold", style={"color": "white", "marginBottom": "5px"}),
                            html.Span("Limpeza e Normalização", className="text-center small text-muted", style={"fontSize": "0.85rem"})
                        ], style=estilo_card_menu(OVG_BLUE)),
                        href="/softwares/padronizador-ies", style={"textDecoration": "none"}
                    )
                ], width="100%", md="auto", className="m-3 d-flex justify-content-center"),
            ], justify="center", className="mt-5"),
        ])
    ])

# =============================================================================
# 4. FERRAMENTA: PADRONIZADOR DE INSCRIÇÕES (Corrigido e Alinhado)
# =============================================================================
def layout_ferramenta_inscricoes():
    return html.Div(className="container-fluid p-3 p-md-5", children=[ 
        html.Div(className="main-container", style={"minHeight": "85vh", "maxWidth": "1600px"}, children=[
            
            # Header
            dbc.Row([
                dbc.Col([
                    html.H4([DashIconify(icon="lucide:brain-circuit", className="me-2", color=OVG_GREEN), "Padronizador de Inscrições"], className="m-0 fw-bold"),
                    html.Span("Gestão ProBem - Padronização de dados do Excel", className="text-muted small")
                ]),
                dbc.Col(
                    dbc.Button([DashIconify(icon="lucide:arrow-left", width=25), "Voltar"], 
                               href="/softwares", color="light", outline=True, className="btn-nav"), 
                    width="auto", className="ms-auto"
                )
            ], className="mb-4 pb-3 border-bottom", style={"borderColor": "var(--border)"}),

            # Área de Trabalho - ALTURA FIXA 65vh para alinhamento perfeito
            dbc.Row([
                
                # COLUNA ESQUERDA: Entrada + Botões
                dbc.Col([
                    # Label + Contador
                    html.Div([
                        dbc.Label("Cole o texto aqui (Excel):", className="fw-bold text-muted mb-0"),
                        dbc.Badge("0 itens", id="badge-inscricoes-entrada", color="secondary", className="ms-2", style={"backgroundColor": "#6c757d"})
                    ], className="d-flex align-items-center mb-2"),
                    
                    # Textarea (Flexível)
                    dbc.Textarea(
                        id="input-inscricoes", 
                        className="mb-3 flex-grow-1", # Ocupa todo o espaço vertical
                        style={
                            "backgroundColor": "rgba(0,0,0,0.2)", 
                            "color": "white", 
                            "border": "1px solid var(--border)", 
                            "fontSize": "0.95rem",
                            "resize": "none",
                            "height": "100%"
                        }, 
                        placeholder="Ex:\nInscrição 1\nInscrição 2\nInscrição 3"
                    ),
                    
                    # Botões no rodapé
                    dbc.Row([
                        dbc.Col(dbc.Button("LIMPAR", id="btn-limpar-inscricoes", color="secondary", className="w-100 fw-bold py-2"), width=12, md=3, className="mb-2 mb-md-0"),
                        dbc.Col(dbc.Button("GERAR LISTA", id="btn-processar-inscricoes", className="w-100 fw-bold py-2", style={"backgroundColor": OVG_PURPLE, "border": "none"}), width=12, md=9),
                    ], className="g-2")

                ], md=6, className="d-flex flex-column h-100 mb-4 mb-md-0"), # 'flex-column h-100' garante alinhamento

                # COLUNA DIREITA: Saída
                dbc.Col([
                    html.Div([
                        dbc.Label("Resultado formatado:", className="fw-bold text-muted mb-0"),
                        dbc.Badge("0 itens", id="badge-inscricoes-saida", color="info", className="ms-2", style={"backgroundColor": OVG_BLUE})
                    ], className="d-flex align-items-center mb-2"),

                    html.Div([
                        dbc.Textarea(
                            id="output-inscricoes", 
                            readonly=True, 
                            style={
                                "backgroundColor": "rgba(0,0,0,0.4)", 
                                "color": OVG_GREEN, 
                                "border": f"1px solid {OVG_GREEN}", 
                                "fontFamily": "monospace", 
                                "fontSize": "1rem",
                                "height": "100%",
                                "resize": "none"
                            }
                        ),
                        html.Div([
                            dcc.Clipboard(target_id="output-inscricoes", title="Copiar", style={"fontSize": 24, "color": "white"}),
                        ], style={"position": "absolute", "top": "15px", "right": "15px", "backgroundColor": OVG_GREEN, "padding": "8px 12px", "borderRadius": "8px", "cursor": "pointer", "boxShadow": "0 4px 10px rgba(0,0,0,0.3)"})
                    ], style={"position": "relative", "flex": "1"}), # Flex 1 para igualar a esquerda
                    
                ], md=6, className="d-flex flex-column h-100"),
                
            ], style={"height": "65vh"}), # ALTURA MESTRA
            
            dbc.Toast(id="toast-inscricoes", header="Sucesso", icon="success", duration=4000, is_open=False, style={"position": "fixed", "top": 20, "right": 20, "width": 300, "zIndex": 1050}),
        ])
    ])

# =============================================================================
# 5. FERRAMENTA: PADRONIZADOR DE IES
# =============================================================================
def layout_ferramenta_ies():
    return html.Div(className="container-fluid p-3 p-md-5", children=[ 
        html.Div(className="main-container", style={"minHeight": "85vh", "maxWidth": "1600px"}, children=[
            
            # Header
            dbc.Row([
                dbc.Col([
                    html.H4([DashIconify(icon="lucide:graduation-cap", className="me-2", color=OVG_BLUE), "Padronizador de IES"], className="m-0 fw-bold"),
                    html.Span("Limpeza e Padronização de Colunas do Excel", className="text-muted small")
                ]),
                dbc.Col(
                    dbc.Button([DashIconify(icon="lucide:arrow-left", width=25), "Voltar"], 
                               href="/softwares", color="light", outline=True, className="btn-nav"), 
                    width="auto", className="ms-auto"
                )
            ], className="mb-4 pb-3 border-bottom", style={"borderColor": "var(--border)"}),

            # Área de Trabalho - ALTURA FIXA 65vh
            dbc.Row([
                # COLUNA ESQUERDA
                dbc.Col([
                    html.Div([
                        dbc.Label("Cole a coluna do Excel aqui:", className="fw-bold text-muted mb-0"),
                        dbc.Badge("0 itens", id="badge-ies-entrada", color="secondary", className="ms-2", style={"backgroundColor": "#6c757d"})
                    ], className="d-flex align-items-center mb-2"),

                    dbc.Textarea(
                        id="input-ies", 
                        className="mb-3 flex-grow-1",
                        style={
                            "backgroundColor": "rgba(0,0,0,0.2)", 
                            "color": "white", 
                            "border": "1px solid var(--border)", 
                            "fontSize": "0.95rem",
                            "resize": "none",
                            "height": "100%"
                        }, 
                        placeholder="Ex:\nFaculdade Unip\nPUC Goias\nUFG - Campus 1"
                    ),
                    
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Label("Tipo de Saída:", className="fw-bold text-light small"),
                            dbc.RadioItems(
                                options=[
                                    {"label": "Valores Únicos (Remove repetidos)", "value": "unique"},
                                    {"label": "Valores Correspondentes (Mesma ordem)", "value": "full"},
                                ],
                                value="unique",
                                id="radio-tipo-ies",
                                inline=True,
                                style={"color": "white"},
                                labelStyle={"marginRight": "20px"}
                            ),
                        ], className="p-2")
                    ], className="mb-3", style={"backgroundColor": "rgba(255,255,255,0.05)", "border": "none"}),

                    dbc.Row([
                        dbc.Col(dbc.Button("LIMPAR", id="btn-limpar-ies", color="secondary", className="w-100 fw-bold py-2"), width=12, md=3, className="mb-2 mb-md-0"),
                        dbc.Col(dbc.Button("PADRONIZAR", id="btn-processar-ies", className="w-100 fw-bold py-2", style={"backgroundColor": OVG_BLUE, "border": "none"}), width=12, md=9),
                    ], className="g-2")

                ], md=6, className="d-flex flex-column h-100 mb-4 mb-md-0"),

                # COLUNA DIREITA
                dbc.Col([
                    html.Div([
                        dbc.Label("Resultado Padronizado:", className="fw-bold text-muted mb-0"),
                        dbc.Badge("0 itens", id="badge-ies-saida", color="info", className="ms-2", style={"backgroundColor": OVG_BLUE})
                    ], className="d-flex align-items-center mb-2"),

                    html.Div([
                        dbc.Textarea(
                            id="output-ies", 
                            readonly=True, 
                            style={
                                "backgroundColor": "rgba(0,0,0,0.4)", 
                                "color": OVG_BLUE, 
                                "border": f"1px solid {OVG_BLUE}", 
                                "fontFamily": "monospace", 
                                "fontSize": "1rem",
                                "height": "100%",
                                "resize": "none"
                            }
                        ),
                        html.Div([
                            dcc.Clipboard(target_id="output-ies", title="Copiar", style={"fontSize": 24, "color": "white"}),
                        ], style={"position": "absolute", "top": "15px", "right": "15px", "backgroundColor": OVG_BLUE, "padding": "8px 12px", "borderRadius": "8px", "cursor": "pointer", "boxShadow": "0 4px 10px rgba(0,0,0,0.3)"})
                    ], style={"position": "relative", "flex": "1"}),
                ], md=6, className="d-flex flex-column h-100"),

            ], style={"height": "65vh"}),

            dbc.Toast(id="toast-ies", header="Processado", icon="info", duration=4000, is_open=False, style={"position": "fixed", "top": 20, "right": 20, "width": 300, "zIndex": 1050}),
        ])
    ])

# =============================================================================
# 6. GESTÃO DE ACESSOS
# =============================================================================
def layout_login_admin():
    return html.Div(className="login-container", children=[
        html.Div(className="main-container login-box", style={"border": f"1px solid {OVG_PINK}"}, children=[
            html.Img(src="/assets/logo.png", className="logo-img"),
            html.H4("Gestão de Acessos", className="text-center mb-4 text-white"),
            html.Div(id="alert-login-admin"),
            dbc.Label("Usuário Admin", style={"color": OVG_PINK}),
            dbc.Input(id="input-admin-user", type="text", className="mb-3"),
            dbc.Label("Senha", style={"color": OVG_PINK}),
            dbc.Input(id="input-admin-pass", type="password", className="mb-4"),
            dbc.Button("ACESSAR PAINEL", id="btn-login-admin", className="fw-bold", style={"background": f"linear-gradient(90deg, {OVG_PINK}, {OVG_PURPLE})", "color": "white", "border": "none", "width": "100%", "padding": "12px", "borderRadius": "10px"}),
            dcc.Link("Cancelar e Voltar", href="/home", className="d-block text-center mt-4 text-muted small text-decoration-none")
        ])
    ])

def layout_dashboard_admin():
    df = listar_todos_usuarios() # Uso da função renomeada
    tabela_header = [html.Thead(html.Tr([html.Th("ID"), html.Th("Nome"), html.Th("Login"), html.Th("Email"), html.Th("Perfil"), html.Th("Ações", style={"textAlign": "center"})]))]
    rows = []
    for index, row in df.iterrows():
        is_main_admin = (row['id'] == 1)
        rows.append(html.Tr([
            html.Td(row['id']), html.Td(f"{row['primeiro_nome']} {row['ultimo_nome']}"), html.Td(row['username']), html.Td(row['email']), html.Td("Admin" if row['is_admin'] else "Usuário"),
            html.Td([
                dbc.Button(DashIconify(icon="lucide:edit", width=18), id={"type": "btn-edit-user", "index": row['id']}, style={"backgroundColor": OVG_YELLOW, "border": "none", "color": "#333"}, size="sm", className="me-2", n_clicks=0),
                dbc.Button(DashIconify(icon="lucide:trash-2", width=18), id={"type": "btn-delete-user", "index": row['id']}, color="danger", size="sm", n_clicks=0, disabled=is_main_admin)
            ], style={"textAlign": "center"})
        ]))

    return html.Div(className="container-fluid p-4", children=[
        html.Div(className="main-container", style={"minHeight": "80vh"}, children=[
            dbc.Row([
                dbc.Col(html.H3("Gestão de Acessos", className="fw-bold"), width=8),
                dbc.Col(dbc.Button([DashIconify(icon="lucide:arrow-left", width=22), "Voltar"], href="/home", color="light", outline=True, className="btn-nav"), width=4, className="text-end")
            ], className="mb-4 pb-3 border-bottom", style={"borderColor": "var(--border)"}),
            dbc.Row([
                dbc.Col([
                    dbc.Button([DashIconify(icon="lucide:plus", className="me-2"), "Novo Usuário"], id="btn-novo-usuario", className="mb-3 fw-bold", style={"backgroundColor": OVG_PURPLE, "border": "none", "color": "white", "borderRadius": "8px"}, n_clicks=0),
                    dbc.Table(tabela_header + [html.Tbody(rows)], bordered=True, hover=True, responsive=True, striped=True, className="table-dark")
                ])
            ]),
            html.Div(id="container-modais") 
        ])
    ])

def componentes_modais_admin():
    return html.Div([
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="modal-titulo-usuario")),
            dbc.ModalBody([
                dbc.Row([dbc.Col([dbc.Checkbox(id="check-is-admin", label="Admin", style={"fontWeight": "bold", "color": OVG_PINK})], className="d-flex justify-content-end mb-2")]),
                dbc.Row([dbc.Col([dbc.Label("Primeiro Nome"), dbc.Input(id="input-primeiro-nome")], width=6), dbc.Col([dbc.Label("Último Nome"), dbc.Input(id="input-ultimo-nome")], width=6)], className="mb-3"),
                dbc.Label("E-mail (@ovg.org.br)"), dbc.Input(id="input-email", type="email", placeholder="nome@ovg.org.br", className="mb-3"),
                dbc.Label("Senha"), 
                dbc.Input(id="input-senha", type="password", placeholder="Mín. 8 caracteres | 1 Maiúscula | 2 Números | 1 Símbolo", className="mb-2"),
                dbc.Input(id="input-senha-confirma", type="password", placeholder="Confirme", className="mb-2"),
                dbc.Checkbox(id="check-mostrar-senha-admin", label="Mostrar senha", className="mb-3"),
                html.Div(id="alert-modal-usuario", className="mt-3")
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="btn-cancelar-modal", color="secondary"), 
                dbc.Button("Salvar", id="btn-salvar-usuario", style={"backgroundColor": OVG_PURPLE, "border": "none"})
            ])
        ], id="modal-usuario", is_open=False, size="lg", backdrop="static"),
        
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão")),
            dbc.ModalBody("Tem certeza que deseja excluir este usuário?"),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="btn-cancelar-delete", color="secondary"), 
                dbc.Button("Excluir", id="btn-confirmar-delete", color="danger")
            ])
        ], id="modal-delete", is_open=False),
        
        dcc.Store(id="store-edit-id", data=None), 
        dcc.Store(id="store-delete-id", data=None)
    ])