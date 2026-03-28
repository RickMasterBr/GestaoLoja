"""
views/entregadores.py — Painel diário de entregadores.
Exibe resumo do dia, acumulado da semana e histórico de corridas extras/reentregas.
"""

import os
from datetime import date, timedelta

import flet as ft

import database
from relatorios.pdf_gerador import gerar_pdf_entregadores, abrir_pdf
from relatorios.excel_gerador import excel_entregadores


# ── Helpers ───────────────────────────────────────────────────────────────────

def _data_br_para_iso(s: str) -> str:
    try:
        d, m, a = s.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


def _data_iso_para_br(s: str) -> str:
    try:
        a, m, d = s.split("-")
        return f"{d}/{m}/{a}"
    except Exception:
        return s


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


def _tabela(colunas: list, linhas: list) -> ft.Row:
    return ft.Row(
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text(c)) for c in colunas],
                rows=linhas,
                column_spacing=16,
                horizontal_lines=ft.BorderSide(
                    1, ft.Colors.with_opacity(0.15, ft.Colors.BLACK)
                ),
            )
        ],
    )


def _semvazio(linhas: list, n_colunas: int) -> list:
    if linhas:
        return linhas
    return [ft.DataRow(cells=[
        ft.DataCell(ft.Text("Sem dados.", italic=True, color=ft.Colors.GREY_500)),
        *[ft.DataCell(ft.Text("")) for _ in range(n_colunas - 1)],
    ])]


def _id_categoria(conn, descricao: str):
    """Busca o id de uma categoria pelo nome exato usando conexão existente."""
    row = conn.execute(
        "SELECT id FROM cad_categorias_extra WHERE descricao = ?", (descricao,)
    ).fetchone()
    return row["id"] if row else None


# ── View principal ────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    hoje_br = date.today().strftime("%d/%m/%Y")

    tf_data = ft.TextField(
        label="Data",
        value=hoje_br,
        width=160,
        text_align=ft.TextAlign.CENTER,
        hint_text="DD/MM/AAAA",
    )

    def _on_date_picked(e):
        if e.control.value:
            tf_data.value = e.control.value.strftime("%d/%m/%Y")
            page.update()

    date_picker = ft.DatePicker(on_change=_on_date_picked)
    page.overlay.append(date_picker)

    btn_calendario = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar data",
        on_click=lambda e: (setattr(date_picker, "open", True), page.update()),
    )

    col_conteudo = ft.Column(spacing=16)
    _dados_export: dict = {}

    # ─────────────────────────────────────────────────────────────────────
    def _carregar(e=None):
        data_iso = _data_br_para_iso(tf_data.value or hoje_br)
        data_br  = _data_iso_para_br(data_iso)

        entregadores = database.pessoa_listar(tipo="ENTREGADOR", apenas_ativos=True)

        dt_fim  = date.fromisoformat(data_iso)
        dt_ini  = dt_fim - timedelta(days=6)
        ini_iso = dt_ini.isoformat()
        ini_br  = dt_ini.strftime("%d/%m")
        fim_br  = dt_fim.strftime("%d/%m")

        conn = database.conectar()
        try:
            id_cat_pagamento = _id_categoria(conn, "Pagamento")

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 1 — Painel do Dia
            # ══════════════════════════════════════════════════════════════
            colunas_b1 = [
                "Nome", "Entregas", "Soma Taxas", "Diária",
                "Corridas Extra", "Vales", "Total a Pagar", "Ação",
            ]
            linhas_b1 = []
            _dia_lista = []

            for ent in entregadores:
                r = database.calcular_pagamento_entregador(ent["id"], data_iso)

                # Verifica se pagamento já foi registrado hoje para este entregador
                ja_pago = False
                if id_cat_pagamento:
                    row_chk = conn.execute(
                        """SELECT COUNT(*) FROM movimentacoes_extras
                           WHERE data = ? AND id_pessoa = ? AND id_categoria = ?""",
                        (data_iso, ent["id"], id_cat_pagamento)
                    ).fetchone()
                    ja_pago = row_chk[0] > 0

                if ja_pago:
                    btn_pagar = ft.TextButton(
                        "Pago",
                        icon=ft.Icons.CHECK,
                        disabled=True,
                        style=ft.ButtonStyle(color=ft.Colors.GREY_500),
                    )
                else:
                    def _registrar_pagamento(ev,
                                             _id=ent["id"],
                                             _nome=ent["nome"],
                                             _total=r["total_liquido"],
                                             _data=data_iso,
                                             _data_br=data_br,
                                             _id_cat=id_cat_pagamento):
                        if _total <= 0:
                            page.overlay.append(ft.SnackBar(
                                content=ft.Text(f"{_nome}: total R$ 0,00, nada a pagar."),
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
                            obs=f"Pagamento entregador {_data_br}",
                        )
                        page.overlay.append(ft.SnackBar(
                            content=ft.Text(
                                f"Pagamento de {_nome} registrado: R$ {_total:.2f}"
                            ),
                            bgcolor=ft.Colors.GREEN_700, open=True,
                        ))
                        _carregar()   # recarrega a tabela (já chama page.update)

                    btn_pagar = ft.TextButton(
                        "Registrar",
                        icon=ft.Icons.PAYMENTS,
                        on_click=_registrar_pagamento,
                        style=ft.ButtonStyle(color=ft.Colors.TEAL_300),
                    )

                linhas_b1.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(ent["nome"])),
                    ft.DataCell(ft.Text(str(r["total_entregas"]))),
                    ft.DataCell(ft.Text(f"R$ {r['soma_taxas']:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {r['diaria']:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {r['corridas_extras']:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {r['vales']:.2f}")),
                    ft.DataCell(ft.Text(
                        f"R$ {r['total_liquido']:.2f}",
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_300,
                    )),
                    ft.DataCell(btn_pagar),
                ]))
                _dia_lista.append({
                    "nome": ent["nome"],
                    "entregas": r["total_entregas"],
                    "soma_taxas": r["soma_taxas"],
                    "diaria": r["diaria"],
                    "corridas_extras": r["corridas_extras"],
                    "vales": r["vales"],
                    "total_a_pagar": r["total_liquido"],
                })

            # Total de taxas do dia (apenas canais com entregador próprio)
            row_taxas_dia = conn.execute("""
                SELECT COALESCE(SUM(p.taxa_entrega), 0) AS total
                FROM vendas_pedidos p
                LEFT JOIN cad_canais c ON c.nome = p.canal
                WHERE p.data = ?
                  AND COALESCE(c.entregador_plataforma, 0) = 0
            """, (data_iso,)).fetchone()
            total_taxas_dia = row_taxas_dia["total"] if row_taxas_dia else 0.0

            bloco1 = _card(
                f"Painel do Dia — {data_br}",
                _tabela(colunas_b1, _semvazio(linhas_b1, len(colunas_b1))),
                ft.Divider(height=1),
                ft.Text(
                    f"Total de taxas de entrega recebidas no dia: R$ {total_taxas_dia:.2f}",
                    size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300,
                ),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 2 — Acumulado da Semana (7 dias até a data selecionada)
            # ══════════════════════════════════════════════════════════════
            linhas_b2 = []
            _semana_lista = []
            for ent in entregadores:
                row_entr = conn.execute(
                    """SELECT COUNT(*) AS qtd,
                              COALESCE(SUM(repasse_entregador), 0) AS soma_taxas
                       FROM vendas_pedidos
                       WHERE data BETWEEN ? AND ?
                         AND id_operador = ? AND repasse_entregador > 0""",
                    (ini_iso, data_iso, ent["id"])
                ).fetchone()

                qtd_sem      = row_entr["qtd"]
                soma_taxas_s = row_entr["soma_taxas"]

                dias_com_entrega = conn.execute(
                    """SELECT COUNT(DISTINCT data) AS dias
                       FROM vendas_pedidos
                       WHERE data BETWEEN ? AND ?
                         AND id_operador = ? AND repasse_entregador > 0""",
                    (ini_iso, data_iso, ent["id"])
                ).fetchone()["dias"]

                try:
                    diaria_val = ent["diaria_valor"] or 0.0
                    tipo_sal   = ent["tipo_salario"]
                    if tipo_sal == "ENTREGADOR" and diaria_val == 0.0:
                        diaria_val = 40.0
                except (IndexError, KeyError):
                    diaria_val = 40.0

                diarias_s = dias_com_entrega * diaria_val

                row_extras = conn.execute(
                    """SELECT COALESCE(SUM(me.valor), 0) AS total
                       FROM movimentacoes_extras me
                       JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                       WHERE me.data BETWEEN ? AND ?
                         AND me.id_pessoa = ? AND ce.descricao = 'Corrida Extra'""",
                    (ini_iso, data_iso, ent["id"])
                ).fetchone()

                row_vales = conn.execute(
                    """SELECT COALESCE(SUM(me.valor), 0) AS total
                       FROM movimentacoes_extras me
                       JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                       WHERE me.data BETWEEN ? AND ?
                         AND me.id_pessoa = ? AND ce.descricao = 'Vale'""",
                    (ini_iso, data_iso, ent["id"])
                ).fetchone()

                extras_s = row_extras["total"] if row_extras else 0.0
                vales_s  = row_vales["total"]  if row_vales  else 0.0
                total_s  = diarias_s + soma_taxas_s + extras_s - vales_s

                linhas_b2.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(ent["nome"])),
                    ft.DataCell(ft.Text(str(qtd_sem))),
                    ft.DataCell(ft.Text(f"R$ {soma_taxas_s:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {diarias_s:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {extras_s:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {vales_s:.2f}")),
                    ft.DataCell(ft.Text(
                        f"R$ {total_s:.2f}",
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_300,
                    )),
                ]))
                _semana_lista.append({
                    "nome": ent["nome"],
                    "entregas": qtd_sem,
                    "soma_taxas": soma_taxas_s,
                    "diaria": diarias_s,
                    "corridas_extras": extras_s,
                    "vales": vales_s,
                    "total_a_pagar": total_s,
                })

            # Total de taxas da semana (apenas canais com entregador próprio)
            row_taxas_sem = conn.execute("""
                SELECT COALESCE(SUM(p.taxa_entrega), 0) AS total
                FROM vendas_pedidos p
                LEFT JOIN cad_canais c ON c.nome = p.canal
                WHERE p.data BETWEEN ? AND ?
                  AND COALESCE(c.entregador_plataforma, 0) = 0
            """, (ini_iso, data_iso)).fetchone()
            total_taxas_sem = row_taxas_sem["total"] if row_taxas_sem else 0.0

            colunas_b2 = [
                "Nome", "Entregas", "Soma Taxas", "Diárias",
                "Corridas Extra", "Vales", "Total",
            ]
            bloco2 = _card(
                f"Semana: {ini_br} a {fim_br}",
                _tabela(colunas_b2, _semvazio(linhas_b2, len(colunas_b2))),
                ft.Divider(height=1),
                ft.Text(
                    f"Total de taxas de entrega recebidas na semana: R$ {total_taxas_sem:.2f}",
                    size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300,
                ),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 3 — Histórico de Corridas Extras e Reentregas
            # ══════════════════════════════════════════════════════════════
            rows_hist = conn.execute(
                """SELECT me.id, me.obs,
                          cp.nome AS nome_pessoa,
                          ce.descricao AS categoria,
                          me.valor
                   FROM movimentacoes_extras me
                   LEFT JOIN cad_pessoas cp ON cp.id = me.id_pessoa
                   LEFT JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                   WHERE me.data = ?
                     AND ce.descricao IN ('Corrida Extra', 'Reentrega')
                   ORDER BY me.id""",
                (data_iso,)
            ).fetchall()

        finally:
            conn.close()

        linhas_b3 = []
        for h in rows_hist:
            linhas_b3.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(h["nome_pessoa"] or "—")),
                ft.DataCell(ft.Text(h["categoria"])),
                ft.DataCell(ft.Text(f"R$ {h['valor']:.2f}")),
                ft.DataCell(ft.Text(h["obs"] or "")),
            ]))

        bloco3 = _card(
            f"Corridas Extras e Reentregas — {data_br}",
            _tabela(
                ["Entregador", "Categoria", "Valor", "Obs"],
                _semvazio(linhas_b3, 4),
            ),
        )

        _dados_export.update({
            "data_br": data_br,
            "dia": _dia_lista,
            "semana": _semana_lista,
        })

        col_conteudo.controls.clear()
        col_conteudo.controls += [bloco1, bloco2, bloco3]
        page.update()

    # ── Layout ────────────────────────────────────────────────────────────

    def _exportar_excel(e):
        if not _dados_export:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o relatório antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            caminho = excel_entregadores(_dados_export["data_br"], _dados_export)
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
        if not _dados_export:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o relatório antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            caminho = gerar_pdf_entregadores(_dados_export["data_br"], _dados_export)
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

    btn_carregar = ft.ElevatedButton(
        "Carregar",
        icon=ft.Icons.REFRESH,
        on_click=_carregar,
        style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE),
    )

    tf_data.on_submit = _carregar

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
        controls=[
            ft.Row(controls=[
                tf_data, btn_calendario, btn_carregar,
                ft.ElevatedButton(
                    "Excel",
                    icon=ft.Icons.TABLE_VIEW,
                    on_click=_exportar_excel,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800, color=ft.Colors.WHITE),
                ),
                ft.ElevatedButton(
                    "PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=_exportar_pdf,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE),
                ),
            ], spacing=8),
            ft.Text(
                "Selecione a data e clique em Carregar.",
                color=ft.Colors.GREY_500, italic=True, size=12,
            ),
            ft.Divider(height=1),
            col_conteudo,
        ],
    )
