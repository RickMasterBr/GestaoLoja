"""
views/parametros.py — Tela de Parâmetros com 6 abas de cadastro.
Gerencia Pessoas, Bairros, Plataformas, Métodos de Pagamento,
Categorias Extras e Configurações Gerais.
"""

import csv
import os
from datetime import date, timedelta

import flet as ft
import database


# ── Utilitário ────────────────────────────────────────────────────────────────

def _to_float(s: str) -> float:
    try:
        return float((s or "0").replace(",", ".").strip())
    except ValueError:
        return 0.0


def _snack(page: ft.Page, msg: str, cor=ft.Colors.GREEN_700):
    page.overlay.append(ft.SnackBar(
        content=ft.Text(msg), bgcolor=cor, open=True,
    ))
    page.update()


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def _fechar(e, dlg, page):
    dlg.open = False
    page.update()


def _confirmar_exclusao(page, descricao: str, on_confirmar) -> None:
    """Abre um AlertDialog pedindo confirmação antes de excluir."""
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar exclusão"),
        content=ft.Text(
            f"Deseja excluir {descricao}? Esta ação não pode ser desfeita."
        ),
        actions=[
            ft.TextButton("Cancelar",
                          on_click=lambda e: _fechar(e, dlg, page)),
            ft.ElevatedButton(
                "Excluir",
                on_click=lambda e: (_fechar(e, dlg, page), on_confirmar()),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE,
                ),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def view(page: ft.Page) -> ft.Control:

    # ══════════════════════════════════════════
    #  ABA 1 — PESSOAS
    # ══════════════════════════════════════════

    _pessoa_id: dict = {"v": None}

    tf_p_nome     = ft.TextField(label="Nome", expand=True)
    dd_p_tipo     = ft.Dropdown(
        label="Tipo", width=160,
        options=[ft.dropdown.Option("INTERNO"), ft.dropdown.Option("ENTREGADOR")],
    )
    tf_p_cargo    = ft.TextField(label="Cargo", expand=True)
    dd_p_tiposal  = ft.Dropdown(
        label="Tipo Salário", width=175,
        options=[
            ft.dropdown.Option("FIXO"),
            ft.dropdown.Option("DIARIO"),
            ft.dropdown.Option("ENTREGADOR"),
        ],
    )
    tf_p_salario  = ft.TextField(label="Salário Base (R$)",  keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    tf_p_diaria   = ft.TextField(label="Valor Diária (R$)",  keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    tf_p_feriado  = ft.TextField(label="Bônus Feriado (R$)", keyboard_type=ft.KeyboardType.NUMBER, width=160, value="60.00")
    tf_p_extra    = ft.TextField(label="Bônus Extra (R$)",   keyboard_type=ft.KeyboardType.NUMBER, width=160, value="50.00")
    tf_p_falta    = ft.TextField(label="Desconto Falta (R$)",keyboard_type=ft.KeyboardType.NUMBER, width=160, value="60.00")
    cb_p_ativo    = ft.Checkbox(label="Ativo", value=True)
    txt_p_erro    = ft.Text("", color=ft.Colors.RED_400, size=12)
    lbl_p_titulo  = ft.Text("Nova Pessoa", size=14, weight=ft.FontWeight.BOLD)

    # Acesso ao Sistema
    dd_perfil = ft.Dropdown(
        label="Perfil de Acesso", width=180,
        options=[
            ft.dropdown.Option("OPERADOR"),
            ft.dropdown.Option("GERENTE"),
            ft.dropdown.Option("ADMIN"),
            ft.dropdown.Option(key="SEM_ACESSO", text="Sem Acesso ao Sistema"),
        ],
        value="OPERADOR",
    )
    tf_pin             = ft.TextField(label="PIN (4 dígitos)", password=True, max_length=4,
                                       keyboard_type=ft.KeyboardType.NUMBER, width=160)
    tf_pin_confirmar   = ft.TextField(label="Confirmar PIN",   password=True, max_length=4,
                                       keyboard_type=ft.KeyboardType.NUMBER, width=160)
    txt_pin_nota       = ft.Text(
        "Deixe o PIN em branco para manter o atual. Defina um PIN para habilitar o login.",
        size=11, italic=True, color=ft.Colors.GREY_500,
    )
    secao_acesso = ft.Column(
        spacing=8,
        visible=True,
        controls=[
            ft.Text("Acesso ao Sistema", size=13, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1),
            ft.Row([dd_perfil, tf_pin, tf_pin_confirmar], spacing=12),
            txt_pin_nota,
        ],
    )

    # Dados pessoais
    tf_dp_cpf     = ft.TextField(label="CPF",              width=160, hint_text="000.000.000-00")
    tf_dp_rg      = ft.TextField(label="RG",               width=160, hint_text="00.000.000-0")
    tf_dp_nasc    = ft.TextField(label="Data Nascimento",  width=160, hint_text="DD/MM/AAAA")
    tf_dp_tel     = ft.TextField(label="Telefone",         width=180, hint_text="(21) 99999-9999")
    tf_dp_end     = ft.TextField(label="Endereço",         expand=True)
    tf_dp_obs     = ft.TextField(label="Observações",      expand=True,
                                  multiline=True, min_lines=2, max_lines=3)

    linha_p_salario  = ft.Row([tf_p_salario], visible=True)
    linha_p_diaria   = ft.Row([tf_p_diaria],  visible=False)
    linha_p_holerite = ft.Row(
        controls=[tf_p_feriado, tf_p_extra, tf_p_falta],
        spacing=12, visible=True,
    )

    tabela_pessoas = ft.Column(spacing=0)

    def _on_tiposal_change(e):
        ts = dd_p_tiposal.value
        linha_p_salario.visible  = (ts == "FIXO")
        linha_p_diaria.visible   = (ts in ("DIARIO", "ENTREGADOR"))
        linha_p_holerite.visible = (ts != "ENTREGADOR")
        page.update()

    def _on_tipo_change(e):
        eh_entregador = dd_p_tipo.value == "ENTREGADOR"
        if eh_entregador:
            dd_p_tiposal.value = "ENTREGADOR"
            linha_p_salario.visible  = False
            linha_p_diaria.visible   = True
            linha_p_holerite.visible = False
        else:
            if dd_p_tiposal.value == "ENTREGADOR":
                dd_p_tiposal.value = None
                linha_p_salario.visible  = True
                linha_p_diaria.visible   = False
                linha_p_holerite.visible = True
        secao_acesso.visible = not eh_entregador
        page.update()

    dd_p_tipo.on_select    = _on_tipo_change
    dd_p_tiposal.on_select = _on_tiposal_change

    def _refresh_pessoas():
        rows = database.pessoa_listar(apenas_ativos=False)
        linhas = []
        for p in rows:
            ts = p["tipo_salario"] or ""
            if ts == "DIARIO":
                sal_txt = f"R$ {p['diaria_valor']:.2f}/dia"
            elif ts == "ENTREGADOR":
                sal_txt = f"Diária R$ {p['diaria_valor']:.2f}"
            else:
                sal_txt = f"R$ {p['salario_base']:.2f}"

            status_cor = ft.Colors.GREEN_400 if p["status_ativo"] else ft.Colors.GREY_500
            status_txt = "Ativo" if p["status_ativo"] else "Inativo"

            def _on_editar_pessoa(pid):
                def handler(e):
                    r = database.pessoa_buscar(pid)
                    if not r:
                        return
                    _pessoa_id["v"]      = pid
                    lbl_p_titulo.value   = f"Editando: {r['nome']}"
                    tf_p_nome.value      = r["nome"]
                    dd_p_tipo.value      = r["tipo"]
                    tf_p_cargo.value     = r["cargo"] or ""
                    dd_p_tiposal.value   = r["tipo_salario"]
                    tf_p_salario.value   = f"{r['salario_base']:.2f}"
                    tf_p_diaria.value    = f"{r['diaria_valor']:.2f}"
                    cb_p_ativo.value     = bool(r["status_ativo"])
                    try:
                        tf_p_feriado.value = f"{r['valor_feriado']:.2f}"
                        tf_p_extra.value   = f"{r['valor_extra']:.2f}"
                        tf_p_falta.value   = f"{r['valor_falta']:.2f}"
                    except (IndexError, KeyError):
                        tf_p_feriado.value = "60.00"
                        tf_p_extra.value   = "50.00"
                        tf_p_falta.value   = "60.00"
                    ts = r["tipo_salario"] or ""
                    linha_p_salario.visible  = (ts == "FIXO")
                    linha_p_diaria.visible   = (ts in ("DIARIO", "ENTREGADOR"))
                    linha_p_holerite.visible = (ts != "ENTREGADOR")
                    secao_acesso.visible     = (r["tipo"] != "ENTREGADOR")
                    txt_p_erro.value = ""
                    _carregar_dias_fixos(pid)
                    card_dias_fixos.visible = True
                    # Dados pessoais
                    def _iso_para_br(iso):
                        try:
                            return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso else ""
                        except Exception:
                            return ""
                    tf_dp_cpf.value  = r["cpf"]  or ""
                    tf_dp_rg.value   = r["rg"]   or ""
                    tf_dp_nasc.value = _iso_para_br(r["data_nascimento"])
                    tf_dp_tel.value  = r["telefone"] or ""
                    tf_dp_end.value  = r["endereco"] or ""
                    tf_dp_obs.value  = r["observacoes_pessoais"] or ""
                    card_dados_pessoais.visible = True
                    dd_perfil.value          = r["perfil_acesso"] or "OPERADOR"
                    tf_pin.value             = ""
                    tf_pin_confirmar.value   = ""
                    page.update()
                return handler

            def _on_toggle_pessoa(pid, ativo_atual):
                def handler(e):
                    database.pessoa_atualizar(pid, status_ativo=0 if ativo_atual else 1)
                    _refresh_pessoas()
                    page.update()
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(p["nome"])),
                ft.DataCell(ft.Text(p["tipo"])),
                ft.DataCell(ft.Text(p["cargo"] or "—")),
                ft.DataCell(ft.Text(sal_txt)),
                ft.DataCell(ft.Text(status_txt, color=status_cor)),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.TextButton("Editar",
                                  on_click=_on_editar_pessoa(p["id"])),
                    ft.TextButton(
                        "Inativar" if p["status_ativo"] else "Reativar",
                        on_click=_on_toggle_pessoa(p["id"], p["status_ativo"]),
                        style=ft.ButtonStyle(
                            color=ft.Colors.RED_400 if p["status_ativo"] else ft.Colors.GREEN_400,
                        ),
                    ),
                ])),
            ]))

        tabela_pessoas.controls.clear()
        if not linhas:
            tabela_pessoas.controls.append(
                ft.Text("Nenhuma pessoa cadastrada.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_pessoas.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Nome")),
                            ft.DataColumn(ft.Text("Tipo")),
                            ft.DataColumn(ft.Text("Cargo")),
                            ft.DataColumn(ft.Text("Salário")),
                            ft.DataColumn(ft.Text("Status")),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _limpar_pessoa():
        _pessoa_id["v"]          = None
        lbl_p_titulo.value       = "Nova Pessoa"
        tf_p_nome.value          = ""
        dd_p_tipo.value          = None
        tf_p_cargo.value         = ""
        dd_p_tiposal.value       = None
        tf_p_salario.value       = ""
        tf_p_diaria.value        = ""
        tf_p_feriado.value       = "60.00"
        tf_p_extra.value         = "50.00"
        tf_p_falta.value         = "60.00"
        cb_p_ativo.value         = True
        linha_p_salario.visible  = True
        linha_p_diaria.visible   = False
        linha_p_holerite.visible = True
        txt_p_erro.value         = ""
        _limpar_dias_fixos()
        card_dias_fixos.visible  = False
        tf_dp_cpf.value  = ""
        tf_dp_rg.value   = ""
        tf_dp_nasc.value = ""
        tf_dp_tel.value  = ""
        tf_dp_end.value  = ""
        tf_dp_obs.value  = ""
        card_dados_pessoais.visible = False
        dd_perfil.value          = "OPERADOR"
        tf_pin.value             = ""
        tf_pin_confirmar.value   = ""

    def _salvar_pessoa(e):
        txt_p_erro.value = ""
        nome = tf_p_nome.value.strip()
        if not nome:
            txt_p_erro.value = "Nome é obrigatório."
            page.update()
            return
        if not dd_p_tipo.value:
            txt_p_erro.value = "Selecione o tipo (INTERNO ou ENTREGADOR)."
            page.update()
            return

        ts      = dd_p_tiposal.value
        salario = _to_float(tf_p_salario.value) if ts == "FIXO"             else 0.0
        diaria  = _to_float(tf_p_diaria.value)  if ts in ("DIARIO","ENTREGADOR") else 0.0

        kwargs_hol = {}
        if ts != "ENTREGADOR":
            kwargs_hol = dict(
                valor_feriado=_to_float(tf_p_feriado.value),
                valor_extra=  _to_float(tf_p_extra.value),
                valor_falta=  _to_float(tf_p_falta.value),
            )

        if _pessoa_id["v"] is None:
            pid = database.pessoa_inserir(
                nome=nome,
                tipo=dd_p_tipo.value,
                cargo=tf_p_cargo.value.strip() or None,
                salario_base=salario,
                tipo_salario=ts,
                diaria_valor=diaria,
                status_ativo=cb_p_ativo.value,
            )
            if kwargs_hol:
                database.pessoa_atualizar(pid, **kwargs_hol)
        else:
            pid = _pessoa_id["v"]
            database.pessoa_atualizar(
                pid,
                nome=nome,
                tipo=dd_p_tipo.value,
                cargo=tf_p_cargo.value.strip() or None,
                salario_base=salario,
                tipo_salario=ts,
                diaria_valor=diaria,
                status_ativo=int(cb_p_ativo.value),
                **kwargs_hol,
            )

        # PIN / perfil de acesso
        pin     = tf_pin.value.strip()
        pin_c   = tf_pin_confirmar.value.strip()
        if pin or pin_c:
            if pin != pin_c:
                txt_p_erro.value = "Os PINs não coincidem."
                page.update()
                return
            if not pin.isdigit() or len(pin) != 4:
                txt_p_erro.value = "O PIN deve ter exatamente 4 dígitos numéricos."
                page.update()
                return
            database.usuario_definir_pin(pid, pin)
        database.usuario_definir_perfil(pid, dd_perfil.value or "OPERADOR")

        database.log_registrar(
            acao="ALTERAR_PESSOA",
            tabela="cad_pessoas",
            id_registro=pid,
            descricao=f"Pessoa salva — {nome} ({dd_p_tipo.value})",
        )
        _limpar_pessoa()
        _refresh_pessoas()
        page.update()

    def _cancelar_pessoa(e):
        _limpar_pessoa()
        page.update()

    # ── Dias Fixos de Trabalho ─────────────────────────────────────────────
    # Ter=1, Qua=2, Qui=3, Sex=4, Sáb=5, Dom=6  (Segunda=0 é folga geral)
    _DIAS_FIXOS = [
        (1, "Terça"),
        (2, "Quarta"),
        (3, "Quinta"),
        (4, "Sexta"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    _df_checks: dict = {}
    _df_horas:  dict = {}

    for _dia, _nome in _DIAS_FIXOS:
        _cb = ft.Checkbox(label=_nome, value=False)
        _tf = ft.TextField(width=90, hint_text="HH:MM", disabled=True)
        _df_checks[_dia] = _cb
        _df_horas[_dia]  = _tf

        def _on_df_change(e, d=_dia):
            _df_horas[d].disabled = not _df_checks[d].value
            if not _df_checks[d].value:
                _df_horas[d].value = ""
            page.update()

        _cb.on_change = _on_df_change

    def _limpar_dias_fixos():
        for d, _ in _DIAS_FIXOS:
            _df_checks[d].value   = False
            _df_horas[d].value    = ""
            _df_horas[d].disabled = True

    def _carregar_dias_fixos(pid: int):
        _limpar_dias_fixos()
        for row in database.dias_fixos_listar(pid):
            d = row["dia_semana"]
            if d in _df_checks:
                _df_checks[d].value   = True
                _df_horas[d].value    = row["horario_entrada"] or ""
                _df_horas[d].disabled = False

    def _salvar_dias_fixos(e):
        pid = _pessoa_id["v"]
        if pid is None:
            return
        dias = [
            {"dia_semana": d, "horario_entrada": _df_horas[d].value.strip() or None}
            for d, _ in _DIAS_FIXOS
            if _df_checks[d].value
        ]
        database.dias_fixos_salvar(pid, dias)
        _snack(page, "Dias fixos salvos!")

    # Grade: 2 dias por linha
    _df_grade_linhas = []
    for i in range(0, len(_DIAS_FIXOS), 2):
        par = _DIAS_FIXOS[i:i + 2]
        row_ctrls = []
        for d, _ in par:
            row_ctrls += [_df_checks[d], _df_horas[d]]
        _df_grade_linhas.append(ft.Row(controls=row_ctrls, spacing=16))

    card_dias_fixos = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Dias Fixos de Trabalho",
                            size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    *_df_grade_linhas,
                    ft.ElevatedButton(
                        "Salvar Dias Fixos",
                        icon=ft.Icons.CALENDAR_MONTH,
                        on_click=_salvar_dias_fixos,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.INDIGO_600,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
            ),
        ),
    )

    def _salvar_dados_pessoais(e):
        pid = _pessoa_id["v"]
        if pid is None:
            return
        nasc_val = tf_dp_nasc.value.strip()
        if nasc_val and "/" in nasc_val:
            try:
                d, m, a = nasc_val.split("/")
                nasc_iso = f"{a}-{m.zfill(2)}-{d.zfill(2)}"
            except Exception:
                nasc_iso = nasc_val
        else:
            nasc_iso = nasc_val or None
        nome = database.pessoa_buscar(pid)["nome"]
        database.pessoa_atualizar(
            pid,
            cpf=tf_dp_cpf.value.strip() or None,
            rg=tf_dp_rg.value.strip() or None,
            data_nascimento=nasc_iso,
            telefone=tf_dp_tel.value.strip() or None,
            endereco=tf_dp_end.value.strip() or None,
            observacoes_pessoais=tf_dp_obs.value.strip() or None,
        )
        _snack(page, f"Dados pessoais de {nome} salvos.")

    card_dados_pessoais = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(16),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Dados Pessoais", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row([tf_dp_cpf, tf_dp_rg], spacing=12),
                    ft.Row([tf_dp_nasc, tf_dp_tel], spacing=12),
                    ft.Row([tf_dp_end], spacing=12),
                    ft.Row([tf_dp_obs], spacing=12),
                    ft.ElevatedButton(
                        "Salvar Dados Pessoais",
                        icon=ft.Icons.PERSON,
                        on_click=_salvar_dados_pessoais,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.TEAL_700,
                            color=ft.Colors.WHITE,
                        ),
                    ),
                ],
            ),
        ),
    )

    _refresh_pessoas()

    tab_pessoas = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    lbl_p_titulo,
                    ft.Row([tf_p_nome, dd_p_tipo], spacing=12),
                    ft.Row([tf_p_cargo, dd_p_tiposal], spacing=12),
                    linha_p_salario,
                    linha_p_diaria,
                    linha_p_holerite,
                    cb_p_ativo,
                    secao_acesso,
                    txt_p_erro,
                    ft.Row([
                        ft.ElevatedButton("Salvar",   icon=ft.Icons.SAVE,  on_click=_salvar_pessoa),
                        ft.TextButton("Cancelar", on_click=_cancelar_pessoa),
                    ]),
                ]),
            )),
            card_dias_fixos,
            card_dados_pessoais,
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Pessoas Cadastradas", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_pessoas,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 2 — BAIRROS
    # ══════════════════════════════════════════

    _bairro_id: dict = {"v": None}

    tf_b_nome    = ft.TextField(label="Nome do Bairro",          expand=True)
    tf_b_taxa    = ft.TextField(label="Taxa Cobrada (R$)",        keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    tf_b_repasse = ft.TextField(label="Repasse Entregador (R$)",  keyboard_type=ft.KeyboardType.NUMBER, expand=True)
    txt_b_erro   = ft.Text("", color=ft.Colors.RED_400, size=12)
    lbl_b_titulo = ft.Text("Novo Bairro", size=14, weight=ft.FontWeight.BOLD)

    tabela_bairros = ft.Column(spacing=0)

    def _refresh_bairros():
        rows = database.bairro_listar()
        linhas = []
        for b in rows:
            def _on_editar_bairro(bid):
                def handler(e):
                    r = database.bairro_buscar(bid)
                    if not r:
                        return
                    _bairro_id["v"]    = bid
                    lbl_b_titulo.value = f"Editando: {r['nome_bairro']}"
                    tf_b_nome.value    = r["nome_bairro"]
                    tf_b_taxa.value    = f"{r['taxa_cobrada']:.2f}"
                    tf_b_repasse.value = f"{r['repasse_entregador']:.2f}"
                    txt_b_erro.value   = ""
                    page.update()
                return handler

            def _on_excluir_bairro(bid, nome):
                def handler(e):
                    def _excluir():
                        database.bairro_excluir(bid)
                        _refresh_bairros()
                        page.update()
                    _confirmar_exclusao(page, f"o bairro '{nome}'", _excluir)
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(b["nome_bairro"])),
                ft.DataCell(ft.Text(f"R$ {b['taxa_cobrada']:.2f}")),
                ft.DataCell(ft.Text(f"R$ {b['repasse_entregador']:.2f}")),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.TextButton("Editar", on_click=_on_editar_bairro(b["id"])),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Excluir bairro",
                        on_click=_on_excluir_bairro(b["id"], b["nome_bairro"]),
                    ),
                ])),
            ]))

        tabela_bairros.controls.clear()
        if not linhas:
            tabela_bairros.controls.append(
                ft.Text("Nenhum bairro cadastrado.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_bairros.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Bairro")),
                            ft.DataColumn(ft.Text("Taxa Cobrada"),       numeric=True),
                            ft.DataColumn(ft.Text("Repasse Entregador"), numeric=True),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _limpar_bairro():
        _bairro_id["v"]    = None
        lbl_b_titulo.value = "Novo Bairro"
        tf_b_nome.value    = ""
        tf_b_taxa.value    = ""
        tf_b_repasse.value = ""
        txt_b_erro.value   = ""

    def _salvar_bairro(e):
        txt_b_erro.value = ""
        nome = tf_b_nome.value.strip()
        if not nome:
            txt_b_erro.value = "Nome do bairro é obrigatório."
            page.update()
            return
        taxa    = _to_float(tf_b_taxa.value)
        repasse = _to_float(tf_b_repasse.value)
        if _bairro_id["v"] is None:
            id_bairro = database.bairro_inserir(nome, taxa, repasse)
        else:
            id_bairro = _bairro_id["v"]
            database.bairro_atualizar(
                id_bairro,
                nome_bairro=nome,
                taxa_cobrada=taxa,
                repasse_entregador=repasse,
            )
        database.log_registrar(
            acao="ALTERAR_BAIRRO",
            tabela="cad_bairros",
            id_registro=id_bairro,
            descricao=f"Bairro salvo — {nome}: "
                      f"Taxa R$ {taxa:.2f} | "
                      f"Repasse R$ {repasse:.2f}",
        )
        _limpar_bairro()
        _refresh_bairros()
        page.update()

    def _cancelar_bairro(e):
        _limpar_bairro()
        page.update()

    _refresh_bairros()

    tab_bairros = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    lbl_b_titulo,
                    tf_b_nome,
                    ft.Row([tf_b_taxa, tf_b_repasse], spacing=12),
                    txt_b_erro,
                    ft.Row([
                        ft.ElevatedButton("Salvar",   icon=ft.Icons.SAVE, on_click=_salvar_bairro),
                        ft.TextButton("Cancelar", on_click=_cancelar_bairro),
                    ]),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Bairros Cadastrados", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_bairros,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 3 — PLATAFORMAS
    # ══════════════════════════════════════════

    _DIAS_REPASSE = ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]

    def _card_plataforma(plat: dict) -> ft.Card:
        pid  = plat["id"]
        nome = plat["nome"]

        tf_pl_comissao = ft.TextField(
            label="Comissão (%)",
            value=f"{plat['comissao_pct']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        tf_pl_taxa_tr = ft.TextField(
            label="Taxa Transação (%)",
            value=f"{plat['taxa_transacao_pct']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        tf_pl_subsidio = ft.TextField(
            label="Subsídio (R$)",
            value=f"{plat['subsidio']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER, expand=True,
        )
        dd_pl_dia = ft.Dropdown(
            label="Dia de Repasse",
            value=plat["dia_repasse"] or None,
            options=[ft.dropdown.Option(d) for d in _DIAS_REPASSE],
            expand=True,
        )
        sw_pl_ativo = ft.Switch(label="Ativo", value=bool(plat["ativo"]))
        txt_pl_ok   = ft.Text("", color=ft.Colors.GREEN_400, size=12)

        def _salvar_plat(e):
            database.plataforma_atualizar(
                pid,
                comissao_pct=      _to_float(tf_pl_comissao.value),
                taxa_transacao_pct=_to_float(tf_pl_taxa_tr.value),
                subsidio=          _to_float(tf_pl_subsidio.value),
                dia_repasse=       dd_pl_dia.value,
                ativo=             int(sw_pl_ativo.value),
            )
            database.log_registrar(
                acao="ALTERAR_PLATAFORMA",
                tabela="cad_plataformas",
                id_registro=pid,
                descricao=f"Plataforma atualizada — {nome}",
            )
            txt_pl_ok.value = "Salvo!"
            page.update()

        return ft.Card(content=ft.Container(
            padding=ft.Padding.all(16),
            content=ft.Column(spacing=12, controls=[
                ft.Row([
                    ft.Text(nome, size=15, weight=ft.FontWeight.BOLD, expand=True),
                    sw_pl_ativo,
                ]),
                ft.Row([tf_pl_comissao, tf_pl_taxa_tr, tf_pl_subsidio], spacing=12),
                dd_pl_dia,
                ft.Row([
                    ft.ElevatedButton("Salvar", icon=ft.Icons.SAVE, on_click=_salvar_plat),
                    txt_pl_ok,
                ]),
            ]),
        ))

    plataformas_db = database.plataforma_listar(apenas_ativas=False)

    tab_plataformas = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[_card_plataforma(dict(p)) for p in plataformas_db],
    )

    # ══════════════════════════════════════════
    #  ABA 4 — MÉTODOS DE PAGAMENTO
    # ══════════════════════════════════════════

    tf_m_nome  = ft.TextField(label="Nome", expand=True)
    dd_m_tipo  = ft.Dropdown(
        label="Tipo", width=200,
        options=[
            ft.dropdown.Option("FISICO"),
            ft.dropdown.Option("PLATAFORMA"),
            ft.dropdown.Option("BENEFICIO"),
            ft.dropdown.Option("CORTESIA"),
        ],
    )
    txt_m_erro = ft.Text("", color=ft.Colors.RED_400, size=12)

    tabela_metodos = ft.Column(spacing=0)

    def _refresh_metodos():
        rows = database.metodo_pag_listar()
        linhas = []
        for m in rows:
            def _on_excluir_metodo(mid):
                def handler(e):
                    def _excluir():
                        database.metodo_pag_excluir(mid)
                        _refresh_metodos()
                        page.update()
                    _confirmar_exclusao(page, "este método de pagamento", _excluir)
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(m["nome"])),
                ft.DataCell(ft.Text(m["tipo"])),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Excluir método",
                    on_click=_on_excluir_metodo(m["id"]),
                )),
            ]))

        tabela_metodos.controls.clear()
        if not linhas:
            tabela_metodos.controls.append(
                ft.Text("Nenhum método cadastrado.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_metodos.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Nome")),
                            ft.DataColumn(ft.Text("Tipo")),
                            ft.DataColumn(ft.Text("")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _salvar_metodo(e):
        txt_m_erro.value = ""
        nome = tf_m_nome.value.strip()
        if not nome:
            txt_m_erro.value = "Nome é obrigatório."
            page.update()
            return
        if not dd_m_tipo.value:
            txt_m_erro.value = "Selecione o tipo."
            page.update()
            return
        database.metodo_pag_inserir(nome, dd_m_tipo.value)
        tf_m_nome.value = ""
        dd_m_tipo.value = None
        _refresh_metodos()
        page.update()

    _refresh_metodos()

    tab_metodos = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    ft.Text("Adicionar Método de Pagamento", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([tf_m_nome, dd_m_tipo], spacing=12),
                    txt_m_erro,
                    ft.ElevatedButton("Adicionar", icon=ft.Icons.ADD, on_click=_salvar_metodo),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Métodos Cadastrados", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_metodos,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 5 — CATEGORIAS EXTRAS
    # ══════════════════════════════════════════

    tf_cat_desc   = ft.TextField(label="Descrição", expand=True)
    dd_cat_fluxo  = ft.Dropdown(
        label="Fluxo", width=160,
        options=[ft.dropdown.Option("ENTRADA"), ft.dropdown.Option("SAIDA")],
    )
    cb_cat_func   = ft.Checkbox(label="Usa Funcionário", value=False)
    txt_cat_erro  = ft.Text("", color=ft.Colors.RED_400, size=12)

    tabela_cats = ft.Column(spacing=0)

    def _refresh_cats():
        rows = database.categoria_extra_listar()
        linhas = []
        for c in rows:
            cor_fluxo = ft.Colors.GREEN_400 if c["fluxo"] == "ENTRADA" else ft.Colors.RED_400

            def _on_excluir_cat(cid):
                def handler(e):
                    def _excluir():
                        database.categoria_extra_excluir(cid)
                        _refresh_cats()
                        page.update()
                    _confirmar_exclusao(page, "esta categoria", _excluir)
                return handler

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["descricao"])),
                ft.DataCell(ft.Text(c["fluxo"], color=cor_fluxo)),
                ft.DataCell(ft.Text("Sim" if c["usa_funcionario"] else "Não")),
                ft.DataCell(ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ft.Colors.RED_400,
                    tooltip="Excluir categoria",
                    on_click=_on_excluir_cat(c["id"]),
                )),
            ]))

        tabela_cats.controls.clear()
        if not linhas:
            tabela_cats.controls.append(
                ft.Text("Nenhuma categoria cadastrada.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            tabela_cats.controls.append(
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=[
                    ft.DataTable(
                        column_spacing=16,
                        columns=[
                            ft.DataColumn(ft.Text("Descrição")),
                            ft.DataColumn(ft.Text("Fluxo")),
                            ft.DataColumn(ft.Text("Usa Func.")),
                            ft.DataColumn(ft.Text("")),
                        ],
                        rows=linhas,
                    )
                ])
            )

    def _salvar_cat(e):
        txt_cat_erro.value = ""
        desc = tf_cat_desc.value.strip()
        if not desc:
            txt_cat_erro.value = "Descrição é obrigatória."
            page.update()
            return
        if not dd_cat_fluxo.value:
            txt_cat_erro.value = "Selecione o fluxo."
            page.update()
            return
        database.categoria_extra_inserir(desc, dd_cat_fluxo.value, cb_cat_func.value)
        tf_cat_desc.value  = ""
        dd_cat_fluxo.value = None
        cb_cat_func.value  = False
        _refresh_cats()
        page.update()

    _refresh_cats()

    tab_categorias = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    ft.Text("Adicionar Categoria Extra", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([tf_cat_desc, dd_cat_fluxo], spacing=12),
                    cb_cat_func,
                    txt_cat_erro,
                    ft.ElevatedButton("Adicionar", icon=ft.Icons.ADD, on_click=_salvar_cat),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Categorias Cadastradas", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_cats,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 6 — CONFIGURAÇÕES GERAIS
    # ══════════════════════════════════════════

    tf_cfg_loja   = ft.TextField(
        label="Nome da Loja",
        value=database.config_obter("nome_loja", "Minha Loja"),
        expand=True,
    )
    tf_cfg_diaria = ft.TextField(
        label="Diária Padrão Entregadores (R$)",
        value=database.config_obter("diaria_padrao_entregador", "40.00"),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=260,
        hint_text="Padrão ao cadastrar novo entregador",
    )
    tf_cfg_limite = ft.TextField(
        label="Limite de divergência de caixa (R$)",
        value=database.config_obter("limite_divergencia_caixa", "5.00"),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=280,
        hint_text="Diferença acima deste valor gera alerta",
    )
    sw_fechamento_cego = ft.Switch(
        label="Fechamento cego",
        value=database.config_obter("fechamento_cego", "0") == "1",
    )
    txt_cfg_ok = ft.Text("", color=ft.Colors.GREEN_400, size=13)

    def _salvar_cfg(e):
        nome_loja = tf_cfg_loja.value.strip()
        diaria    = tf_cfg_diaria.value.strip() or "40.00"
        limite    = tf_cfg_limite.value.strip() or "5.00"
        if nome_loja:
            database.config_salvar("nome_loja", nome_loja)
        database.config_salvar("diaria_padrao_entregador", diaria)
        database.config_salvar("limite_divergencia_caixa", limite)
        database.config_salvar("fechamento_cego", "1" if sw_fechamento_cego.value else "0")
        database.log_registrar(
            acao="ALTERAR_CONFIGURACAO",
            tabela="cad_configuracoes",
            descricao="Configurações gerais atualizadas",
        )
        txt_cfg_ok.value = "Configurações salvas!"
        page.update()

    tab_config = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=16, controls=[
                    ft.Text("Configurações Gerais", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row([tf_cfg_loja], spacing=12),
                    ft.Row([tf_cfg_diaria], spacing=12),
                    ft.Text(
                        "A diária padrão é usada como valor inicial ao cadastrar novos entregadores.",
                        size=12, color=ft.Colors.GREY_500, italic=True,
                    ),
                    ft.Row([tf_cfg_limite], spacing=12),
                    ft.Text(
                        "Divergências de caixa acima deste valor exibem um alerta no fechamento.",
                        size=12, color=ft.Colors.GREY_500, italic=True,
                    ),
                    sw_fechamento_cego,
                    ft.Text(
                        "Quando ativo, o operador não vê o saldo teórico na hora de fechar o caixa. "
                        "Ele informa o valor contado e o sistema revela a diferença só após confirmar.",
                        size=12, italic=True, color=ft.Colors.GREY_500,
                    ),
                    txt_cfg_ok,
                    ft.ElevatedButton(
                        "Salvar Configurações",
                        icon=ft.Icons.SAVE,
                        on_click=_salvar_cfg,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE,
                        ),
                    ),
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  ABA 7 — AUDITORIA
    # ══════════════════════════════════════════

    _aud_hoje  = date.today()
    _aud_ini_v = (_aud_hoje - timedelta(days=7)).strftime("%d/%m/%Y")
    _aud_fim_v = _aud_hoje.strftime("%d/%m/%Y")

    tf_aud_ini = ft.TextField(
        label="Data início", value=_aud_ini_v, width=140,
        hint_text="DD/MM/AAAA", text_align=ft.TextAlign.CENTER,
    )
    tf_aud_fim = ft.TextField(
        label="Data fim", value=_aud_fim_v, width=140,
        hint_text="DD/MM/AAAA", text_align=ft.TextAlign.CENTER,
    )

    _ACOES_AUDIT = [
        "EXCLUIR_PEDIDO", "EDITAR_PEDIDO",
        "EXCLUIR_MOVIMENTACAO",
        "ENTRADA_ESTOQUE", "SAIDA_ESTOQUE", "EXCLUIR_ESTOQUE_MOV",
        "QUITAR_FIADO", "EXCLUIR_FIADO",
        "PAGAMENTO_ENTREGADOR", "PAGAMENTO_FUNCIONARIO",
        "ALTERAR_BAIRRO", "ALTERAR_PLATAFORMA",
        "ALTERAR_PESSOA", "ALTERAR_CONFIGURACAO",
        "LOGIN",
    ]

    dd_aud_acao = ft.Dropdown(
        label="Ação",
        width=260,
        options=[ft.dropdown.Option(key="", text="Todas")] + [
            ft.dropdown.Option(a) for a in _ACOES_AUDIT
        ],
        value="",
    )

    tabela_aud = ft.Column(spacing=0, controls=[
        ft.Text(
            "Use os filtros acima e clique em Filtrar.",
            italic=True, color=ft.Colors.GREY_500,
        ),
    ])
    _logs_cache: list = []

    def _iso_aud(data_br: str) -> str:
        try:
            d, m, a = data_br.strip().split("/")
            return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
        except Exception:
            return date.today().isoformat()

    def _chip_acao(acao: str) -> ft.Container:
        if acao.startswith("EXCLUIR_"):
            cor = ft.Colors.RED_700
        elif acao == "EDITAR_PEDIDO":
            cor = ft.Colors.ORANGE_700
        elif acao in ("PAGAMENTO_ENTREGADOR", "PAGAMENTO_FUNCIONARIO", "QUITAR_FIADO"):
            cor = ft.Colors.GREEN_700
        elif acao == "ENTRADA_ESTOQUE":
            cor = ft.Colors.BLUE_700
        elif acao == "SAIDA_ESTOQUE":
            cor = ft.Colors.ORANGE_700
        elif acao.startswith("ALTERAR_"):
            cor = ft.Colors.GREY_700
        elif acao == "LOGIN":
            cor = ft.Colors.PURPLE_700
        else:
            cor = ft.Colors.GREY_700
        return ft.Container(
            content=ft.Text(acao, size=10, color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD),
            bgcolor=cor,
            border_radius=4,
            padding=ft.Padding(left=6, right=6, top=3, bottom=3),
        )

    def _filtrar_aud(e=None):
        ini  = _iso_aud(tf_aud_ini.value)
        fim  = _iso_aud(tf_aud_fim.value)
        acao = dd_aud_acao.value or None

        logs = database.log_listar(data_inicio=ini, data_fim=fim, acao=acao)
        _logs_cache.clear()
        _logs_cache.extend([dict(lg) for lg in logs])

        tabela_aud.controls.clear()

        if not logs:
            tabela_aud.controls.append(ft.Text(
                "Nenhum log encontrado para os filtros selecionados.",
                italic=True, color=ft.Colors.GREY_500,
            ))
            page.update()
            return

        tabela_aud.controls.append(ft.Row(
            spacing=0,
            controls=[
                ft.Container(width=145, content=ft.Text(
                    "Data/Hora", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=200, content=ft.Text(
                    "Ação", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(expand=True, content=ft.Text(
                    "Descrição", size=11, weight=ft.FontWeight.BOLD)),
                ft.Container(width=100, content=ft.Text(
                    "Usuário", size=11, weight=ft.FontWeight.BOLD)),
            ],
        ))
        tabela_aud.controls.append(ft.Divider(height=1))

        for lg in logs:
            tabela_aud.controls.append(ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=145, content=ft.Text(
                        (lg["data_hora"] or "")[:16], size=12,
                        color=ft.Colors.GREY_500)),
                    ft.Container(width=200,
                                 padding=ft.Padding(left=0, right=4, top=2, bottom=2),
                                 content=_chip_acao(lg["acao"])),
                    ft.Container(expand=True, content=ft.Text(
                        lg["descricao"], size=12)),
                    ft.Container(width=100, content=ft.Text(
                        lg["usuario"] or "—", size=12, color=ft.Colors.GREY_500)),
                ],
            ))
            tabela_aud.controls.append(ft.Divider(
                height=1, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
            ))

        page.update()

    def _exportar_csv(e):
        if not _logs_cache:
            _snack(page, "Nenhum log para exportar. Clique em Filtrar primeiro.",
                   ft.Colors.ORANGE_700)
            return
        exports_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "exports"
        )
        os.makedirs(exports_dir, exist_ok=True)
        ini_str = tf_aud_ini.value.replace("/", "")
        fim_str = tf_aud_fim.value.replace("/", "")
        caminho = os.path.join(exports_dir, f"auditoria_{ini_str}_{fim_str}.csv")
        with open(caminho, "w", newline="", encoding="utf-8-sig") as fcsv:
            writer = csv.writer(fcsv)
            writer.writerow([
                "Data/Hora", "Ação", "Tabela", "ID Registro",
                "Descrição", "Valor Antes", "Valor Depois", "Usuário",
            ])
            for lg in _logs_cache:
                writer.writerow([
                    lg["data_hora"],
                    lg["acao"],
                    lg["tabela"] or "",
                    lg["id_registro"] or "",
                    lg["descricao"],
                    lg["valor_antes"] or "",
                    lg["valor_depois"] or "",
                    lg["usuario"] or "",
                ])
        _snack(page, f"CSV exportado: {os.path.basename(caminho)}")

    def _limpar_logs_antigos(e):
        tf_dias = ft.TextField(
            label="Dias a manter", value="90", width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _executar(ev):
            dlg.open = False
            try:
                dias = int(tf_dias.value or "90")
            except ValueError:
                dias = 90
            removidos = database.log_limpar_antigos(dias)
            page.update()
            _snack(page, f"{removidos} log(s) removido(s) com mais de {dias} dias.")
            _filtrar_aud()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Remover logs antigos"),
            content=ft.Column(tight=True, spacing=8, controls=[
                ft.Text("Remover logs com mais de quantos dias?", size=13),
                tf_dias,
            ]),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: _fechar(e, dlg, page)),
                ft.ElevatedButton(
                    "Confirmar",
                    ft.Icons.DELETE_SWEEP,
                    on_click=_executar,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    tab_auditoria = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=12, controls=[
                    ft.Text("Filtros", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row([tf_aud_ini, tf_aud_fim, dd_aud_acao], spacing=12, wrap=True),
                    ft.Row([
                        ft.ElevatedButton(
                            "Filtrar",
                            ft.Icons.SEARCH,
                            on_click=_filtrar_aud,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.TEAL_600, color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.ElevatedButton(
                            "Exportar CSV",
                            ft.Icons.DOWNLOAD,
                            on_click=_exportar_csv,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.TextButton(
                            "Limpar logs antigos",
                            icon=ft.Icons.DELETE_SWEEP,
                            on_click=_limpar_logs_antigos,
                            style=ft.ButtonStyle(color=ft.Colors.RED_400),
                        ),
                    ], spacing=8),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Registros de Auditoria", size=14,
                            weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    tabela_aud,
                ]),
            )),
        ],
    )

    # ══════════════════════════════════════════
    #  TABS
    # ══════════════════════════════════════════

    def _wrap(content: ft.Control) -> ft.Container:
        return ft.Container(content=content, padding=ft.Padding.all(16))

    tab_bar = ft.TabBar(
        scrollable=True,
        tabs=[
            ft.Tab(label="Pessoas",       icon=ft.Icons.PEOPLE),
            ft.Tab(label="Bairros",        icon=ft.Icons.MAP),
            ft.Tab(label="Plataformas",    icon=ft.Icons.STORE),
            ft.Tab(label="Pagamentos",     icon=ft.Icons.PAYMENT),
            ft.Tab(label="Categorias",     icon=ft.Icons.CATEGORY),
            ft.Tab(label="Configurações",  icon=ft.Icons.SETTINGS),
            ft.Tab(label="Auditoria",      icon=ft.Icons.SECURITY),
        ],
    )

    tab_view = ft.TabBarView(
        controls=[
            _wrap(tab_pessoas),
            _wrap(tab_bairros),
            _wrap(tab_plataformas),
            _wrap(tab_metodos),
            _wrap(tab_categorias),
            _wrap(tab_config),
            _wrap(tab_auditoria),
        ],
        expand=True,
    )

    return ft.Tabs(
        content=ft.Column([tab_bar, tab_view], expand=True),
        length=7,
        selected_index=0,
        expand=True,
    )
