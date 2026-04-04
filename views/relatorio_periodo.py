"""
views/relatorio_periodo.py — Relatório de período para fechamento parcial/mensal.
"""

import csv
import os
from datetime import date, timedelta

import flet as ft

import database
from relatorios.pdf_gerador import gerar_pdf_periodo, abrir_pdf
from relatorios.excel_gerador import excel_relatorio_periodo


# ── Utilitários ───────────────────────────────────────────────────────────────

def _to_float(s: str) -> float:
    try:
        return float((s or "0").replace(",", ".").strip())
    except ValueError:
        return 0.0


def _data_br_para_iso(s: str) -> str:
    try:
        d, m, a = s.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


def _iso_para_date(s: str) -> date:
    try:
        a, m, d = s.split("-")
        return date(int(a), int(m), int(d))
    except Exception:
        return date.today()


def _proxima_quarta(d: date) -> date:
    days_ahead = 2 - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def _proximo_repasse_ifood(data_fim: date) -> date:
    day, year, month = data_fim.day, data_fim.year, data_fim.month
    if day <= 15:
        return date(year + 1, 1, 5) if month == 12 else date(year, month + 1, 5)
    return date(year + 1, 1, 20) if month == 12 else date(year, month + 1, 20)


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


def _row_total(*celulas_txt: str) -> ft.DataRow:
    return ft.DataRow(
        cells=[ft.DataCell(ft.Text(t, weight=ft.FontWeight.BOLD)) for t in celulas_txt],
        color=None,
    )


def _semvazio(linhas: list, n_colunas: int) -> list:
    if linhas:
        return linhas
    return [ft.DataRow(cells=[
        ft.DataCell(ft.Text(
            "Sem dados para o período.", italic=True, color=ft.Colors.GREY_500
        )),
        *[ft.DataCell(ft.Text("")) for _ in range(n_colunas - 1)],
    ])]


# ── Constantes de nomes amigáveis e métodos ───────────────────────────────────

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

# Métodos recebidos diretamente; o resto é "online" (plataforma repassa)
_METODOS_DIRETOS = ('Crédito', 'Débito', 'PIX', 'Dinheiro', 'VA', 'VR', 'Voucher')


# ── View principal ────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    hoje_br   = date.today().strftime("%d/%m/%Y")
    inicio_br = date.today().replace(day=1).strftime("%d/%m/%Y")

    tf_inicio = ft.TextField(
        label="Data Início", value=inicio_br, width=160,
        text_align=ft.TextAlign.CENTER, hint_text="DD/MM/AAAA",
    )
    tf_fim = ft.TextField(
        label="Data Fim", value=hoje_br, width=160,
        text_align=ft.TextAlign.CENTER, hint_text="DD/MM/AAAA",
    )

    # ── DatePickers ───────────────────────────────────────────────────────
    def _on_picked_ini(e):
        if e.control.value:
            tf_inicio.value = e.control.value.strftime("%d/%m/%Y")
            page.update()

    def _on_picked_fim(e):
        if e.control.value:
            tf_fim.value = e.control.value.strftime("%d/%m/%Y")
            page.update()

    dp_ini = ft.DatePicker(on_change=_on_picked_ini)
    dp_fim = ft.DatePicker(on_change=_on_picked_fim)
    page.overlay.append(dp_ini)
    page.overlay.append(dp_fim)

    btn_cal_ini = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH, tooltip="Data início",
        on_click=lambda e: (setattr(dp_ini, "open", True), page.update()),
    )
    btn_cal_fim = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH, tooltip="Data fim",
        on_click=lambda e: (setattr(dp_fim, "open", True), page.update()),
    )

    col_relatorio = ft.Column(spacing=16, expand=True)
    _dados_csv: dict = {}
    _dados_pdf: dict = {}

    # ─────────────────────────────────────────────────────────────────────
    def _gerar(e=None):
        _dados_csv.clear()

        data_ini_iso = _data_br_para_iso(tf_inicio.value or inicio_br)
        data_fim_iso = _data_br_para_iso(tf_fim.value or hoje_br)
        data_fim_dt  = _iso_para_date(data_fim_iso)

        conn = database.conectar()
        try:
            # ══════════════════════════════════════════════════════════════
            #  BLOCO 1 — Resumo Geral do Período
            # ══════════════════════════════════════════════════════════════
            r_geral = conn.execute("""
                SELECT
                    COUNT(DISTINCT p.id) AS total_pedidos,
                    COALESCE(SUM(p.valor_total), 0) AS valor_bruto,
                    COALESCE(SUM(
                        CASE WHEN EXISTS(
                            SELECT 1 FROM vendas_pagamentos vp
                            WHERE vp.id_pedido = p.id AND vp.cortesia = 1
                        ) THEN p.valor_total ELSE 0 END
                    ), 0) AS total_cortesias
                FROM vendas_pedidos p
                WHERE p.data BETWEEN ? AND ?
            """, (data_ini_iso, data_fim_iso)).fetchone()

            r_fat = conn.execute("""
                SELECT COALESCE(SUM(vp.valor), 0) AS fat_real
                FROM vendas_pagamentos vp
                JOIN vendas_pedidos  p ON p.id   = vp.id_pedido
                JOIN cad_metodos_pag m ON m.nome = vp.metodo
                WHERE p.data BETWEEN ? AND ?
                  AND vp.cortesia = 0
                  AND m.tipo != 'CORTESIA'
                  AND vp.metodo != 'Voucher'
            """, (data_ini_iso, data_fim_iso)).fetchone()

            # Total taxas de entrega recebidas (exceto canais _Deles)
            r_taxas_geral = conn.execute("""
                SELECT COALESCE(SUM(p.taxa_entrega), 0) AS total
                FROM vendas_pedidos p
                LEFT JOIN cad_canais c ON c.nome = p.canal
                WHERE p.data BETWEEN ? AND ?
                  AND COALESCE(c.entregador_plataforma, 0) = 0
            """, (data_ini_iso, data_fim_iso)).fetchone()

            total_pedidos   = r_geral["total_pedidos"]
            valor_bruto     = r_geral["valor_bruto"]
            total_cortesias = r_geral["total_cortesias"]
            fat_real        = r_fat["fat_real"] if r_fat else 0.0
            total_taxas     = r_taxas_geral["total"] if r_taxas_geral else 0.0

            _dados_csv["resumo_geral"] = {
                "total_pedidos":   total_pedidos,
                "valor_bruto":     valor_bruto,
                "total_cortesias": total_cortesias,
                "fat_real":        fat_real,
                "total_taxas":     total_taxas,
            }

            bloco1 = _card(
                "Resumo Geral do Período",
                ft.Row(
                    spacing=32, wrap=True,
                    controls=[
                        ft.Column(spacing=4, controls=[
                            ft.Text("Total de Pedidos", size=12, color=ft.Colors.GREY_500),
                            ft.Text(str(total_pedidos), size=26, weight=ft.FontWeight.BOLD),
                        ]),
                        ft.Column(spacing=4, controls=[
                            ft.Text("Valor Bruto", size=12, color=ft.Colors.GREY_500),
                            ft.Text(f"R$ {valor_bruto:.2f}", size=26, weight=ft.FontWeight.BOLD),
                        ]),
                        ft.Column(spacing=4, controls=[
                            ft.Text("Total Cortesias", size=12, color=ft.Colors.GREY_500),
                            ft.Text(
                                f"R$ {total_cortesias:.2f}", size=26,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_300,
                            ),
                        ]),
                        ft.Column(spacing=4, controls=[
                            ft.Text("Faturamento Real", size=12, color=ft.Colors.GREY_500),
                            ft.Text(
                                f"R$ {fat_real:.2f}", size=26,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300,
                            ),
                        ]),
                        ft.Column(spacing=4, controls=[
                            ft.Text("Taxas de Entrega Recebidas", size=12, color=ft.Colors.GREY_500),
                            ft.Text(
                                f"R$ {total_taxas:.2f}", size=26,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300,
                            ),
                        ]),
                    ],
                ),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 2 — Resumo por Canal
            # ══════════════════════════════════════════════════════════════
            rows_canal = conn.execute("""
                SELECT canal,
                       SUM(CASE WHEN NOT EXISTS(
                           SELECT 1 FROM vendas_pagamentos vp2
                           WHERE vp2.id_pedido = p.id
                             AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado')
                       ) THEN 1 ELSE 0 END) AS qtd,
                       COALESCE(SUM(
                           CASE WHEN EXISTS(
                               SELECT 1 FROM vendas_pagamentos vp
                               WHERE vp.id_pedido = p.id
                                 AND (vp.cortesia = 1 OR vp.metodo = 'Fiado')
                           ) THEN 0.0 ELSE p.valor_total END
                       ), 0) AS valor_total
                FROM vendas_pedidos p
                WHERE p.data BETWEEN ? AND ?
                GROUP BY canal
                HAVING SUM(CASE WHEN NOT EXISTS(
                    SELECT 1 FROM vendas_pagamentos vp2
                    WHERE vp2.id_pedido = p.id
                      AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado')
                ) THEN 1 ELSE 0 END) > 0
                ORDER BY canal
            """, (data_ini_iso, data_fim_iso)).fetchall()

            total_qtd_c   = sum(r["qtd"] for r in rows_canal)
            total_valor_c = sum(r["valor_total"] for r in rows_canal)

            linhas_c = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(CANAL_NOMES.get(r["canal"], r["canal"]))),
                    ft.DataCell(ft.Text(str(r["qtd"]))),
                    ft.DataCell(ft.Text(f"R$ {r['valor_total']:.2f}")),
                ])
                for r in rows_canal
            ]
            linhas_c.append(_row_total("TOTAL", str(total_qtd_c), f"R$ {total_valor_c:.2f}"))
            _dados_csv["canais"] = [dict(r) for r in rows_canal]

            bloco2 = _card(
                "Resumo por Canal",
                _tabela(["Canal", "Qtd Pedidos", "Valor Total"], _semvazio(linhas_c, 3)),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 3 — Resumo por Pagamento
            # ══════════════════════════════════════════════════════════════
            # LEFT JOIN para não perder métodos ausentes de cad_metodos_pag
            # (iFood, 99Food, Keeta podem não ter cadastro).
            # CTE pag_count corrige vp.valor=0 em pedidos com pagamento único.
            sql_pag = """
                WITH pag_count AS (
                    SELECT id_pedido, COUNT(*) AS qtd,
                           SUM(valor) AS soma_pag
                    FROM vendas_pagamentos
                    GROUP BY id_pedido
                )
                SELECT vp.metodo,
                       COALESCE(m.tipo, 'OUTROS') AS tipo,
                       COUNT(DISTINCT CASE WHEN NOT EXISTS(
                           SELECT 1 FROM vendas_pagamentos vp3
                           WHERE vp3.id_pedido = p.id
                             AND (vp3.cortesia = 1 OR vp3.metodo = 'Fiado')
                       ) THEN p.id ELSE NULL END) AS qtd_pedidos,
                       COALESCE(SUM(
                           CASE
                             WHEN pc.qtd = 1
                             THEN p.valor_total
                             WHEN vp.id = (
                                 SELECT MIN(id) FROM vendas_pagamentos
                                 WHERE id_pedido = vp.id_pedido
                             )
                             THEN vp.valor + (p.valor_total - pc.soma_pag)
                             ELSE vp.valor
                           END
                       ), 0) AS total
                FROM vendas_pagamentos vp
                JOIN vendas_pedidos       p  ON p.id         = vp.id_pedido
                JOIN pag_count            pc ON pc.id_pedido = vp.id_pedido
                LEFT JOIN cad_metodos_pag m  ON m.nome       = vp.metodo
                WHERE p.data BETWEEN ? AND ?
                  AND COALESCE(m.tipo, 'OUTROS') != 'CORTESIA'
                  AND vp.metodo != 'Fiado'
                  AND NOT EXISTS (
                      SELECT 1 FROM vendas_pagamentos vp2
                      WHERE vp2.id_pedido = p.id
                        AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado')
                  )
                GROUP BY vp.metodo, m.tipo
                ORDER BY m.tipo, vp.metodo
            """
            rows_pag = conn.execute(sql_pag, (data_ini_iso, data_fim_iso)).fetchall()

            total_pag = sum(r["total"]       for r in rows_pag)
            total_qtd = sum(r["qtd_pedidos"] for r in rows_pag)
            linhas_p  = []
            for r in rows_pag:
                cor = ft.Colors.BLUE_200 if r["tipo"] == "BENEFICIO" else None
                linhas_p.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(r["metodo"], color=cor)),
                    ft.DataCell(ft.Text(str(r["qtd_pedidos"]), color=cor)),
                    ft.DataCell(ft.Text(f"R$ {r['total']:.2f}", color=cor)),
                ]))
            linhas_p.append(_row_total("TOTAL", str(total_qtd), f"R$ {total_pag:.2f}"))
            _dados_csv["pagamentos"] = [dict(r) for r in rows_pag]

            n_split = conn.execute("""
                SELECT COUNT(*) FROM (
                    SELECT id_pedido
                    FROM vendas_pagamentos vp
                    JOIN vendas_pedidos p ON p.id = vp.id_pedido
                    WHERE p.data BETWEEN ? AND ?
                      AND vp.cortesia = 0
                      AND vp.metodo != 'Fiado'
                    GROUP BY id_pedido
                    HAVING COUNT(*) > 1
                      AND COUNT(DISTINCT vp.metodo) > 1
                )
            """, (data_ini_iso, data_fim_iso)).fetchone()[0]

            bloco3 = _card(
                "Resumo por Pagamento",
                ft.Text(
                    "VA/VR destacados em azul  ·  Voucher/Cortesia e Fiado excluídos",
                    size=12, color=ft.Colors.GREY_500, italic=True,
                ),
                _tabela(["Método", "Qtd Pedidos", "Valor Total"], _semvazio(linhas_p, 3)),
                ft.Text(
                    f"A quantidade de transações pode ser maior que a de pedidos "
                    f"quando o cliente paga com mais de um método. "
                    f"No período foram {n_split} pedido(s) com pagamento dividido.",
                    size=12, color=ft.Colors.GREY_500, italic=True,
                ),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 4 — Detalhamento Plataformas
            # ══════════════════════════════════════════════════════════════
            plat_db = {
                p["nome"]: dict(p)
                for p in database.plataforma_listar(apenas_ativas=False)
            }

            prox_quarta  = _proxima_quarta(data_fim_dt).strftime("%d/%m/%Y")
            rep_ifood    = _proximo_repasse_ifood(data_fim_dt).strftime("%d/%m/%Y")
            plat_repasse = {
                "iFood1": rep_ifood,
                "iFood2": rep_ifood,
                "99Food": prox_quarta,
                "Keeta":  prox_quarta,
            }
            _dados_csv["plataformas"] = {}

            ph = ",".join("?" * len(_METODOS_DIRETOS))  # placeholders SQL

            def _conteudo_plataforma(nome_plat: str) -> ft.Control:
                plat         = plat_db.get(nome_plat, {})
                comissao_pct = plat.get("comissao_pct",       0.0)
                tx_trans_pct = plat.get("taxa_transacao_pct", 0.0)
                subsidio_pp  = plat.get("subsidio",           0.0)
                dt_repasse   = plat_repasse.get(nome_plat, "—")

                r_bruto = conn.execute("""
                    SELECT COUNT(*) AS qtd, COALESCE(SUM(valor_total), 0) AS bruto
                    FROM vendas_pedidos
                    WHERE data BETWEEN ? AND ? AND canal LIKE ?
                """, (data_ini_iso, data_fim_iso, f"{nome_plat}%")).fetchone()

                qtd   = r_bruto["qtd"]   if r_bruto else 0
                bruto = r_bruto["bruto"] if r_bruto else 0.0

                # Split online (plataforma repassa) vs maquininha (já recebido)
                row_split = conn.execute(f"""
                    WITH pc AS (
                        SELECT id_pedido, COUNT(*) AS qtd
                        FROM vendas_pagamentos
                        GROUP BY id_pedido
                    )
                    SELECT
                        COALESCE(SUM(CASE
                            WHEN vp.metodo NOT IN ({ph})
                            THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END
                            ELSE 0
                        END), 0) AS bruto_online,
                        COALESCE(SUM(CASE
                            WHEN vp.metodo IN ({ph})
                            THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END
                            ELSE 0
                        END), 0) AS bruto_maq
                    FROM vendas_pagamentos vp
                    JOIN vendas_pedidos p ON p.id = vp.id_pedido
                    JOIN pc ON pc.id_pedido = vp.id_pedido
                    WHERE p.data BETWEEN ? AND ? AND p.canal LIKE ?
                """, (*_METODOS_DIRETOS, *_METODOS_DIRETOS,
                      data_ini_iso, data_fim_iso, f"{nome_plat}%")).fetchone()

                bruto_online = row_split["bruto_online"] if row_split else 0.0
                bruto_maq    = row_split["bruto_maq"]    if row_split else 0.0

                comissao_online = bruto_online * comissao_pct / 100
                tx_trans        = bruto_online * tx_trans_pct / 100
                comissao_maq    = bruto_maq    * comissao_pct / 100
                subsidio        = qtd * subsidio_pp
                liquido = (bruto_online - comissao_online - tx_trans) - comissao_maq + subsidio

                def _item(label: str, valor: float, bold=False, verde=False,
                          vermelho=False, muted=False):
                    if verde:
                        cor = ft.Colors.GREEN_300
                    elif vermelho:
                        cor = ft.Colors.RED_300
                    elif muted:
                        cor = ft.Colors.GREY_500
                    else:
                        cor = None
                    w = ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL
                    return ft.Row(spacing=8, controls=[
                        ft.Text(label, expand=3, color=cor, weight=w, size=13),
                        ft.Text(
                            f"R$ {valor:.2f}", expand=1,
                            text_align=ft.TextAlign.RIGHT,
                            color=cor, weight=w, size=13,
                        ),
                    ])

                itens = [
                    ft.Text(
                        f"Previsão de repasse: {dt_repasse}",
                        size=12, color=ft.Colors.AMBER_300, italic=True,
                    ),
                    _item(f"Pedidos: {qtd}   |   Bruto total", bruto),
                    ft.Divider(height=1),
                    _item("Pago online (plataforma repassa)", bruto_online),
                    _item(f"  (-) Comissão {comissao_pct:.1f}% s/ online", comissao_online, vermelho=True),
                    _item(f"  (-) Taxa transação {tx_trans_pct:.1f}% s/ online", tx_trans, vermelho=True),
                ]

                if bruto_maq > 0:
                    itens += [
                        ft.Divider(height=1),
                        _item("Recebido na maquininha (plat. debitará comissão)", bruto_maq, muted=True),
                        _item(f"  (-) Comissão {comissao_pct:.1f}% s/ maquininha", comissao_maq, vermelho=True),
                    ]

                itens.append(_item(f"(+) Subsídio R$ {subsidio_pp:.2f}/ped", subsidio))

                lucro_liquido = bruto_online - comissao_online - tx_trans + subsidio

                if nome_plat == "99Food":
                    custo_log = qtd * plat.get("custo_logistico_maximo", 0.0)
                    itens.append(_item("(-) Custo Logístico (máx)", custo_log, vermelho=True))
                    lucro_liquido -= custo_log
                    liquido       -= custo_log

                cor_lucro   = ft.Colors.GREEN_400 if lucro_liquido >= 0 else ft.Colors.RED_400
                label_lucro = "Lucro Líquido Estimado" if lucro_liquido >= 0 else "Prejuízo Estimado"
                itens += [
                    ft.Divider(height=1),
                    ft.Row(controls=[
                        ft.Text(label_lucro, expand=True, weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(f"R$ {lucro_liquido:.2f}", weight=ft.FontWeight.BOLD,
                                color=cor_lucro, size=13),
                    ]),
                ]

                _dados_csv["plataformas"][nome_plat] = {
                    "qtd": qtd, "bruto": bruto,
                    "bruto_online": bruto_online, "bruto_maq": bruto_maq,
                    "comissao_online": comissao_online, "tx_trans": tx_trans,
                    "comissao_maq": comissao_maq, "subsidio": subsidio,
                    "liquido": liquido, "dt_repasse": dt_repasse,
                    "comissao_pct": comissao_pct, "tx_trans_pct": tx_trans_pct,
                    "subsidio_pp": subsidio_pp,
                }

                return ft.Container(
                    padding=ft.Padding.all(10),
                    content=ft.Column(spacing=6, controls=itens),
                )

            plat_tabs = ft.Tabs(
                content=ft.Column(
                    expand=True,
                    controls=[
                        ft.TabBar(
                            scrollable=False,
                            tabs=[
                                ft.Tab(label="iFood L1"),
                                ft.Tab(label="iFood L2"),
                                ft.Tab(label="99Food"),
                                ft.Tab(label="Keeta"),
                            ],
                        ),
                        ft.TabBarView(
                            expand=True,
                            controls=[
                                _conteudo_plataforma("iFood1"),
                                _conteudo_plataforma("iFood2"),
                                _conteudo_plataforma("99Food"),
                                _conteudo_plataforma("Keeta"),
                            ],
                        ),
                    ],
                ),
                length=4,
                selected_index=0,
                expand=True,
            )

            bloco4 = _card(
                "Detalhamento Plataformas",
                ft.Container(height=330, content=plat_tabs),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 5 — Resumo Entregadores no Período
            # ══════════════════════════════════════════════════════════════
            entregadores = database.pessoa_listar(tipo="ENTREGADOR", apenas_ativos=False)
            linhas_e = []
            _dados_csv["entregadores"] = []
            total_taxas_ent = 0.0   # acumulador para o rodapé

            for ent in entregadores:
                id_ent = ent["id"]

                diaria_valor = ent["diaria_valor"] or 0.0
                if ent["tipo_salario"] == "ENTREGADOR" and diaria_valor == 0.0:
                    diaria_valor = 40.0

                r_entr = conn.execute("""
                    SELECT COUNT(*) AS total_entregas,
                           COALESCE(SUM(repasse_entregador), 0) AS soma_taxas,
                           COUNT(DISTINCT data) AS dias_com_entrega
                    FROM vendas_pedidos
                    WHERE data BETWEEN ? AND ?
                      AND id_operador = ?
                      AND repasse_entregador > 0
                """, (data_ini_iso, data_fim_iso, id_ent)).fetchone()

                total_entregas   = r_entr["total_entregas"]
                soma_taxas       = r_entr["soma_taxas"]
                dias_com_entrega = r_entr["dias_com_entrega"]

                if total_entregas == 0:
                    continue

                total_diarias = dias_com_entrega * diaria_valor

                r_extras = conn.execute("""
                    SELECT COALESCE(SUM(me.valor), 0) AS total
                    FROM movimentacoes_extras me
                    JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                    WHERE me.data BETWEEN ? AND ?
                      AND me.id_pessoa = ? AND ce.descricao = 'Corrida Extra'
                """, (data_ini_iso, data_fim_iso, id_ent)).fetchone()

                r_vales = conn.execute("""
                    SELECT COALESCE(SUM(me.valor), 0) AS total
                    FROM movimentacoes_extras me
                    JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                    WHERE me.data BETWEEN ? AND ?
                      AND me.id_pessoa = ? AND ce.descricao = 'Vale'
                """, (data_ini_iso, data_fim_iso, id_ent)).fetchone()

                # Taxas de entrega recebidas por este entregador (canais próprios)
                r_taxa_ent = conn.execute("""
                    SELECT COALESCE(SUM(p.taxa_entrega), 0) AS total
                    FROM vendas_pedidos p
                    LEFT JOIN cad_canais c ON c.nome = p.canal
                    WHERE p.data BETWEEN ? AND ?
                      AND p.id_operador = ?
                      AND COALESCE(c.entregador_plataforma, 0) = 0
                """, (data_ini_iso, data_fim_iso, id_ent)).fetchone()

                corridas_extras = r_extras["total"]  if r_extras  else 0.0
                vales           = r_vales["total"]   if r_vales   else 0.0
                taxa_ent        = r_taxa_ent["total"] if r_taxa_ent else 0.0
                total_liquido   = total_diarias + soma_taxas + corridas_extras - vales
                total_taxas_ent += taxa_ent

                linhas_e.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(ent["nome"])),
                    ft.DataCell(ft.Text(str(total_entregas))),
                    ft.DataCell(ft.Text(f"R$ {soma_taxas:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {taxa_ent:.2f}",
                                        color=ft.Colors.TEAL_300)),
                    ft.DataCell(ft.Text(f"R$ {total_diarias:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {corridas_extras:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {vales:.2f}")),
                    ft.DataCell(ft.Text(
                        f"R$ {total_liquido:.2f}",
                        weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300,
                    )),
                ]))
                _dados_csv["entregadores"].append({
                    "nome": ent["nome"], "total_entregas": total_entregas,
                    "soma_taxas": soma_taxas, "taxa_entrega_recebida": taxa_ent,
                    "total_diarias": total_diarias,
                    "corridas_extras": corridas_extras, "vales": vales,
                    "total_liquido": total_liquido,
                })

            cols_e = ["Nome", "Entregas", "Soma Taxas Rep.", "Taxas Recebidas",
                      "Total Diárias", "Extras", "Vales", "Total a Pagar"]
            if linhas_e:
                linhas_e.append(_row_total(
                    "TOTAL", "", "", f"R$ {total_taxas_ent:.2f}", "", "", "", "",
                ))

            bloco5 = _card(
                "Resumo Entregadores no Período",
                _tabela(cols_e, _semvazio(linhas_e, len(cols_e))),
                ft.Divider(height=1),
                ft.Text(
                    f"Total de taxas de entrega recebidas no período: R$ {total_taxas_ent:.2f}",
                    size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300,
                ),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 6 — Resumo Funcionários no Período
            # ══════════════════════════════════════════════════════════════
            internos = database.pessoa_listar(tipo="INTERNO", apenas_ativos=False)
            linhas_f = []
            _dados_csv["funcionarios"] = []

            for func in internos:
                id_func = func["id"]

                dias_trab = database.escala_contar_dias(
                    id_func, data_ini_iso, data_fim_iso, "TRABALHOU")
                faltas    = database.escala_contar_dias(
                    id_func, data_ini_iso, data_fim_iso, "FALTA")
                extras    = database.escala_contar_dias(
                    id_func, data_ini_iso, data_fim_iso, "EXTRA")
                feriados  = database.escala_contar_dias(
                    id_func, data_ini_iso, data_fim_iso, "FERIADO")

                r_vales_f = conn.execute("""
                    SELECT COALESCE(SUM(me.valor), 0) AS total
                    FROM movimentacoes_extras me
                    JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                    WHERE me.data BETWEEN ? AND ?
                      AND me.id_pessoa = ? AND ce.descricao = 'Vale'
                """, (data_ini_iso, data_fim_iso, id_func)).fetchone()

                r_consumos = conn.execute("""
                    SELECT COALESCE(SUM(me.valor), 0) AS total
                    FROM movimentacoes_extras me
                    JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                    WHERE me.data BETWEEN ? AND ?
                      AND me.id_pessoa = ? AND ce.descricao = 'Consumo'
                """, (data_ini_iso, data_fim_iso, id_func)).fetchone()

                vales_f    = r_vales_f["total"] if r_vales_f else 0.0
                consumos_f = r_consumos["total"] if r_consumos else 0.0

                tipo_sal = func["tipo_salario"] or "FIXO"
                base = (dias_trab * (func["diaria_valor"] or 0.0)
                        if tipo_sal == "DIARIO"
                        else func["salario_base"] or 0.0)
                salario_liquido = base - vales_f - consumos_f

                linhas_f.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(func["nome"])),
                    ft.DataCell(ft.Text(str(dias_trab))),
                    ft.DataCell(ft.Text(str(faltas))),
                    ft.DataCell(ft.Text(str(extras))),
                    ft.DataCell(ft.Text(str(feriados))),
                    ft.DataCell(ft.Text(f"R$ {vales_f:.2f}")),
                    ft.DataCell(ft.Text(f"R$ {consumos_f:.2f}")),
                    ft.DataCell(ft.Text(
                        f"R$ {salario_liquido:.2f}",
                        weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300,
                    )),
                ]))
                _dados_csv["funcionarios"].append({
                    "nome": func["nome"], "dias_trab": dias_trab,
                    "faltas": faltas, "extras": extras, "feriados": feriados,
                    "vales": vales_f, "consumos": consumos_f,
                    "salario_liquido": salario_liquido,
                })

            bloco6 = _card(
                "Resumo Funcionários no Período",
                _tabela(
                    ["Nome", "Trabalhados", "Faltas", "Extras", "Feriados",
                     "Vales", "Consumos", "Salário Est."],
                    _semvazio(linhas_f, 8),
                ),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 7 — Projeção de Repasses
            # ══════════════════════════════════════════════════════════════
            total_liquido_plats = sum(
                d.get("liquido", 0.0)
                for d in _dados_csv["plataformas"].values()
            )

            linhas_rep = []
            for nome_plat in ["iFood1", "iFood2", "99Food", "Keeta"]:
                dados_plat = _dados_csv["plataformas"].get(nome_plat, {})
                liquido    = dados_plat.get("liquido", 0.0)
                dt_rep     = dados_plat.get("dt_repasse", "—")
                linhas_rep.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(nome_plat)),
                    ft.DataCell(ft.Text(
                        f"R$ {liquido:.2f}",
                        color=ft.Colors.GREEN_300 if liquido > 0 else ft.Colors.GREY_500,
                        weight=ft.FontWeight.BOLD,
                    )),
                    ft.DataCell(ft.Text(dt_rep, color=ft.Colors.AMBER_300)),
                ]))

            bloco7 = _card(
                "Projeção de Repasses",
                ft.Text(
                    "iFood: próximo ciclo quinzenal  ·  99Food/Keeta: próxima quarta-feira",
                    size=12, color=ft.Colors.GREY_500, italic=True,
                ),
                _tabela(
                    ["Plataforma", "Líquido Estimado", "Data Prevista"],
                    _semvazio(linhas_rep, 3),
                ),
                ft.Divider(height=1),
                ft.Row(spacing=32, wrap=True, controls=[
                    ft.Column(spacing=2, controls=[
                        ft.Text("Total Líquido Plataformas", size=12, color=ft.Colors.GREY_500),
                        ft.Text(
                            f"R$ {total_liquido_plats:.2f}", size=20,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300,
                        ),
                    ]),
                    ft.Column(spacing=2, controls=[
                        ft.Text("Taxas de Entrega Recebidas (motoboys próprios)",
                                size=12, color=ft.Colors.GREY_500),
                        ft.Text(
                            f"R$ {total_taxas:.2f}", size=20,
                            weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300,
                        ),
                    ]),
                ]),
            )

            row_fiados_p = conn.execute("""
                SELECT COUNT(DISTINCT p.id) AS qtd,
                       COALESCE(SUM(p.valor_total), 0) AS total
                FROM vendas_pedidos p
                JOIN vendas_pagamentos vp ON vp.id_pedido = p.id
                WHERE p.data BETWEEN ? AND ?
                  AND vp.metodo = 'Fiado'
            """, (data_ini_iso, data_fim_iso)).fetchone()

            row_cortesias_p = conn.execute("""
                SELECT COUNT(DISTINCT p.id) AS qtd,
                       COALESCE(SUM(p.valor_total), 0) AS total
                FROM vendas_pedidos p
                JOIN vendas_pagamentos vp ON vp.id_pedido = p.id
                WHERE p.data BETWEEN ? AND ?
                  AND (vp.cortesia = 1 OR vp.metodo = 'Voucher')
            """, (data_ini_iso, data_fim_iso)).fetchone()

            qtd_fiados_p      = row_fiados_p["qtd"]    if row_fiados_p    else 0
            total_fiados_p    = row_fiados_p["total"]  if row_fiados_p    else 0.0
            qtd_cortesias_p   = row_cortesias_p["qtd"] if row_cortesias_p else 0
            total_cortesias_p = row_cortesias_p["total"] if row_cortesias_p else 0.0

        finally:
            conn.close()

        def _mini_card_info(titulo, qtd, total, cor_titulo, obs=None):
            controls = [
                ft.Text(titulo, size=15, weight=ft.FontWeight.BOLD, color=cor_titulo),
                ft.Divider(height=1),
                ft.Row(controls=[
                    ft.Text("Pedidos:", expand=1, size=13),
                    ft.Text(str(qtd), size=13, weight=ft.FontWeight.BOLD),
                ]),
                ft.Row(controls=[
                    ft.Text("Valor total:", expand=1, size=13),
                    ft.Text(f"R$ {total:.2f}", size=13,
                            weight=ft.FontWeight.BOLD, color=cor_titulo),
                ]),
                ft.Text(
                    "Valores não somados ao faturamento do período.",
                    size=11, italic=True, color=ft.Colors.GREY_500,
                ),
            ]
            if obs:
                controls.append(ft.Text(obs, size=11, italic=True,
                                        color=ft.Colors.GREY_500))
            return ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=controls),
            ))

        bloco8 = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    expand=True,
                    content=_mini_card_info(
                        "Fiados do Período",
                        qtd_fiados_p,
                        total_fiados_p,
                        ft.Colors.ORANGE_300,
                        obs="Consulte a tela de Fiados para detalhes e quitações."
                        if qtd_fiados_p > 0 else None,
                    ),
                ),
                ft.Container(
                    expand=True,
                    content=_mini_card_info(
                        "Cortesias e Vouchers do Período",
                        qtd_cortesias_p,
                        total_cortesias_p,
                        ft.Colors.PURPLE_300,
                    ),
                ),
            ],
        )

        # Populando _dados_pdf a partir dos dados já calculados
        _dados_pdf.clear()
        _dados_pdf["nome_loja"]    = database.config_obter("nome_loja", "Gestão Loja")
        _dados_pdf["resumo_geral"] = _dados_csv.get("resumo_geral", {})
        _dados_pdf["canais"]       = [
            dict(r, canal_amigavel=CANAL_NOMES.get(r["canal"], r["canal"]))
            for r in _dados_csv.get("canais", [])
        ]
        _dados_pdf["pagamentos"]   = _dados_csv.get("pagamentos", [])
        _dados_pdf["plataformas"]  = _dados_csv.get("plataformas", {})
        _dados_pdf["entregadores"] = _dados_csv.get("entregadores", [])
        _dados_pdf["funcionarios"] = _dados_csv.get("funcionarios", [])

        linha_canais_pag = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(expand=True, content=bloco2),
                ft.Container(expand=True, content=bloco3),
            ],
        )
        col_relatorio.controls.clear()
        col_relatorio.controls += [bloco1, linha_canais_pag, bloco4, bloco5, bloco6, bloco7, bloco8]
        page.update()

    # ── Exportar CSV ──────────────────────────────────────────────────────

    def _exportar_csv(e):
        if not _dados_csv:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o relatório antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return

        os.makedirs("exports", exist_ok=True)
        ini_str = (tf_inicio.value or inicio_br).replace("/", "")
        fim_str = (tf_fim.value or hoje_br).replace("/", "")
        caminho = os.path.join("exports", f"relatorio_{ini_str}_{fim_str}.csv")

        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)

            rg = _dados_csv.get("resumo_geral", {})
            w.writerow(["=== RESUMO GERAL ==="])
            w.writerow(["Total Pedidos", "Valor Bruto", "Total Cortesias",
                        "Faturamento Real", "Taxas de Entrega Recebidas"])
            w.writerow([
                rg.get("total_pedidos", 0),
                f"{rg.get('valor_bruto', 0):.2f}",
                f"{rg.get('total_cortesias', 0):.2f}",
                f"{rg.get('fat_real', 0):.2f}",
                f"{rg.get('total_taxas', 0):.2f}",
            ])
            w.writerow([])

            w.writerow(["=== RESUMO POR CANAL ==="])
            w.writerow(["Canal", "Canal Amigável", "Qtd Pedidos", "Valor Total"])
            for r in _dados_csv.get("canais", []):
                w.writerow([
                    r["canal"],
                    CANAL_NOMES.get(r["canal"], r["canal"]),
                    r["qtd"],
                    f"{r['valor_total']:.2f}",
                ])
            w.writerow([])

            w.writerow(["=== RESUMO POR PAGAMENTO ==="])
            w.writerow(["Método", "Tipo", "Valor Total"])
            for r in _dados_csv.get("pagamentos", []):
                w.writerow([r["metodo"], r["tipo"], f"{r['total']:.2f}"])
            w.writerow([])

            w.writerow(["=== DETALHAMENTO PLATAFORMAS ==="])
            w.writerow(["Plataforma", "Pedidos", "Bruto Total",
                        "Online", "Comissão Online", "Tx Transação",
                        "Maquininha", "Comissão Maquininha",
                        "Subsídio", "Líquido", "Data Repasse"])
            for nome, d in _dados_csv.get("plataformas", {}).items():
                w.writerow([
                    nome, d.get("qtd", 0),
                    f"{d.get('bruto', 0):.2f}",
                    f"{d.get('bruto_online', 0):.2f}",
                    f"{d.get('comissao_online', 0):.2f}",
                    f"{d.get('tx_trans', 0):.2f}",
                    f"{d.get('bruto_maq', 0):.2f}",
                    f"{d.get('comissao_maq', 0):.2f}",
                    f"{d.get('subsidio', 0):.2f}",
                    f"{d.get('liquido', 0):.2f}",
                    d.get("dt_repasse", "—"),
                ])
            w.writerow([])

            w.writerow(["=== RESUMO ENTREGADORES ==="])
            w.writerow(["Nome", "Entregas", "Soma Taxas Rep.", "Taxas Recebidas",
                        "Total Diárias", "Extras", "Vales", "Total a Pagar"])
            for r in _dados_csv.get("entregadores", []):
                w.writerow([
                    r["nome"], r["total_entregas"],
                    f"{r['soma_taxas']:.2f}",
                    f"{r['taxa_entrega_recebida']:.2f}",
                    f"{r['total_diarias']:.2f}",
                    f"{r['corridas_extras']:.2f}", f"{r['vales']:.2f}",
                    f"{r['total_liquido']:.2f}",
                ])
            w.writerow([])

            w.writerow(["=== RESUMO FUNCIONÁRIOS ==="])
            w.writerow(["Nome", "Trabalhados", "Faltas", "Extras", "Feriados",
                        "Vales", "Consumos", "Salário Est."])
            for r in _dados_csv.get("funcionarios", []):
                w.writerow([
                    r["nome"], r["dias_trab"], r["faltas"],
                    r["extras"], r["feriados"],
                    f"{r['vales']:.2f}", f"{r['consumos']:.2f}",
                    f"{r['salario_liquido']:.2f}",
                ])

        page.overlay.append(ft.SnackBar(
            content=ft.Text(f"CSV exportado: {caminho}"),
            bgcolor=ft.Colors.GREEN_700, open=True,
        ))
        page.update()

    # ── Exportar PDF ──────────────────────────────────────────────────────

    def _exportar_pdf(e):
        if not _dados_pdf:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o relatório antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        data_ini_iso = _data_br_para_iso(tf_inicio.value or inicio_br)
        data_fim_iso = _data_br_para_iso(tf_fim.value    or hoje_br)
        caminho      = gerar_pdf_periodo(data_ini_iso, data_fim_iso, _dados_pdf)
        abrir_pdf(caminho)
        page.overlay.append(ft.SnackBar(
            content=ft.Text("PDF gerado e aberto para impressão."),
            bgcolor=ft.Colors.GREEN_700, open=True,
        ))
        page.update()

    btn_exportar_pdf = ft.ElevatedButton(
        "PDF",
        icon=ft.Icons.PICTURE_AS_PDF,
        on_click=_exportar_pdf,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.RED_800,
            color=ft.Colors.WHITE,
        ),
    )

    def _exportar_excel(e):
        if not _dados_pdf:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o relatório antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            dados = dict(_dados_pdf)
            dados["funcionarios"] = _dados_csv.get("funcionarios", [])
            ini_br = tf_inicio.value or inicio_br
            fim_br = tf_fim.value    or hoje_br
            caminho = excel_relatorio_periodo(ini_br, fim_br, dados)
            import os; os.startfile(caminho)
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

    btn_exportar_excel = ft.ElevatedButton(
        "Excel",
        icon=ft.Icons.TABLE_VIEW,
        on_click=_exportar_excel,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN_800,
            color=ft.Colors.WHITE,
        ),
    )

    # ── Layout do topo ────────────────────────────────────────────────────

    btn_gerar = ft.ElevatedButton(
        "Gerar Relatório",
        icon=ft.Icons.ASSESSMENT,
        on_click=_gerar,
        style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE),
    )

    btn_exportar = ft.ElevatedButton(
        "Exportar CSV",
        icon=ft.Icons.DOWNLOAD,
        on_click=_exportar_csv,
        style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE),
    )

    topo = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    controls=[
                        tf_inicio, btn_cal_ini,
                        tf_fim,    btn_cal_fim,
                        btn_gerar, btn_exportar, btn_exportar_excel, btn_exportar_pdf,
                    ],
                    spacing=8,
                    wrap=True,
                ),
                ft.Text(
                    "Selecione o período e clique em Gerar Relatório. "
                    "Use Exportar CSV para salvar em exports/.",
                    color=ft.Colors.GREY_500, italic=True, size=12,
                ),
            ],
        ),
    ))

    return ft.Column(
        controls=[topo, col_relatorio],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
