"""
views/funcionarios.py — Escala mensal e holerite por funcionário interno.
"""

import calendar
import csv
import os
from datetime import date

import flet as ft

import database
from relatorios.pdf_gerador import gerar_pdf_holerite, abrir_pdf
from relatorios.excel_gerador import excel_holerite


# ── Constantes ────────────────────────────────────────────────────────────────

TIPOS_ESCALA = ["TRABALHOU", "FALTA", "FOLGA", "FERIADO", "EXTRA"]
_ABREV = {
    "TRABALHOU": "Trab.",
    "FALTA":     "Falta",
    "FOLGA":     "Folga",
    "FERIADO":   "Feriado",
    "EXTRA":     "Extra",
}
DIA_SEMANA   = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MESES = [
    (1, "Janeiro"),   (2, "Fevereiro"), (3, "Março"),    (4, "Abril"),
    (5, "Maio"),      (6, "Junho"),     (7, "Julho"),    (8, "Agosto"),
    (9, "Setembro"), (10, "Outubro"),  (11, "Novembro"), (12, "Dezembro"),
]
_NOME_MES = {n: nome for n, nome in MESES}

_COR_FDS = ft.Colors.with_opacity(0.07, ft.Colors.BLUE)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _card(titulo: str, *controls) -> ft.Card:
    return ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(height=1),
                *controls,
            ],
        ),
    ))


def _linha_hol(descricao: str, valor: float,
               negativo: bool = False,
               bold: bool = False,
               grande: bool = False) -> ft.Row:
    tamanho = 16 if grande else 14
    peso    = ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL
    if negativo:
        cor, sinal = ft.Colors.RED_400, "−"
    elif bold:
        cor, sinal = ft.Colors.GREEN_300, ""
    else:
        cor, sinal = None, "+"
    return ft.Row(
        controls=[
            ft.Text(descricao, expand=True, size=tamanho, weight=peso),
            ft.Text(
                f"{sinal}R$ {abs(valor):.2f}",
                size=tamanho, weight=peso, color=cor,
                text_align=ft.TextAlign.RIGHT,
            ),
        ],
        spacing=16,
    )


def _mini_tabela(colunas: list, linhas: list) -> ft.Row:
    """Tabela compacta para as seções de detalhamento."""
    if not linhas:
        linhas = [ft.DataRow(cells=[
            ft.DataCell(ft.Text("Sem registros.", italic=True, color=ft.Colors.GREY_500)),
            *[ft.DataCell(ft.Text("")) for _ in range(len(colunas) - 1)],
        ])]
    return ft.Row(
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text(c, size=12)) for c in colunas],
                rows=linhas,
                column_spacing=14,
                data_row_min_height=32,
                data_row_max_height=40,
                horizontal_lines=ft.BorderSide(
                    1, ft.Colors.with_opacity(0.15, ft.Colors.BLACK)
                ),
            )
        ],
    )


# ── View principal ────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    hoje       = date.today()
    pessoas_db = database.pessoa_listar(tipo="INTERNO", apenas_ativos=True)

    dd_funcionario = ft.Dropdown(
        label="Funcionário",
        width=260,
        options=[
            ft.dropdown.Option(key=str(p["id"]), text=p["nome"])
            for p in pessoas_db
        ],
        hint_text="Sem funcionários internos" if not pessoas_db else None,
    )

    dd_mes = ft.Dropdown(
        label="Mês",
        width=155,
        value=str(hoje.month),
        options=[
            ft.dropdown.Option(key=str(n), text=nome)
            for n, nome in MESES
        ],
    )

    tf_ano = ft.TextField(
        label="Ano",
        value=str(hoje.year),
        width=90,
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.CENTER,
    )

    # ── DatePicker para seleção rápida de mês ─────────────────────────────
    def _on_date_picked(e):
        if e.control.value:
            picked = e.control.value
            dd_mes.value = str(picked.month)
            tf_ano.value = str(picked.year)
            page.update()

    date_picker = ft.DatePicker(on_change=_on_date_picked)
    page.overlay.append(date_picker)

    btn_calendario = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar mês pelo calendário",
        on_click=lambda e: (setattr(date_picker, "open", True), page.update()),
    )

    col_conteudo   = ft.Column(spacing=16)
    _holerite_dados: dict = {}

    # ─────────────────────────────────────────────────────────────────────
    def _carregar(e=None):
        if not dd_funcionario.value:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Selecione um funcionário."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return

        id_func = int(dd_funcionario.value)
        mes     = int(dd_mes.value or hoje.month)
        try:
            ano = int(tf_ano.value or hoje.year)
        except ValueError:
            ano = hoje.year

        func = database.pessoa_buscar(id_func)
        if not func:
            return

        ultimo_dia   = calendar.monthrange(ano, mes)[1]
        data_ini_iso = f"{ano:04d}-{mes:02d}-01"
        data_fim_iso = f"{ano:04d}-{mes:02d}-{ultimo_dia:02d}"
        mes_ano_txt  = f"{_NOME_MES[mes]} {ano}"

        # Escala existente no período
        escalas    = database.escala_listar_por_pessoa(id_func, data_ini_iso, data_fim_iso)
        escala_map = {row["data"]: row["tipo"] for row in escalas}

        # ══════════════════════════════════════════════════════════════
        #  BLOCO 1 — Grade de escala do mês
        # ══════════════════════════════════════════════════════════════
        semanas = calendar.monthcalendar(ano, mes)

        cabecalho = ft.Row(
            spacing=4,
            controls=[
                ft.Container(
                    width=136, height=30,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(
                        d, size=12, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_300 if i >= 5 else ft.Colors.GREY_500,
                    ),
                )
                for i, d in enumerate(DIA_SEMANA)
            ],
        )

        linhas_grade = [cabecalho]

        for semana in semanas:
            celulas = []
            for i_col, dia in enumerate(semana):
                eh_fds = i_col >= 5

                if dia == 0:
                    celulas.append(ft.Container(width=136, height=90))
                    continue

                data_iso   = f"{ano:04d}-{mes:02d}-{dia:02d}"
                tipo_atual = escala_map.get(data_iso)

                def _on_sel(ev, _data=data_iso, _id=id_func):
                    novo = ev.control.value
                    if novo:
                        database.escala_registrar(_data, _id, novo)
                    else:
                        database.escala_excluir(_data, _id)

                dd_cel = ft.Dropdown(
                    value=tipo_atual,
                    options=[
                        ft.dropdown.Option(key="", text="—"),
                        *[ft.dropdown.Option(key=t, text=_ABREV.get(t, t))
                          for t in TIPOS_ESCALA],
                    ],
                    on_select=_on_sel,
                    width=132,
                    text_size=11,
                )

                celulas.append(ft.Container(
                    width=136, height=90,
                    padding=ft.Padding.all(4),
                    bgcolor=_COR_FDS if eh_fds else None,
                    border_radius=4,
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                str(dia), size=12, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_300 if eh_fds else ft.Colors.GREY_500,
                            ),
                            dd_cel,
                        ],
                    ),
                ))

            linhas_grade.append(ft.Row(controls=celulas, spacing=4))

        bloco1 = _card(
            "Escala do Mês",
            ft.Row(
                scroll=ft.ScrollMode.AUTO,
                controls=[ft.Column(spacing=4, controls=linhas_grade)],
            ),
        )

        # ══════════════════════════════════════════════════════════════
        #  BLOCO 2 — Holerite
        # ══════════════════════════════════════════════════════════════
        conn = database.conectar()
        try:
            def _contar(tipo_esc: str) -> int:
                return conn.execute(
                    """SELECT COUNT(*) FROM escalas_trabalho
                       WHERE id_pessoa = ? AND data BETWEEN ? AND ? AND tipo = ?""",
                    (id_func, data_ini_iso, data_fim_iso, tipo_esc)
                ).fetchone()[0]

            dias_trabalhou = _contar("TRABALHOU")
            dias_falta     = _contar("FALTA")
            dias_extra     = _contar("EXTRA")
            dias_feriado   = _contar("FERIADO")

            r_vales = conn.execute("""
                SELECT COALESCE(SUM(me.valor), 0) AS total
                FROM movimentacoes_extras me
                JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                WHERE me.id_pessoa = ? AND me.data BETWEEN ? AND ?
                  AND ce.descricao = 'Vale'
            """, (id_func, data_ini_iso, data_fim_iso)).fetchone()

            r_consumos = conn.execute("""
                SELECT COALESCE(SUM(me.valor), 0) AS total
                FROM movimentacoes_extras me
                JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                WHERE me.id_pessoa = ? AND me.data BETWEEN ? AND ?
                  AND ce.descricao = 'Consumo'
            """, (id_func, data_ini_iso, data_fim_iso)).fetchone()

            # ── Detalhamento: vales ───────────────────────────────────
            rows_vales_det = conn.execute("""
                SELECT me.data, me.valor, me.obs
                FROM movimentacoes_extras me
                JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                WHERE me.id_pessoa = ? AND me.data BETWEEN ? AND ?
                  AND ce.descricao = 'Vale'
                ORDER BY me.data
            """, (id_func, data_ini_iso, data_fim_iso)).fetchall()

            # ── Detalhamento: consumos ────────────────────────────────
            rows_consumos_det = conn.execute("""
                SELECT me.data, me.valor, me.obs
                FROM movimentacoes_extras me
                JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                WHERE me.id_pessoa = ? AND me.data BETWEEN ? AND ?
                  AND ce.descricao = 'Consumo'
                ORDER BY me.data
            """, (id_func, data_ini_iso, data_fim_iso)).fetchall()

            # ── Detalhamento: ocorrências de escala ───────────────────
            rows_ocorr = conn.execute("""
                SELECT data, tipo FROM escalas_trabalho
                WHERE id_pessoa = ? AND data BETWEEN ? AND ?
                  AND tipo NOT IN ('TRABALHOU', 'FOLGA')
                ORDER BY data
            """, (id_func, data_ini_iso, data_fim_iso)).fetchall()

            # ── id da categoria Pagamento ─────────────────────────────
            row_cat_pag = conn.execute(
                "SELECT id FROM cad_categorias_extra WHERE descricao = 'Pagamento'"
            ).fetchone()
            id_cat_pagamento = row_cat_pag["id"] if row_cat_pag else None

            # Verifica se salário do mês já foi registrado
            ja_pago = False
            if id_cat_pagamento:
                row_chk = conn.execute(
                    """SELECT COUNT(*) FROM movimentacoes_extras
                       WHERE id_pessoa = ? AND id_categoria = ?
                         AND data BETWEEN ? AND ?""",
                    (id_func, id_cat_pagamento, data_ini_iso, data_fim_iso)
                ).fetchone()
                ja_pago = row_chk[0] > 0

        finally:
            conn.close()

        soma_vales    = r_vales["total"]    if r_vales    else 0.0
        soma_consumos = r_consumos["total"] if r_consumos else 0.0

        try:
            valor_extra   = func["valor_extra"]   or 50.0
            valor_feriado = func["valor_feriado"] or 60.0
            valor_falta   = func["valor_falta"]   or 60.0
        except (IndexError, KeyError):
            valor_extra, valor_feriado, valor_falta = 50.0, 60.0, 60.0

        tipo_sal = func["tipo_salario"] or "FIXO"
        if tipo_sal == "DIARIO":
            dias_pagos = dias_trabalhou + dias_extra + dias_feriado
            diaria     = func["diaria_valor"] or 0.0
            base       = dias_pagos * diaria
            desc_base  = f"Salário diário: {dias_pagos} dias × R$ {diaria:.2f}"
        else:
            base      = func["salario_base"] or 0.0
            desc_base = "Salário base mensal"

        val_extras   = dias_extra   * valor_extra
        val_feriados = dias_feriado * valor_feriado
        val_faltas   = dias_falta   * valor_falta
        val_consumos = soma_consumos * 0.8

        total_liquido = base + val_extras + val_feriados - val_faltas - soma_vales - val_consumos

        _holerite_dados.update({
            "funcionario":    func["nome"],
            "mes_ano":        f"{mes:02d}/{ano}",
            "desc_base":      desc_base,
            "base":           base,
            "dias_trabalhou": dias_trabalhou,
            "dias_extra":     dias_extra,   "valor_extra":   valor_extra,   "val_extras":   val_extras,
            "dias_feriado":   dias_feriado, "valor_feriado": valor_feriado, "val_feriados": val_feriados,
            "dias_falta":     dias_falta,   "valor_falta":   valor_falta,   "val_faltas":   val_faltas,
            "soma_vales":     soma_vales,
            "soma_consumos":  soma_consumos, "val_consumos": val_consumos,
            "total_liquido":  total_liquido,
            "_vales_export": [
                {"data": v["data"][8:10] + "/" + v["data"][5:7],
                 "valor": v["valor"], "obs": v["obs"] or ""}
                for v in rows_vales_det
            ],
            "_consumos_export": [
                {"data": c["data"][8:10] + "/" + c["data"][5:7],
                 "valor": c["valor"], "desconto": c["valor"] * 0.8,
                 "obs": c["obs"] or ""}
                for c in rows_consumos_det
            ],
            "_ocorr_export": [
                {"data": o["data"][8:10] + "/" + o["data"][5:7], "tipo": o["tipo"]}
                for o in rows_ocorr
            ],
        })

        # ── Linhas do holerite ────────────────────────────────────────
        linhas_hol = [_linha_hol(desc_base, base)]
        if dias_extra > 0:
            linhas_hol.append(_linha_hol(
                f"Extras: {dias_extra} dia(s) × R$ {valor_extra:.2f}", val_extras,
            ))
        if dias_feriado > 0:
            linhas_hol.append(_linha_hol(
                f"Feriados trabalhados: {dias_feriado} × R$ {valor_feriado:.2f}", val_feriados,
            ))
        if dias_falta > 0:
            linhas_hol.append(_linha_hol(
                f"Faltas: {dias_falta} × R$ {valor_falta:.2f}", val_faltas, negativo=True,
            ))
        if soma_vales > 0:
            linhas_hol.append(_linha_hol(
                "Vales / Adiantamentos", soma_vales, negativo=True,
            ))
        if soma_consumos > 0:
            linhas_hol.append(_linha_hol(
                f"Consumos (80% de R$ {soma_consumos:.2f})", val_consumos, negativo=True,
            ))

        linhas_hol += [
            ft.Divider(height=1),
            _linha_hol("TOTAL LÍQUIDO", total_liquido, bold=True, grande=True),
        ]

        # ── Botão Registrar Pagamento do Mês ─────────────────────────
        if ja_pago:
            btn_registrar = ft.ElevatedButton(
                "Salário já registrado",
                icon=ft.Icons.CHECK,
                disabled=True,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.GREY_700,
                    color=ft.Colors.GREY_400,
                ),
            )
        else:
            def _registrar_pagamento_mes(ev,
                                         _id=id_func,
                                         _nome=func["nome"],
                                         _total=total_liquido,
                                         _id_cat=id_cat_pagamento,
                                         _data=data_fim_iso,
                                         _mes_ano=mes_ano_txt):
                if _total <= 0:
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text("Total líquido R$ 0,00 — nada a registrar."),
                        bgcolor=ft.Colors.ORANGE_700, open=True,
                    ))
                    page.update()
                    return
                if _id_cat is None:
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text("Categoria 'Pagamento' não encontrada."),
                        bgcolor=ft.Colors.RED_700, open=True,
                    ))
                    page.update()
                    return
                database.mov_extra_inserir(
                    data=_data,
                    id_categoria=_id_cat,
                    fluxo="SAIDA",
                    valor=_total,
                    id_pessoa=_id,
                    metodo="Dinheiro",
                    obs=f"Salário {_nome} {_mes_ano}",
                )
                database.log_registrar(
                    acao="PAGAMENTO_FUNCIONARIO",
                    tabela="movimentacoes_extras",
                    descricao=f"Salário registrado — {_nome}: "
                              f"R$ {_total:.2f} | {_mes_ano}",
                )
                page.overlay.append(ft.SnackBar(
                    content=ft.Text(
                        f"Pagamento de {_nome} registrado: R$ {_total:.2f}"
                    ),
                    bgcolor=ft.Colors.GREEN_700, open=True,
                ))
                _carregar()   # recarrega (já chama page.update)

            btn_registrar = ft.ElevatedButton(
                "Registrar Pagamento do Mês",
                icon=ft.Icons.PAYMENTS,
                on_click=_registrar_pagamento_mes,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.TEAL_700,
                    color=ft.Colors.WHITE,
                ),
            )

        # ── Tabelas de Detalhamento ───────────────────────────────────

        # Vales
        linhas_vales = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(v["data"][8:10] + "/" + v["data"][5:7])),
                ft.DataCell(ft.Text(f"R$ {v['valor']:.2f}", color=ft.Colors.RED_300)),
                ft.DataCell(ft.Text(v["obs"] or "")),
            ])
            for v in rows_vales_det
        ]

        # Consumos
        linhas_consumos = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["data"][8:10] + "/" + c["data"][5:7])),
                ft.DataCell(ft.Text(f"R$ {c['valor']:.2f}")),
                ft.DataCell(ft.Text(f"R$ {c['valor'] * 0.8:.2f}", color=ft.Colors.RED_300)),
                ft.DataCell(ft.Text(c["obs"] or "")),
            ])
            for c in rows_consumos_det
        ]

        # Ocorrências de escala
        def _impacto_ocorr(tipo: str) -> tuple:
            if tipo == "FALTA":
                return f"− R$ {valor_falta:.2f}", ft.Colors.RED_400
            if tipo == "EXTRA":
                return f"+ R$ {valor_extra:.2f}", ft.Colors.GREEN_400
            if tipo == "FERIADO":
                return f"+ R$ {valor_feriado:.2f}", ft.Colors.BLUE_300
            return "—", None

        linhas_ocorr = []
        for o in rows_ocorr:
            impacto_txt, impacto_cor = _impacto_ocorr(o["tipo"])
            linhas_ocorr.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(o["data"][8:10] + "/" + o["data"][5:7])),
                ft.DataCell(ft.Text(o["tipo"])),
                ft.DataCell(ft.Text(impacto_txt, color=impacto_cor)),
            ]))

        secao_det = ft.Column(
            spacing=12,
            controls=[
                ft.Divider(height=1),
                ft.Text("Detalhamento", size=15, weight=ft.FontWeight.BOLD,
                        color=None),
                ft.Text("Vales e Adiantamentos", size=13, color=ft.Colors.GREY_500),
                _mini_tabela(["Data", "Valor", "Obs"], linhas_vales),
                ft.Text("Consumos", size=13, color=ft.Colors.GREY_500),
                _mini_tabela(
                    ["Data", "Valor Original", "Desconto (80%)", "Obs"],
                    linhas_consumos,
                ),
                ft.Text("Ocorrências de Escala", size=13, color=ft.Colors.GREY_500),
                _mini_tabela(["Data", "Tipo", "Impacto"], linhas_ocorr),
            ],
        )

        # ══════════════════════════════════════════════════════════════
        #  SEÇÃO PONTO — apenas para FIXO e DIARIO (não ENTREGADOR)
        # ══════════════════════════════════════════════════════════════
        secao_ponto = None
        if tipo_sal != "ENTREGADOR":
            try:
                ch_diaria = float(func["carga_horaria_diaria"] or 8.0)
            except Exception:
                ch_diaria = 8.0

            resumo_pt = database.ponto_resumo_mensal(
                id_func,
                data_ini_iso,
                data_fim_iso,
                salario_base=func["salario_base"] or 0.0,
                diaria_valor=func["diaria_valor"] or 0.0,
                tipo_salario=tipo_sal,
                carga_horaria=ch_diaria,
            )

            # Cards de resumo
            def _card_pt(titulo, valor_str, cor):
                return ft.Container(
                    content=ft.Column(
                        spacing=2, tight=True,
                        controls=[
                            ft.Text(titulo, size=11, color=ft.Colors.GREY_500),
                            ft.Text(valor_str, size=15,
                                    weight=ft.FontWeight.BOLD, color=cor),
                        ],
                    ),
                    bgcolor=None,
                    border_radius=8,
                    padding=ft.Padding.all(10),
                )

            valor_ext_str = (
                f"R$ {resumo_pt['valor_total_extras']:.2f}"
                if resumo_pt["valor_hora_normal"] > 0
                else "—"
            )
            cards_resumo = ft.Row(
                spacing=10,
                wrap=True,
                controls=[
                    _card_pt("Dias c/ ponto",
                             str(resumo_pt["dias_com_ponto"]),
                             ft.Colors.GREY_500),
                    _card_pt("Jornadas completas",
                             str(resumo_pt["dias_completos"]),
                             ft.Colors.GREY_500),
                    _card_pt("Horas trabalhadas",
                             f"{resumo_pt['total_horas_liquidas']:.1f}h",
                             ft.Colors.BLUE_300),
                    _card_pt("Horas extras",
                             f"+{resumo_pt['total_horas_extras']:.1f}h",
                             ft.Colors.GREEN_400 if resumo_pt["total_horas_extras"] > 0
                             else ft.Colors.GREY_600),
                    _card_pt("Horas faltantes",
                             f"-{resumo_pt['total_horas_faltantes']:.1f}h",
                             ft.Colors.ORANGE_400 if resumo_pt["total_horas_faltantes"] > 0
                             else ft.Colors.GREY_600),
                    _card_pt("Valor est. extras (info)",
                             valor_ext_str,
                             ft.Colors.YELLOW_600),
                ],
            )

            # Tabela de detalhamento por dia
            dias_com_escala = {
                row["data"]
                for row in database.escala_listar_por_pessoa(
                    id_func, data_ini_iso, data_fim_iso
                )
                if row["tipo"] in ("TRABALHOU", "EXTRA")
            }

            linhas_ponto = []
            for det in resumo_pt["detalhes"]:
                if det["data"] not in dias_com_escala:
                    continue
                data_br = det["data"][8:10] + "/" + det["data"][5:7]
                ent_str = det["hora_entrada"] or "—"
                sai_str = det["hora_saida"]   or "—"
                int_str = (
                    f"{det['hora_ini_int']}–{det['hora_fim_int']}"
                    if det["hora_ini_int"] and det["hora_fim_int"]
                    else f"{det['minutos_intervalo']}min" if det["completo"] else "—"
                )
                bru_str = f"{det['horas_brutas']:.1f}h"   if det["completo"] else "—"
                liq_str = f"{det['horas_liquidas']:.1f}h" if det["completo"] else "—"

                if not det["hora_entrada"]:
                    ext_txt, ext_cor = "—", ft.Colors.GREY_600
                elif not det["hora_saida"]:
                    ext_txt, ext_cor = "Incompleto", ft.Colors.GREY_500
                elif det["horas_extras"] > 0:
                    ext_txt, ext_cor = f"+{det['horas_extras']:.1f}h", ft.Colors.GREEN_400
                elif det["horas_extras"] < 0:
                    ext_txt, ext_cor = f"{det['horas_extras']:.1f}h", ft.Colors.ORANGE_400
                else:
                    ext_txt, ext_cor = "Cumprida", ft.Colors.GREEN_300

                linhas_ponto.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(data_br, size=12)),
                    ft.DataCell(ft.Text(ent_str, size=12)),
                    ft.DataCell(ft.Text(sai_str, size=12)),
                    ft.DataCell(ft.Text(int_str, size=12)),
                    ft.DataCell(ft.Text(bru_str, size=12)),
                    ft.DataCell(ft.Text(liq_str, size=12)),
                    ft.DataCell(ft.Text(
                        ext_txt, size=12,
                        weight=ft.FontWeight.BOLD if det.get("horas_extras", 0) > 0
                        else ft.FontWeight.NORMAL,
                        color=ext_cor,
                    )),
                ]))

            nota_ponto = ft.Text(
                "Cálculo: (Saída − Entrada) − 1h intervalo padrão. "
                "Hora extra = valor/hora × 150%. "
                "Valor hora = Salário ÷ 220 (fixo) ou Diária ÷ 8h (diário). "
                "Os valores de horas extras são apenas informativos.",
                size=11,
                italic=True,
                color=ft.Colors.GREY_500,
            )

            secao_ponto = ft.Column(
                spacing=12,
                controls=[
                    ft.Divider(height=1),
                    ft.Text("Controle de Ponto", size=15,
                            weight=ft.FontWeight.BOLD, color=None),
                    cards_resumo,
                    _mini_tabela(
                        ["Data", "Entrada", "Saída", "Intervalo",
                         "H. Brutas", "H. Líquidas", "Extras/Faltantes"],
                        linhas_ponto,
                    ),
                    nota_ponto,
                ],
            )

        bloco2 = _card(
            "Holerite do Mês",
            *linhas_hol,
            ft.Row(spacing=12, controls=[
                ft.ElevatedButton(
                    "Exportar CSV",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=_exportar_csv,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO_600,
                        color=ft.Colors.WHITE,
                    ),
                ),
                ft.ElevatedButton(
                    "Excel",
                    icon=ft.Icons.TABLE_VIEW,
                    on_click=_exportar_excel,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.GREEN_800,
                        color=ft.Colors.WHITE,
                    ),
                ),
                ft.ElevatedButton(
                    "PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=_exportar_pdf,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_800,
                        color=ft.Colors.WHITE,
                    ),
                ),
                btn_registrar,
            ]),
            secao_det,
            *([] if secao_ponto is None else [secao_ponto]),
        )

        col_conteudo.controls.clear()
        col_conteudo.controls += [bloco1, bloco2]
        page.update()

    def _carregar_seguro(e=None):
        try:
            _carregar(e)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            col_conteudo.controls.clear()
            col_conteudo.controls.append(ft.Text(
                f"Erro ao carregar: {exc}",
                color=ft.Colors.RED_400, selectable=True,
            ))
            page.update()

    # ── Exportar CSV ──────────────────────────────────────────────────────

    def _exportar_csv(e):
        if not _holerite_dados:
            return

        os.makedirs("exports", exist_ok=True)
        nome    = _holerite_dados["funcionario"].replace(" ", "_")
        mesano  = _holerite_dados["mes_ano"].replace("/", "")
        caminho = os.path.join("exports", f"holerite_{nome}_{mesano}.csv")

        d = _holerite_dados
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Funcionário", d["funcionario"]])
            w.writerow(["Mês/Ano",     d["mes_ano"]])
            w.writerow([])
            w.writerow(["Descrição", "Valor (R$)"])
            w.writerow([d["desc_base"], f"{d['base']:.2f}"])
            if d["dias_extra"] > 0:
                w.writerow([
                    f"Extras: {d['dias_extra']} × R$ {d['valor_extra']:.2f}",
                    f"+{d['val_extras']:.2f}",
                ])
            if d["dias_feriado"] > 0:
                w.writerow([
                    f"Feriados: {d['dias_feriado']} × R$ {d['valor_feriado']:.2f}",
                    f"+{d['val_feriados']:.2f}",
                ])
            if d["dias_falta"] > 0:
                w.writerow([
                    f"Faltas: {d['dias_falta']} × R$ {d['valor_falta']:.2f}",
                    f"-{d['val_faltas']:.2f}",
                ])
            if d["soma_vales"] > 0:
                w.writerow(["Vales / Adiantamentos", f"-{d['soma_vales']:.2f}"])
            if d["soma_consumos"] > 0:
                w.writerow([
                    f"Consumos (80% de R$ {d['soma_consumos']:.2f})",
                    f"-{d['val_consumos']:.2f}",
                ])
            w.writerow(["TOTAL LÍQUIDO", f"{d['total_liquido']:.2f}"])

        page.overlay.append(ft.SnackBar(
            content=ft.Text(f"Holerite exportado: {caminho}"),
            bgcolor=ft.Colors.GREEN_700, open=True,
        ))
        page.update()

    def _holerite_para_dados() -> dict:
        """Converte _holerite_dados para o formato esperado pelas funções de exportação."""
        d = _holerite_dados
        resumo = [{"descricao": d["desc_base"], "valor": d["base"], "tipo": "receita"}]
        if d.get("val_extras", 0) > 0:
            resumo.append({
                "descricao": f"Extras: {d['dias_extra']} dia(s) × R$ {d['valor_extra']:.2f}",
                "valor": d["val_extras"], "tipo": "receita",
            })
        if d.get("val_feriados", 0) > 0:
            resumo.append({
                "descricao": f"Feriados trabalhados: {d['dias_feriado']} × R$ {d['valor_feriado']:.2f}",
                "valor": d["val_feriados"], "tipo": "receita",
            })
        if d.get("val_faltas", 0) > 0:
            resumo.append({
                "descricao": f"Faltas: {d['dias_falta']} × R$ {d['valor_falta']:.2f}",
                "valor": d["val_faltas"], "tipo": "desconto",
            })
        if d.get("soma_vales", 0) > 0:
            resumo.append({"descricao": "Vales / Adiantamentos", "valor": d["soma_vales"], "tipo": "desconto"})
        if d.get("soma_consumos", 0) > 0:
            resumo.append({
                "descricao": f"Consumos (80% de R$ {d['soma_consumos']:.2f})",
                "valor": d["val_consumos"], "tipo": "desconto",
            })
        resumo.append({"descricao": "TOTAL LÍQUIDO", "valor": d["total_liquido"], "tipo": "total"})
        return {
            "resumo":      resumo,
            "vales":       d.get("_vales_export", []),
            "consumos":    d.get("_consumos_export", []),
            "ocorrencias": d.get("_ocorr_export", []),
            "ponto":       [],
        }

    def _exportar_excel(e):
        if not _holerite_dados:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o relatório antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            d = _holerite_dados
            caminho = excel_holerite(d["funcionario"], d["mes_ano"], _holerite_para_dados())
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

    def _exportar_pdf(e):
        if not _holerite_dados:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o relatório antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            d = _holerite_dados
            caminho = gerar_pdf_holerite(d["funcionario"], d["mes_ano"], _holerite_para_dados())
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

    # ── Layout ────────────────────────────────────────────────────────────

    btn_carregar = ft.ElevatedButton(
        "Carregar",
        icon=ft.Icons.REFRESH,
        on_click=_carregar_seguro,
        style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE),
    )

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
        controls=[
            ft.Row(
                controls=[dd_funcionario, dd_mes, tf_ano, btn_calendario, btn_carregar],
                spacing=8,
                wrap=True,
            ),
            ft.Text(
                "Selecione o funcionário, mês e ano e clique em Carregar.",
                color=ft.Colors.GREY_500, italic=True, size=12,
            ),
            ft.Divider(height=1),
            col_conteudo,
        ],
    )
