"""
views/dashboard.py — Dashboard com resumo do dia atual.
Layout: grade 2×1 (Vendas | Caixa) + card largo Presença de Hoje.
"""

import flet as ft
from datetime import date

import database


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

_TIPOS_ESCALA = ["TRABALHOU", "FALTA", "FOLGA", "FERIADO", "EXTRA"]


# ── Utilitários ────────────────────────────────────────────────────────────────

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


def _linha(label: str, valor: str, color=None, bold=False) -> ft.Row:
    weight = ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL
    return ft.Row(controls=[
        ft.Text(label, expand=3, size=13),
        ft.Text(
            valor, expand=2,
            text_align=ft.TextAlign.RIGHT,
            color=color, weight=weight, size=13,
        ),
    ])


def _cor_dif(d: float) -> str:
    if d == 0:
        return ft.Colors.GREEN_400
    if d > 0:
        return ft.Colors.YELLOW_400
    return ft.Colors.RED_400


# ── View principal ─────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    _data_atual = {"iso": date.today().isoformat()}

    # Colunas mutáveis dos cards 1 e 2
    card1_col    = ft.Column(spacing=8)
    card2_col    = ft.Column(spacing=8)

    # Coluna mutável do card Alertas de Estoque
    alertas_col = ft.Column(spacing=6)

    # Coluna mutável do card Presença
    presenca_col = ft.Column(spacing=4)

    # Coluna mutável do card Alertas de Boletos
    alertas_boletos_col = ft.Column(spacing=6)

    # ── Cards 1 e 2 ────────────────────────────────────────────────────────────

    def _atualizar_cards_1_2(conn):
        """Preenche card1_col e card2_col. Reutiliza conn já aberta."""

        # Card 1 — Resumo de Vendas
        rows_canal = conn.execute("""
            SELECT
                canal,
                COUNT(*) AS qtd,
                COALESCE(SUM(
                    CASE WHEN EXISTS(
                        SELECT 1 FROM vendas_pagamentos vp
                        WHERE vp.id_pedido = p.id
                          AND (vp.cortesia = 1 OR vp.metodo = 'Fiado')
                    ) THEN 0.0 ELSE p.valor_total END
                ), 0) AS valor_real
            FROM vendas_pedidos p
            WHERE p.data = ?
            GROUP BY canal
            ORDER BY canal
        """, (_data_atual["iso"],)).fetchall()

        total_qtd   = sum(r["qtd"]       for r in rows_canal)
        total_valor = sum(r["valor_real"] for r in rows_canal)

        linhas_canal = []
        for r in rows_canal:
            nome = CANAL_NOMES.get(r["canal"], r["canal"])
            linhas_canal.append(ft.Row(controls=[
                ft.Text(nome,              expand=5, size=12),
                ft.Text(str(r["qtd"]),     expand=1, size=12,
                        text_align=ft.TextAlign.CENTER),
                ft.Text(f"R$ {r['valor_real']:.2f}", expand=2, size=12,
                        text_align=ft.TextAlign.RIGHT),
            ]))

        c1 = [
            _linha("Total de pedidos:", str(total_qtd)),
            _linha("Faturamento real:", f"R$ {total_valor:.2f}",
                   bold=True, color=ft.Colors.GREEN_300),
            ft.Divider(height=1),
            ft.Row(controls=[
                ft.Text("Canal",  expand=5, size=12, weight=ft.FontWeight.BOLD,
                        color=None),
                ft.Text("Qtd",    expand=1, size=12, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER, color=None),
                ft.Text("Valor",  expand=2, size=12, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.RIGHT,  color=None),
            ]),
        ]
        if linhas_canal:
            c1.extend(linhas_canal)
        else:
            c1.append(ft.Text("Sem vendas hoje.", italic=True,
                              color=ft.Colors.GREY_500))

        card1_col.controls.clear()
        card1_col.controls.extend(c1)

        # Card 2 — Status do Caixa
        modo_cego = database.config_obter("fechamento_cego", "0") == "1"
        database.fluxo_caixa_abrir(_data_atual["iso"])
        fc   = database.fluxo_caixa_buscar(_data_atual["iso"])
        calc = database.fluxo_caixa_recalcular(_data_atual["iso"])

        troco    = fc["troco_inicial"]     if fc else 0.0
        entradas = calc.get("total_especie_entradas", 0.0)
        saidas   = calc.get("total_especie_saidas",   0.0)
        saldo    = calc.get("saldo_teorico",          0.0)
        real     = fc["saldo_gaveta_real"] if fc else 0.0
        dif      = real - saldo

        linhas_caixa = [
            _linha("Troco inicial:",    f"R$ {troco:.2f}"),
            _linha("Entradas espécie:", f"R$ {entradas:.2f}"),
            _linha("Saídas espécie:",   f"R$ {saidas:.2f}"),
            ft.Divider(height=1),
            _linha("Saldo teórico:",    f"R$ {saldo:.2f}", bold=True),
        ]
        if not modo_cego:
            linhas_caixa.append(
                _linha("Diferença:", f"R$ {dif:.2f}", bold=True, color=_cor_dif(dif))
            )

        card2_col.controls.clear()
        card2_col.controls.extend(linhas_caixa)

    # ── Card Presença de Hoje ───────────────────────────────────────────────────

    def _atualizar_presenca():
        """Reconstrói a lista de linhas do card Presença de Hoje."""

        _hoje = _data_atual["iso"]
        _hoje_wd = date.fromisoformat(_hoje).weekday()

        # 1. Pré-popula escalas a partir dos dias fixos cadastrados
        database.escala_pre_popular_do_dia(_hoje)

        # 2. Horário padrão do dia fixo: id_pessoa -> horario_entrada
        horario_fixo: dict = {}
        for row in database.dias_fixos_listar_todos():
            if row["dia_semana"] == _hoje_wd:
                horario_fixo[row["id_pessoa"]] = row["horario_entrada"] or ""

        # 3. Escalas já registradas hoje: id_pessoa -> tipo
        escalas_hoje: dict = {
            e["id_pessoa"]: e["tipo"]
            for e in database.escala_listar_por_data(_hoje)
        }

        # 4. Pontos já registrados hoje: id_pessoa -> (hora_entrada, hora_saida)
        todos = sorted(
            database.pessoa_listar(apenas_ativos=True),
            key=lambda p: (0 if p["tipo"] == "INTERNO" else 1, p["nome"]),
        )
        pontos_hoje: dict = {}
        for pessoa in todos:
            pt = database.ponto_buscar(_hoje, pessoa["id"])
            pontos_hoje[pessoa["id"]] = (
                (pt["hora_entrada"] or "") if pt else "",
                (pt["hora_saida"]   or "") if pt else "",
            )

        presenca_col.controls.clear()

        if not todos:
            presenca_col.controls.append(
                ft.Text(
                    "Nenhuma pessoa ativa cadastrada. Acesse Parâmetros > Pessoas.",
                    italic=True, color=ft.Colors.GREY_500,
                )
            )
            return

        # Cabeçalho
        presenca_col.controls.append(ft.Row(controls=[
            ft.Container(expand=4, content=ft.Text(
                "Nome / Cargo", size=12, weight=ft.FontWeight.BOLD,
                color=None,
            )),
            ft.Container(expand=3, content=ft.Text(
                "Status", size=12, weight=ft.FontWeight.BOLD,
                color=None,
            )),
            ft.Container(expand=3, content=ft.Text(
                "Entrada / Saída", size=12, weight=ft.FontWeight.BOLD,
                color=None,
            )),
            ft.Container(expand=1),
        ]))
        presenca_col.controls.append(ft.Divider(height=1))

        for pessoa in todos:
            pid      = pessoa["id"]
            nome     = pessoa["nome"]
            desc     = pessoa["cargo"] or pessoa["tipo"]
            ja_salvo = pid in escalas_hoje

            dd = ft.Dropdown(
                value=escalas_hoje.get(pid),
                width=155,
                options=[ft.dropdown.Option(t) for t in _TIPOS_ESCALA],
            )

            ent_ini, ent_sai = pontos_hoje.get(pid, ("", ""))
            tf = ft.TextField(
                value=ent_ini or horario_fixo.get(pid, ""),
                width=80,
                hint_text="Entrada",
                text_align=ft.TextAlign.CENTER,
            )
            tf_saida = ft.TextField(
                value=ent_sai,
                width=80,
                hint_text="Saída",
                text_align=ft.TextAlign.CENTER,
            )

            # Container do botão — conteúdo trocado in-place após salvar
            btn_container = ft.Container(expand=1)

            def _validar_hora(hora: str) -> bool:
                if not hora:
                    return True
                partes = hora.split(":")
                return (
                    len(partes) == 2
                    and all(p.isdigit() for p in partes)
                    and 0 <= int(partes[0]) <= 23
                    and 0 <= int(partes[1]) <= 59
                )

            def _registrar(e, _pid=pid, _nome=nome, _dd=dd, _tf=tf,
                           _tf_sai=tf_saida, _btn=btn_container):
                tipo = _dd.value
                # Validação 1: status obrigatório
                if not tipo:
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text(f"Selecione o status de {_nome}."),
                        bgcolor=ft.Colors.ORANGE_700, open=True,
                    ))
                    page.update()
                    return
                hora_ent = _tf.value.strip()
                hora_sai = _tf_sai.value.strip()
                # Validação 2: formato HH:MM
                for hora, label in ((hora_ent, "entrada"), (hora_sai, "saída")):
                    if hora and not _validar_hora(hora):
                        page.overlay.append(ft.SnackBar(
                            content=ft.Text(
                                f"Horário de {label} inválido para {_nome}. "
                                "Use o formato HH:MM."
                            ),
                            bgcolor=ft.Colors.ORANGE_700, open=True,
                        ))
                        page.update()
                        return
                # Salvar escala
                database.escala_registrar(_data_atual["iso"], _pid, tipo)
                # Salvar pontos se TRABALHOU
                if tipo == "TRABALHOU":
                    if hora_ent:
                        database.ponto_registrar_entrada(_data_atual["iso"], _pid, hora_ent)
                    if hora_sai:
                        database.ponto_registrar_saida(_data_atual["iso"], _pid, hora_sai)
                # Feedback visual: troca o botão pelo ícone de check
                _btn.content = ft.Icon(
                    ft.Icons.CHECK_CIRCLE,
                    color=ft.Colors.GREEN_400,
                    size=24,
                )
                # Atualiza cards 1 e 2
                conn = database.conectar()
                try:
                    _atualizar_cards_1_2(conn)
                finally:
                    conn.close()
                # SnackBar de confirmação
                page.overlay.append(ft.SnackBar(
                    content=ft.Text(
                        f"Presença de {_nome} registrada como {tipo}."
                    ),
                    bgcolor=ft.Colors.GREEN_700, open=True,
                ))
                page.update()

            # Estado inicial do botão
            if ja_salvo:
                btn_container.content = ft.Icon(
                    ft.Icons.CHECK_CIRCLE,
                    color=ft.Colors.GREEN_400,
                    size=24,
                )
            else:
                btn_container.content = ft.ElevatedButton(
                    "OK",
                    on_click=_registrar,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.TEAL_700,
                        color=ft.Colors.WHITE,
                    ),
                )

            presenca_col.controls.append(ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(expand=4, content=ft.Column(
                        spacing=0,
                        controls=[
                            ft.Text(nome, size=13, weight=ft.FontWeight.W_500),
                            ft.Text(desc, size=11, color=ft.Colors.GREY_500),
                        ],
                    )),
                    ft.Container(expand=3, content=dd),
                    ft.Container(expand=3, content=ft.Row(
                        spacing=6,
                        controls=[tf, tf_saida],
                    )),
                    btn_container,
                ],
            ))

    # ── Card Alertas de Estoque ─────────────────────────────────────────────────

    def _atualizar_alertas_est():
        produtos = database.estoque_produtos_abaixo_minimo()
        alertas_col.controls.clear()

        if not produtos:
            card_alertas_est.visible = False
            return

        card_alertas_est.visible = True
        total = len(produtos)
        exibir = produtos[:5]

        alertas_col.controls.append(
            ft.Container(
                bgcolor=ft.Colors.ORANGE_900,
                border_radius=6,
                padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                content=ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                            color=ft.Colors.YELLOW_300, size=20),
                    ft.Text(
                        f"Estoque Baixo — {total} produto(s) abaixo do mínimo",
                        color=ft.Colors.YELLOW_300,
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    ),
                ]),
            )
        )

        for p in exibir:
            alertas_col.controls.append(ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.ORANGE_400, size=10),
                ft.Text(p["nome"], expand=True, size=13),
                ft.Text(
                    f"Atual: {p['quantidade_atual']:.1f} {p['unidade']}",
                    color=ft.Colors.RED_400,
                    size=13,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(" | ", color=ft.Colors.GREY_500, size=13),
                ft.Text(
                    f"Mínimo: {p['quantidade_minima']:.1f} {p['unidade']}",
                    color=ft.Colors.GREY_500,
                    size=13,
                ),
            ]))

        if total > 5:
            alertas_col.controls.append(ft.Text(
                f"... e mais {total - 5} produto(s). "
                "Veja a tela de Estoque para detalhes.",
                italic=True,
                color=ft.Colors.GREY_500,
                size=12,
            ))

    # ── Card Alertas de Boletos ────────────────────────────────────────────────

    def _atualizar_alertas_boletos():
        database.boleto_atualizar_status_vencidos()
        vencidos = database.boletos_vencidos_hoje()
        alertas_boletos_col.controls.clear()

        if not vencidos:
            card_alertas_boletos.visible = False
            return

        card_alertas_boletos.visible = True
        alertas_boletos_col.controls.append(ft.Container(
            bgcolor=ft.Colors.RED_900,
            border_radius=6,
            padding=ft.Padding(left=12, right=12, top=8, bottom=8),
            content=ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                        color=ft.Colors.YELLOW_300, size=20),
                ft.Text(
                    f"Boletos Vencidos/Vencendo Hoje — {len(vencidos)} item(s)",
                    color=ft.Colors.YELLOW_300,
                    weight=ft.FontWeight.BOLD,
                    size=14,
                ),
            ]),
        ))

        for v in vencidos[:5]:
            alertas_boletos_col.controls.append(ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.RED_400, size=10),
                ft.Text(
                    f"{v['nome_fornecedor']} — {v['descricao']}",
                    expand=True, size=13,
                ),
                ft.Text(
                    f"R$ {v['valor']:.2f} | Venc: {v['vencimento'][8:10]}/"
                    f"{v['vencimento'][5:7]}/{v['vencimento'][:4]}",
                    color=ft.Colors.RED_400,
                    size=13,
                    weight=ft.FontWeight.BOLD,
                ),
            ]))

        if len(vencidos) > 5:
            alertas_boletos_col.controls.append(ft.Text(
                f"... e mais {len(vencidos) - 5} item(s). "
                "Veja Fornecedores para detalhes.",
                italic=True, color=ft.Colors.GREY_500, size=12,
            ))

    # ── Atualização geral ───────────────────────────────────────────────────────

    def _atualizar(e=None):
        d = date.fromisoformat(_data_atual["iso"])
        txt_data_topo.value = f"Dashboard  —  {d.strftime('%d/%m/%Y')}"
        conn = database.conectar()
        try:
            _atualizar_cards_1_2(conn)
        finally:
            conn.close()
        _atualizar_alertas_est()
        _atualizar_alertas_boletos()
        _atualizar_presenca()
        page.update()

    # ── Barra superior ─────────────────────────────────────────────────────────

    btn_atualizar = ft.ElevatedButton(
        "Atualizar",
        icon=ft.Icons.REFRESH,
        on_click=_atualizar,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.INDIGO_600,
            color=ft.Colors.WHITE,
        ),
    )

    txt_data_topo = ft.Text(
        f"Dashboard  —  {date.today().strftime('%d/%m/%Y')}",
        size=18,
        weight=ft.FontWeight.BOLD,
        expand=True,
    )

    tf_data_dash = ft.TextField(
        value=date.today().strftime("%d/%m/%Y"),
        width=140,
        text_align=ft.TextAlign.CENTER,
        hint_text="DD/MM/AAAA",
    )

    def _on_date_picked_dash(e):
        if e.control.value:
            _data_atual["iso"] = e.control.value.strftime("%Y-%m-%d")
            tf_data_dash.value = e.control.value.strftime("%d/%m/%Y")
            _atualizar()

    date_picker_dash = ft.DatePicker(on_change=_on_date_picked_dash)
    page.overlay.append(date_picker_dash)

    btn_calendario_dash = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar data",
        on_click=lambda e: (
            setattr(date_picker_dash, "open", True),
            page.update(),
        ),
    )

    topo = ft.Card(content=ft.Container(
        padding=ft.Padding.all(12),
        content=ft.Row(
            controls=[
                txt_data_topo,
                tf_data_dash,
                btn_calendario_dash,
                btn_atualizar,
            ],
            spacing=16,
        ),
    ))

    # ── Grade 2 × 1 (Vendas | Caixa) ───────────────────────────────────────────

    grade = ft.Row(
        expand=True,
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Column(expand=True, spacing=16, controls=[
                _card("Resumo de Vendas do Dia", card1_col),
            ]),
            ft.Column(expand=True, spacing=16, controls=[
                _card("Status do Caixa", card2_col),
            ]),
        ],
    )

    # ── Card Alertas de Estoque (visível só quando há alertas) ──────────────────

    card_alertas_est = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=alertas_col,
        ),
    )

    # ── Card Alertas de Boletos (visível só quando há vencidos) ──────────────────

    card_alertas_boletos = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=alertas_boletos_col,
        ),
    )

    # ── Card largo — Presença de Hoje ───────────────────────────────────────────

    card_presenca = _card("Presença de Hoje", presenca_col)

    # Carrega todos os dados ao abrir a tela
    _atualizar()

    return ft.Column(
        controls=[topo, grade, card_alertas_est, card_alertas_boletos, card_presenca],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
