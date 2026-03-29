"""
views/pdv.py — Tela de PDV: lançamento e listagem de pedidos do dia.
"""

import flet as ft
from datetime import date, datetime

import database


# ── Utilitários ───────────────────────────────────────────────────────────────

def _to_float(valor: str) -> float:
    try:
        return float((valor or "0").replace(",", ".").strip())
    except ValueError:
        return 0.0


def _data_br_para_iso(data_br: str) -> str:
    try:
        d, m, a = data_br.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


# ── Mapa de nomes amigáveis para canais ───────────────────────────────────────

CANAL_NOMES = {
    "Mesa":                    "Mesa",
    "Retirada_PDV":            "Retirada (loja)",
    "Delivery_PDV":            "Delivery (nosso motoboy)",
    "iFood1_Delivery":         "iFood L1 - Entrega",
    "iFood1_Delivery_Deles":   "iFood L1 - Entregador deles",
    "iFood1_Retirada":         "iFood L1 - Retirada",
    "iFood2_Delivery":         "iFood L2 - Entrega",
    "iFood2_Delivery_Deles":   "iFood L2 - Entregador deles",
    "iFood2_Retirada":         "iFood L2 - Retirada",
    "99Food_Delivery":         "99Food - Entrega",
    "99Food_Delivery_Deles":   "99Food - Entregador deles",
    "99Food_Retirada":         "99Food - Retirada",
    "Keeta_Delivery":          "Keeta - Entrega",
    "Keeta_Delivery_Deles":    "Keeta - Entregador deles",
    "Keeta_Retirada":          "Keeta - Retirada",
}


# ── View principal ────────────────────────────────────────────────────────────

def _fechar(e, dlg, page):
    dlg.open = False
    page.update()


def _confirmar_exclusao(page, descricao: str, on_confirmar) -> None:
    """Abre um AlertDialog pedindo confirmação antes de excluir."""
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


def view(page: ft.Page) -> ft.Control:
    hoje_br = date.today().strftime("%d/%m/%Y")

    # ── Dados de referência ───────────────────────────────────────────────
    canais_db  = database.canal_listar()
    metodos_db = database.metodo_pag_listar()
    _nomes_fisicos = {
        r["nome"] for r in metodos_db
        if r["tipo"] in ("FISICO", "BENEFICIO", "CORTESIA")
    }
    _opts_metodos_fisicos = [
        ft.dropdown.Option(r["nome"])
        for r in metodos_db
        if r["tipo"] in ("FISICO", "BENEFICIO", "CORTESIA")
    ]
    _opts_metodos_todos = [ft.dropdown.Option(r["nome"]) for r in metodos_db]
    pessoas_db = database.pessoa_listar(apenas_ativos=True)
    bairros_db = database.bairro_listar()

    canal_info      = {r["nome"]: dict(r) for r in canais_db}
    bairro_map      = {r["id"]:   dict(r) for r in bairros_db}
    pessoa_map      = {r["id"]:   r["nome"] for r in pessoas_db}
    bairro_nome_map = {r["id"]:   r["nome_bairro"] for r in bairros_db}

    # ── Linha 1: Data + Canal ─────────────────────────────────────────────
    tf_data = ft.TextField(
        label="Data",
        value=hoje_br,
        width=140,
        text_align=ft.TextAlign.CENTER,
        hint_text="DD/MM/AAAA",
    )

    def _on_date_picked(e):
        if e.control.value:
            tf_data.value = e.control.value.strftime("%d/%m/%Y")
            _atualizar_tabela()
            page.update()

    date_picker = ft.DatePicker(on_change=_on_date_picked)
    page.overlay.append(date_picker)

    def _abrir_calendario(e):
        date_picker.open = True
        page.update()

    btn_calendario = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar data",
        on_click=_abrir_calendario,
    )

    dd_canal = ft.Dropdown(
        label="Canal de Venda",
        options=[
            ft.dropdown.Option(key=r["nome"], text=CANAL_NOMES.get(r["nome"], r["nome"]))
            for r in canais_db
        ],
        expand=True,
    )

    # ── Linha 2: Valor total ──────────────────────────────────────────────
    tf_valor = ft.TextField(
        label="Valor Total (R$)",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    # ── Linha 3: Pagamentos dinâmicos ─────────────────────────────────────
    # _pag_itens: lista de (dd_metodo, tf_valor_pag, ft.Row)
    _pag_itens = []
    col_pag    = ft.Column(spacing=6)

    def _nova_linha_pag():
        eh_plataforma = bool(canal_info.get(dd_canal.value or "", {}).get("tem_comissao", 0))
        dd_m = ft.Dropdown(
            label="Método",
            options=_opts_metodos_todos if eh_plataforma else _opts_metodos_fisicos,
            expand=2,
        )
        tf_v = ft.TextField(
            label="Valor (R$)",
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=1,
        )
        btn_x = ft.IconButton(
            icon=ft.Icons.CLOSE,
            icon_color=ft.Colors.RED_400,
            tooltip="Remover",
        )
        row  = ft.Row([dd_m, tf_v, btn_x], spacing=8)
        item = (dd_m, tf_v, row)
        _pag_itens.append(item)
        col_pag.controls.append(row)

        def _remover(e, _item=item, _row=row):
            if len(_pag_itens) <= 1:
                return
            _pag_itens.remove(_item)
            col_pag.controls.remove(_row)
            page.update()

        btn_x.on_click = _remover

    _nova_linha_pag()   # começa com uma linha aberta

    btn_add_pag = ft.TextButton(
        "Pagamento",
        icon=ft.Icons.ADD,
        on_click=lambda e: (_nova_linha_pag(), page.update()),
    )

    def _on_valor_blur(e):
        if len(_pag_itens) == 1 and (tf_valor.value or "").strip():
            _, tf_v, _ = _pag_itens[0]
            tf_v.value = tf_valor.value
            page.update()

    tf_valor.on_blur = _on_valor_blur

    # ── Linha 4: Operador ─────────────────────────────────────────────────
    dd_operador = ft.Dropdown(
        label="Operador",
        options=[
            ft.dropdown.Option(key=str(r["id"]), text=r["nome"])
            for r in pessoas_db
        ],
        expand=True,
    )

    # ── Linha 5: Bairro (condicional) ─────────────────────────────────────
    dd_bairro = ft.Dropdown(
        label="Bairro *",
        options=[
            ft.dropdown.Option(key=str(r["id"]), text=r["nome_bairro"])
            for r in bairros_db
        ],
        expand=True,
    )

    # ── Linha 6: Taxas (condicionais) ─────────────────────────────────────
    tf_taxa = ft.TextField(
        label="Taxa Entrega (R$)",
        value="0.00",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    tf_repasse = ft.TextField(
        label="Repasse Entregador (R$)",
        value="0.00",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    linha_bairro = ft.Row([dd_bairro], visible=False)
    linha_taxas  = ft.Row([tf_taxa, tf_repasse], spacing=12, visible=False)

    # ── Linha 7: Obs ──────────────────────────────────────────────────────
    tf_obs = ft.TextField(
        label="Observações",
        multiline=True,
        min_lines=2,
        max_lines=3,
        expand=True,
    )

    txt_erro = ft.Text("", color=ft.Colors.RED_400, size=13)

    _editando  = {"id": None}
    txt_titulo = ft.Text("Novo Pedido", size=18, weight=ft.FontWeight.BOLD)

    # ── Tabela de pedidos do dia ──────────────────────────────────────────
    col_tabela    = ft.Column(spacing=0, expand=True)
    _todos_pedidos: list = []

    tf_filtro = ft.TextField(
        label="Buscar pedido...",
        hint_text="Canal, operador, valor ou método",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
    )
    btn_limpar_filtro = ft.IconButton(
        ft.Icons.CLEAR,
        tooltip="Limpar filtro",
    )

    def _filtrar(termo: str):
        col_tabela.controls.clear()
        filtradas = (
            [r for r in _todos_pedidos if termo.lower() in (r.data or "")]
            if termo
            else _todos_pedidos
        )
        if not filtradas:
            msg = (
                f"Nenhum pedido encontrado para '{termo}'."
                if termo
                else "Nenhum pedido registrado nesta data."
            )
            col_tabela.controls.append(
                ft.Text(msg, italic=True, color=ft.Colors.GREY_500)
            )
        else:
            col_tabela.controls.append(
                ft.Row(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(ft.Text("Hora")),
                                ft.DataColumn(ft.Text("Canal")),
                                ft.DataColumn(ft.Text("Valor"), numeric=True),
                                ft.DataColumn(ft.Text("Pagamentos")),
                                ft.DataColumn(ft.Text("Operador")),
                                ft.DataColumn(ft.Text("Bairro")),
                                ft.DataColumn(ft.Text("Taxa"), numeric=True),
                                ft.DataColumn(ft.Text("Obs")),
                                ft.DataColumn(ft.Text("")),
                            ],
                            rows=filtradas,
                            column_spacing=14,
                            horizontal_lines=ft.BorderSide(
                                1, ft.Colors.with_opacity(0.15, ft.Colors.BLACK)
                            ),
                        )
                    ],
                )
            )

    def _on_filtro_change(e):
        _filtrar(tf_filtro.value or "")
        page.update()

    def _limpar_filtro(e):
        tf_filtro.value = ""
        _filtrar("")
        page.update()

    tf_filtro.on_change         = _on_filtro_change
    btn_limpar_filtro.on_click  = _limpar_filtro

    def _atualizar_tabela():
        data_iso = _data_br_para_iso(tf_data.value or hoje_br)
        pedidos  = database.pedido_listar_por_data(data_iso)

        def _on_excluir(id_pedido, canal_p, valor_p, data_p):
            def handler(e):
                def _excluir():
                    database.pedido_excluir(id_pedido)
                    database.log_registrar(
                        acao="EXCLUIR_PEDIDO",
                        tabela="vendas_pedidos",
                        id_registro=id_pedido,
                        descricao=f"Pedido #{id_pedido} excluído — "
                                  f"Canal: {canal_p} | Valor: R$ {valor_p:.2f} | "
                                  f"Data: {data_p}",
                        valor_antes=f"canal={canal_p}, valor={valor_p}, data={data_p}",
                    )
                    _atualizar_tabela()
                    page.update()
                _confirmar_exclusao(page, "este pedido", _excluir)
            return handler

        def _on_editar(id_pedido):
            return _iniciar_edicao(id_pedido)

        linhas = []
        for p in pedidos:
            pags    = database.pagamento_buscar_por_pedido(p["id"])
            pag_txt = " | ".join(
                f"{pg['metodo']} R${pg['valor']:.2f}" for pg in pags
            ) or "—"
            nome_op  = pessoa_map.get(p["id_operador"], "—")
            bairro_n = bairro_nome_map.get(p["id_bairro"], "—") if p["id_bairro"] else "—"

            canal_amigavel = CANAL_NOMES.get(p["canal"], p["canal"])
            em_edicao = _editando["id"] == p["id"]
            busca_data = (
                f"{canal_amigavel} {nome_op} {bairro_n} "
                f"{p['valor_total']:.2f} {pag_txt}"
            ).lower()
            linhas.append(ft.DataRow(
                data=busca_data,
                color=ft.Colors.with_opacity(0.08, ft.Colors.BLUE) if em_edicao else None,
                cells=[
                    ft.DataCell(ft.Text(p["hora"] or "—")),
                    ft.DataCell(ft.Text(canal_amigavel)),
                    ft.DataCell(ft.Text(f"R$ {p['valor_total']:.2f}")),
                    ft.DataCell(ft.Text(pag_txt)),
                    ft.DataCell(ft.Text(nome_op)),
                    ft.DataCell(ft.Text(bairro_n)),
                    ft.DataCell(ft.Text(
                        f"R$ {p['taxa_entrega']:.2f}" if p["taxa_entrega"] else "—"
                    )),
                    ft.DataCell(ft.Text(p["obs"] or "")),
                    ft.DataCell(ft.Row(spacing=0, controls=[
                        ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED,
                            icon_color=ft.Colors.BLUE_300,
                            tooltip="Editar pedido",
                            on_click=_on_editar(p["id"]),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_400,
                            tooltip="Excluir pedido",
                            on_click=_on_excluir(p["id"], p["canal"], p["valor_total"], p["data"]),
                        ),
                    ])),
                ],
            ))

        _todos_pedidos.clear()
        _todos_pedidos.extend(linhas)
        _filtrar(tf_filtro.value or "")

    # ── Lógica dinâmica ───────────────────────────────────────────────────

    def _atualizar_opts_metodos(eh_plataforma: bool):
        opts = _opts_metodos_todos if eh_plataforma else _opts_metodos_fisicos
        for dd_m, _, _ in _pag_itens:
            dd_m.options = opts
            if not eh_plataforma and dd_m.value and dd_m.value not in _nomes_fisicos:
                dd_m.value = None

    def _on_canal_change(e):
        nome  = dd_canal.value or ""
        info  = canal_info.get(nome, {})
        requer_bairro = bool(info.get("requer_bairro", 0))
        eh_deles      = bool(info.get("entregador_plataforma", 0))
        eh_plataforma = bool(info.get("tem_comissao", 0))

        linha_bairro.visible = requer_bairro
        # _Deles: entregador é da plataforma — taxa e repasse sempre zero, campos ocultos
        linha_taxas.visible  = requer_bairro and not eh_deles

        if not requer_bairro or eh_deles:
            tf_taxa.value    = "0.00"
            tf_repasse.value = "0.00"
        if not requer_bairro:
            dd_bairro.value  = None

        _atualizar_opts_metodos(eh_plataforma)
        txt_erro.value = ""
        page.update()

    def _on_bairro_change(e):
        if not dd_bairro.value:
            return
        bairro = bairro_map.get(int(dd_bairro.value), {})
        tf_taxa.value    = f"{bairro.get('taxa_cobrada', 0):.2f}"
        tf_repasse.value = f"{bairro.get('repasse_entregador', 0):.2f}"
        page.update()

    def _on_data_change(e):
        _atualizar_tabela()
        page.update()

    dd_canal.on_select  = _on_canal_change
    dd_bairro.on_select = _on_bairro_change
    tf_data.on_submit   = _on_data_change
    tf_data.on_blur     = _on_data_change

    # ── Limpar formulário ─────────────────────────────────────────────────

    def _limpar():
        data_atual           = tf_data.value
        dd_canal.value       = None
        tf_valor.value       = ""
        dd_operador.value    = None
        dd_bairro.value      = None
        page.update()  # força limpeza visual do dropdown antes de ocultar a linha
        tf_taxa.value        = "0.00"
        tf_repasse.value     = "0.00"
        tf_obs.value         = ""
        linha_bairro.visible = False
        linha_taxas.visible  = False
        tf_repasse.visible   = True
        txt_erro.value       = ""

        # Mantém só a primeira linha de pagamento e limpa seus valores
        while len(_pag_itens) > 1:
            _, _, row = _pag_itens.pop()
            col_pag.controls.remove(row)
        if _pag_itens:
            dd_m, tf_v, _ = _pag_itens[0]
            dd_m.value = None
            tf_v.value = ""

        tf_data.value = data_atual  # mantém a data selecionada

        _editando["id"]      = None
        txt_titulo.value     = "Novo Pedido"
        txt_titulo.color     = None
        btn_cancelar.visible = False

    # ── Iniciar edição de pedido existente ────────────────────────────────

    def _iniciar_edicao(pid):
        def handler(e):
            p = database.pedido_buscar(pid)
            if not p:
                return

            # Data
            try:
                a, m, d = p["data"].split("-")
                tf_data.value = f"{d}/{m}/{a}"
            except Exception:
                tf_data.value = hoje_br

            dd_canal.value    = p["canal"]
            tf_valor.value    = f"{p['valor_total']:.2f}"
            dd_operador.value = str(p["id_operador"]) if p["id_operador"] else None
            tf_obs.value      = p["obs"] or ""

            # Bairro
            if p["id_bairro"]:
                dd_bairro.value      = str(p["id_bairro"])
                linha_bairro.visible = True
            else:
                dd_bairro.value      = None
                linha_bairro.visible = False

            # Taxas
            taxa    = p["taxa_entrega"]        or 0.0
            repasse = p["repasse_entregador"]  or 0.0
            tf_taxa.value    = f"{taxa:.2f}"
            tf_repasse.value = f"{repasse:.2f}"
            info     = canal_info.get(p["canal"], {})
            eh_deles = bool(info.get("entregador_plataforma", 0))
            linha_taxas.visible = bool(p["id_bairro"]) and not eh_deles

            # Pagamentos: reduzir para uma linha e repopular
            while len(_pag_itens) > 1:
                _, _, row = _pag_itens.pop()
                col_pag.controls.remove(row)
            pags = database.pagamento_buscar_por_pedido(pid)
            if pags:
                dd_m0, tf_v0, _ = _pag_itens[0]
                dd_m0.value = pags[0]["metodo"]
                tf_v0.value = f"{pags[0]['valor']:.2f}"
                for pg in pags[1:]:
                    _nova_linha_pag()
                    dd_m, tf_v, _ = _pag_itens[-1]
                    dd_m.value = pg["metodo"]
                    tf_v.value = f"{pg['valor']:.2f}"
            else:
                dd_m0, tf_v0, _ = _pag_itens[0]
                dd_m0.value = None
                tf_v0.value = ""

            _editando["id"]      = pid
            txt_titulo.value     = f"Editando Pedido #{pid}"
            txt_titulo.color     = ft.Colors.ORANGE_400
            btn_cancelar.visible = True
            txt_erro.value       = ""

            page.scroll_to(offset=0)
            page.update()
        return handler

    # ── Salvar ────────────────────────────────────────────────────────────

    def _salvar(e):
        txt_erro.value = ""

        canal = dd_canal.value
        if not canal:
            txt_erro.value = "Selecione o canal de venda."
            page.update()
            return

        valor = _to_float(tf_valor.value)
        if valor <= 0:
            txt_erro.value = "Informe o valor total do pedido."
            page.update()
            return

        # Coleta pagamentos preenchidos
        pags_validos = [
            (dd_m.value, _to_float(tf_v.value))
            for dd_m, tf_v, _ in _pag_itens
            if dd_m.value
        ]
        if not pags_validos:
            txt_erro.value = "Informe ao menos um pagamento com método selecionado."
            page.update()
            return

        if not dd_operador.value:
            txt_erro.value = "Selecione o operador."
            page.update()
            return

        info      = canal_info.get(canal, {})
        requer_b  = bool(info.get("requer_bairro", 0))
        id_bairro = int(dd_bairro.value) if dd_bairro.value and requer_b else None

        if requer_b and id_bairro is None:
            txt_erro.value = "Selecione o bairro para este canal."
            page.update()
            return

        eh_deles = bool(info.get("entregador_plataforma", 0))
        taxa    = 0.0 if eh_deles else _to_float(tf_taxa.value)
        repasse = 0.0 if eh_deles else _to_float(tf_repasse.value)
        obs     = tf_obs.value.strip() or None

        if _editando["id"] is not None:
            pid = _editando["id"]
            p_antes = database.pedido_buscar(pid)
            canal_antes = p_antes["canal"] if p_antes else ""
            valor_antes = p_antes["valor_total"] if p_antes else 0.0
            database.pedido_atualizar(
                pid,
                canal=canal,
                valor_total=valor,
                id_operador=int(dd_operador.value),
                id_bairro=id_bairro,
                taxa_entrega=taxa,
                repasse_entregador=repasse,
                obs=obs,
            )
            database.pagamento_deletar_por_pedido(pid)
            for metodo, val_pag in pags_validos:
                database.pagamento_inserir(pid, metodo, val_pag, cortesia=(metodo == "Voucher"))
            database.log_registrar(
                acao="EDITAR_PEDIDO",
                tabela="vendas_pedidos",
                id_registro=pid,
                descricao=f"Pedido #{pid} editado",
                valor_antes=f"canal={canal_antes}, valor={valor_antes}",
                valor_depois=f"canal={canal}, valor={valor}",
            )
            _limpar()
            _atualizar_tabela()
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Pedido #{pid} atualizado com sucesso."),
                bgcolor=ft.Colors.GREEN_700,
                open=True,
            ))
            page.update()
        else:
            id_pedido = database.pedido_inserir(
                data=_data_br_para_iso(tf_data.value or hoje_br),
                hora=datetime.now().strftime("%H:%M"),
                canal=canal,
                valor_total=valor,
                id_operador=int(dd_operador.value),
                id_bairro=id_bairro,
                taxa_entrega=taxa,
                repasse_entregador=repasse,
                obs=obs,
            )
            for metodo, val_pag in pags_validos:
                database.pagamento_inserir(
                    id_pedido, metodo, val_pag, cortesia=(metodo == "Voucher")
                )
            _limpar()
            _atualizar_tabela()
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Pedido salvo!"),
                bgcolor=ft.Colors.GREEN_700,
                open=True,
            ))
            dd_canal.focus()
            page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def _cancelar_edicao(e):
        _limpar()
        page.update()

    btn_cancelar = ft.ElevatedButton(
        "Cancelar Edição",
        icon=ft.Icons.CLOSE,
        visible=False,
        on_click=_cancelar_edicao,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREY_700,
            color=ft.Colors.WHITE,
        ),
    )

    btn_salvar = ft.ElevatedButton(
        "Salvar Pedido",
        icon=ft.Icons.SAVE,
        on_click=_salvar,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        ),
    )

    formulario = ft.Card(
        content=ft.Container(
            padding=ft.Padding.all(20),
            content=ft.Column(
                spacing=14,
                controls=[
                    txt_titulo,
                    ft.Divider(height=1),
                    ft.Row([tf_data, btn_calendario, dd_canal], spacing=8),
                    tf_valor,
                    ft.Column(spacing=4, controls=[
                        ft.Text("Pagamentos", size=13, color=ft.Colors.GREY_500),
                        col_pag,
                        btn_add_pag,
                    ]),
                    dd_operador,
                    linha_bairro,
                    linha_taxas,
                    tf_obs,
                    txt_erro,
                    ft.Row([btn_salvar, btn_cancelar], spacing=12),
                ],
            ),
        ),
    )

    _atualizar_tabela()

    secao_tabela = ft.Card(
        content=ft.Container(
            padding=ft.Padding.all(20),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Pedidos do Dia", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row(controls=[tf_filtro, btn_limpar_filtro], spacing=8),
                    col_tabela,
                ],
            ),
        ),
    )

    return ft.Column(
        controls=[formulario, secao_tabela],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
