"""
views/fornecedores.py — Cadastro e gestão de fornecedores.
"""

import flet as ft
from datetime import date, timedelta

import database


# ── Helpers de data ───────────────────────────────────────────────────────────

def _br_iso(s: str) -> str:
    try:
        d, m, a = s.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return ""


def _iso_br(s: str) -> str:
    try:
        return f"{s[8:10]}/{s[5:7]}/{s[:4]}"
    except Exception:
        return s


# ── Diálogos de confirmação ───────────────────────────────────────────────────

def _fechar(dlg, page):
    dlg.open = False
    page.update()


def _dialogo_quitar(page, titulo: str, subtitulo: str,
                    valor_default: float, on_confirmar) -> None:
    """
    Confirmação de quitação com data, valor e método editáveis.
    Chama on_confirmar(data_iso, valor, metodo) só depois de validar.

    O valor é editável para cobrir desconto/juros: ele altera apenas o
    lançamento no caixa — a parcela/boleto é marcada como quitada de todo jeito.
    """
    tf_data = ft.TextField(
        label="Data do pagamento", width=170,
        value=date.today().strftime("%d/%m/%Y"), hint_text="DD/MM/AAAA",
    )
    tf_valor = ft.TextField(
        label="Valor pago (R$)", width=170,
        value=f"{valor_default:.2f}",
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    dd_metodo = ft.Dropdown(
        label="Método", width=180, value="Dinheiro",
        options=[ft.dropdown.Option(m["nome"])
                 for m in database.metodo_pag_listar()],
    )
    txt_erro = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _confirmar(e):
        data_iso = _br_iso(tf_data.value or "")
        if not data_iso:
            txt_erro.value = "Informe a data no formato DD/MM/AAAA."
            page.update()
            return
        try:
            valor = float((tf_valor.value or "0").replace(",", "."))
            assert valor > 0
        except Exception:
            txt_erro.value = "Informe um valor válido."
            page.update()
            return
        _fechar(dlg, page)
        on_confirmar(data_iso, valor, dd_metodo.value)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(titulo),
        content=ft.Column(tight=True, width=560, spacing=12, controls=[
            ft.Text(subtitulo, size=13, color=ft.Colors.GREY_400),
            ft.Row([tf_data, tf_valor, dd_metodo], spacing=10, wrap=True),
            ft.Text(
                "A quitação gera uma saída no Fluxo de Caixa "
                f"(categoria '{database.CATEGORIA_PAGAMENTO_FORNECEDOR}').",
                size=11, italic=True, color=ft.Colors.GREY_500,
            ),
            txt_erro,
        ]),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _fechar(dlg, page)),
            ft.ElevatedButton(
                "Confirmar Pagamento", icon=ft.Icons.PAYMENTS,
                on_click=_confirmar,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700,
                                     color=ft.Colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def _dialogo_excluir_boleto(page, descricao: str, valor: float,
                            on_confirmar) -> None:
    """Confirmação antes de excluir um boleto (mesmo padrão do estorno)."""
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar Exclusão"),
        content=ft.Text(
            f"Deseja excluir o boleto \"{descricao}\" "
            f"(R$ {valor:.2f})?\n\n"
            f"Todas as parcelas vinculadas serão removidas. "
            f"Esta ação não pode ser desfeita."
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _fechar(dlg, page)),
            ft.ElevatedButton(
                "Confirmar Exclusão", icon=ft.Icons.DELETE_OUTLINE,
                on_click=lambda e: (_fechar(dlg, page), on_confirmar()),
                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700,
                                     color=ft.Colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def view(page: ft.Page) -> ft.Control:

    # ── Estado ────────────────────────────────────────────────────────────────
    _id_edicao: dict = {"v": None}   # None = novo registro

    # ── Campos do formulário ──────────────────────────────────────────────────
    tf_nome     = ft.TextField(label="Nome *", expand=True)
    tf_telefone = ft.TextField(label="Telefone", width=180)
    tf_email    = ft.TextField(label="E-mail", expand=True)
    tf_cnpj     = ft.TextField(label="CNPJ / CPF", width=200)
    tf_endereco = ft.TextField(label="Endereço", expand=True)
    tf_vendedor = ft.TextField(label="Vendedor / Contato", expand=True)
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

    # ── Contas a pagar (visão consolidada de vencimentos) ─────────────────────
    row_aging      = ft.Row(spacing=12, wrap=True)
    col_vencimentos = ft.Column(spacing=0)
    dd_janela = ft.Dropdown(
        label="Janela", width=170, value="30",
        options=[
            ft.dropdown.Option("7",  "Próximos 7 dias"),
            ft.dropdown.Option("15", "Próximos 15 dias"),
            ft.dropdown.Option("30", "Próximos 30 dias"),
            ft.dropdown.Option("90", "Próximos 90 dias"),
        ],
        on_select=lambda e: (_carregar_vencimentos(), page.update()),
    )

    _FAIXAS = [
        ("VENCIDO", "Vencido",        ft.Colors.RED_400),
        ("HOJE",    "Vence hoje",     ft.Colors.ORANGE_400),
        ("ATE_7",   "Até 7 dias",     ft.Colors.YELLOW_700),
        ("ATE_30",  "Mais adiante",   ft.Colors.GREY_500),
    ]

    def _notificar_quitacao(ok: bool, valor: float):
        """Feedback do resultado da quitação (False = já estava quitado)."""
        if ok:
            texto, cor = (f"Pagamento de R$ {valor:.2f} registrado no caixa.",
                          ft.Colors.GREEN_700)
        else:
            texto, cor = ("Nada a quitar — já estava pago. "
                          "Nenhum lançamento gerado.", ft.Colors.ORANGE_700)
        page.overlay.append(ft.SnackBar(content=ft.Text(texto),
                                        bgcolor=cor, open=True))

    def _carregar_vencimentos():
        # Atualiza o status de vencidos de forma central, para todos os
        # fornecedores — antes só acontecia ao abrir o diálogo de um deles.
        database.boleto_atualizar_status_vencidos()

        try:
            dias = int(dd_janela.value or 30)
        except ValueError:
            dias = 30
        parcelas = database.boletos_parcelas_em_aberto(dias_frente=dias)

        # Cards de aging
        row_aging.controls.clear()
        for chave, rotulo, cor in _FAIXAS:
            do_grupo = [p for p in parcelas if p["faixa"] == chave]
            total    = sum(p["valor"] for p in do_grupo)
            row_aging.controls.append(ft.Container(
                padding=ft.Padding.all(12),
                border_radius=8,
                width=180,
                content=ft.Column(spacing=2, tight=True, controls=[
                    ft.Text(rotulo, size=11, color=ft.Colors.GREY_500),
                    ft.Text(f"R$ {total:.2f}", size=17,
                            weight=ft.FontWeight.BOLD, color=cor),
                    ft.Text(f"{len(do_grupo)} parcela(s)", size=11,
                            color=ft.Colors.GREY_500),
                ]),
            ))

        col_vencimentos.controls.clear()
        if not parcelas:
            col_vencimentos.controls.append(ft.Text(
                "Nenhuma parcela em aberto nessa janela.",
                italic=True, color=ft.Colors.GREY_500,
            ))
            return

        linhas = []
        for p in parcelas:
            cor_faixa = next(c for k, _r, c in _FAIXAS if k == p["faixa"])
            dias_txt = (
                f"{abs(p['dias_para_vencer'])}d atrás"
                if p["dias_para_vencer"] < 0 else
                "hoje" if p["dias_para_vencer"] == 0 else
                f"em {p['dias_para_vencer']}d"
            )
            parc_txt = (f"{p['num_parcela']}/{p['num_parcelas']}"
                        if p["num_parcelas"] > 1 else "única")

            def _quitar(ev, _pid=p["id"], _nome=p["nome_fornecedor"],
                        _desc=p["descricao"], _val=p["valor"],
                        _pnum=p["num_parcela"]):
                def _executar(data_iso, valor, metodo):
                    ok = database.boleto_quitar_parcela(
                        _pid, data_iso, metodo=metodo, valor_pago=valor,
                    )
                    _notificar_quitacao(ok, valor)
                    _carregar_vencimentos()
                    page.update()

                _dialogo_quitar(
                    page,
                    f"Quitar Parcela {_pnum}",
                    f"{_nome} — {_desc}\nParcela {_pnum}: R$ {_val:.2f}",
                    _val,
                    _executar,
                )

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(_iso_br(p["vencimento"]), size=12,
                                    color=cor_faixa,
                                    weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(dias_txt, size=12, color=cor_faixa)),
                ft.DataCell(ft.Text(p["nome_fornecedor"], size=12)),
                ft.DataCell(ft.Text(p["descricao"], size=12)),
                ft.DataCell(ft.Text(parc_txt, size=12,
                                    color=ft.Colors.GREY_500)),
                ft.DataCell(ft.Text(f"R$ {p['valor']:.2f}", size=12,
                                    color=ft.Colors.TEAL_300)),
                ft.DataCell(ft.TextButton(
                    "Quitar", icon=ft.Icons.PAYMENTS, on_click=_quitar,
                    style=ft.ButtonStyle(color=ft.Colors.GREEN_400),
                )),
            ]))

        col_vencimentos.controls.append(ft.Row(
            scroll=ft.ScrollMode.AUTO,
            controls=[ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Vencimento", size=12)),
                    ft.DataColumn(ft.Text("Prazo",      size=12)),
                    ft.DataColumn(ft.Text("Fornecedor", size=12)),
                    ft.DataColumn(ft.Text("Descrição",  size=12)),
                    ft.DataColumn(ft.Text("Parcela",    size=12)),
                    ft.DataColumn(ft.Text("Valor",      size=12), numeric=True),
                    ft.DataColumn(ft.Text("Ação",       size=12)),
                ],
                rows=linhas,
                column_spacing=14,
                horizontal_lines=ft.BorderSide(
                    1, ft.Colors.with_opacity(0.15, ft.Colors.BLACK)
                ),
            )],
        ))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _limpar():
        _id_edicao["v"] = None
        tf_nome.value     = ""
        tf_telefone.value = ""
        tf_email.value    = ""
        tf_cnpj.value     = ""
        tf_endereco.value = ""
        tf_vendedor.value = ""
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
                ft.Container(expand=2, content=ft.Text(
                    "Vendedor", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=80, content=ft.Text(
                    "Status", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=180, content=ft.Text(
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

            def _fazer_boletos(fid=f["id"], fnome=f["nome"]):
                return lambda e: _abrir_boletos(fid, fnome)

            tabela_col.controls.append(ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(expand=3, content=ft.Text(f["nome"], size=13)),
                    ft.Container(width=140, content=ft.Text(f["telefone"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(expand=2, content=ft.Text(f["email"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(width=160, content=ft.Text(f["cnpj_cpf"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(expand=2, content=ft.Text(f["vendedor"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(width=80, content=ft.Text(
                        txt_status, size=12, color=cor_status, weight=ft.FontWeight.BOLD,
                    )),
                    ft.Container(width=180, content=ft.Row(spacing=2, controls=[
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
                        ft.TextButton(
                            "Boletos",
                            on_click=_fazer_boletos(),
                            style=ft.ButtonStyle(color=ft.Colors.BLUE_300),
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
        tf_vendedor.value = forn["vendedor"] or ""
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
                vendedor=tf_vendedor.value.strip() or None,
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
                vendedor=tf_vendedor.value.strip() or None,
                obs=tf_obs.value.strip() or None,
                ativo=1 if cb_ativo.value else 0,
            )

        page.overlay.append(ft.SnackBar(
            content=ft.Text("Fornecedor salvo com sucesso."),
            bgcolor=ft.Colors.GREEN_700, open=True,
        ))
        _limpar()
        _carregar()

    # ── Boletos ───────────────────────────────────────────────────────────────

    def _abrir_boletos(id_forn: int, nome_forn: str):
        def _recarregar_dialog():
            database.boleto_atualizar_status_vencidos()
            boletos = database.boleto_listar(id_fornecedor=id_forn)
            linhas.controls.clear()
            if not boletos:
                linhas.controls.append(ft.Text(
                    "Nenhum boleto cadastrado.", italic=True,
                    color=ft.Colors.GREY_500,
                ))
            else:
                for b in boletos:
                    cor = (ft.Colors.GREEN_400 if b["status"] == "PAGO"
                           else ft.Colors.RED_400 if b["status"] == "VENCIDO"
                           else ft.Colors.ORANGE_300)
                    parcelas = database.boleto_parcelas_listar(b["id"])
                    prox_venc = next(
                        (p["vencimento"] for p in parcelas if not p["pago"]), None
                    )
                    prox_txt = f"Próx. venc: {_iso_br(prox_venc)}" if prox_venc else ""

                    # Total ainda em aberto: é o que será pago e lançado no caixa
                    _aberto = sum(p["valor"] for p in parcelas if not p["pago"])

                    def _quitar_boleto(ev, _bid=b["id"], _bdesc=b["descricao"],
                                       _aberto=_aberto, _nparc=len(parcelas)):
                        def _executar(data_iso, valor, metodo):
                            ok = database.boleto_quitar(
                                _bid, data_pago=data_iso,
                                metodo=metodo, valor_pago=valor,
                            )
                            _notificar_quitacao(ok, valor)
                            _recarregar_dialog()
                            _carregar_vencimentos()
                            page.update()

                        _dialogo_quitar(
                            page,
                            "Quitar Boleto",
                            f"{nome_forn} — {_bdesc}\n"
                            f"{_nparc} parcela(s), R$ {_aberto:.2f} em aberto.",
                            _aberto,
                            _executar,
                        )

                    def _excluir_boleto(ev, _bid=b["id"], _bdesc=b["descricao"],
                                        _bval=b["valor_total"]):
                        def _executar():
                            database.boleto_excluir(_bid)
                            database.log_registrar(
                                acao="EXCLUIR_BOLETO",
                                tabela="cad_boletos",
                                id_registro=_bid,
                                descricao=f"Boleto excluído — {nome_forn}: "
                                          f"{_bdesc} | R$ {_bval:.2f}",
                                valor_antes=f"descricao={_bdesc}, valor_total={_bval}",
                                usuario=database.sessao_obter().get("nome"),
                            )
                            page.overlay.append(ft.SnackBar(
                                content=ft.Text(f"Boleto \"{_bdesc}\" excluído."),
                                bgcolor=ft.Colors.ORANGE_700, open=True,
                            ))
                            _recarregar_dialog()
                            _carregar_vencimentos()
                            page.update()

                        _dialogo_excluir_boleto(page, _bdesc, _bval, _executar)

                    def _ver_parcelas(ev, _bid=b["id"], _bdesc=b["descricao"]):
                        parcs = database.boleto_parcelas_listar(_bid)
                        linhas_p = []
                        for p in parcs:
                            cor_p = ft.Colors.GREEN_400 if p["pago"] else ft.Colors.ORANGE_300

                            def _quitar_parcela(ev2, _pid=p["id"],
                                                _pnum=p["num_parcela"],
                                                _pval=p["valor"]):
                                def _executar(data_iso, valor, metodo):
                                    ok = database.boleto_quitar_parcela(
                                        _pid, data_iso,
                                        metodo=metodo, valor_pago=valor,
                                    )
                                    _notificar_quitacao(ok, valor)
                                    _recarregar_dialog()
                                    _carregar_vencimentos()
                                    dlg_p.open = False
                                    page.update()

                                _dialogo_quitar(
                                    page,
                                    f"Quitar Parcela {_pnum}",
                                    f"{nome_forn} — {_bdesc}\n"
                                    f"Parcela {_pnum}: R$ {_pval:.2f}",
                                    _pval,
                                    _executar,
                                )

                            linhas_p.append(ft.Row(controls=[
                                ft.Text(f"Parcela {p['num_parcela']}", width=80, size=12),
                                ft.Text(f"R$ {p['valor']:.2f}", width=90, size=12),
                                ft.Text(_iso_br(p["vencimento"]), width=90, size=12),
                                ft.Text(
                                    "Pago" if p["pago"] else "Em aberto",
                                    width=80, size=12, color=cor_p,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                *([] if p["pago"] else [ft.TextButton(
                                    "Quitar",
                                    on_click=_quitar_parcela,
                                    style=ft.ButtonStyle(color=ft.Colors.GREEN_400),
                                )]),
                            ]))

                        dlg_p = ft.AlertDialog(
                            modal=True,
                            title=ft.Text(f"Parcelas — {_bdesc}"),
                            content=ft.Column(
                                controls=linhas_p or [ft.Text("Sem parcelas.")],
                                scroll=ft.ScrollMode.AUTO,
                                height=300,
                                width=500,
                            ),
                            actions=[ft.TextButton("Fechar", on_click=lambda e: (
                                setattr(dlg_p, "open", False), page.update()
                            ))],
                            actions_alignment=ft.MainAxisAlignment.END,
                        )
                        page.overlay.append(dlg_p)
                        dlg_p.open = True
                        page.update()

                    acoes = [
                        ft.Text(
                            b["status"], size=11, color=cor,
                            weight=ft.FontWeight.BOLD, width=70,
                        ),
                    ]
                    if b["status"] != "PAGO":
                        acoes.append(ft.TextButton(
                            "Quitar tudo",
                            on_click=_quitar_boleto,
                            style=ft.ButtonStyle(color=ft.Colors.GREEN_400),
                        ))
                    if parcelas:
                        acoes.append(ft.TextButton("Parcelas", on_click=_ver_parcelas))
                    acoes.append(ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Excluir boleto",
                        on_click=_excluir_boleto,
                    ))

                    linhas.controls.append(ft.Column(spacing=2, controls=[
                        ft.Row(controls=[
                            ft.Text(b["descricao"], expand=True, size=13,
                                    weight=ft.FontWeight.W_500),
                            ft.Text(f"R$ {b['valor_total']:.2f}", size=13,
                                    color=ft.Colors.TEAL_300, width=100),
                            ft.Text(
                                f"Emissão: {_iso_br(b['data_emissao'])}",
                                size=11, color=ft.Colors.GREY_500, width=130,
                            ),
                            *acoes,
                        ]),
                        *([ ft.Text(prox_txt, size=11, color=ft.Colors.ORANGE_300) ]
                          if prox_txt else []),
                        ft.Divider(height=1),
                    ]))
            page.update()

        # ── Formulário de novo boleto ─────────────────────────────────────────
        tf_b_desc    = ft.TextField(label="Descrição *", expand=True)
        tf_b_valor   = ft.TextField(label="Valor Total (R$)", width=150,
                                    keyboard_type=ft.KeyboardType.NUMBER)
        dd_b_tipo    = ft.Dropdown(
            label="Tipo", width=160,
            options=[
                ft.dropdown.Option("AVISTA", "À Vista"),
                ft.dropdown.Option("BOLETO", "Boleto"),
                ft.dropdown.Option("PARCELADO", "Parcelado"),
            ],
            value="BOLETO",
        )
        tf_b_emissao = ft.TextField(
            label="Data Emissão", width=140,
            hint_text="DD/MM/AAAA",
            value=date.today().strftime("%d/%m/%Y"),
        )
        tf_b_parcelas = ft.TextField(
            label="Nº Parcelas", width=120,
            keyboard_type=ft.KeyboardType.NUMBER,
            value="1",
            visible=False,
        )
        tf_b_venc1   = ft.TextField(
            label="1º Vencimento", width=140,
            hint_text="DD/MM/AAAA",
            visible=True,
        )
        dd_b_metodo  = ft.Dropdown(
            label="Método", width=160,
            options=[
                ft.dropdown.Option("Dinheiro"),
                ft.dropdown.Option("PIX"),
                ft.dropdown.Option("Cartão"),
            ],
            visible=False,
        )
        tf_b_obs = ft.TextField(label="Observações", expand=True)
        txt_b_erro = ft.Text("", color=ft.Colors.RED_400, size=12)

        def _on_tipo_change(e):
            t = dd_b_tipo.value
            tf_b_parcelas.visible = (t == "PARCELADO")
            tf_b_venc1.visible    = (t in ("BOLETO", "PARCELADO"))
            dd_b_metodo.visible   = (t == "AVISTA")
            page.update()

        dd_b_tipo.on_change = _on_tipo_change

        def _salvar_boleto(e):
            desc  = tf_b_desc.value.strip()
            valor_s = tf_b_valor.value.strip().replace(",", ".")
            tipo  = dd_b_tipo.value
            emissao_iso = _br_iso(tf_b_emissao.value)

            if not desc:
                txt_b_erro.value = "Informe a descrição."
                page.update(); return
            try:
                valor = float(valor_s)
                assert valor > 0
            except Exception:
                txt_b_erro.value = "Informe um valor válido."
                page.update(); return
            if not emissao_iso:
                txt_b_erro.value = "Informe a data de emissão (DD/MM/AAAA)."
                page.update(); return

            if tipo == "AVISTA":
                id_b = database.boleto_inserir(
                    id_forn, desc, valor, 1, emissao_iso, tipo,
                    metodo_avista=dd_b_metodo.value,
                    obs=tf_b_obs.value.strip() or None,
                )
                database.boleto_inserir_parcelas(id_b, [
                    {"num_parcela": 1, "valor": valor, "vencimento": emissao_iso}
                ])
            elif tipo == "BOLETO":
                venc_iso = _br_iso(tf_b_venc1.value)
                if not venc_iso:
                    txt_b_erro.value = "Informe o vencimento."
                    page.update(); return
                id_b = database.boleto_inserir(
                    id_forn, desc, valor, 1, emissao_iso, tipo,
                    obs=tf_b_obs.value.strip() or None,
                )
                database.boleto_inserir_parcelas(id_b, [
                    {"num_parcela": 1, "valor": valor, "vencimento": venc_iso}
                ])
            else:  # PARCELADO
                try:
                    n = int(tf_b_parcelas.value)
                    assert n >= 1
                except Exception:
                    txt_b_erro.value = "Informe o número de parcelas."
                    page.update(); return
                venc_iso = _br_iso(tf_b_venc1.value)
                if not venc_iso:
                    txt_b_erro.value = "Informe o 1º vencimento."
                    page.update(); return
                val_parc = round(valor / n, 2)
                parcelas = []
                venc_dt  = date.fromisoformat(venc_iso)
                for i in range(n):
                    m_offset = i
                    y  = venc_dt.year + (venc_dt.month - 1 + m_offset) // 12
                    mo = (venc_dt.month - 1 + m_offset) % 12 + 1
                    import calendar
                    day = min(venc_dt.day, calendar.monthrange(y, mo)[1])
                    parcelas.append({
                        "num_parcela": i + 1,
                        "valor":       val_parc,
                        "vencimento":  date(y, mo, day).isoformat(),
                    })
                id_b = database.boleto_inserir(
                    id_forn, desc, valor, n, emissao_iso, tipo,
                    obs=tf_b_obs.value.strip() or None,
                )
                database.boleto_inserir_parcelas(id_b, parcelas)

            txt_b_erro.value = ""
            tf_b_desc.value = ""; tf_b_valor.value = ""
            tf_b_obs.value = ""; tf_b_venc1.value = ""
            _recarregar_dialog()

        linhas = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=300)

        form_novo = ft.Column(spacing=8, controls=[
            ft.Divider(height=1),
            ft.Text("Novo Boleto", size=13, weight=ft.FontWeight.BOLD),
            ft.Row([tf_b_desc, tf_b_valor, dd_b_tipo], spacing=8),
            ft.Row([tf_b_emissao, tf_b_venc1, tf_b_parcelas, dd_b_metodo], spacing=8),
            tf_b_obs,
            txt_b_erro,
            ft.ElevatedButton(
                "Salvar Boleto",
                icon=ft.Icons.SAVE,
                on_click=_salvar_boleto,
                style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_700,
                                     color=ft.Colors.WHITE),
            ),
        ])

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Boletos — {nome_forn}"),
            content=ft.Column(
                controls=[linhas, form_novo],
                scroll=ft.ScrollMode.AUTO,
                height=600,
                width=700,
            ),
            actions=[ft.TextButton("Fechar", on_click=lambda e: (
                setattr(dlg, "open", False), page.update()
            ))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        _recarregar_dialog()

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
            tf_vendedor,
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

    bloco_vencimentos = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Column(spacing=10, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Contas a Pagar — Vencimentos", size=15,
                            weight=ft.FontWeight.BOLD),
                    ft.Row(spacing=8, controls=[
                        dd_janela,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Atualizar vencimentos",
                            on_click=lambda e: (_carregar_vencimentos(),
                                                page.update()),
                        ),
                    ]),
                ],
            ),
            ft.Divider(height=1),
            row_aging,
            ft.Divider(height=1),
            col_vencimentos,
        ]),
    ))

    _carregar()
    _carregar_vencimentos()

    return ft.Column(
        controls=[bloco_vencimentos, bloco_form, bloco_tabela],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
