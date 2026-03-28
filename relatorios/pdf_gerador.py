"""
relatorios/pdf_gerador.py — Geração de relatórios PDF para impressão.
Abre o arquivo diretamente no visualizador padrão do Windows via os.startfile().
"""

import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
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
        cab_p = ["Data", "Entrada", "Saída", "H.Brutas", "H.Líquidas", "Extras/Falt."]
        lin_p = [[r.get("data", ""), r.get("entrada", ""), r.get("saida", ""),
                  r.get("horas_brutas", ""), r.get("horas_liquidas", ""),
                  str(r.get("extras_faltantes", ""))]
                 for r in ponto]
        n = len(lin_p)
        color_pt = []
        for i, r in enumerate(ponto):
            ev = str(r.get("extras_faltantes", ""))
            ri = i + 1
            if ev.startswith("+"):
                color_pt.append(("TEXTCOLOR", (5, ri), (5, ri), _VERDE))
            elif ev.startswith("-"):
                color_pt.append(("TEXTCOLOR", (5, ri), (5, ri), _VERMELHO))
        cw_p = [_LU*0.14, _LU*0.12, _LU*0.12, _LU*0.14, _LU*0.14, _LU*0.34]
        t_p = Table([cab_p] + lin_p, colWidths=cw_p)
        t_p.setStyle(TableStyle(
            _cab_style() + _body_style() + [_alt_rows(1, n)] + color_pt
        ))
        story.append(t_p)

    _rodape(story)
    doc.build(story)
    return caminho


# ── Gerador entregadores ──────────────────────────────────────────────────────

def gerar_pdf_entregadores(data_br: str, dados: dict) -> str:
    """Gera PDF do painel de entregadores (dia + semana)."""
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


# ── Abrir PDF no visualizador padrão do Windows ───────────────────────────────

def abrir_pdf(caminho: str) -> None:
    """Abre o PDF no visualizador padrão via os.startfile()."""
    os.startfile(caminho)
