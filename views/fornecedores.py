"""
views/fornecedores.py — Cadastro e gestão de fornecedores.
"""

import flet as ft

import database


def view(page: ft.Page) -> ft.Control:

    # ── Estado ────────────────────────────────────────────────────────────────
    _id_edicao: dict = {"v": None}   # None = novo registro

    # ── Campos do formulário ──────────────────────────────────────────────────
    tf_nome     = ft.TextField(label="Nome *", expand=True)
    tf_telefone = ft.TextField(label="Telefone", width=180)
    tf_email    = ft.TextField(label="E-mail", expand=True)
    tf_cnpj     = ft.TextField(label="CNPJ / CPF", width=200)
    tf_endereco = ft.TextField(label="Endereço", expand=True)
    tf_obs      = ft.TextField(
        label="Observações",
        multiline=True, min_lines=2, expand=True,
    )
    cb_ativo    = ft.Checkbox(label="Ativo", value=True)
    txt_erro    = ft.Text("", color=ft.Colors.RED_400, size=12)

    # ── Filtro da tabela ──────────────────────────────────────────────────────
    cb_apenas_ativos = ft.Checkbox(
        label="Mostrar apenas ativos", value=True,
        on_change=lambda e: _carregar(),
    )

    tabela_col = ft.Column(spacing=0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _limpar():
        _id_edicao["v"] = None
        tf_nome.value     = ""
        tf_telefone.value = ""
        tf_email.value    = ""
        tf_cnpj.value     = ""
        tf_endereco.value = ""
        tf_obs.value      = ""
        cb_ativo.value    = True
        txt_erro.value    = ""
        btn_cancelar.visible = False
        lbl_titulo.value  = "Novo Fornecedor"

    def _carregar():
        apenas_ativos = cb_apenas_ativos.value
        fornecedores  = database.fornecedor_listar(apenas_ativos=apenas_ativos)

        tabela_col.controls.clear()

        # Cabeçalho
        tabela_col.controls.append(ft.Row(
            spacing=0,
            controls=[
                ft.Container(expand=3, content=ft.Text(
                    "Nome", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=140, content=ft.Text(
                    "Telefone", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(expand=2, content=ft.Text(
                    "E-mail", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=160, content=ft.Text(
                    "CNPJ / CPF", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=80, content=ft.Text(
                    "Status", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=130, content=ft.Text(
                    "Ações", size=11, weight=ft.FontWeight.BOLD)),
            ],
        ))
        tabela_col.controls.append(ft.Divider(height=1))

        if not fornecedores:
            tabela_col.controls.append(ft.Text(
                "Nenhum fornecedor encontrado.",
                italic=True, color=ft.Colors.GREY_500,
            ))
            page.update()
            return

        for f in fornecedores:
            ativo      = bool(f["ativo"])
            cor_status = ft.Colors.GREEN_400 if ativo else ft.Colors.GREY_500
            txt_status = "Ativo"            if ativo else "Inativo"

            def _fazer_editar(forn=f):
                return lambda e: _editar(forn)

            def _fazer_inativar(fid=f["id"], fat=ativo):
                return lambda e: _confirmar_inativar(fid, fat)

            tabela_col.controls.append(ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(expand=3, content=ft.Text(f["nome"], size=13)),
                    ft.Container(width=140, content=ft.Text(f["telefone"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(expand=2, content=ft.Text(f["email"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(width=160, content=ft.Text(f["cnpj_cpf"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(width=80, content=ft.Text(
                        txt_status, size=12, color=cor_status, weight=ft.FontWeight.BOLD,
                    )),
                    ft.Container(width=130, content=ft.Row(spacing=4, controls=[
                        ft.TextButton(
                            "Editar",
                            on_click=_fazer_editar(),
                        ),
                        ft.TextButton(
                            "Inativar" if ativo else "Reativar",
                            on_click=_fazer_inativar(),
                            style=ft.ButtonStyle(
                                color=ft.Colors.RED_400 if ativo else ft.Colors.GREEN_400,
                            ),
                        ),
                    ])),
                ],
            ))
            tabela_col.controls.append(ft.Divider(height=1, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK)))

        page.update()

    def _editar(forn):
        _id_edicao["v"]   = forn["id"]
        tf_nome.value     = forn["nome"] or ""
        tf_telefone.value = forn["telefone"] or ""
        tf_email.value    = forn["email"] or ""
        tf_cnpj.value     = forn["cnpj_cpf"] or ""
        tf_endereco.value = forn["endereco"] or ""
        tf_obs.value      = forn["obs"] or ""
        cb_ativo.value    = bool(forn["ativo"])
        txt_erro.value    = ""
        btn_cancelar.visible = True
        lbl_titulo.value  = f"Editando: {forn['nome']}"
        page.update()

    def _salvar(e):
        nome = tf_nome.value.strip()
        if not nome:
            txt_erro.value = "O nome do fornecedor é obrigatório."
            page.update()
            return

        if _id_edicao["v"] is None:
            database.fornecedor_inserir(
                nome=nome,
                telefone=tf_telefone.value.strip() or None,
                email=tf_email.value.strip() or None,
                cnpj_cpf=tf_cnpj.value.strip() or None,
                endereco=tf_endereco.value.strip() or None,
                obs=tf_obs.value.strip() or None,
            )
        else:
            database.fornecedor_atualizar(
                _id_edicao["v"],
                nome=nome,
                telefone=tf_telefone.value.strip() or None,
                email=tf_email.value.strip() or None,
                cnpj_cpf=tf_cnpj.value.strip() or None,
                endereco=tf_endereco.value.strip() or None,
                obs=tf_obs.value.strip() or None,
                ativo=1 if cb_ativo.value else 0,
            )

        page.overlay.append(ft.SnackBar(
            content=ft.Text("Fornecedor salvo com sucesso."),
            bgcolor=ft.Colors.GREEN_700, open=True,
        ))
        _limpar()
        _carregar()

    def _confirmar_inativar(id_forn: int, ativo_atual: bool):
        acao  = "inativar" if ativo_atual else "reativar"
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Confirmar {acao}"),
            content=ft.Text(
                f"Deseja {acao} este fornecedor?"
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (
                    setattr(dlg, "open", False), page.update()
                )),
                ft.ElevatedButton(
                    acao.capitalize(),
                    on_click=lambda e: _executar_inativar(dlg, id_forn, ativo_atual),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_700 if ativo_atual else ft.Colors.GREEN_700,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _executar_inativar(dlg, id_forn: int, ativo_atual: bool):
        dlg.open = False
        if ativo_atual:
            database.fornecedor_inativar(id_forn)
        else:
            database.fornecedor_atualizar(id_forn, ativo=1)
        _carregar()

    # ── Controles com estado ──────────────────────────────────────────────────
    lbl_titulo   = ft.Text("Novo Fornecedor", size=15, weight=ft.FontWeight.BOLD)
    btn_cancelar = ft.TextButton(
        "Cancelar",
        on_click=lambda e: (_limpar(), _carregar()),
        visible=False,
    )

    bloco_form = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Column(spacing=12, controls=[
            ft.Row(controls=[lbl_titulo, ft.Container(expand=True), btn_cancelar]),
            ft.Divider(height=1),
            tf_nome,
            ft.Row([tf_telefone, tf_email], spacing=12),
            ft.Row([tf_cnpj, tf_endereco], spacing=12),
            tf_obs,
            cb_ativo,
            txt_erro,
            ft.Row(controls=[
                ft.ElevatedButton(
                    "Salvar Fornecedor",
                    icon=ft.Icons.SAVE,
                    on_click=_salvar,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.TEAL_700,
                        color=ft.Colors.WHITE,
                    ),
                ),
            ]),
        ]),
    ))

    bloco_tabela = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Column(spacing=10, controls=[
            ft.Text("Fornecedores Cadastrados", size=15, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            cb_apenas_ativos,
            tabela_col,
        ]),
    ))

    _carregar()

    return ft.Column(
        controls=[bloco_form, bloco_tabela],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
