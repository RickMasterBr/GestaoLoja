"""
views/relatorio_diario.py — Relatório diário de fechamento de caixa.
"""

import flet as ft
from datetime import date

import database
from relatorios.pdf_gerador import gerar_pdf_diario, abrir_pdf
from relatorios.excel_gerador import excel_relatorio_diario


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
    """Linha de rodapé em negrito com fundo levemente destacado."""
    return ft.DataRow(
        cells=[
            ft.DataCell(ft.Text(t, weight=ft.FontWeight.BOLD)) for t in celulas_txt
        ],
        color=None,
    )


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

# Métodos recebidos diretamente (maquininha/espécie); o resto é "online" (plataforma repassa)
_METODOS_DIRETOS = ('Crédito', 'Débito', 'PIX', 'Dinheiro', 'VA', 'VR', 'Voucher')


def _semvazio(linhas: list, n_colunas: int) -> list:
    """Se não há linhas, retorna uma linha de placeholder no lugar."""
    if linhas:
        return linhas
    return [ft.DataRow(cells=[
        ft.DataCell(ft.Text(
            "Sem dados para esta data.", italic=True, color=ft.Colors.GREY_500
        )),
        *[ft.DataCell(ft.Text("")) for _ in range(n_colunas - 1)],
    ])]


# ── View principal ────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    hoje_br = date.today().strftime("%d/%m/%Y")

    tf_data      = ft.TextField(
        label="Data", value=hoje_br, width=160,
        text_align=ft.TextAlign.CENTER, hint_text="DD/MM/AAAA",
    )
    col_relatorio = ft.Column(spacing=16, expand=True)
    _dados_pdf: dict = {}

    # ─────────────────────────────────────────────────────────────────────
    def _gerar(e=None):
        data_iso = _data_br_para_iso(tf_data.value or hoje_br)
        _dados_pdf.clear()
        _dados_pdf["nome_loja"] = database.config_obter("nome_loja", "Gestão Loja")
        _dados_pdf["data_br"]   = f"{data_iso[8:10]}/{data_iso[5:7]}/{data_iso[:4]}"
        conn     = database.conectar()

        try:
            # ══════════════════════════════════════════════════════════════
            #  BLOCO 1 — Resumo de Canais
            # ══════════════════════════════════════════════════════════════
            rows_canal = conn.execute("""
                SELECT
                    canal,
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
                    ), 0) AS valor_liquido
                FROM vendas_pedidos p
                WHERE p.data = ?
                GROUP BY canal
                HAVING SUM(CASE WHEN NOT EXISTS(
                    SELECT 1 FROM vendas_pagamentos vp2
                    WHERE vp2.id_pedido = p.id
                      AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado')
                ) THEN 1 ELSE 0 END) > 0
                ORDER BY canal
            """, (data_iso,)).fetchall()

            total_qtd   = sum(r["qtd"] for r in rows_canal)
            total_valor = sum(r["valor_liquido"] for r in rows_canal)

            _dados_pdf["canais"] = [
                {"canal": r["canal"],
                 "canal_amigavel": CANAL_NOMES.get(r["canal"], r["canal"]),
                 "qtd": r["qtd"],
                 "valor_liquido": r["valor_liquido"]}
                for r in rows_canal
            ]

            linhas_c = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(CANAL_NOMES.get(r["canal"], r["canal"]))),
                    ft.DataCell(ft.Text(str(r["qtd"]))),
                    ft.DataCell(ft.Text(f"R$ {r['valor_liquido']:.2f}")),
                ])
                for r in rows_canal
            ]
            linhas_c.append(_row_total("TOTAL", str(total_qtd), f"R$ {total_valor:.2f}"))

            bloco1 = _card(
                "Resumo por Canal",
                _tabela(["Canal", "Qtd Pedidos", "Valor Total"], _semvazio(linhas_c, 3)),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 2 — Pagamentos (excluindo CORTESIA)
            # ══════════════════════════════════════════════════════════════
            # Para pedidos com pagamento único, usa p.valor_total (evita
            # divergência quando vp.valor foi gravado como 0 por engano).
            # Para split (múltiplos pagamentos), usa vp.valor normalmente.
            # Exclui pedidos que tenham qualquer linha com cortesia=1
            # (mesma lógica do BLOCO 1).
            rows_pag = conn.execute("""
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
                WHERE p.data = ?
                  AND COALESCE(m.tipo, 'OUTROS') != 'CORTESIA'
                  AND vp.metodo != 'Fiado'
                  AND NOT EXISTS (
                      SELECT 1 FROM vendas_pagamentos vp2
                      WHERE vp2.id_pedido = p.id
                        AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado')
                  )
                GROUP BY vp.metodo, m.tipo
                ORDER BY m.tipo, vp.metodo
            """, (data_iso,)).fetchall()

            total_pag = sum(r["total"]       for r in rows_pag)
            total_qtd = sum(r["qtd_pedidos"] for r in rows_pag)
            _dados_pdf["pagamentos"] = [
                {"metodo": r["metodo"], "tipo": r["tipo"],
                 "qtd_pedidos": r["qtd_pedidos"], "total": r["total"]}
                for r in rows_pag
            ]
            linhas_p  = []
            for r in rows_pag:
                destaque = r["tipo"] == "BENEFICIO"
                cor = ft.Colors.BLUE_200 if destaque else None
                linhas_p.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(r["metodo"], color=cor)),
                    ft.DataCell(ft.Text(str(r["qtd_pedidos"]), color=cor)),
                    ft.DataCell(ft.Text(f"R$ {r['total']:.2f}", color=cor)),
                ]))
            linhas_p.append(_row_total("TOTAL", str(total_qtd), f"R$ {total_pag:.2f}"))

            n_split = conn.execute("""
                SELECT COUNT(*) FROM (
                    SELECT id_pedido
                    FROM vendas_pagamentos vp
                    JOIN vendas_pedidos p ON p.id = vp.id_pedido
                    WHERE p.data = ?
                      AND vp.cortesia = 0
                      AND vp.metodo != 'Fiado'
                    GROUP BY id_pedido
                    HAVING COUNT(*) > 1
                      AND COUNT(DISTINCT vp.metodo) > 1
                )
            """, (data_iso,)).fetchone()[0]

            bloco2 = _card(
                "Pagamentos",
                ft.Text(
                    "VA/VR destacados em azul  ·  Voucher/Cortesia e Fiado excluídos",
                    size=12, color=ft.Colors.GREY_500, italic=True,
                ),
                _tabela(["Método", "Qtd Pedidos", "Valor Total"], _semvazio(linhas_p, 3)),
                ft.Text(
                    f"A quantidade de transações pode ser maior que a de pedidos "
                    f"quando o cliente paga com mais de um método. "
                    f"Hoje foram {n_split} pedido(s) com pagamento dividido.",
                    size=12, color=ft.Colors.GREY_500, italic=True,
                ),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 3 — Detalhamento Plataformas
            # ══════════════════════════════════════════════════════════════
            plat_db = {
                p["nome"]: dict(p)
                for p in database.plataforma_listar(apenas_ativas=False)
            }
            _dados_pdf["plataformas"] = {}

            def _conteudo_plataforma(nome_plat: str) -> ft.Control:
                plat         = plat_db.get(nome_plat, {})
                comissao_pct = plat.get("comissao_pct",       0.0)
                tx_trans_pct = plat.get("taxa_transacao_pct", 0.0)
                subsidio_pp  = plat.get("subsidio",           0.0)

                r_bruto = conn.execute("""
                    SELECT COUNT(*) AS qtd, COALESCE(SUM(valor_total), 0) AS bruto
                    FROM vendas_pedidos
                    WHERE data = ? AND canal LIKE ?
                """, (data_iso, f"{nome_plat}%")).fetchone()

                qtd   = r_bruto["qtd"]   if r_bruto else 0
                bruto = r_bruto["bruto"] if r_bruto else 0.0

                # Split online (plataforma repassa) vs maquininha (já recebido)
                # Usa CTE pag_count para tratar pedidos com vp.valor=0
                placeholders = ",".join("?" * len(_METODOS_DIRETOS))
                row_split = conn.execute(f"""
                    WITH pc AS (
                        SELECT id_pedido, COUNT(*) AS qtd
                        FROM vendas_pagamentos
                        GROUP BY id_pedido
                    )
                    SELECT
                        COALESCE(SUM(CASE
                            WHEN vp.metodo NOT IN ({placeholders})
                            THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END
                            ELSE 0
                        END), 0) AS bruto_online,
                        COALESCE(SUM(CASE
                            WHEN vp.metodo IN ({placeholders})
                            THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END
                            ELSE 0
                        END), 0) AS bruto_maq
                    FROM vendas_pagamentos vp
                    JOIN vendas_pedidos p ON p.id = vp.id_pedido
                    JOIN pc ON pc.id_pedido = vp.id_pedido
                    WHERE p.data = ? AND p.canal LIKE ?
                """, (*_METODOS_DIRETOS, *_METODOS_DIRETOS, data_iso, f"{nome_plat}%")).fetchone()

                bruto_online = row_split["bruto_online"] if row_split else 0.0
                bruto_maq    = row_split["bruto_maq"]    if row_split else 0.0

                comissao_online = bruto_online * comissao_pct / 100
                tx_trans        = bruto_online * tx_trans_pct / 100
                comissao_maq    = bruto_maq    * comissao_pct / 100
                subsidio        = qtd * subsidio_pp
                liquido = (bruto_online - comissao_online - tx_trans) - comissao_maq + subsidio

                def _item(label: str, valor: float, bold=False, verde=False, vermelho=False, muted=False):
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
                            f"R$ {valor:.2f}",
                            expand=1,
                            text_align=ft.TextAlign.RIGHT,
                            color=cor, weight=w, size=13,
                        ),
                    ])

                itens = [
                    _item(f"Pedidos: {qtd}   |   Bruto total", bruto),
                    ft.Divider(height=1),
                    _item(f"Pago online (plataforma repassa)", bruto_online),
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

                _dados_pdf["plataformas"][nome_plat] = {
                    "qtd": qtd, "bruto": bruto,
                    "bruto_online": bruto_online, "bruto_maq": bruto_maq,
                    "comissao_online": comissao_online, "tx_trans": tx_trans,
                    "comissao_maq": comissao_maq, "subsidio": subsidio,
                    "liquido": liquido,
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

            bloco3 = _card(
                "Detalhamento Plataformas",
                ft.Container(height=260, content=plat_tabs),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 4 — Entregadores
            # ══════════════════════════════════════════════════════════════
            entregadores = database.pessoa_listar(tipo="ENTREGADOR", apenas_ativos=False)
            linhas_e = []
            _dados_pdf["entregadores"] = []
            for ent in entregadores:
                r = database.calcular_pagamento_entregador(ent["id"], data_iso)
                if r["total_entregas"] == 0:
                    continue
                _dados_pdf["entregadores"].append({
                    "nome": ent["nome"],
                    "total_entregas": r["total_entregas"],
                    "soma_taxas":     r["soma_taxas"],
                    "diaria":         r["diaria"],
                    "corridas_extras":r["corridas_extras"],
                    "vales":          r["vales"],
                    "total_liquido":  r["total_liquido"],
                })
                linhas_e.append(ft.DataRow(cells=[
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
                ]))

            # Total geral de taxas cobradas dos clientes (exceto canais com entregador da plataforma)
            row_taxas = conn.execute("""
                SELECT COALESCE(SUM(p.taxa_entrega), 0) AS total
                FROM vendas_pedidos p
                LEFT JOIN cad_canais c ON c.nome = p.canal
                WHERE p.data = ?
                  AND COALESCE(c.entregador_plataforma, 0) = 0
            """, (data_iso,)).fetchone()
            total_taxas_dia = row_taxas["total"] if row_taxas else 0.0

            row_repasse = conn.execute("""
                SELECT COALESCE(SUM(p.repasse_entregador), 0) AS total
                FROM vendas_pedidos p
                LEFT JOIN cad_canais c ON c.nome = p.canal
                WHERE p.data = ?
                  AND COALESCE(c.entregador_plataforma, 0) = 0
            """, (data_iso,)).fetchone()
            total_repasse_dia = row_repasse["total"] if row_repasse else 0.0

            bloco4 = _card(
                "Entregadores",
                _tabela(
                    ["Nome", "Entregas", "Repasses", "Diária",
                     "Extras", "Vales", "Total a Pagar"],
                    _semvazio(linhas_e, 7),
                ),
                ft.Divider(height=1),
                ft.Column(spacing=4, controls=[
                    ft.Text(
                        f"Taxas recebidas por clientes: R$ {total_taxas_dia:.2f}",
                        size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300,
                    ),
                    ft.Text(
                        f"Total pago aos entregadores: R$ {total_repasse_dia:.2f}",
                        size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_300,
                    ),
                    ft.Text(
                        f"Saldo de taxas: R$ {total_taxas_dia - total_repasse_dia:.2f}",
                        size=13, weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_400 if total_taxas_dia >= total_repasse_dia
                              else ft.Colors.RED_400,
                    ),
                ]),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 5 — Caixa e Troco
            # ══════════════════════════════════════════════════════════════
            database.fluxo_caixa_abrir(data_iso)
            fc   = database.fluxo_caixa_buscar(data_iso)
            calc = database.fluxo_caixa_recalcular(data_iso)

            tf_troco     = ft.TextField(
                label="Troco Inicial (R$)",
                value=f"{fc['troco_inicial']:.2f}" if fc else "0.00",
                keyboard_type=ft.KeyboardType.NUMBER,
                expand=True,
            )
            tf_saldo_real = ft.TextField(
                label="Saldo Real Gaveta (R$)",
                value=f"{fc['saldo_gaveta_real']:.2f}" if fc else "0.00",
                keyboard_type=ft.KeyboardType.NUMBER,
                expand=True,
            )

            entradas  = calc.get("total_especie_entradas", 0.0)
            saidas    = calc.get("total_especie_saidas",   0.0)
            saldo_teo = calc.get("saldo_teorico",          0.0)
            saldo_rl  = fc["saldo_gaveta_real"] if fc else 0.0
            dif_ini   = saldo_rl - saldo_teo

            _dados_pdf["caixa"] = {
                "troco_inicial":          fc["troco_inicial"] if fc else 0.0,
                "total_especie_entradas": entradas,
                "total_especie_saidas":   saidas,
                "saldo_teorico":          saldo_teo,
                "saldo_gaveta_real":      saldo_rl,
                "diferenca":              dif_ini,
            }
            _dados_pdf["taxas_entrega"] = {
                "recebidas":  total_taxas_dia,
                "repassadas": total_repasse_dia,
                "saldo":      total_taxas_dia - total_repasse_dia,
            }

            def _cor_dif(d: float) -> str:
                if d == 0:   return ft.Colors.GREEN_400
                if d > 0:    return ft.Colors.YELLOW_400
                return ft.Colors.RED_400

            txt_entradas = ft.Text(f"Entradas Espécie:  R$ {entradas:.2f}", size=14)
            txt_saidas   = ft.Text(f"Saídas Espécie:    R$ {saidas:.2f}",   size=14)
            txt_teo      = ft.Text(
                f"Saldo Teórico:     R$ {saldo_teo:.2f}",
                size=14, weight=ft.FontWeight.BOLD,
            )
            txt_dif      = ft.Text(
                f"Diferença:         R$ {dif_ini:.2f}",
                size=14, weight=ft.FontWeight.BOLD,
                color=_cor_dif(dif_ini),
            )

            # Banner de divergência — oculto até o primeiro fechamento
            banner_divergencia = ft.Container(visible=False)

            def _salvar_fechamento(ev):
                troco = _to_float(tf_troco.value)
                real  = _to_float(tf_saldo_real.value)
                database.fluxo_caixa_atualizar(data_iso, troco_inicial=troco)
                res = database.fluxo_caixa_fechar(data_iso, real)
                dif = res["diferenca"]
                txt_entradas.value = f"Entradas Espécie:  R$ {res['total_especie_entradas']:.2f}"
                txt_saidas.value   = f"Saídas Espécie:    R$ {res['total_especie_saidas']:.2f}"
                txt_teo.value      = f"Saldo Teórico:     R$ {res['saldo_teorico']:.2f}"
                txt_dif.value      = f"Diferença:         R$ {dif:.2f}"
                txt_dif.color      = _cor_dif(dif)

                # Banner de alerta para divergências significativas
                limite = _to_float(
                    database.config_obter("limite_divergencia_caixa", "5.00")
                )
                if abs(dif) > limite:
                    if dif < 0:
                        bg  = ft.Colors.RED_900
                        msg = (
                            f"A gaveta está R$ {abs(dif):.2f} abaixo do esperado. "
                            "Verifique se houve sangria não registrada ou troco errado."
                        )
                    else:
                        bg  = ft.Colors.ORANGE_900
                        msg = (
                            f"A gaveta está R$ {dif:.2f} acima do esperado. "
                            "Verifique se houve entrada não registrada."
                        )
                    banner_divergencia.padding      = ft.Padding.all(12)
                    banner_divergencia.border_radius = 8
                    banner_divergencia.bgcolor       = bg
                    banner_divergencia.content       = ft.Row(
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                                    color=ft.Colors.YELLOW_300, size=24),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        "Divergência de caixa detectada",
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.WHITE,
                                    ),
                                    ft.Text(
                                        msg, size=12,
                                        color=ft.Colors.with_opacity(
                                            0.85, ft.Colors.WHITE
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    )
                    banner_divergencia.visible = True
                else:
                    banner_divergencia.visible = False

                page.overlay.append(ft.SnackBar(
                    content=ft.Text("Fechamento salvo!"),
                    bgcolor=ft.Colors.GREEN_700,
                    open=True,
                ))
                page.update()

            # ── Modo fechamento cego ─────────────────────────────────────────
            modo_cego = database.config_obter("fechamento_cego", "0") == "1"

            if not modo_cego:
                bloco5 = _card(
                    "Caixa e Troco",
                    ft.Row([tf_troco, tf_saldo_real], spacing=12),
                    txt_entradas,
                    txt_saidas,
                    txt_teo,
                    txt_dif,
                    banner_divergencia,
                    ft.ElevatedButton(
                        "Salvar Fechamento",
                        icon=ft.Icons.LOCK_CLOCK,
                        on_click=_salvar_fechamento,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.INDIGO_600,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                )
            else:
                # FASE 1: ocultar valores teóricos
                txt_entradas.visible = False
                txt_saidas.visible   = False
                txt_teo.visible      = False
                txt_dif.visible      = False

                txt_msg_cego = ft.Text(
                    "Modo fechamento cego ativo. Informe o valor contado "
                    "na gaveta sem consultar o sistema.",
                    italic=True, color=ft.Colors.GREY_500, size=13,
                )
                banner_resultado_cego = ft.Container(visible=False)
                btn_registrado_cego   = ft.ElevatedButton(
                    "Fechamento Registrado",
                    icon=ft.Icons.CHECK,
                    disabled=True,
                    visible=False,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.GREY_700,
                        color=ft.Colors.GREEN_400,
                    ),
                )

                def _confirmar_contagem_cego(ev):
                    troco = _to_float(tf_troco.value)
                    real  = _to_float(tf_saldo_real.value)
                    database.fluxo_caixa_atualizar(data_iso, troco_inicial=troco)
                    res = database.fluxo_caixa_fechar(data_iso, real)
                    dif = res["diferenca"]

                    # Atualizar e revelar valores teóricos (FASE 2)
                    txt_entradas.value   = f"Entradas Espécie:  R$ {res['total_especie_entradas']:.2f}"
                    txt_saidas.value     = f"Saídas Espécie:    R$ {res['total_especie_saidas']:.2f}"
                    txt_teo.value        = f"Saldo Teórico:     R$ {res['saldo_teorico']:.2f}"
                    txt_dif.value        = f"Diferença:         R$ {dif:.2f}"
                    txt_dif.color        = _cor_dif(dif)
                    txt_entradas.visible = True
                    txt_saidas.visible   = True
                    txt_teo.visible      = True
                    txt_dif.visible      = True

                    # Banner de resultado
                    if dif == 0:
                        bg_res  = ft.Colors.GREEN_700
                        msg_res = "Caixa fechado sem divergências."
                    elif dif > 0:
                        bg_res  = ft.Colors.YELLOW_800
                        msg_res = f"Sobra de R$ {dif:.2f} na gaveta."
                    else:
                        bg_res  = ft.Colors.RED_700
                        msg_res = f"Falta de R$ {abs(dif):.2f} na gaveta."

                    banner_resultado_cego.bgcolor       = bg_res
                    banner_resultado_cego.padding       = ft.Padding.all(12)
                    banner_resultado_cego.border_radius = 8
                    banner_resultado_cego.content       = ft.Text(
                        msg_res,
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD,
                    )
                    banner_resultado_cego.visible = True

                    # Trocar botão
                    btn_confirmar_cego.visible  = False
                    btn_registrado_cego.visible = True

                    page.overlay.append(ft.SnackBar(
                        content=ft.Text("Fechamento salvo!"),
                        bgcolor=ft.Colors.GREEN_700, open=True,
                    ))
                    page.update()

                btn_confirmar_cego = ft.ElevatedButton(
                    "Confirmar Contagem",
                    icon=ft.Icons.LOCK_CLOCK,
                    on_click=_confirmar_contagem_cego,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.INDIGO_600,
                        color=ft.Colors.WHITE,
                    ),
                )

                bloco5 = _card(
                    "Caixa e Troco",
                    txt_msg_cego,
                    ft.Row([tf_troco, tf_saldo_real], spacing=12),
                    txt_entradas,
                    txt_saidas,
                    txt_teo,
                    txt_dif,
                    banner_resultado_cego,
                    btn_confirmar_cego,
                    btn_registrado_cego,
                )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 6 — Extras do Dia
            # ══════════════════════════════════════════════════════════════
            movs      = database.mov_extra_listar_por_data(data_iso)
            _dados_pdf["extras"] = [
                {"nome_pessoa": m["nome_pessoa"], "categoria": m["categoria"],
                 "fluxo": m["fluxo"], "metodo": m["metodo"],
                 "valor": m["valor"], "obs": m["obs"] or ""}
                for m in movs
            ]
            linhas_x  = []
            for m in movs:
                fluxo = m["fluxo"]
                if fluxo == "ENTRADA":
                    cor_f = ft.Colors.GREEN_400
                elif fluxo == "SAIDA":
                    cor_f = ft.Colors.RED_400
                else:   # NEUTRO
                    cor_f = ft.Colors.GREY_500
                linhas_x.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(m["nome_pessoa"] or "—")),
                    ft.DataCell(ft.Text(m["categoria"])),
                    ft.DataCell(ft.Text(fluxo, color=cor_f)),
                    ft.DataCell(ft.Text(m["metodo"] or "—")),
                    ft.DataCell(ft.Text(f"R$ {m['valor']:.2f}")),
                    ft.DataCell(ft.Text(m["obs"] or "")),
                ]))

            bloco6 = _card(
                "Movimentações do Dia",
                _tabela(
                    ["Funcionário", "Categoria", "Fluxo", "Método", "Valor", "Obs"],
                    _semvazio(linhas_x, 6),
                ),
            )

            row_fiados = conn.execute("""
                SELECT COUNT(DISTINCT p.id) AS qtd,
                       COALESCE(SUM(p.valor_total), 0) AS total
                FROM vendas_pedidos p
                JOIN vendas_pagamentos vp ON vp.id_pedido = p.id
                WHERE p.data = ?
                  AND vp.metodo = 'Fiado'
            """, (data_iso,)).fetchone()

            row_cortesias = conn.execute("""
                SELECT COUNT(DISTINCT p.id) AS qtd,
                       COALESCE(SUM(p.valor_total), 0) AS total
                FROM vendas_pedidos p
                JOIN vendas_pagamentos vp ON vp.id_pedido = p.id
                WHERE p.data = ?
                  AND (vp.cortesia = 1 OR vp.metodo = 'Voucher')
            """, (data_iso,)).fetchone()

            qtd_fiados          = row_fiados["qtd"]    if row_fiados    else 0
            total_fiados        = row_fiados["total"]  if row_fiados    else 0.0
            qtd_cortesias       = row_cortesias["qtd"] if row_cortesias else 0
            total_cortesias_det = row_cortesias["total"] if row_cortesias else 0.0

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
                    "Valores não somados ao faturamento do dia.",
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

        bloco7 = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    expand=True,
                    content=_mini_card_info(
                        "Fiados do Dia",
                        qtd_fiados,
                        total_fiados,
                        ft.Colors.ORANGE_300,
                        obs="Consulte a tela de Fiados para detalhes e quitações."
                        if qtd_fiados > 0 else None,
                    ),
                ),
                ft.Container(
                    expand=True,
                    content=_mini_card_info(
                        "Cortesias e Vouchers do Dia",
                        qtd_cortesias,
                        total_cortesias_det,
                        ft.Colors.PURPLE_300,
                    ),
                ),
            ],
        )

        linha_resumo = ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(expand=True, content=bloco1),
                ft.Container(expand=True, content=bloco2),
            ],
        )
        col_relatorio.controls.clear()
        col_relatorio.controls += [linha_resumo, bloco3, bloco4, bloco5, bloco6, bloco7]
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
        data_iso = _data_br_para_iso(tf_data.value or hoje_br)
        caminho  = gerar_pdf_diario(data_iso, _dados_pdf)
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
            caminho = excel_relatorio_diario(_dados_pdf.get("data_br", ""), _dados_pdf)
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

    # ── Topo ──────────────────────────────────────────────────────────────
    btn_gerar = ft.ElevatedButton(
        "Gerar Relatório",
        icon=ft.Icons.ASSESSMENT,
        on_click=_gerar,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.TEAL_600,
            color=ft.Colors.WHITE,
        ),
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

    tf_data.on_submit = _gerar

    _gerar()

    topo = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Row(
            controls=[
                tf_data,
                btn_calendario,
                btn_gerar,
                btn_exportar_excel,
                btn_exportar_pdf,
            ],
            spacing=16,
        ),
    ))

    return ft.Column(
        controls=[topo, col_relatorio],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
