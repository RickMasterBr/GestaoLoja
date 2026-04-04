"""
limpar_dados_teste.py — Remove dados de teste anteriores a 01/04/2026.
Execute apenas UMA VEZ antes da entrega do sistema.
FAÇA BACKUP DO BANCO ANTES DE EXECUTAR.
"""

import sqlite3
import os
import shutil
from datetime import date

# ── Importa o caminho do banco do projeto ─────────────────────────────
import database

DATA_CORTE = "2026-04-01"   # apaga tudo ANTES desta data (exclusive)


def confirmar() -> bool:
    print("=" * 60)
    print("  LIMPEZA DE DADOS DE TESTE — GestaoLoja")
    print("=" * 60)
    print(f"\n  Banco ativo: {database.get_db_path()}")
    print(f"  Serão apagados todos os registros com data < {DATA_CORTE}")
    print("\n  Tabelas afetadas:")
    print("    - vendas_pedidos + vendas_pagamentos (cascade)")
    print("    - movimentacoes_extras")
    print("    - escalas_trabalho")
    print("    - registros_ponto")
    print("    - fluxo_caixa_diario")
    print("    - estoque_movimentacoes")
    print("    - fiados")
    print("    - logs_auditoria")
    print("\n  Tabelas de cadastro NÃO serão alteradas.")
    print("\n  ATENÇÃO: Esta operação não pode ser desfeita sem backup.")
    resp = input("\n  Digite CONFIRMAR para prosseguir: ")
    return resp.strip() == "CONFIRMAR"


def fazer_backup():
    origem  = database.get_db_path()
    destino = origem.replace(".db", f"_BACKUP_{date.today().strftime('%Y%m%d')}.db")
    shutil.copy2(origem, destino)
    print(f"\n  Backup criado: {destino}")
    for sufixo in ("-wal", "-shm"):
        src = origem + sufixo
        if os.path.exists(src):
            shutil.copy2(src, destino + sufixo)
    return destino


def limpar():
    conn = sqlite3.connect(database.get_db_path())
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row

    try:
        # Contagem antes (para relatório)
        def contar(tabela, coluna="data"):
            try:
                return conn.execute(
                    f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} < ?",
                    (DATA_CORTE,)
                ).fetchone()[0]
            except Exception:
                return 0

        counts = {
            "vendas_pedidos":       contar("vendas_pedidos"),
            "movimentacoes_extras": contar("movimentacoes_extras"),
            "escalas_trabalho":     contar("escalas_trabalho"),
            "registros_ponto":      contar("registros_ponto"),
            "fluxo_caixa_diario":   contar("fluxo_caixa_diario"),
            "estoque_movimentacoes":contar("estoque_movimentacoes"),
            "fiados":               contar("fiados", "data_lancamento"),
            "logs_auditoria":       contar("logs_auditoria", "data_hora"),
        }

        print("\n  Registros que serão removidos:")
        for tabela, qtd in counts.items():
            print(f"    {tabela:<30} {qtd} registros")

        total = sum(counts.values())
        if total == 0:
            print("\n  Nenhum registro encontrado antes da data de corte. Nada a fazer.")
            return

        resp = input(f"\n  Total: {total} registros. Confirma a exclusão? (s/n): ")
        if resp.strip().lower() != "s":
            print("  Operação cancelada.")
            return

        # ── Exclusões ────────────────────────────────────────────────
        # vendas_pagamentos é apagado em cascade via FK de vendas_pedidos
        conn.execute(
            "DELETE FROM vendas_pedidos WHERE data < ?", (DATA_CORTE,)
        )
        conn.execute(
            "DELETE FROM movimentacoes_extras WHERE data < ?", (DATA_CORTE,)
        )
        conn.execute(
            "DELETE FROM escalas_trabalho WHERE data < ?", (DATA_CORTE,)
        )
        conn.execute(
            "DELETE FROM registros_ponto WHERE data < ?", (DATA_CORTE,)
        )
        conn.execute(
            "DELETE FROM fluxo_caixa_diario WHERE data < ?", (DATA_CORTE,)
        )
        conn.execute(
            "DELETE FROM estoque_movimentacoes WHERE data < ?", (DATA_CORTE,)
        )
        conn.execute(
            "DELETE FROM fiados WHERE data_lancamento < ?", (DATA_CORTE,)
        )
        conn.execute(
            "DELETE FROM logs_auditoria WHERE data_hora < ?", (DATA_CORTE,)
        )

        # Recalcula quantidade atual de todos os produtos após limpar movimentações
        # (os triggers não disparam em DELETE, então recalculamos manualmente)
        produtos = conn.execute(
            "SELECT id FROM estoque_produtos"
        ).fetchall()

        for p in produtos:
            pid = p["id"]
            ultimo_ajuste = conn.execute(
                """SELECT id, quantidade FROM estoque_movimentacoes
                   WHERE id_produto = ? AND tipo = 'AJUSTE'
                   ORDER BY data DESC, hora DESC, id DESC LIMIT 1""",
                (pid,)
            ).fetchone()

            if ultimo_ajuste:
                base = ultimo_ajuste["quantidade"]
                delta = conn.execute(
                    """SELECT COALESCE(SUM(
                           CASE tipo
                               WHEN 'ENTRADA' THEN quantidade
                               WHEN 'SAIDA'   THEN -quantidade
                               ELSE 0
                           END
                       ), 0) FROM estoque_movimentacoes
                       WHERE id_produto = ? AND id > ?""",
                    (pid, ultimo_ajuste["id"])
                ).fetchone()[0]
                nova_qtd = base + delta
            else:
                nova_qtd = conn.execute(
                    """SELECT COALESCE(SUM(
                           CASE tipo
                               WHEN 'ENTRADA' THEN quantidade
                               WHEN 'SAIDA'   THEN -quantidade
                               ELSE 0
                           END
                       ), 0) FROM estoque_movimentacoes
                       WHERE id_produto = ?""",
                    (pid,)
                ).fetchone()[0]

            conn.execute(
                "UPDATE estoque_produtos SET quantidade_atual = ? WHERE id = ?",
                (nova_qtd, pid)
            )

        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()

        print("\n  Limpeza concluída com sucesso.")
        print("  Os cadastros (pessoas, bairros, plataformas, etc.) foram preservados.")

    except Exception as exc:
        conn.rollback()
        print(f"\n  ERRO — operação revertida: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if not confirmar():
        print("\n  Operação cancelada. Nada foi alterado.")
    else:
        fazer_backup()
        limpar()
