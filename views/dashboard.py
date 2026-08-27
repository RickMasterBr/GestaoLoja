"""
views/dashboard.py — Dashboard executivo com resumo do dia atual.
Layout modular 2x2 com ações rápidas, alertas proativos e modal de presença.
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


# ── Utilitários de UI ─────────────────────────────────────────────────────────

def _card(titulo: str, *controls) -> ft.Card:
    return ft.Card(content=ft.Container(
        padding=ft.Padding.all(16),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text(titulo, size=15, weight=ft.FontWeight.BOLD),
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

    # Colunas dos cards executivos
    card1_col           = ft.Column(spacing=8)
    card2_col           = ft.Column(spacing=8)
    card_boletos_col    = ft.Column(spacing=8)
    card_presenca_col   = ft.Column(spacing=10)

    # Colunas de alertas proativos
    alertas_col         = ft.Column(spacing=6)
    alertas_boletos_col = ft.Column(spacing=6)

    # ── Card 1 & Card 2: Vendas e Caixa ───────────────────────────────────────

    def _atualizar_cards_1_2(conn):
        """Preenche card1_col (Vendas) e card2_col (Caixa)."""

        # 1. Resumo de Vendas
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
                ft.Text("Canal",  expand=5, size=12, weight=ft.FontWeight.BOLD),
                ft.Text("Qtd",    expand=1, size=12, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Valor",  expand=2, size=12, weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.RIGHT),
            ]),
        ]
        if linhas_canal:
            c1.extend(linhas_canal)
        else:
            c1.append(ft.Text("Sem vendas registradas hoje.", italic=True,
                              color=ft.Colors.GREY_500))

        card1_col.controls.clear()
        card1_col.controls.extend(c1)

        # 2. Status do Caixa
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
            _linha("Saldo teórico gaveta:", f"R$ {saldo:.2f}", bold=True),
        ]
        if not modo_cego:
            linhas_caixa.append(
                _linha("Diferença apurada:", f"R$ {dif:.2f}", bold=True, color=_cor_dif(dif))
            )

        card2_col.controls.clear()
        card2_col.controls.extend(linhas_caixa)

    # ── Card 3: Contas a Pagar & Boletos ──────────────────────────────────────

    def _atualizar_card_boletos():
        database.boleto_atualizar_status_vencidos()
        abertos_7d = database.boletos_parcelas_em_aberto(dias_frente=7)

        _hoje_iso = _data_atual["iso"]
        hoje_itens = [b for b in abertos_7d if b.get("vencimento") == _hoje_iso]
        valor_hoje = sum(b.get("valor", 0.0) for b in hoje_itens)

        vencidos_itens = [b for b in abertos_7d if b.get("dias_para_vencer", 0) < 0]
        valor_vencidos = sum(b.get("valor", 0.0) for b in vencidos_itens)

        prox_itens = [b for b in abertos_7d if 0 < b.get("dias_para_vencer", 0) <= 7]
        valor_prox = sum(b.get("valor", 0.0) for b in prox_itens)

        card_boletos_col.controls.clear()

        card_boletos_col.controls.append(
            _linha(
                "Vencendo hoje:",
                f"{len(hoje_itens)} (R$ {valor_hoje:.2f})",
                bold=bool(hoje_itens),
                color=ft.Colors.YELLOW_300 if hoje_itens else None,
            )
        )

        if vencidos_itens:
            card_boletos_col.controls.append(
                _linha(
                    "Vencidos (pendentes):",
                    f"{len(vencidos_itens)} (R$ {valor_vencidos:.2f})",
                    bold=True,
                    color=ft.Colors.RED_400,
                )
            )

        card_boletos_col.controls.append(
            _linha(
                "Próximos 7 dias:",
                f"{len(prox_itens)} (R$ {valor_prox:.2f})",
                color=ft.Colors.GREY_400,
            )
        )

        card_boletos_col.controls.append(ft.Divider(height=1))

        def _ir_fornecedores(e):
            if hasattr(page, "navegar"):
                page.navegar("Fornecedores")

        total_semana = valor_hoje + valor_vencidos + valor_prox
        card_boletos_col.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        f"Compromissos: R$ {total_semana:.2f}",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREY_300,
                    ),
                    ft.ElevatedButton(
                        "Gerenciar Boletos",
                        icon=ft.Icons.PAYMENTS_OUTLINED,
                        on_click=_ir_fornecedores,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.BLUE_GREY_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
            )
        )

    # ── Card 4: Equipe & Presença Compacta + Modal ─────────────────────────────

    def _obter_equipe_interna():
        """Retorna apenas colaboradores internos ativos que batem ponto (exclui entregadores)."""
        todas = database.pessoa_listar(apenas_ativos=True)
        resultado = []
        for p in todas:
            tipo = p["tipo"] if "tipo" in p.keys() else ""
            aparece = bool(p["aparece_no_ponto"]) if "aparece_no_ponto" in p.keys() else True
            if tipo != "ENTREGADOR" and aparece:
                resultado.append(p)
        return sorted(resultado, key=lambda x: (0 if x["tipo"] == "INTERNO" else 1, x["nome"]))

    modal_presenca_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    dlg_presenca = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.BADGE_OUTLINED, color=ft.Colors.TEAL_400, size=22),
            ft.Text("Presença e Ponto da Equipe (Hoje)", size=16, weight=ft.FontWeight.BOLD),
        ], spacing=8),
        content=ft.Container(
            width=680,
            height=460,
            content=modal_presenca_col,
        ),
        actions=[
            ft.TextButton("Concluir e Fechar", on_click=lambda e: _fechar_modal_presenca()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg_presenca)

    def _fechar_modal_presenca(e=None):
        dlg_presenca.open = False
        _atualizar_resumo_presenca()
        page.update()

    def _abrir_modal_presenca(e=None):
        _carregar_linhas_modal_presenca()
        dlg_presenca.open = True
        page.update()

    def _atualizar_resumo_presenca():
        _hoje = _data_atual["iso"]
        equipe = _obter_equipe_interna()
        escalas = {
            e["id_pessoa"]: e["tipo"]
            for e in database.escala_listar_por_data(_hoje)
        }

        presentes = sum(1 for p in equipe if escalas.get(p["id"]) in ("TRABALHOU", "EXTRA"))
        folgas    = sum(1 for p in equipe if escalas.get(p["id"]) == "FOLGA")
        faltas    = sum(1 for p in equipe if escalas.get(p["id"]) == "FALTA")
        feriados  = sum(1 for p in equipe if escalas.get(p["id"]) == "FERIADO")
        pendentes = len(equipe) - (presentes + folgas + faltas + feriados)

        card_presenca_col.controls.clear()

        def _badge(label: str, count: int, cor_bg: str, cor_txt: str = ft.Colors.WHITE):
            return ft.Container(
                bgcolor=cor_bg,
                border_radius=6,
                padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                content=ft.Text(f"{label}: {count}", size=12, weight=ft.FontWeight.BOLD, color=cor_txt),
            )

        badges = [
            _badge("Trabalhando", presentes, ft.Colors.TEAL_800),
            _badge("Folga", folgas, ft.Colors.BLUE_GREY_800),
        ]
        if faltas > 0:
            badges.append(_badge("Falta", faltas, ft.Colors.RED_900))
        if pendentes > 0:
            badges.append(_badge("Pendente", pendentes, ft.Colors.ORANGE_900, ft.Colors.YELLOW_200))

        card_presenca_col.controls.append(
            ft.Row(spacing=8, wrap=True, controls=badges)
        )

        card_presenca_col.controls.append(ft.Divider(height=1))

        card_presenca_col.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        f"Equipe interna: {len(equipe)} colaboradores",
                        size=12, color=ft.Colors.GREY_400,
                    ),
                    ft.ElevatedButton(
                        "Lançar Presença",
                        icon=ft.Icons.BADGE_OUTLINED,
                        on_click=_abrir_modal_presenca,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.TEAL_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
            )
        )

    def _carregar_linhas_modal_presenca():
        """Preenche o conteúdo do modal de presença para lançamento rápido."""
        _hoje = _data_atual["iso"]
        _hoje_wd = date.fromisoformat(_hoje).weekday()

        database.escala_pre_popular_do_dia(_hoje)

        horario_fixo: dict = {}
        for row in database.dias_fixos_listar_todos():
            if row["dia_semana"] == _hoje_wd:
                horario_fixo[row["id_pessoa"]] = row["horario_entrada"] or ""

        escalas_hoje: dict = {
            e["id_pessoa"]: e["tipo"]
            for e in database.escala_listar_por_data(_hoje)
        }

        equipe = _obter_equipe_interna()
        pontos_hoje: dict = {}
        for pessoa in equipe:
            pt = database.ponto_buscar(_hoje, pessoa["id"])
            pontos_hoje[pessoa["id"]] = (
                (pt["hora_entrada"] or "") if pt else "",
                (pt["hora_saida"]   or "") if pt else "",
            )

        modal_presenca_col.controls.clear()

        if not equipe:
            modal_presenca_col.controls.append(
                ft.Text(
                    "Nenhum colaborador interno ativo cadastrado com ponto habilitado.",
                    italic=True, color=ft.Colors.GREY_400,
                )
            )
            return

        # Cabeçalho da tabela do modal
        modal_presenca_col.controls.append(ft.Row(controls=[
            ft.Container(expand=4, content=ft.Text("Colaborador", size=12, weight=ft.FontWeight.BOLD)),
            ft.Container(expand=3, content=ft.Text("Status", size=12, weight=ft.FontWeight.BOLD)),
            ft.Container(expand=3, content=ft.Text("Entrada / Saída", size=12, weight=ft.FontWeight.BOLD)),
            ft.Container(expand=1),
        ]))
        modal_presenca_col.controls.append(ft.Divider(height=1))

        for pessoa in equipe:
            pid      = pessoa["id"]
            nome     = pessoa["nome"]
            desc     = pessoa["cargo"] or pessoa["tipo"]
            ja_salvo = pid in escalas_hoje

            dd = ft.Dropdown(
                value=escalas_hoje.get(pid),
                width=140,
                options=[ft.dropdown.Option(t) for t in _TIPOS_ESCALA],
            )

            ent_ini, ent_sai = pontos_hoje.get(pid, ("", ""))
            tf_ent = ft.TextField(
                value=ent_ini or horario_fixo.get(pid, ""),
                width=72,
                hint_text="Entr.",
                text_align=ft.TextAlign.CENTER,
            )
            tf_sai = ft.TextField(
                value=ent_sai,
                width=72,
                hint_text="Saída",
                text_align=ft.TextAlign.CENTER,
            )

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

            def _salvar_linha(e, _pid=pid, _nome=nome, _dd=dd, _tf_e=tf_ent,
                              _tf_s=tf_sai, _btn=btn_container):
                tipo = _dd.value
                if not tipo:
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text(f"Selecione o status de {_nome}."),
                        bgcolor=ft.Colors.ORANGE_700, open=True,
                    ))
                    page.update()
                    return

                h_ent = _tf_e.value.strip()
                h_sai = _tf_s.value.strip()

                for h, rotulo in ((h_ent, "entrada"), (h_sai, "saída")):
                    if h and not _validar_hora(h):
                        page.overlay.append(ft.SnackBar(
                            content=ft.Text(f"Horário de {rotulo} inválido para {_nome} (use HH:MM)."),
                            bgcolor=ft.Colors.ORANGE_700, open=True,
                        ))
                        page.update()
                        return

                database.escala_registrar(_data_atual["iso"], _pid, tipo)
                if tipo == "TRABALHOU":
                    if h_ent:
                        database.ponto_registrar_entrada(_data_atual["iso"], _pid, h_ent)
                    if h_sai:
                        database.ponto_registrar_saida(_data_atual["iso"], _pid, h_sai)

                _btn.content = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=22)
                _atualizar_resumo_presenca()
                page.update()

            if ja_salvo:
                btn_container.content = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=22)
            else:
                btn_container.content = ft.ElevatedButton(
                    "OK",
                    on_click=_salvar_linha,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.TEAL_700,
                        color=ft.Colors.WHITE,
                        padding=ft.Padding(8, 4, 8, 4),
                    ),
                )

            modal_presenca_col.controls.append(ft.Row(
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
                    ft.Container(expand=3, content=ft.Row(spacing=4, controls=[tf_ent, tf_sai])),
                    btn_container,
                ],
            ))

    # ── Alertas Proativos (Estoque e Boletos) ──────────────────────────────────

    def _atualizar_alertas_est():
        produtos = database.estoque_produtos_abaixo_minimo()
        alertas_col.controls.clear()

        if not produtos:
            card_alertas_est.visible = False
            return

        card_alertas_est.visible = True
        total = len(produtos)
        exibir = produtos[:4]

        def _ir_estoque(e):
            if hasattr(page, "navegar"):
                page.navegar("Estoque")

        alertas_col.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=ft.Colors.YELLOW_300, size=20),
                        ft.Text(
                            f"Estoque Crítico — {total} produto(s) abaixo do nível mínimo",
                            color=ft.Colors.YELLOW_300, weight=ft.FontWeight.BOLD, size=13,
                        ),
                    ]),
                    ft.TextButton("Ver Estoque →", on_click=_ir_estoque),
                ],
            )
        )

        for p in exibir:
            alertas_col.controls.append(ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.ORANGE_400, size=8),
                ft.Text(p["nome"], expand=True, size=12),
                ft.Text(f"Atual: {p['quantidade_atual']:.1f} {p['unidade']}", color=ft.Colors.RED_300, size=12),
                ft.Text(f"Mín: {p['quantidade_minima']:.1f}", color=ft.Colors.GREY_500, size=12),
            ]))

    def _atualizar_alertas_boletos():
        vencidos = database.boletos_vencidos_hoje()
        alertas_boletos_col.controls.clear()

        if not vencidos:
            card_alertas_boletos.visible = False
            return

        card_alertas_boletos.visible = True

        def _ir_fornecedores(e):
            if hasattr(page, "navegar"):
                page.navegar("Fornecedores")

        alertas_boletos_col.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_300, size=20),
                        ft.Text(
                            f"Atenção: {len(vencidos)} boleto(s) vencido(s) aguardando quitação",
                            color=ft.Colors.RED_300, weight=ft.FontWeight.BOLD, size=13,
                        ),
                    ]),
                    ft.TextButton("Quitar no Fornecedores →", on_click=_ir_fornecedores),
                ],
            )
        )

        for v in vencidos[:3]:
            alertas_boletos_col.controls.append(ft.Row(spacing=8, controls=[
                ft.Icon(ft.Icons.CIRCLE, color=ft.Colors.RED_400, size=8),
                ft.Text(f"{v['nome_fornecedor']} — {v['descricao']}", expand=True, size=12),
                ft.Text(f"R$ {v['valor']:.2f}", color=ft.Colors.RED_300, size=12, weight=ft.FontWeight.BOLD),
            ]))

    # ── Atualização Geral da Tela ───────────────────────────────────────────────

    def _atualizar(e=None):
        d = date.fromisoformat(_data_atual["iso"])
        txt_data_topo.value = f"Dashboard  —  {d.strftime('%d/%m/%Y')}"
        conn = database.conectar()
        try:
            _atualizar_cards_1_2(conn)
        finally:
            conn.close()
        _atualizar_card_boletos()
        _atualizar_resumo_presenca()
        _atualizar_alertas_est()
        _atualizar_alertas_boletos()
        page.update()

    # ── Barra Superior (Data + Atualizar) ──────────────────────────────────────

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
        width=130,
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
        padding=ft.Padding(left=16, right=16, top=10, bottom=10),
        content=ft.Row(
            controls=[
                txt_data_topo,
                tf_data_dash,
                btn_calendario_dash,
                btn_atualizar,
            ],
            spacing=12,
        ),
    ))

    # ── Barra de Ações Rápidas (Atalhos) ───────────────────────────────────────

    def _criar_btn_atalho(label: str, icone: str, destino: str, cor_bg: str = None):
        def _ao_clicar(e):
            if hasattr(page, "navegar"):
                page.navegar(destino)

        return ft.ElevatedButton(
            label,
            icon=icone,
            on_click=_ao_clicar,
            style=ft.ButtonStyle(
                bgcolor=cor_bg or ft.Colors.with_opacity(0.10, ft.Colors.WHITE),
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(left=14, right=14, top=10, bottom=10),
            ),
        )

    barra_atalhos = ft.Container(
        padding=ft.Padding(left=12, right=12, top=8, bottom=8),
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
        border_radius=8,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
        content=ft.Row(
            spacing=8,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Ações Rápidas:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_300),
                _criar_btn_atalho("Novo Pedido", ft.Icons.POINT_OF_SALE, "PDV", ft.Colors.TEAL_800),
                _criar_btn_atalho("Agenda", ft.Icons.EVENT_NOTE, "Agenda", ft.Colors.INDIGO_800),
                _criar_btn_atalho("Fluxo de Caixa", ft.Icons.ACCOUNT_BALANCE_WALLET, "Fluxo Caixa"),
                _criar_btn_atalho("Relatório Diário", ft.Icons.PIE_CHART_OUTLINE, "Rel. Diário"),
                _criar_btn_atalho("Fornecedores", ft.Icons.LOCAL_SHIPPING_OUTLINED, "Fornecedores"),
                _criar_btn_atalho("Estoque", ft.Icons.INVENTORY_2_OUTLINED, "Estoque"),
                _criar_btn_atalho("Entregadores", ft.Icons.TWO_WHEELER, "Entregadores"),
            ],
        ),
    )

    # ── Grade Executiva 2×2 ────────────────────────────────────────────────────

    linha_kpis_1 = ft.Row(
        expand=True,
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Column(expand=1, controls=[_card("Resumo de Vendas do Dia", card1_col)]),
            ft.Column(expand=1, controls=[_card("Status do Caixa & Gaveta", card2_col)]),
        ],
    )

    linha_kpis_2 = ft.Row(
        expand=True,
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Column(expand=1, controls=[_card("Contas a Pagar / Boletos", card_boletos_col)]),
            ft.Column(expand=1, controls=[_card("Equipe & Presença de Hoje", card_presenca_col)]),
        ],
    )

    # ── Cards de Alertas ───────────────────────────────────────────────────────

    card_alertas_est = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(12),
            content=alertas_col,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.ORANGE_900),
            border_radius=8,
        ),
    )

    card_alertas_boletos = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(12),
            content=alertas_boletos_col,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.RED_900),
            border_radius=8,
        ),
    )

    # Carrega dados iniciais
    _atualizar()

    return ft.Column(
        controls=[
            topo,
            barra_atalhos,
            linha_kpis_1,
            linha_kpis_2,
            card_alertas_boletos,
            card_alertas_est,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=14,
    )
