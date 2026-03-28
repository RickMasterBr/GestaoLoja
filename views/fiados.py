"""
views/fiados.py — Controle de fiados: registro e quitação de dívidas de clientes.
"""

import flet as ft
from datetime import date

import database


# ── Helpers de confirmação (mesmo padrão das outras views) ─────────────────────

def _fechar(e, dlg, page):
    dlg.open = False
    page.update()


def _confirmar_exclusao(page, descricao: str, on_confirmar) -> None:
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar exclusão"),
        content=ft.Text(
            f"Deseja excluir {descricao}? Esta ação não pode ser desfeita."
        ),
        actions=[
            ft.TextButton("Cancelar",
                          on_click=lambda e: _fechar(e, dlg, page)),
            ft.ElevatedButton(
                "Excluir",
                on_click=lambda e: (_fechar(e, dlg, page), on_confirmar()),
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


def _iso(s: str) -> str:
    """Converte DD/MM/AAAA → YYYY-MM-DD; fallback para hoje."""
    try:
        d, m, a = s.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


def _br(iso: str) -> str:
    """Converte YYYY-MM-DD → DD/MM/AAAA."""
    try:
        a, m, d = iso.split("-")
        return f"{d}/{m}/{a}"
    except Exception:
        return iso


# ── View principal ─────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    hoje_br = date.today().strftime("%d/%m/%Y")

    # ── Formulário ─────────────────────────────────────────────────────────────
    tf_nome  = ft.TextField(label="Nome do cliente",       expand=True)
    tf_valor = ft.TextField(label="Valor (R$)",            expand=True,
                            keyboard_type=ft.KeyboardType.NUMBER)
    tf_desc  = ft.TextField(label="Descrição do pedido",   expand=True)
    tf_data  = ft.TextField(label="Data", value=hoje_br,   width=140,
                            text_align=ft.TextAlign.CENTER,
                            hint_text="DD/MM/AAAA")
    tf_obs   = ft.TextField(label="Observações",           expand=True,
                            multiline=True, min_lines=2, max_lines=4)
    txt_erro = ft.Text("", color=ft.Colors.RED_400, size=12)

    # ── Tabela ──────────────────────────────────────────────────────────────────
    cb_apenas_abertos = ft.Checkbox(label="Mostrar apenas abertos", value=True)
    tabela_col        = ft.Column(spacing=0)
    txt_total         = ft.Text("", size=14, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ORANGE_400)

    def _refresh(e=None):
        apenas = cb_apenas_abertos.value
        rows   = database.fiado_listar(apenas_abertos=apenas)
        total  = database.fiado_total_aberto()
        txt_total.value = f"Total em aberto: R$ {total:.2f}"

        linhas = []
        for f in rows:
            pago = bool(f["pago"])

            if pago:
                status_chip = ft.Container(
                    padding=ft.Padding.all(6),
                    border_radius=12,
                    bgcolor=ft.Colors.GREEN_900,
                    content=ft.Text("Quitado", size=12,
                                    color=ft.Colors.GREEN_300),
                )
                acoes = ft.Icon(ft.Icons.CHECK_CIRCLE,
                                color=ft.Colors.GREEN_400, size=20)
            else:
                status_chip = ft.Container(
                    padding=ft.Padding.all(6),
                    border_radius=12,
                    bgcolor=ft.Colors.ORANGE_900,
                    content=ft.Text("Em aberto", size=12,
                                    color=ft.Colors.ORANGE_300),
                )

                def _abrir_quitar(fid, fnome, fvalor):
                    def handler(e):
                        tf_pgto = ft.TextField(
                            label="Data de pagamento",
                            value=hoje_br,
                            width=160,
                            text_align=ft.TextAlign.CENTER,
                            hint_text="DD/MM/AAAA",
                        )

                        def _on_confirmar_quitar(ev):
                            _fechar(ev, dlg, page)
                            database.fiado_quitar(fid, _iso(tf_pgto.value))
                            database.log_registrar(
                                acao="QUITAR_FIADO",
                                tabela="fiados",
                                id_registro=fid,
                                descricao=f"Fiado quitado — Cliente: {fnome} | "
                                          f"Valor: R$ {fvalor:.2f}",
                            )
                            _refresh()
                            page.update()

                        dlg = ft.AlertDialog(
                            modal=True,
                            title=ft.Text(f"Quitar fiado de {fnome}"),
                            content=tf_pgto,
                            actions=[
                                ft.TextButton(
                                    "Cancelar",
                                    on_click=lambda e: _fechar(e, dlg, page),
                                ),
                                ft.ElevatedButton(
                                    "Confirmar",
                                    on_click=_on_confirmar_quitar,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.GREEN_700,
                                        color=ft.Colors.WHITE,
                                    ),
                                ),
                            ],
                            actions_alignment=ft.MainAxisAlignment.END,
                        )
                        page.overlay.append(dlg)
                        dlg.open = True
                        page.update()
                    return handler

                def _on_excluir(fid, fnome, fvalor):
                    def handler(e):
                        def _excluir():
                            database.fiado_excluir(fid)
                            database.log_registrar(
                                acao="EXCLUIR_FIADO",
                                tabela="fiados",
                                id_registro=fid,
                                descricao=f"Fiado excluído — Cliente: {fnome} | "
                                          f"Valor: R$ {fvalor:.2f}",
                            )
                            _refresh()
                            page.update()
                        _confirmar_exclusao(page, "este fiado", _excluir)
                    return handler

                acoes = ft.Row(spacing=0, controls=[
                    ft.ElevatedButton(
                        "Quitar",
                        icon=ft.Icons.ATTACH_MONEY,
                        on_click=_abrir_quitar(f["id"], f["nome_cliente"], f["valor"]),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.GREEN_800,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Excluir fiado",
                        on_click=_on_excluir(f["id"], f["nome_cliente"], f["valor"]),
                    ),
                ])

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(_br(f["data_lancamento"]), size=12)),
                ft.DataCell(ft.Text(f["nome_cliente"])),
                ft.DataCell(ft.Text(f["descricao"] or "—", size=12,
                                    color=ft.Colors.GREY_500)),
                ft.DataCell(ft.Text(f"R$ {f['valor']:.2f}",
                                    weight=ft.FontWeight.BOLD)),
                ft.DataCell(status_chip),
                ft.DataCell(acoes),
            ]))

        tabela_col.controls.clear()
        if not linhas:
            tabela_col.controls.append(
                ft.Text("Nenhum fiado encontrado.", italic=True,
                        color=ft.Colors.GREY_500)
            )
        else:
            tabela_col.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Data")),
                            ft.DataColumn(ft.Text("Cliente")),
                            ft.DataColumn(ft.Text("Descrição")),
                            ft.DataColumn(ft.Text("Valor"), numeric=True),
                            ft.DataColumn(ft.Text("Status")),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=linhas,
                    ),
                ])
            )

        page.update()

    def _registrar(e):
        txt_erro.value = ""
        nome = tf_nome.value.strip()
        if not nome:
            txt_erro.value = "Nome do cliente é obrigatório."
            page.update()
            return
        try:
            valor = float(
                (tf_valor.value or "0").replace(",", ".").strip()
            )
            if valor <= 0:
                raise ValueError
        except ValueError:
            txt_erro.value = "Informe um valor válido maior que zero."
            page.update()
            return

        database.fiado_inserir(
            data=_iso(tf_data.value or hoje_br),
            nome_cliente=nome,
            valor=valor,
            descricao=tf_desc.value.strip() or None,
            obs=tf_obs.value.strip() or None,
        )
        tf_nome.value  = ""
        tf_valor.value = ""
        tf_desc.value  = ""
        tf_obs.value   = ""
        tf_data.value  = hoje_br
        page.overlay.append(ft.SnackBar(
            content=ft.Text(f"Fiado de {nome} registrado!"),
            bgcolor=ft.Colors.INDIGO_700, open=True,
        ))
        _refresh()

    cb_apenas_abertos.on_change = _refresh
    _refresh()

    # ── Layout ─────────────────────────────────────────────────────────────────
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            # Formulário
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    ft.Text("Registrar Novo Fiado", size=14,
                            weight=ft.FontWeight.BOLD),
                    ft.Row([tf_nome, tf_valor], spacing=12),
                    ft.Row([tf_desc, tf_data], spacing=12),
                    tf_obs,
                    txt_erro,
                    ft.ElevatedButton(
                        "Registrar Fiado",
                        icon=ft.Icons.ADD,
                        on_click=_registrar,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.INDIGO_600,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ]),
            )),
            # Tabela
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=10, controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Fiados", size=14,
                                    weight=ft.FontWeight.BOLD),
                            cb_apenas_abertos,
                        ],
                        spacing=16,
                    ),
                    ft.Divider(height=1),
                    tabela_col,
                    ft.Divider(height=1),
                    txt_total,
                ]),
            )),
        ],
    )
