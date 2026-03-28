"""
views/estoque.py — Controle de estoque interno (insumos, embalagens, uso interno).
Três abas: Estoque (visão), Movimentações, Cadastro.
"""

import csv
import os
from datetime import date

import flet as ft

import database
from relatorios.pdf_gerador import gerar_pdf_estoque, abrir_pdf
from relatorios.excel_gerador import excel_estoque_movimentacoes


# ── Utilitários ────────────────────────────────────────────────────────────────

def _fmt_moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_qtd(v: float, unidade: str = "") -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return f"{s} {unidade}".strip() if unidade else s


def _data_br_para_iso(s: str) -> str:
    try:
        d, m, a = s.strip().split("/")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    except Exception:
        return date.today().isoformat()


def _iso_para_br(iso: str) -> str:
    try:
        return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"
    except Exception:
        return iso or ""


def _to_float(s: str) -> float:
    try:
        return float(s.replace(",", "."))
    except Exception:
        return 0.0


_UNIDADES = ["un", "kg", "g", "l", "ml", "cx", "pct"]

_MOTIVOS = {
    "ENTRADA": ["Compra", "Devolução", "Ajuste positivo", "Outro"],
    "SAIDA":   ["Consumo", "Perda", "Vencimento", "Ajuste negativo", "Outro"],
    "AJUSTE":  ["Inventário", "Correção manual", "Outro"],
}

_COR_TIPO = {
    "ENTRADA": ft.Colors.GREEN_700,
    "SAIDA":   ft.Colors.RED_700,
    "AJUSTE":  ft.Colors.BLUE_700,
}

_BG_TIPO = {
    "ENTRADA": ft.Colors.with_opacity(0.05, ft.Colors.GREEN),
    "SAIDA":   ft.Colors.with_opacity(0.05, ft.Colors.RED),
    "AJUSTE":  ft.Colors.with_opacity(0.05, ft.Colors.BLUE),
}


def _chip_status(qtd_atual, qtd_min):
    if qtd_atual <= 0:
        return ft.Container(
            content=ft.Text("Zerado", size=11, color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.RED_700, border_radius=10,
            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
        )
    if qtd_atual <= qtd_min:
        return ft.Container(
            content=ft.Text("Baixo", size=11, color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD),
            bgcolor=ft.Colors.ORANGE_700, border_radius=10,
            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
        )
    return ft.Container(
        content=ft.Text("OK", size=11, color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD),
        bgcolor=ft.Colors.GREEN_700, border_radius=10,
        padding=ft.Padding(left=8, right=8, top=2, bottom=2),
    )


# ── View principal ────────────────────────────────────────────────────────────

def view(page: ft.Page) -> ft.Control:

    hoje      = date.today()
    hoje_br   = hoje.strftime("%d/%m/%Y")
    ini_mes_br = date(hoje.year, hoje.month, 1).strftime("%d/%m/%Y")

    # ═══════════════════════════════════════════════════════════════════════
    #  ABA 1 — ESTOQUE
    # ═══════════════════════════════════════════════════════════════════════

    col_alertas  = ft.Column(spacing=4)
    card_alertas = ft.Card(
        visible=False,
        content=ft.Container(
            padding=ft.Padding.all(12),
            bgcolor=ft.Colors.with_opacity(0.18, ft.Colors.RED),
            border_radius=8,
            content=ft.Column(spacing=6, controls=[
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.ORANGE_300, size=20),
                    ft.Text("Produtos abaixo do estoque mínimo",
                            size=13, weight=ft.FontWeight.BOLD,
                            color=ft.Colors.ORANGE_200),
                ]),
                col_alertas,
            ]),
        ),
    )

    row_resumo = ft.Row(spacing=12, wrap=True)

    # Filtros
    cats_est = database.estoque_categoria_listar()
    dd_filtro_cat = ft.Dropdown(
        label="Categoria",
        width=200,
        options=[ft.dropdown.Option("", text="Todas")]
        + [ft.dropdown.Option(str(c["id"]), text=c["nome"]) for c in cats_est],
        value="",
    )
    cb_apenas_baixo = ft.Checkbox(label="Apenas abaixo do mínimo", value=False)

    col_tabela_est = ft.Column(spacing=0)

    def _card_metric(titulo, valor_str, cor):
        return ft.Container(
            content=ft.Column(spacing=2, tight=True, controls=[
                ft.Text(titulo,    size=11, color=ft.Colors.GREY_500),
                ft.Text(valor_str, size=16, weight=ft.FontWeight.BOLD, color=cor),
            ]),
            bgcolor=None,
            border_radius=8, padding=ft.Padding.all(10),
        )

    def _abrir_dialog_mov(produto, tipo: str):
        """Abre AlertDialog para registrar ENTRADA, SAIDA ou AJUSTE."""
        tf_qtd    = ft.TextField(label="Quantidade", keyboard_type=ft.KeyboardType.NUMBER, width=160)
        tf_preco  = ft.TextField(
            label="Preço de custo (R$)",
            value=f"{produto['preco_custo']:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER, width=160,
        )
        dd_motivo = ft.Dropdown(
            label="Motivo",
            width=220,
            options=[ft.dropdown.Option(m) for m in _MOTIVOS[tipo]],
            value=_MOTIVOS[tipo][0],
        )
        tf_obs = ft.TextField(label="Observações (opcional)", expand=True)
        txt_err = ft.Text("", color=ft.Colors.RED_400, size=12)

        cor_tipo = _COR_TIPO[tipo]

        def _confirmar(e):
            qtd = _to_float(tf_qtd.value)
            if qtd <= 0:
                txt_err.value = "Informe uma quantidade maior que zero."
                page.update()
                return
            database.estoque_mov_inserir(
                data=hoje.isoformat(),
                id_produto=produto["id"],
                tipo=tipo,
                quantidade=qtd,
                preco_custo=_to_float(tf_preco.value),
                motivo=dd_motivo.value,
                obs=tf_obs.value.strip() or None,
            )
            dlg.open = False
            page.update()
            _carregar_estoque()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row(spacing=8, controls=[
                ft.Container(
                    content=ft.Text(tipo, size=13, color=ft.Colors.WHITE,
                                    weight=ft.FontWeight.BOLD),
                    bgcolor=cor_tipo, border_radius=6,
                    padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                ),
                ft.Text(produto["nome"], size=14),
            ]),
            content=ft.Column(spacing=10, width=460, tight=True, controls=[
                ft.Text(
                    f"Estoque atual: {_fmt_qtd(produto['quantidade_atual'], produto['unidade'])}",
                    size=12, color=ft.Colors.GREY_500,
                ),
                ft.Row([tf_qtd, tf_preco], spacing=12),
                dd_motivo,
                tf_obs,
                txt_err,
            ]),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: (
                    setattr(dlg, "open", False), page.update()
                )),
                ft.ElevatedButton(
                    "Confirmar",
                    ft.Icons.CHECK,
                    on_click=_confirmar,
                    style=ft.ButtonStyle(bgcolor=cor_tipo, color=ft.Colors.WHITE),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def _carregar_estoque(e=None):
        # Recarregar lista de categorias para o filtro
        nonlocal cats_est
        cats_est = database.estoque_categoria_listar()
        dd_filtro_cat.options = (
            [ft.dropdown.Option("", text="Todas")]
            + [ft.dropdown.Option(str(c["id"]), text=c["nome"]) for c in cats_est]
        )

        id_cat = int(dd_filtro_cat.value) if dd_filtro_cat.value else None
        produtos = database.estoque_produto_listar(
            apenas_ativos=True, id_categoria=id_cat
        )
        if cb_apenas_baixo.value:
            produtos = [p for p in produtos if p["abaixo_minimo"]]

        # Alertas
        abaixo = database.estoque_produtos_abaixo_minimo()
        col_alertas.controls = [
            ft.Text(
                f"• {p['nome']} — atual: {_fmt_qtd(p['quantidade_atual'], p['unidade'])}"
                f" | mínimo: {_fmt_qtd(p['quantidade_minima'], p['unidade'])}",
                size=12, color=ft.Colors.ORANGE_200,
            )
            for p in abaixo
        ]
        card_alertas.visible = bool(abaixo)

        # Resumo
        total_ativos = len(database.estoque_produto_listar())
        total_baixo  = len(abaixo)
        valor_tot    = database.estoque_valor_total()
        row_resumo.controls = [
            _card_metric("Total de produtos",    str(total_ativos),    ft.Colors.GREY_500),
            _card_metric(
                "Abaixo do mínimo",
                str(total_baixo),
                ft.Colors.ORANGE_400 if total_baixo > 0 else ft.Colors.GREY_600,
            ),
            _card_metric("Valor em estoque", _fmt_moeda(valor_tot), ft.Colors.BLUE_300),
        ]

        # Tabela
        cab = ft.Row(spacing=0, controls=[
            ft.Container(expand=3, content=ft.Text("Produto",     size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=120, content=ft.Text("Categoria",  size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=55,  content=ft.Text("Un.",        size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=85,  content=ft.Text("Qtd Atual",  size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=85,  content=ft.Text("Qtd Mín.",   size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=90,  content=ft.Text("Custo Unit.",size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=90,  content=ft.Text("Valor Total",size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=70,  content=ft.Text("Status",     size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=210, content=ft.Text("Ações",      size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
        ])

        col_tabela_est.controls = [cab, ft.Divider(height=1)]

        for p in produtos:
            qtd_a = p["quantidade_atual"]
            qtd_m = p["quantidade_minima"]
            vt    = qtd_a * p["preco_custo"]
            if qtd_a <= 0:
                cor_qtd = ft.Colors.RED_400
            elif qtd_a <= qtd_m:
                cor_qtd = ft.Colors.ORANGE_400
            elif qtd_a > qtd_m * 2:
                cor_qtd = ft.Colors.GREEN_400
            else:
                cor_qtd = None

            def _btn_mov(tipo, prod=p):
                cores = {"ENTRADA": ft.Colors.GREEN_700,
                         "SAIDA":   ft.Colors.ORANGE_700,
                         "AJUSTE":  ft.Colors.BLUE_700}
                icons = {"ENTRADA": ft.Icons.ADD,
                         "SAIDA":   ft.Icons.REMOVE,
                         "AJUSTE":  ft.Icons.TUNE}
                return ft.IconButton(
                    icon=icons[tipo],
                    icon_color=cores[tipo],
                    tooltip=tipo.capitalize(),
                    icon_size=18,
                    on_click=lambda e, t=tipo, pr=prod: _abrir_dialog_mov(pr, t),
                )

            col_tabela_est.controls.append(ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(expand=3, content=ft.Text(p["nome"], size=12)),
                    ft.Container(width=120, content=ft.Text(p["nome_categoria"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(width=55,  content=ft.Text(p["unidade"], size=12)),
                    ft.Container(width=85,  content=ft.Text(_fmt_qtd(qtd_a), size=12, color=cor_qtd, weight=ft.FontWeight.BOLD if cor_qtd else ft.FontWeight.NORMAL)),
                    ft.Container(width=85,  content=ft.Text(_fmt_qtd(qtd_m), size=12, color=ft.Colors.GREY_500)),
                    ft.Container(width=90,  content=ft.Text(_fmt_moeda(p["preco_custo"]), size=12)),
                    ft.Container(width=90,  content=ft.Text(_fmt_moeda(vt), size=12)),
                    ft.Container(width=70,  content=_chip_status(qtd_a, qtd_m)),
                    ft.Container(width=210, content=ft.Row(spacing=0, controls=[
                        _btn_mov("ENTRADA", p),
                        _btn_mov("SAIDA",   p),
                        _btn_mov("AJUSTE",  p),
                    ])),
                ],
            ))

        if not produtos:
            col_tabela_est.controls.append(
                ft.Text("Nenhum produto encontrado.", italic=True,
                        color=ft.Colors.GREY_500)
            )

        page.update()

    aba_estoque = ft.Column(
        expand=True, spacing=12,
        controls=[
            card_alertas,
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(12),
                content=row_resumo,
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(12),
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=12, wrap=True, controls=[
                        dd_filtro_cat,
                        cb_apenas_baixo,
                        ft.ElevatedButton(
                            "Filtrar",
                            ft.Icons.FILTER_LIST,
                            on_click=_carregar_estoque,
                        ),
                    ]),
                    ft.Row(scroll=ft.ScrollMode.AUTO, controls=[col_tabela_est]),
                ]),
            )),
        ],
    )

    # ═══════════════════════════════════════════════════════════════════════
    #  ABA 2 — MOVIMENTAÇÕES
    # ═══════════════════════════════════════════════════════════════════════

    tf_mov_ini  = ft.TextField(value=ini_mes_br, label="Início", width=130, hint_text="DD/MM/AAAA")
    tf_mov_fim  = ft.TextField(value=hoje_br,    label="Fim",    width=130, hint_text="DD/MM/AAAA")

    prods_todos = database.estoque_produto_listar(apenas_ativos=False)
    dd_mov_prod = ft.Dropdown(
        label="Produto", width=220,
        options=[ft.dropdown.Option("", text="Todos")]
        + [ft.dropdown.Option(str(p["id"]), text=p["nome"]) for p in prods_todos],
        value="",
    )
    dd_mov_tipo = ft.Dropdown(
        label="Tipo", width=140,
        options=[
            ft.dropdown.Option("",       text="Todos"),
            ft.dropdown.Option("ENTRADA",text="ENTRADA"),
            ft.dropdown.Option("SAIDA",  text="SAÍDA"),
            ft.dropdown.Option("AJUSTE", text="AJUSTE"),
        ],
        value="",
    )

    col_mov = ft.Column(spacing=0)
    row_rodape_mov = ft.Row(spacing=24, wrap=True)
    _movs_cache: list = []

    def _carregar_movs(e=None):
        nonlocal _movs_cache
        ini_iso = _data_br_para_iso(tf_mov_ini.value)
        fim_iso = _data_br_para_iso(tf_mov_fim.value)
        id_prod = int(dd_mov_prod.value) if dd_mov_prod.value else None
        tipo_f  = dd_mov_tipo.value or None

        movs = database.estoque_mov_listar(ini_iso, fim_iso, id_prod, tipo_f)
        _movs_cache = [dict(m) for m in movs]

        cab = ft.Row(spacing=0, controls=[
            ft.Container(width=80,  content=ft.Text("Data",       size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=50,  content=ft.Text("Hora",       size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(expand=2,  content=ft.Text("Produto",    size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=70,  content=ft.Text("Tipo",       size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=70,  content=ft.Text("Qtd",        size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=85,  content=ft.Text("Custo Unit.",size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=85,  content=ft.Text("Valor Total",size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=110, content=ft.Text("Motivo",     size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(expand=1,  content=ft.Text("Obs",        size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=40,  content=ft.Text("",           size=11)),
        ])
        col_mov.controls = [cab, ft.Divider(height=1)]

        tot_ent_qtd = tot_ent_val = tot_sai_qtd = tot_sai_val = 0.0

        for m in movs:
            if m["tipo"] == "ENTRADA":
                tot_ent_qtd += m["quantidade"];  tot_ent_val += m["valor_total"]
            elif m["tipo"] == "SAIDA":
                tot_sai_qtd += m["quantidade"];  tot_sai_val += m["valor_total"]

            bg = _BG_TIPO.get(m["tipo"])

            def _excluir(mid=m["id"]):
                def handler(e):
                    database.estoque_mov_excluir(mid)
                    _carregar_movs()
                return handler

            col_mov.controls.append(ft.Container(
                bgcolor=bg,
                content=ft.Row(
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=80,  content=ft.Text(_iso_para_br(m["data"]), size=12)),
                        ft.Container(width=50,  content=ft.Text(m["hora"] or "", size=12)),
                        ft.Container(expand=2,  content=ft.Text(m["nome_produto"], size=12)),
                        ft.Container(width=70,  content=ft.Text(m["tipo"], size=11,
                                                                color=_COR_TIPO[m["tipo"]],
                                                                weight=ft.FontWeight.BOLD)),
                        ft.Container(width=70,  content=ft.Text(f"{m['quantidade']:.3f}".rstrip("0").rstrip(".") + f" {m['unidade']}", size=12)),
                        ft.Container(width=85,  content=ft.Text(_fmt_moeda(m["preco_custo"]), size=12)),
                        ft.Container(width=85,  content=ft.Text(_fmt_moeda(m["valor_total"]), size=12)),
                        ft.Container(width=110, content=ft.Text(m["motivo"] or "—", size=12)),
                        ft.Container(expand=1,  content=ft.Text(m["obs"] or "", size=11, color=ft.Colors.GREY_500)),
                        ft.Container(width=40,  content=ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_400,
                            icon_size=16,
                            tooltip="Excluir",
                            on_click=_excluir(m["id"]),
                        )),
                    ],
                ),
            ))

        if not movs:
            col_mov.controls.append(
                ft.Text("Nenhuma movimentação no período.", italic=True,
                        color=ft.Colors.GREY_500)
            )

        row_rodape_mov.controls = [
            ft.Text(f"Entradas: {tot_ent_qtd:.2f} | {_fmt_moeda(tot_ent_val)}",
                    size=12, color=ft.Colors.GREEN_400),
            ft.Text(f"Saídas: {tot_sai_qtd:.2f} | {_fmt_moeda(tot_sai_val)}",
                    size=12, color=ft.Colors.RED_400),
        ]
        page.update()

    def _exportar_csv_mov(e):
        if not _movs_cache:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o filtro antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        os.makedirs("exports", exist_ok=True)
        ini_str = _data_br_para_iso(tf_mov_ini.value).replace("-", "")
        fim_str = _data_br_para_iso(tf_mov_fim.value).replace("-", "")
        caminho = os.path.join("exports", f"estoque_mov_{ini_str}_{fim_str}.csv")
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Data", "Hora", "Produto", "Tipo", "Quantidade",
                        "Preço Unit.", "Valor Total", "Motivo", "Obs"])
            for m in _movs_cache:
                w.writerow([
                    _iso_para_br(m["data"]), m["hora"] or "",
                    m["nome_produto"], m["tipo"],
                    f"{m['quantidade']:.3f}", f"{m['preco_custo']:.2f}",
                    f"{m['valor_total']:.2f}", m["motivo"] or "", m["obs"] or "",
                ])
        os.startfile(os.path.abspath(caminho))

    def _resumo_movs() -> dict:
        total_ent_qtd = total_ent_val = total_sai_qtd = total_sai_val = 0.0
        for m in _movs_cache:
            if m.get("tipo") == "ENTRADA":
                total_ent_qtd += m.get("quantidade", 0)
                total_ent_val += m.get("valor_total", 0.0)
            elif m.get("tipo") == "SAIDA":
                total_sai_qtd += m.get("quantidade", 0)
                total_sai_val += m.get("valor_total", 0.0)
        return {
            "total_entrada_qtd":   total_ent_qtd,
            "total_entrada_valor": total_ent_val,
            "total_saida_qtd":     total_sai_qtd,
            "total_saida_valor":   total_sai_val,
        }

    def _exportar_excel_mov(e):
        if not _movs_cache:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o filtro antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            ini_br = tf_mov_ini.value or date.today().strftime("%d/%m/%Y")
            fim_br = tf_mov_fim.value or date.today().strftime("%d/%m/%Y")
            caminho = excel_estoque_movimentacoes(ini_br, fim_br, _movs_cache, _resumo_movs())
            os.startfile(caminho)
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

    def _exportar_pdf_mov(e):
        if not _movs_cache:
            page.overlay.append(ft.SnackBar(
                content=ft.Text("Gere o filtro antes de exportar."),
                bgcolor=ft.Colors.ORANGE_700, open=True,
            ))
            page.update()
            return
        try:
            ini_br = tf_mov_ini.value or date.today().strftime("%d/%m/%Y")
            fim_br = tf_mov_fim.value or date.today().strftime("%d/%m/%Y")
            caminho = gerar_pdf_estoque(ini_br, fim_br, _movs_cache, _resumo_movs())
            abrir_pdf(caminho)
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

    aba_movimentacoes = ft.Column(
        expand=True, spacing=12,
        controls=[
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(12),
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=12, wrap=True, controls=[
                        tf_mov_ini, tf_mov_fim,
                        dd_mov_prod, dd_mov_tipo,
                        ft.ElevatedButton("Filtrar", ft.Icons.FILTER_LIST,
                                          on_click=_carregar_movs),
                        ft.ElevatedButton(
                            "Exportar CSV", ft.Icons.DOWNLOAD,
                            on_click=_exportar_csv_mov,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.TEAL_700,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.ElevatedButton(
                            "Excel",
                            icon=ft.Icons.TABLE_VIEW,
                            on_click=_exportar_excel_mov,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.GREEN_800,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.ElevatedButton(
                            "PDF",
                            icon=ft.Icons.PICTURE_AS_PDF,
                            on_click=_exportar_pdf_mov,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.RED_800,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                    ]),
                ]),
            )),
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(12),
                content=ft.Column(spacing=6, controls=[
                    ft.Row(scroll=ft.ScrollMode.AUTO, controls=[col_mov]),
                    row_rodape_mov,
                ]),
            )),
        ],
    )

    # ═══════════════════════════════════════════════════════════════════════
    #  ABA 3 — CADASTRO
    # ═══════════════════════════════════════════════════════════════════════

    # ── Categorias ─────────────────────────────────────────────────────────

    tf_cat_nome     = ft.TextField(label="Nome da categoria", expand=True)
    tabela_cats_col = ft.Column(spacing=0)

    def _refresh_cats():
        cats = database.estoque_categoria_listar(apenas_ativas=False)
        tabela_cats_col.controls = []
        for c in cats:
            ativo = bool(c["ativo"])
            def _toggle(cid=c["id"], a=ativo):
                database.estoque_categoria_atualizar(cid, ativo=0 if a else 1)
                _refresh_cats()
                # Recarregar dropdown de produtos
                _refresh_dd_cat_prod()
                page.update()
            tabela_cats_col.controls.append(ft.Row(
                spacing=8,
                controls=[
                    ft.Container(expand=True, content=ft.Text(c["nome"], size=13)),
                    ft.Text("Ativo" if ativo else "Inativo",
                            size=12,
                            color=ft.Colors.GREEN_400 if ativo else ft.Colors.GREY_600),
                    ft.TextButton(
                        "Inativar" if ativo else "Reativar",
                        on_click=lambda e, _toggle=_toggle: _toggle(),
                        style=ft.ButtonStyle(
                            color=ft.Colors.RED_400 if ativo else ft.Colors.GREEN_400,
                        ),
                    ),
                ],
            ))
        if not cats:
            tabela_cats_col.controls.append(
                ft.Text("Nenhuma categoria.", italic=True, color=ft.Colors.GREY_500)
            )

    def _adicionar_cat(e):
        nome = tf_cat_nome.value.strip()
        if not nome:
            return
        database.estoque_categoria_inserir(nome)
        tf_cat_nome.value = ""
        _refresh_cats()
        _refresh_dd_cat_prod()
        page.update()

    # ── Produtos (formulário) ───────────────────────────────────────────────

    _prod_id: dict = {"v": None}

    tf_prod_nome  = ft.TextField(label="Nome do produto", expand=True)
    dd_prod_cat   = ft.Dropdown(label="Categoria", width=200, options=[])
    dd_prod_un    = ft.Dropdown(
        label="Unidade", width=110,
        options=[ft.dropdown.Option(u) for u in _UNIDADES],
        value="un",
    )
    tf_prod_custo = ft.TextField(label="Preço de custo (R$)",
                                  keyboard_type=ft.KeyboardType.NUMBER, width=160, value="0.00")
    tf_prod_qtd   = ft.TextField(label="Quantidade inicial",
                                  keyboard_type=ft.KeyboardType.NUMBER, width=160, value="0")
    tf_prod_min   = ft.TextField(label="Qtd mínima (alerta)",
                                  keyboard_type=ft.KeyboardType.NUMBER, width=160, value="0")
    cb_prod_ativo = ft.Checkbox(label="Ativo", value=True)
    lbl_prod_tit  = ft.Text("Novo Produto", size=13, weight=ft.FontWeight.BOLD)
    txt_prod_err  = ft.Text("", color=ft.Colors.RED_400, size=12)

    tabela_prods_col = ft.Column(spacing=0)

    def _refresh_dd_cat_prod():
        cats_now = database.estoque_categoria_listar()
        dd_prod_cat.options = (
            [ft.dropdown.Option("", text="Sem categoria")]
            + [ft.dropdown.Option(str(c["id"]), text=c["nome"]) for c in cats_now]
        )

    def _limpar_prod():
        _prod_id["v"]      = None
        lbl_prod_tit.value = "Novo Produto"
        tf_prod_nome.value = ""
        dd_prod_cat.value  = ""
        dd_prod_un.value   = "un"
        tf_prod_custo.value = "0.00"
        tf_prod_qtd.value  = "0"
        tf_prod_min.value  = "0"
        cb_prod_ativo.value = True
        txt_prod_err.value = ""

    def _refresh_prods():
        prods = database.estoque_produto_listar(apenas_ativos=False)
        cab = ft.Row(spacing=0, controls=[
            ft.Container(expand=2, content=ft.Text("Nome",      size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=120, content=ft.Text("Categoria",size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=55,  content=ft.Text("Un.",      size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=85,  content=ft.Text("Qtd Mín.", size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=90,  content=ft.Text("Custo",    size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
            ft.Container(width=120, content=ft.Text("Ações",    size=11, color=ft.Colors.GREY_500, weight=ft.FontWeight.BOLD)),
        ])
        tabela_prods_col.controls = [cab, ft.Divider(height=1)]
        for p in prods:
            ativo = bool(p["ativo"])
            def _editar(pid=p["id"]):
                r = database.estoque_produto_buscar(pid)
                if not r:
                    return
                _prod_id["v"]       = pid
                lbl_prod_tit.value  = f"Editando: {r['nome']}"
                tf_prod_nome.value  = r["nome"]
                dd_prod_cat.value   = str(r["id_categoria"]) if r["id_categoria"] else ""
                dd_prod_un.value    = r["unidade"]
                tf_prod_custo.value = f"{r['preco_custo']:.2f}"
                tf_prod_qtd.value   = f"{r['quantidade_atual']:.3f}".rstrip("0").rstrip(".")
                tf_prod_min.value   = f"{r['quantidade_minima']:.3f}".rstrip("0").rstrip(".")
                cb_prod_ativo.value = bool(r["ativo"])
                txt_prod_err.value  = ""
                page.update()

            def _toggle_ativo(pid=p["id"], a=ativo):
                database.estoque_produto_atualizar(pid, ativo=0 if a else 1)
                _refresh_prods()
                page.update()

            tabela_prods_col.controls.append(ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(expand=2,  content=ft.Column(spacing=0, controls=[
                        ft.Text(p["nome"], size=12),
                        ft.Text("Inativo" if not ativo else "", size=10, color=ft.Colors.GREY_600),
                    ])),
                    ft.Container(width=120, content=ft.Text(p["nome_categoria"] or "—", size=12, color=ft.Colors.GREY_500)),
                    ft.Container(width=55,  content=ft.Text(p["unidade"], size=12)),
                    ft.Container(width=85,  content=ft.Text(_fmt_qtd(p["quantidade_minima"]), size=12)),
                    ft.Container(width=90,  content=ft.Text(_fmt_moeda(p["preco_custo"]), size=12)),
                    ft.Container(width=120, content=ft.Row(spacing=0, controls=[
                        ft.TextButton("Editar",   on_click=lambda e, _ed=_editar:   _ed()),
                        ft.TextButton(
                            "Inativar" if ativo else "Reativar",
                            on_click=lambda e, _tg=_toggle_ativo: _tg(),
                            style=ft.ButtonStyle(
                                color=ft.Colors.RED_400 if ativo else ft.Colors.GREEN_400,
                            ),
                        ),
                    ])),
                ],
            ))
        if not prods:
            tabela_prods_col.controls.append(
                ft.Text("Nenhum produto cadastrado.", italic=True, color=ft.Colors.GREY_500)
            )

    def _salvar_prod(e):
        nome = tf_prod_nome.value.strip()
        if not nome:
            txt_prod_err.value = "Nome é obrigatório."
            page.update()
            return
        id_cat  = int(dd_prod_cat.value) if dd_prod_cat.value else None
        un      = dd_prod_un.value or "un"
        custo   = _to_float(tf_prod_custo.value)
        qtd_ini = _to_float(tf_prod_qtd.value)
        qtd_min = _to_float(tf_prod_min.value)

        if _prod_id["v"] is None:
            database.estoque_produto_inserir(
                nome, id_cat, un, custo, qtd_ini, qtd_min,
            )
        else:
            database.estoque_produto_atualizar(
                _prod_id["v"],
                nome=nome, id_categoria=id_cat, unidade=un,
                preco_custo=custo,
                quantidade_atual=qtd_ini,
                quantidade_minima=qtd_min,
                ativo=int(cb_prod_ativo.value),
            )
        _limpar_prod()
        _refresh_prods()
        page.update()

    # Carga inicial do dropdown de categorias no formulário
    _refresh_dd_cat_prod()
    _refresh_cats()
    _refresh_prods()

    aba_cadastro = ft.Column(
        expand=True, spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            # Categorias
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=10, controls=[
                    ft.Text("Categorias", size=14, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row(spacing=12, controls=[
                        tf_cat_nome,
                        ft.ElevatedButton(
                            "Adicionar",
                            ft.Icons.ADD,
                            on_click=_adicionar_cat,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.INDIGO_600,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                    ]),
                    tabela_cats_col,
                ]),
            )),
            # Produtos — formulário
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(16),
                content=ft.Column(spacing=10, controls=[
                    lbl_prod_tit,
                    ft.Divider(height=1),
                    ft.Row([tf_prod_nome, dd_prod_cat], spacing=12),
                    ft.Row([dd_prod_un, tf_prod_custo, tf_prod_qtd, tf_prod_min], spacing=12),
                    cb_prod_ativo,
                    txt_prod_err,
                    ft.Row(spacing=8, controls=[
                        ft.ElevatedButton(
                            "Salvar Produto",
                            ft.Icons.SAVE,
                            on_click=_salvar_prod,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.TEAL_700,
                                color=ft.Colors.WHITE,
                            ),
                        ),
                        ft.TextButton(
                            "Cancelar",
                            on_click=lambda e: (_limpar_prod(), page.update()),
                        ),
                    ]),
                ]),
            )),
            # Produtos — tabela
            ft.Card(content=ft.Container(
                padding=ft.Padding.all(12),
                content=ft.Column(spacing=6, controls=[
                    ft.Text("Produtos Cadastrados", size=13, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row(scroll=ft.ScrollMode.AUTO, controls=[tabela_prods_col]),
                ]),
            )),
        ],
    )

    # ═══════════════════════════════════════════════════════════════════════
    #  TABS
    # ═══════════════════════════════════════════════════════════════════════

    tabs = ft.Tabs(
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(tabs=[
                    ft.Tab("Estoque"),
                    ft.Tab("Movimentações"),
                    ft.Tab("Cadastro"),
                ]),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        ft.Container(content=aba_estoque,       expand=True, padding=ft.Padding(top=12)),
                        ft.Container(content=aba_movimentacoes, expand=True, padding=ft.Padding(top=12)),
                        ft.Container(content=aba_cadastro,      expand=True, padding=ft.Padding(top=12)),
                    ],
                ),
            ],
        ),
        length=3,
    )

    # Carga inicial da aba Estoque
    _carregar_estoque()

    return ft.Column(
        controls=[
            ft.Text("Estoque", size=22, weight=ft.FontWeight.BOLD),
            tabs,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
