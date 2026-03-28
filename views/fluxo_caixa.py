"""
views/fluxo_caixa.py — Extrato cronológico do fluxo de caixa (Diário e por Período).
"""

import csv
import os
from datetime import date

import flet as ft

import database
from relatorios.excel_gerador import (
    excel_fluxo_caixa,
    excel_divergencias,
)
from relatorios.pdf_gerador import (
    gerar_pdf_fluxo_caixa,
    gerar_pdf_divergencias,
    abrir_pdf,
)


# ── Utilitários ───────────────────────────────────────────────────────────────

def _fmt_moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_data_br(iso: str) -> str:
    if not iso or len(iso) < 10:
        return iso or ""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def _data_br_para_iso(s: str) -> str:
    try:
        d, m, a = s.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


def _tipo_chip(tipo: str) -> ft.Container:
    _CORES = {
        "TROCO_INICIAL": (ft.Colors.BLUE_700,   "Troco Ini."),
        "VENDA":         (ft.Colors.GREEN_700,  "Venda"),
        "EXTRA":         (ft.Colors.ORANGE_700, "Extra"),
        "PAGAMENTO":     (ft.Colors.PURPLE_700, "Pagamento"),
    }
    cor, label = _CORES.get(tipo, (ft.Colors.GREY_700, tipo))
    return ft.Container(
        content=ft.Text(label, size=11, color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD),
        bgcolor=cor,
        border_radius=12,
        padding=ft.Padding(left=8, right=8, top=3, bottom=3),
    )


def _card_resumo(titulo: str, valor, cor: str, moeda: bool = True) -> ft.Container:
    valor_str = _fmt_moeda(float(valor)) if moeda else str(int(valor))
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(titulo, size=11, color=ft.Colors.GREY_500),
                ft.Text(valor_str, size=17, weight=ft.FontWeight.BOLD, color=cor),
            ],
            spacing=2,
            tight=True,
        ),
        bgcolor=None,
        border_radius=8,
        padding=ft.Padding.all(12),
        width=175,
    )


def _linha_separador_data(data_iso: str) -> ft.DataRow:
    try:
        d = date.fromisoformat(data_iso)
        DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta",
                   "Sexta", "Sábado", "Domingo"]
        MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio",
                    "Junho", "Julho", "Agosto", "Setembro", "Outubro",
                    "Novembro", "Dezembro"]
        texto = f"{DIAS_PT[d.weekday()]}, {d.day} de {MESES_PT[d.month]} de {d.year}"
    except Exception:
        texto = data_iso

    return ft.DataRow(
        cells=[
            ft.DataCell(ft.Text(
                texto,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.BLUE_200,
                size=13,
            )),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text("")),
        ],
        color=ft.Colors.with_opacity(0.06, ft.Colors.BLUE),
    )


def _calcular_saldo_acumulado(lancamentos):
    """Retorna lista de (row_dict, saldo_acumulado)."""
    saldo = 0.0
    result = []
    for row in lancamentos:
        saldo += (row["entrada"] or 0.0) - (row["saida"] or 0.0)
        result.append((dict(row), saldo))
    return result


def _construir_tabela(linhas_rows: list) -> ft.Row:
    colunas = [
        ft.DataColumn(ft.Text("Hora",      size=12)),
        ft.DataColumn(ft.Text("Tipo",      size=12)),
        ft.DataColumn(ft.Text("Descrição", size=12)),
        ft.DataColumn(ft.Text("Método",    size=12)),
        ft.DataColumn(ft.Text("Entrada",   size=12), numeric=True),
        ft.DataColumn(ft.Text("Saída",     size=12), numeric=True),
        ft.DataColumn(ft.Text("Saldo",     size=12), numeric=True),
    ]
    return ft.Row(
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.DataTable(
                columns=colunas,
                rows=linhas_rows,
                column_spacing=14,
                border=ft.border.all(1, ft.Colors.GREY_600),
                border_radius=8,
                horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_600),
            )
        ],
    )


def _data_row(row: dict, saldo: float) -> ft.DataRow:
    entrada = row.get("entrada") or 0.0
    saida   = row.get("saida")   or 0.0
    return ft.DataRow(cells=[
        ft.DataCell(ft.Text(row.get("hora") or "", size=12)),
        ft.DataCell(_tipo_chip(row.get("tipo") or "")),
        ft.DataCell(ft.Text(row.get("descricao") or "", size=12)),
        ft.DataCell(ft.Text(row.get("metodo") or "", size=12)),
        ft.DataCell(ft.Text(
            _fmt_moeda(entrada) if entrada else "",
            size=12, color=ft.Colors.GREEN_400,
        )),
        ft.DataCell(ft.Text(
            _fmt_moeda(saida) if saida else "",
            size=12, color=ft.Colors.RED_400,
        )),
        ft.DataCell(ft.Text(
            _fmt_moeda(saldo),
            size=12,
            color=ft.Colors.BLUE_300 if saldo >= 0 else ft.Colors.RED_300,
        )),
    ])


# ── View principal ────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Column:

    hoje_iso = date.today().isoformat()
    hoje_br  = date.today().strftime("%d/%m/%Y")

    # ── Estado ──────────────────────────────────────────────────────────────
    _state_diario   = {"data": hoje_iso, "lancamentos": []}
    _state_periodo  = {"ini": None, "fim": None, "lancamentos": []}

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB DIÁRIO
    # ═════════════════════════════════════════════════════════════════════════

    tf_data_diario = ft.TextField(
        value=hoje_br,
        label="Data",
        width=130,
        text_size=14,
        hint_text="DD/MM/AAAA",
    )

    date_picker_diario = ft.DatePicker(
        on_change=lambda e: _on_pick_diario(e.control.value),
    )
    page.overlay.append(date_picker_diario)

    def _on_pick_diario(val):
        if val:
            _state_diario["data"] = val.strftime("%Y-%m-%d")
            tf_data_diario.value  = val.strftime("%d/%m/%Y")
            _gerar_diario()

    btn_cal_diario = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar data",
        on_click=lambda e: (
            setattr(date_picker_diario, "open", True),
            page.update(),
        ),
    )

    row_resumo_diario = ft.Row(spacing=12, wrap=True)
    col_conteudo_diario = ft.Column(spacing=8, expand=True)

    def _gerar_diario(e=None):
        iso = _data_br_para_iso(tf_data_diario.value)
        _state_diario["data"] = iso
        lancamentos = database.fluxo_caixa_listar_lancamentos(iso, iso)
        _state_diario["lancamentos"] = [dict(r) for r in lancamentos]

        total_e = sum((r["entrada"] or 0.0) for r in lancamentos)
        total_s = sum((r["saida"]   or 0.0) for r in lancamentos)
        saldo_f = total_e - total_s

        row_resumo_diario.controls = [
            _card_resumo("Total Entradas",  total_e, ft.Colors.GREEN_400),
            _card_resumo("Total Saídas",    total_s, ft.Colors.RED_400),
            _card_resumo("Saldo Final",     saldo_f,
                         ft.Colors.BLUE_300 if saldo_f >= 0 else ft.Colors.RED_300),
            _card_resumo("Lançamentos", len(lancamentos),
                         ft.Colors.GREY_500, moeda=False),
        ]

        with_saldo = _calcular_saldo_acumulado(lancamentos)

        if not with_saldo:
            col_conteudo_diario.controls = [
                ft.Text(
                    "Sem lançamentos para a data selecionada.",
                    italic=True,
                    color=ft.Colors.GREY_500,
                )
            ]
        else:
            rows = [_data_row(r, s) for r, s in with_saldo]
            col_conteudo_diario.controls = [_construir_tabela(rows)]

        page.update()

    btn_gerar_diario = ft.ElevatedButton(
        "Gerar",
        ft.Icons.REFRESH,
        on_click=_gerar_diario,
    )

    def _exportar_csv_diario(e):
        if not _state_diario["lancamentos"]:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o extrato antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        os.makedirs("exports", exist_ok=True)
        nome = f"fluxo_caixa_{_state_diario['data'].replace('-', '')}.csv"
        caminho = os.path.join("exports", nome)
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Data", "Hora", "Tipo", "Descrição", "Método",
                        "Entrada", "Saída", "Saldo"])
            saldo = 0.0
            for r in _state_diario["lancamentos"]:
                saldo += (r.get("entrada") or 0.0) - (r.get("saida") or 0.0)
                w.writerow([
                    r.get("data", ""),
                    r.get("hora", "") or "",
                    r.get("tipo", ""),
                    r.get("descricao", "") or "",
                    r.get("metodo", "") or "",
                    f"{r.get('entrada') or 0.0:.2f}",
                    f"{r.get('saida') or 0.0:.2f}",
                    f"{saldo:.2f}",
                ])
        os.startfile(os.path.abspath(caminho))

    btn_exportar_diario = ft.ElevatedButton(
        "Exportar CSV",
        ft.Icons.DOWNLOAD,
        on_click=_exportar_csv_diario,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.TEAL_700,
            color=ft.Colors.WHITE,
        ),
    )

    def _exportar_excel_diario(e):
        if not _state_diario["lancamentos"]:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o extrato antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            data_br = tf_data_diario.value or date.today().strftime("%d/%m/%Y")
            caminho = excel_fluxo_caixa("Diário", data_br, data_br,
                                        _state_diario["lancamentos"])
            os.startfile(caminho)
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Arquivo aberto para visualização."),
                bgcolor=ft.Colors.GREEN_700, open=True,
            ))
        except Exception as exc:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Erro ao gerar arquivo: {exc}"),
                bgcolor=ft.Colors.RED_700, open=True,
            ))
        page.update()

    def _exportar_pdf_diario(e):
        if not _state_diario["lancamentos"]:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o extrato antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            data_br = tf_data_diario.value or date.today().strftime("%d/%m/%Y")
            caminho = gerar_pdf_fluxo_caixa("Diário", data_br, data_br,
                                            _state_diario["lancamentos"])
            abrir_pdf(caminho)
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Arquivo aberto para visualização."),
                bgcolor=ft.Colors.GREEN_700, open=True,
            ))
        except Exception as exc:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Erro ao gerar arquivo: {exc}"),
                bgcolor=ft.Colors.RED_700, open=True,
            ))
        page.update()

    tf_data_diario.on_submit = _gerar_diario

    topo_diario = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Row(
            controls=[
                tf_data_diario,
                btn_cal_diario,
                btn_gerar_diario,
                btn_exportar_diario,
                ft.ElevatedButton(
                    "Excel",
                    icon=ft.Icons.TABLE_VIEW,
                    on_click=_exportar_excel_diario,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.GREEN_800,
                        color=ft.Colors.WHITE,
                    ),
                ),
                ft.ElevatedButton(
                    "PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=_exportar_pdf_diario,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_800,
                        color=ft.Colors.WHITE,
                    ),
                ),
                ft.Text(
                    "Selecione a data e clique em Gerar",
                    color=ft.Colors.GREY_500,
                    italic=True,
                    size=13,
                ),
            ],
            spacing=12,
        ),
    ))

    aba_diario = ft.Column(
        controls=[
            topo_diario,
            ft.Container(
                content=row_resumo_diario,
                padding=ft.Padding(top=8, bottom=8),
            ),
            col_conteudo_diario,
        ],
        spacing=8,
        expand=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB PERÍODO
    # ═════════════════════════════════════════════════════════════════════════

    tf_ini = ft.TextField(
        value=hoje_br,
        label="Início",
        width=130,
        text_size=14,
        hint_text="DD/MM/AAAA",
    )
    tf_fim = ft.TextField(
        value=hoje_br,
        label="Fim",
        width=130,
        text_size=14,
        hint_text="DD/MM/AAAA",
    )

    date_picker_periodo = ft.DatePicker(
        on_change=lambda e: _on_pick_periodo(e.control.value),
    )
    page.overlay.append(date_picker_periodo)

    _pick_target = {"campo": "ini"}

    def _on_pick_periodo(val):
        if val:
            iso = val.strftime("%Y-%m-%d")
            br  = val.strftime("%d/%m/%Y")
            if _pick_target["campo"] == "ini":
                tf_ini.value = br
                _state_periodo["ini"] = iso
            else:
                tf_fim.value = br
                _state_periodo["fim"] = iso
            page.update()

    def _abrir_dp_ini(e):
        _pick_target["campo"] = "ini"
        date_picker_periodo.open = True
        page.update()

    def _abrir_dp_fim(e):
        _pick_target["campo"] = "fim"
        date_picker_periodo.open = True
        page.update()

    btn_cal_ini = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar início",
        on_click=_abrir_dp_ini,
    )
    btn_cal_fim = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar fim",
        on_click=_abrir_dp_fim,
    )

    row_resumo_periodo = ft.Row(spacing=12, wrap=True)
    col_conteudo_periodo = ft.Column(spacing=8, expand=True)

    def _gerar_periodo(e=None):
        ini_iso = _data_br_para_iso(tf_ini.value)
        fim_iso = _data_br_para_iso(tf_fim.value)
        _state_periodo["ini"] = ini_iso
        _state_periodo["fim"] = fim_iso

        lancamentos = database.fluxo_caixa_listar_lancamentos(ini_iso, fim_iso)
        _state_periodo["lancamentos"] = [dict(r) for r in lancamentos]

        total_e = sum((r["entrada"] or 0.0) for r in lancamentos)
        total_s = sum((r["saida"]   or 0.0) for r in lancamentos)
        saldo_f = total_e - total_s

        row_resumo_periodo.controls = [
            _card_resumo("Total Entradas",  total_e, ft.Colors.GREEN_400),
            _card_resumo("Total Saídas",    total_s, ft.Colors.RED_400),
            _card_resumo("Saldo Final",     saldo_f,
                         ft.Colors.BLUE_300 if saldo_f >= 0 else ft.Colors.RED_300),
            _card_resumo("Lançamentos", len(lancamentos),
                         ft.Colors.GREY_500, moeda=False),
        ]

        if not lancamentos:
            col_conteudo_periodo.controls = [
                ft.Text(
                    "Sem lançamentos no período selecionado.",
                    italic=True,
                    color=ft.Colors.GREY_500,
                )
            ]
            page.update()
            return

        # Constrói rows com separadores de data
        with_saldo = _calcular_saldo_acumulado(lancamentos)
        rows = []
        data_atual = None
        for row, saldo in with_saldo:
            if row["data"] != data_atual:
                data_atual = row["data"]
                rows.append(_linha_separador_data(data_atual))
            rows.append(_data_row(row, saldo))

        N_COLUNAS = 7
        for i, row in enumerate(rows):
            if len(row.cells) != N_COLUNAS:
                print(f"[ERRO] Linha {i} tem {len(row.cells)} células, esperado {N_COLUNAS}")

        col_conteudo_periodo.controls = [_construir_tabela(rows)]
        page.update()

    btn_gerar_periodo = ft.ElevatedButton(
        "Gerar",
        ft.Icons.REFRESH,
        on_click=_gerar_periodo,
    )

    def _exportar_csv_periodo(e):
        if not _state_periodo["lancamentos"]:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o extrato antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        os.makedirs("exports", exist_ok=True)
        ini_str = (_state_periodo["ini"] or hoje_iso).replace("-", "")
        fim_str = (_state_periodo["fim"] or hoje_iso).replace("-", "")
        nome    = f"fluxo_caixa_{ini_str}_{fim_str}.csv"
        caminho = os.path.join("exports", nome)
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Data", "Hora", "Tipo", "Descrição", "Método",
                        "Entrada", "Saída", "Saldo"])
            saldo = 0.0
            for r in _state_periodo["lancamentos"]:
                saldo += (r.get("entrada") or 0.0) - (r.get("saida") or 0.0)
                w.writerow([
                    r.get("data", ""),
                    r.get("hora", "") or "",
                    r.get("tipo", ""),
                    r.get("descricao", "") or "",
                    r.get("metodo", "") or "",
                    f"{r.get('entrada') or 0.0:.2f}",
                    f"{r.get('saida') or 0.0:.2f}",
                    f"{saldo:.2f}",
                ])
        os.startfile(os.path.abspath(caminho))

    btn_exportar_periodo = ft.ElevatedButton(
        "Exportar CSV",
        ft.Icons.DOWNLOAD,
        on_click=_exportar_csv_periodo,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.TEAL_700,
            color=ft.Colors.WHITE,
        ),
    )

    def _exportar_excel_periodo(e):
        if not _state_periodo["lancamentos"]:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o extrato antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            ini_br = tf_ini.value or hoje_br
            fim_br = tf_fim.value or hoje_br
            caminho = excel_fluxo_caixa("Período", ini_br, fim_br,
                                        _state_periodo["lancamentos"])
            os.startfile(caminho)
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Arquivo aberto para visualização."),
                bgcolor=ft.Colors.GREEN_700, open=True,
            ))
        except Exception as exc:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Erro ao gerar arquivo: {exc}"),
                bgcolor=ft.Colors.RED_700, open=True,
            ))
        page.update()

    def _exportar_pdf_periodo(e):
        if not _state_periodo["lancamentos"]:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o extrato antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            ini_br = tf_ini.value or hoje_br
            fim_br = tf_fim.value or hoje_br
            caminho = gerar_pdf_fluxo_caixa("Período", ini_br, fim_br,
                                            _state_periodo["lancamentos"])
            abrir_pdf(caminho)
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Arquivo aberto para visualização."),
                bgcolor=ft.Colors.GREEN_700, open=True,
            ))
        except Exception as exc:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Erro ao gerar arquivo: {exc}"),
                bgcolor=ft.Colors.RED_700, open=True,
            ))
        page.update()

    topo_periodo = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Row(
            controls=[
                tf_ini,
                btn_cal_ini,
                tf_fim,
                btn_cal_fim,
                btn_gerar_periodo,
                btn_exportar_periodo,
                ft.ElevatedButton(
                    "Excel",
                    icon=ft.Icons.TABLE_VIEW,
                    on_click=_exportar_excel_periodo,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.GREEN_800,
                        color=ft.Colors.WHITE,
                    ),
                ),
                ft.ElevatedButton(
                    "PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=_exportar_pdf_periodo,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_800,
                        color=ft.Colors.WHITE,
                    ),
                ),
                ft.Text(
                    "Selecione o período e clique em Gerar",
                    color=ft.Colors.GREY_500,
                    italic=True,
                    size=13,
                ),
            ],
            spacing=12,
        ),
    ))

    aba_periodo = ft.Column(
        controls=[
            topo_periodo,
            ft.Container(
                content=row_resumo_periodo,
                padding=ft.Padding(top=8, bottom=8),
            ),
            col_conteudo_periodo,
        ],
        spacing=8,
        expand=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    #  TAB HISTÓRICO
    # ═════════════════════════════════════════════════════════════════════════

    tf_hist_ini = ft.TextField(
        value=hoje_br, label="Início", width=130, text_size=14, hint_text="DD/MM/AAAA",
    )
    tf_hist_fim = ft.TextField(
        value=hoje_br, label="Fim", width=130, text_size=14, hint_text="DD/MM/AAAA",
    )

    date_picker_hist = ft.DatePicker(
        on_change=lambda e: _on_pick_hist(e.control.value),
    )
    page.overlay.append(date_picker_hist)
    _hist_pick_target = {"campo": "ini"}

    def _on_pick_hist(val):
        if val:
            br = val.strftime("%d/%m/%Y")
            if _hist_pick_target["campo"] == "ini":
                tf_hist_ini.value = br
            else:
                tf_hist_fim.value = br
            page.update()

    def _abrir_dp_hist_ini(e):
        _hist_pick_target["campo"] = "ini"
        date_picker_hist.open = True
        page.update()

    def _abrir_dp_hist_fim(e):
        _hist_pick_target["campo"] = "fim"
        date_picker_hist.open = True
        page.update()

    chk_apenas_div = ft.Checkbox(label="Apenas divergências", value=False)

    row_resumo_hist = ft.Row(spacing=12, wrap=True)
    col_hist = ft.Column(spacing=8, expand=True)

    _state_hist: dict = {"registros": [], "ini": None, "fim": None}

    def _gerar_historico(e=None):
        ini_iso = _data_br_para_iso(tf_hist_ini.value)
        fim_iso = _data_br_para_iso(tf_hist_fim.value)
        _state_hist["ini"] = ini_iso
        _state_hist["fim"] = fim_iso
        registros = database.fluxo_caixa_historico_divergencias(
            ini_iso, fim_iso, apenas_divergencias=chk_apenas_div.value or False,
        )
        _state_hist["registros"] = registros

        total_dias   = len(registros)
        total_div    = sum(1 for r in registros if abs(r.get("diferenca") or 0.0) > 0.001)
        soma_positiv = sum((r.get("diferenca") or 0.0) for r in registros
                          if (r.get("diferenca") or 0.0) > 0.001)
        soma_negativ = sum((r.get("diferenca") or 0.0) for r in registros
                          if (r.get("diferenca") or 0.0) < -0.001)

        row_resumo_hist.controls = [
            _card_resumo("Dias no Período",    total_dias,   ft.Colors.GREY_500,    moeda=False),
            _card_resumo("Com Divergência",    total_div,    ft.Colors.ORANGE_400,  moeda=False),
            _card_resumo("Sobras (+)",         soma_positiv, ft.Colors.GREEN_400),
            _card_resumo("Faltas (−)",         abs(soma_negativ), ft.Colors.RED_400),
        ]

        if not registros:
            col_hist.controls = [
                ft.Text(
                    "Nenhum registro encontrado para o período.",
                    italic=True, color=ft.Colors.GREY_500,
                )
            ]
            page.update()
            return

        rows_dt = []
        for r in registros:
            diferenca = r.get("diferenca") or 0.0
            if abs(diferenca) > 0.001:
                cor_div = ft.Colors.GREEN_400 if diferenca > 0 else ft.Colors.RED_400
            else:
                cor_div = ft.Colors.GREY_500

            obs_atual = r.get("obs_fechamento") or ""
            data_iso  = r.get("data") or ""

            def _fazer_editar_obs(data_ref, obs_ref):
                def _editar_obs(e):
                    tf_obs = ft.TextField(
                        value=obs_ref,
                        label="Observação do Fechamento",
                        multiline=True,
                        min_lines=2,
                        max_lines=5,
                        width=400,
                    )

                    def _salvar_obs(e2):
                        database.fluxo_caixa_atualizar(
                            data_ref, obs_fechamento=tf_obs.value
                        )
                        dlg.open = False
                        _gerar_historico()

                    dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Text(f"Observação — {_fmt_data_br(data_ref)}"),
                        content=tf_obs,
                        actions=[
                            ft.TextButton("Cancelar", on_click=lambda e2: (
                                setattr(dlg, "open", False), page.update()
                            )),
                            ft.ElevatedButton("Salvar", on_click=_salvar_obs),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                    )
                    page.overlay.append(dlg)
                    dlg.open = True
                    page.update()
                return _editar_obs

            def _fazer_ver_relatorio(data_ref):
                def _ver(e):
                    tf_data_diario.value = _fmt_data_br(data_ref)
                    tabs.selected_index = 0
                    _gerar_diario()
                return _ver

            rows_dt.append(ft.DataRow(
                color=(
                    ft.Colors.with_opacity(0.06, ft.Colors.RED)
                    if abs(diferenca) > 0.001 else None
                ),
                cells=[
                    ft.DataCell(ft.Text(_fmt_data_br(data_iso), size=12)),
                    ft.DataCell(ft.Text(_fmt_moeda(r.get("saldo_teorico") or 0.0),
                                        size=12, color=ft.Colors.BLUE_300)),
                    ft.DataCell(ft.Text(_fmt_moeda(r.get("saldo_gaveta_real") or 0.0),
                                        size=12, color=ft.Colors.GREY_500)),
                    ft.DataCell(ft.Text(
                        _fmt_moeda(diferenca),
                        size=12, color=cor_div,
                        weight=ft.FontWeight.BOLD if abs(diferenca) > 0.001 else None,
                    )),
                    ft.DataCell(ft.Text(
                        obs_atual if obs_atual else "—",
                        size=11,
                        color=ft.Colors.GREY_500 if not obs_atual else None,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    )),
                    ft.DataCell(ft.Row(spacing=4, controls=[
                        ft.IconButton(
                            icon=ft.Icons.EDIT_NOTE,
                            icon_size=16,
                            tooltip="Editar observação",
                            on_click=_fazer_editar_obs(data_iso, obs_atual),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.OPEN_IN_NEW,
                            icon_size=16,
                            tooltip="Ver extrato do dia",
                            on_click=_fazer_ver_relatorio(data_iso),
                        ),
                    ])),
                ],
            ))

        tabela_hist = ft.Row(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Data",        size=12)),
                        ft.DataColumn(ft.Text("Teórico",     size=12), numeric=True),
                        ft.DataColumn(ft.Text("Gaveta Real", size=12), numeric=True),
                        ft.DataColumn(ft.Text("Diferença",   size=12), numeric=True),
                        ft.DataColumn(ft.Text("Observação",  size=12)),
                        ft.DataColumn(ft.Text("Ações",       size=12)),
                    ],
                    rows=rows_dt,
                    column_spacing=14,
                    border=ft.border.all(1, ft.Colors.GREY_600),
                    border_radius=8,
                    horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_600),
                )
            ],
        )
        col_hist.controls = [tabela_hist]
        page.update()

    def _exportar_csv_hist(e):
        registros = _state_hist["registros"]
        if not registros:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Carregue o histórico antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        os.makedirs("exports", exist_ok=True)
        ini_str = (_state_hist["ini"] or hoje_iso).replace("-", "")
        fim_str = (_state_hist["fim"] or hoje_iso).replace("-", "")
        nome    = f"historico_fechamentos_{ini_str}_{fim_str}.csv"
        caminho = os.path.join("exports", nome)
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Data", "Saldo Teórico", "Gaveta Real", "Diferença", "Observação"])
            for r in registros:
                w.writerow([
                    r.get("data", ""),
                    f"{r.get('saldo_teorico') or 0.0:.2f}",
                    f"{r.get('saldo_gaveta_real') or 0.0:.2f}",
                    f"{r.get('diferenca') or 0.0:.2f}",
                    r.get("obs_fechamento") or "",
                ])
        os.startfile(os.path.abspath(caminho))

    def _exportar_excel_hist(e):
        registros = _state_hist["registros"]
        if not registros:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Carregue o histórico antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            ini_br = tf_hist_ini.value or hoje_br
            fim_br = tf_hist_fim.value or hoje_br
            caminho = excel_divergencias(ini_br, fim_br, registros)
            os.startfile(caminho)
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Arquivo aberto para visualização."),
                bgcolor=ft.Colors.GREEN_700, open=True,
            ))
        except Exception as exc:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Erro ao gerar arquivo: {exc}"),
                bgcolor=ft.Colors.RED_700, open=True,
            ))
        page.update()

    def _exportar_pdf_hist(e):
        registros = _state_hist["registros"]
        if not registros:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Carregue o histórico antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            ini_br = tf_hist_ini.value or hoje_br
            fim_br = tf_hist_fim.value or hoje_br
            caminho = gerar_pdf_divergencias(ini_br, fim_br, registros)
            abrir_pdf(caminho)
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Arquivo aberto para visualização."),
                bgcolor=ft.Colors.GREEN_700, open=True,
            ))
        except Exception as exc:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Erro ao gerar arquivo: {exc}"),
                bgcolor=ft.Colors.RED_700, open=True,
            ))
        page.update()

    topo_hist = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Row(
            controls=[
                tf_hist_ini,
                ft.IconButton(icon=ft.Icons.CALENDAR_MONTH,
                              tooltip="Selecionar início", on_click=_abrir_dp_hist_ini),
                tf_hist_fim,
                ft.IconButton(icon=ft.Icons.CALENDAR_MONTH,
                              tooltip="Selecionar fim", on_click=_abrir_dp_hist_fim),
                chk_apenas_div,
                ft.ElevatedButton("Carregar", ft.Icons.REFRESH, on_click=_gerar_historico),
                ft.ElevatedButton(
                    "Exportar CSV", ft.Icons.DOWNLOAD,
                    on_click=_exportar_csv_hist,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_700, color=ft.Colors.WHITE),
                ),
                ft.ElevatedButton(
                    "Excel",
                    icon=ft.Icons.TABLE_VIEW,
                    on_click=_exportar_excel_hist,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800, color=ft.Colors.WHITE),
                ),
                ft.ElevatedButton(
                    "PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=_exportar_pdf_hist,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE),
                ),
            ],
            spacing=12,
        ),
    ))

    aba_historico = ft.Column(
        controls=[
            topo_hist,
            ft.Container(content=row_resumo_hist, padding=ft.Padding(top=8, bottom=8)),
            col_hist,
        ],
        spacing=8,
        expand=True,
    )

    # ═════════════════════════════════════════════════════════════════════════
    #  TABS (padrão Flet 0.82: ft.Tabs + ft.TabBar + ft.TabBarView)
    # ═════════════════════════════════════════════════════════════════════════

    tabs = ft.Tabs(
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(tabs=[
                    ft.Tab("Diário"),
                    ft.Tab("Período"),
                    ft.Tab("Histórico"),
                ]),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        ft.Container(
                            content=aba_diario,
                            expand=True,
                            padding=ft.Padding(top=12),
                        ),
                        ft.Container(
                            content=aba_periodo,
                            expand=True,
                            padding=ft.Padding(top=12),
                        ),
                        ft.Container(
                            content=aba_historico,
                            expand=True,
                            padding=ft.Padding(top=12),
                        ),
                    ],
                ),
            ],
        ),
        length=3,
    )

    return ft.Column(
        controls=[
            ft.Text(
                "Fluxo de Caixa",
                size=22,
                weight=ft.FontWeight.BOLD,
            ),
            tabs,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
