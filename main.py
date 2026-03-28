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
    parametros,
    estoque,
)


def main(page: ft.Page):
    page.title = "Gestão Loja"
    tema_salvo = database.config_obter("tema", "DARK")
    page.theme_mode = (ft.ThemeMode.DARK
                       if tema_salvo == "DARK"
                       else ft.ThemeMode.LIGHT)
    page.window.min_width  = 900
    page.window.min_height = 600

    # ── Mapeamento índice → módulo de view ────────────────────────────
    _views = [
        dashboard.view,        # 0
        pdv.view,              # 1
        extras.view,           # 2
        relatorio_diario.view, # 3
        relatorio_periodo.view,# 4
        fluxo_caixa.view,      # 5
        fiados.view,           # 6
        funcionarios.view,     # 7
        escala_geral.view,     # 8
        entregadores.view,     # 9
        estoque.view,          # 10
        parametros.view,       # 11
    ]

    # ── Área de conteúdo (direita) ────────────────────────────────────
    area_conteudo = ft.Container(
        expand=True,
        padding=ft.Padding.all(24),
    )

    # ── Barra de status ────────────────────────────────────────────────
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

    # ── Botão de alternância de tema ──────────────────────────────────
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
                btn_tema,
            ]
        ),
    )

    def carregar_view(indice: int):
        """Instancia a view selecionada e atualiza a área de conteúdo."""
        try:
            area_conteudo.content = _views[indice](page)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            area_conteudo.content = ft.Column(controls=[
                ft.Text("Erro ao carregar tela:", size=16, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.RED_400),
                ft.Text(str(exc), color=ft.Colors.RED_300, selectable=True),
            ])
        page.update()

    # ── NavigationRail (esquerda, fixo) ───────────────────────────────
    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=110,
        group_alignment=-1.0,   # itens alinhados ao topo
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD,
                label="Dashboard",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.POINT_OF_SALE,
                label="PDV",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ADD_CIRCLE,
                label="Movim. e Caixa",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.TODAY,
                label="Rel. Diário",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DATE_RANGE,
                label="Rel. Período",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                label="Fluxo Caixa",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.MONEY_OFF,
                label="Fiados",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PEOPLE,
                label="Funcionários",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.CALENDAR_MONTH,
                label="Escala Geral",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DELIVERY_DINING,
                label="Entregadores",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.INVENTORY_2,
                label="Estoque",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS,
                label="Parâmetros",
            ),
        ],
        on_change=lambda e: carregar_view(e.control.selected_index),
    )

    # ── Layout principal: top bar + rail | divisor | conteúdo + barra status ───
    page.add(
        ft.Column(
            expand=True,
            spacing=0,
            controls=[
                top_bar,
                ft.Divider(height=1),
                ft.Row(
                    controls=[
                        rail,
                        ft.VerticalDivider(width=1),
                        area_conteudo,
                    ],
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                barra_status,
            ],
        )
    )

    # Carrega a primeira view (PDV) ao iniciar
    carregar_view(0)


if __name__ == "__main__":
    database.inicializar_banco()
    ft.app(target=main)
