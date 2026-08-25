"""
perf_instr.py - INSTRUMENTACAO TEMPORARIA DE DIAGNOSTICO.

NAO faz parte do app. Nao e importado por main.py.
Para remover o diagnostico basta APAGAR este arquivo e perf_driver.py.

Usa o MESMO padrao _t() ja existente em database.py; apenas acrescenta
um segundo handler de log (arquivo separado) e um acumulador estruturado
para gerar o relatorio final.
"""

import functools
import inspect
import logging
import os
import time

import database
from database import _t   # mesmo context manager ja existente

# -- Handler extra: nao mexe no perf_log.txt de producao ----------------------
DIAG_LOG = os.environ.get("GESTAOLOJA_DIAG_LOG", "perf_diag.txt")
_h = logging.FileHandler(DIAG_LOG, encoding="utf-8", mode="w")
_h.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d | %(message)s",
                                  datefmt="%H:%M:%S"))
logging.getLogger("perf").addHandler(_h)

# -- Coleta estruturada ------------------------------------------------------
CTX = {"tela": "-", "rodada": 0}          # contexto corrente (tela sendo medida)
EVENTOS = []                              # [{tela,rodada,tipo,label,ms,sql}]
SQL_VISTAS = {}                           # sql_normalizado -> {params, n, ms, telas}


def _reg(tipo, label, ms, sql=None, params=None):
    EVENTOS.append({
        "tela":   CTX["tela"],
        "rodada": CTX["rodada"],
        "tipo":   tipo,
        "label":  label,
        "ms":     ms,
        "sql":    sql,
    })
    if sql is not None:
        k = " ".join(sql.split())
        d = SQL_VISTAS.setdefault(k, {"params": params, "n": 0, "ms": 0.0,
                                      "telas": set()})
        d["n"] += 1
        d["ms"] += ms
        d["telas"].add(CTX["tela"])
        if d["params"] is None:
            d["params"] = params


def _resumo_sql(sql, n=60):
    return " ".join(sql.split())[:n]


# ============================================================================
#  Camada 1 - proxy de conexao: mede TODA query SQL
#             (tanto as de database.py quanto as inline dentro das views)
# ============================================================================

class _CursorProxy:
    """Cronometra o fetch, onde o SQLite realmente percorre as linhas."""

    def __init__(self, cur, sql, params):
        self._cur = cur
        self._sql = sql
        self._params = params

    def _medir(self, nome, *a, **kw):
        real = getattr(self._cur, nome)
        t0 = time.perf_counter()
        try:
            return real(*a, **kw)
        finally:
            ms = (time.perf_counter() - t0) * 1000
            rot = "  SQL %s %s" % (nome, _resumo_sql(self._sql, 40))
            logging.getLogger("perf").debug("%-55s %8.1f ms" % (rot, ms))
            _reg("sql_fetch", rot.strip(), ms, self._sql, self._params)

    def fetchall(self, *a, **kw):
        return self._medir("fetchall", *a, **kw)

    def fetchone(self, *a, **kw):
        return self._medir("fetchone", *a, **kw)

    def fetchmany(self, *a, **kw):
        return self._medir("fetchmany", *a, **kw)

    def __iter__(self):
        t0 = time.perf_counter()
        rows = list(self._cur)
        ms = (time.perf_counter() - t0) * 1000
        _reg("sql_fetch", "iter " + _resumo_sql(self._sql, 40), ms,
             self._sql, self._params)
        return iter(rows)

    def __getattr__(self, n):
        return getattr(self._cur, n)


class _ConnProxy:
    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def execute(self, sql, params=()):
        t0 = time.perf_counter()
        cur = None
        try:
            cur = self._conn.execute(sql, params)
        finally:
            ms = (time.perf_counter() - t0) * 1000
            rot = "  SQL exec " + _resumo_sql(sql, 40)
            logging.getLogger("perf").debug("%-55s %8.1f ms" % (rot, ms))
            _reg("sql_exec", rot.strip(), ms, sql, params)
        return _CursorProxy(cur, sql, params)

    def executemany(self, sql, seq):
        seq = list(seq)
        t0 = time.perf_counter()
        try:
            return self._conn.executemany(sql, seq)
        finally:
            ms = (time.perf_counter() - t0) * 1000
            _reg("sql_exec", "executemany(%d) %s" % (len(seq), _resumo_sql(sql, 30)),
                 ms, sql, seq[0] if seq else None)

    def commit(self):
        t0 = time.perf_counter()
        try:
            return self._conn.commit()
        finally:
            _reg("commit", "commit", (time.perf_counter() - t0) * 1000)

    def close(self):
        t0 = time.perf_counter()
        try:
            return self._conn.close()
        finally:
            _reg("close", "close", (time.perf_counter() - t0) * 1000)

    def cursor(self, *a, **kw):
        return self._conn.cursor(*a, **kw)

    def __enter__(self):
        self._conn.__enter__()
        return self

    def __exit__(self, *a):
        return self._conn.__exit__(*a)

    def __getattr__(self, n):
        return getattr(self._conn, n)

    def __setattr__(self, n, v):
        setattr(self._conn, n, v)


_conectar_original = database.conectar


@functools.wraps(_conectar_original)
def _conectar_instrumentado():
    t0 = time.perf_counter()
    conn = _conectar_original()
    _reg("conectar", "database.conectar()", (time.perf_counter() - t0) * 1000)
    return _ConnProxy(conn)


# ============================================================================
#  Camada 2 - wrapper em cada funcao publica de database.py
#             (da atribuicao "qual funcao de negocio custou o que")
# ============================================================================

def _envolver_funcoes_database():
    for nome, obj in list(vars(database).items()):
        if nome.startswith("_") or not inspect.isfunction(obj):
            continue
        if getattr(obj, "__module__", None) != "database":
            continue
        if nome in ("conectar", "get_db_path"):
            continue

        def make(nome, fn):
            @functools.wraps(fn)
            def w(*a, **kw):
                t0 = time.perf_counter()
                try:
                    with _t("db." + nome):
                        return fn(*a, **kw)
                finally:
                    _reg("db_func", "database.%s()" % nome,
                         (time.perf_counter() - t0) * 1000)
            return w

        setattr(database, nome, make(nome, obj))


def ativar():
    """Aplica os dois niveis de instrumentacao. Idempotente."""
    if getattr(database, "_PERF_INSTR_ATIVO", False):
        return
    _envolver_funcoes_database()
    database.conectar = _conectar_instrumentado
    database._PERF_INSTR_ATIVO = True
    logging.getLogger("perf").debug("=== perf_instr ATIVO ===")


# ============================================================================
#  EXPLAIN QUERY PLAN das queries coletadas
# ============================================================================

def explain_todas(min_ms=0.0):
    """Roda EXPLAIN QUERY PLAN em cada SQL vista. Retorna lista ordenada por ms."""
    import sqlite3
    conn = sqlite3.connect(database.get_db_path())
    out = []
    for sql, d in SQL_VISTAS.items():
        if d["ms"] < min_ms:
            continue
        if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
            continue
        plano = []
        try:
            p = d["params"]
            if isinstance(p, dict):
                pp = p
            elif p is None:
                pp = ()
            else:
                pp = tuple(p)
            for r in conn.execute("EXPLAIN QUERY PLAN " + sql, pp):
                plano.append(r[-1])
        except Exception as e:
            plano.append("<erro no EXPLAIN: %s>" % e)
        out.append({"sql": sql, "n": d["n"], "ms": d["ms"],
                    "telas": sorted(d["telas"]), "plano": plano})
    conn.close()
    out.sort(key=lambda x: -x["ms"])
    return out
