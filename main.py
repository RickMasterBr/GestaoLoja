"""
main.py — Ponto de entrada do app Gestão Loja.
Configura a janela, o NavigationRail lateral e carrega as views sob demanda.
"""

import ctypes
import logging
import os
import subprocess
import time

import flet as ft
from datetime import date

import database

# ── Instrumentação de performance (mesmo logger "perf" de database.py) ────
_perf_logger = logging.getLogger("perf")


def _encerrar_instancias_anteriores() -> None:
    """Encerra silenciosamente qualquer processo GestaoLoja.exe anterior ao atual."""
    pid_atual = os.getpid()
    try:
        resultado = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq GestaoLoja.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for linha in resultado.stdout.splitlines():
            partes = linha.strip().strip('"').split('","')
            if len(partes) < 2:
                continue
            try:
                pid = int(partes[1])
            except ValueError:
                continue
            if pid != pid_atual:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
    except Exception:
        pass
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
    agenda,
)


# ── Mapeamento de telas com perfil mínimo necessário ──────────────────────────

TELAS = [
    {"view": dashboard.view,         "label": "Dashboard",      "icon": ft.Icons.DASHBOARD,              "min_perfil": "OPERADOR"},
    {"view": pdv.view,               "label": "PDV",            "icon": ft.Icons.POINT_OF_SALE,          "min_perfil": "OPERADOR"},
    {"view": extras.view,            "label": "Movim. e Caixa", "icon": ft.Icons.ADD_CIRCLE,             "min_perfil": "OPERADOR"},
    {"view": agenda.view,            "label": "Agenda",         "icon": ft.Icons.EVENT_NOTE,             "min_perfil": "OPERADOR"},
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
    _t_boot = time.perf_counter()
    logging.debug("main() iniciado — Flet UI thread ativa")

    page.title = "Gestão Loja"
    tema_salvo = database.config_obter("tema", "DARK")
    page.theme_mode = (ft.ThemeMode.DARK
                       if tema_salvo == "DARK"
                       else ft.ThemeMode.LIGHT)
    page.window.min_width  = 900
    page.window.min_height = 600

    def _on_login(perfil: str):
        page.clean()
        _carregar_app_principal(page, perfil, _on_login, _t_boot)

    usuarios = database.usuario_listar_ativos()
    if usuarios:
        page.add(login.view(page, _on_login))
    else:
        _carregar_app_principal(page, "ADMIN", _on_login, _t_boot)


def _carregar_app_principal(page: ft.Page, perfil: str, on_login=None, _t_boot: float = 0.0):

    # ── Filtrar telas pelo perfil ──────────────────────────────────────────
    _hierarquia      = {"OPERADOR": 1, "GERENTE": 2, "ADMIN": 3}
    _nivel           = _hierarquia.get(perfil, 0)
    telas_perm       = [t for t in TELAS if _hierarquia.get(t["min_perfil"], 1) <= _nivel]
    _views           = [t["view"] for t in telas_perm]
    _idx_selecionado = {"v": 0}
    # Controla a construção da view em segundo plano: "geracao" descarta
    # resultados obsoletos quando uma navegação mais nova já assumiu a tela;
    # "indice_ativo" evita disparar duas construções para o mesmo índice.
    _carregamento    = {"geracao": 0, "indice_ativo": None}

    # ── Área de conteúdo (direita com Stack para transição instantânea) ───
    camada_view = ft.Container(expand=True)
    camada_loading = ft.Container(
        expand=True,
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[ft.ProgressRing(), ft.Text("Carregando...")],
            tight=True,
        ),
        visible=False,
    )
    area_conteudo = ft.Container(
        expand=True,
        padding=ft.Padding.all(24),
        content=ft.Stack(
            expand=True,
            controls=[camada_view, camada_loading],
        ),
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

    def _sincronizar(e):
        btn_sync.disabled = True
        btn_sync.icon = ft.Icons.HOURGLASS_EMPTY
        page.update()

        resultado = database.sincronizar_banco()

        if resultado["sucesso"]:
            btn_sync.tooltip = (
                f"Última sincronização: {resultado['timestamp']} "
                f"({resultado['pedidos']} pedidos no banco)"
            )
            page.overlay.append(ft.SnackBar(
                content=ft.Text(
                    f"Banco sincronizado às {resultado['timestamp']}. "
                    f"Atualize a tela atual para ver os novos dados."
                ),
                bgcolor=ft.Colors.GREEN_700,
                open=True,
            ))
        else:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(
                    f"Erro ao sincronizar: {resultado.get('erro', 'desconhecido')}"
                ),
                bgcolor=ft.Colors.RED_700,
                open=True,
            ))

        btn_sync.disabled = False
        btn_sync.icon = ft.Icons.SYNC
        page.update()

    btn_sync = ft.IconButton(
        icon=ft.Icons.SYNC,
        tooltip="Sincronizar banco com Google Drive",
        on_click=_sincronizar,
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
                btn_sync,
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

    # ── Sessão e perfil ───────────────────────────────────────────────────
    sessao       = database.sessao_obter()
    nome_usuario = sessao["nome"] or "Convidado"
    eh_operador  = sessao.get("perfil_acesso") == "OPERADOR"

    # ── Encerramento de Turno (apenas OPERADOR) ────────────────────────��──

    def _abrir_encerramento_turno(e):
        _estado = {"etapa": 1, "data_iso": None}

        tf_data_turno = ft.TextField(
            label="Data do turno",
            value=date.today().strftime("%d/%m/%Y"),
            width=160,
            text_align=ft.TextAlign.CENTER,
            hint_text="DD/MM/AAAA",
        )
        cb1 = ft.Checkbox(
            label="Lancei todos os pedidos do dia na data correta, "
                  "sem deixar nenhum de fora ou na data errada.",
            value=False,
        )
        cb2 = ft.Checkbox(
            label="Registrei todas as movimentações do dia: vales, "
                  "consumos, sangrias e outras entradas ou saídas.",
            value=False,
        )
        cb3 = ft.Checkbox(
            label="Gerei o relatório PDF do dia e enviei ao gerente "
                  "ou responsável.",
            value=False,
        )
        txt_etapa1_erro = ft.Text("", color=ft.Colors.RED_400, size=12)

        content_col = ft.Column(
            tight=True, spacing=12, width=480,
            scroll=ft.ScrollMode.AUTO,
        )

        def _br_para_iso(s: str) -> str:
            try:
                d, m, a = s.strip().split("/")
                return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
            except Exception:
                return ""

        def _montar_etapa1():
            content_col.controls.clear()
            content_col.controls.extend([
                ft.Text(
                    "Antes de encerrar, confirme que você completou "
                    "todas as tarefas do turno:",
                    size=13,
                ),
                ft.Row([ft.Text("Data do turno:", size=13), tf_data_turno],
                       spacing=12),
                cb1, cb2, cb3,
                txt_etapa1_erro,
                ft.ElevatedButton(
                    "Verificar e Continuar",
                    icon=ft.Icons.ARROW_FORWARD,
                    on_click=_verificar,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO_600,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ])
            page.update()

        def _verificar(e):
            if not (cb1.value and cb2.value and cb3.value):
                txt_etapa1_erro.value = (
                    "Por favor, confirme todos os itens acima antes de continuar."
                )
                page.update()
                return
            txt_etapa1_erro.value = ""
            data_iso = _br_para_iso(tf_data_turno.value)
            if not data_iso:
                txt_etapa1_erro.value = "Informe uma data válida (DD/MM/AAAA)."
                page.update()
                return
            _estado["data_iso"] = data_iso
            resultado = database.verificar_encerramento_turno(data_iso)
            _montar_etapa2(resultado)

        def _montar_etapa2(r):
            def _linha_check(ok: bool, txt_ok: str, txt_err: str,
                             bloqueia: bool = True):
                if ok:
                    return ft.Row(spacing=8, controls=[
                        ft.Icon(ft.Icons.CHECK_CIRCLE,
                                color=ft.Colors.GREEN_400, size=20),
                        ft.Text(txt_ok, expand=True, size=13),
                    ])
                cor  = ft.Colors.RED_400 if bloqueia else ft.Colors.ORANGE_400
                icone = (ft.Icons.ERROR if bloqueia
                         else ft.Icons.WARNING_AMBER_ROUNDED)
                return ft.Row(spacing=8, controls=[
                    ft.Icon(icone, color=cor, size=20),
                    ft.Text(txt_err, expand=True, size=13, color=cor),
                ])

            linha_pedidos = _linha_check(
                r["tem_pedidos"],
                f"Pedidos lançados no dia: {r['n_pedidos']} pedido(s) registrado(s). Tudo certo!",
                "Nenhum pedido encontrado para esta data. Certifique-se de que é isso mesmo.",
                bloqueia=False,
            )
            linha_caixa = _linha_check(
                r["caixa_fechado"],
                "Caixa fechado! O fechamento do caixa foi salvo com sucesso.",
                "O caixa ainda não foi fechado! Volte ao Relatório Diário, "
                "preencha o troco e o valor na gaveta e clique em Salvar "
                "Fechamento antes de encerrar.",
            )
            linha_escala = _linha_check(
                r["escala_completa"],
                f"Presenças registradas! Todos os {r['total_pessoas']} "
                "funcionário(s) têm presença registrada hoje.",
                f"Faltam presenças! {r['pessoas_sem_escala']} funcionário(s) "
                "ainda não tiveram a presença registrada hoje. Acesse o "
                "Dashboard ou a Escala Geral para corrigir.",
            )

            content_col.controls.clear()
            content_col.controls.extend([
                ft.Text("Resultado das verificações:", size=13,
                        weight=ft.FontWeight.BOLD),
                linha_pedidos,
                linha_caixa,
                linha_escala,
            ])

            if r["pode_encerrar"]:
                def _confirmar_enc(e):
                    database.registrar_encerramento_turno(
                        _estado["data_iso"], nome_usuario
                    )
                    dlg.open = False
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text("Turno encerrado com sucesso! Bom descanso."),
                        bgcolor=ft.Colors.GREEN_700, open=True,
                    ))
                    page.update()

                content_col.controls.extend([
                    ft.Text(
                        "Tudo certo! O turno está pronto para ser encerrado.",
                        size=13, color=ft.Colors.GREEN_400,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.ElevatedButton(
                        "Confirmar Encerramento",
                        icon=ft.Icons.NIGHT_SHELTER,
                        on_click=_confirmar_enc,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.DEEP_ORANGE_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ])
            else:
                content_col.controls.extend([
                    ft.Text(
                        "Corrija os itens em vermelho antes de encerrar o turno.",
                        size=13, color=ft.Colors.RED_400,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.ElevatedButton(
                        "Voltar e Corrigir",
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: (
                            setattr(dlg, "open", False), page.update()
                        ),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREY_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ])

            page.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Encerrar Turno"),
            content=content_col,
            actions=[ft.TextButton("Cancelar", on_click=lambda e: (
                setattr(dlg, "open", False), page.update()
            ))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        _montar_etapa1()
        dlg.open = True
        page.update()

    btn_encerrar_turno = ft.ElevatedButton(
        "Encerrar Turno",
        icon=ft.Icons.NIGHT_SHELTER,
        on_click=_abrir_encerramento_turno,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.DEEP_ORANGE_700,
            color=ft.Colors.WHITE,
        ),
    )

    # ── Botão de logout ───────────────────────────────────────────────────

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
                btn_encerrar_turno if eh_operador else ft.Container(),
                btn_tema,
                btn_logout,
            ]
        ),
    )

    # ── Menu lateral retrátil e customizado ─────────────────────────────
    _menu_expandido = {"v": database.config_obter("menu_expandido", "0") == "1"}
    menu_col = ft.Column(spacing=3, scroll=ft.ScrollMode.AUTO, expand=True)

    def _toggle_menu(_e=None):
        _menu_expandido["v"] = not _menu_expandido["v"]
        try:
            database.config_definir("menu_expandido", "1" if _menu_expandido["v"] else "0")
        except Exception:
            pass
        _atualizar_estrutura_menu()

    btn_toggle_menu = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_size=18,
        tooltip="Expandir menu" if not _menu_expandido["v"] else "Recolher menu",
        on_click=_toggle_menu,
    )

    menu_header = ft.Container(
        padding=ft.Padding(left=4, right=4, top=2, bottom=2),
        content=btn_toggle_menu,
    )

    def _build_menu():
        expandido = _menu_expandido["v"]
        menu_col.controls.clear()

        # Botão de alternância no topo da barra lateral
        if expandido:
            btn_toggle_menu.icon = ft.Icons.KEYBOARD_DOUBLE_ARROW_LEFT
            btn_toggle_menu.tooltip = "Recolher menu"
            menu_header.content = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Menu", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400),
                    btn_toggle_menu,
                ],
            )
        else:
            btn_toggle_menu.icon = ft.Icons.MENU
            btn_toggle_menu.tooltip = "Expandir menu"
            menu_header.content = ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[btn_toggle_menu],
            )

        for i, t in enumerate(telas_perm):
            selecionado = (i == _idx_selecionado["v"])
            cor_destaque = ft.Colors.INDIGO_300 if selecionado else ft.Colors.GREY_400
            bg_cor = ft.Colors.with_opacity(0.18, ft.Colors.INDIGO_400) if selecionado else ft.Colors.TRANSPARENT

            if expandido:
                item_content = ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(t["icon"], size=18, color=cor_destaque),
                        ft.Text(
                            t["label"],
                            size=12,
                            color=ft.Colors.INDIGO_200 if selecionado else ft.Colors.GREY_300,
                            weight=ft.FontWeight.BOLD if selecionado else ft.FontWeight.NORMAL,
                            no_wrap=True,
                        ),
                    ],
                )
                padding = ft.Padding(left=10, right=10, top=7, bottom=7)
            else:
                item_content = ft.Container(
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(t["icon"], size=20, color=cor_destaque),
                )
                padding = ft.Padding(left=4, right=4, top=7, bottom=7)

            menu_col.controls.append(
                ft.Container(
                    border_radius=8,
                    ink=True,
                    tooltip=t["label"],
                    bgcolor=bg_cor,
                    padding=padding,
                    on_click=_make_nav_handler(i),
                    content=item_content,
                )
            )

    def _atualizar_estrutura_menu():
        menu_wrapper.width = 180 if _menu_expandido["v"] else 58
        _build_menu()
        page.update()

    def _make_nav_handler(idx):
        def handler(e):
            _idx_selecionado["v"] = idx
            _build_menu()
            carregar_view(idx)
        return handler

    menu_wrapper = ft.Container(
        width=180 if _menu_expandido["v"] else 58,
        expand=False,
        padding=ft.Padding(top=4, bottom=8, left=4, right=4),
        content=ft.Column(
            spacing=4,
            expand=True,
            controls=[
                menu_header,
                ft.Divider(height=1, color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE)),
                menu_col,
            ],
        ),
    )

    ALIASES_TELAS = {
        "fluxo de caixa": "Fluxo Caixa",
        "fluxo caixa": "Fluxo Caixa",
        "fluxo": "Fluxo Caixa",
        "caixa": "Fluxo Caixa",
        "relatorio diario": "Rel. Diário",
        "relatório diário": "Rel. Diário",
        "relatorio": "Rel. Diário",
        "relatório": "Rel. Diário",
        "rel. diario": "Rel. Diário",
        "rel. diário": "Rel. Diário",
        "relatorio periodo": "Rel. Período",
        "relatório período": "Rel. Período",
        "rel. periodo": "Rel. Período",
        "rel. período": "Rel. Período",
        "pdv": "PDV",
        "vendas": "PDV",
        "pedidos": "PDV",
        "novo pedido": "PDV",
        "fornecedores": "Fornecedores",
        "boletos": "Fornecedores",
        "contas a pagar": "Fornecedores",
        "estoque": "Estoque",
        "produtos": "Estoque",
        "entregadores": "Entregadores",
        "motoboys": "Entregadores",
        "funcionarios": "Funcionários",
        "funcionários": "Funcionários",
        "equipe": "Funcionários",
        "escala geral": "Escala Geral",
        "escala": "Escala Geral",
        "fiados": "Fiados",
        "parametros": "Parâmetros",
        "parâmetros": "Parâmetros",
        "configuracoes": "Parâmetros",
        "configurações": "Parâmetros",
        "movim e caixa": "Movim. e Caixa",
        "movimentacoes": "Movim. e Caixa",
        "dashboard": "Dashboard",
        "inicio": "Dashboard",
        "agenda": "Agenda",
        "calendario": "Agenda",
        "calendário": "Agenda",
        "lembretes": "Agenda",
        "compromissos": "Agenda",
    }

    def navegar_para(destino):
        """
        Navega para uma tela por índice (int) ou por rótulo/alias (str, case-insensitive).
        Ex: page.navegar("PDV"), page.navegar("Fluxo de Caixa"), page.navegar("Relatório Diário").
        """
        if isinstance(destino, int):
            idx = destino
        else:
            destino_norm = str(destino).strip().lower()
            alvo = ALIASES_TELAS.get(destino_norm, destino_norm)
            idx = None
            for i, t in enumerate(telas_perm):
                rotulo = t["label"].strip().lower()
                if rotulo == alvo.lower() or rotulo == destino_norm:
                    idx = i
                    break
        if idx is not None and 0 <= idx < len(telas_perm):
            _idx_selecionado["v"] = idx
            _build_menu()
            carregar_view(idx)
        else:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Acesso à tela '{destino}' restrito ao perfil de acesso ({perfil})."),
                bgcolor=ft.Colors.ORANGE_800,
                open=True,
            ))
            page.update()

    page.navegar = navegar_para

    def carregar_view(indice: int):
        """
        Mostra um indicador de carregamento imediatamente sobrepondo a camada_loading
        e instancia a view selecionada em uma thread separada, trocando camada_view.content
        pelo resultado quando a construção terminar sem travar a UI na saída da tela anterior.
        """
        if _carregamento["indice_ativo"] == indice:
            return  # já há uma construção em andamento para este mesmo índice

        _t0 = time.perf_counter()
        try:
            nome_tela = telas_perm[indice]["label"]
        except (IndexError, KeyError):
            nome_tela = f"índice {indice}"

        _carregamento["geracao"] += 1
        minha_geracao = _carregamento["geracao"]
        _carregamento["indice_ativo"] = indice

        # Ativa o indicador de carregamento instantaneamente na camada superior
        # sem destruir os controles da tela anterior ainda (elimina a trava de saída)
        camada_loading.visible = True
        page.update()

        def _construir():
            try:
                resultado = _views[indice](page)
                exc = None
            except Exception as _exc:
                import traceback
                traceback.print_exc()
                resultado = None
                exc = _exc

            if _carregamento["indice_ativo"] == indice:
                _carregamento["indice_ativo"] = None

            if minha_geracao != _carregamento["geracao"]:
                return  # uma navegação mais recente já assumiu a tela

            camada_loading.visible = False

            if exc is not None:
                def _tentar_novamente(e, _idx=indice):
                    carregar_view(_idx)

                def _ir_pdv(e):
                    _idx_selecionado["v"] = 0
                    _build_menu()
                    carregar_view(0)
                    page.update()

                camada_view.content = ft.Column(controls=[
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
            else:
                camada_view.content = resultado

            page.update()
            _ms = (time.perf_counter() - _t0) * 1000
            _perf_logger.debug(f"{'main.carregar_view > ' + nome_tela:<55} {_ms:8.1f} ms")

        page.run_thread(_construir)

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

    def _ao_fechar(_e):
        ctypes.windll.kernel32.TerminateProcess(
            ctypes.windll.kernel32.GetCurrentProcess(), 0
        )

    page.on_disconnect = _ao_fechar

    # Carrega a primeira view ao iniciar
    _build_menu()
    carregar_view(0)
    logging.debug(f"primeira view carregada — {(time.perf_counter() - _t_boot)*1000:.0f}ms desde main()")


if __name__ == "__main__":
    _encerrar_instancias_anteriores()
    database.inicializar_banco()
    ft.app(target=_iniciar_app)
