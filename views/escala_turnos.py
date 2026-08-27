"""
views/escala_turnos.py — Escala Mensal de Turnos e Planejamento Visual de Equipe.

Permite planejar visualmente quem trabalha em quais dias e turnos (DIA / NOITE),
gerenciar extras avulsos, suportar dobras (mesma pessoa em DIA e NOITE),
e gerar impressão em folha A4 Paisagem formatada para mural.
"""

import calendar
from datetime import date, datetime
import flet as ft

import database
from relatorios import pdf_gerador

MESES_PT = [
    "", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

DIAS_SEMANA_PT = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"]


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

    # Controle de Acesso
    pode_editar = database.sessao_tem_acesso("GERENTE")

    # Estado de Navegação e Seleção
    estado = {
        "ano": hoje.year,
        "mes": hoje.month,
        "dia_selecionado": hoje_iso,
        "turno_selecionado": "DIA",  # 'DIA' | 'NOITE'
    }

    # Pessoas Ativas Cadastradas
    pessoas_ativas = [dict(p) for p in database.pessoa_listar(tipo="INTERNO", apenas_ativos=True)]
    if not pessoas_ativas:
        pessoas_ativas = [dict(p) for p in database.pessoa_listar(apenas_ativos=True)]

    # ── Controles da Barra Superior ──────────────────────────────────────────
    txt_mes_ano = ft.Text(
        f"{MESES_PT[hoje.month]} / {hoje.year}",
        size=17,
        weight=ft.FontWeight.BOLD,
    )

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

    def _imprimir_escala(e):
        ano = estado["ano"]
        mes = estado["mes"]
        mes_ano_iso = f"{ano:04d}-{mes:02d}"

        # Carrega dados do mês agrupados por dia e turno
        escalas = [dict(r) for r in database.escala_turnos_listar_mes(mes_ano_iso)]
        escalas_por_dia = {}
        for r in escalas:
            d = r["data"]
            t = r["turno"]
            escalas_por_dia.setdefault(d, {}).setdefault(t, []).append(r)

        dados_pdf = {
            "nome_loja": database.config_obter("nome_loja", "Gestão Loja"),
            "escalas_por_dia": escalas_por_dia,
        }

        try:
            caminho = pdf_gerador.gerar_pdf_escala_turnos(ano, mes, dados_pdf, abrir_ao_concluir=True)
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Escala gerada para impressão: {caminho}"),
                bgcolor=ft.Colors.GREEN_700,
                open=True,
            ))
            page.update()
        except Exception as ex:
            page.overlay.append(ft.SnackBar(
                content=ft.Text(f"Erro ao gerar PDF da escala: {ex}"),
                bgcolor=ft.Colors.RED_700,
                open=True,
            ))
            page.update()

    btn_imprimir = ft.ElevatedButton(
        "Imprimir Escala (PDF)",
        icon=ft.Icons.PRINT,
        style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_700, color=ft.Colors.WHITE),
        on_click=_imprimir_escala,
    )

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
                    btn_imprimir,
                ],
            ),
        )
    )

    # ── Componentes das Colunas Principais ───────────────────────────────────
    grid_dias_col = ft.Column(spacing=6)
    painel_dia_col = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # ── Controles do Modal de Inclusão de Pessoa / Turno ─────────────────────
    opts_pessoas = [
        ft.dropdown.Option(key=str(p["id"]), text=f"{p['nome']} ({p['cargo'] or 'Funcionário'})")
        for p in pessoas_ativas
    ]
    opts_pessoas.append(ft.dropdown.Option(key="__OUTRO__", text="Outro / Extra Avulso"))

    dd_pessoa = ft.Dropdown(
        label="Pessoa / Funcionária *",
        options=opts_pessoas,
    )

    tf_nome_avulso = ft.TextField(
        label="Nome do Extra Avulso *",
        visible=False,
    )

    tf_funcao_avulso = ft.TextField(
        label="Função / Cargo do Extra",
        hint_text="ex: Cozinha, Atendimento, Caixa",
        visible=False,
    )

    btn_turno_dia = ft.ElevatedButton(
        "Turno DIA",
        icon=ft.Icons.WB_SUNNY_OUTLINED,
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_800, color=ft.Colors.WHITE),
    )
    btn_turno_noite = ft.ElevatedButton(
        "Turno NOITE",
        icon=ft.Icons.BEDTIME_OUTLINED,
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_800, color=ft.Colors.GREY_300),
    )

    def _selecionar_turno(turno: str):
        estado["turno_selecionado"] = turno
        btn_turno_dia.style.bgcolor = ft.Colors.BLUE_800 if turno == "DIA" else ft.Colors.GREY_800
        btn_turno_dia.style.color = ft.Colors.WHITE if turno == "DIA" else ft.Colors.GREY_300
        btn_turno_noite.style.bgcolor = ft.Colors.PURPLE_800 if turno == "NOITE" else ft.Colors.GREY_800
        btn_turno_noite.style.color = ft.Colors.WHITE if turno == "NOITE" else ft.Colors.GREY_300
        page.update()

    btn_turno_dia.on_click   = lambda e: _selecionar_turno("DIA")
    btn_turno_noite.on_click = lambda e: _selecionar_turno("NOITE")

    txt_erro_modal = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _on_pessoa_change(e):
        eh_avulso = (dd_pessoa.value == "__OUTRO__")
        tf_nome_avulso.visible = eh_avulso
        tf_funcao_avulso.visible = eh_avulso
        txt_erro_modal.value = ""
        page.update()

    dd_pessoa.on_select = _on_pessoa_change

    def _fechar_modal(e=None):
        dlg_adicionar_turno.open = False
        txt_erro_modal.value = ""
        page.update()

    def _salvar_pessoa_modal(e=None):
        txt_erro_modal.value = ""
        dia_iso = estado["dia_selecionado"]
        turno = estado["turno_selecionado"]

        if not dd_pessoa.value:
            txt_erro_modal.value = "Selecione a pessoa ou escolha 'Outro'."
            page.update()
            return

        id_p = None
        nome_av = None
        func_av = None

        if dd_pessoa.value == "__OUTRO__":
            nome_av = (tf_nome_avulso.value or "").strip()
            if not nome_av:
                txt_erro_modal.value = "Informe o nome do extra avulso."
                page.update()
                return
            func_av = (tf_funcao_avulso.value or "").strip() or None
        else:
            id_p = int(dd_pessoa.value)

        try:
            database.escala_turno_inserir(
                data=dia_iso,
                turno=turno,
                id_pessoa=id_p,
                nome_avulso=nome_av,
                funcao=func_av,
            )
            dlg_adicionar_turno.open = False
            dd_pessoa.value = None
            tf_nome_avulso.value = ""
            tf_nome_avulso.visible = False
            tf_funcao_avulso.value = ""
            tf_funcao_avulso.visible = False
            txt_erro_modal.value = ""

            page.overlay.append(ft.SnackBar(
                content=ft.Text("Pessoa adicionada à escala com sucesso!"),
                bgcolor=ft.Colors.GREEN_700,
                open=True,
            ))
            _recarregar_tudo()
        except Exception as ex:
            if "UNIQUE" in str(ex).upper():
                txt_erro_modal.value = f"Esta pessoa já está escalada no turno {turno} nesta data."
            else:
                txt_erro_modal.value = f"Erro ao salvar: {ex}"
            page.update()

    lbl_modal_tit = ft.Text("Adicionar Pessoa / Turno", size=15, weight=ft.FontWeight.BOLD)

    dlg_adicionar_turno = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                lbl_modal_tit,
                ft.IconButton(ft.Icons.CLOSE, on_click=_fechar_modal),
            ],
        ),
        content=ft.Column(
            tight=True,
            width=460,
            spacing=12,
            controls=[
                dd_pessoa,
                tf_nome_avulso,
                tf_funcao_avulso,
                ft.Row([btn_turno_dia, btn_turno_noite], spacing=8),
                txt_erro_modal,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_fechar_modal),
            ft.ElevatedButton(
                "Salvar",
                icon=ft.Icons.SAVE,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800, color=ft.Colors.WHITE),
                on_click=_salvar_pessoa_modal,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg_adicionar_turno)

    def _abrir_modal_adicionar():
        dd_pessoa.value = None
        tf_nome_avulso.value = ""
        tf_nome_avulso.visible = False
        tf_funcao_avulso.value = ""
        tf_funcao_avulso.visible = False
        txt_erro_modal.value = ""
        _selecionar_turno("DIA")
        dia_br = _iso_para_br(estado["dia_selecionado"])
        lbl_modal_tit.value = f"Adicionar Pessoa — {dia_br}"
        dlg_adicionar_turno.open = True
        page.update()

    # ── Construção do Grid Mensal ────────────────────────────────────────────
    def _montar_grid():
        ano = estado["ano"]
        mes = estado["mes"]
        mes_ano_iso = f"{ano:04d}-{mes:02d}"

        txt_mes_ano.value = f"{MESES_PT[mes]} / {ano}"

        # Busca turnos do mês
        escalas_mes = [dict(r) for r in database.escala_turnos_listar_mes(mes_ano_iso)]
        escalas_por_dia = {}
        for r in escalas_mes:
            d = r["data"]
            t = r["turno"]
            escalas_por_dia.setdefault(d, {}).setdefault(t, []).append(r)

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

                turnos_dia = escalas_por_dia.get(dt_iso, {})
                lista_dia = turnos_dia.get("DIA", [])
                lista_noite = turnos_dia.get("NOITE", [])

                resumos_turno = []

                if eh_do_mes:
                    if lista_dia:
                        nomes_d = ", ".join(p["nome_exibicao"] for p in lista_dia)
                        if len(nomes_d) > 22:
                            nomes_d = nomes_d[:20] + "…"
                        resumos_turno.append(
                            ft.Container(
                                padding=ft.Padding(left=4, right=4, top=1, bottom=1),
                                border_radius=3,
                                bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.BLUE_400),
                                content=ft.Text(f"DIA: {nomes_d}", size=9, color=ft.Colors.BLUE_200, weight=ft.FontWeight.W_500),
                            )
                        )

                    if lista_noite:
                        nomes_n = ", ".join(p["nome_exibicao"] for p in lista_noite)
                        if len(nomes_n) > 22:
                            nomes_n = nomes_n[:20] + "…"
                        resumos_turno.append(
                            ft.Container(
                                padding=ft.Padding(left=4, right=4, top=1, bottom=1),
                                border_radius=3,
                                bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.PURPLE_400),
                                content=ft.Text(f"NOITE: {nomes_n}", size=9, color=ft.Colors.PURPLE_200, weight=ft.FontWeight.W_500),
                            )
                        )

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
                    height=85,
                    border_radius=6,
                    padding=ft.Padding.all(4),
                    bgcolor=bg_card,
                    opacity=opacidade,
                    border=ft.Border.all(1.5 if (eh_selecionado or eh_hoje) else 1, borda_cor),
                    on_click=_selecionar_dia,
                    content=ft.Column(
                        spacing=3,
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
                            *resumos_turno,
                        ],
                    ),
                )
                dias_row.append(card_dia)

            linhas_grid.append(ft.Row(spacing=4, controls=dias_row))

        grid_dias_col.controls = linhas_grid

    # ── Construção do Painel de Detalhes do Dia (Direita) ────────────────────
    def _montar_painel_dia():
        dia_iso = estado["dia_selecionado"]
        dia_br = _iso_para_br(dia_iso)

        try:
            dt_obj = datetime.strptime(dia_iso, "%Y-%m-%d")
            dia_sem_str = DIAS_SEMANA_PT[dt_obj.weekday() == 6 and 0 or dt_obj.weekday() + 1]
            titulo_dia = f"{dia_sem_str}, {dia_br}"
        except Exception:
            titulo_dia = dia_br

        escalas_dia = [dict(r) for r in database.escala_turnos_listar_dia(dia_iso)]
        turnos_dia = [r for r in escalas_dia if r["turno"] == "DIA"]
        turnos_noite = [r for r in escalas_dia if r["turno"] == "NOITE"]

        painel_dia_col.controls.clear()

        # Cabeçalho do Painel com Botão Fixo no Topo
        btn_add_topo = ft.ElevatedButton(
            "Adicionar Pessoa",
            icon=ft.Icons.PERSON_ADD_ALT_1,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.TEAL_700,
                color=ft.Colors.WHITE,
                padding=ft.Padding(12, 6, 12, 6),
            ),
            on_click=lambda e: _abrir_modal_adicionar(),
            visible=pode_editar,
        )

        painel_dia_col.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(titulo_dia, size=16, weight=ft.FontWeight.BOLD),
                            ft.Text("Escala de Trabalho do Dia", size=12, color=ft.Colors.GREY_400),
                        ],
                    ),
                    btn_add_topo,
                ],
            )
        )
        painel_dia_col.controls.append(ft.Divider(height=1))

        # ── Bloco Turno DIA ──
        painel_dia_col.controls.append(
            ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.WB_SUNNY, size=15, color=ft.Colors.BLUE_400),
                    ft.Text("Turno DIA", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300),
                    ft.Text(f"({len(turnos_dia)} pessoa(s))", size=11, color=ft.Colors.GREY_500),
                ],
            )
        )

        if not turnos_dia:
            painel_dia_col.controls.append(
                ft.Container(
                    padding=ft.Padding.all(6),
                    content=ft.Text("Nenhuma pessoa escalada no turno do dia.", size=11, italic=True, color=ft.Colors.GREY_500),
                )
            )
        else:
            for item in turnos_dia:
                def _excluir_item(e, _id=item["id"]):
                    database.escala_turno_excluir(_id)
                    _recarregar_tudo()

                badge_extra = ft.Container(
                    padding=ft.Padding(4, 1, 4, 1),
                    border_radius=3,
                    bgcolor=ft.Colors.AMBER_900,
                    content=ft.Text("EXTRA", size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ) if item["nome_avulso"] else ft.Container()

                btn_del = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=16,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Remover da escala",
                    on_click=_excluir_item,
                    visible=pode_editar,
                )

                card_p = ft.Container(
                    padding=ft.Padding(8, 6, 8, 6),
                    border_radius=6,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_400),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.BLUE_400)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row([
                                ft.Column([
                                    ft.Row([
                                        ft.Text(item["nome_exibicao"], size=13, weight=ft.FontWeight.W_500),
                                        badge_extra,
                                    ], spacing=6),
                                    ft.Text(item["cargo_exibicao"], size=11, color=ft.Colors.GREY_400),
                                ], spacing=1),
                            ], spacing=6),
                            btn_del,
                        ],
                    ),
                )
                painel_dia_col.controls.append(card_p)

        painel_dia_col.controls.append(ft.Divider(height=1))

        # ── Bloco Turno NOITE ──
        painel_dia_col.controls.append(
            ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.BEDTIME, size=15, color=ft.Colors.PURPLE_400),
                    ft.Text("Turno NOITE", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_300),
                    ft.Text(f"({len(turnos_noite)} pessoa(s))", size=11, color=ft.Colors.GREY_500),
                ],
            )
        )

        if not turnos_noite:
            painel_dia_col.controls.append(
                ft.Container(
                    padding=ft.Padding.all(6),
                    content=ft.Text("Nenhuma pessoa escalada no turno da noite.", size=11, italic=True, color=ft.Colors.GREY_500),
                )
            )
        else:
            for item in turnos_noite:
                def _excluir_item_n(e, _id=item["id"]):
                    database.escala_turno_excluir(_id)
                    _recarregar_tudo()

                badge_extra_n = ft.Container(
                    padding=ft.Padding(4, 1, 4, 1),
                    border_radius=3,
                    bgcolor=ft.Colors.AMBER_900,
                    content=ft.Text("EXTRA", size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ) if item["nome_avulso"] else ft.Container()

                btn_del_n = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=16,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Remover da escala",
                    on_click=_excluir_item_n,
                    visible=pode_editar,
                )

                card_pn = ft.Container(
                    padding=ft.Padding(8, 6, 8, 6),
                    border_radius=6,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.PURPLE_400),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.PURPLE_400)),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row([
                                ft.Column([
                                    ft.Row([
                                        ft.Text(item["nome_exibicao"], size=13, weight=ft.FontWeight.W_500),
                                        badge_extra_n,
                                    ], spacing=6),
                                    ft.Text(item["cargo_exibicao"], size=11, color=ft.Colors.GREY_400),
                                ], spacing=1),
                            ], spacing=6),
                            btn_del_n,
                        ],
                    ),
                )
                painel_dia_col.controls.append(card_pn)

        # ── Nota para Operador (Somente Leitura) ──
        if not pode_editar:
            painel_dia_col.controls.append(ft.Divider(height=1))
            painel_dia_col.controls.append(
                ft.Container(
                    padding=ft.Padding.all(10),
                    content=ft.Text(
                        "Visualização da escala de trabalho da equipe. A edição e inclusão de turnos é restrita à gerência.",
                        size=11,
                        italic=True,
                        color=ft.Colors.GREY_500,
                    ),
                )
            )

    def _recarregar_tudo():
        _montar_grid()
        _montar_painel_dia()
        page.update()

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
