"""
views/relatorio_diario.py — Relatório diário de fechamento de caixa.
"""

import flet as ft
from datetime import date

import database


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
                    1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
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
        color=ft.Colors.with_opacity(0.06, ft.Colors.WHITE),
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

    # ─────────────────────────────────────────────────────────────────────
    def _gerar(e=None):
        data_iso = _data_br_para_iso(tf_data.value or hoje_br)
        conn     = database.conectar()

        try:
            # ══════════════════════════════════════════════════════════════
            #  BLOCO 1 — Resumo de Canais
            # ══════════════════════════════════════════════════════════════
            rows_canal = conn.execute("""
                SELECT
                    canal,
                    COUNT(*) AS qtd,
                    COALESCE(SUM(
                        CASE WHEN EXISTS(
                            SELECT 1 FROM vendas_pagamentos vp
                            WHERE vp.id_pedido = p.id AND vp.cortesia = 1
                        ) THEN 0.0 ELSE p.valor_total END
                    ), 0) AS valor_liquido
                FROM vendas_pedidos p
                WHERE p.data = ?
                GROUP BY canal
                ORDER BY canal
            """, (data_iso,)).fetchall()

            total_qtd   = sum(r["qtd"] for r in rows_canal)
            total_valor = sum(r["valor_liquido"] for r in rows_canal)

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
                    SELECT id_pedido, COUNT(*) AS qtd
                    FROM vendas_pagamentos
                    GROUP BY id_pedido
                )
                SELECT vp.metodo,
                       COALESCE(m.tipo, 'OUTROS') AS tipo,
                       COALESCE(SUM(
                           CASE WHEN pc.qtd = 1
                                THEN p.valor_total
                                ELSE vp.valor
                           END
                       ), 0) AS total
                FROM vendas_pagamentos vp
                JOIN vendas_pedidos       p  ON p.id        = vp.id_pedido
                JOIN pag_count            pc ON pc.id_pedido = vp.id_pedido
                LEFT JOIN cad_metodos_pag m  ON m.nome      = vp.metodo
                WHERE p.data = ?
                  AND COALESCE(m.tipo, 'OUTROS') != 'CORTESIA'
                  AND NOT EXISTS (
                      SELECT 1 FROM vendas_pagamentos vp2
                      WHERE vp2.id_pedido = p.id AND vp2.cortesia = 1
                  )
                GROUP BY vp.metodo, m.tipo
                ORDER BY m.tipo, vp.metodo
            """, (data_iso,)).fetchall()

            total_pag = sum(r["total"] for r in rows_pag)
            linhas_p  = []
            for r in rows_pag:
                destaque = r["tipo"] == "BENEFICIO"
                cor = ft.Colors.BLUE_200 if destaque else None
                linhas_p.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(r["metodo"], color=cor)),
                    ft.DataCell(ft.Text(f"R$ {r['total']:.2f}", color=cor)),
                ]))
            linhas_p.append(_row_total("TOTAL", f"R$ {total_pag:.2f}"))

            bloco2 = _card(
                "Pagamentos",
                ft.Text(
                    "VA/VR destacados em azul  ·  Voucher/Cortesia excluídos",
                    size=12, color=ft.Colors.GREY_500, italic=True,
                ),
                _tabela(["Método", "Valor Total"], _semvazio(linhas_p, 2)),
            )

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 3 — Detalhamento Plataformas
            # ══════════════════════════════════════════════════════════════
            plat_db = {
                p["nome"]: dict(p)
                for p in database.plataforma_listar(apenas_ativas=False)
            }

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

                if nome_plat == "99Food":
                    custo_log = plat.get("custo_logistico_maximo", 0.0)
                    itens.append(_item("(-) Custo Logístico (máx)", custo_log, vermelho=True))
                    liquido -= custo_log

                itens += [
                    ft.Divider(height=1),
                    _item("Líquido Estimado", liquido, bold=True, verde=True),
                ]

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
            for ent in entregadores:
                r = database.calcular_pagamento_entregador(ent["id"], data_iso)
                if r["total_entregas"] == 0:
                    continue
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

            bloco4 = _card(
                "Entregadores",
                _tabela(
                    ["Nome", "Entregas", "Soma Taxas", "Diária",
                     "Extras", "Vales", "Total a Pagar"],
                    _semvazio(linhas_e, 7),
                ),
                ft.Divider(height=1),
                ft.Text(
                    f"Total Geral de Taxas de Entrega recebidas: R$ {total_taxas_dia:.2f}",
                    size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300,
                ),
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
                snack = ft.SnackBar(
                    content=ft.Text("Fechamento salvo!"),
                    bgcolor=ft.Colors.GREEN_700,
                    open=True,
                )
                page.overlay.append(snack)
                page.update()

            bloco5 = _card(
                "Caixa e Troco",
                ft.Row([tf_troco, tf_saldo_real], spacing=12),
                txt_entradas,
                txt_saidas,
                txt_teo,
                txt_dif,
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

            # ══════════════════════════════════════════════════════════════
            #  BLOCO 6 — Extras do Dia
            # ══════════════════════════════════════════════════════════════
            movs      = database.mov_extra_listar_por_data(data_iso)
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

        finally:
            conn.close()

        col_relatorio.controls.clear()
        col_relatorio.controls += [bloco1, bloco2, bloco3, bloco4, bloco5, bloco6]
        page.update()

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

    topo = ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Row(
            controls=[
                tf_data,
                btn_calendario,
                btn_gerar,
                ft.Text(
                    "Selecione a data e clique em Gerar Relatório",
                    color=ft.Colors.GREY_500,
                    italic=True,
                    size=13,
                ),
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
