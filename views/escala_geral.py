"""
views/escala_geral.py — Escala mensal e registro de ponto diário.
Duas seções alternáveis: Escala (grade mensal) e Ponto (tabela diária).
"""

import flet as ft
import calendar
from datetime import date

import database


# ── Constantes ─────────────────────────────────────────────────────────────────

_MESES = [
    "Janeiro", "Fevereiro", "Março",    "Abril",   "Maio",     "Junho",
    "Julho",   "Agosto",    "Setembro", "Outubro", "Novembro", "Dezembro",
]

_DIAS_ABR = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# Opções compactas para a grade; "_" = limpar (excluir escala)
_OPCOES_GRADE = [
    ft.dropdown.Option("_",          text="—"),
    ft.dropdown.Option("TRABALHOU",  text="Trab."),
    ft.dropdown.Option("FALTA",      text="Falta"),
    ft.dropdown.Option("FOLGA",      text="Folga"),
    ft.dropdown.Option("FERIADO",    text="Feriado"),
    ft.dropdown.Option("EXTRA",      text="Extra"),
]

_NOME_COL = 165   # px — coluna de nome na grade
_DIA_COL  =  90   # px — coluna de cada dia
_CNT_COL  =  44   # px — colunas de contagem


# ── Helpers ────────────────────────────────────────────────────────────────────

def _iso(s: str) -> str:
    """Converte DD/MM/AAAA → YYYY-MM-DD; fallback para hoje."""
    try:
        d, m, a = s.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


def _pessoas_ordenadas() -> list:
    """Retorna pessoas ativas: INTERNO primeiro, depois ENTREGADOR, ambos por nome."""
    return sorted(
        database.pessoa_listar(apenas_ativos=True),
        key=lambda p: (0 if p["tipo"] == "INTERNO" else 1, p["nome"]),
    )


# ── View principal ─────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    hoje = date.today()

    # ── Estado dos botões de alternância ───────────────────────────────────────
    _estilo_ativo   = ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE)
    _estilo_inativo = ft.ButtonStyle(bgcolor=ft.Colors.GREY_800,   color=ft.Colors.GREY_300)

    btn_escala = ft.ElevatedButton(
        "Escala",
        icon=ft.Icons.CALENDAR_MONTH,
        style=_estilo_ativo,
    )
    btn_ponto = ft.ElevatedButton(
        "Ponto",
        icon=ft.Icons.ACCESS_TIME,
        style=_estilo_inativo,
    )

    # ══════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 1 — ESCALA MENSAL
    # ══════════════════════════════════════════════════════════════════════════

    dd_mes = ft.Dropdown(
        value=str(hoje.month),
        width=155,
        options=[ft.dropdown.Option(str(i + 1), text=_MESES[i]) for i in range(12)],
    )
    tf_ano = ft.TextField(
        value=str(hoje.year),
        width=90,
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.CENTER,
    )

    grade_col      = ft.Column(spacing=0)   # grade preenchida por _carregar_escala()
    grade_geral_col = ft.Column(spacing=0)  # grade preenchida por _carregar_visao_geral()
    resumo_geral_col = ft.Column(spacing=8) # métricas de resumo da visão geral

    _modo_escala = {"v": "individual"}  # "individual" | "geral"

    _est_sub_ativo   = ft.ButtonStyle(bgcolor=ft.Colors.TEAL_600,                          color=ft.Colors.WHITE)
    _est_sub_inativo = ft.ButtonStyle(bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.WHITE), color=ft.Colors.GREY_300)

    btn_ind = ft.ElevatedButton("Individual", style=_est_sub_ativo)
    btn_vis = ft.ElevatedButton("Visão Geral", style=_est_sub_inativo)

    def _carregar_escala(e=None):
        try:
            mes = int(dd_mes.value or hoje.month)
            ano = int(tf_ano.value  or hoje.year)
        except ValueError:
            return

        num_dias = calendar.monthrange(ano, mes)[1]
        dias     = [date(ano, mes, d) for d in range(1, num_dias + 1)]

        # Escalas do mês: (data_iso, id_pessoa) → tipo
        escalas: dict = {}
        for d in dias:
            for row in database.escala_listar_por_data(d.isoformat()):
                escalas[(d.isoformat(), row["id_pessoa"])] = row["tipo"]

        pessoas = _pessoas_ordenadas()

        grade_col.controls.clear()

        # ── Cabeçalho ──────────────────────────────────────────────────────
        cab = [ft.Container(
            width=_NOME_COL,
            content=ft.Text("Pessoa", size=12, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREY_500),
        )]
        for d in dias:
            wd  = d.weekday()
            cor = ft.Colors.RED_400 if wd == 6 else ft.Colors.GREY_500
            cab.append(ft.Container(
                width=_DIA_COL,
                content=ft.Column(
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(str(d.day),    size=12, weight=ft.FontWeight.BOLD,
                                color=cor, text_align=ft.TextAlign.CENTER),
                        ft.Text(_DIAS_ABR[wd], size=10, color=cor,
                                text_align=ft.TextAlign.CENTER),
                    ],
                ),
            ))
        for lbl in ("T", "F", "Ex", "Fe"):
            cab.append(ft.Container(
                width=_CNT_COL,
                content=ft.Text(lbl, size=11, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_500,
                                text_align=ft.TextAlign.CENTER),
            ))
        grade_col.controls.append(ft.Row(controls=cab, spacing=0))
        grade_col.controls.append(ft.Divider(height=1))

        # ── Linhas por pessoa ───────────────────────────────────────────────
        for pessoa in pessoas:
            pid  = pessoa["id"]

            def _make_handler(dia_iso: str, p_id: int):
                def handler(e):
                    val = e.control.value
                    if val and val != "_":
                        database.escala_registrar(dia_iso, p_id, val)
                    else:
                        database.escala_excluir(dia_iso, p_id)
                return handler

            cells = [ft.Container(
                width=_NOME_COL,
                content=ft.Column(spacing=0, controls=[
                    ft.Text(pessoa["nome"], size=12),
                    ft.Text(pessoa["tipo"], size=10, color=ft.Colors.GREY_500),
                ]),
            )]

            cnt = {"TRABALHOU": 0, "FALTA": 0, "EXTRA": 0, "FERIADO": 0}

            for d in dias:
                wd      = d.weekday()
                dia_iso = d.isoformat()
                val_db  = escalas.get((dia_iso, pid), "_")
                if val_db != "_" and val_db in cnt:
                    cnt[val_db] += 1

                # Segunda (wd=0) = folga geral → fundo levemente destacado
                bg = (ft.Colors.with_opacity(0.07, ft.Colors.BLUE_GREY)
                      if wd == 0 else None)

                cells.append(ft.Container(
                    width=_DIA_COL,
                    bgcolor=bg,
                    content=ft.Dropdown(
                        value=val_db,
                        width=_DIA_COL - 4,
                        options=_OPCOES_GRADE,
                        on_select=_make_handler(dia_iso, pid),
                    ),
                ))

            for key, cor in (
                ("TRABALHOU", ft.Colors.GREEN_300),
                ("FALTA",     ft.Colors.RED_300),
                ("EXTRA",     ft.Colors.GREY_500),
                ("FERIADO",   ft.Colors.GREY_500),
            ):
                cells.append(ft.Container(
                    width=_CNT_COL,
                    content=ft.Text(
                        str(cnt[key]), size=12,
                        color=cor,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ))

            grade_col.controls.append(ft.Row(controls=cells, spacing=0))

        page.update()

    def _carregar_visao_geral(e=None):
        try:
            mes = int(dd_mes.value or hoje.month)
            ano = int(tf_ano.value  or hoje.year)
        except ValueError:
            return

        num_dias     = calendar.monthrange(ano, mes)[1]
        dias         = [date(ano, mes, d) for d in range(1, num_dias + 1)]
        data_ini_iso = dias[0].isoformat()
        data_fim_iso = dias[-1].isoformat()

        # Buscar todas as escalas do período de uma vez
        conn = database.conectar()
        try:
            rows_esc = conn.execute(
                """SELECT et.data, et.id_pessoa, et.tipo
                   FROM escalas_trabalho et
                   WHERE et.data BETWEEN ? AND ?
                   ORDER BY et.data""",
                (data_ini_iso, data_fim_iso),
            ).fetchall()
            # Horas extras: soma de horas_extras > 0 via registros_ponto
            rows_pt = conn.execute(
                """SELECT rp.hora_entrada, rp.hora_saida,
                          rp.hora_inicio_intervalo, rp.hora_fim_intervalo
                   FROM registros_ponto rp
                   WHERE rp.data BETWEEN ? AND ?""",
                (data_ini_iso, data_fim_iso),
            ).fetchall()
        finally:
            conn.close()

        # escala_map[id_pessoa][data] = tipo
        escala_map: dict = {}
        for r in rows_esc:
            escala_map.setdefault(r["id_pessoa"], {})[r["data"]] = r["tipo"]

        pessoas = _pessoas_ordenadas()

        # ── Métricas de resumo ─────────────────────────────────────────
        # 1. Dias com pelo menos 1 TRABALHOU
        dias_com_trabalho = set()
        pessoas_por_dia: dict = {}   # data → count
        faltas_por_pessoa: dict = {}
        for r in rows_esc:
            if r["tipo"] == "TRABALHOU":
                dias_com_trabalho.add(r["data"])
                pessoas_por_dia[r["data"]] = pessoas_por_dia.get(r["data"], 0) + 1
            if r["tipo"] == "FALTA":
                faltas_por_pessoa[r["id_pessoa"]] = faltas_por_pessoa.get(r["id_pessoa"], 0) + 1

        total_dias_trab = len(dias_com_trabalho)
        media_por_dia   = (
            sum(pessoas_por_dia.values()) / total_dias_trab
            if total_dias_trab > 0 else 0.0
        )

        mais_faltas_nome = "—"
        if faltas_por_pessoa:
            pid_max = max(faltas_por_pessoa, key=faltas_por_pessoa.get)
            p_max   = next((p for p in pessoas if p["id"] == pid_max), None)
            if p_max:
                mais_faltas_nome = f"{p_max['nome']} ({faltas_por_pessoa[pid_max]}x)"

        total_horas_extras = 0.0
        for r in rows_pt:
            c = database.ponto_calcular_horas(
                r["hora_entrada"], r["hora_saida"],
                r["hora_inicio_intervalo"], r["hora_fim_intervalo"],
            )
            if c["completo"] and c["horas_extras"] > 0:
                total_horas_extras += c["horas_extras"]

        def _card_metrica(titulo, valor_str, cor):
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

        resumo_geral_col.controls = [
            ft.Row(spacing=10, wrap=True, controls=[
                _card_metrica("Dias c/ equipe",   str(total_dias_trab),            ft.Colors.BLUE_300),
                _card_metrica("Média/dia",         f"{media_por_dia:.1f} pessoas",  ft.Colors.GREY_500),
                _card_metrica("Mais faltas",       mais_faltas_nome,               ft.Colors.ORANGE_400),
                _card_metrica("H. extras (ponto)", f"{total_horas_extras:.1f}h",   ft.Colors.GREEN_400),
            ]),
        ]

        # ── Colunas de abreviação: tipo → (texto, cor, bold) ───────────
        _ABR = {
            "TRABALHOU": ("T",  ft.Colors.GREEN_400,  True),
            "FALTA":     ("F",  ft.Colors.RED_400,    True),
            "FOLGA":     ("Fo", ft.Colors.GREY_500,   False),
            "FERIADO":   ("Fe", ft.Colors.BLUE_300,   False),
            "EXTRA":     ("Ex", ft.Colors.YELLOW_600, True),
        }
        _VG_NOME = 160
        _VG_DIA  = 44
        _VG_RES  = 120

        def _celula_tipo(tipo):
            txt, cor, bold = _ABR.get(tipo, ("—", ft.Colors.GREY_700, False))
            return ft.Container(
                width=_VG_DIA,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(
                    txt, size=12, color=cor,
                    weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
                    text_align=ft.TextAlign.CENTER,
                ),
            )

        # totais por dia (TRABALHOU count)
        trab_por_dia = {d.isoformat(): 0 for d in dias}
        for r in rows_esc:
            if r["tipo"] == "TRABALHOU" and r["data"] in trab_por_dia:
                trab_por_dia[r["data"]] += 1

        grade_geral_col.controls.clear()

        # ── Cabeçalho ──────────────────────────────────────────────────
        _DIAS_INICIAL = ["S", "T", "Q", "Q", "S", "S", "D"]
        cab = [ft.Container(width=_VG_NOME,
                            content=ft.Text("Pessoa", size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_500))]
        for d in dias:
            wd  = d.weekday()
            cor = ft.Colors.RED_400 if wd == 6 else ft.Colors.GREY_500
            cab.append(ft.Container(
                width=_VG_DIA,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(
                    f"{d.day}{_DIAS_INICIAL[wd]}",
                    size=10, color=cor,
                    text_align=ft.TextAlign.CENTER,
                ),
            ))
        cab.append(ft.Container(
            width=_VG_RES,
            content=ft.Text("T / F / Ex", size=10,
                            color=ft.Colors.GREY_500,
                            text_align=ft.TextAlign.CENTER),
        ))
        grade_geral_col.controls.append(ft.Row(controls=cab, spacing=0))
        grade_geral_col.controls.append(ft.Divider(height=1))

        # ── Linhas por pessoa ───────────────────────────────────────────
        grupo_atual = None
        for pessoa in pessoas:
            pid  = pessoa["id"]
            tipo_p = pessoa["tipo"]

            # Separador entre grupos
            if tipo_p != grupo_atual:
                if grupo_atual is not None:
                    grade_geral_col.controls.append(ft.Divider(height=2))
                grupo_atual = tipo_p

            bg_nome = (
                ft.Colors.with_opacity(0.06, ft.Colors.BLUE)
                if tipo_p == "INTERNO"
                else ft.Colors.with_opacity(0.06, ft.Colors.ORANGE)
            )

            cells = [ft.Container(
                width=_VG_NOME,
                bgcolor=bg_nome,
                padding=ft.Padding(left=6, right=2, top=4, bottom=4),
                content=ft.Column(spacing=0, controls=[
                    ft.Text(pessoa["nome"], size=12),
                    ft.Text(tipo_p, size=9, color=ft.Colors.GREY_500),
                ]),
            )]

            p_esc = escala_map.get(pid, {})
            cnt = {"TRABALHOU": 0, "FALTA": 0, "EXTRA": 0}

            for d in dias:
                dia_iso = d.isoformat()
                wd      = d.weekday()
                tipo_dia = p_esc.get(dia_iso)
                bg_cel   = (ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY)
                            if wd == 0 else None)
                c = _celula_tipo(tipo_dia)
                c.bgcolor = bg_cel
                cells.append(c)
                if tipo_dia in cnt:
                    cnt[tipo_dia] += 1

            resumo_txt = f"T:{cnt['TRABALHOU']}  F:{cnt['FALTA']}  Ex:{cnt['EXTRA']}"
            cells.append(ft.Container(
                width=_VG_RES,
                padding=ft.Padding(left=6, right=0, top=0, bottom=0),
                content=ft.Row(spacing=4, controls=[
                    ft.Text(f"T:{cnt['TRABALHOU']}", size=11,
                            color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD),
                    ft.Text(f"F:{cnt['FALTA']}",     size=11, color=ft.Colors.RED_400),
                    ft.Text(f"Ex:{cnt['EXTRA']}",    size=11, color=ft.Colors.YELLOW_600),
                ]),
            ))
            grade_geral_col.controls.append(ft.Row(controls=cells, spacing=0))

        # ── Rodapé: TRABALHOU por dia ───────────────────────────────────
        grade_geral_col.controls.append(ft.Divider(height=1))
        rod = [ft.Container(
            width=_VG_NOME,
            padding=ft.Padding(left=6, right=0, top=0, bottom=0),
            content=ft.Text("Equipe/dia", size=10,
                            color=ft.Colors.GREY_500,
                            weight=ft.FontWeight.BOLD),
        )]
        for d in dias:
            n = trab_por_dia[d.isoformat()]
            rod.append(ft.Container(
                width=_VG_DIA,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(
                    str(n) if n > 0 else "·",
                    size=11,
                    color=ft.Colors.GREEN_300 if n > 0 else ft.Colors.GREY_800,
                    text_align=ft.TextAlign.CENTER,
                ),
            ))
        rod.append(ft.Container(width=_VG_RES))
        grade_geral_col.controls.append(ft.Row(controls=rod, spacing=0))

        page.update()

    # Cards da seção escala (visibilidade controlada pelo toggle)
    card_escala_controles = ft.Card(
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=ft.Column(spacing=12, controls=[
                ft.Text("Escala Mensal", size=14, weight=ft.FontWeight.BOLD),
                ft.Row(controls=[
                    dd_mes, tf_ano,
                    ft.ElevatedButton(
                        "Carregar",
                        icon=ft.Icons.REFRESH,
                        on_click=lambda e: (
                            _carregar_escala(e)
                            if _modo_escala["v"] == "individual"
                            else _carregar_visao_geral(e)
                        ),
                    ),
                ], spacing=12),
                ft.Row(controls=[btn_ind, btn_vis], spacing=8),
            ]),
        ),
    )

    card_escala_grade = ft.Card(
        content=ft.Container(
            padding=ft.Padding.all(12),
            content=ft.Row(
                scroll=ft.ScrollMode.AUTO,
                controls=[grade_col],
            ),
        ),
    )

    card_visao_geral_resumo = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=resumo_geral_col,
        ),
    )

    card_visao_geral_grade = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(12),
            content=ft.Row(
                scroll=ft.ScrollMode.AUTO,
                controls=[grade_geral_col],
            ),
        ),
    )

    # ── Sub-alternância Individual / Visão Geral ──────────────────────────────

    def _mostrar_individual(e=None):
        _modo_escala["v"]               = "individual"
        btn_ind.style                   = _est_sub_ativo
        btn_vis.style                   = _est_sub_inativo
        card_escala_grade.visible       = True
        card_visao_geral_resumo.visible = False
        card_visao_geral_grade.visible  = False
        page.update()

    def _mostrar_visao_geral(e=None):
        _modo_escala["v"]               = "geral"
        btn_ind.style                   = _est_sub_inativo
        btn_vis.style                   = _est_sub_ativo
        card_escala_grade.visible       = False
        card_visao_geral_resumo.visible = True
        card_visao_geral_grade.visible  = True
        _carregar_visao_geral()

    btn_ind.on_click = _mostrar_individual
    btn_vis.on_click = _mostrar_visao_geral

    # ══════════════════════════════════════════════════════════════════════════
    #  SEÇÃO 2 — PONTO DIÁRIO
    # ══════════════════════════════════════════════════════════════════════════

    tf_data_ponto = ft.TextField(
        value=hoje.strftime("%d/%m/%Y"),
        width=140,
        text_align=ft.TextAlign.CENTER,
        hint_text="DD/MM/AAAA",
    )

    def _on_date_picked(e):
        if e.control.value:
            tf_data_ponto.value = e.control.value.strftime("%d/%m/%Y")
            page.update()

    date_picker = ft.DatePicker(on_change=_on_date_picked)
    page.overlay.append(date_picker)

    tabela_ponto_col = ft.Column(spacing=4)

    def _carregar_ponto(e=None):
        data_iso = _iso(tf_data_ponto.value)

        pessoas = _pessoas_ordenadas()

        ponto_map = {
            row["id_pessoa"]: row
            for row in database.ponto_listar_por_data(data_iso)
        }

        tabela_ponto_col.controls.clear()

        # Cabeçalho
        tabela_ponto_col.controls.append(ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(expand=3, content=ft.Text(
                    "Pessoa", size=12, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_500,
                )),
                ft.Container(width=90, content=ft.Text(
                    "Entrada", size=12, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_500,
                )),
                ft.Container(width=90, content=ft.Text(
                    "Iní. Int.", size=12, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_500,
                )),
                ft.Container(width=90, content=ft.Text(
                    "Fim Int.", size=12, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_500,
                )),
                ft.Container(width=90, content=ft.Text(
                    "Saída", size=12, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREY_500,
                )),
                ft.Container(width=75),
                ft.Container(width=28),
            ],
        ))
        tabela_ponto_col.controls.append(ft.Divider(height=1))

        dia_total_liquidas = 0.0
        dia_total_extras   = 0.0
        dia_completos      = 0

        for pessoa in pessoas:
            pid = pessoa["id"]
            pt  = ponto_map.get(pid)

            tf_ent = ft.TextField(
                value=pt["hora_entrada"]          if pt else "",
                width=90, hint_text="HH:MM",
            )
            tf_ini = ft.TextField(
                value=pt["hora_inicio_intervalo"] if pt else "",
                width=90, hint_text="HH:MM",
            )
            tf_fim = ft.TextField(
                value=pt["hora_fim_intervalo"]    if pt else "",
                width=90, hint_text="HH:MM",
            )
            tf_sai = ft.TextField(
                value=pt["hora_saida"]            if pt else "",
                width=90, hint_text="HH:MM",
            )

            tem_entrada = bool(pt and pt["hora_entrada"])
            icone = ft.Icon(
                (ft.Icons.CHECK_CIRCLE if tem_entrada
                 else ft.Icons.RADIO_BUTTON_UNCHECKED),
                color=(ft.Colors.GREEN_400 if tem_entrada
                       else ft.Colors.GREY_600),
                size=20,
            )

            def _salvar_ponto(e,
                              _pid=pid,
                              _ent=tf_ent, _ini=tf_ini,
                              _fim=tf_fim, _sai=tf_sai,
                              _ico=icone):
                if (_ent is None or _ent.value is None or
                        _ini is None or _ini.value is None or
                        _fim is None or _fim.value is None or
                        _sai is None or _sai.value is None):
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text("Preencha os horários antes de salvar."),
                        bgcolor=ft.Colors.ORANGE_700,
                        open=True,
                    ))
                    page.update()
                    return
                d_iso = _iso(tf_data_ponto.value)
                ent   = _ent.value.strip()
                ini   = _ini.value.strip()
                fim   = _fim.value.strip()
                sai   = _sai.value.strip()
                if ent:
                    database.ponto_registrar_entrada(d_iso, _pid, ent)
                    _ico.name  = ft.Icons.CHECK_CIRCLE
                    _ico.color = ft.Colors.GREEN_400
                if ini or fim:
                    database.ponto_registrar_intervalo(d_iso, _pid, ini, fim)
                if sai:
                    database.ponto_registrar_saida(d_iso, _pid, sai)
                page.update()

            tabela_ponto_col.controls.append(ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(expand=3, content=ft.Column(
                        spacing=0,
                        controls=[
                            ft.Text(pessoa["nome"], size=13,
                                    weight=ft.FontWeight.W_500),
                            ft.Text(pessoa["tipo"], size=11,
                                    color=ft.Colors.GREY_500),
                        ],
                    )),
                    tf_ent,
                    tf_ini,
                    tf_fim,
                    tf_sai,
                    ft.Container(
                        width=75,
                        content=ft.ElevatedButton(
                            "Salvar",
                            on_click=_salvar_ponto,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.TEAL_700,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                    ),
                    icone,
                ],
            ))

            # Detalhe de horas (exibido se jornada completa)
            if pt and pt["hora_entrada"] and pt["hora_saida"]:
                try:
                    ch = float(pessoa["carga_horaria_diaria"] or 8.0)
                except Exception:
                    ch = 8.0
                calc = database.ponto_calcular_horas(
                    pt["hora_entrada"],
                    pt["hora_saida"],
                    pt["hora_inicio_intervalo"],
                    pt["hora_fim_intervalo"],
                    ch,
                )
                if calc["completo"]:
                    dia_completos      += 1
                    dia_total_liquidas += calc["horas_liquidas"]
                    if calc["horas_extras"] > 0:
                        dia_total_extras += calc["horas_extras"]

                    he = calc["horas_extras"]
                    if he > 0:
                        txt_he = f"+{he:.1f}h extras"
                        cor_he = ft.Colors.GREEN_400
                    elif he < 0:
                        txt_he = f"{he:.1f}h faltantes"
                        cor_he = ft.Colors.ORANGE_400
                    else:
                        txt_he = "Jornada cumprida"
                        cor_he = ft.Colors.GREEN_300

                    tabela_ponto_col.controls.append(ft.Container(
                        padding=ft.Padding(left=16, right=0, top=0, bottom=4),
                        content=ft.Row(
                            spacing=16,
                            controls=[
                                ft.Text(
                                    f"Brutas: {calc['horas_brutas']:.1f}h",
                                    size=11, color=ft.Colors.GREY_500,
                                ),
                                ft.Text(
                                    f"Intervalo: {calc['minutos_intervalo']}min",
                                    size=11, color=ft.Colors.GREY_500,
                                ),
                                ft.Text(
                                    f"Líquidas: {calc['horas_liquidas']:.1f}h",
                                    size=11, color=ft.Colors.GREY_500,
                                ),
                                ft.Text(
                                    txt_he,
                                    size=11,
                                    weight=ft.FontWeight.BOLD if he > 0 else ft.FontWeight.NORMAL,
                                    color=cor_he,
                                ),
                            ],
                        ),
                    ))

        # Rodapé do dia com totais
        if dia_completos > 0:
            tabela_ponto_col.controls.append(ft.Divider(height=1))
            rodape_controls = [
                ft.Text(
                    f"Completos: {dia_completos}",
                    size=12, color=ft.Colors.GREY_500,
                ),
                ft.Text(
                    f"Total líquido: {dia_total_liquidas:.1f}h",
                    size=12, color=ft.Colors.GREY_500,
                ),
            ]
            if dia_total_extras > 0:
                rodape_controls.append(ft.Text(
                    f"Extras do dia: +{dia_total_extras:.1f}h",
                    size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400,
                ))
            tabela_ponto_col.controls.append(ft.Row(
                spacing=20, controls=rodape_controls,
            ))

        page.update()

    # Cards da seção ponto (ocultos por padrão)
    card_ponto_controles = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=ft.Column(spacing=12, controls=[
                ft.Text("Ponto Diário", size=14, weight=ft.FontWeight.BOLD),
                ft.Row(controls=[
                    tf_data_ponto,
                    ft.IconButton(
                        icon=ft.Icons.CALENDAR_MONTH,
                        tooltip="Selecionar data",
                        on_click=lambda e: (
                            setattr(date_picker, "open", True),
                            page.update(),
                        ),
                    ),
                    ft.ElevatedButton(
                        "Carregar",
                        icon=ft.Icons.REFRESH,
                        on_click=_carregar_ponto,
                    ),
                ], spacing=8),
            ]),
        ),
    )

    card_ponto_tabela = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=tabela_ponto_col,
        ),
    )

    # ── Alternância entre seções ───────────────────────────────────────────────

    def _mostrar_escala(e=None):
        card_escala_controles.visible   = True
        card_escala_grade.visible       = (_modo_escala["v"] == "individual")
        card_visao_geral_resumo.visible = (_modo_escala["v"] == "geral")
        card_visao_geral_grade.visible  = (_modo_escala["v"] == "geral")
        card_ponto_controles.visible    = False
        card_ponto_tabela.visible       = False
        btn_escala.style = _estilo_ativo
        btn_ponto.style  = _estilo_inativo
        page.update()

    def _mostrar_ponto(e=None):
        card_escala_controles.visible   = False
        card_escala_grade.visible       = False
        card_visao_geral_resumo.visible = False
        card_visao_geral_grade.visible  = False
        card_ponto_controles.visible    = True
        card_ponto_tabela.visible       = True
        btn_escala.style = _estilo_inativo
        btn_ponto.style  = _estilo_ativo
        page.update()

    btn_escala.on_click = _mostrar_escala
    btn_ponto.on_click  = _mostrar_ponto

    # Carrega a grade do mês atual ao abrir a tela
    _carregar_escala()

    # ── Layout ─────────────────────────────────────────────────────────────────

    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            # Barra de alternância
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(12),
                content=ft.Row(controls=[
                    ft.Text("Escala e Ponto", size=18,
                            weight=ft.FontWeight.BOLD),
                    ft.VerticalDivider(width=16),
                    btn_escala,
                    btn_ponto,
                ], spacing=12),
            )),
            # Seção Escala
            card_escala_controles,
            card_escala_grade,
            card_visao_geral_resumo,
            card_visao_geral_grade,
            # Seção Ponto
            card_ponto_controles,
            card_ponto_tabela,
        ],
    )
