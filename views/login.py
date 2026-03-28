"""
views/login.py — Tela de login com seleção de usuário e PIN numérico.
"""

import threading

import flet as ft

import database


def view(page: ft.Page, on_login_success) -> ft.Control:
    usuarios = database.usuario_listar_ativos()

    # ── Estado ────────────────────────────────────────────────────────────
    _pin_atual: list = []
    _sel: dict = {"id": None, "nome": None, "perfil": None}

    # ── Display de PIN — 4 círculos ───────────────────────────────────────
    _circulos = [
        ft.Container(
            width=20, height=20, border_radius=10,
            bgcolor=None,
            border=ft.border.all(2, ft.Colors.GREY_600),
        )
        for _ in range(4)
    ]
    display_pin = ft.Row(
        spacing=12,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=_circulos,
    )

    def _atualizar_display():
        for i, c in enumerate(_circulos):
            if i < len(_pin_atual):
                c.bgcolor = ft.Colors.TEAL_400
                c.border  = None
            else:
                c.bgcolor = None
                c.border  = ft.border.all(2, ft.Colors.GREY_600)

    # ── Textos da fase PIN ────────────────────────────────────────────────
    txt_ola     = ft.Text("", size=18, weight=ft.FontWeight.BOLD,
                          text_align=ft.TextAlign.CENTER)
    txt_instruc = ft.Text("Digite seu PIN:", size=13, color=ft.Colors.GREY_500,
                          text_align=ft.TextAlign.CENTER)
    txt_erro    = ft.Text("", color=ft.Colors.RED_400, size=13,
                          text_align=ft.TextAlign.CENTER, visible=False)

    # ── Verificação automática ────────────────────────────────────────────
    def _verificar():
        pin_str = "".join(_pin_atual)
        if database.usuario_autenticar(_sel["id"], pin_str):
            database.sessao_iniciar(_sel["id"], _sel["nome"], _sel["perfil"])
            on_login_success(_sel["perfil"])
        else:
            _pin_atual.clear()
            _atualizar_display()
            txt_erro.value   = "PIN incorreto. Tente novamente."
            txt_erro.visible = True
            page.update()

            def _limpar_erro():
                txt_erro.value   = ""
                txt_erro.visible = False
                page.update()

            threading.Timer(2.0, _limpar_erro).start()

    # ── Teclado numérico ──────────────────────────────────────────────────
    def _digitar(d: str):
        def handler(e):
            if len(_pin_atual) >= 4:
                return
            _pin_atual.append(d)
            _atualizar_display()
            txt_erro.visible = False
            page.update()
            if len(_pin_atual) == 4:
                _verificar()
        return handler

    def _apagar(e):
        if _pin_atual:
            _pin_atual.pop()
            _atualizar_display()
            txt_erro.visible = False
            page.update()

    def _btn_n(label: str) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            label,
            on_click=_digitar(label),
            width=80, height=60,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        )

    teclado = ft.Column(
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                   controls=[_btn_n("1"), _btn_n("2"), _btn_n("3")]),
            ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                   controls=[_btn_n("4"), _btn_n("5"), _btn_n("6")]),
            ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                   controls=[_btn_n("7"), _btn_n("8"), _btn_n("9")]),
            ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                   controls=[
                       ft.Container(width=80, height=60),
                       _btn_n("0"),
                       ft.ElevatedButton(
                           "⌫",
                           on_click=_apagar,
                           width=80, height=60,
                           style=ft.ButtonStyle(
                               shape=ft.RoundedRectangleBorder(radius=8),
                           ),
                       ),
                   ]),
        ],
    )

    # ── Navegação entre fases ─────────────────────────────────────────────
    fase_selecao = ft.Column(visible=True,  horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12, controls=[])
    fase_pin     = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16, controls=[])

    def _voltar(e):
        _pin_atual.clear()
        _atualizar_display()
        txt_erro.visible     = False
        fase_pin.visible     = False
        fase_selecao.visible = True
        page.update()

    def _selecionar(u):
        def handler(e):
            _sel["id"]    = u["id"]
            _sel["nome"]  = u["nome"]
            _sel["perfil"] = u["perfil_acesso"]
            _pin_atual.clear()
            _atualizar_display()
            txt_ola.value        = f"Olá, {u['nome']}!"
            txt_erro.visible     = False
            fase_selecao.visible = False
            fase_pin.visible     = True
            page.update()
        return handler

    # ── Montar fase de seleção ────────────────────────────────────────────
    fase_selecao.controls += [
        ft.Text("Quem está acessando?", size=14, color=ft.Colors.GREY_500,
                text_align=ft.TextAlign.CENTER),
        ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.ElevatedButton(
                    u["nome"],
                    icon=ft.Icons.PERSON,
                    on_click=_selecionar(u),
                    width=320,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
                    ),
                )
                for u in usuarios
            ],
        ),
    ]

    # ── Montar fase de PIN ────────────────────────────────────────────────
    fase_pin.controls += [
        txt_ola,
        txt_instruc,
        display_pin,
        txt_erro,
        teclado,
        ft.TextButton("← Voltar", on_click=_voltar),
    ]

    # ── Conteúdo do card ──────────────────────────────────────────────────
    nome_loja = database.config_obter("nome_loja", "Gestão Loja")

    if usuarios:
        conteudo = ft.Column(
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(nome_loja, size=22, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER),
                fase_selecao,
                fase_pin,
            ],
        )
    else:
        def _entrar_sem_auth(e):
            database.sessao_iniciar(0, "Administrador", "ADMIN")
            on_login_success("ADMIN")

        conteudo = ft.Column(
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(nome_loja, size=22, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER),
                ft.Icon(ft.Icons.LOCK_OPEN, size=48, color=ft.Colors.GREY_500),
                ft.Text(
                    "Nenhum usuário configurado.\n"
                    "Acesse Parâmetros > Pessoas para cadastrar PINs.",
                    size=13, color=ft.Colors.GREY_500,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.ElevatedButton(
                    "Entrar sem autenticação",
                    icon=ft.Icons.LOGIN,
                    on_click=_entrar_sem_auth,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.TEAL_700, color=ft.Colors.WHITE,
                    ),
                ),
            ],
        )

    card = ft.Card(
        width=380,
        content=ft.Container(
            padding=ft.Padding.all(32),
            content=conteudo,
        ),
    )

    return ft.Column(
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
        controls=[card],
    )
