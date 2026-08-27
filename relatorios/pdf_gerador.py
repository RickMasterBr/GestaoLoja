"""
relatorios/pdf_gerador.py — Geração de relatórios PDF para impressão.
Abre o arquivo diretamente no visualizador padrão do Windows via os.startfile().
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime



# ── Carga preguicosa do reportlab ──────────────────────────────────
# O reportlab custa ~200 ms para importar e este modulo e importado no boot do
# app (6 views o importam no topo). _carregar() adia esse custo ate a primeira
# exportacao de PDF. Publica os nomes como globais do modulo para que os
# helpers e constantes continuem funcionando exatamente como antes.

_CARREGADO = False


def _carregar() -> None:
    """Importa o reportlab e monta paleta/estilos na primeira chamada."""
    global _CARREGADO
    if _CARREGADO:
        return
    global A4, landscape, colors, cm, SimpleDocTemplate, Table, TableStyle, Paragraph
    global Spacer, HRFlowable, ParagraphStyle, TA_CENTER, TA_RIGHT
    global _AZUL, _CINZA_SEC, _CINZA_ALT, _VERDE, _VERMELHO, _LARANJA
    global _BRANCO, _CINZA_TEXT, _CINZA_GRADE, _VERDE_CLARO, _LU
    global _ST_NOME_LOJA, _ST_SUBTITULO, _ST_DATA_HDR, _ST_SECAO_TXT
    global _ST_SUBSECAO, _ST_NOTA, _ST_RODAPE, _ST_SEM_DADOS

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    # ── Paleta de cores ───────────────────────────────────────────────────────────

    _AZUL        = colors.HexColor("#1a3a5c")
    _CINZA_SEC   = colors.HexColor("#2d2d2d")
    _CINZA_ALT   = colors.HexColor("#f5f5f5")
    _VERDE       = colors.HexColor("#2d7a2d")
    _VERMELHO    = colors.HexColor("#a02020")
    _LARANJA     = colors.HexColor("#c47000")
    _BRANCO      = colors.white
    _CINZA_TEXT  = colors.HexColor("#555555")
    _CINZA_GRADE = colors.HexColor("#cccccc")
    _VERDE_CLARO = colors.HexColor("#d4edda")

    # Largura útil: A4 com margens 2 cm de cada lado
    _LU = A4[0] - 4 * cm   # ≈ 481.9 pt


    # ── Estilos de parágrafo ──────────────────────────────────────────────────────

    _ST_NOME_LOJA = ParagraphStyle(
        "nome_loja", fontName="Helvetica-Bold", fontSize=18,
        alignment=TA_CENTER, textColor=_AZUL, spaceAfter=4,
    )
    _ST_SUBTITULO = ParagraphStyle(
        "subtitulo", fontName="Helvetica", fontSize=12,
        alignment=TA_CENTER, textColor=_CINZA_TEXT, spaceAfter=2,
    )
    _ST_DATA_HDR = ParagraphStyle(
        "data_hdr", fontName="Helvetica", fontSize=11,
        alignment=TA_CENTER, textColor=_CINZA_TEXT, spaceAfter=6,
    )
    _ST_SECAO_TXT = ParagraphStyle(
        "secao_txt", fontName="Helvetica-Bold", fontSize=11,
        textColor=_BRANCO, leading=16, leftIndent=6,
    )
    _ST_SUBSECAO = ParagraphStyle(
        "subsecao", fontName="Helvetica-Bold", fontSize=10,
        textColor=_CINZA_SEC, spaceBefore=6, spaceAfter=3,
    )
    _ST_NOTA = ParagraphStyle(
        "nota", fontName="Helvetica-Oblique", fontSize=9,
        textColor=_CINZA_TEXT, spaceAfter=4,
    )
    _ST_RODAPE = ParagraphStyle(
        "rodape", fontName="Helvetica", fontSize=9,
        alignment=TA_RIGHT, textColor=_CINZA_TEXT,
    )
    _ST_SEM_DADOS = ParagraphStyle(
        "sem_dados", fontName="Helvetica-Oblique", fontSize=10,
        textColor=_CINZA_TEXT, spaceAfter=6, leftIndent=6,
    )

    _CARREGADO = True


_PLAT_NOMES = {
    "iFood1": "iFood L1",
    "iFood2": "iFood L2",
    "99Food": "99Food",
    "Keeta":  "Keeta",
}


# ── Auxiliares ────────────────────────────────────────────────────────────────

def _r(valor: float) -> str:
    return f"R$ {valor:.2f}"


def _secao(texto: str) -> Table:
    """Cabeçalho de seção com fundo cinza escuro e texto branco."""
    t = Table([[Paragraph(texto, _ST_SECAO_TXT)]], colWidths=[_LU])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _CINZA_SEC),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
    ]))
    return t


def _sp() -> Spacer:
    return Spacer(1, 8)


def _cab_style() -> list:
    """Comandos de estilo padrão para a linha de cabeçalho (linha 0)."""
    return [
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _BRANCO),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
    ]


def _body_style() -> list:
    """Comandos de estilo padrão para o corpo da tabela."""
    return [
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
    ]


def _alt_rows(start: int, end: int) -> tuple:
    """Linhas alternadas branco/cinza claro."""
    return ("ROWBACKGROUNDS", (0, start), (-1, end), [_BRANCO, _CINZA_ALT])


def _total_style(row_idx: int) -> list:
    """Estilo para linha de totais."""
    return [
        ("FONTNAME",   (0, row_idx), (-1, row_idx), "Helvetica-Bold"),
        ("BACKGROUND", (0, row_idx), (-1, row_idx), _CINZA_ALT),
    ]


def _iso_para_br(iso: str) -> str:
    try:
        a, m, d = iso.split("-")
        return f"{d}/{m}/{a}"
    except Exception:
        return iso


def _rodape(story: list) -> None:
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_CINZA_TEXT))
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Gerado em {agora}", _ST_RODAPE))


# ── Bloco de plataforma (compartilhado diário/período) ────────────────────────

def _bloco_plataforma(story: list, nome_plat: str, d: dict,
                      com_repasse: bool = False) -> None:
    story.append(_sp())
    story.append(Paragraph(_PLAT_NOMES.get(nome_plat, nome_plat), _ST_SUBSECAO))

    cp  = d.get("comissao_pct", 0.0)
    tp  = d.get("tx_trans_pct", 0.0)
    spp = d.get("subsidio_pp",  0.0)

    lin = [
        [f"Pedidos: {d.get('qtd',0)}  |  Bruto total",  _r(d.get("bruto", 0.0))],
        ["Pago online (plataforma repassa)",               _r(d.get("bruto_online", 0.0))],
        [f"  (-) Comissão {cp:.1f}% s/ online",           _r(d.get("comissao_online", 0.0))],
        [f"  (-) Taxa transação {tp:.1f}% s/ online",     _r(d.get("tx_trans", 0.0))],
        [f"  (+) Subsídio R$ {spp:.2f}/ped",              _r(d.get("subsidio", 0.0))],
        ["Líquido Estimado",                               _r(d.get("liquido", 0.0))],
    ]
    if com_repasse:
        lin.append([f"Previsão de repasse: {d.get('dt_repasse', '—')}", ""])

    liq_idx = 5   # índice da linha "Líquido Estimado"
    n = len(lin)

    cmds = [
        ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ALIGN",          (1, 0), (1, -1), "RIGHT"),
        ("ALIGN",          (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        _alt_rows(0, liq_idx - 1),
        ("BACKGROUND",     (0, liq_idx), (-1, liq_idx), _VERDE_CLARO),
        ("FONTNAME",       (0, liq_idx), (-1, liq_idx), "Helvetica-Bold"),
        ("TEXTCOLOR",      (0, liq_idx), (-1, liq_idx), _VERDE),
        ("TEXTCOLOR",      (0, 2), (1, 3), _VERMELHO),
        ("GRID",           (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
    ]
    if com_repasse:
        cmds += [
            ("FONTNAME",  (0, n-1), (-1, n-1), "Helvetica-Oblique"),
            ("TEXTCOLOR", (0, n-1), (0, n-1), colors.HexColor("#b87000")),
        ]

    t = Table(lin, colWidths=[_LU*0.70, _LU*0.30])
    t.setStyle(TableStyle(cmds))
    story.append(t)


# ── Gerador diário ────────────────────────────────────────────────────────────

def gerar_pdf_diario(data_iso: str, dados: dict) -> str:
    """Gera o PDF do relatório diário. Retorna o caminho do arquivo temporário."""
    _carregar()
    caminho = os.path.join(tempfile.gettempdir(), f"relatorio_{data_iso}.pdf")

    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    # ── CABEÇALHO ─────────────────────────────────────────────────────────
    story.append(Paragraph(dados.get("nome_loja", "Gestão Loja"), _ST_NOME_LOJA))
    story.append(Paragraph("Relatório de Fechamento Diário", _ST_SUBTITULO))
    story.append(Paragraph(dados.get("data_br", _iso_para_br(data_iso)), _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=10))

    # ── RESUMO POR CANAL ──────────────────────────────────────────────────
    story.append(_secao("Resumo por Canal"))
    story.append(_sp())
    canais = dados.get("canais", [])
    if canais:
        total_q = sum(r.get("qtd", 0) for r in canais)
        total_v = sum(r.get("valor_liquido", 0.0) for r in canais)
        lin_c   = [[r.get("canal_amigavel", r.get("canal", "")),
                    str(r.get("qtd", 0)),
                    _r(r.get("valor_liquido", 0.0))] for r in canais]
        lin_c.append(["TOTAL", str(total_q), _r(total_v)])
        cab_c   = ["Canal", "Qtd Pedidos", "Valor Total"]
        n_total = len(lin_c)   # índice da linha TOTAL (0-based no corpo = n_total-1; na tabela = n_total)
        t_c = Table([cab_c] + lin_c,
                    colWidths=[_LU*0.55, _LU*0.20, _LU*0.25])
        t_c.setStyle(TableStyle(
            _cab_style() + _body_style() + [
                _alt_rows(1, n_total - 1),
            ] + _total_style(n_total)
        ))
        story.append(t_c)
    else:
        story.append(Paragraph("Sem registros para esta data.", _ST_SEM_DADOS))

    # ── PAGAMENTOS ────────────────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Pagamentos"))
    story.append(_sp())
    story.append(Paragraph("VA/VR = Benefício · Voucher/Cortesia excluídos", _ST_NOTA))
    pagamentos = dados.get("pagamentos", [])
    if pagamentos:
        total_p = sum(r.get("total", 0.0) for r in pagamentos)
        lin_p   = [[r.get("metodo", ""), r.get("tipo", ""), _r(r.get("total", 0.0))]
                   for r in pagamentos]
        lin_p.append(["TOTAL", "", _r(total_p)])
        cab_p   = ["Método", "Tipo", "Valor Total"]
        n_total = len(lin_p)
        t_p = Table([cab_p] + lin_p,
                    colWidths=[_LU*0.40, _LU*0.30, _LU*0.30])
        t_p.setStyle(TableStyle(
            _cab_style() + _body_style() + [
                _alt_rows(1, n_total - 1),
            ] + _total_style(n_total)
        ))
        story.append(t_p)
    else:
        story.append(Paragraph("Sem registros para esta data.", _ST_SEM_DADOS))

    # ── DETALHAMENTO PLATAFORMAS ──────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Detalhamento Plataformas"))
    plataformas  = dados.get("plataformas", {})
    alguma_plat  = False
    for nome_plat in ["iFood1", "iFood2", "99Food", "Keeta"]:
        d = plataformas.get(nome_plat, {})
        if not d.get("qtd", 0):
            continue
        alguma_plat = True
        _bloco_plataforma(story, nome_plat, d, com_repasse=False)
    if not alguma_plat:
        story.append(_sp())
        story.append(Paragraph("Sem registros para esta data.", _ST_SEM_DADOS))

    # ── ENTREGADORES ─────────────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Entregadores"))
    story.append(_sp())
    entregadores = dados.get("entregadores", [])
    if entregadores:
        cab_e = ["Nome", "Entregas", "Soma Taxas", "Diária",
                 "Extras", "Vales", "Total a Pagar"]
        cw_e  = [_LU*0.22, _LU*0.10, _LU*0.13, _LU*0.12,
                 _LU*0.10, _LU*0.10, _LU*0.23]
        lin_e = [[r.get("nome", ""),
                  str(r.get("total_entregas", 0)),
                  _r(r.get("soma_taxas", 0.0)),
                  _r(r.get("diaria", 0.0)),
                  _r(r.get("corridas_extras", 0.0)),
                  _r(r.get("vales", 0.0)),
                  _r(r.get("total_liquido", 0.0))]
                 for r in entregadores]
        n = len(lin_e)
        verde_cmds = [("TEXTCOLOR", (6, i+1), (6, i+1), _VERDE)
                      for i in range(n)]
        verde_cmds += [("FONTNAME", (6, i+1), (6, i+1), "Helvetica-Bold")
                       for i in range(n)]
        t_e = Table([cab_e] + lin_e, colWidths=cw_e)
        t_e.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + verde_cmds
        ))
        story.append(t_e)
    else:
        story.append(Paragraph("Sem registros para esta data.", _ST_SEM_DADOS))

    # ── FECHAMENTO DE CAIXA ───────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Fechamento de Caixa"))
    story.append(_sp())
    cx  = dados.get("caixa", {})
    dif = cx.get("diferenca", 0.0)
    cor_dif = _VERDE if dif == 0 else (_VERMELHO if dif < 0 else _LARANJA)
    lin_cx = [
        ["Troco Inicial",        _r(cx.get("troco_inicial", 0.0))],
        ["Entradas Espécie",     _r(cx.get("total_especie_entradas", 0.0))],
        ["Saídas Espécie",       _r(cx.get("total_especie_saidas", 0.0))],
        ["Saldo Teórico",        _r(cx.get("saldo_teorico", 0.0))],
        ["Saldo Real (gaveta)",  _r(cx.get("saldo_gaveta_real", 0.0))],
        ["Diferença",            _r(dif)],
    ]
    t_cx = Table(lin_cx, colWidths=[_LU*0.60, _LU*0.40])
    t_cx.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME",       (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",      (0, -1), (-1, -1), cor_dif),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ALIGN",          (1, 0), (1, -1), "RIGHT"),
        ("ALIGN",          (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        _alt_rows(0, 5),
        ("GRID",           (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
    ]))
    story.append(t_cx)

    # ── MOVIMENTAÇÕES DO DIA ──────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Movimentações do Dia"))
    story.append(_sp())
    extras = dados.get("extras", [])
    if extras:
        cab_x = ["Pessoa", "Categoria", "Fluxo", "Método", "Valor", "Obs"]
        cw_x  = [_LU*0.17, _LU*0.15, _LU*0.09, _LU*0.15, _LU*0.12, _LU*0.32]
        lin_x = [[r.get("nome_pessoa", "—"), r.get("categoria", ""),
                  r.get("fluxo", ""), r.get("metodo", "—"),
                  _r(r.get("valor", 0.0)), r.get("obs", "")]
                 for r in extras]
        fluxo_cmds = []
        for i, r in enumerate(extras):
            f = r.get("fluxo", "")
            c = _VERDE if f == "ENTRADA" else (_VERMELHO if f == "SAIDA" else _CINZA_TEXT)
            fluxo_cmds.append(("TEXTCOLOR", (2, i+1), (2, i+1), c))
        n = len(lin_x)
        t_x = Table([cab_x] + lin_x, colWidths=cw_x)
        t_x.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + fluxo_cmds
        ))
        story.append(t_x)
    else:
        story.append(Paragraph("Sem registros para esta data.", _ST_SEM_DADOS))

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador período ───────────────────────────────────────────────────────────

def gerar_pdf_periodo(data_ini: str, data_fim: str, dados: dict) -> str:
    """Gera o PDF do relatório de período. Retorna o caminho do arquivo temporário."""
    _carregar()
    caminho = os.path.join(
        tempfile.gettempdir(),
        f"relatorio_{data_ini}_{data_fim}.pdf",
    )

    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    # ── CABEÇALHO ─────────────────────────────────────────────────────────
    story.append(Paragraph(dados.get("nome_loja", "Gestão Loja"), _ST_NOME_LOJA))
    story.append(Paragraph("Relatório de Período", _ST_SUBTITULO))
    story.append(Paragraph(
        f"De {_iso_para_br(data_ini)} a {_iso_para_br(data_fim)}", _ST_DATA_HDR,
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=10))

    # ── RESUMO GERAL ──────────────────────────────────────────────────────
    story.append(_secao("Resumo Geral"))
    story.append(_sp())
    rg = dados.get("resumo_geral", {})
    lin_rg = [
        ["Total de Pedidos",  str(rg.get("total_pedidos", 0))],
        ["Valor Bruto",       _r(rg.get("valor_bruto", 0.0))],
        ["Faturamento Real",  _r(rg.get("fat_real", 0.0))],
        ["Total Cortesias",   _r(rg.get("total_cortesias", 0.0))],
        ["Taxas de Entrega",  _r(rg.get("total_taxas", 0.0))],
    ]
    t_rg = Table(lin_rg, colWidths=[_LU*0.60, _LU*0.40])
    t_rg.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME",       (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 10),
        ("ALIGN",          (1, 0), (1, -1), "RIGHT"),
        ("ALIGN",          (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        _alt_rows(0, 4),
        ("GRID",           (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
        ("TEXTCOLOR",      (1, 2), (1, 2), _VERDE),
        ("TEXTCOLOR",      (1, 3), (1, 3), _LARANJA),
        ("TEXTCOLOR",      (1, 4), (1, 4), colors.HexColor("#007070")),
    ]))
    story.append(t_rg)

    # ── RESUMO POR CANAL ──────────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Resumo por Canal"))
    story.append(_sp())
    canais = dados.get("canais", [])
    if canais:
        total_q = sum(r.get("qtd", 0) for r in canais)
        total_v = sum(r.get("valor_total", r.get("valor_liquido", 0.0)) for r in canais)
        lin_c   = [[r.get("canal_amigavel", r.get("canal", "")),
                    str(r.get("qtd", 0)),
                    _r(r.get("valor_total", r.get("valor_liquido", 0.0)))]
                   for r in canais]
        lin_c.append(["TOTAL", str(total_q), _r(total_v)])
        cab_c   = ["Canal", "Qtd Pedidos", "Valor Total"]
        n_total = len(lin_c)
        t_c = Table([cab_c] + lin_c,
                    colWidths=[_LU*0.55, _LU*0.20, _LU*0.25])
        t_c.setStyle(TableStyle(
            _cab_style() + _body_style() + [
                _alt_rows(1, n_total - 1),
            ] + _total_style(n_total)
        ))
        story.append(t_c)
    else:
        story.append(Paragraph("Sem registros para este período.", _ST_SEM_DADOS))

    # ── PAGAMENTOS ────────────────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Pagamentos"))
    story.append(_sp())
    story.append(Paragraph("VA/VR = Benefício · Voucher/Cortesia excluídos", _ST_NOTA))
    pagamentos = dados.get("pagamentos", [])
    if pagamentos:
        total_p = sum(r.get("total", 0.0) for r in pagamentos)
        lin_p   = [[r.get("metodo", ""), r.get("tipo", ""), _r(r.get("total", 0.0))]
                   for r in pagamentos]
        lin_p.append(["TOTAL", "", _r(total_p)])
        cab_p   = ["Método", "Tipo", "Valor Total"]
        n_total = len(lin_p)
        t_p = Table([cab_p] + lin_p,
                    colWidths=[_LU*0.40, _LU*0.30, _LU*0.30])
        t_p.setStyle(TableStyle(
            _cab_style() + _body_style() + [
                _alt_rows(1, n_total - 1),
            ] + _total_style(n_total)
        ))
        story.append(t_p)
    else:
        story.append(Paragraph("Sem registros para este período.", _ST_SEM_DADOS))

    # ── DETALHAMENTO PLATAFORMAS ──────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Detalhamento Plataformas"))
    plataformas = dados.get("plataformas", {})
    alguma_plat = False
    for nome_plat in ["iFood1", "iFood2", "99Food", "Keeta"]:
        d = plataformas.get(nome_plat, {})
        if not d.get("qtd", 0):
            continue
        alguma_plat = True
        _bloco_plataforma(story, nome_plat, d, com_repasse=True)
    if not alguma_plat:
        story.append(_sp())
        story.append(Paragraph("Sem registros para este período.", _ST_SEM_DADOS))

    # ── ENTREGADORES ─────────────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Entregadores"))
    story.append(_sp())
    entregadores = dados.get("entregadores", [])
    if entregadores:
        cab_e = ["Nome", "Entregas", "Soma Taxas", "Diárias",
                 "Extras", "Vales", "Total a Pagar"]
        cw_e  = [_LU*0.22, _LU*0.10, _LU*0.13, _LU*0.12,
                 _LU*0.10, _LU*0.10, _LU*0.23]
        lin_e = [[r.get("nome", ""),
                  str(r.get("total_entregas", 0)),
                  _r(r.get("soma_taxas", 0.0)),
                  _r(r.get("total_diarias", r.get("diaria", 0.0))),
                  _r(r.get("corridas_extras", 0.0)),
                  _r(r.get("vales", 0.0)),
                  _r(r.get("total_liquido", 0.0))]
                 for r in entregadores]
        n = len(lin_e)
        verde_cmds = [("TEXTCOLOR", (6, i+1), (6, i+1), _VERDE) for i in range(n)]
        verde_cmds += [("FONTNAME",  (6, i+1), (6, i+1), "Helvetica-Bold") for i in range(n)]
        t_e = Table([cab_e] + lin_e, colWidths=cw_e)
        t_e.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + verde_cmds
        ))
        story.append(t_e)
    else:
        story.append(Paragraph("Sem registros para este período.", _ST_SEM_DADOS))

    # ── PROJEÇÃO DE REPASSES ──────────────────────────────────────────────
    story.append(_sp())
    story.append(_secao("Projeção de Repasses"))
    story.append(_sp())
    cab_rep = ["Plataforma", "Líquido Estimado", "Data Prevista"]
    lin_rep = [
        [_PLAT_NOMES.get(np, np),
         _r(plataformas.get(np, {}).get("liquido", 0.0)),
         plataformas.get(np, {}).get("dt_repasse", "—")]
        for np in ["iFood1", "iFood2", "99Food", "Keeta"]
    ]
    t_rep = Table([cab_rep] + lin_rep,
                  colWidths=[_LU*0.35, _LU*0.35, _LU*0.30])
    t_rep.setStyle(TableStyle(
        _cab_style() + _body_style() + [_alt_rows(1, len(lin_rep))]
    ))
    story.append(t_rep)

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador fluxo de caixa ────────────────────────────────────────────────────

def gerar_pdf_fluxo_caixa(titulo: str, ini_br: str, fim_br: str,
                           lancamentos: list) -> str:
    """Gera PDF do extrato de fluxo de caixa. Retorna o caminho do arquivo."""
    _carregar()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(tempfile.gettempdir(), f"fluxo_caixa_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    periodo_txt = ini_br if ini_br == fim_br else f"{ini_br} a {fim_br}"
    story.append(Paragraph("Gestão Loja", _ST_NOME_LOJA))
    story.append(Paragraph("Fluxo de Caixa", _ST_SUBTITULO))
    story.append(Paragraph(f"{titulo} — {periodo_txt}", _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=10))

    # Resumo
    story.append(_secao("Resumo"))
    story.append(_sp())
    total_e = sum((r.get("entrada") or 0.0) for r in lancamentos)
    total_s = sum((r.get("saida")   or 0.0) for r in lancamentos)
    saldo_f = total_e - total_s
    cor_sf  = _VERDE if saldo_f >= 0 else _VERMELHO
    t_res = Table(
        [["Total Entradas", _r(total_e)],
         ["Total Saídas",   _r(total_s)],
         ["Saldo Final",    _r(saldo_f)]],
        colWidths=[_LU * 0.60, _LU * 0.40],
    )
    t_res.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",       (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ALIGN",          (1, 0), (1, -1), "RIGHT"),
        ("ALIGN",          (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        _alt_rows(0, 2),
        ("TEXTCOLOR",      (0, 0), (1, 0), _VERDE),
        ("TEXTCOLOR",      (0, 1), (1, 1), _VERMELHO),
        ("TEXTCOLOR",      (0, 2), (1, 2), cor_sf),
        ("GRID",           (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
    ]))
    story.append(t_res)

    # Lançamentos
    story.append(_sp())
    story.append(_secao("Lançamentos"))
    story.append(_sp())
    if lancamentos:
        cab = ["Data", "Hora", "Tipo", "Descrição", "Método",
               "Entrada", "Saída", "Saldo"]
        cw  = [_LU*0.10, _LU*0.07, _LU*0.10, _LU*0.22, _LU*0.12,
               _LU*0.12, _LU*0.12, _LU*0.15]
        rows = []
        color_cmds = []
        saldo = 0.0
        for i, r in enumerate(lancamentos):
            entrada = r.get("entrada") or 0.0
            saida   = r.get("saida")   or 0.0
            saldo  += entrada - saida
            ri = i + 1
            rows.append([
                r.get("data", ""),
                r.get("hora", "") or "",
                r.get("tipo", ""),
                r.get("descricao", "") or "",
                r.get("metodo", "") or "",
                _r(entrada) if entrada else "",
                _r(saida)   if saida   else "",
                _r(saldo),
            ])
            if entrada > 0:
                color_cmds.append(("TEXTCOLOR", (5, ri), (5, ri), _VERDE))
            if saida > 0:
                color_cmds.append(("TEXTCOLOR", (6, ri), (6, ri), _VERMELHO))
            color_cmds.append((
                "TEXTCOLOR", (7, ri), (7, ri),
                _VERDE if saldo >= 0 else _VERMELHO,
            ))
        n = len(rows)
        t = Table([cab] + rows, colWidths=cw)
        t.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + color_cmds
        ))
        story.append(t)
    else:
        story.append(Paragraph("Sem lançamentos para o período.", _ST_SEM_DADOS))

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador histórico de divergências ─────────────────────────────────────────

def gerar_pdf_divergencias(ini_br: str, fim_br: str, registros: list) -> str:
    """Gera PDF do histórico de divergências de fechamento."""
    _carregar()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(tempfile.gettempdir(), f"divergencias_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    story.append(Paragraph("Gestão Loja", _ST_NOME_LOJA))
    story.append(Paragraph("Histórico de Divergências de Fechamento", _ST_SUBTITULO))
    story.append(Paragraph(f"De {ini_br} a {fim_br}", _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=10))

    story.append(_secao("Fechamentos"))
    story.append(_sp())
    if registros:
        cab = ["Data", "Saldo Teórico", "Saldo Real", "Diferença", "Observação"]
        cw  = [_LU*0.12, _LU*0.18, _LU*0.16, _LU*0.16, _LU*0.38]
        rows = []
        color_cmds = []
        for i, r in enumerate(registros):
            dif = r.get("diferenca") or 0.0
            rows.append([
                _iso_para_br(r.get("data", "")),
                _r(r.get("saldo_teorico") or 0.0),
                _r(r.get("saldo_gaveta_real") or 0.0),
                _r(dif),
                r.get("obs_fechamento") or "",
            ])
            ri = i + 1
            if abs(dif) <= 0.001:
                color_cmds.append(("TEXTCOLOR", (3, ri), (3, ri), _VERDE))
            elif dif < 0:
                color_cmds.append(("TEXTCOLOR",  (3, ri), (3, ri), _VERMELHO))
                color_cmds.append(("BACKGROUND", (0, ri), (-1, ri),
                                   colors.HexColor("#fff0f0")))
            else:
                color_cmds.append(("TEXTCOLOR", (3, ri), (3, ri), _LARANJA))
        n = len(rows)
        t = Table([cab] + rows, colWidths=cw)
        t.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + color_cmds
        ))
        story.append(t)
    else:
        story.append(Paragraph("Sem registros para este período.", _ST_SEM_DADOS))

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador holerite ──────────────────────────────────────────────────────────

def gerar_pdf_holerite(nome: str, mes_ano: str, dados: dict) -> str:
    """Gera PDF do holerite de um funcionário."""
    _carregar()
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arq = nome.replace(" ", "_").lower()
    caminho  = os.path.join(tempfile.gettempdir(), f"holerite_{nome_arq}_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    story.append(Paragraph("Gestão Loja", _ST_NOME_LOJA))
    story.append(Paragraph("Holerite", _ST_SUBTITULO))
    story.append(Paragraph(f"{nome} — {mes_ano}", _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=10))

    # Resumo
    story.append(_secao("Resumo"))
    story.append(_sp())
    resumo = dados.get("resumo", [])
    if resumo:
        lin_r = [[r.get("descricao", ""), _r(r.get("valor", 0.0))] for r in resumo]
        n = len(lin_r)
        cmds = [
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
            ("ALIGN",         (0, 0), (0, -1), "LEFT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            _alt_rows(0, n - 1),
            ("GRID",          (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
        ]
        for i, r in enumerate(resumo):
            tipo = r.get("tipo", "")
            if tipo == "desconto":
                cmds.append(("TEXTCOLOR", (0, i), (1, i), _VERMELHO))
            elif tipo == "total":
                cmds.append(("FONTNAME",   (0, i), (-1, i), "Helvetica-Bold"))
                cmds.append(("TEXTCOLOR",  (0, i), (1,  i), _VERDE))
                cmds.append(("BACKGROUND", (0, i), (-1, i), _CINZA_ALT))
        t = Table(lin_r, colWidths=[_LU * 0.65, _LU * 0.35])
        t.setStyle(TableStyle(cmds))
        story.append(t)

    # Vales
    story.append(_sp())
    story.append(_secao("Detalhamento Vales"))
    story.append(_sp())
    vales = dados.get("vales", [])
    if vales:
        cab_v = ["Data", "Valor", "Observação"]
        lin_v = [[r.get("data", ""), _r(r.get("valor", 0.0)), r.get("obs", "")]
                 for r in vales]
        n = len(lin_v)
        t_v = Table([cab_v] + lin_v, colWidths=[_LU*0.18, _LU*0.20, _LU*0.62])
        t_v.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)]
        ))
        story.append(t_v)
    else:
        story.append(Paragraph("Nenhum vale registrado.", _ST_SEM_DADOS))

    # Consumos
    story.append(_sp())
    story.append(_secao("Detalhamento Consumos"))
    story.append(_sp())
    consumos = dados.get("consumos", [])
    if consumos:
        cab_c = ["Data", "Valor Original", "Desconto 80%", "Observação"]
        lin_c = [[r.get("data", ""),
                  _r(r.get("valor_original", 0.0)),
                  _r(r.get("desconto_80", 0.0)),
                  r.get("obs", "")]
                 for r in consumos]
        n = len(lin_c)
        t_c = Table([cab_c] + lin_c,
                    colWidths=[_LU*0.15, _LU*0.20, _LU*0.20, _LU*0.45])
        t_c.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)]
        ))
        story.append(t_c)
    else:
        story.append(Paragraph("Nenhum consumo registrado.", _ST_SEM_DADOS))

    # Ocorrências de Escala
    story.append(_sp())
    story.append(_secao("Ocorrências de Escala"))
    story.append(_sp())
    ocorrencias = dados.get("ocorrencias", [])
    if ocorrencias:
        cab_o = ["Data", "Tipo", "Impacto"]
        lin_o = [[r.get("data", ""), r.get("tipo", ""), r.get("impacto", "")]
                 for r in ocorrencias]
        n = len(lin_o)
        t_o = Table([cab_o] + lin_o, colWidths=[_LU*0.18, _LU*0.32, _LU*0.50])
        t_o.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)]
        ))
        story.append(t_o)
    else:
        story.append(Paragraph("Nenhuma ocorrência registrada.", _ST_SEM_DADOS))

    # Controle de Ponto
    ponto = dados.get("ponto", [])
    if ponto:
        story.append(_sp())
        story.append(_secao("Controle de Ponto"))
        story.append(_sp())
        cab_p = ["Data", "Entrada", "Saída", "Intervalo", "H.Brutas", "H.Líq.", "Extras/Falt."]
        lin_p = [[r.get("data", ""), r.get("entrada", ""), r.get("saida", ""),
                  r.get("intervalo", "—"),
                  r.get("horas_brutas", ""), r.get("horas_liquidas", ""),
                  str(r.get("extras_faltantes", ""))]
                 for r in ponto]
        n = len(lin_p)
        color_pt = []
        for i, r in enumerate(ponto):
            ev = str(r.get("extras_faltantes", ""))
            ri = i + 1
            if ev.startswith("+"):
                color_pt.append(("TEXTCOLOR", (6, ri), (6, ri), _VERDE))
            elif ev.startswith("-") or "FALTA" in ev.upper():
                color_pt.append(("TEXTCOLOR", (6, ri), (6, ri), _VERMELHO))
            elif "FOLGA" in ev.upper() or "FERIADO" in ev.upper():
                color_pt.append(("TEXTCOLOR", (6, ri), (6, ri), _AZUL))
        cw_p = [_LU*0.18, _LU*0.12, _LU*0.12, _LU*0.16, _LU*0.12, _LU*0.12, _LU*0.18]
        t_p = Table([cab_p] + lin_p, colWidths=cw_p)
        t_p.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + color_pt + [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        ))
        story.append(t_p)

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador Espelho de Ponto Individual ───────────────────────────────────────

def gerar_pdf_espelho_ponto(nome: str, mes_ano: str, dados: dict) -> str:
    """Gera PDF do espelho de ponto individual do funcionário para todo o mês."""
    _carregar()
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arq = nome.replace(" ", "_").lower()
    caminho  = os.path.join(tempfile.gettempdir(), f"ponto_{nome_arq}_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    info = dados.get("info_func", {})
    tipo_sal = info.get("tipo_salario", "")
    carga_h  = info.get("carga_horaria", 8.0)

    story.append(Paragraph("Gestão Loja", _ST_NOME_LOJA))
    story.append(Paragraph("Espelho de Ponto Individual", _ST_SUBTITULO))
    sub_info = f"Funcionário: <b>{nome}</b> &nbsp;|&nbsp; Período: <b>{mes_ano}</b> &nbsp;|&nbsp; Carga: <b>{carga_h:.1f}h/dia</b>"
    story.append(Paragraph(sub_info, _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=8))

    # Quadro de Resumo de Horas
    resumo = dados.get("resumo", {})
    if resumo:
        story.append(_secao("Resumo de Horas do Período"))
        story.append(_sp())
        lin_res = [
            ["Dias c/ Ponto:", str(resumo.get("dias_com_ponto", 0)),
             "Jornadas Completas:", str(resumo.get("dias_completos", 0))],
            ["Total Horas Líquidas:", f"{resumo.get('total_horas_liquidas', 0.0):.1f}h",
             "Saldo Horas Extras:", f"+{resumo.get('total_horas_extras', 0.0):.1f}h"],
            ["Horas Faltantes:", f"-{resumo.get('total_horas_faltantes', 0.0):.1f}h",
             "Valor Est. Extras:", f"R$ {resumo.get('valor_total_extras', 0.0):.2f}" if resumo.get('valor_total_extras') else "—"],
        ]
        t_res = Table(lin_res, colWidths=[_LU*0.25, _LU*0.25, _LU*0.25, _LU*0.25])
        t_res.setStyle(TableStyle([
            ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",       (0, 0), (-1, -1), 9),
            ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",       (2, 0), (2, -1), "Helvetica-Bold"),
            ("ALIGN",          (1, 0), (1, -1), "LEFT"),
            ("ALIGN",          (3, 0), (3, -1), "LEFT"),
            ("TOPPADDING",     (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
            ("LEFTPADDING",    (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
            _alt_rows(0, 2),
            ("GRID",           (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
            ("TEXTCOLOR",      (3, 1), (3, 1), _VERDE),
            ("TEXTCOLOR",      (1, 2), (1, 2), _VERMELHO),
        ]))
        story.append(t_res)
        story.append(_sp())

    # Tabela Detalhada de Ponto
    registros = dados.get("registros", [])
    if registros:
        story.append(_secao("Registros de Ponto Diário"))
        story.append(_sp())
        cab_p = ["Data", "Entrada", "Saída", "Intervalo", "H.Brutas", "H.Líq.", "Situação / Saldo"]
        lin_p = [
            [
                r.get("data", ""),
                r.get("entrada", "—"),
                r.get("saida", "—"),
                r.get("intervalo", "—"),
                r.get("horas_brutas", "—"),
                r.get("horas_liquidas", "—"),
                str(r.get("extras_faltantes", "—")),
            ]
            for r in registros
        ]
        n = len(lin_p)
        color_pt = []
        for i, r in enumerate(registros):
            ev = str(r.get("extras_faltantes", ""))
            ri = i + 1
            if ev.startswith("+"):
                color_pt.append(("TEXTCOLOR", (6, ri), (6, ri), _VERDE))
            elif ev.startswith("-") or "FALTA" in ev.upper():
                color_pt.append(("TEXTCOLOR", (6, ri), (6, ri), _VERMELHO))
            elif "FOLGA" in ev.upper() or "FERIADO" in ev.upper():
                color_pt.append(("TEXTCOLOR", (6, ri), (6, ri), _AZUL))
        cw_p = [_LU*0.20, _LU*0.12, _LU*0.12, _LU*0.16, _LU*0.12, _LU*0.12, _LU*0.16]
        t_p = Table([cab_p] + lin_p, colWidths=cw_p)
        t_p.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + color_pt + [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        ))
        story.append(t_p)
    else:
        story.append(Paragraph("Sem registros de ponto para este período.", _ST_SEM_DADOS))

    # Bloco de declaração e assinaturas
    story.append(Spacer(1, 14))
    st_declaracao = ParagraphStyle(
        "decl", fontName="Helvetica", fontSize=8,
        textColor=_CINZA_TEXT, alignment=TA_CENTER, spaceAfter=20,
    )
    story.append(Paragraph(
        "Reconheço a exatidão dos horários e frequências constantes deste espelho de ponto referente ao período indicado.",
        st_declaracao,
    ))

    # Assinaturas lado a lado
    lin_ass = [
        ["____________________________________________", "____________________________________________"],
        [f"{nome}\nEmpregado(a)", "Gestão Loja\nEmpregador / Responsável"],
        ["Data: _____ / _____ / _________", "Data: _____ / _____ / _________"],
    ]
    t_ass = Table(lin_ass, colWidths=[_LU*0.50, _LU*0.50])
    t_ass.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_ass)

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador entregadores ──────────────────────────────────────────────────────


def gerar_pdf_entregadores(data_br: str, dados: dict) -> str:
    """Gera PDF do painel de entregadores (dia + semana)."""
    _carregar()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(tempfile.gettempdir(), f"entregadores_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    story.append(Paragraph("Gestão Loja", _ST_NOME_LOJA))
    story.append(Paragraph("Painel de Entregadores", _ST_SUBTITULO))
    story.append(Paragraph(data_br, _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=10))

    cab_e = ["Nome", "Entregas", "Soma Taxas", "Diária",
             "Corridas Extra", "Vales", "Total a Pagar"]
    cw_e  = [_LU*0.20, _LU*0.10, _LU*0.13, _LU*0.11,
             _LU*0.13, _LU*0.10, _LU*0.23]

    def _tabela(lista: list):
        if not lista:
            return None
        lin = [[r.get("nome", ""),
                str(r.get("entregas", r.get("total_entregas", 0))),
                _r(r.get("soma_taxas", 0.0)),
                _r(r.get("diaria", 0.0)),
                _r(r.get("corridas_extras", r.get("corridas_extra", 0.0))),
                _r(r.get("vales", 0.0)),
                _r(r.get("total_a_pagar", r.get("total_liquido", 0.0)))]
               for r in lista]
        n = len(lin)
        verde_cmds  = [("TEXTCOLOR", (6, i+1), (6, i+1), _VERDE) for i in range(n)]
        verde_cmds += [("FONTNAME",  (6, i+1), (6, i+1), "Helvetica-Bold") for i in range(n)]
        t = Table([cab_e] + lin, colWidths=cw_e)
        t.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + verde_cmds
        ))
        return t

    story.append(_secao("Resumo do Dia"))
    story.append(_sp())
    t_dia = _tabela(dados.get("dia", []))
    story.append(t_dia if t_dia else Paragraph("Sem registros para esta data.", _ST_SEM_DADOS))

    story.append(_sp())
    story.append(_secao("Acumulado da Semana"))
    story.append(_sp())
    t_sem = _tabela(dados.get("semana", []))
    story.append(t_sem if t_sem else Paragraph("Sem dados acumulados para a semana.", _ST_SEM_DADOS))

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador estoque ───────────────────────────────────────────────────────────

def gerar_pdf_estoque(ini_br: str, fim_br: str,
                      movimentacoes: list, resumo: dict) -> str:
    """Gera PDF do relatório de movimentações de estoque."""
    _carregar()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(tempfile.gettempdir(), f"estoque_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    story.append(Paragraph("Gestão Loja", _ST_NOME_LOJA))
    story.append(Paragraph("Controle de Estoque — Movimentações", _ST_SUBTITULO))
    story.append(Paragraph(f"De {ini_br} a {fim_br}", _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=10))

    # Resumo
    story.append(_secao("Resumo"))
    story.append(_sp())
    lin_res = [
        ["Total Entradas (qtd)",   str(resumo.get("total_entrada_qtd",   0))],
        ["Total Entradas (valor)", _r(resumo.get("total_entrada_valor",  0.0))],
        ["Total Saídas (qtd)",     str(resumo.get("total_saida_qtd",     0))],
        ["Total Saídas (valor)",   _r(resumo.get("total_saida_valor",    0.0))],
    ]
    t_res = Table(lin_res, colWidths=[_LU * 0.60, _LU * 0.40])
    t_res.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ALIGN",          (1, 0), (1, -1), "RIGHT"),
        ("ALIGN",          (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        _alt_rows(0, 3),
        ("TEXTCOLOR",      (0, 0), (1, 1), _VERDE),
        ("TEXTCOLOR",      (0, 2), (1, 3), _VERMELHO),
        ("GRID",           (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
    ]))
    story.append(t_res)

    # Movimentações
    story.append(_sp())
    story.append(_secao("Movimentações"))
    story.append(_sp())
    if movimentacoes:
        cab = ["Data", "Produto", "Cat.", "Tipo", "Qtd",
               "Preço Unit.", "Valor Total", "Motivo"]
        cw  = [_LU*0.09, _LU*0.20, _LU*0.10, _LU*0.08, _LU*0.06,
               _LU*0.11, _LU*0.11, _LU*0.25]
        rows = []
        color_cmds = []
        for i, r in enumerate(movimentacoes):
            tipo = (r.get("tipo") or "").upper()
            rows.append([
                r.get("data", ""),
                r.get("produto", r.get("nome_produto", "")),
                r.get("categoria", r.get("nome_categoria", "")),
                tipo,
                str(r.get("quantidade", 0)),
                _r(r.get("preco_unit", r.get("preco_unitario", 0.0))),
                _r(r.get("valor_total", 0.0)),
                r.get("motivo", "") or "",
            ])
            ri = i + 1
            if tipo == "ENTRADA":
                color_cmds.append(("TEXTCOLOR", (3, ri), (3, ri), _VERDE))
            elif tipo == "SAIDA":
                color_cmds.append(("TEXTCOLOR", (3, ri), (3, ri), _VERMELHO))
        n = len(rows)
        t = Table([cab] + rows, colWidths=cw)
        t.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + color_cmds
        ))
        story.append(t)
    else:
        story.append(Paragraph("Sem movimentações para este período.", _ST_SEM_DADOS))

    _rodape(story)
    doc.build(story)
    return caminho


# ══════════════════════════════════════════════════════════════════════════════
#  8. gerar_pdf_movimentacoes
# ══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_movimentacoes(ini_br: str, fim_br: str, dados: dict, abrir_ao_concluir: bool = True) -> str:
    """Gera relatório em PDF das movimentações extras do período."""
    _carregar()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(tempfile.gettempdir(), f"movimentacoes_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    story = []

    story.append(Paragraph(dados.get("nome_loja", "Gestão Loja"), _ST_NOME_LOJA))
    story.append(Paragraph("Relatório de Movimentações e Caixa", _ST_SUBTITULO))
    story.append(Paragraph(f"Período: {ini_br} a {fim_br}", _ST_DATA_HDR))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=8))

    # Resumo Geral
    story.append(_secao("Resumo Financeiro do Período"))
    story.append(_sp())
    totais = dados.get("totais", {})
    saldo = totais.get("saldo", 0.0)
    lin_res = [
        ["Total de Entradas", _r(totais.get("entradas", 0.0))],
        ["Total de Saídas", _r(totais.get("saidas", 0.0))],
        ["Saldo Líquido", _r(saldo)],
        ["Saídas em Dinheiro (Gaveta)", _r(totais.get("saidas_dinheiro", 0.0))],
        ["Saídas em PIX", _r(totais.get("saidas_pix", 0.0))],
        ["Neutro (Consumo/Corridas)", _r(totais.get("neutro", 0.0))],
    ]
    t_res = Table(lin_res, colWidths=[_LU * 0.65, _LU * 0.35])
    t_res.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ALIGN",          (1, 0), (1, -1), "RIGHT"),
        ("ALIGN",          (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        _alt_rows(0, 5),
        ("TEXTCOLOR",      (0, 0), (1, 0), _VERDE),
        ("TEXTCOLOR",      (0, 1), (1, 1), _VERMELHO),
        ("TEXTCOLOR",      (0, 2), (1, 2), _VERDE if saldo >= 0 else _VERMELHO),
        ("FONTNAME",       (0, 2), (1, 2), "Helvetica-Bold"),
        ("GRID",           (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
    ]))
    story.append(t_res)

    # Gastos por Fornecedor
    fornecedores = dados.get("resumo_fornecedores", [])
    if fornecedores:
        story.append(_sp())
        story.append(_secao("Gastos por Fornecedor (Saídas)"))
        story.append(_sp())
        cab_f = ["Fornecedor", "Lançamentos", "Total Gasto"]
        cw_f  = [_LU * 0.55, _LU * 0.20, _LU * 0.25]
        rows_f = []
        for f in fornecedores:
            rows_f.append([
                f.get("nome", "Não informado"),
                str(f.get("qtd", 0)),
                _r(f.get("total", 0.0)),
            ])
        t_f = Table([cab_f] + rows_f, colWidths=cw_f)
        t_f.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, len(rows_f))] + [
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("TEXTCOLOR", (2, 1), (2, -1), _VERMELHO),
            ]
        ))
        story.append(t_f)

    # Resumo por Categoria
    categorias = dados.get("resumo_categorias", [])
    if categorias:
        story.append(_sp())
        story.append(_secao("Resumo por Categoria"))
        story.append(_sp())
        cab_c = ["Categoria", "Fluxo", "Lançamentos", "Total"]
        cw_c  = [_LU * 0.45, _LU * 0.18, _LU * 0.17, _LU * 0.20]
        rows_c = []
        color_cmds_c = []
        for i, c in enumerate(categorias):
            fl = c.get("fluxo", "")
            rows_c.append([
                c.get("categoria", ""),
                fl,
                str(c.get("qtd", 0)),
                _r(c.get("total", 0.0)),
            ])
            ri = i + 1
            if fl == "ENTRADA":
                color_cmds_c.append(("TEXTCOLOR", (1, ri), (1, ri), _VERDE))
                color_cmds_c.append(("TEXTCOLOR", (3, ri), (3, ri), _VERDE))
            elif fl == "SAIDA":
                color_cmds_c.append(("TEXTCOLOR", (1, ri), (1, ri), _VERMELHO))
                color_cmds_c.append(("TEXTCOLOR", (3, ri), (3, ri), _VERMELHO))
        t_c = Table([cab_c] + rows_c, colWidths=cw_c)
        t_c.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, len(rows_c))] + [
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ] + color_cmds_c
        ))
        story.append(t_c)

    # Extrato Analítico
    itens = dados.get("itens", [])
    story.append(_sp())
    story.append(_secao("Extrato Detalhado de Movimentações"))
    story.append(_sp())
    if itens:
        cab_i = ["Data", "Beneficiário", "Categoria", "Fluxo", "Método", "Valor", "Obs"]
        cw_i  = [_LU * 0.10, _LU * 0.20, _LU * 0.18, _LU * 0.10, _LU * 0.12, _LU * 0.12, _LU * 0.18]
        rows_i = []
        color_cmds_i = []
        for i, r in enumerate(itens):
            fl = r.get("fluxo", "")
            beneficiario = r.get("nome_fornecedor") or r.get("nome_pessoa") or "—"
            if beneficiario == "—" and r.get("obs") and r.get("obs").startswith("Fornecedor: "):
                corpo = r["obs"][len("Fornecedor: "):]
                beneficiario = corpo.split(" | ", 1)[0].strip() if " | " in corpo else corpo.strip()

            dt_br = r.get("data", "")
            if "-" in dt_br:
                try:
                    ano, mes, dia = dt_br.split("-")
                    dt_br = f"{dia}/{mes}/{ano}"
                except Exception:
                    pass

            obs_txt = r.get("obs", "") or ""
            if len(obs_txt) > 30:
                obs_txt = obs_txt[:28] + "…"

            rows_i.append([
                dt_br,
                beneficiario,
                r.get("categoria", ""),
                fl,
                r.get("metodo", "—") or "—",
                _r(r.get("valor", 0.0)),
                obs_txt,
            ])
            ri = i + 1
            if fl == "ENTRADA":
                color_cmds_i.append(("TEXTCOLOR", (3, ri), (3, ri), _VERDE))
                color_cmds_i.append(("TEXTCOLOR", (5, ri), (5, ri), _VERDE))
            elif fl == "SAIDA":
                color_cmds_i.append(("TEXTCOLOR", (3, ri), (3, ri), _VERMELHO))
                color_cmds_i.append(("TEXTCOLOR", (5, ri), (5, ri), _VERMELHO))

        t_i = Table([cab_i] + rows_i, colWidths=cw_i)
        t_i.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, len(rows_i))] + [
                ("ALIGN", (5, 0), (5, -1), "RIGHT"),
            ] + color_cmds_i
        ))
        story.append(t_i)
    else:
        story.append(Paragraph("Sem movimentações registradas para este período.", _ST_SEM_DADOS))

    _rodape(story)
    doc.build(story)
    if abrir_ao_concluir:
        abrir_pdf(caminho)
    return caminho


# ══════════════════════════════════════════════════════════════════════════════
#  9. gerar_pdf_escala_turnos
# ══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_escala_turnos(ano: int, mes: int, dados: dict, abrir_ao_concluir: bool = True) -> str:
    """
    Gera relatório em PDF (A4 Paisagem) com a grade mensal de escala de turnos
    para fixação no mural da loja.
    """
    _carregar()
    import calendar
    from datetime import date

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(tempfile.gettempdir(), f"escala_turnos_{ano}_{mes:02d}_{ts}.pdf")
    doc = SimpleDocTemplate(
        caminho,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    story = []

    meses_pt = [
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    nome_mes = meses_pt[mes] if 1 <= mes <= 12 else str(mes)

    # Cabeçalho
    story.append(Paragraph(dados.get("nome_loja", "Gestão Loja"), _ST_NOME_LOJA))
    story.append(Paragraph(f"Escala Mensal de Turnos — {nome_mes.upper()} / {ano}", _ST_SUBTITULO))
    story.append(HRFlowable(width="100%", thickness=2, color=_AZUL, spaceAfter=8))

    # Largura útil em paisagem: ~756 pt / 7 colunas ≈ 108 pt
    largura_total = landscape(A4)[0] - 3.0 * cm
    col_w = largura_total / 7.0

    dias_map = dados.get("escalas_por_dia", {})

    # Monta a matriz de semanas
    cal = calendar.Calendar(firstweekday=6) # Domingo a Sábado
    semanas = cal.monthdatescalendar(ano, mes)

    cabecalho = ["DOMINGO", "SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO"]
    linhas_tabela = [cabecalho]

    # Estilos de parágrafo para as células do calendário
    st_dia_num = ParagraphStyle(
        "DiaNum",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=_AZUL,
        alignment=0,
    )
    st_dia_num_fora = ParagraphStyle(
        "DiaNumFora",
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#bbbbbb"),
        alignment=0,
    )
    st_turno_dia = ParagraphStyle(
        "TurnoDia",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0d47a1"),
    )
    st_turno_noite = ParagraphStyle(
        "TurnoNoite",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#4a148c"),
    )

    for sem in semanas:
        linha_celulas = []
        for dt in sem:
            dt_iso = dt.isoformat()
            eh_do_mes = (dt.month == mes)

            elementos_celula = []
            if eh_do_mes:
                elementos_celula.append(Paragraph(f"<b>{dt.day}</b>", st_dia_num))
            else:
                elementos_celula.append(Paragraph(f"{dt.day}", st_dia_num_fora))

            if eh_do_mes:
                turnos_dia = dias_map.get(dt_iso, {})
                lista_dia = turnos_dia.get("DIA", [])
                lista_noite = turnos_dia.get("NOITE", [])

                if lista_dia:
                    nomes_d = ", ".join(p.get("nome_exibicao", "") for p in lista_dia)
                    elementos_celula.append(Paragraph(f"<b>DIA:</b> {nomes_d}", st_turno_dia))

                if lista_noite:
                    nomes_n = ", ".join(p.get("nome_exibicao", "") for p in lista_noite)
                    elementos_celula.append(Paragraph(f"<b>NOITE:</b> {nomes_n}", st_turno_noite))

                if not lista_dia and not lista_noite:
                    elementos_celula.append(Paragraph("—", ParagraphStyle("Vazio", fontName="Helvetica", fontSize=7, textColor=colors.HexColor("#aaaaaa"))))

            linha_celulas.append(elementos_celula)
        linhas_tabela.append(linha_celulas)

    # Estilo da grade mensal
    t_grade = Table(linhas_tabela, colWidths=[col_w] * 7)
    t_grade.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _BRANCO),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8.5),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("GRID",          (0, 0), (-1, -1), 0.5, _CINZA_GRADE),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("BACKGROUND",    (0, 1), (0, -1), colors.HexColor("#fafafa")), # Domingo destaque
        ("BACKGROUND",    (6, 1), (6, -1), colors.HexColor("#fafafa")), # Sábado destaque
    ]))
    story.append(t_grade)

    _rodape(story)
    doc.build(story)
    if abrir_ao_concluir:
        abrir_pdf(caminho)
    return caminho


# ── Abrir PDF no visualizador padrão do Windows ───────────────────────────────

def abrir_pdf(caminho: str) -> None:
    """Abre o PDF no visualizador padrão via os.startfile()."""
    os.startfile(caminho)
