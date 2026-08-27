"""
views/extras.py — Movimentações de Caixa (Entradas, Saídas, Neutros, Quitação de Boletos e Relatórios)

Reestruturação completa da Fase 3:
- Seletor de fluxo superior [SAÍDA] / [ENTRADA] / [PAGAR BOLETO] / [RELATÓRIOS & GASTOS].
- Subtipos canônicos filtrados por ativo=1 e permissão de perfil (sessao_tem_acesso).
- Aba de Relatórios & Gastos consolidada para gerência com filtros por período, KPIs, tabelas de resumo e exportação Excel/PDF.
- Campos dinâmicos: Funcionário/Entregador (usa_funcionario=1), Fornecedor (usa_fornecedor=1), Método de Pagamento.
- Quitação rápida de boletos e duplicatas integrada na operação de caixa.
- Gravação estrita do fluxo da categoria (categoria['fluxo']) preservando NEUTRO.
- Formatação de valor 150 -> 150,00 (centavos por último).
- Rastreabilidade bidirecional e estorno atômico.
"""

import flet as ft
from datetime import date, datetime, timedelta
import database
from relatorios import excel_gerador, pdf_gerador


# ── Utilitários ───────────────────────────────────────────────────────────────

def _to_float(valor: str) -> float:
    try:
        return float((valor or "0").replace(",", ".").strip())
    except ValueError:
        return 0.0


def _data_br_para_iso(data_br: str) -> str:
    try:
        d, m, a = data_br.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


def _data_iso_para_br(data_iso: str) -> str:
    try:
        a, m, d = data_iso.strip().split("-")
        return f"{d}/{m}/{a}"
    except Exception:
        return date.today().strftime("%d/%m/%Y")


_SUFIXO_CONSUMO = "(desconto 20% aplicado no holerite)"


def _extrair_obs_consumo(obs: str) -> str:
    """Remove o sufixo de desconto do Consumo, se presente."""
    obs = (obs or "").strip()
    if obs == _SUFIXO_CONSUMO:
        return ""
    sufixo_com_espaco = f" {_SUFIXO_CONSUMO}"
    if obs.endswith(sufixo_com_espaco):
        return obs[: -len(sufixo_com_espaco)].strip()
    return obs


def _montar_obs_consumo(obs: str) -> str:
    """Acrescenta o sufixo de desconto ao texto-base do Consumo (idempotente)."""
    obs = (obs or "").strip()
    return f"{obs} {_SUFIXO_CONSUMO}" if obs else _SUFIXO_CONSUMO


def _fechar_dlg(dlg, page):
    dlg.open = False
    page.update()


def _confirmar_exclusao(page: ft.Page, descricao: str, on_confirmar) -> None:
    """Abre um AlertDialog pedindo confirmação antes de excluir."""
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar exclusão"),
        content=ft.Text(
            f"Deseja excluir {descricao}? Esta ação não pode ser desfeita."
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _fechar_dlg(dlg, page)),
            ft.ElevatedButton(
                "Excluir",
                on_click=lambda e: (_fechar_dlg(dlg, page), on_confirmar()),
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


# ── Modal de Cadastro Rápido de Fornecedor ────────────────────────────────────

def _dialogo_novo_fornecedor(page: ft.Page, on_salvo, tipo_sugerido: str = "PRODUTO"):
    """Modal rápido para cadastrar um novo fornecedor sem sair do caixa."""
    tf_nome = ft.TextField(label="Nome do Fornecedor / Razão Social *", autofocus=True, expand=True)
    tf_telefone = ft.TextField(label="Telefone / WhatsApp", width=200)
    dd_tipo = ft.Dropdown(
        label="Tipo *",
        width=180,
        value=tipo_sugerido,
        options=[
            ft.dropdown.Option("PRODUTO", "Produto / Insumos"),
            ft.dropdown.Option("SERVICO", "Prestador de Serviço"),
            ft.dropdown.Option("OUTRO", "Outro"),
        ],
    )
    txt_erro_forn = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _salvar_forn(e):
        nome = (tf_nome.value or "").strip()
        if not nome:
            txt_erro_forn.value = "Informe o nome do fornecedor."
            page.update()
            return
        try:
            id_novo = database.fornecedor_inserir(
                nome=nome,
                telefone=tf_telefone.value.strip() or None,
            )
            # Atualiza o tipo se diferente de PRODUTO
            tipo_sel = dd_tipo.value or "PRODUTO"
            if tipo_sel != "PRODUTO":
                database.fornecedor_atualizar(id_novo, tipo=tipo_sel)

            _fechar_dlg(dlg, page)
            on_salvo(id_novo, nome)
        except Exception as ex:
            txt_erro_forn.value = f"Erro ao salvar: {ex}"
            page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Cadastrar Novo Fornecedor"),
        content=ft.Column(
            tight=True,
            width=500,
            spacing=12,
            controls=[
                ft.Text("Preencha os dados básicos do fornecedor:", size=13, color=ft.Colors.GREY_400),
                tf_nome,
                ft.Row([tf_telefone, dd_tipo], spacing=10),
                txt_erro_forn,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _fechar_dlg(dlg, page)),
            ft.ElevatedButton(
                "Salvar Fornecedor",
                on_click=_salvar_forn,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


# ── Modal de Quitação de Parcela de Boleto ─────────────────────────────────────

def _dialogo_quitar_parcela(page: ft.Page, parcela: dict, on_sucesso) -> None:
    """Modal para confirmação de pagamento de parcela de boleto/conta."""
    hoje_str = date.today().strftime("%d/%m/%Y")
    tf_data_pag = ft.TextField(
        label="Data do Pagamento",
        value=hoje_str,
        width=150,
        text_align=ft.TextAlign.CENTER,
    )
    tf_valor_pag = ft.TextField(
        label="Valor Pago (R$) *",
        value=f"{parcela['valor']:.2f}".replace(".", ","),
        width=170,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    metodos = database.metodo_pag_listar()
    dd_metodo_pag = ft.Dropdown(
        label="Método de Pagamento",
        width=200,
        value="Dinheiro",
        options=[ft.dropdown.Option(m["nome"]) for m in metodos],
    )
    txt_erro_pag = ft.Text("", color=ft.Colors.RED_400, size=12)

    def _confirmar(e):
        data_iso = _data_br_para_iso(tf_data_pag.value)
        val = _to_float(tf_valor_pag.value)
        if val <= 0:
            txt_erro_pag.value = "Informe um valor válido."
            page.update()
            return
        metodo = dd_metodo_pag.value or "Dinheiro"

        try:
            ok = database.boleto_quitar_parcela(
                id_parcela=parcela["id"],
                data_pago=data_iso,
                metodo=metodo,
                valor_pago=val,
                registrar_caixa=True,
            )
            if ok:
                _fechar_dlg(dlg, page)
                on_sucesso(f"Parcela #{parcela['id']} ({parcela['nome_fornecedor']}) quitada com sucesso!")
            else:
                txt_erro_pag.value = "Esta parcela já consta como paga ou não existe mais."
                page.update()
        except Exception as ex:
            txt_erro_pag.value = f"Erro ao quitar: {ex}"
            page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"Quitar Boleto — {parcela['nome_fornecedor']}"),
        content=ft.Column(
            tight=True,
            width=560,
            spacing=12,
            controls=[
                ft.Text(
                    f"Descrição: {parcela['descricao']} | Parcela {parcela['num_parcela']}/{parcela['num_parcelas']} "
                    f"(Vencimento: {_data_iso_para_br(parcela['vencimento'])})",
                    size=13,
                    color=ft.Colors.GREY_300,
                ),
                ft.Row([tf_data_pag, tf_valor_pag, dd_metodo_pag], spacing=10, wrap=True),
                ft.Text(
                    "Esta ação lançará automaticamente uma saída no caixa vinculada à categoria 'Compra Fornecedor / Insumos'.",
                    size=11,
                    italic=True,
                    color=ft.Colors.GREY_500,
                ),
                txt_erro_pag,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: _fechar_dlg(dlg, page)),
            ft.ElevatedButton(
                "Confirmar Quitação",
                on_click=_confirmar,
                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


# ── View Principal ────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:
    hoje_obj = date.today()
    hoje_br  = hoje_obj.strftime("%d/%m/%Y")

    # ── 1. Dados e Permissões da Sessão ───────────────────────────────────────
    categorias_todas = [dict(c) for c in database.categoria_extra_listar()]
    metodos_db       = [dict(m) for m in database.metodo_pag_listar()]
    funcionarios_db  = [dict(p) for p in database.pessoa_listar(tipo="INTERNO", apenas_ativos=True)]
    entregadores_db  = [dict(p) for p in database.pessoa_listar(tipo="ENTREGADOR", apenas_ativos=True)]
    pessoas_todas    = [dict(p) for p in database.pessoa_listar(apenas_ativos=True)]
    fornecedores_db  = [dict(f) for f in database.fornecedor_listar(apenas_ativos=True)]

    # Permissão para visualizar relatórios consolidados de gastos (Restrito a Gerente/Admin)
    pode_ver_relatorios = database.sessao_tem_acesso("GERENTE")

    # Filtra apenas categorias ativas E com permissão mínima da sessão
    categorias_validas = [
        c for c in categorias_todas
        if c["ativo"] == 1 and database.sessao_tem_acesso(c["min_perfil"])
    ]
    cat_map = {r["id"]: r for r in categorias_validas}

    # Separação de categorias por agrupamento de fluxo
    cats_saida = [c for c in categorias_validas if c["fluxo"] in ("SAIDA", "NEUTRO")]
    cats_entrada = [c for c in categorias_validas if c["fluxo"] == "ENTRADA"]

    # ── 2. Estado da Tela ─────────────────────────────────────────────────────
    _estado = {
        "fluxo_ui": "SAIDA",     # 'SAIDA' | 'ENTRADA' | 'BOLETO' | 'RELATORIOS'
        "cat_selecionada": None, # dict da categoria ativa
        "editando_id": None,     # ID da movimentação em edição
    }

    # ── 3. Controles do Topo (Data e Seletor de Fluxo) ────────────────────────
    tf_data = ft.TextField(
        label="Data",
        value=hoje_br,
        width=135,
        text_align=ft.TextAlign.CENTER,
        hint_text="DD/MM/AAAA",
    )

    def _on_date_picked(e):
        if e.control.value:
            tf_data.value = e.control.value.strftime("%d/%m/%Y")
            _atualizar_tudo()
            page.update()

    date_picker = ft.DatePicker(on_change=_on_date_picked)
    page.overlay.append(date_picker)

    btn_calendario = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH,
        tooltip="Selecionar data",
        on_click=lambda e: (setattr(date_picker, "open", True), page.update()),
    )

    btn_refresh = ft.IconButton(
        icon=ft.Icons.REFRESH,
        tooltip="Atualizar dados",
        on_click=lambda e: (_atualizar_tudo(), page.update()),
    )

    # Botões do Seletor de Fluxo Superior
    btn_aba_saida = ft.ElevatedButton(
        "Saídas / Despesas",
        icon=ft.Icons.ARROW_UPWARD,
        style=ft.ButtonStyle(bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE),
    )
    btn_aba_entrada = ft.ElevatedButton(
        "Entradas / Troco",
        icon=ft.Icons.ARROW_DOWNWARD,
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_800, color=ft.Colors.GREY_300),
    )
    btn_aba_boletos = ft.ElevatedButton(
        "Pagar Boletos",
        icon=ft.Icons.RECEIPT_LONG,
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_800, color=ft.Colors.GREY_300),
    )
    btn_aba_relatorios = ft.ElevatedButton(
        "Relatórios & Gastos",
        icon=ft.Icons.BAR_CHART,
        visible=pode_ver_relatorios,
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_800, color=ft.Colors.GREY_300),
    )

    # ── 4. Controles do Formulário de Lançamento ──────────────────────────────
    lbl_titulo_form = ft.Text("Nova Saída de Caixa", size=18, weight=ft.FontWeight.BOLD)

    dd_subtipo = ft.Dropdown(
        label="Subtipo / Categoria *",
        expand=True,
    )

    def _opts_pessoa(tipo_filtro):
        if tipo_filtro == "ENTREGADOR":
            src = entregadores_db
            return [ft.dropdown.Option(key=str(r["id"]), text=r["nome"]) for r in src]
        elif tipo_filtro == "INTERNO":
            src = funcionarios_db
            return [ft.dropdown.Option(key=str(r["id"]), text=r["nome"]) for r in src]
        src = sorted(pessoas_todas, key=lambda r: r["nome"])
        return [
            ft.dropdown.Option(
                key=str(r["id"]),
                text=r["nome"] if r["tipo"] == "INTERNO" else f"{r['nome']} ({r['tipo'].lower()})",
            )
            for r in src
        ]

    dd_pessoa = ft.Dropdown(
        label="Pessoa / Funcionário *",
        expand=True,
    )
    linha_pessoa = ft.Row([dd_pessoa], visible=False)

    def _carregar_opcoes_fornecedor(subtipo_codigo=""):
        forns_ordenados = list(fornecedores_db)
        if subtipo_codigo == "manutencao":
            forns_ordenados.sort(key=lambda f: (0 if (f.get("tipo") or "").upper() == "SERVICO" else 1, f["nome"]))
        else:
            forns_ordenados.sort(key=lambda f: f["nome"])

        opts = []
        for f in forns_ordenados:
            badge = f" [{f['tipo']}]" if f.get("tipo") else ""
            opts.append(ft.dropdown.Option(key=str(f["id"]), text=f"{f['nome']}{badge}"))
        return opts

    dd_fornecedor = ft.Dropdown(
        label="Fornecedor / Prestador *",
        expand=True,
    )

    def _ao_cadastrar_novo_fornecedor(id_novo, nome_novo):
        nonlocal fornecedores_db
        fornecedores_db = [dict(f) for f in database.fornecedor_listar(apenas_ativos=True)]
        dd_fornecedor.options = _carregar_opcoes_fornecedor(_estado["cat_selecionada"].get("codigo") if _estado["cat_selecionada"] else "")
        dd_fornecedor.value = str(id_novo)
        page.overlay.append(ft.SnackBar(
            content=ft.Text(f"Fornecedor '{nome_novo}' cadastrado e selecionado!"),
            bgcolor=ft.Colors.GREEN_700,
            open=True,
        ))
        page.update()

    def _abrir_novo_fornecedor(e):
        cod = _estado["cat_selecionada"].get("codigo") if _estado["cat_selecionada"] else ""
        sugestao = "SERVICO" if cod == "manutencao" else "PRODUTO"
        _dialogo_novo_fornecedor(page, _ao_cadastrar_novo_fornecedor, tipo_sugerido=sugestao)

    btn_novo_forn = ft.IconButton(
        icon=ft.Icons.PERSON_ADD_ALT_1,
        tooltip="Cadastrar novo fornecedor",
        on_click=_abrir_novo_fornecedor,
    )
    linha_fornecedor = ft.Row([dd_fornecedor, btn_novo_forn], visible=False)

    dd_metodo = ft.Dropdown(
        label="Método de Pagamento *",
        options=[ft.dropdown.Option(r["nome"]) for r in metodos_db],
        value="Dinheiro",
        expand=True,
    )
    linha_metodo = ft.Row([dd_metodo], visible=True)

    tf_valor = ft.TextField(
        label="Valor (R$) *",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )

    def _formatar_campo_valor(e=None):
        v = _to_float(tf_valor.value)
        if v > 0:
            tf_valor.value = f"{v:.2f}".replace(".", ",")
            page.update()

    tf_valor.on_blur   = _formatar_campo_valor
    tf_valor.on_submit = _formatar_campo_valor

    tf_obs = ft.TextField(
        label="Observações / Detalhes",
        multiline=True,
        min_lines=2,
        max_lines=3,
        expand=True,
    )

    txt_erro = ft.Text("", color=ft.Colors.RED_400, size=13)

    # ── 5. Lógica de Subtipos e Campos Dinâmicos ──────────────────────────────

    def _atualizar_opcoes_subtipo():
        dd_subtipo.value = None
        if _estado["fluxo_ui"] == "SAIDA":
            dd_subtipo.options = [
                ft.dropdown.Option(key=str(c["id"]), text=c["descricao"])
                for c in cats_saida
            ]
        elif _estado["fluxo_ui"] == "ENTRADA":
            dd_subtipo.options = [
                ft.dropdown.Option(key=str(c["id"]), text=c["descricao"])
                for c in cats_entrada
            ]
        _ajustar_campos_por_subtipo(None)

    def _ajustar_campos_por_subtipo(cat_dict):
        _estado["cat_selecionada"] = cat_dict
        if not cat_dict:
            linha_pessoa.visible = False
            linha_fornecedor.visible = False
            linha_metodo.visible = False
            page.update()
            return

        cod = cat_dict.get("codigo") or ""
        usa_func = cat_dict.get("usa_funcionario", 0) == 1
        usa_forn = cat_dict.get("usa_fornecedor", 0) == 1

        # 1. Campo Pessoa
        if usa_func:
            if cod in ("corrida_extra", "reentrega"):
                dd_pessoa.label = "Entregador *"
                dd_pessoa.options = _opts_pessoa("ENTREGADOR")
            else:
                dd_pessoa.label = "Funcionário *"
                dd_pessoa.options = _opts_pessoa("INTERNO")
            linha_pessoa.visible = True
        else:
            linha_pessoa.visible = False
            dd_pessoa.value = None

        # 2. Campo Fornecedor
        if usa_forn:
            dd_fornecedor.label = "Prestador de Serviço *" if cod == "manutencao" else "Fornecedor / Insumos *"
            dd_fornecedor.options = _carregar_opcoes_fornecedor(cod)
            linha_fornecedor.visible = True
        else:
            linha_fornecedor.visible = False
            dd_fornecedor.value = None

        # 3. Campo Método de Pagamento
        if cod in ("consumo", "corrida_extra", "reentrega"):
            linha_metodo.visible = False
            dd_metodo.value = None
        else:
            linha_metodo.visible = True
            if not dd_metodo.value:
                dd_metodo.value = "Dinheiro"

        txt_erro.value = ""
        page.update()

    def _on_subtipo_select(e):
        if dd_subtipo.value:
            cat = cat_map.get(int(dd_subtipo.value))
            _ajustar_campos_por_subtipo(cat)
        else:
            _ajustar_campos_por_subtipo(None)

    dd_subtipo.on_select = _on_subtipo_select

    # ── 6. Alternância de Abas Superiores ─────────────────────────────────────

    def _trocar_aba(aba: str):
        _estado["fluxo_ui"] = aba
        _limpar_form()

        btn_aba_saida.style.bgcolor = ft.Colors.RED_800 if aba == "SAIDA" else ft.Colors.GREY_800
        btn_aba_saida.style.color = ft.Colors.WHITE if aba == "SAIDA" else ft.Colors.GREY_300

        btn_aba_entrada.style.bgcolor = ft.Colors.GREEN_800 if aba == "ENTRADA" else ft.Colors.GREY_800
        btn_aba_entrada.style.color = ft.Colors.WHITE if aba == "ENTRADA" else ft.Colors.GREY_300

        btn_aba_boletos.style.bgcolor = ft.Colors.ORANGE_800 if aba == "BOLETO" else ft.Colors.GREY_800
        btn_aba_boletos.style.color = ft.Colors.WHITE if aba == "BOLETO" else ft.Colors.GREY_300

        btn_aba_relatorios.style.bgcolor = ft.Colors.BLUE_800 if aba == "RELATORIOS" else ft.Colors.GREY_800
        btn_aba_relatorios.style.color = ft.Colors.WHITE if aba == "RELATORIOS" else ft.Colors.GREY_300

        if aba == "BOLETO":
            card_formulario.visible = False
            card_boletos.visible = True
            card_extrato.visible = True
            card_relatorios.visible = False
            _carregar_tabela_boletos()
        elif aba == "RELATORIOS":
            card_formulario.visible = False
            card_boletos.visible = False
            card_extrato.visible = False
            card_relatorios.visible = True
            _carregar_relatorio_periodo()
        else:
            card_formulario.visible = True
            card_boletos.visible = False
            card_extrato.visible = True
            card_relatorios.visible = False
            lbl_titulo_form.value = "Nova Saída de Caixa" if aba == "SAIDA" else "Nova Entrada de Caixa"
            _atualizar_opcoes_subtipo()

        page.update()

    btn_aba_saida.on_click      = lambda e: _trocar_aba("SAIDA")
    btn_aba_entrada.on_click    = lambda e: _trocar_aba("ENTRADA")
    btn_aba_boletos.on_click    = lambda e: _trocar_aba("BOLETO")
    btn_aba_relatorios.on_click = lambda e: _trocar_aba("RELATORIOS")

    # ── 7. Seção de Boletos em Aberto ─────────────────────────────────────────
    col_lista_boletos = ft.Column(spacing=8, expand=True)

    def _carregar_tabela_boletos():
        database.boleto_atualizar_status_vencidos()
        parcelas = database.boletos_parcelas_em_aberto(dias_frente=60)

        col_lista_boletos.controls.clear()
        if not parcelas:
            col_lista_boletos.controls.append(ft.Container(
                padding=ft.Padding.all(20),
                content=ft.Text("Nenhum boleto ou conta a pagar em aberto nos próximos 60 dias.", italic=True, color=ft.Colors.GREY_400),
            ))
            return

        linhas_b = []
        for p in parcelas:
            faixa = p["faixa"]
            if faixa == "VENCIDO":
                badge_cor = ft.Colors.RED_700
                badge_txt = f"VENCIDO ({abs(p['dias_para_vencer'])}d)"
            elif faixa == "HOJE":
                badge_cor = ft.Colors.ORANGE_700
                badge_txt = "VENCE HOJE"
            elif faixa == "ATE_7":
                badge_cor = ft.Colors.AMBER_800
                badge_txt = f"Vence em {p['dias_para_vencer']}d"
            else:
                badge_cor = ft.Colors.BLUE_GREY_700
                badge_txt = f"Em {p['dias_para_vencer']}d"

            def _fazer_quitar(_p=p):
                return lambda ev: _dialogo_quitar_parcela(
                    page, _p, on_sucesso=lambda msg: (_carregar_tabela_boletos(), _atualizar_tabela_extrato(), page.overlay.append(ft.SnackBar(content=ft.Text(msg), bgcolor=ft.Colors.GREEN_700, open=True)), page.update())
                )

            linhas_b.append(ft.DataRow(cells=[
                ft.DataCell(ft.Container(
                    content=ft.Text(badge_txt, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    bgcolor=badge_cor,
                    border_radius=4,
                    padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                )),
                ft.DataCell(ft.Text(_data_iso_para_br(p["vencimento"]))),
                ft.DataCell(ft.Text(p["nome_fornecedor"], weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(p["descricao"])),
                ft.DataCell(ft.Text(f"{p['num_parcela']}/{p['num_parcelas']}")),
                ft.DataCell(ft.Text(f"R$ {p['valor']:.2f}", weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.ElevatedButton(
                    "Quitar",
                    icon=ft.Icons.CHECK_CIRCLE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
                    on_click=_fazer_quitar(),
                )),
            ]))

        col_lista_boletos.controls.append(ft.Row(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Situação")),
                        ft.DataColumn(ft.Text("Vencimento")),
                        ft.DataColumn(ft.Text("Fornecedor")),
                        ft.DataColumn(ft.Text("Descrição")),
                        ft.DataColumn(ft.Text("Parc.")),
                        ft.DataColumn(ft.Text("Valor"), numeric=True),
                        ft.DataColumn(ft.Text("Ação")),
                    ],
                    rows=linhas_b,
                    column_spacing=16,
                )
            ]
        ))

    card_boletos = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(20),
            content=ft.Column(
                spacing=14,
                controls=[
                    ft.Row([
                        ft.Text("Boletos e Contas a Pagar em Aberto (Próximos 60 dias)", size=16, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Atualizar", on_click=lambda e: (_carregar_tabela_boletos(), page.update())),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=1),
                    col_lista_boletos,
                ],
            ),
        ),
    )

    # ── 8. Salvar Lançamento (Manual / Edição) ─────────────────────────────────

    def _limpar_form():
        data_anterior = tf_data.value
        dd_subtipo.value = None
        dd_pessoa.value = None
        dd_fornecedor.value = None
        dd_metodo.value = "Dinheiro"
        tf_valor.value = ""
        tf_obs.value = ""
        txt_erro.value = ""
        linha_pessoa.visible = False
        linha_fornecedor.visible = False
        linha_metodo.visible = False
        _estado["cat_selecionada"] = None
        _estado["editando_id"] = None
        btn_salvar.text = "Salvar Lançamento"
        btn_cancelar.visible = False
        lbl_titulo_form.value = "Nova Saída de Caixa" if _estado["fluxo_ui"] == "SAIDA" else "Nova Entrada de Caixa"
        tf_data.value = data_anterior

    def _salvar(e):
        txt_erro.value = ""

        if not dd_subtipo.value:
            txt_erro.value = "Selecione o subtipo / categoria."
            page.update()
            return

        cat = cat_map.get(int(dd_subtipo.value))
        if not cat:
            txt_erro.value = "Categoria inválida."
            page.update()
            return

        valor = _to_float(tf_valor.value)
        if valor <= 0:
            txt_erro.value = "Informe o valor do lançamento."
            page.update()
            return

        cod = cat.get("codigo") or ""
        usa_func = cat.get("usa_funcionario", 0) == 1
        usa_forn = cat.get("usa_fornecedor", 0) == 1

        id_pessoa = int(dd_pessoa.value) if (usa_func and dd_pessoa.value) else None
        if usa_func and not id_pessoa:
            lbl_pessoa = "o entregador" if cod in ("corrida_extra", "reentrega") else "o funcionário"
            txt_erro.value = f"Selecione {lbl_pessoa}."
            page.update()
            return

        id_fornecedor = int(dd_fornecedor.value) if (usa_forn and dd_fornecedor.value) else None
        if usa_forn and not id_fornecedor:
            txt_erro.value = "Selecione o fornecedor / prestador de serviço."
            page.update()
            return

        # Método de pagamento é obrigatório para todas as categorias com movimentação financeira real
        if cod not in ("consumo", "corrida_extra", "reentrega") and not dd_metodo.value:
            txt_erro.value = "Selecione o método de pagamento."
            page.update()
            return

        fluxo_banco = cat["fluxo"]
        metodo = dd_metodo.value if linha_metodo.visible else None
        obs = tf_obs.value.strip() or None
        if cod == "consumo":
            obs = _montar_obs_consumo(obs)

        data_iso = _data_br_para_iso(tf_data.value)

        try:
            if _estado["editando_id"] is not None:
                database.mov_extra_atualizar(
                    _estado["editando_id"],
                    data=data_iso,
                    id_categoria=cat["id"],
                    fluxo=fluxo_banco,
                    valor=valor,
                    id_pessoa=id_pessoa,
                    id_fornecedor=id_fornecedor,
                    metodo=metodo,
                    obs=obs,
                )
                msg = "Movimentação atualizada com sucesso!"
            else:
                database.mov_extra_inserir(
                    data=data_iso,
                    id_categoria=cat["id"],
                    fluxo=fluxo_banco,
                    valor=valor,
                    id_pessoa=id_pessoa,
                    id_fornecedor=id_fornecedor,
                    metodo=metodo,
                    obs=obs,
                )
                msg = "Movimentação registrada com sucesso!"

            _limpar_form()
            _atualizar_tabela_extrato()

            page.overlay.append(ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.GREEN_700,
                open=True,
            ))
            page.update()
        except Exception as ex:
            txt_erro.value = f"Erro ao salvar: {ex}"
            page.update()

    btn_salvar = ft.ElevatedButton(
        "Salvar Lançamento",
        icon=ft.Icons.SAVE,
        on_click=_salvar,
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
    )

    btn_cancelar = ft.TextButton(
        "Cancelar Edição",
        visible=False,
        on_click=lambda e: (_limpar_form(), page.update()),
    )

    card_formulario = ft.Card(
        content=ft.Container(
            padding=ft.Padding.all(20),
            content=ft.Column(
                spacing=14,
                controls=[
                    lbl_titulo_form,
                    ft.Divider(height=1),
                    dd_subtipo,
                    linha_pessoa,
                    linha_fornecedor,
                    linha_metodo,
                    tf_valor,
                    tf_obs,
                    txt_erro,
                    ft.Row([btn_salvar, btn_cancelar], spacing=10),
                ],
            ),
        ),
    )

    # ── 9. Extrato do Dia e Totais ────────────────────────────────────────────
    col_tabela_extrato = ft.Column(spacing=0, expand=True)
    row_totais_extrato = ft.Row(spacing=16, wrap=True)

    def _atualizar_tabela_extrato():
        data_iso = _data_br_para_iso(tf_data.value or hoje_br)
        movs = [dict(m) for m in database.mov_extra_listar_por_data(data_iso)]

        def _on_editar(m):
            def handler(e):
                _estado["editando_id"] = m["id"]
                tf_data.value = _data_iso_para_br(m["data"])

                cat = cat_map.get(m["id_categoria"])
                if cat:
                    fluxo = cat["fluxo"]
                    if fluxo in ("SAIDA", "NEUTRO"):
                        _trocar_aba("SAIDA")
                    else:
                        _trocar_aba("ENTRADA")

                    dd_subtipo.value = str(cat["id"])
                    _ajustar_campos_por_subtipo(cat)

                if m["id_pessoa"]:
                    dd_pessoa.value = str(m["id_pessoa"])
                if m.get("id_fornecedor"):
                    dd_fornecedor.value = str(m["id_fornecedor"])
                if m["metodo"]:
                    dd_metodo.value = m["metodo"]

                tf_valor.value = f"{m['valor']:.2f}".replace(".", ",")
                
                obs_txt = m["obs"] or ""
                if cat and cat.get("codigo") == "consumo":
                    obs_txt = _extrair_obs_consumo(obs_txt)
                tf_obs.value = obs_txt

                btn_salvar.text = "Salvar Alteração"
                btn_cancelar.visible = True
                lbl_titulo_form.value = f"Editando Movimentação #{m['id']}"
                page.update()
            return handler

        def _on_excluir(id_mov, desc, val, dt):
            def handler(e):
                def _executar():
                    database.mov_extra_excluir(id_mov)
                    database.log_registrar(
                        acao="EXCLUIR_MOVIMENTACAO",
                        tabela="movimentacoes_extras",
                        id_registro=id_mov,
                        descricao=f"Movimentação excluída: {desc} | R$ {val:.2f} | Data: {dt}",
                        valor_antes=f"cat={desc}, val={val}",
                    )
                    _atualizar_tabela_extrato()
                    page.overlay.append(ft.SnackBar(
                        content=ft.Text("Movimentação excluída e estornada com sucesso."),
                        bgcolor=ft.Colors.AMBER_900,
                        open=True,
                    ))
                    page.update()
                _confirmar_exclusao(page, f"a movimentação #{id_mov} ({desc} - R$ {val:.2f})", _executar)
            return handler

        total_entrada = 0.0
        total_saida   = 0.0
        total_neutro  = 0.0
        linhas = []
        forn_nome_map = {f["id"]: f["nome"] for f in fornecedores_db}

        for m in movs:
            fluxo = m["fluxo"]
            if fluxo == "ENTRADA":
                total_entrada += m["valor"]
                fluxo_cor = ft.Colors.GREEN_400
            elif fluxo == "SAIDA":
                total_saida += m["valor"]
                fluxo_cor = ft.Colors.RED_400
            else:  # NEUTRO
                total_neutro += m["valor"]
                fluxo_cor = ft.Colors.GREY_500

            entidade_vinculada = "—"
            if m["nome_pessoa"]:
                entidade_vinculada = m["nome_pessoa"]
            elif m.get("id_fornecedor") and m["id_fornecedor"] in forn_nome_map:
                entidade_vinculada = forn_nome_map[m["id_fornecedor"]]

            linhas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(entidade_vinculada)),
                ft.DataCell(ft.Text(m["categoria"] or "—", weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(fluxo, color=fluxo_cor, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(m["metodo"] or "—")),
                ft.DataCell(ft.Text(f"R$ {m['valor']:.2f}")),
                ft.DataCell(ft.Text(m["obs"] or "", size=12)),
                ft.DataCell(ft.Row(spacing=0, controls=[
                    ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED,
                        icon_color=ft.Colors.BLUE_400,
                        tooltip="Editar",
                        on_click=_on_editar(m),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Excluir / Estornar",
                        on_click=_on_excluir(m["id"], m["categoria"], m["valor"], tf_data.value),
                    ),
                ])),
            ]))

        col_tabela_extrato.controls.clear()
        if not linhas:
            col_tabela_extrato.controls.append(ft.Text(
                "Nenhuma movimentação registrada nesta data.",
                italic=True,
                color=ft.Colors.GREY_500,
            ))
        else:
            col_tabela_extrato.controls.append(ft.Row(
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Pessoa / Fornecedor")),
                            ft.DataColumn(ft.Text("Categoria")),
                            ft.DataColumn(ft.Text("Fluxo")),
                            ft.DataColumn(ft.Text("Método")),
                            ft.DataColumn(ft.Text("Valor"), numeric=True),
                            ft.DataColumn(ft.Text("Obs")),
                            ft.DataColumn(ft.Text("Ações")),
                        ],
                        rows=linhas,
                        column_spacing=14,
                    )
                ],
            ))

        row_totais_extrato.controls.clear()
        row_totais_extrato.controls += [
            ft.Text(f"Entradas: R$ {total_entrada:.2f}", color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD, size=14),
            ft.Text("|", color=ft.Colors.GREY_600),
            ft.Text(f"Saídas: R$ {total_saida:.2f}", color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD, size=14),
            ft.Text("|", color=ft.Colors.GREY_600),
            ft.Text(f"Neutro (corridas/consumo): R$ {total_neutro:.2f}", color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD, size=14),
        ]

    card_extrato = ft.Card(
        content=ft.Container(
            padding=ft.Padding.all(20),
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Row([
                        ft.Text("Extrato de Movimentações do Dia", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([tf_data, btn_calendario, btn_refresh], spacing=6),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    ft.Divider(height=1),
                    col_tabela_extrato,
                    ft.Divider(height=1),
                    row_totais_extrato,
                ],
            ),
        ),
    )

    # ── 10. Seção de Relatórios & Consulta por Período ─────────────────────────
    # Filtros de data do relatório
    primeiro_dia_mes = date(hoje_obj.year, hoje_obj.month, 1)
    tf_rel_ini = ft.TextField(label="Data Início", value=primeiro_dia_mes.strftime("%d/%m/%Y"), width=130, text_align=ft.TextAlign.CENTER)
    tf_rel_fim = ft.TextField(label="Data Fim", value=hoje_br, width=130, text_align=ft.TextAlign.CENTER)

    def _on_rel_ini_picked(e):
        if e.control.value:
            tf_rel_ini.value = e.control.value.strftime("%d/%m/%Y")
            _carregar_relatorio_periodo()
            page.update()

    def _on_rel_fim_picked(e):
        if e.control.value:
            tf_rel_fim.value = e.control.value.strftime("%d/%m/%Y")
            _carregar_relatorio_periodo()
            page.update()

    dp_rel_ini = ft.DatePicker(on_change=_on_rel_ini_picked)
    dp_rel_fim = ft.DatePicker(on_change=_on_rel_fim_picked)
    page.overlay.extend([dp_rel_ini, dp_rel_fim])

    # Containers de exibição do relatório
    row_kpis_relatorio = ft.Row(spacing=12, wrap=True)
    col_tabela_resumos = ft.Column(spacing=14, expand=True)
    col_analitico_rel  = ft.Column(spacing=8, expand=True)

    _relatorio_cache = {"dados": {}, "ini_iso": "", "fim_iso": ""}

    def _definir_periodo_rapido(dias_atras=0, mes_atual=False, mes_anterior=False):
        nonlocal hoje_obj
        if mes_atual:
            dt_ini = date(hoje_obj.year, hoje_obj.month, 1)
            dt_fim = hoje_obj
        elif mes_anterior:
            primeiro_deste = date(hoje_obj.year, hoje_obj.month, 1)
            ultimo_passado = primeiro_deste - timedelta(days=1)
            dt_ini = date(ultimo_passado.year, ultimo_passado.month, 1)
            dt_fim = ultimo_passado
        else:
            dt_ini = hoje_obj - timedelta(days=dias_atras)
            dt_fim = hoje_obj

        tf_rel_ini.value = dt_ini.strftime("%d/%m/%Y")
        tf_rel_fim.value = dt_fim.strftime("%d/%m/%Y")
        _carregar_relatorio_periodo()
        page.update()

    def _exportar_excel(e):
        dados = _relatorio_cache.get("dados")
        if not dados:
            return
        try:
            caminho = excel_gerador.excel_movimentacoes(tf_rel_ini.value, tf_rel_fim.value, dados, abrir_ao_concluir=True)
            page.overlay.append(ft.SnackBar(content=ft.Text(f"Planilha Excel gerada: {caminho}"), bgcolor=ft.Colors.GREEN_700, open=True))
            page.update()
        except Exception as ex:
            page.overlay.append(ft.SnackBar(content=ft.Text(f"Erro ao exportar Excel: {ex}"), bgcolor=ft.Colors.RED_700, open=True))
            page.update()

    def _exportar_pdf(e):
        dados = _relatorio_cache.get("dados")
        if not dados:
            return
        try:
            caminho = pdf_gerador.gerar_pdf_movimentacoes(tf_rel_ini.value, tf_rel_fim.value, dados, abrir_ao_concluir=True)
            page.overlay.append(ft.SnackBar(content=ft.Text(f"Relatório PDF gerado: {caminho}"), bgcolor=ft.Colors.GREEN_700, open=True))
            page.update()
        except Exception as ex:
            page.overlay.append(ft.SnackBar(content=ft.Text(f"Erro ao exportar PDF: {ex}"), bgcolor=ft.Colors.RED_700, open=True))
            page.update()

    def _kpi_card(titulo: str, valor: float, cor_valor: str, icon: ft.Icons):
        return ft.Container(
            width=180,
            padding=ft.Padding.all(12),
            bgcolor=ft.Colors.GREY_900,
            border_radius=8,
            border=ft.Border.all(1, ft.Colors.GREY_800),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row([ft.Icon(icon, size=16, color=cor_valor), ft.Text(titulo, size=12, color=ft.Colors.GREY_400)], spacing=6),
                    ft.Text(f"R$ {valor:.2f}", size=18, weight=ft.FontWeight.BOLD, color=cor_valor),
                ],
            ),
        )

    def _carregar_relatorio_periodo():
        ini_iso = _data_br_para_iso(tf_rel_ini.value)
        fim_iso = _data_br_para_iso(tf_rel_fim.value)

        dados = database.mov_extra_relatorio_periodo(ini_iso, fim_iso)
        _relatorio_cache["dados"]   = dados
        _relatorio_cache["ini_iso"] = ini_iso
        _relatorio_cache["fim_iso"] = fim_iso

        totais = dados.get("totais", {})
        saldo = totais.get("saldo", 0.0)

        # 1. Atualiza KPIs
        row_kpis_relatorio.controls.clear()
        row_kpis_relatorio.controls.extend([
            _kpi_card("Total Entradas", totais.get("entradas", 0.0), ft.Colors.GREEN_400, ft.Icons.ARROW_DOWNWARD),
            _kpi_card("Total Saídas", totais.get("saidas", 0.0), ft.Colors.RED_400, ft.Icons.ARROW_UPWARD),
            _kpi_card("Saldo Líquido", saldo, ft.Colors.GREEN_400 if saldo >= 0 else ft.Colors.RED_400, ft.Icons.ACCOUNT_BALANCE_WALLET),
            _kpi_card("Saídas Dinheiro", totais.get("saidas_dinheiro", 0.0), ft.Colors.AMBER_400, ft.Icons.MONEY),
            _kpi_card("Saídas PIX", totais.get("saidas_pix", 0.0), ft.Colors.CYAN_400, ft.Icons.PIX),
            _kpi_card("Neutro (Compensações)", totais.get("neutro", 0.0), ft.Colors.GREY_400, ft.Icons.SYNC_ALT),
        ])

        # 2. Resumo por Categoria
        categorias = dados.get("resumo_categorias", [])
        lin_cat = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(c["categoria"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(
                    c["fluxo"],
                    color=ft.Colors.GREEN_400 if c["fluxo"] == "ENTRADA" else (ft.Colors.RED_400 if c["fluxo"] == "SAIDA" else ft.Colors.GREY_400),
                    weight=ft.FontWeight.BOLD,
                )),
                ft.DataCell(ft.Text(str(c["qtd"]))),
                ft.DataCell(ft.Text(f"R$ {c['total']:.2f}", weight=ft.FontWeight.BOLD)),
            ])
            for c in categorias
        ]
        tab_cat = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Categoria")),
                ft.DataColumn(ft.Text("Fluxo")),
                ft.DataColumn(ft.Text("Qtd Lanç."), numeric=True),
                ft.DataColumn(ft.Text("Total (R$)"), numeric=True),
            ],
            rows=lin_cat,
            column_spacing=16,
        ) if lin_cat else ft.Text("Nenhuma movimentação no período.", italic=True, color=ft.Colors.GREY_500)

        # 3. Resumo por Fornecedor
        fornecedores = dados.get("resumo_fornecedores", [])
        lin_forn = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(f["nome"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(str(f["qtd"]))),
                ft.DataCell(ft.Text(f"R$ {f['total']:.2f}", color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD)),
            ])
            for f in fornecedores
        ]
        tab_forn = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fornecedor")),
                ft.DataColumn(ft.Text("Qtd Lanç."), numeric=True),
                ft.DataColumn(ft.Text("Total Gasto (R$)"), numeric=True),
            ],
            rows=lin_forn,
            column_spacing=16,
        ) if lin_forn else ft.Text("Nenhum lançamento com fornecedor no período.", italic=True, color=ft.Colors.GREY_500)

        # 4. Resumo por Método
        metodos = dados.get("resumo_metodos", [])
        lin_met = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(m["metodo"], weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(str(m["qtd"]))),
                ft.DataCell(ft.Text(f"R$ {m['total']:.2f}", weight=ft.FontWeight.BOLD)),
            ])
            for m in metodos
        ]
        tab_met = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Forma de Pagamento")),
                ft.DataColumn(ft.Text("Qtd Lanç."), numeric=True),
                ft.DataColumn(ft.Text("Total (R$)"), numeric=True),
            ],
            rows=lin_met,
            column_spacing=16,
        ) if lin_met else ft.Text("Nenhum método registrado no período.", italic=True, color=ft.Colors.GREY_500)

        col_tabela_resumos.controls.clear()
        col_tabela_resumos.controls.append(
            ft.ResponsiveRow(
                columns=12,
                spacing=14,
                controls=[
                    ft.Container(
                        col={"sm": 12, "md": 12, "lg": 4},
                        padding=ft.Padding.all(16),
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.GREY_800),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.CATEGORY, size=18, color=ft.Colors.BLUE_400),
                                ft.Text("Resumo por Categoria", size=15, weight=ft.FontWeight.BOLD),
                            ], spacing=8),
                            ft.Divider(height=1),
                            ft.Row([tab_cat], scroll=ft.ScrollMode.AUTO),
                        ], spacing=10),
                    ),
                    ft.Container(
                        col={"sm": 12, "md": 6, "lg": 4},
                        padding=ft.Padding.all(16),
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.GREY_800),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.STORE, size=18, color=ft.Colors.ORANGE_400),
                                ft.Text("Gastos por Fornecedor", size=15, weight=ft.FontWeight.BOLD),
                            ], spacing=8),
                            ft.Divider(height=1),
                            ft.Row([tab_forn], scroll=ft.ScrollMode.AUTO),
                        ], spacing=10),
                    ),
                    ft.Container(
                        col={"sm": 12, "md": 6, "lg": 4},
                        padding=ft.Padding.all(16),
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=8,
                        border=ft.Border.all(1, ft.Colors.GREY_800),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PAYMENT, size=18, color=ft.Colors.GREEN_400),
                                ft.Text("Forma de Pagamento", size=15, weight=ft.FontWeight.BOLD),
                            ], spacing=8),
                            ft.Divider(height=1),
                            ft.Row([tab_met], scroll=ft.ScrollMode.AUTO),
                        ], spacing=10),
                    ),
                ],
            )
        )

        # 5. Extrato Analítico (Recolhível e Paginado 20 em 20)
        _renderizar_extrato_analitico()

    _rel_analitico_expandido = {"v": False}
    _rel_pagina_atual = {"v": 1}
    ITENS_POR_PAGINA = 20

    def _renderizar_extrato_analitico():
        dados = _relatorio_cache.get("dados", {})
        itens = dados.get("itens", [])
        total_itens = len(itens)

        def _toggle_expandir(e):
            _rel_analitico_expandido["v"] = not _rel_analitico_expandido["v"]
            _renderizar_extrato_analitico()
            page.update()

        def _mudar_pagina(delta):
            total_pags = max(1, (total_itens + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
            nova_pag = _rel_pagina_atual["v"] + delta
            if 1 <= nova_pag <= total_pags:
                _rel_pagina_atual["v"] = nova_pag
                _renderizar_extrato_analitico()
                page.update()

        txt_btn = "Ocultar Extrato Analítico [^]" if _rel_analitico_expandido["v"] else f"Ver Extrato Analítico Completo ({total_itens} registros) [v]"
        btn_toggle = ft.OutlinedButton(
            txt_btn,
            icon=ft.Icons.VISIBILITY_OFF if _rel_analitico_expandido["v"] else ft.Icons.VISIBILITY,
            on_click=_toggle_expandir,
        )

        col_analitico_rel.controls.clear()
        if not _rel_analitico_expandido["v"]:
            col_analitico_rel.controls.append(
                ft.Container(
                    padding=ft.Padding.all(12),
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=8,
                    border=ft.Border.all(1, ft.Colors.GREY_800),
                    content=ft.Row([
                        btn_toggle,
                        ft.Text("Extrato analítico recolhido. Clique para visualizar e paginar os lançamentos detalhados.", size=12, color=ft.Colors.GREY_500, italic=True),
                    ], spacing=16, wrap=True, alignment=ft.MainAxisAlignment.START),
                )
            )
            return

        # Modo Expandido: Paginação de 20 em 20
        total_pags = max(1, (total_itens + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
        if _rel_pagina_atual["v"] > total_pags:
            _rel_pagina_atual["v"] = total_pags

        idx_inicio = (_rel_pagina_atual["v"] - 1) * ITENS_POR_PAGINA
        idx_fim    = min(idx_inicio + ITENS_POR_PAGINA, total_itens)
        itens_pag  = itens[idx_inicio:idx_fim]

        lin_itens = []
        for r in itens_pag:
            fl = r["fluxo"]
            cor = ft.Colors.GREEN_400 if fl == "ENTRADA" else (ft.Colors.RED_400 if fl == "SAIDA" else ft.Colors.GREY_400)
            entidade = r["nome_fornecedor"] or r["nome_pessoa"] or "—"
            lin_itens.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(_data_iso_para_br(r["data"]))),
                ft.DataCell(ft.Text(entidade)),
                ft.DataCell(ft.Text(r["categoria"] or "—")),
                ft.DataCell(ft.Text(fl, color=cor, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(r["metodo"] or "—")),
                ft.DataCell(ft.Text(f"R$ {r['valor']:.2f}")),
                ft.DataCell(ft.Text(r["obs"] or "", size=11)),
            ]))

        tab_analitico = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Data")),
                ft.DataColumn(ft.Text("Pessoa / Fornecedor")),
                ft.DataColumn(ft.Text("Categoria")),
                ft.DataColumn(ft.Text("Fluxo")),
                ft.DataColumn(ft.Text("Método")),
                ft.DataColumn(ft.Text("Valor"), numeric=True),
                ft.DataColumn(ft.Text("Obs")),
            ],
            rows=lin_itens,
            column_spacing=14,
        ) if lin_itens else ft.Text("Nenhum lançamento no período filtrado.", italic=True, color=ft.Colors.GREY_500)

        controles_paginacao = ft.Row([
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT,
                tooltip="Página anterior",
                disabled=(_rel_pagina_atual["v"] <= 1),
                on_click=lambda e: _mudar_pagina(-1),
            ),
            ft.Text(
                f"Página {_rel_pagina_atual['v']} de {total_pags} (Exibindo {len(itens_pag)} de {total_itens} registros)",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREY_300,
            ),
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT,
                tooltip="Próxima página",
                disabled=(_rel_pagina_atual["v"] >= total_pags),
                on_click=lambda e: _mudar_pagina(1),
            ),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

        col_analitico_rel.controls.append(
            ft.Container(
                padding=ft.Padding.all(16),
                bgcolor=ft.Colors.GREY_900,
                border_radius=8,
                border=ft.Border.all(1, ft.Colors.GREY_800),
                content=ft.Column([
                    ft.Row([
                        btn_toggle,
                        controles_paginacao,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    ft.Divider(height=1),
                    ft.Row([tab_analitico], scroll=ft.ScrollMode.AUTO),
                    ft.Divider(height=1),
                    controles_paginacao,
                ], spacing=10),
            )
        )

    card_relatorios = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(20),
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Row([
                        ft.Text("Relatório & Análise de Movimentações", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.ElevatedButton("Exportar Excel", icon=ft.Icons.TABLE_VIEW, style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800, color=ft.Colors.WHITE), on_click=_exportar_excel),
                            ft.ElevatedButton("Gerar PDF", icon=ft.Icons.PICTURE_AS_PDF, style=ft.ButtonStyle(bgcolor=ft.Colors.RED_800, color=ft.Colors.WHITE), on_click=_exportar_pdf),
                        ], spacing=8),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    ft.Divider(height=1),
                    # Filtros de Período
                    ft.Row([
                        ft.OutlinedButton("Hoje", on_click=lambda e: _definir_periodo_rapido(dias_atras=0)),
                        ft.OutlinedButton("7 Dias", on_click=lambda e: _definir_periodo_rapido(dias_atras=7)),
                        ft.OutlinedButton("Mês Atual", on_click=lambda e: _definir_periodo_rapido(mes_atual=True)),
                        ft.OutlinedButton("Mês Anterior", on_click=lambda e: _definir_periodo_rapido(mes_anterior=True)),
                        ft.Row([
                            tf_rel_ini,
                            ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=lambda e: (setattr(dp_rel_ini, "open", True), page.update())),
                            ft.Text("até"),
                            tf_rel_fim,
                            ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=lambda e: (setattr(dp_rel_fim, "open", True), page.update())),
                            ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Filtrar Período", on_click=lambda e: (_carregar_relatorio_periodo(), page.update())),
                        ], spacing=4, wrap=True),
                    ], wrap=True, spacing=8),
                    ft.Divider(height=1),
                    # KPIs
                    row_kpis_relatorio,
                    ft.Divider(height=1),
                    # Tabelas de Resumo
                    col_tabela_resumos,
                    ft.Divider(height=1),
                    # Extrato Analítico
                    ft.Text("Lançamentos Analíticos do Período", size=15, weight=ft.FontWeight.BOLD),
                    col_analitico_rel,
                ],
            ),
        ),
    )

    def _atualizar_tudo():
        _atualizar_tabela_extrato()
        if _estado["fluxo_ui"] == "BOLETO":
            _carregar_tabela_boletos()
        elif _estado["fluxo_ui"] == "RELATORIOS":
            _carregar_relatorio_periodo()

    # Dispara a carga inicial da tela
    _trocar_aba("SAIDA")
    _atualizar_tudo()

    # ── 11. Montagem da Estrutura Final da Tela ───────────────────────────────
    seletor_abas_topo = ft.Container(
        padding=ft.Padding.symmetric(vertical=6),
        content=ft.Row(
            spacing=10,
            controls=[
                btn_aba_saida,
                btn_aba_entrada,
                btn_aba_boletos,
                btn_aba_relatorios,
            ],
            wrap=True,
        ),
    )

    return ft.Column(
        controls=[
            seletor_abas_topo,
            card_formulario,
            card_boletos,
            card_extrato,
            card_relatorios,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=16,
    )
