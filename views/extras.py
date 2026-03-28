"""
views/extras.py — Movimentações: Vale, Sangria, Consumo, Corrida Extra,
                  Reentrega, Fiado, Pagamento, Outros.
"""

import flet as ft
from datetime import date

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


# Configuração por nome de categoria:
# (mostra_pessoa, tipo_pessoa, mostra_metodo, fluxo_override)
# tipo_pessoa: "INTERNO" | "ENTREGADOR" | "ALL" | None
_CAT_CONFIG = {
    "Vale":          (True,  "INTERNO",    True,  None),
    "Adiantamento":  (True,  "INTERNO",    True,  None),
    "Sangria":       (False, None,         False, None),
    "Consumo":       (True,  "INTERNO",    False, None),
    "Corrida Extra": (True,  "ENTREGADOR", False, "NEUTRO"),
    "Reentrega":     (True,  "ENTREGADOR", False, "NEUTRO"),
    "Fiado":         (False, None,         True,  None),
    "Pagamento":     (True,  "INTERNO",    True,  None),
}
_CFG_DEFAULT = (True, "ALL", True, None)   # Outros / categorias não mapeadas


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
    categorias_db   = database.categoria_extra_listar()
    metodos_db      = database.metodo_pag_listar()
    funcionarios_db = database.pessoa_listar(tipo="INTERNO",    apenas_ativos=True)
    entregadores_db = database.pessoa_listar(tipo="ENTREGADOR", apenas_ativos=True)
    pessoas_db      = database.pessoa_listar(apenas_ativos=True)

    cat_map = {r["id"]: dict(r) for r in categorias_db}

    def _opts_pessoa(tipo):
        if tipo == "INTERNO":
            src = funcionarios_db
        elif tipo == "ENTREGADOR":
            src = entregadores_db
        else:
            src = pessoas_db
        return [ft.dropdown.Option(key=str(r["id"]), text=r["nome"]) for r in src]

    # ── Campo Data + calendário ───────────────────────────────────────────
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

    # ── Controles do formulário ───────────────────────────────────────────
    dd_categoria = ft.Dropdown(
        label="Categoria *",
        options=[
            ft.dropdown.Option(key=str(r["id"]), text=r["descricao"])
            for r in categorias_db
        ],
        expand=True,
    )

    dd_pessoa = ft.Dropdown(
        label="Funcionário *",
        options=_opts_pessoa(None),
        expand=True,
    )
    linha_pessoa = ft.Row([dd_pessoa], visible=False)

    dd_metodo = ft.Dropdown(
        label="Método de Pagamento",
        options=[ft.dropdown.Option(r["nome"]) for r in metodos_db],
        expand=True,
    )
    linha_metodo = ft.Row([dd_metodo], visible=False)

    tf_valor = ft.TextField(
        label="Valor (R$) *",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    tf_obs = ft.TextField(
        label="Observações",
        multiline=True,
        min_lines=2,
        max_lines=3,
        expand=True,
    )

    txt_erro = ft.Text("", color=ft.Colors.RED_400, size=13)

    # Estado interno da categoria selecionada
    _estado = {"fluxo": "", "pessoa_obrig": False, "cat_nome": ""}

    # ── Tabela ────────────────────────────────────────────────────────────
    col_tabela = ft.Column(spacing=0, expand=True)
    row_totais  = ft.Row(spacing=16, wrap=True)

    def _atualizar_tabela():
        data_iso = _data_br_para_iso(tf_data.value or hoje_br)
        movs     = database.mov_extra_listar_por_data(data_iso)

        def _on_excluir(id_mov, cat, val, dt):
            def handler(e):
                def _excluir():
                    database.mov_extra_excluir(id_mov)
                    database.log_registrar(
                        acao="EXCLUIR_MOVIMENTACAO",
                        tabela="movimentacoes_extras",
                        id_registro=id_mov,
                        descricao=f"Movimentação excluída — "
                                  f"Categoria: {cat} | "
                                  f"Valor: R$ {val:.2f} | Data: {dt}",
                        valor_antes=f"categoria={cat}, valor={val}",
                    )
                    _atualizar_tabela()
                    page.update()
                _confirmar_exclusao(page, "esta movimentação", _excluir)
            return handler

        total_entrada = 0.0
        total_saida   = 0.0
        total_neutro  = 0.0
        linhas = []

        for m in movs:
            fluxo = m["fluxo"]
            if fluxo == "ENTRADA":
                total_entrada += m["valor"]
                fluxo_cor = ft.Colors.GREEN_400
            elif fluxo == "SAIDA":
                total_saida += m["valor"]
                fluxo_cor = ft.Colors.RED_400
            else:   # NEUTRO
                total_neutro += m["valor"]
                fluxo_cor = ft.Colors.GREY_500

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(m["nome_pessoa"] or "—")),
                ft.DataCell(ft.Text(m["categoria"])),
                ft.DataCell(ft.Text(
                    fluxo,
                    color=fluxo_cor,
                    weight=ft.FontWeight.W_500,
                )),
                ft.DataCell(ft.Text(m["metodo"] or "—")),
                ft.DataCell(ft.Text(f"R$ {m['valor']:.2f}")),
                ft.DataCell(ft.Text(m["obs"] or "")),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Excluir",
                    on_click=_on_excluir(m["id"], m["categoria"], m["valor"], tf_data.value),
                )),
            ]))

        col_tabela.controls.clear()
        if not linhas:
            col_tabela.controls.append(ft.Text(
                "Nenhuma movimentação nesta data.",
                italic=True,
                color=ft.Colors.GREY_500,
            ))
        else:
            col_tabela.controls.append(ft.Row(
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Pessoa")),
                            ft.DataColumn(ft.Text("Categoria")),
                            ft.DataColumn(ft.Text("Fluxo")),
                            ft.DataColumn(ft.Text("Método")),
                            ft.DataColumn(ft.Text("Valor"), numeric=True),
                            ft.DataColumn(ft.Text("Obs")),
                            ft.DataColumn(ft.Text("")),
                        ],
                        rows=linhas,
                        column_spacing=14,
                        horizontal_lines=ft.BorderSide(
                            1, ft.Colors.with_opacity(0.15, ft.Colors.BLACK)
                        ),
                    )
                ],
            ))

        row_totais.controls.clear()
        row_totais.controls += [
            ft.Text(
                f"Entradas: R$ {total_entrada:.2f}",
                color=ft.Colors.GREEN_400,
                weight=ft.FontWeight.BOLD,
                size=14,
            ),
            ft.Text("|", color=ft.Colors.GREY_600),
            ft.Text(
                f"Saídas: R$ {total_saida:.2f}",
                color=ft.Colors.RED_400,
                weight=ft.FontWeight.BOLD,
                size=14,
            ),
            ft.Text("|", color=ft.Colors.GREY_600),
            ft.Text(
                f"Neutro (corridas/reentregas): R$ {total_neutro:.2f}",
                color=ft.Colors.GREY_500,
                weight=ft.FontWeight.BOLD,
                size=14,
            ),
        ]

    # ── Lógica dinâmica de campos ─────────────────────────────────────────

    def _on_categoria_select(e):
        if not dd_categoria.value:
            linha_pessoa.visible = False
            linha_metodo.visible = False
            _estado["fluxo"]        = ""
            _estado["pessoa_obrig"] = False
            _estado["cat_nome"]     = ""
            txt_erro.value = ""
            page.update()
            return

        cat  = cat_map.get(int(dd_categoria.value), {})
        nome = cat.get("descricao", "")
        cfg  = _CAT_CONFIG.get(nome, _CFG_DEFAULT)
        mostra_pessoa, tipo_pessoa, mostra_metodo, fluxo_override = cfg

        fluxo = fluxo_override if fluxo_override else cat.get("fluxo", "SAIDA")
        _estado["fluxo"]        = fluxo
        _estado["pessoa_obrig"] = mostra_pessoa
        _estado["cat_nome"]     = nome

        # Ajusta dropdown de pessoa
        if mostra_pessoa:
            dd_pessoa.label   = "Entregador *" if tipo_pessoa == "ENTREGADOR" else "Funcionário *"
            dd_pessoa.options = _opts_pessoa(tipo_pessoa)
            dd_pessoa.value   = None
        linha_pessoa.visible = mostra_pessoa

        # Ajusta método
        dd_metodo.value      = None
        linha_metodo.visible = mostra_metodo

        txt_erro.value = ""
        page.update()

    def _on_data_change(e):
        _atualizar_tabela()
        page.update()

    dd_categoria.on_select = _on_categoria_select
    tf_data.on_submit      = _on_data_change
    tf_data.on_blur        = _on_data_change

    # ── Limpar formulário (mantém data) ───────────────────────────────────

    def _limpar():
        data_atual           = tf_data.value
        dd_categoria.value   = None
        dd_pessoa.value      = None
        dd_metodo.value      = None
        tf_valor.value       = ""
        tf_obs.value         = ""
        txt_erro.value       = ""
        linha_pessoa.visible = False
        linha_metodo.visible = False
        _estado["fluxo"]        = ""
        _estado["pessoa_obrig"] = False
        _estado["cat_nome"]     = ""
        tf_data.value = data_atual

    # ── Salvar ────────────────────────────────────────────────────────────

    def _salvar(e):
        txt_erro.value = ""

        if not dd_categoria.value:
            txt_erro.value = "Selecione a categoria."
            page.update()
            return

        valor = _to_float(tf_valor.value)
        if valor <= 0:
            txt_erro.value = "Informe o valor."
            page.update()
            return

        if _estado["pessoa_obrig"] and not dd_pessoa.value:
            lbl = "Entregador" if _estado["cat_nome"] in ("Corrida Extra", "Reentrega") else "Funcionário"
            txt_erro.value = f"Selecione o {lbl}."
            page.update()
            return

        id_cat   = int(dd_categoria.value)
        cat      = cat_map[id_cat]
        cat_nome = cat["descricao"]
        fluxo    = _estado["fluxo"] or cat["fluxo"]
        id_pessoa = int(dd_pessoa.value) if dd_pessoa.value else None
        metodo    = dd_metodo.value or None

        obs = tf_obs.value.strip() or None
        if cat_nome == "Consumo":
            sufixo = "(desconto 20% aplicado no holerite)"
            obs    = f"{obs} {sufixo}" if obs else sufixo

        database.mov_extra_inserir(
            data=_data_br_para_iso(tf_data.value),
            id_categoria=id_cat,
            fluxo=fluxo,
            valor=valor,
            id_pessoa=id_pessoa,
            metodo=metodo,
            obs=obs,
        )

        _limpar()
        _atualizar_tabela()

        page.overlay.append(ft.SnackBar(
            content=ft.Text("Movimentação salva!"),
            bgcolor=ft.Colors.GREEN_700,
            open=True,
        ))
        page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    btn_salvar = ft.ElevatedButton(
        "Salvar",
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
                    ft.Text("Nova Movimentação", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row([tf_data, btn_calendario], spacing=8),
                    dd_categoria,
                    linha_pessoa,
                    linha_metodo,
                    tf_valor,
                    tf_obs,
                    txt_erro,
                    btn_salvar,
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
                    ft.Text("Movimentações do Dia", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    col_tabela,
                    ft.Divider(height=1),
                    row_totais,
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
