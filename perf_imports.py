"""
perf_imports.py - DIAGNOSTICO TEMPORARIO: custo de import de cada view.

Mede, em processo unico e na ordem em que main.py importaria:
  - 1a importacao do modulo (custo real de carregar o modulo + suas deps)
  - 2a importacao do mesmo modulo (deve ser ~0 por causa do sys.modules cache)

Tambem mede as dependencias pesadas isoladamente (flet, reportlab, openpyxl).

Apagar este arquivo remove o diagnostico. Nao e importado por main.py.
"""

import importlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VIEWS = [
    "views.extras",
    "views.fluxo_caixa",
    "views.escala_geral",
    "views.estoque",
    "views.relatorio_diario",
    "views.relatorio_periodo",
    "views.funcionarios",
    "views.entregadores",
    "views.fornecedores",
    "views.parametros",
    # de referencia (ja validadas / nao pedidas)
    "views.dashboard",
    "views.pdv",
    "views.fiados",
    "views.login",
]

DEPS = ["flet", "database", "reportlab.platypus", "openpyxl",
        "relatorios.pdf_gerador", "relatorios.excel_gerador"]


def _imp(nome):
    t0 = time.perf_counter()
    importlib.import_module(nome)
    return (time.perf_counter() - t0) * 1000


def main():
    print("=" * 78)
    print("CUSTO DE IMPORT - DEPENDENCIAS PESADAS (isoladas, 1a vez)")
    print("=" * 78)
    print("%-32s %10s %10s" % ("modulo", "1a (ms)", "2a (ms)"))
    for d in DEPS:
        try:
            a = _imp(d)
            b = _imp(d)
            print("%-32s %10.1f %10.3f" % (d, a, b))
        except Exception as e:
            print("%-32s ERRO: %s" % (d, e))

    print()
    print("=" * 78)
    print("CUSTO DE IMPORT - VIEWS (na ordem de main.py; deps ja aquecidas acima)")
    print("=" * 78)
    print("%-32s %10s %10s" % ("modulo", "1a (ms)", "2a (ms)"))
    total = 0.0
    for v in VIEWS:
        try:
            a = _imp(v)
            b = _imp(v)
            total += a
            print("%-32s %10.1f %10.3f" % (v, a, b))
        except Exception as e:
            print("%-32s ERRO: %s" % (v, e))
    print("-" * 78)
    print("%-32s %10.1f" % ("TOTAL views", total))


if __name__ == "__main__":
    main()
