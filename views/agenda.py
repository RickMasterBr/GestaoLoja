"""
views/agenda.py — Calendário & Agenda Operacional da Loja.
Exibe visão mensal com grid de dias, integração automática com boletos a pagar,
marcação de datas de pessoal e mural de lembretes, entregas e manutenções.
"""

import calendar
from datetime import date, datetime
import flet as ft

import database

# Nomes dos meses em português
MESES_PT = [
    "", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

DIAS_SEMANA_PT = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"]

# Tipos de lembretes com cores e ícones
TIPOS_EVENTO = {
    "LEMBRETE":    {"label": "Lembrete Geral",       "cor": ft.Colors.BLUE_400,   "icon": ft.Icons.PUSH_PIN_OUTLINED},
    "ENTREGA":     {"label": "Chegada Fornecedor",   "cor": ft.Colors.AMBER_400,  "icon": ft.Icons.LOCAL_SHIPPING_OUTLINED},
    "MANUTENCAO":  {"label": "Manutenção / Limpeza", "cor": ft.Colors.PURPLE_400, "icon": ft.Icons.BUILD_OUTLINED},
    "FINANCEIRO":  {"label": "Financeiro / Contas",  "cor": ft.Colors.GREEN_400,  "icon": ft.Icons.ATTACH_MONEY},
}


def _iso_para_br(iso: str) -> str:
    try:
        a, m, d = iso.strip().split("-")
        return f"{d}/{m}/{a}"
    except Exception:
        return iso or ""


def _br_para_iso(br: str) -> str:
    try:
        d, m, a = br.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return ""


def view(page: ft.Page) -> ft.Control:
    hoje = date.today()
    hoje_iso = hoje.isoformat()

    # Estado de navegação
    estado = {
        "ano": hoje.year,
        "mes": hoje.month,
        "dia_selecionado": hoje_iso,
        "id_edicao": None,
    }

    # ── Controles do Modal de Lembrete ───────────────────────────────────────
    lbl_modal_tit = ft.Text("Novo Lembrete", size=15, weight=ft.FontWeight.BOLD)
    tf_tit = ft.TextField(label="Título do lembrete *", expand=True)
    tf_data_lembrete = ft.TextField(
        label="Data *",
        value=_iso_para_br(hoje_iso),
        width=140,
        hint_text="DD/MM/AAAA",
        text_align=ft.TextAlign.CENTER,
    )
    tf_hora_lembrete = ft.TextField(
        label="Horário",
        hint_text="HH:MM",
        width=110,
        text_align=ft.TextAlign.CENTER,
    )
    dd_tipo_lembrete = ft.Dropdown(
        label="Tipo / Categoria",
        width=220,
        value="LEMBRETE",
        options=[
            ft.dropdown.Option(k, v["label"])
            for k, v in TIPOS_EVENTO.items()
        ],
    )
    tf_desc_lembrete = ft.TextField(
        label="Observações / Detalhes",
        multiline=True,
        min_lines=2,
        max_lines=3,
        expand=True,
    )
    txt_modal_err = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _fechar_modal(e=None):
        dlg_lembrete.open = False
        txt_modal_err.value = ""
        page.update()

    def _salvar_lembrete(e=None):
        txt_modal_err.value = ""
        titulo = tf_tit.value.strip()
        if not titulo:
            txt_modal_err.value = "O título é obrigatório."
            page.update()
            return

        data_iso = _br_para_iso(tf_data_lembrete.value)
        if not data_iso:
            txt_modal_err.value = "Informe uma data válida (DD/MM/AAAA)."
            page.update()
            return

        hora = tf_hora_lembrete.value.strip() or None
        desc = tf_desc_lembrete.value.strip() or None
        tipo = dd_tipo_lembrete.value or "LEMBRETE"

        sessao = database.sessao_obter()
        usuario_nome = sessao.get("nome", "Admin") if sessao else "Admin"

        if estado["id_edicao"] is None:
            database.agenda_inserir(
                data=data_iso,
                titulo=titulo,
                horario=hora,
                descricao=desc,
                tipo=tipo,
                criado_por=usuario_nome,
            )
            msg = "Lembrete adicionado com sucesso."
        else:
            database.agenda_atualizar(
                estado["id_edicao"],
                data=data_iso,
                titulo=titulo,
                horario=hora,
                descricao=desc,
                tipo=tipo,
            )
            msg = "Lembrete atualizado com sucesso."

        dlg_lembrete.open = False
        page.overlay.append(ft.SnackBar(
            content=ft.Text(msg), bgcolor=ft.Colors.GREEN_700, open=True,
        ))
        _recarregar_tudo()

    dlg_lembrete = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                lbl_modal_tit,
                ft.IconButton(ft.Icons.CLOSE, on_click=_fechar_modal),
            ],
        ),
        content=ft.Container(
            width=540,
            content=ft.Column(
                tight=True,
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    tf_tit,
                    ft.Row([tf_data_lembrete, tf_hora_lembrete, dd_tipo_lembrete], spacing=10),
                    tf_desc_lembrete,
                    txt_modal_err,
                ],
            ),
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_fechar_modal),
            ft.ElevatedButton(
                "Salvar",
                icon=ft.Icons.SAVE,
                on_click=_salvar_lembrete,
                style=ft.ButtonStyle(bgcolor=ft.Colors.TEAL_700, color=ft.Colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg_lembrete)

    def _abrir_modal_novo(dia_iso: str = None):
        estado["id_edicao"] = None
        lbl_modal_tit.value = "Novo Lembrete / Tarefa"
        tf_tit.value = ""
        tf_data_lembrete.value = _iso_para_br(dia_iso or estado["dia_selecionado"])
        tf_hora_lembrete.value = ""
        dd_tipo_lembrete.value = "LEMBRETE"
        tf_desc_lembrete.value = ""
        txt_modal_err.value = ""
        dlg_lembrete.open = True
        page.update()

    def _abrir_modal_editar(item):
        estado["id_edicao"] = item["id"]
        lbl_modal_tit.value = f"Editando: {item['titulo']}"
        tf_tit.value = item["titulo"]
        tf_data_lembrete.value = _iso_para_br(item["data"])
        tf_hora_lembrete.value = item["horario"] or ""
        dd_tipo_lembrete.value = item["tipo"] or "LEMBRETE"
        tf_desc_lembrete.value = item["descricao"] or ""
        txt_modal_err.value = ""
        dlg_lembrete.open = True
        page.update()

    # ── Componentes Visuais Principais ───────────────────────────────────────
    txt_mes_ano = ft.Text(
        f"{MESES_PT[hoje.month]} / {hoje.year}",
        size=17,
        weight=ft.FontWeight.BOLD,
    )

    grid_dias_col = ft.Column(spacing=6)
    painel_dia_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def _mes_anterior(e):
        if estado["mes"] == 1:
            estado["mes"] = 12
            estado["ano"] -= 1
        else:
            estado["mes"] -= 1
        _recarregar_tudo()

    def _mes_proximo(e):
        if estado["mes"] == 12:
            estado["mes"] = 1
            estado["ano"] += 1
        else:
            estado["mes"] += 1
        _recarregar_tudo()

    def _ir_para_hoje(e):
        estado["ano"] = hoje.year
        estado["mes"] = hoje.month
        estado["dia_selecionado"] = hoje_iso
        _recarregar_tudo()

    # ── Construção do Grid Mensal ────────────────────────────────────────────
    def _montar_grid():
        ano = estado["ano"]
        mes = estado["mes"]
        mes_ano_iso = f"{ano:04d}-{mes:02d}"

        txt_mes_ano.value = f"{MESES_PT[mes]} / {ano}"

        # Busca dados do mês
        lembretes_mes = database.agenda_listar_mes(mes_ano_iso)
        boletos_mes = database.agenda_boletos_mes(mes_ano_iso)

        # Agrupa por data
        lembretes_por_dia = {}
        for lem in lembretes_mes:
            d = lem["data"]
            lembretes_por_dia.setdefault(d, []).append(lem)

        boletos_por_dia = {}
        for bol in boletos_mes:
            d = bol["vencimento"]
            boletos_por_dia.setdefault(d, []).append(bol)

        cab_dias = ft.Row(
            spacing=4,
            controls=[
                ft.Container(
                    expand=1,
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding(top=4, bottom=4, left=0, right=0),
                    content=ft.Text(ds, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400),
                )
                for ds in DIAS_SEMANA_PT
            ],
        )

        cal = calendar.Calendar(firstweekday=6)
        semanas = cal.monthdatescalendar(ano, mes)

        linhas_grid = [cab_dias]

        for sem in semanas:
            dias_row = []
            for dt in sem:
                dt_iso = dt.isoformat()
                eh_do_mes = (dt.month == mes)
                eh_hoje = (dt_iso == hoje_iso)
                eh_selecionado = (dt_iso == estado["dia_selecionado"])

                l_list = lembretes_por_dia.get(dt_iso, [])
                b_list = boletos_por_dia.get(dt_iso, [])

                badges = []

                if b_list:
                    abertos = [b for b in b_list if not b["pago"]]
                    total_aberto = sum(b["valor"] for b in abertos)
                    if abertos:
                        badges.append(ft.Container(
                            padding=ft.Padding(left=4, right=4, top=1, bottom=1),
                            border_radius=4,
                            bgcolor=ft.Colors.with_opacity(0.20, ft.Colors.ORANGE_700),
                            content=ft.Row(
                                spacing=2,
                                tight=True,
                                controls=[
                                    ft.Icon(ft.Icons.RECEIPT_LONG, size=10, color=ft.Colors.ORANGE_400),
                                    ft.Text(f"R$ {total_aberto:,.0f}".replace(",", "."), size=9, color=ft.Colors.ORANGE_300, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                        ))
                    else:
                        badges.append(ft.Container(
                            padding=ft.Padding(left=4, right=4, top=1, bottom=1),
                            border_radius=4,
                            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.GREEN_700),
                            content=ft.Text(f"OK {len(b_list)} pago(s)", size=9, color=ft.Colors.GREEN_400),
                        ))

                if l_list:
                    badges.append(ft.Container(
                        padding=ft.Padding(left=4, right=4, top=1, bottom=1),
                        border_radius=4,
                        bgcolor=ft.Colors.with_opacity(0.20, ft.Colors.BLUE_700),
                        content=ft.Row(
                            spacing=2,
                            tight=True,
                            controls=[
                                ft.Icon(ft.Icons.PUSH_PIN, size=10, color=ft.Colors.BLUE_400),
                                ft.Text(f"{len(l_list)} item(ns)", size=9, color=ft.Colors.BLUE_300),
                            ],
                        ),
                    ))

                def _selecionar_dia(e, d=dt_iso):
                    estado["dia_selecionado"] = d
                    _recarregar_tudo()

                if eh_selecionado:
                    borda_cor = ft.Colors.TEAL_400
                    bg_card = ft.Colors.with_opacity(0.18, ft.Colors.TEAL)
                elif eh_hoje:
                    borda_cor = ft.Colors.INDIGO_400
                    bg_card = ft.Colors.with_opacity(0.10, ft.Colors.INDIGO)
                else:
                    borda_cor = ft.Colors.with_opacity(0.08, ft.Colors.WHITE)
                    bg_card = ft.Colors.with_opacity(0.03, ft.Colors.WHITE) if eh_do_mes else ft.Colors.with_opacity(0.01, ft.Colors.WHITE)

                opacidade = 1.0 if eh_do_mes else 0.35

                card_dia = ft.Container(
                    expand=1,
                    height=72,
                    border_radius=6,
                    padding=ft.Padding.all(4),
                    bgcolor=bg_card,
                    opacity=opacidade,
                    border=ft.Border.all(1.5 if (eh_selecionado or eh_hoje) else 1, borda_cor),
                    on_click=_selecionar_dia,
                    content=ft.Column(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        str(dt.day),
                                        size=11,
                                        weight=ft.FontWeight.BOLD if (eh_hoje or eh_selecionado) else ft.FontWeight.NORMAL,
                                        color=ft.Colors.TEAL_200 if eh_selecionado else ft.Colors.INDIGO_200 if eh_hoje else ft.Colors.WHITE,
                                    ),
                                    ft.Container(
                                        width=5, height=5,
                                        border_radius=3,
                                        bgcolor=ft.Colors.INDIGO_400 if eh_hoje else None,
                                    ),
                                ],
                            ),
                            *badges,
                        ],
                    ),
                )
                dias_row.append(card_dia)

            linhas_grid.append(ft.Row(spacing=4, controls=dias_row))

        grid_dias_col.controls = linhas_grid

    # ── Construção do Painel de Detalhes do Dia ──────────────────────────────
    def _montar_painel_dia():
        dia_iso = estado["dia_selecionado"]
        dia_br = _iso_para_br(dia_iso)

        try:
            dt_obj = datetime.strptime(dia_iso, "%Y-%m-%d")
            dia_sem_str = DIAS_SEMANA_PT[dt_obj.weekday() == 6 and 0 or dt_obj.weekday() + 1]
            titulo_dia = f"{dia_sem_str}, {dia_br}"
        except Exception:
            titulo_dia = dia_br

        lembretes_dia = database.agenda_listar_dia(dia_iso)

        mes_ano_iso = dia_iso[:7]
        boletos_mes = database.agenda_boletos_mes(mes_ano_iso)
        boletos_dia = [b for b in boletos_mes if b["vencimento"] == dia_iso]

        painel_dia_col.controls.clear()

        # Topo do Painel
        painel_dia_col.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(titulo_dia, size=15, weight=ft.FontWeight.BOLD),
                            ft.Text("Compromissos e Contas", size=11, color=ft.Colors.GREY_400),
                        ],
                    ),
                    ft.ElevatedButton(
                        "+ Lembrete",
                        icon=ft.Icons.ADD,
                        on_click=lambda e: _abrir_modal_novo(dia_iso),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.TEAL_700,
                            color=ft.Colors.WHITE,
                            padding=ft.Padding(10, 6, 10, 6),
                        ),
                    ),
                ],
            )
        )
        painel_dia_col.controls.append(ft.Divider(height=1))

        # ── Seção: Boletos a Vencer ──
        painel_dia_col.controls.append(
            ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.RECEIPT_LONG, size=16, color=ft.Colors.ORANGE_400),
                    ft.Text("Contas & Boletos a Vencer", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_300),
                ],
            )
        )

        if not boletos_dia:
            painel_dia_col.controls.append(
                ft.Container(
                    padding=ft.Padding.all(8),
                    content=ft.Text("Nenhum boleto de fornecedor para esta data.", size=11, italic=True, color=ft.Colors.GREY_500),
                )
            )
        else:
            for b in boletos_dia:
                pago = bool(b["pago"])
                cor_status = ft.Colors.GREEN_400 if pago else ft.Colors.ORANGE_400
                txt_status = "PAGO" if pago else "EM ABERTO"

                painel_dia_col.controls.append(
                    ft.Container(
                        padding=ft.Padding.all(10),
                        border_radius=8,
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
                        border=ft.Border.all(1, ft.Colors.with_opacity(0.10, ft.Colors.WHITE)),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(b["nome_fornecedor"], size=13, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{b['descricao']} (Parc. {b['num_parcela']}/{b['num_parcelas']})", size=11, color=ft.Colors.GREY_400),
                                    ],
                                ),
                                ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                    spacing=2,
                                    controls=[
                                        ft.Text(f"R$ {b['valor']:.2f}", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_300),
                                        ft.Container(
                                            padding=ft.Padding(left=6, right=6, top=1, bottom=1),
                                            border_radius=4,
                                            bgcolor=ft.Colors.with_opacity(0.20, cor_status),
                                            content=ft.Text(txt_status, size=9, color=cor_status, weight=ft.FontWeight.BOLD),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    )
                )

        painel_dia_col.controls.append(ft.Divider(height=1))

        # ── Seção: Lembretes & Tarefas da Loja ──
        painel_dia_col.controls.append(
            ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.CHECKLIST, size=16, color=ft.Colors.BLUE_400),
                    ft.Text("Lembretes & Tarefas da Loja", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300),
                ],
            )
        )

        if not lembretes_dia:
            painel_dia_col.controls.append(
                ft.Container(
                    padding=ft.Padding.all(8),
                    content=ft.Text("Nenhuma tarefa anotada para este dia.", size=11, italic=True, color=ft.Colors.GREY_500),
                )
            )
        else:
            for item in lembretes_dia:
                concluido = bool(item["concluido"])
                info_tipo = TIPOS_EVENTO.get(item["tipo"] or "LEMBRETE", TIPOS_EVENTO["LEMBRETE"])

                def _toggle_concluido(e, _id=item["id"], _c=concluido):
                    database.agenda_concluir(_id, not _c)
                    _recarregar_tudo()

                def _excluir_lem(e, _id=item["id"]):
                    database.agenda_excluir(_id)
                    _recarregar_tudo()

                cb_item = ft.Checkbox(
                    value=concluido,
                    on_change=_toggle_concluido,
                )

                txt_tit_ctrl = ft.Text(
                    item["titulo"],
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH if concluido else None),
                    color=ft.Colors.GREY_500 if concluido else ft.Colors.WHITE,
                )

                sub_ctrls = []
                if item["horario"]:
                    sub_ctrls.append(ft.Text(f"Horário: {item['horario']}", size=10, color=ft.Colors.AMBER_300))
                if item["descricao"]:
                    sub_ctrls.append(ft.Text(item["descricao"], size=10, color=ft.Colors.GREY_400))

                card_lem = ft.Container(
                    padding=ft.Padding.all(8),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.WHITE),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.WHITE)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=4,
                                expand=True,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    cb_item,
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Row(
                                                spacing=6,
                                                controls=[
                                                    ft.Icon(info_tipo["icon"], size=13, color=info_tipo["cor"]),
                                                    txt_tit_ctrl,
                                                ],
                                            ),
                                            *sub_ctrls,
                                        ],
                                    ),
                                ],
                            ),
                            ft.Row(
                                spacing=0,
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_size=16,
                                        tooltip="Editar",
                                        on_click=lambda e, _it=item: _abrir_modal_editar(_it),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_size=16,
                                        icon_color=ft.Colors.RED_400,
                                        tooltip="Excluir",
                                        on_click=_excluir_lem,
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
                painel_dia_col.controls.append(card_lem)

    def _recarregar_tudo():
        _montar_grid()
        _montar_painel_dia()
        page.update()

    # ── Barra Superior (Navegação de Mês) ────────────────────────────────────
    topo_barra = ft.Card(
        content=ft.Container(
            padding=ft.Padding.all(12),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
                controls=[
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=_mes_anterior, tooltip="Mês anterior"),
                            txt_mes_ano,
                            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=_mes_proximo, tooltip="Próximo mês"),
                            ft.ElevatedButton(
                                "Hoje",
                                icon=ft.Icons.TODAY,
                                on_click=_ir_para_hoje,
                                style=ft.ButtonStyle(
                                    bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
                                    color=ft.Colors.WHITE,
                                ),
                            ),
                        ],
                    ),
                    ft.ElevatedButton(
                        "Novo Lembrete",
                        icon=ft.Icons.ADD,
                        on_click=lambda e: _abrir_modal_novo(),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.TEAL_700,
                            color=ft.Colors.WHITE,
                            padding=ft.Padding(14, 10, 14, 10),
                        ),
                    ),
                ],
            ),
        )
    )

    card_grid = ft.Card(
        expand=6,
        content=ft.Container(
            padding=ft.Padding.all(14),
            content=grid_dias_col,
        ),
    )

    card_painel = ft.Card(
        expand=4,
        content=ft.Container(
            padding=ft.Padding.all(14),
            content=painel_dia_col,
        ),
    )

    corpo = ft.Row(
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[card_grid, card_painel],
        expand=True,
    )

    _recarregar_tudo()

    return ft.Column(
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[topo_barra, corpo],
    )
