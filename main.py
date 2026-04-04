"""
main.py — Ponto de entrada do app Gestão Loja.
Configura a janela, o NavigationRail lateral e carrega as views sob demanda.
"""

import flet as ft

import database
from views import (
    dashboard,
    pdv,
    extras,
    relatorio_diario,
    relatorio_periodo,
    fluxo_caixa,
    fiados,
    funcionarios,
    escala_geral,
    entregadores,
    estoque,
    fornecedores,
    parametros,
    login,
)


# ── Mapeamento de telas com perfil mínimo necessário ──────────────────────────

TELAS = [
    {"view": dashboard.view,         "label": "Dashboard",      "icon": ft.Icons.DASHBOARD,              "min_perfil": "OPERADOR"},
    {"view": pdv.view,               "label": "PDV",            "icon": ft.Icons.POINT_OF_SALE,          "min_perfil": "OPERADOR"},
    {"view": extras.view,            "label": "Movim. e Caixa", "icon": ft.Icons.ADD_CIRCLE,             "min_perfil": "OPERADOR"},
    {"view": relatorio_diario.view,  "label": "Rel. Diário",    "icon": ft.Icons.TODAY,                  "min_perfil": "OPERADOR"},
    {"view": relatorio_periodo.view, "label": "Rel. Período",   "icon": ft.Icons.DATE_RANGE,             "min_perfil": "GERENTE"},
    {"view": fluxo_caixa.view,       "label": "Fluxo Caixa",   "icon": ft.Icons.ACCOUNT_BALANCE_WALLET, "min_perfil": "GERENTE"},
    {"view": funcionarios.view,      "label": "Funcionários",   "icon": ft.Icons.PEOPLE,                 "min_perfil": "GERENTE"},
    {"view": escala_geral.view,      "label": "Escala Geral",   "icon": ft.Icons.CALENDAR_MONTH,         "min_perfil": "OPERADOR"},
    {"view": entregadores.view,      "label": "Entregadores",   "icon": ft.Icons.DELIVERY_DINING,        "min_perfil": "OPERADOR"},
    {"view": fiados.view,            "label": "Fiados",         "icon": ft.Icons.MONEY_OFF,              "min_perfil": "OPERADOR"},
    {"view": estoque.view,           "label": "Estoque",        "icon": ft.Icons.INVENTORY_2,            "min_perfil": "GERENTE"},
    {"view": fornecedores.view,      "label": "Fornecedores",   "icon": ft.Icons.LOCAL_SHIPPING,         "min_perfil": "GERENTE"},
    {"view": parametros.view,        "label": "Parâmetros",     "icon": ft.Icons.SETTINGS,               "min_perfil": "ADMIN"},
]


def _iniciar_app(page: ft.Page):
    page.title = "Gestão Loja"
    tema_salvo = database.config_obter("tema", "DARK")
    page.theme_mode = (ft.ThemeMode.DARK
                       if tema_salvo == "DARK"
                       else ft.ThemeMode.LIGHT)
    page.window.min_width  = 900
    page.window.min_height = 600

    def _on_login(perfil: str):
        page.clean()
        _carregar_app_principal(page, perfil, _on_login)

    usuarios = database.usuario_listar_ativos()
    if usuarios:
        page.add(login.view(page, _on_login))
    else:
        _carregar_app_principal(page, "ADMIN", _on_login)


def _carregar_app_principal(page: ft.Page, perfil: str, on_login=None):

    # ── Filtrar telas pelo perfil ──────────────────────────────────────────
    _hierarquia      = {"OPERADOR": 1, "GERENTE": 2, "ADMIN": 3}
    _nivel           = _hierarquia.get(perfil, 0)
    telas_perm       = [t for t in TELAS if _hierarquia.get(t["min_perfil"], 1) <= _nivel]
    _views           = [t["view"] for t in telas_perm]
    _idx_selecionado = {"v": 0}

    # ── Área de conteúdo (direita) ────────────────────────────────────────
    area_conteudo = ft.Container(
        expand=True,
        padding=ft.Padding.all(24),
    )

    # ── Barra de status ────────────────────────────────────────────────────
    _st = database.banco_status()

    def _mostrar_detalhes_banco(e):
        status_txt = "Conectado" if _st["existe"] else "Arquivo não encontrado"
        origem_txt = "Google Drive" if _st["eh_drive"] else "Local"
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Banco de Dados"),
            content=ft.Column(tight=True, spacing=8, controls=[
                ft.Text(f"Caminho: {_st['caminho']}", size=12, selectable=True),
                ft.Text(f"Origem: {origem_txt}", size=12),
                ft.Text(f"Tamanho: {_st['tamanho_kb']} KB", size=12),
                ft.Text(f"Última modificação: {_st['modificado']}", size=12),
                ft.Text(
                    f"Status: {status_txt}", size=12,
                    color=ft.Colors.GREEN_400 if _st["existe"] else ft.Colors.RED_400,
                ),
            ]),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: (
                    setattr(dlg, "open", False), page.update()
                )),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    if _st["eh_drive"] and _st["existe"]:
        _icone_db = ft.Icons.CLOUD_DONE
        _cor_db   = ft.Colors.GREEN_400
        _label_db = "Google Drive"
    elif _st["eh_drive"] and not _st["existe"]:
        _icone_db = ft.Icons.CLOUD_OFF
        _cor_db   = ft.Colors.RED_400
        _label_db = "Drive não encontrado — usando banco local"
    else:
        _icone_db = ft.Icons.COMPUTER
        _cor_db   = ft.Colors.GREY_400
        _label_db = "Banco local"

    _caminho_resumido = (
        ("…" + _st["caminho"][-40:]) if len(_st["caminho"]) > 40 else _st["caminho"]
    )

    barra_status = ft.Container(
        height=28,
        bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
        padding=ft.Padding(left=12, right=12, top=0, bottom=0),
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
            controls=[
                ft.Icon(_icone_db, color=_cor_db, size=14),
                ft.Text(_label_db, size=11, color=_cor_db),
                ft.Text("|", size=11, color=ft.Colors.GREY_600),
                ft.Text(f"{_st['tamanho_kb']} KB", size=11, color=ft.Colors.GREY_500),
                ft.Text("|", size=11, color=ft.Colors.GREY_600),
                ft.Text(f"Atualizado: {_st['modificado']}", size=11, color=ft.Colors.GREY_500),
                ft.Container(expand=True),
                ft.TextButton(
                    _caminho_resumido,
                    on_click=_mostrar_detalhes_banco,
                    tooltip=_st["caminho"],
                    style=ft.ButtonStyle(color=ft.Colors.GREY_600),
                ),
            ],
        ),
    )

    # ── Botão de alternância de tema ──────────────────────────────────────
    tema_salvo = database.config_obter("tema", "DARK")
    btn_tema = ft.IconButton(
        icon=(ft.Icons.LIGHT_MODE if tema_salvo == "DARK" else ft.Icons.DARK_MODE),
        tooltip="Alternar tema",
        on_click=lambda e: _alternar_tema(e),
    )

    def _alternar_tema(e):
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            database.config_salvar("tema", "LIGHT")
            btn_tema.icon = ft.Icons.DARK_MODE
        else:
            page.theme_mode = ft.ThemeMode.DARK
            database.config_salvar("tema", "DARK")
            btn_tema.icon = ft.Icons.LIGHT_MODE
        page.update()

    # ── Botão de logout ───────────────────────────────────────────────────
    sessao       = database.sessao_obter()
    nome_usuario = sessao["nome"] or "Convidado"

    def _logout(e):
        def _confirmar(dlg):
            dlg.open = False
            database.sessao_encerrar()
            page.clean()
            if on_login is not None:
                page.add(login.view(page, on_login))
            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sair"),
            content=ft.Text("Deseja sair e trocar de usuário?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (
                    setattr(dlg, "open", False), page.update()
                )),
                ft.ElevatedButton(
                    "Sair",
                    ft.Icons.LOGOUT,
                    on_click=lambda e: _confirmar(dlg),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    btn_logout = ft.IconButton(
        icon=ft.Icons.LOGOUT,
        tooltip="Sair / Trocar usuário",
        on_click=_logout,
    )

    # ── Top bar ───────────────────────────────────────────────────────────
    top_bar = ft.Container(
        height=48,
        padding=ft.Padding(left=16, right=16, top=0, bottom=0),
        content=ft.Row(
            controls=[
                ft.Text(
                    database.config_obter("nome_loja", "Gestão Loja"),
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    expand=True,
                ),
                ft.Text(f"Olá, {nome_usuario}", size=13, color=ft.Colors.GREY_500),
                btn_tema,
                btn_logout,
            ]
        ),
    )

    # ── Menu lateral customizado ──────────────────────────────────────────
    menu_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=False)

    def _build_menu():
        menu_col.controls.clear()
        for i, t in enumerate(telas_perm):
            selecionado = (i == _idx_selecionado["v"])
            menu_col.controls.append(
                ft.Container(
                    width=110,
                    border_radius=8,
                    ink=True,
                    tooltip=t["label"],
                    bgcolor=(
                        ft.Colors.with_opacity(0.18, ft.Colors.INDIGO_400)
                        if selecionado
                        else ft.Colors.TRANSPARENT
                    ),
                    padding=ft.Padding(left=6, right=6, top=10, bottom=10),
                    on_click=_make_nav_handler(i),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                        controls=[
                            ft.Icon(
                                t["icon"],
                                size=20,
                                color=(
                                    ft.Colors.INDIGO_300
                                    if selecionado
                                    else ft.Colors.GREY_400
                                ),
                            ),
                            ft.Text(
                                t["label"],
                                size=10,
                                text_align=ft.TextAlign.CENTER,
                                color=(
                                    ft.Colors.INDIGO_200
                                    if selecionado
                                    else ft.Colors.GREY_400
                                ),
                                weight=(
                                    ft.FontWeight.BOLD
                                    if selecionado
                                    else ft.FontWeight.NORMAL
                                ),
                            ),
                        ],
                    ),
                )
            )
        page.update()

    def _make_nav_handler(idx):
        def handler(e):
            _idx_selecionado["v"] = idx
            _build_menu()
            carregar_view(idx)
        return handler

    menu_wrapper = ft.Container(
        width=110,
        expand=False,
        padding=ft.Padding(top=8, bottom=8, left=4, right=4),
        content=menu_col,
    )

    def carregar_view(indice: int):
        """Instancia a view selecionada e atualiza a área de conteúdo."""
        try:
            area_conteudo.content = _views[indice](page)
        except Exception as exc:
            import traceback
            traceback.print_exc()

            def _tentar_novamente(e, _idx=indice):
                carregar_view(_idx)

            def _ir_pdv(e):
                _idx_selecionado["v"] = 0
                _build_menu()
                carregar_view(0)
                page.update()

            area_conteudo.content = ft.Column(controls=[
                ft.Text("Erro ao carregar tela:", size=16,
                        weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                ft.Text(str(exc), color=ft.Colors.RED_300, selectable=True),
                ft.Row(spacing=12, controls=[
                    ft.ElevatedButton(
                        "Tentar novamente",
                        icon=ft.Icons.REFRESH,
                        on_click=_tentar_novamente,
                    ),
                    ft.OutlinedButton(
                        "Ir para Dashboard",
                        icon=ft.Icons.DASHBOARD,
                        on_click=_ir_pdv,
                    ),
                ]),
            ])
        page.update()

    # ── Layout principal ──────────────────────────────────────────────────
    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                top_bar,
                ft.Divider(height=1),
                ft.Row(
                    controls=[
                        menu_wrapper,
                        ft.VerticalDivider(width=1),
                        area_conteudo,
                    ],
                    expand=True,
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                barra_status,
            ],
        )
    )

    # Carrega a primeira view ao iniciar
    _build_menu()
    carregar_view(0)


if __name__ == "__main__":
    database.inicializar_banco()
    ft.app(target=_iniciar_app)
