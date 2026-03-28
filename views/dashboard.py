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
    hoje    = date.today().isoformat()
    hoje_wd = date.today().weekday()   # 0=Seg … 6=Dom

    # Colunas mutáveis dos cards 1 e 2
    card1_col    = ft.Column(spacing=8)
    card2_col    = ft.Column(spacing=8)

    # Coluna mutável do card Presença
    presenca_col = ft.Column(spacing=4)

    # ── Cards 1 e 2 ────────────────────────────────────────────────────────────

    def _atualizar_cards_1_2(conn):
        """Preenche card1_col e card2_col. Reutiliza conn já aberta."""

        # Card 1 — Resumo de Vendas
        rows_canal = conn.execute("""
            SELECT
                canal,
                COUNT(*) AS qtd,
                COALESCE(SUM(
                    CASE
                        WHEN EXISTS(
                            SELECT 1 FROM vendas_pagamentos vp
                            WHERE vp.id_pedido = p.id AND vp.cortesia = 1
                        ) THEN 0.0
                        WHEN EXISTS(
                            SELECT 1 FROM vendas_pagamentos vp2
                            WHERE vp2.id_pedido = p.id AND vp2.metodo = 'Voucher'
                        ) THEN 0.0
                        ELSE p.valor_total
                    END
                ), 0) AS valor_real
            FROM vendas_pedidos p
            WHERE p.data = ?
            GROUP BY canal
            ORDER BY canal
        """, (hoje,)).fetchall()

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
        database.fluxo_caixa_abrir(hoje)
        fc   = database.fluxo_caixa_buscar(hoje)
        calc = database.fluxo_caixa_recalcular(hoje)

        troco    = fc["troco_inicial"]     if fc else 0.0
        entradas = calc.get("total_especie_entradas", 0.0)
        saidas   = calc.get("total_especie_saidas",   0.0)
        saldo    = calc.get("saldo_teorico",          0.0)
        real     = fc["saldo_gaveta_real"] if fc else 0.0
        dif      = real - saldo

        card2_col.controls.clear()
        card2_col.controls.extend([
            _linha("Troco inicial:",    f"R$ {troco:.2f}"),
            _linha("Entradas espécie:", f"R$ {entradas:.2f}"),
            _linha("Saídas espécie:",   f"R$ {saidas:.2f}"),
            ft.Divider(height=1),
            _linha("Saldo teórico:",    f"R$ {saldo:.2f}", bold=True),
            _linha("Diferença:",        f"R$ {dif:.2f}",
                   bold=True, color=_cor_dif(dif)),
        ])

    # ── Card Presença de Hoje ───────────────────────────────────────────────────

    def _atualizar_presenca():
        """Reconstrói a lista de linhas do card Presença de Hoje."""

        # 1. Pré-popula escalas a partir dos dias fixos cadastrados
        database.escala_pre_popular_do_dia(hoje)

        # 2. Horário padrão do dia fixo: id_pessoa -> horario_entrada
        horario_fixo: dict = {}
        for row in database.dias_fixos_listar_todos():
            if row["dia_semana"] == hoje_wd:
                horario_fixo[row["id_pessoa"]] = row["horario_entrada"] or ""

        # 3. Escalas já registradas hoje: id_pessoa -> tipo
        escalas_hoje: dict = {
            e["id_pessoa"]: e["tipo"]
            for e in database.escala_listar_por_data(hoje)
        }

        # 4. Pontos de entrada já registrados hoje: id_pessoa -> hora_entrada
        todos = sorted(
            database.pessoa_listar(apenas_ativos=True),
            key=lambda p: (0 if p["tipo"] == "INTERNO" else 1, p["nome"]),
        )
        pontos_hoje: dict = {}
        for pessoa in todos:
            pt = database.ponto_buscar(hoje, pessoa["id"])
            if pt and pt["hora_entrada"]:
                pontos_hoje[pessoa["id"]] = pt["hora_entrada"]

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
            ft.Container(expand=2, content=ft.Text(
                "Entrada", size=12, weight=ft.FontWeight.BOLD,
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

            tf = ft.TextField(
                value=pontos_hoje.get(pid) or horario_fixo.get(pid, ""),
                width=100,
                hint_text="HH:MM",
            )

            # Container do botão — conteúdo trocado in-place após salvar
            btn_container = ft.Container(expand=1)

            def _registrar(e, _pid=pid, _nome=nome, _dd=dd, _tf=tf,
                           _btn=btn_container):
                tipo = _dd.value
                # Validação 1: status obrigatório
                if not tipo:
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text(f"Selecione o status de {_nome}."),
                        bgcolor=ft.Colors.ORANGE_700, open=True,
                    ))
                    page.update()
                    return
                hora = _tf.value.strip()
                # Validação 2: formato HH:MM quando TRABALHOU + hora preenchida
                if tipo == "TRABALHOU" and hora:
                    partes = hora.split(":")
                    hhmm_ok = (
                        len(partes) == 2
                        and all(p.isdigit() for p in partes)
                        and 0 <= int(partes[0]) <= 23
                        and 0 <= int(partes[1]) <= 59
                    )
                    if not hhmm_ok:
                        page.overlay.append(ft.SnackBar(
                            content=ft.Text(
                                f"Horário inválido para {_nome}. "
                                "Use o formato HH:MM."
                            ),
                            bgcolor=ft.Colors.ORANGE_700, open=True,
                        ))
                        page.update()
                        return
                # Salvar escala
                database.escala_registrar(hoje, _pid, tipo)
                # Salvar ponto de entrada apenas se TRABALHOU + hora válida
                if tipo == "TRABALHOU" and hora:
                    database.ponto_registrar_entrada(hoje, _pid, hora)
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
                    ft.Container(expand=2, content=tf),
                    btn_container,
                ],
            ))

    # ── Atualização geral ───────────────────────────────────────────────────────

    def _atualizar(e=None):
        conn = database.conectar()
        try:
            _atualizar_cards_1_2(conn)
        finally:
            conn.close()
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

    topo = ft.Card(content=ft.Container(
        padding=ft.Padding.all(12),
        content=ft.Row(
            controls=[
                ft.Text(
                    f"Dashboard  —  {date.today().strftime('%d/%m/%Y')}",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
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

    # ── Card largo — Presença de Hoje ───────────────────────────────────────────

    card_presenca = _card("Presença de Hoje", presenca_col)

    # Carrega todos os dados ao abrir a tela
    _atualizar()

    return ft.Column(
        controls=[topo, grade, card_presenca],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
