"""
perf_driver.py - DIAGNOSTICO TEMPORARIO.

Sobe o app Flet de verdade contra um banco de TESTE isolado
(GESTAOLOJA_TESTE) e navega automaticamente por cada tela 2x,
medindo separadamente:

    - import do modulo da view (1a e 2a vez)
    - cada query SQL executada (via perf_instr, padrao _t())
    - construcao dos controles Flet (view(page) retornar)
    - page.update() (render)
    - numero de controles Flet na arvore montada

No fim grava relatorio_perf.md e roda EXPLAIN QUERY PLAN das queries mais lentas.

Apagar perf_driver.py + perf_instr.py + perf_imports.py remove todo o diagnostico.
NAO altera nenhum arquivo do app.
"""

import importlib
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if not os.environ.get("GESTAOLOJA_TESTE"):
    print("ERRO: defina GESTAOLOJA_TESTE apontando para um .db de teste.")
    sys.exit(1)

import flet as ft
import database
import perf_instr

perf_instr.ativar()

# --- SHIM DE DIAGNOSTICO (nao e correcao) ------------------------------------
# views/fluxo_caixa.py linhas 138 e 844 chamam ft.Border.BorderSide, que NAO
# existe no Flet 0.86 (o correto, usado por todas as outras views, e
# ft.BorderSide). Isso e um BUG PRE-EXISTENTE que quebra a tela Fluxo Caixa.
# Sem este shim nao da para medir a tela. O shim vive so aqui, no diagnostico.
if not hasattr(ft.Border, "BorderSide"):
    ft.Border.BorderSide = ft.BorderSide
    print("[shim-diag] ft.Border.BorderSide adicionado apenas para medicao "
          "(bug real em views/fluxo_caixa.py:138 e :844)", flush=True)

# Telas a diagnosticar (nome do modulo em views/)
TELAS = [
    "extras",
    "fluxo_caixa",
    "escala_geral",
    "estoque",
    "relatorio_diario",
    "relatorio_periodo",
    "funcionarios",
    "entregadores",
    "fornecedores",
    "parametros",
]

RODADAS = 2
RESULTADOS = []

# Telas que so consultam o banco quando o usuario dispara uma acao.
# Cada acao: (rotulo, campos_a_preencher, texto_do_botao, ocorrencia_do_botao)
ACOES = {
    "fluxo_caixa": [
        ("Gerar (aba Diario)", {}, "Gerar", 0),
        ("Gerar (aba Periodo)", {}, "Gerar", 1),
    ],
    "relatorio_periodo": [
        ("Gerar Relatorio (mes corrente)", {}, "Gerar Relatório", 0),
        ("Gerar Relatorio (90 dias)",
         {"Data inicial": "_D-90", "Data final": "_HOJE"}, "Gerar Relatório", 0),
        ("Gerar Relatorio (365 dias)",
         {"Data inicial": "_D-365", "Data final": "_HOJE"}, "Gerar Relatório", 0),
    ],
    "funcionarios": [
        ("Carregar (1o funcionario, mes corrente)",
         {"__dropdown_first__": "Funcionário"}, "Carregar", 0),
    ],
    "escala_geral": [
        ("Trocar para secao Ponto", {}, "Ponto", 0),
    ],
}


def _andar(ctrl, vistos=None):
    """Percorre recursivamente a arvore de controles Flet."""
    if vistos is None:
        vistos = set()
    if ctrl is None or not isinstance(ctrl, ft.Control) or id(ctrl) in vistos:
        return
    vistos.add(id(ctrl))
    yield ctrl
    for attr in ("controls", "content", "actions", "tabs", "rows", "columns",
                 "cells", "leading", "trailing", "title", "subtitle",
                 "tab_content"):
        v = getattr(ctrl, attr, None)
        if v is None:
            continue
        for c in (v if isinstance(v, (list, tuple)) else [v]):
            for x in _andar(c, vistos):
                yield x


def _rotulo(c):
    """Texto visivel de um botao, seja via .text, .content str ou ft.Text."""
    for attr in ("text", "content", "label"):
        v = getattr(c, attr, None)
        if isinstance(v, str):
            return v
        if isinstance(v, ft.Text) and isinstance(v.value, str):
            return v.value
    return None


def _resolver_data(v):
    from datetime import date, timedelta
    if v == "_HOJE":
        return date.today().strftime("%d/%m/%Y")
    if v.startswith("_D-"):
        return (date.today() - timedelta(days=int(v[3:]))).strftime("%d/%m/%Y")
    return v


def _executar_acao(ctrl, campos, texto_botao, ocorrencia):
    """Preenche campos e dispara o on_click do botao. Retorna (ok, msg)."""
    nos = list(_andar(ctrl))

    for label, valor in campos.items():
        if label == "__dropdown_first__":
            for c in nos:
                if isinstance(c, ft.Dropdown) and getattr(c, "label", None) == valor:
                    if c.options:
                        c.value = c.options[0].key
                    break
            continue
        for c in nos:
            if isinstance(c, ft.TextField) and getattr(c, "label", None) == label:
                c.value = _resolver_data(valor)
                break

    achados = [c for c in nos
               if getattr(c, "on_click", None) and _rotulo(c) == texto_botao]
    if len(achados) <= ocorrencia:
        return False, "botao %r ocorrencia %d nao encontrado (achados: %d)" % (
            texto_botao, ocorrencia, len(achados))
    achados[ocorrencia].on_click(None)
    return True, ""


def _contar_controles(ctrl, vistos=None):
    """Conta recursivamente quantos controles Flet existem na arvore."""
    if vistos is None:
        vistos = set()
    if ctrl is None or id(ctrl) in vistos:
        return 0
    if not isinstance(ctrl, ft.Control):
        return 0
    vistos.add(id(ctrl))
    n = 1
    for attr in ("controls", "content", "actions", "tabs", "rows", "columns",
                 "cells", "leading", "trailing", "title", "subtitle", "tab_content"):
        v = getattr(ctrl, attr, None)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            for c in v:
                n += _contar_controles(c, vistos)
        else:
            n += _contar_controles(v, vistos)
    return n


def main(page: ft.Page):
    page.title = "DIAGNOSTICO PERF"
    page.window.width = 1400
    page.window.height = 900

    # sessao ADMIN para nao esbarrar em checagem de perfil
    try:
        database.sessao_iniciar(1, "DIAG", "ADMIN")
    except Exception:
        pass

    area = ft.Container(expand=True)
    page.add(area)
    page.update()

    for rodada in range(1, RODADAS + 1):
        for nome in TELAS:
            perf_instr.CTX["tela"] = nome
            perf_instr.CTX["rodada"] = rodada
            n_ev = len(perf_instr.EVENTOS)

            reg = {"tela": nome, "rodada": rodada}

            # --- import do modulo -------------------------------------------
            t0 = time.perf_counter()
            try:
                mod = importlib.import_module("views." + nome)
            except Exception as e:
                reg["erro"] = "import: %s" % e
                RESULTADOS.append(reg)
                continue
            reg["ms_import"] = (time.perf_counter() - t0) * 1000

            # --- construcao dos controles (inclui as queries) ---------------
            t0 = time.perf_counter()
            try:
                ctrl = mod.view(page)
            except Exception as e:
                reg["erro"] = "view(): %s" % e
                reg["traceback"] = traceback.format_exc()[-1500:]
                RESULTADOS.append(reg)
                perf_instr.CTX["tela"] = "-"
                continue
            reg["ms_build"] = (time.perf_counter() - t0) * 1000

            # --- attach + render --------------------------------------------
            t0 = time.perf_counter()
            area.content = ctrl
            page.update()
            reg["ms_update"] = (time.perf_counter() - t0) * 1000

            reg["n_controles"] = _contar_controles(ctrl)

            # --- soma por categoria a partir dos eventos desta tela ---------
            evs = perf_instr.EVENTOS[n_ev:]
            reg["ms_sql_total"] = sum(e["ms"] for e in evs
                                      if e["tipo"] in ("sql_exec", "sql_fetch"))
            reg["ms_conectar"] = sum(e["ms"] for e in evs if e["tipo"] == "conectar")
            reg["n_queries"] = sum(1 for e in evs if e["tipo"] == "sql_exec")
            reg["n_conexoes"] = sum(1 for e in evs if e["tipo"] == "conectar")
            reg["top_db_funcs"] = sorted(
                _agrupar(evs, "db_func").items(), key=lambda kv: -kv[1][1]
            )[:8]
            reg["top_sql"] = sorted(
                _agrupar(evs, "sql_exec", "sql_fetch").items(),
                key=lambda kv: -kv[1][1]
            )[:10]

            RESULTADOS.append(reg)
            print("[%d] %-18s import %7.1f  build %8.1f  update %7.1f  "
                  "sql %8.1f (%d q / %d conn)  ctrls %d"
                  % (rodada, nome, reg["ms_import"], reg["ms_build"],
                     reg["ms_update"], reg["ms_sql_total"],
                     reg["n_queries"], reg["n_conexoes"], reg["n_controles"]),
                  flush=True)

            # --- acoes do usuario que disparam a carga de dados -------------
            for rotulo, campos, texto_btn, ocorr in ACOES.get(nome, []):
                m = len(perf_instr.EVENTOS)
                t0 = time.perf_counter()
                try:
                    ok, msg = _executar_acao(ctrl, campos, texto_btn, ocorr)
                except Exception as e:
                    ok, msg = False, "%s: %s" % (type(e).__name__, e)
                ms = (time.perf_counter() - t0) * 1000
                evs2 = perf_instr.EVENTOS[m:]
                a = {
                    "tela": nome, "rodada": rodada, "acao": rotulo,
                    "ms_acao": ms,
                    "ms_sql_total": sum(e["ms"] for e in evs2
                                        if e["tipo"] in ("sql_exec", "sql_fetch")),
                    "ms_conectar": sum(e["ms"] for e in evs2
                                       if e["tipo"] == "conectar"),
                    "n_queries": sum(1 for e in evs2 if e["tipo"] == "sql_exec"),
                    "n_conexoes": sum(1 for e in evs2 if e["tipo"] == "conectar"),
                    "n_controles": _contar_controles(ctrl),
                    "top_db_funcs": sorted(_agrupar(evs2, "db_func").items(),
                                           key=lambda kv: -kv[1][1])[:8],
                    "top_sql": sorted(
                        _agrupar(evs2, "sql_exec", "sql_fetch").items(),
                        key=lambda kv: -kv[1][1])[:10],
                }
                if not ok:
                    a["erro"] = msg
                RESULTADOS.append(a)
                print("      -> acao %-34s %8.1f ms  (sql %7.1f / %d q / %d conn"
                      "  ctrls %d) %s"
                      % (rotulo, ms, a["ms_sql_total"], a["n_queries"],
                         a["n_conexoes"], a["n_controles"],
                         "FALHOU: " + msg if not ok else ""), flush=True)

    perf_instr.CTX["tela"] = "-"
    _gravar_relatorio()
    print("\nOK -> relatorio_perf.md", flush=True)
    os._exit(0)


def _agrupar(evs, *tipos):
    d = {}
    for e in evs:
        if e["tipo"] in tipos:
            n, ms = d.get(e["label"], (0, 0.0))
            d[e["label"]] = (n + 1, ms + e["ms"])
    return d


def _gravar_relatorio():
    with open("relatorio_perf.json", "w", encoding="utf-8") as f:
        json.dump({"resultados": RESULTADOS}, f, indent=1, default=str)

    planos = perf_instr.explain_todas(min_ms=1.0)

    L = []
    L.append("# Diagnostico de performance por tela\n")
    L.append("Banco de teste: `%s`\n" % database.get_db_path())
    L.append("\n## 1. Resumo por tela (ms)\n")
    L.append("| Tela | Rodada | import | build (view()) | page.update() | "
             "SQL total | # queries | # conexoes | # controles Flet |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in RESULTADOS:
        if "acao" in r:
            L.append("| %s -> *%s* | %d | (acao) | %.1f | (incluso) | %.1f | "
                     "%d | %d | %d |"
                     % (r["tela"], r["acao"], r["rodada"], r["ms_acao"],
                        r["ms_sql_total"], r["n_queries"], r["n_conexoes"],
                        r["n_controles"]))
            continue
        if "erro" in r:
            L.append("| %s | %d | ERRO: %s | | | | | | |"
                     % (r["tela"], r["rodada"], r["erro"]))
            continue
        L.append("| %s | %d | %.1f | %.1f | %.1f | %.1f | %d | %d | %d |"
                 % (r["tela"], r["rodada"], r["ms_import"], r["ms_build"],
                    r["ms_update"], r["ms_sql_total"], r["n_queries"],
                    r["n_conexoes"], r["n_controles"]))

    L.append("\n## 2. Detalhe por tela\n")
    for r in RESULTADOS:
        if "acao" in r:
            L.append("\n### %s -> acao: %s (rodada %d)\n"
                     % (r["tela"], r["acao"], r["rodada"]))
            L.append("- total da acao: **%.1f ms** | SQL: **%.1f ms** | "
                     "queries: **%d** | conexoes: **%d** | controles na tela "
                     "depois: **%d**"
                     % (r["ms_acao"], r["ms_sql_total"], r["n_queries"],
                        r["n_conexoes"], r["n_controles"]))
            L.append("- Python/Flet fora do SQL (inclui page.update() interno): "
                     "**%.1f ms**"
                     % (r["ms_acao"] - r["ms_sql_total"] - r["ms_conectar"]))
            if "erro" in r:
                L.append("- FALHOU: `%s`" % r["erro"])
        elif "erro" in r:
            L.append("\n### %s (rodada %d) - ERRO\n" % (r["tela"], r["rodada"]))
            L.append("```\n%s\n```" % r.get("traceback", r["erro"]))
            continue
        else:
            L.append("\n### %s (rodada %d)\n" % (r["tela"], r["rodada"]))
            L.append("- import: **%.1f ms** | build: **%.1f ms** | update: "
                     "**%.1f ms** | SQL: **%.1f ms** | controles: **%d**"
                     % (r["ms_import"], r["ms_build"], r["ms_update"],
                        r["ms_sql_total"], r["n_controles"]))
            ms_py = r["ms_build"] - r["ms_sql_total"] - r["ms_conectar"]
            L.append("- construcao Python/Flet fora do SQL: **%.1f ms**" % ms_py)
        if r["top_db_funcs"]:
            L.append("\nFuncoes de database.py mais caras:\n")
            L.append("| funcao | chamadas | ms |")
            L.append("|---|---|---|")
            for lab, (n, ms) in r["top_db_funcs"]:
                L.append("| `%s` | %d | %.1f |" % (lab, n, ms))
        if r["top_sql"]:
            L.append("\nQueries mais caras:\n")
            L.append("| query | chamadas | ms |")
            L.append("|---|---|---|")
            for lab, (n, ms) in r["top_sql"]:
                L.append("| `%s` | %d | %.1f |" % (lab.replace("|", "/"), n, ms))

    L.append("\n## 3. EXPLAIN QUERY PLAN das queries mais custosas\n")
    for p in planos[:40]:
        L.append("\n#### %.1f ms total (%d exec) - telas: %s\n"
                 % (p["ms"], p["n"], ", ".join(p["telas"])))
        L.append("```sql\n%s\n```" % p["sql"][:1400])
        L.append("```\n%s\n```" % "\n".join(p["plano"]))

    with open("relatorio_perf.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    ft.app(target=main)
