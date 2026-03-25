"""
views/parametros.py — Tela de Parâmetros com 6 abas de cadastro.
Gerencia Pessoas, Bairros, Plataformas, Métodos de Pagamento,
Categorias Extras e Configurações Gerais.
"""

import flet as ft
import database


# ── Utilitário ────────────────────────────────────────────────────────────────

def _to_float(s: str) -> float:
    try:
        return float((s or "0").replace(",", ".").strip())
    except ValueError:
        return 0.0


def _snack(page: ft.Page, msg: str, cor=ft.Colors.GREEN_700):
    page.overlay.append(ft.SnackBar(
        content=ft.Text(msg), bgcolor=cor, open=True,
    ))
    page.update()


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def view(page: ft.Page) -> ft.Control:

    # ══════════════════════════════════════════
    #  ABA 1 — PESSOAS
    # ══════════════════════════════════════════

    _pessoa_id: dict = {"v": None}

    tf_p_nome     = ft.TextField(label="Nome", expand=True)
    dd_p_tipo     = ft.Dropdown(
        label="Tipo", width=160,
        options=[ft.dropdown.Option("INTERNO"), ft.dropdown.Option("ENTREGADOR")],
    )
    tf_p_cargo    = ft.TextField(label="Cargo", expand=True)
    dd_p_tiposal  = ft.Dropdown(
        label="Tipo Salário", width=175,
        options=[
            ft.dropdown.Option("FIXO"),
            ft.dropdown.Option("DIARIO"),
            ft.dropdown.Option("ENTREGADOR"),
        ],
    )
    tf_p_salario  = ft.TextField(label="Salário Base (R$)",  keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    tf_p_diaria   = ft.TextField(label="Valor Diária (R$)",  keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    tf_p_feriado  = ft.TextField(label="Bônus Feriado (R$)", keyboard_type=ft.KeyboardType.NUMBER, width=160, value="60.00")
    tf_p_extra    = ft.TextField(label="Bônus Extra (R$)",   keyboard_type=ft.KeyboardType.NUMBER, width=160, value="50.00")
    tf_p_falta    = ft.TextField(label="Desconto Falta (R$)",keyboard_type=ft.KeyboardType.NUMBER, width=160, value="60.00")
    cb_p_ativo    = ft.Checkbox(label="Ativo", value=True)
    txt_p_erro    = ft.Text("", color=ft.Colors.RED_400, size=12)
    lbl_p_titulo  = ft.Text("Nova Pessoa", size=14, weight=ft.FontWeight.BOLD)

    linha_p_salario  = ft.Row([tf_p_salario], visible=True)
    linha_p_diaria   = ft.Row([tf_p_diaria],  visible=False)
    linha_p_holerite = ft.Row(
        controls=[tf_p_feriado, tf_p_extra, tf_p_falta],
        spacing=12, visible=True,
    )

    tabela_pessoas = ft.Column(spacing=0)

    def _on_tiposal_change(e):
        ts = dd_p_tiposal.value
        linha_p_salario.visible  = (ts == "FIXO")
        linha_p_diaria.visible   = (ts in ("DIARIO", "ENTREGADOR"))
        linha_p_holerite.visible = (ts != "ENTREGADOR")
        page.update()

    def _on_tipo_change(e):
        if dd_p_tipo.value == "ENTREGADOR":
            dd_p_tiposal.value = "ENTREGADOR"
            linha_p_salario.visible  = False
            linha_p_diaria.visible   = True
            linha_p_holerite.visible = False
        else:
            if dd_p_tiposal.value == "ENTREGADOR":
                dd_p_tiposal.value = None
                linha_p_salario.visible  = True
                linha_p_diaria.visible   = False
                linha_p_holerite.visible = True
        page.update()

    dd_p_tipo.on_select    = _on_tipo_change
    dd_p_tiposal.on_select = _on_tiposal_change

    def _refresh_pessoas():
        rows = database.pessoa_listar(apenas_ativos=False)
        linhas = []
        for p in rows:
            ts = p["tipo_salario"] or ""
            if ts == "DIARIO":
                sal_txt = f"R$ {p['diaria_valor']:.2f}/dia"
            elif ts == "ENTREGADOR":
                sal_txt = f"Diária R$ {p['diaria_valor']:.2f}"
            else:
                sal_txt = f"R$ {p['salario_base']:.2f}"

            status_cor = ft.Colors.GREEN_400 if p["status_ativo"] else ft.Colors.GREY_500
            status_txt = "Ativo" if p["status_ativo"] else "Inativo"

            def _on_editar_pessoa(pid):
                def handler(e):
                    r = database.pessoa_buscar(pid)
                    if not r:
                        return
                    _pessoa_id["v"]      = pid
                    lbl_p_titulo.value   = f"Editando: {r['nome']}"
                    tf_p_nome.value      = r["nome"]
                    dd_p_tipo.value      = r["tipo"]
                    tf_p_cargo.value     = r["cargo"] or ""
                    dd_p_tiposal.value   = r["tipo_salario"]
                    tf_p_salario.value   = f"{r['salario_base']:.2f}"
                    tf_p_diaria.value    = f"{r['diaria_valor']:.2f}"
                    cb_p_ativo.value     = bool(r["status_ativo"])
                    try:
                        tf_p_feriado.value = f"{r['valor_feriado']:.2f}"
                        tf_p_extra.value   = f"{r['valor_extra']:.2f}"
                        tf_p_falta.value   = f"{r['valor_falta']:.2f}"
                    except (IndexError, KeyError):
                        tf_p_feriado.value = "60.00"
                        tf_p_extra.value   = "50.00"
                        tf_p_falta.value   = "60.00"
                    ts = r["tipo_salario"] or ""
                    linha_p_salario.visible  = (ts == "FIXO")
                    linha_p_diaria.visible   = (ts in ("DIARIO", "ENTREGADOR"))
                    linha_p_holerite.visible = (ts != "ENTREGADOR")
                    txt_p_erro.value = ""
                    page.update()
                return handler

            def _on_toggle_pessoa(pid, ativo_atual):
                def handler(e):
                    database.pessoa_atualizar(pid, status_ativo=0 if ativo_atual else 1)
                    _refresh_pessoas()
                    page.update()
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(p["nome"])),
                ft.DataCell(ft.Text(p["tipo"])),
                ft.DataCell(ft.Text(p["cargo"] or "—")),
                ft.DataCell(ft.Text(sal_txt)),
                ft.DataCell(ft.Text(status_txt, color=status_cor)),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.TextButton("Editar",
                                  on_click=_on_editar_pessoa(p["id"])),
                    ft.TextButton(
                        "Inativar" if p["status_ativo"] else "Reativar",
                        on_click=_on_toggle_pessoa(p["id"], p["status_ativo"]),
                        style=ft.ButtonStyle(
                            color=ft.Colors.RED_400 if p["status_ativo"] else ft.Colors.GREEN_400,
                        ),
                    ),
                ])),
            ]))

        tabela_pessoas.controls.clear()
        if not linhas:
            tabela_pessoas.controls.append(
                ft.Text("Nenhuma pessoa cadastrada.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_pessoas.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Nome")),
                            ft.DataColumn(ft.Text("Tipo")),
                            ft.DataColumn(ft.Text("Cargo")),
                            ft.DataColumn(ft.Text("Salário")),
                            ft.DataColumn(ft.Text("Status")),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _limpar_pessoa():
        _pessoa_id["v"]          = None
        lbl_p_titulo.value       = "Nova Pessoa"
        tf_p_nome.value          = ""
        dd_p_tipo.value          = None
        tf_p_cargo.value         = ""
        dd_p_tiposal.value       = None
        tf_p_salario.value       = ""
        tf_p_diaria.value        = ""
        tf_p_feriado.value       = "60.00"
        tf_p_extra.value         = "50.00"
        tf_p_falta.value         = "60.00"
        cb_p_ativo.value         = True
        linha_p_salario.visible  = True
        linha_p_diaria.visible   = False
        linha_p_holerite.visible = True
        txt_p_erro.value         = ""

    def _salvar_pessoa(e):
        txt_p_erro.value = ""
        nome = tf_p_nome.value.strip()
        if not nome:
            txt_p_erro.value = "Nome é obrigatório."
            page.update()
            return
        if not dd_p_tipo.value:
            txt_p_erro.value = "Selecione o tipo (INTERNO ou ENTREGADOR)."
            page.update()
            return

        ts      = dd_p_tiposal.value
        salario = _to_float(tf_p_salario.value) if ts == "FIXO"             else 0.0
        diaria  = _to_float(tf_p_diaria.value)  if ts in ("DIARIO","ENTREGADOR") else 0.0

        kwargs_hol = {}
        if ts != "ENTREGADOR":
            kwargs_hol = dict(
                valor_feriado=_to_float(tf_p_feriado.value),
                valor_extra=  _to_float(tf_p_extra.value),
                valor_falta=  _to_float(tf_p_falta.value),
            )

        if _pessoa_id["v"] is None:
            pid = database.pessoa_inserir(
                nome=nome,
                tipo=dd_p_tipo.value,
                cargo=tf_p_cargo.value.strip() or None,
                salario_base=salario,
                tipo_salario=ts,
                diaria_valor=diaria,
                status_ativo=cb_p_ativo.value,
            )
            if kwargs_hol:
                database.pessoa_atualizar(pid, **kwargs_hol)
        else:
            database.pessoa_atualizar(
                _pessoa_id["v"],
                nome=nome,
                tipo=dd_p_tipo.value,
                cargo=tf_p_cargo.value.strip() or None,
                salario_base=salario,
                tipo_salario=ts,
                diaria_valor=diaria,
                status_ativo=int(cb_p_ativo.value),
                **kwargs_hol,
            )

        _limpar_pessoa()
        _refresh_pessoas()
        page.update()

    def _cancelar_pessoa(e):
        _limpar_pessoa()
        page.update()

    _refresh_pessoas()

    tab_pessoas = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    lbl_p_titulo,
                    ft.Row([tf_p_nome, dd_p_tipo], spacing=12),
                    ft.Row([tf_p_cargo, dd_p_tiposal], spacing=12),
                    linha_p_salario,
                    linha_p_diaria,
                    linha_p_holerite,
                    cb_p_ativo,
                    txt_p_erro,
                    ft.Row([
                        ft.ElevatedButton("Salvar",   icon=ft.Icons.SAVE,  on_click=_salvar_pessoa),
                        ft.TextButton("Cancelar", on_click=_cancelar_pessoa),
                    ]),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Pessoas Cadastradas", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_pessoas,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 2 — BAIRROS
    # ══════════════════════════════════════════

    _bairro_id: dict = {"v": None}

    tf_b_nome    = ft.TextField(label="Nome do Bairro",          expand=True)
    tf_b_taxa    = ft.TextField(label="Taxa Cobrada (R$)",        keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    tf_b_repasse = ft.TextField(label="Repasse Entregador (R$)",  keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    txt_b_erro   = ft.Text("", color=ft.Colors.RED_400, size=12)
    lbl_b_titulo = ft.Text("Novo Bairro", size=14, weight=ft.FontWeight.BOLD)

    tabela_bairros = ft.Column(spacing=0)

    def _refresh_bairros():
        rows = database.bairro_listar()
        linhas = []
        for b in rows:
            def _on_editar_bairro(bid):
                def handler(e):
                    r = database.bairro_buscar(bid)
                    if not r:
                        return
                    _bairro_id["v"]    = bid
                    lbl_b_titulo.value = f"Editando: {r['nome_bairro']}"
                    tf_b_nome.value    = r["nome_bairro"]
                    tf_b_taxa.value    = f"{r['taxa_cobrada']:.2f}"
                    tf_b_repasse.value = f"{r['repasse_entregador']:.2f}"
                    txt_b_erro.value   = ""
                    page.update()
                return handler

            def _on_excluir_bairro(bid):
                def handler(e):
                    database.bairro_excluir(bid)
                    _refresh_bairros()
                    page.update()
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(b["nome_bairro"])),
                ft.DataCell(ft.Text(f"R$ {b['taxa_cobrada']:.2f}")),
                ft.DataCell(ft.Text(f"R$ {b['repasse_entregador']:.2f}")),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.TextButton("Editar", on_click=_on_editar_bairro(b["id"])),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Excluir bairro",
                        on_click=_on_excluir_bairro(b["id"]),
                    ),
                ])),
            ]))

        tabela_bairros.controls.clear()
        if not linhas:
            tabela_bairros.controls.append(
                ft.Text("Nenhum bairro cadastrado.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_bairros.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Bairro")),
                            ft.DataColumn(ft.Text("Taxa Cobrada"),       numeric=True),
                            ft.DataColumn(ft.Text("Repasse Entregador"), numeric=True),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _limpar_bairro():
        _bairro_id["v"]    = None
        lbl_b_titulo.value = "Novo Bairro"
        tf_b_nome.value    = ""
        tf_b_taxa.value    = ""
        tf_b_repasse.value = ""
        txt_b_erro.value   = ""

    def _salvar_bairro(e):
        txt_b_erro.value = ""
        nome = tf_b_nome.value.strip()
        if not nome:
            txt_b_erro.value = "Nome do bairro é obrigatório."
            page.update()
            return
        taxa    = _to_float(tf_b_taxa.value)
        repasse = _to_float(tf_b_repasse.value)
        if _bairro_id["v"] is None:
            database.bairro_inserir(nome, taxa, repasse)
        else:
            database.bairro_atualizar(
                _bairro_id["v"],
                nome_bairro=nome,
                taxa_cobrada=taxa,
                repasse_entregador=repasse,
            )
        _limpar_bairro()
        _refresh_bairros()
        page.update()

    def _cancelar_bairro(e):
        _limpar_bairro()
        page.update()

    _refresh_bairros()

    tab_bairros = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    lbl_b_titulo,
                    tf_b_nome,
                    ft.Row([tf_b_taxa, tf_b_repasse], spacing=12),
                    txt_b_erro,
                    ft.Row([
                        ft.ElevatedButton("Salvar",   icon=ft.Icons.SAVE, on_click=_salvar_bairro),
                        ft.TextButton("Cancelar", on_click=_cancelar_bairro),
                    ]),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Bairros Cadastrados", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_bairros,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 3 — PLATAFORMAS
    # ══════════════════════════════════════════

    _DIAS_REPASSE = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]

    def _card_plataforma(plat: dict) -> ft.Card:
        pid  = plat["id"]
        nome = plat["nome"]

        tf_pl_comissao = ft.TextField(
            label="Comissão (%)",
            value=f"{plat['comissao_pct']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        tf_pl_taxa_tr = ft.TextField(
            label="Taxa Transação (%)",
            value=f"{plat['taxa_transacao_pct']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        tf_pl_subsidio = ft.TextField(
            label="Subsídio (R$)",
            value=f"{plat['subsidio']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        dd_pl_dia = ft.Dropdown(
            label="Dia de Repasse",
            value=plat["dia_repasse"] or None,
            options=[ft.dropdown.Option(d) for d in _DIAS_REPASSE],
            expand=True,
        )
        sw_pl_ativo = ft.Switch(label="Ativo", value=bool(plat["ativo"]))
        txt_pl_ok   = ft.Text("", color=ft.Colors.GREEN_400, size=12)

        def _salvar_plat(e):
            database.plataforma_atualizar(
                pid,
                comissao_pct=      _to_float(tf_pl_comissao.value),
                taxa_transacao_pct=_to_float(tf_pl_taxa_tr.value),
                subsidio=          _to_float(tf_pl_subsidio.value),
                dia_repasse=       dd_pl_dia.value,
                ativo=             int(sw_pl_ativo.value),
            )
            txt_pl_ok.value = "Salvo!"
            page.update()

        return ft.Card(content=ft.Container(
            padding=ft.Padding.all(16),
            content=ft.Column(spacing=12, controls=[
                ft.Row([
                    ft.Text(nome, size=15, weight=ft.FontWeight.BOLD, expand=True),
                    sw_pl_ativo,
                ]),
                ft.Row([tf_pl_comissao, tf_pl_taxa_tr, tf_pl_subsidio], spacing=12),
                dd_pl_dia,
                ft.Row([
                    ft.ElevatedButton("Salvar", icon=ft.Icons.SAVE, on_click=_salvar_plat),
                    txt_pl_ok,
                ]),
            ]),
        ))

    plataformas_db = database.plataforma_listar(apenas_ativas=False)

    tab_plataformas = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[_card_plataforma(dict(p)) for p in plataformas_db],
    )

    # ══════════════════════════════════════════
    #  ABA 4 — MÉTODOS DE PAGAMENTO
    # ══════════════════════════════════════════

    tf_m_nome  = ft.TextField(label="Nome", expand=True)
    dd_m_tipo  = ft.Dropdown(
        label="Tipo", width=200,
        options=[
            ft.dropdown.Option("FISICO"),
            ft.dropdown.Option("PLATAFORMA"),
            ft.dropdown.Option("BENEFICIO"),
            ft.dropdown.Option("CORTESIA"),
        ],
    )
    txt_m_erro = ft.Text("", color=ft.Colors.RED_400, size=12)

    tabela_metodos = ft.Column(spacing=0)

    def _refresh_metodos():
        rows = database.metodo_pag_listar()
        linhas = []
        for m in rows:
            def _on_excluir_metodo(mid):
                def handler(e):
                    database.metodo_pag_excluir(mid)
                    _refresh_metodos()
                    page.update()
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(m["nome"])),
                ft.DataCell(ft.Text(m["tipo"])),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Excluir método",
                    on_click=_on_excluir_metodo(m["id"]),
                )),
            ]))

        tabela_metodos.controls.clear()
        if not linhas:
            tabela_metodos.controls.append(
                ft.Text("Nenhum método cadastrado.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_metodos.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Nome")),
                            ft.DataColumn(ft.Text("Tipo")),
                            ft.DataColumn(ft.Text("")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _salvar_metodo(e):
        txt_m_erro.value = ""
        nome = tf_m_nome.value.strip()
        if not nome:
            txt_m_erro.value = "Nome é obrigatório."
            page.update()
            return
        if not dd_m_tipo.value:
            txt_m_erro.value = "Selecione o tipo."
            page.update()
            return
        database.metodo_pag_inserir(nome, dd_m_tipo.value)
        tf_m_nome.value = ""
        dd_m_tipo.value = None
        _refresh_metodos()
        page.update()

    _refresh_metodos()

    tab_metodos = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    ft.Text("Adicionar Método de Pagamento", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([tf_m_nome, dd_m_tipo], spacing=12),
                    txt_m_erro,
                    ft.ElevatedButton("Adicionar", icon=ft.Icons.ADD, on_click=_salvar_metodo),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Métodos Cadastrados", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_metodos,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 5 — CATEGORIAS EXTRAS
    # ══════════════════════════════════════════

    tf_cat_desc   = ft.TextField(label="Descrição", expand=True)
    dd_cat_fluxo  = ft.Dropdown(
        label="Fluxo", width=160,
        options=[ft.dropdown.Option("ENTRADA"), ft.dropdown.Option("SAIDA")],
    )
    cb_cat_func   = ft.Checkbox(label="Usa Funcionário", value=False)
    txt_cat_erro  = ft.Text("", color=ft.Colors.RED_400, size=12)

    tabela_cats = ft.Column(spacing=0)

    def _refresh_cats():
        rows = database.categoria_extra_listar()
        linhas = []
        for c in rows:
            cor_fluxo = ft.Colors.GREEN_400 if c["fluxo"] == "ENTRADA" else ft.Colors.RED_400

            def _on_excluir_cat(cid):
                def handler(e):
                    database.categoria_extra_excluir(cid)
                    _refresh_cats()
                    page.update()
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["descricao"])),
                ft.DataCell(ft.Text(c["fluxo"], color=cor_fluxo)),
                ft.DataCell(ft.Text("Sim" if c["usa_funcionario"] else "Não")),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Excluir categoria",
                    on_click=_on_excluir_cat(c["id"]),
                )),
            ]))

        tabela_cats.controls.clear()
        if not linhas:
            tabela_cats.controls.append(
                ft.Text("Nenhuma categoria cadastrada.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_cats.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Descrição")),
                            ft.DataColumn(ft.Text("Fluxo")),
                            ft.DataColumn(ft.Text("Usa Func.")),
                            ft.DataColumn(ft.Text("")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _salvar_cat(e):
        txt_cat_erro.value = ""
        desc = tf_cat_desc.value.strip()
        if not desc:
            txt_cat_erro.value = "Descrição é obrigatória."
            page.update()
            return
        if not dd_cat_fluxo.value:
            txt_cat_erro.value = "Selecione o fluxo."
            page.update()
            return
        database.categoria_extra_inserir(desc, dd_cat_fluxo.value, cb_cat_func.value)
        tf_cat_desc.value  = ""
        dd_cat_fluxo.value = None
        cb_cat_func.value  = False
        _refresh_cats()
        page.update()

    _refresh_cats()

    tab_categorias = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    ft.Text("Adicionar Categoria Extra", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([tf_cat_desc, dd_cat_fluxo], spacing=12),
                    cb_cat_func,
                    txt_cat_erro,
                    ft.ElevatedButton("Adicionar", icon=ft.Icons.ADD, on_click=_salvar_cat),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Categorias Cadastradas", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_cats,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 6 — CONFIGURAÇÕES GERAIS
    # ══════════════════════════════════════════

    tf_cfg_loja   = ft.TextField(
        label="Nome da Loja",
        value=database.config_obter("nome_loja", "Minha Loja"),
        expand=True,
    )
    tf_cfg_diaria = ft.TextField(
        label="Diária Padrão Entregadores (R$)",
        value=database.config_obter("diaria_padrao_entregador", "40.00"),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=260,
        hint_text="Padrão ao cadastrar novo entregador",
    )
    txt_cfg_ok = ft.Text("", color=ft.Colors.GREEN_400, size=13)

    def _salvar_cfg(e):
        nome_loja = tf_cfg_loja.value.strip()
        diaria    = tf_cfg_diaria.value.strip() or "40.00"
        if nome_loja:
            database.config_salvar("nome_loja", nome_loja)
        database.config_salvar("diaria_padrao_entregador", diaria)
        txt_cfg_ok.value = "Configurações salvas!"
        page.update()

    tab_config = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=16, controls=[
                    ft.Text("Configurações Gerais", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row([tf_cfg_loja], spacing=12),
                    ft.Row([tf_cfg_diaria], spacing=12),
                    ft.Text(
                        "A diária padrão é usada como valor inicial ao cadastrar novos entregadores.",
                        size=12, color=ft.Colors.GREY_500, italic=True,
                    ),
                    txt_cfg_ok,
                    ft.ElevatedButton(
                        "Salvar Configurações",
                        icon=ft.Icons.SAVE,
                        on_click=_salvar_cfg,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE,
                        ),
                    ),
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  TABS
    # ══════════════════════════════════════════

    def _wrap(content: ft.Control) -> ft.Container:
        return ft.Container(content=content, padding=ft.Padding.all(16))

    tab_bar = ft.TabBar(
        scrollable=True,
        tabs=[
            ft.Tab(label="Pessoas",       icon=ft.Icons.PEOPLE),
            ft.Tab(label="Bairros",        icon=ft.Icons.MAP),
            ft.Tab(label="Plataformas",    icon=ft.Icons.STORE),
            ft.Tab(label="Pagamentos",     icon=ft.Icons.PAYMENT),
            ft.Tab(label="Categorias",     icon=ft.Icons.CATEGORY),
            ft.Tab(label="Configurações",  icon=ft.Icons.SETTINGS),
        ],
    )

    tab_view = ft.TabBarView(
        controls=[
            _wrap(tab_pessoas),
            _wrap(tab_bairros),
            _wrap(tab_plataformas),
            _wrap(tab_metodos),
            _wrap(tab_categorias),
            _wrap(tab_config),
        ],
        expand=True,
    )

    return ft.Tabs(
        content=ft.Column([tab_bar, tab_view], expand=True),
        length=6,
        selected_index=0,
        expand=True,
    )
