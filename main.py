"""
main.py — Ponto de entrada do app Gestão Loja.
Configura a janela, o NavigationRail lateral e carrega as views sob demanda.
"""

import flet as ft

import database
from views import (
    pdv,
    extras,
    relatorio_diario,
    relatorio_periodo,
    funcionarios,
    entregadores,
    parametros,
)


def main(page: ft.Page):
    page.title = "Gestão Loja"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.min_width  = 900
    page.window.min_height = 600

    # ── Mapeamento índice → módulo de view ────────────────────────────
    _views = [
        pdv.view,
        extras.view,
        relatorio_diario.view,
        relatorio_periodo.view,
        funcionarios.view,
        entregadores.view,
        parametros.view,
    ]

    # ── Área de conteúdo (direita) ────────────────────────────────────
    area_conteudo = ft.Container(
        expand=True,
        padding=ft.Padding.all(24),
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
                icon=ft.Icons.PEOPLE,
                label="Funcionários",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DELIVERY_DINING,
                label="Entregadores",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS,
                label="Parâmetros",
            ),
        ],
        on_change=lambda e: carregar_view(e.control.selected_index),
    )

    # ── Layout principal: rail | divisor | conteúdo ───────────────────
    page.add(
        ft.Row(
            controls=[
                rail,
                ft.VerticalDivider(width=1),
                area_conteudo,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        )
    )

    # Carrega a primeira view (PDV) ao iniciar
    carregar_view(0)


if __name__ == "__main__":
    database.inicializar_banco()
    ft.app(main)
