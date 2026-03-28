"""
database.py — Módulo de banco de dados para o sistema de fechamento de caixa.
Gerencia todas as tabelas SQLite, funções CRUD e dados iniciais do aplicativo.
"""

import os
import sqlite3

# ─────────────────────────────────────────────
#  CONFIGURAÇÃO — tenta os caminhos do Google Drive
#  em ordem; cai para banco local se nenhum existir.
# ─────────────────────────────────────────────
CAMINHOS_POSSIVEIS = [
    r"G:\Meu Drive\loja_app\loja_caixa.db",
    r"G:\.shortcut-targets-by-id\1ZpTw_tkrAopkI6VLdOzGt78YmL5FZOc_\loja_app\loja_caixa.db",
]

LOCAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loja_caixa.db")


def _encontrar_banco():
    for caminho in CAMINHOS_POSSIVEIS:
        if os.path.exists(os.path.dirname(caminho)):
            return caminho
    return LOCAL_PATH


DB_PATH = _encontrar_banco()


def banco_status() -> dict:
    """Retorna informações sobre o banco de dados ativo."""
    from datetime import datetime

    eh_drive = DB_PATH != LOCAL_PATH
    existe   = os.path.exists(DB_PATH)

    try:
        tamanho    = os.path.getsize(DB_PATH) if existe else 0
        modificado = (
            datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime("%d/%m/%Y %H:%M")
            if existe else "—"
        )
    except Exception:
        tamanho    = 0
        modificado = "—"

    return {
        "caminho":    DB_PATH,
        "eh_drive":   eh_drive,
        "existe":     existe,
        "tamanho_kb": round(tamanho / 1024, 1),
        "modificado": modificado,
        "local_path": LOCAL_PATH,
    }


# ══════════════════════════════════════════════
#  CONEXÃO E INICIALIZAÇÃO
# ══════════════════════════════════════════════

def conectar() -> sqlite3.Connection:
    """Retorna uma conexão com WAL mode ativado e foreign keys habilitadas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # acesso por nome de coluna
    conn.execute("PRAGMA journal_mode=WAL") # WAL mode: melhor concorrência
    conn.execute("PRAGMA foreign_keys=ON")  # integridade referencial
    return conn


def inicializar_banco():
    """Cria todas as tabelas (se não existirem) e popula dados iniciais."""
    conn = conectar()
    try:
        _criar_tabelas(conn)
        _migrar_colunas_plataformas(conn)
        _migrar_tipo_salario_entregador(conn)
        _migrar_colunas_pessoas(conn)
        _migrar_carga_horaria(conn)
        _migrar_dados_pessoais(conn)
        _migrar_obs_fechamento(conn)
        conn.commit()
        _popular_dados_iniciais(conn)
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRIAÇÃO DAS TABELAS
# ══════════════════════════════════════════════

def _criar_tabelas(conn: sqlite3.Connection):
    """Executa os CREATE TABLE de todas as entidades do sistema."""

    conn.executescript("""
    -- Funcionários e entregadores cadastrados na loja
    CREATE TABLE IF NOT EXISTS cad_pessoas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nome            TEXT    NOT NULL,
        tipo            TEXT    NOT NULL CHECK(tipo IN ('ENTREGADOR','INTERNO')),
        cargo           TEXT,
        salario_base    REAL    DEFAULT 0,
        tipo_salario    TEXT    CHECK(tipo_salario IN ('FIXO','DIARIO','ENTREGADOR')),
        diaria_valor    REAL    DEFAULT 0,
        status_ativo    INTEGER NOT NULL DEFAULT 1  -- 1=ativo, 0=inativo
    );

    -- Bairros atendidos com taxa de entrega e repasse ao entregador
    CREATE TABLE IF NOT EXISTS cad_bairros (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_bairro         TEXT    NOT NULL UNIQUE,
        taxa_cobrada        REAL    NOT NULL DEFAULT 0,
        repasse_entregador  REAL    NOT NULL DEFAULT 0
    );

    -- Plataformas de delivery integradas
    CREATE TABLE IF NOT EXISTS cad_plataformas (
        id                              INTEGER PRIMARY KEY AUTOINCREMENT,
        nome                            TEXT    NOT NULL UNIQUE
                                                CHECK(nome IN ('iFood1','iFood2','99Food','Keeta')),
        comissao_pct                    REAL    NOT NULL DEFAULT 0,   -- % que a plataforma cobra
        taxa_transacao_pct              REAL    NOT NULL DEFAULT 0,   -- % de taxa por transação
        taxa_transacao_apenas_online    INTEGER NOT NULL DEFAULT 0,   -- 1 = só incide em pgtos online
        custo_logistico_km1             REAL    NOT NULL DEFAULT 0,   -- faixa 1 de custo logístico
        custo_logistico_km2             REAL    NOT NULL DEFAULT 0,   -- faixa 2
        custo_logistico_km3             REAL    NOT NULL DEFAULT 0,   -- faixa 3
        custo_logistico_km4             REAL    NOT NULL DEFAULT 0,   -- faixa 4
        custo_logistico_extra_por_km    REAL    NOT NULL DEFAULT 0,   -- valor por km excedente
        custo_logistico_maximo          REAL    NOT NULL DEFAULT 0,   -- teto do custo logístico
        entrega_hibrida_sem_logistica   INTEGER NOT NULL DEFAULT 0,   -- 1 = entrega híbrida sem custo logístico
        dia_repasse                     TEXT,                         -- dia da semana do repasse
        subsidio                        REAL    NOT NULL DEFAULT 0,   -- subsídio fixo por pedido
        ativo                           INTEGER NOT NULL DEFAULT 1
    );

    -- Canais de venda disponíveis no sistema (referência para vendas_pedidos)
    CREATE TABLE IF NOT EXISTS cad_canais (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        nome                  TEXT    NOT NULL UNIQUE,
        requer_bairro         INTEGER NOT NULL DEFAULT 0, -- 1 = canal de delivery (precisa de bairro)
        tem_comissao          INTEGER NOT NULL DEFAULT 0, -- 1 = canal de plataforma com comissão
        entregador_plataforma INTEGER NOT NULL DEFAULT 0  -- 1 = entregador é da plataforma (_Deles)
    );

    -- Métodos de pagamento aceitos
    CREATE TABLE IF NOT EXISTS cad_metodos_pag (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        nome  TEXT    NOT NULL UNIQUE,
        tipo  TEXT    NOT NULL
              CHECK(tipo IN ('FISICO','PLATAFORMA','BENEFICIO','CORTESIA'))
    );

    -- Categorias de movimentações extras (vale, sangria, consumo, etc.)
    CREATE TABLE IF NOT EXISTS cad_categorias_extra (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao       TEXT    NOT NULL UNIQUE,
        fluxo           TEXT    NOT NULL CHECK(fluxo IN ('ENTRADA','SAIDA')),
        usa_funcionario INTEGER NOT NULL DEFAULT 0  -- 1 se precisa vincular pessoa
    );

    -- Pedidos / vendas registradas
    CREATE TABLE IF NOT EXISTS vendas_pedidos (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        data                TEXT    NOT NULL,           -- formato ISO: YYYY-MM-DD
        hora                TEXT,                       -- HH:MM do lançamento
        canal               TEXT    NOT NULL            -- canal de venda validado
                                    CHECK(canal IN (
                                        'Mesa','Retirada_PDV','Delivery_PDV',
                                        'iFood1_Delivery','iFood1_Delivery_Deles','iFood1_Retirada',
                                        'iFood2_Delivery','iFood2_Delivery_Deles','iFood2_Retirada',
                                        '99Food_Delivery','99Food_Delivery_Deles','99Food_Retirada',
                                        'Keeta_Delivery','Keeta_Delivery_Deles','Keeta_Retirada'
                                    )),
        valor_total         REAL    NOT NULL DEFAULT 0,
        id_operador         INTEGER REFERENCES cad_pessoas(id) ON DELETE SET NULL,
        id_bairro           INTEGER REFERENCES cad_bairros(id) ON DELETE SET NULL,
        taxa_entrega        REAL    DEFAULT 0,
        repasse_entregador  REAL    DEFAULT 0,
        obs                 TEXT
    );

    -- Pagamentos vinculados a cada pedido (suporta split e cortesia por método)
    CREATE TABLE IF NOT EXISTS vendas_pagamentos (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pedido  INTEGER NOT NULL REFERENCES vendas_pedidos(id) ON DELETE CASCADE,
        metodo     TEXT    NOT NULL,          -- nome do método de pagamento
        valor      REAL    NOT NULL DEFAULT 0,
        cortesia   INTEGER NOT NULL DEFAULT 0 -- 1 = este pagamento é cortesia
    );

    -- Movimentações extras: vales, sangrias, consumos, corridas avulsas, etc.
    CREATE TABLE IF NOT EXISTS movimentacoes_extras (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        data         TEXT    NOT NULL,
        id_pessoa    INTEGER REFERENCES cad_pessoas(id) ON DELETE SET NULL,
        id_categoria INTEGER NOT NULL REFERENCES cad_categorias_extra(id),
        fluxo        TEXT    NOT NULL CHECK(fluxo IN ('ENTRADA','SAIDA')),
        metodo       TEXT,           -- nome do método de pagamento utilizado
        valor        REAL    NOT NULL DEFAULT 0,
        obs          TEXT
    );

    -- Resumo diário do caixa — chave primária é a data
    CREATE TABLE IF NOT EXISTS fluxo_caixa_diario (
        data                    TEXT PRIMARY KEY,       -- YYYY-MM-DD
        troco_inicial           REAL NOT NULL DEFAULT 0,
        total_especie_entradas  REAL NOT NULL DEFAULT 0,
        total_especie_saidas    REAL NOT NULL DEFAULT 0,
        saldo_teorico           REAL NOT NULL DEFAULT 0, -- calculado pelo sistema
        saldo_gaveta_real       REAL NOT NULL DEFAULT 0, -- conferido fisicamente
        diferenca               REAL NOT NULL DEFAULT 0  -- gaveta_real - saldo_teorico
    );

    -- Escala de trabalho diária por pessoa
    CREATE TABLE IF NOT EXISTS escalas_trabalho (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        data      TEXT    NOT NULL,
        id_pessoa INTEGER NOT NULL REFERENCES cad_pessoas(id) ON DELETE CASCADE,
        tipo      TEXT    NOT NULL
                  CHECK(tipo IN ('TRABALHOU','FALTA','FOLGA','FERIADO','EXTRA')),
        UNIQUE(data, id_pessoa)  -- uma entrada por pessoa por dia
    );

    -- Configurações gerais do sistema (chave–valor)
    CREATE TABLE IF NOT EXISTS cad_configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT NOT NULL DEFAULT ''
    );

    -- Dias fixos de trabalho por pessoa (grade semanal)
    CREATE TABLE IF NOT EXISTS cad_dias_fixos (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pessoa       INTEGER NOT NULL REFERENCES cad_pessoas(id) ON DELETE CASCADE,
        dia_semana      INTEGER NOT NULL,   -- 0=Segunda ... 6=Domingo
        horario_entrada TEXT,               -- HH:MM, nullable
        UNIQUE(id_pessoa, dia_semana)
    );

    -- Controle de fiados (clientes que levaram sem pagar)
    CREATE TABLE IF NOT EXISTS fiados (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        data_lancamento TEXT    NOT NULL,  -- YYYY-MM-DD
        nome_cliente    TEXT    NOT NULL,
        descricao       TEXT,
        valor           REAL    NOT NULL DEFAULT 0,
        pago            INTEGER NOT NULL DEFAULT 0,  -- 0=aberto, 1=quitado
        data_pagamento  TEXT,                        -- YYYY-MM-DD
        obs             TEXT
    );

    -- Registro de ponto diário por pessoa
    CREATE TABLE IF NOT EXISTS registros_ponto (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        data                    TEXT    NOT NULL,  -- YYYY-MM-DD
        id_pessoa               INTEGER NOT NULL REFERENCES cad_pessoas(id) ON DELETE CASCADE,
        hora_entrada            TEXT,              -- HH:MM
        hora_inicio_intervalo   TEXT,              -- HH:MM, nullable
        hora_fim_intervalo      TEXT,              -- HH:MM, nullable
        hora_saida              TEXT,              -- HH:MM, nullable
        obs                     TEXT,
        UNIQUE(data, id_pessoa)
    );

    -- Módulo de estoque interno
    CREATE TABLE IF NOT EXISTS estoque_categorias (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        nome  TEXT    NOT NULL UNIQUE,
        ativo INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS estoque_produtos (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        nome              TEXT    NOT NULL,
        id_categoria      INTEGER REFERENCES estoque_categorias(id) ON DELETE SET NULL,
        unidade           TEXT    NOT NULL DEFAULT 'un',
        preco_custo       REAL    NOT NULL DEFAULT 0,
        quantidade_atual  REAL    NOT NULL DEFAULT 0,
        quantidade_minima REAL    NOT NULL DEFAULT 0,
        ativo             INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS estoque_movimentacoes (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        data         TEXT    NOT NULL,
        hora         TEXT,
        id_produto   INTEGER NOT NULL REFERENCES estoque_produtos(id) ON DELETE CASCADE,
        tipo         TEXT    NOT NULL CHECK(tipo IN ('ENTRADA','SAIDA','AJUSTE')),
        quantidade   REAL    NOT NULL,
        preco_custo  REAL    NOT NULL DEFAULT 0,
        valor_total  REAL    NOT NULL DEFAULT 0,
        motivo       TEXT,
        obs          TEXT
    );

    CREATE TRIGGER IF NOT EXISTS trg_estoque_entrada
    AFTER INSERT ON estoque_movimentacoes
    WHEN NEW.tipo = 'ENTRADA'
    BEGIN
        UPDATE estoque_produtos SET quantidade_atual = quantidade_atual + NEW.quantidade
        WHERE id = NEW.id_produto;
    END;

    CREATE TRIGGER IF NOT EXISTS trg_estoque_saida
    AFTER INSERT ON estoque_movimentacoes
    WHEN NEW.tipo = 'SAIDA'
    BEGIN
        UPDATE estoque_produtos SET quantidade_atual = quantidade_atual - NEW.quantidade
        WHERE id = NEW.id_produto;
    END;

    CREATE TRIGGER IF NOT EXISTS trg_estoque_ajuste
    AFTER INSERT ON estoque_movimentacoes
    WHEN NEW.tipo = 'AJUSTE'
    BEGIN
        UPDATE estoque_produtos SET quantidade_atual = NEW.quantidade
        WHERE id = NEW.id_produto;
    END;

    -- Canais com '_Deles' usam entregador da plataforma: taxa e repasse devem ser zero.
    -- Trigger AFTER INSERT: corrige caso a camada Python envie valores incorretos.
    CREATE TRIGGER IF NOT EXISTS trg_zerar_taxas_deles_insert
    AFTER INSERT ON vendas_pedidos
    WHEN NEW.canal LIKE '%_Deles'
      AND (NEW.taxa_entrega != 0 OR NEW.repasse_entregador != 0)
    BEGIN
        UPDATE vendas_pedidos
           SET taxa_entrega = 0, repasse_entregador = 0
         WHERE id = NEW.id;
    END;

    -- Trigger AFTER UPDATE: mesma garantia em atualizações de canal ou taxas.
    CREATE TRIGGER IF NOT EXISTS trg_zerar_taxas_deles_update
    AFTER UPDATE ON vendas_pedidos
    WHEN NEW.canal LIKE '%_Deles'
      AND (NEW.taxa_entrega != 0 OR NEW.repasse_entregador != 0)
    BEGIN
        UPDATE vendas_pedidos
           SET taxa_entrega = 0, repasse_entregador = 0
         WHERE id = NEW.id;
    END;
    """)


# ══════════════════════════════════════════════
#  MIGRAÇÃO DE ESQUEMA
# ══════════════════════════════════════════════

def _migrar_tipo_salario_entregador(conn: sqlite3.Connection):
    """
    Adiciona 'ENTREGADOR' ao CHECK de tipo_salario em cad_pessoas.
    SQLite não suporta ALTER TABLE para mudar constraints; é preciso recriar a tabela.
    Idempotente: verifica o schema atual antes de agir.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='cad_pessoas'"
    ).fetchone()
    if row is None or "'DIARIO','ENTREGADOR'" in (row["sql"] or ""):
        return  # tabela inexistente ou já atualizada

    # executescript emite um COMMIT implícito antes de rodar — seguro aqui.
    conn.executescript("""
    PRAGMA foreign_keys = OFF;

    CREATE TABLE cad_pessoas_new (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nome            TEXT    NOT NULL,
        tipo            TEXT    NOT NULL CHECK(tipo IN ('ENTREGADOR','INTERNO')),
        cargo           TEXT,
        salario_base    REAL    DEFAULT 0,
        tipo_salario    TEXT    CHECK(tipo_salario IN ('FIXO','DIARIO','ENTREGADOR')),
        diaria_valor    REAL    DEFAULT 0,
        status_ativo    INTEGER NOT NULL DEFAULT 1
    );

    INSERT INTO cad_pessoas_new SELECT * FROM cad_pessoas;
    DROP TABLE cad_pessoas;
    ALTER TABLE cad_pessoas_new RENAME TO cad_pessoas;

    PRAGMA foreign_keys = ON;
    """)


def _migrar_colunas_plataformas(conn: sqlite3.Connection):
    """
    Adiciona colunas novas à tabela cad_plataformas em bancos já existentes.
    Idempotente: verifica via PRAGMA quais colunas já existem antes de adicionar.
    """
    colunas_existentes = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(cad_plataformas)")
    }
    novas_colunas = [
        ("taxa_transacao_apenas_online",  "INTEGER NOT NULL DEFAULT 0"),
        ("custo_logistico_km1",           "REAL    NOT NULL DEFAULT 0"),
        ("custo_logistico_km2",           "REAL    NOT NULL DEFAULT 0"),
        ("custo_logistico_km3",           "REAL    NOT NULL DEFAULT 0"),
        ("custo_logistico_km4",           "REAL    NOT NULL DEFAULT 0"),
        ("custo_logistico_extra_por_km",  "REAL    NOT NULL DEFAULT 0"),
        ("custo_logistico_maximo",        "REAL    NOT NULL DEFAULT 0"),
        ("entrega_hibrida_sem_logistica", "INTEGER NOT NULL DEFAULT 0"),
    ]
    for nome_col, definicao in novas_colunas:
        if nome_col not in colunas_existentes:
            conn.execute(
                f"ALTER TABLE cad_plataformas ADD COLUMN {nome_col} {definicao}"
            )


def _migrar_colunas_pessoas(conn: sqlite3.Connection):
    """
    Adiciona colunas de valores do holerite em cad_pessoas se não existirem.
    Idempotente: verifica PRAGMA table_info antes de cada ALTER TABLE.
    """
    colunas_existentes = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(cad_pessoas)")
    }
    novas_colunas = [
        ("valor_extra",   "REAL NOT NULL DEFAULT 50.0"),
        ("valor_feriado", "REAL NOT NULL DEFAULT 60.0"),
        ("valor_falta",   "REAL NOT NULL DEFAULT 60.0"),
    ]
    for nome_col, definicao in novas_colunas:
        if nome_col not in colunas_existentes:
            conn.execute(
                f"ALTER TABLE cad_pessoas ADD COLUMN {nome_col} {definicao}"
            )


def _migrar_carga_horaria(conn: sqlite3.Connection):
    """
    Adiciona coluna carga_horaria_diaria em cad_pessoas se não existir.
    Idempotente.
    """
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(cad_pessoas)")}
    if "carga_horaria_diaria" not in colunas:
        conn.execute(
            "ALTER TABLE cad_pessoas ADD COLUMN carga_horaria_diaria REAL NOT NULL DEFAULT 8.0"
        )


def _migrar_dados_pessoais(conn: sqlite3.Connection):
    """
    Adiciona colunas de dados pessoais em cad_pessoas se não existirem.
    Idempotente.
    """
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(cad_pessoas)")}
    novas = [
        ("cpf",                    "TEXT"),
        ("rg",                     "TEXT"),
        ("data_nascimento",        "TEXT"),
        ("telefone",               "TEXT"),
        ("endereco",               "TEXT"),
        ("observacoes_pessoais",   "TEXT"),
    ]
    for nome_col, definicao in novas:
        if nome_col not in colunas:
            conn.execute(f"ALTER TABLE cad_pessoas ADD COLUMN {nome_col} {definicao}")


def _migrar_obs_fechamento(conn: sqlite3.Connection):
    """Adiciona coluna obs_fechamento em fluxo_caixa_diario se não existir."""
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(fluxo_caixa_diario)")}
    if "obs_fechamento" not in colunas:
        conn.execute("ALTER TABLE fluxo_caixa_diario ADD COLUMN obs_fechamento TEXT")


# ══════════════════════════════════════════════
#  DADOS INICIAIS
# ══════════════════════════════════════════════

def _popular_dados_iniciais(conn: sqlite3.Connection):
    """
    Insere dados de referência apenas se a tabela ainda estiver vazia.
    Verifica SELECT COUNT(*) antes de cada bloco — não sobrescreve dados existentes.
    """

    def _vazia(tabela: str) -> bool:
        return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0] == 0

    # Métodos de pagamento padrão
    if _vazia("cad_metodos_pag"):
        conn.executemany(
            "INSERT INTO cad_metodos_pag (nome, tipo) VALUES (?, ?)",
            [
                ("Dinheiro", "FISICO"),
                ("Crédito",  "FISICO"),
                ("Débito",   "FISICO"),
                ("PIX",      "FISICO"),
                ("VA",       "BENEFICIO"),
                ("VR",       "BENEFICIO"),
                ("Voucher",  "CORTESIA"),
                ("iFood",    "PLATAFORMA"),
                ("99Food",   "PLATAFORMA"),
                ("Keeta",    "PLATAFORMA"),
                ("Fiado",    "CORTESIA"),
            ]
        )

    # Categorias extras padrão: (descricao, fluxo, usa_funcionario)
    if _vazia("cad_categorias_extra"):
        conn.executemany(
            "INSERT INTO cad_categorias_extra (descricao, fluxo, usa_funcionario) VALUES (?, ?, ?)",
            [
                ("Vale",          "SAIDA",   1),  # vale retirado por funcionário
                ("Sangria",       "SAIDA",   0),  # retirada de dinheiro do caixa
                ("Consumo",       "SAIDA",   1),  # consumo de funcionário
                ("Corrida Extra", "SAIDA",   1),  # corrida avulsa paga ao entregador
                ("Reentrega",     "SAIDA",   1),  # custo de reentrega
                ("Fiado",         "ENTRADA", 0),  # recebimento de fiado
                ("Pagamento",     "SAIDA",   1),  # pagamento diverso a funcionário
                ("Outros",        "ENTRADA", 0),  # entradas/saídas genéricas
            ]
        )

    # Plataformas de delivery com todas as configurações operacionais
    if _vazia("cad_plataformas"):
        conn.executemany(
            """INSERT INTO cad_plataformas
               (nome, comissao_pct, taxa_transacao_pct, taxa_transacao_apenas_online,
                custo_logistico_km1, custo_logistico_km2, custo_logistico_km3,
                custo_logistico_km4, custo_logistico_extra_por_km, custo_logistico_maximo,
                entrega_hibrida_sem_logistica, dia_repasse, subsidio, ativo)
               VALUES (?,?,?,?, ?,?,?,?,?,?, ?,?,?,?)""",
            [
                # iFood1 e iFood2 têm configuração idêntica
                ("iFood1", 12.0, 3.2, 1,  0.0,  0.0,  0.0,  0.0,  0.00, 0.0,  0, "QUARTA", 0.0, 1),
                ("iFood2", 12.0, 3.2, 1,  0.0,  0.0,  0.0,  0.0,  0.00, 0.0,  0, "QUARTA", 0.0, 1),
                # 99Food tem tabela de custo logístico por faixa de km
                ("99Food",  8.9, 3.2, 1,  3.49, 4.99, 5.99, 7.99, 0.10, 7.99, 1, "QUARTA", 0.0, 1),
                # Keeta: sem comissão e sem taxa de transação configuradas atualmente
                ("Keeta",   0.0, 0.0, 0,  0.0,  0.0,  0.0,  0.0,  0.00, 0.0,  0, "QUARTA", 0.0, 1),
            ]
        )

    # Canais de venda com suas características operacionais
    if _vazia("cad_canais"):
        conn.executemany(
            """INSERT INTO cad_canais
               (nome, requer_bairro, tem_comissao, entregador_plataforma)
               VALUES (?, ?, ?, ?)""",
            [
                # ── Canais próprios ──────────────────────────────────────────────
                ("Mesa",                   0, 0, 0),  # consumo no local
                ("Retirada_PDV",           0, 0, 0),  # cliente retira no balcão
                ("Delivery_PDV",           1, 0, 0),  # delivery pelo PDV, entregador próprio
                # ── iFood1 ───────────────────────────────────────────────────────
                ("iFood1_Delivery",        1, 1, 0),  # entregador próprio da loja via iFood1
                ("iFood1_Delivery_Deles",  1, 1, 1),  # entregador da plataforma iFood1
                ("iFood1_Retirada",        0, 1, 0),  # cliente retira, pedido via iFood1
                # ── iFood2 ───────────────────────────────────────────────────────
                ("iFood2_Delivery",        1, 1, 0),
                ("iFood2_Delivery_Deles",  1, 1, 1),
                ("iFood2_Retirada",        0, 1, 0),
                # ── 99Food ───────────────────────────────────────────────────────
                ("99Food_Delivery",        1, 1, 0),
                ("99Food_Delivery_Deles",  1, 1, 1),
                ("99Food_Retirada",        0, 1, 0),
                # ── Keeta ────────────────────────────────────────────────────────
                ("Keeta_Delivery",         1, 1, 0),
                ("Keeta_Delivery_Deles",   1, 1, 1),
                ("Keeta_Retirada",         0, 1, 0),
            ]
        )


# ══════════════════════════════════════════════
#  CRUD — cad_pessoas
# ══════════════════════════════════════════════

def pessoa_inserir(nome: str, tipo: str, cargo: str = None,
                   salario_base: float = 0.0, tipo_salario: str = None,
                   diaria_valor: float = None, status_ativo: bool = True) -> int:
    """
    Cadastra uma nova pessoa. Retorna o id gerado.
    Para tipo='ENTREGADOR': salario_base é forçado a 0, tipo_salario definido como
    'ENTREGADOR' e diaria_valor padrão é 40.0 (paga apenas se houver entregas no dia).
    """
    if tipo == "ENTREGADOR":
        salario_base  = 0.0
        tipo_salario  = tipo_salario or "ENTREGADOR"
        if diaria_valor is None:
            diaria_valor = 40.0
    if diaria_valor is None:
        diaria_valor = 0.0
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO cad_pessoas
               (nome, tipo, cargo, salario_base, tipo_salario, diaria_valor, status_ativo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (nome, tipo, cargo, salario_base, tipo_salario,
             diaria_valor, int(status_ativo))
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def pessoa_buscar(id_pessoa: int) -> sqlite3.Row | None:
    """Retorna uma pessoa pelo id, ou None se não encontrar."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM cad_pessoas WHERE id = ?", (id_pessoa,)
        ).fetchone()
    finally:
        conn.close()


def pessoa_listar(tipo: str = None, apenas_ativos: bool = True) -> list:
    """
    Lista pessoas. Filtra por tipo ('ENTREGADOR' ou 'INTERNO') e/ou status ativo.
    """
    conn = conectar()
    try:
        sql = "SELECT * FROM cad_pessoas WHERE 1=1"
        params = []
        if apenas_ativos:
            sql += " AND status_ativo = 1"
        if tipo:
            sql += " AND tipo = ?"
            params.append(tipo)
        sql += " ORDER BY nome"
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def pessoa_atualizar(id_pessoa: int, **campos) -> bool:
    """
    Atualiza campos de uma pessoa. Passe os campos como kwargs.
    Exemplo: pessoa_atualizar(3, salario_base=1500.0, status_ativo=0)
    Retorna True se alguma linha foi alterada.
    """
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [id_pessoa]
        cur = conn.execute(
            f"UPDATE cad_pessoas SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def pessoa_excluir(id_pessoa: int) -> bool:
    """Remove uma pessoa pelo id. Retorna True se excluída."""
    conn = conectar()
    try:
        cur = conn.execute("DELETE FROM cad_pessoas WHERE id = ?", (id_pessoa,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — cad_bairros
# ══════════════════════════════════════════════

def bairro_inserir(nome_bairro: str, taxa_cobrada: float = 0.0,
                   repasse_entregador: float = 0.0) -> int:
    """Cadastra um bairro. Retorna o id gerado."""
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO cad_bairros (nome_bairro, taxa_cobrada, repasse_entregador)
               VALUES (?, ?, ?)""",
            (nome_bairro, taxa_cobrada, repasse_entregador)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def bairro_buscar(id_bairro: int) -> sqlite3.Row | None:
    """Retorna um bairro pelo id."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM cad_bairros WHERE id = ?", (id_bairro,)
        ).fetchone()
    finally:
        conn.close()


def bairro_listar() -> list:
    """Lista todos os bairros em ordem alfabética."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM cad_bairros ORDER BY nome_bairro"
        ).fetchall()
    finally:
        conn.close()


def bairro_atualizar(id_bairro: int, **campos) -> bool:
    """Atualiza campos de um bairro. Retorna True se alterado."""
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [id_bairro]
        cur = conn.execute(
            f"UPDATE cad_bairros SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def bairro_excluir(id_bairro: int) -> bool:
    """Remove um bairro. Retorna True se excluído."""
    conn = conectar()
    try:
        cur = conn.execute("DELETE FROM cad_bairros WHERE id = ?", (id_bairro,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — cad_plataformas
# ══════════════════════════════════════════════

def plataforma_inserir(nome: str, comissao_pct: float = 0.0,
                       taxa_transacao_pct: float = 0.0, dia_repasse: str = None,
                       subsidio: float = 0.0, ativo: bool = True) -> int:
    """Cadastra uma plataforma. Retorna o id gerado."""
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO cad_plataformas
               (nome, comissao_pct, taxa_transacao_pct, dia_repasse, subsidio, ativo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nome, comissao_pct, taxa_transacao_pct,
             dia_repasse, subsidio, int(ativo))
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def plataforma_buscar(id_plataforma: int) -> sqlite3.Row | None:
    """Retorna uma plataforma pelo id."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM cad_plataformas WHERE id = ?", (id_plataforma,)
        ).fetchone()
    finally:
        conn.close()


def plataforma_listar(apenas_ativas: bool = True) -> list:
    """Lista plataformas, opcionalmente filtrando apenas as ativas."""
    conn = conectar()
    try:
        sql = "SELECT * FROM cad_plataformas"
        if apenas_ativas:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def plataforma_atualizar(id_plataforma: int, **campos) -> bool:
    """Atualiza campos de uma plataforma. Retorna True se alterado."""
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [id_plataforma]
        cur = conn.execute(
            f"UPDATE cad_plataformas SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def plataforma_excluir(id_plataforma: int) -> bool:
    """Remove uma plataforma. Retorna True se excluída."""
    conn = conectar()
    try:
        cur = conn.execute(
            "DELETE FROM cad_plataformas WHERE id = ?", (id_plataforma,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — cad_metodos_pag
# ══════════════════════════════════════════════

def metodo_pag_inserir(nome: str, tipo: str) -> int:
    """Cadastra um método de pagamento. Retorna o id gerado."""
    conn = conectar()
    try:
        cur = conn.execute(
            "INSERT INTO cad_metodos_pag (nome, tipo) VALUES (?, ?)",
            (nome, tipo)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def metodo_pag_buscar(id_metodo: int) -> sqlite3.Row | None:
    """Retorna um método de pagamento pelo id."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM cad_metodos_pag WHERE id = ?", (id_metodo,)
        ).fetchone()
    finally:
        conn.close()


def metodo_pag_listar(tipo: str = None) -> list:
    """Lista métodos de pagamento. Filtra por tipo se informado."""
    conn = conectar()
    try:
        if tipo:
            return conn.execute(
                "SELECT * FROM cad_metodos_pag WHERE tipo = ? ORDER BY nome",
                (tipo,)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM cad_metodos_pag ORDER BY nome"
        ).fetchall()
    finally:
        conn.close()


def metodo_pag_atualizar(id_metodo: int, **campos) -> bool:
    """Atualiza campos de um método de pagamento. Retorna True se alterado."""
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [id_metodo]
        cur = conn.execute(
            f"UPDATE cad_metodos_pag SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def metodo_pag_excluir(id_metodo: int) -> bool:
    """Remove um método de pagamento. Retorna True se excluído."""
    conn = conectar()
    try:
        cur = conn.execute(
            "DELETE FROM cad_metodos_pag WHERE id = ?", (id_metodo,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — cad_categorias_extra
# ══════════════════════════════════════════════

def categoria_extra_inserir(descricao: str, fluxo: str,
                             usa_funcionario: bool = False) -> int:
    """Cadastra uma categoria extra. Retorna o id gerado."""
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO cad_categorias_extra (descricao, fluxo, usa_funcionario)
               VALUES (?, ?, ?)""",
            (descricao, fluxo, int(usa_funcionario))
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def categoria_extra_buscar(id_categoria: int) -> sqlite3.Row | None:
    """Retorna uma categoria pelo id."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM cad_categorias_extra WHERE id = ?", (id_categoria,)
        ).fetchone()
    finally:
        conn.close()


def categoria_extra_listar(fluxo: str = None) -> list:
    """Lista categorias. Filtra por fluxo ('ENTRADA' ou 'SAIDA') se informado."""
    conn = conectar()
    try:
        if fluxo:
            return conn.execute(
                """SELECT * FROM cad_categorias_extra
                   WHERE fluxo = ? ORDER BY descricao""",
                (fluxo,)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM cad_categorias_extra ORDER BY descricao"
        ).fetchall()
    finally:
        conn.close()


def categoria_extra_atualizar(id_categoria: int, **campos) -> bool:
    """Atualiza campos de uma categoria. Retorna True se alterado."""
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [id_categoria]
        cur = conn.execute(
            f"UPDATE cad_categorias_extra SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def categoria_extra_excluir(id_categoria: int) -> bool:
    """Remove uma categoria. Retorna True se excluída."""
    conn = conectar()
    try:
        cur = conn.execute(
            "DELETE FROM cad_categorias_extra WHERE id = ?", (id_categoria,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — cad_configuracoes
# ══════════════════════════════════════════════

def config_obter(chave: str, padrao: str = "") -> str:
    """Retorna o valor de uma configuração pelo nome da chave."""
    conn = conectar()
    try:
        row = conn.execute(
            "SELECT valor FROM cad_configuracoes WHERE chave = ?", (chave,)
        ).fetchone()
        return row["valor"] if row else padrao
    finally:
        conn.close()


def config_salvar(chave: str, valor: str) -> None:
    """Cria ou atualiza uma configuração (upsert)."""
    conn = conectar()
    try:
        conn.execute(
            """INSERT INTO cad_configuracoes (chave, valor) VALUES (?, ?)
               ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor""",
            (chave, str(valor))
        )
        conn.commit()
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  HELPERS — canais de venda
# ══════════════════════════════════════════════

# Lista completa dos canais de venda aceitos pelo sistema.
CANAIS_VENDA = (
    "Mesa", "Retirada_PDV", "Delivery_PDV",
    "iFood1_Delivery", "iFood1_Delivery_Deles", "iFood1_Retirada",
    "iFood2_Delivery", "iFood2_Delivery_Deles", "iFood2_Retirada",
    "99Food_Delivery", "99Food_Delivery_Deles", "99Food_Retirada",
    "Keeta_Delivery",  "Keeta_Delivery_Deles",  "Keeta_Retirada",
)


def canal_usa_entregador_proprio(canal: str) -> bool:
    """
    Retorna True quando o canal usa entregador da plataforma ('_Deles').
    Nesses casos taxa_entrega e repasse_entregador são sempre zero.
    """
    return canal.endswith("_Deles")


def canal_listar() -> list:
    """Retorna todos os canais cadastrados em cad_canais, ordenados por id."""
    conn = conectar()
    try:
        return conn.execute("SELECT * FROM cad_canais ORDER BY id").fetchall()
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — vendas_pedidos
# ══════════════════════════════════════════════

def pedido_inserir(data: str, canal: str, valor_total: float,
                   hora: str = None,
                   id_operador: int = None, id_bairro: int = None,
                   taxa_entrega: float = 0.0, repasse_entregador: float = 0.0,
                   obs: str = None) -> int:
    """
    Registra um pedido/venda. Retorna o id gerado.
    Os pagamentos devem ser inseridos separadamente via pagamento_inserir().
    Canais com '_Deles' têm taxa e repasse forçados a zero automaticamente.
    """
    if canal.endswith("_Deles"):
        taxa_entrega = 0.0
        repasse_entregador = 0.0
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO vendas_pedidos
               (data, hora, canal, valor_total,
                id_operador, id_bairro, taxa_entrega, repasse_entregador, obs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data, hora, canal, valor_total,
             id_operador, id_bairro, taxa_entrega, repasse_entregador, obs)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def pedido_buscar(id_pedido: int) -> sqlite3.Row | None:
    """Retorna um pedido pelo id."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM vendas_pedidos WHERE id = ?", (id_pedido,)
        ).fetchone()
    finally:
        conn.close()


def pedido_listar_por_data(data: str) -> list:
    """Lista todos os pedidos de uma data específica (YYYY-MM-DD)."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM vendas_pedidos WHERE data = ? ORDER BY id",
            (data,)
        ).fetchall()
    finally:
        conn.close()


def pedido_listar_periodo(data_inicio: str, data_fim: str) -> list:
    """Lista pedidos entre duas datas (inclusive)."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT * FROM vendas_pedidos
               WHERE data BETWEEN ? AND ? ORDER BY data, id""",
            (data_inicio, data_fim)
        ).fetchall()
    finally:
        conn.close()


def pedido_atualizar(id_pedido: int, **campos) -> bool:
    """Atualiza campos de um pedido. Retorna True se alterado."""
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [id_pedido]
        cur = conn.execute(
            f"UPDATE vendas_pedidos SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def pedido_excluir(id_pedido: int) -> bool:
    """Remove um pedido. Retorna True se excluído."""
    conn = conectar()
    try:
        cur = conn.execute(
            "DELETE FROM vendas_pedidos WHERE id = ?", (id_pedido,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — vendas_pagamentos
# ══════════════════════════════════════════════

def pagamento_inserir(id_pedido: int, metodo: str, valor: float,
                      cortesia: bool = False) -> int:
    """Registra um pagamento vinculado a um pedido. Retorna o id gerado."""
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO vendas_pagamentos (id_pedido, metodo, valor, cortesia)
               VALUES (?, ?, ?, ?)""",
            (id_pedido, metodo, valor, int(cortesia))
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def pagamento_buscar_por_pedido(id_pedido: int) -> list:
    """Retorna todos os pagamentos de um pedido, na ordem de inserção."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM vendas_pagamentos WHERE id_pedido = ? ORDER BY id",
            (id_pedido,)
        ).fetchall()
    finally:
        conn.close()


def pagamento_deletar_por_pedido(id_pedido: int) -> int:
    """Remove todos os pagamentos de um pedido. Retorna a quantidade excluída."""
    conn = conectar()
    try:
        cur = conn.execute(
            "DELETE FROM vendas_pagamentos WHERE id_pedido = ?", (id_pedido,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def pedido_totais_por_data(data: str) -> dict:
    """
    Retorna um resumo agregado dos pedidos de um dia:
    qtd_pedidos, total_vendas, total_cortesias,
    total_taxa_entrega, total_repasse_entregador.
    Um pedido é considerado cortesia se ao menos um de seus pagamentos
    tem cortesia=1 na tabela vendas_pagamentos.
    """
    conn = conectar()
    try:
        row = conn.execute(
            """SELECT
                COUNT(*)                        AS qtd_pedidos,
                COALESCE(SUM(p.valor_total), 0) AS total_vendas,
                COALESCE(SUM(CASE WHEN EXISTS(
                    SELECT 1 FROM vendas_pagamentos vp
                    WHERE vp.id_pedido = p.id AND vp.cortesia = 1
                ) THEN p.valor_total ELSE 0 END), 0) AS total_cortesias,
                COALESCE(SUM(p.taxa_entrega), 0)         AS total_taxa_entrega,
                COALESCE(SUM(p.repasse_entregador), 0)   AS total_repasse_entregador
               FROM vendas_pedidos p WHERE p.data = ?""",
            (data,)
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — movimentacoes_extras
# ══════════════════════════════════════════════

def mov_extra_inserir(data: str, id_categoria: int, fluxo: str,
                      valor: float, id_pessoa: int = None,
                      metodo: str = None, obs: str = None) -> int:
    """Registra uma movimentação extra. Retorna o id gerado."""
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO movimentacoes_extras
               (data, id_pessoa, id_categoria, fluxo, metodo, valor, obs)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data, id_pessoa, id_categoria, fluxo, metodo, valor, obs)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def mov_extra_buscar(id_mov: int) -> sqlite3.Row | None:
    """Retorna uma movimentação pelo id."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM movimentacoes_extras WHERE id = ?", (id_mov,)
        ).fetchone()
    finally:
        conn.close()


def mov_extra_listar_por_data(data: str) -> list:
    """Lista movimentações extras de uma data, com nome da pessoa e categoria."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT me.*, cp.nome AS nome_pessoa, ce.descricao AS categoria
               FROM movimentacoes_extras me
               LEFT JOIN cad_pessoas cp ON cp.id = me.id_pessoa
               LEFT JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
               WHERE me.data = ? ORDER BY me.id""",
            (data,)
        ).fetchall()
    finally:
        conn.close()


def mov_extra_listar_periodo(data_inicio: str, data_fim: str,
                              fluxo: str = None) -> list:
    """Lista movimentações extras em um período, com filtro opcional de fluxo."""
    conn = conectar()
    try:
        sql = """SELECT me.*, cp.nome AS nome_pessoa, ce.descricao AS categoria
                 FROM movimentacoes_extras me
                 LEFT JOIN cad_pessoas cp ON cp.id = me.id_pessoa
                 LEFT JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
                 WHERE me.data BETWEEN ? AND ?"""
        params = [data_inicio, data_fim]
        if fluxo:
            sql += " AND me.fluxo = ?"
            params.append(fluxo)
        sql += " ORDER BY me.data, me.id"
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def mov_extra_atualizar(id_mov: int, **campos) -> bool:
    """Atualiza campos de uma movimentação. Retorna True se alterado."""
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [id_mov]
        cur = conn.execute(
            f"UPDATE movimentacoes_extras SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mov_extra_excluir(id_mov: int) -> bool:
    """Remove uma movimentação. Retorna True se excluída."""
    conn = conectar()
    try:
        cur = conn.execute(
            "DELETE FROM movimentacoes_extras WHERE id = ?", (id_mov,)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — fluxo_caixa_diario
# ══════════════════════════════════════════════

def fluxo_caixa_abrir(data: str, troco_inicial: float = 0.0) -> bool:
    """
    Cria o registro de caixa do dia se ainda não existir.
    Retorna True se criado, False se já existia.
    """
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO fluxo_caixa_diario (data, troco_inicial)
               VALUES (?, ?)""",
            (data, troco_inicial)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def fluxo_caixa_buscar(data: str) -> sqlite3.Row | None:
    """Retorna o registro de caixa de uma data específica."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM fluxo_caixa_diario WHERE data = ?", (data,)
        ).fetchone()
    finally:
        conn.close()


def fluxo_caixa_listar(data_inicio: str, data_fim: str) -> list:
    """Lista registros de caixa em um período."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT * FROM fluxo_caixa_diario
               WHERE data BETWEEN ? AND ? ORDER BY data""",
            (data_inicio, data_fim)
        ).fetchall()
    finally:
        conn.close()


def fluxo_caixa_atualizar(data: str, **campos) -> bool:
    """
    Atualiza campos do caixa de um dia. Retorna True se alterado.
    Exemplo: fluxo_caixa_atualizar('2024-01-15', saldo_gaveta_real=350.0)
    """
    if not campos:
        return False
    conn = conectar()
    try:
        set_clause = ", ".join(f"{col} = ?" for col in campos)
        valores = list(campos.values()) + [data]
        cur = conn.execute(
            f"UPDATE fluxo_caixa_diario SET {set_clause} WHERE data = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def fluxo_caixa_recalcular(data: str) -> dict:
    """
    Recalcula automaticamente os totais de espécie do dia com base nos pedidos
    e movimentações, atualiza o registro e retorna os valores calculados.
    Considera apenas transações em 'Dinheiro'.
    """
    conn = conectar()
    try:
        # Entradas em dinheiro vindas de pedidos (exclui pagamentos marcados como cortesia)
        row = conn.execute(
            """SELECT COALESCE(SUM(vp.valor), 0)
               FROM vendas_pagamentos vp
               JOIN vendas_pedidos p ON p.id = vp.id_pedido
               WHERE p.data = ? AND vp.metodo = 'Dinheiro' AND vp.cortesia = 0""",
            (data,)
        ).fetchone()
        entradas_pedidos = row[0] if row else 0.0

        # Entradas e saídas em dinheiro nas movimentações extras
        row_ent = conn.execute(
            """SELECT COALESCE(SUM(valor), 0) FROM movimentacoes_extras
               WHERE data = ? AND fluxo = 'ENTRADA' AND metodo = 'Dinheiro'""",
            (data,)
        ).fetchone()
        row_sai = conn.execute(
            """SELECT COALESCE(SUM(valor), 0) FROM movimentacoes_extras
               WHERE data = ? AND fluxo = 'SAIDA' AND metodo = 'Dinheiro'""",
            (data,)
        ).fetchone()

        total_entradas = entradas_pedidos + (row_ent[0] if row_ent else 0.0)
        total_saidas   = row_sai[0] if row_sai else 0.0

        # Recupera o troco inicial para compor o saldo teórico
        fc = conn.execute(
            "SELECT troco_inicial FROM fluxo_caixa_diario WHERE data = ?", (data,)
        ).fetchone()
        troco = fc["troco_inicial"] if fc else 0.0

        saldo_teorico = troco + total_entradas - total_saidas

        conn.execute(
            """UPDATE fluxo_caixa_diario
               SET total_especie_entradas = ?,
                   total_especie_saidas   = ?,
                   saldo_teorico          = ?
               WHERE data = ?""",
            (total_entradas, total_saidas, saldo_teorico, data)
        )
        conn.commit()
        return {
            "total_especie_entradas": total_entradas,
            "total_especie_saidas":   total_saidas,
            "saldo_teorico":          saldo_teorico,
        }
    finally:
        conn.close()


def fluxo_caixa_fechar(data: str, saldo_gaveta_real: float,
                       obs_fechamento: str | None = None) -> dict:
    """
    Registra o saldo físico da gaveta, calcula a diferença e fecha o caixa.
    Retorna o resumo completo do fechamento.
    """
    calc = fluxo_caixa_recalcular(data)
    diferenca = saldo_gaveta_real - calc["saldo_teorico"]
    kwargs = dict(saldo_gaveta_real=saldo_gaveta_real, diferenca=diferenca)
    if obs_fechamento is not None:
        kwargs["obs_fechamento"] = obs_fechamento
    fluxo_caixa_atualizar(data, **kwargs)
    return {**calc, "saldo_gaveta_real": saldo_gaveta_real, "diferenca": diferenca,
            "obs_fechamento": obs_fechamento}


def fluxo_caixa_historico_divergencias(
    data_inicio: str,
    data_fim: str,
    apenas_divergencias: bool = False,
) -> list:
    """
    Retorna histórico de fechamentos no período.
    Se apenas_divergencias=True, filtra apenas dias com diferença != 0.
    Cada item: data, troco_inicial, saldo_teorico, saldo_gaveta_real,
               diferenca, obs_fechamento.
    """
    conn = conectar()
    try:
        rows = conn.execute(
            """SELECT data, troco_inicial, saldo_teorico, saldo_gaveta_real,
                      diferenca, obs_fechamento
               FROM fluxo_caixa_diario
               WHERE data BETWEEN ? AND ?
               ORDER BY data""",
            (data_inicio, data_fim),
        ).fetchall()
        result = [dict(r) for r in rows]
        if apenas_divergencias:
            result = [r for r in result if abs(r.get("diferenca") or 0.0) > 0.001]
        return result
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — escalas_trabalho
# ══════════════════════════════════════════════

def escala_registrar(data: str, id_pessoa: int, tipo: str) -> int:
    """
    Registra ou substitui a escala de uma pessoa em um dia.
    Retorna o id do registro criado/atualizado.
    """
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO escalas_trabalho (data, id_pessoa, tipo)
               VALUES (?, ?, ?)
               ON CONFLICT(data, id_pessoa) DO UPDATE SET tipo = excluded.tipo""",
            (data, id_pessoa, tipo)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def escala_buscar(data: str, id_pessoa: int) -> sqlite3.Row | None:
    """Retorna a escala de uma pessoa em uma data específica."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM escalas_trabalho WHERE data = ? AND id_pessoa = ?",
            (data, id_pessoa)
        ).fetchone()
    finally:
        conn.close()


def escala_listar_por_data(data: str) -> list:
    """Lista todas as escalas de um dia, com nome e tipo da pessoa."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT et.*, cp.nome, cp.tipo AS tipo_pessoa, cp.cargo
               FROM escalas_trabalho et
               JOIN cad_pessoas cp ON cp.id = et.id_pessoa
               WHERE et.data = ? ORDER BY cp.nome""",
            (data,)
        ).fetchall()
    finally:
        conn.close()


def escala_listar_por_pessoa(id_pessoa: int,
                              data_inicio: str, data_fim: str) -> list:
    """Lista escalas de uma pessoa em um período."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT * FROM escalas_trabalho
               WHERE id_pessoa = ? AND data BETWEEN ? AND ?
               ORDER BY data""",
            (id_pessoa, data_inicio, data_fim)
        ).fetchall()
    finally:
        conn.close()


def escala_contar_dias(id_pessoa: int, data_inicio: str, data_fim: str,
                        tipo: str = "TRABALHOU") -> int:
    """
    Conta quantos dias de um tipo específico uma pessoa tem em um período.
    Útil para calcular diárias ou faltas no fechamento mensal.
    """
    conn = conectar()
    try:
        row = conn.execute(
            """SELECT COUNT(*) FROM escalas_trabalho
               WHERE id_pessoa = ? AND data BETWEEN ? AND ? AND tipo = ?""",
            (id_pessoa, data_inicio, data_fim, tipo)
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def escala_excluir(data: str, id_pessoa: int) -> bool:
    """Remove o registro de escala de uma pessoa em uma data. Retorna True se excluído."""
    conn = conectar()
    try:
        cur = conn.execute(
            "DELETE FROM escalas_trabalho WHERE data = ? AND id_pessoa = ?",
            (data, id_pessoa)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — cad_dias_fixos
# ══════════════════════════════════════════════

def dias_fixos_salvar(id_pessoa: int, dias: list) -> None:
    """
    Substitui todos os dias fixos de uma pessoa.
    Recebe lista de dicts com chaves 'dia_semana' (int) e 'horario_entrada' (str|None).
    Apaga todos os registros da pessoa e reinsere (replace completo).
    """
    conn = conectar()
    try:
        conn.execute(
            "DELETE FROM cad_dias_fixos WHERE id_pessoa = ?", (id_pessoa,)
        )
        if dias:
            conn.executemany(
                """INSERT INTO cad_dias_fixos (id_pessoa, dia_semana, horario_entrada)
                   VALUES (?, ?, ?)""",
                [(id_pessoa, d["dia_semana"], d.get("horario_entrada")) for d in dias],
            )
        conn.commit()
    finally:
        conn.close()


def dias_fixos_listar(id_pessoa: int) -> list:
    """Retorna os dias fixos de uma pessoa ordenados por dia_semana."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT * FROM cad_dias_fixos
               WHERE id_pessoa = ?
               ORDER BY dia_semana""",
            (id_pessoa,),
        ).fetchall()
    finally:
        conn.close()


def dias_fixos_listar_todos() -> list:
    """Retorna todos os dias fixos com nome e tipo da pessoa (JOIN cad_pessoas)."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT df.*, p.nome, p.tipo
               FROM cad_dias_fixos df
               JOIN cad_pessoas p ON p.id = df.id_pessoa
               ORDER BY p.nome, df.dia_semana"""
        ).fetchall()
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — registros_ponto
# ══════════════════════════════════════════════

def ponto_registrar_entrada(data: str, id_pessoa: int, hora_entrada: str) -> int:
    """
    Upsert: cria o registro do dia ou atualiza hora_entrada se já existir.
    Retorna o id do registro.
    """
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO registros_ponto (data, id_pessoa, hora_entrada)
               VALUES (?, ?, ?)
               ON CONFLICT(data, id_pessoa) DO UPDATE SET hora_entrada = excluded.hora_entrada""",
            (data, id_pessoa, hora_entrada),
        )
        conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        row = conn.execute(
            "SELECT id FROM registros_ponto WHERE data = ? AND id_pessoa = ?",
            (data, id_pessoa),
        ).fetchone()
        return row["id"] if row else -1
    finally:
        conn.close()


def ponto_registrar_intervalo(data: str, id_pessoa: int,
                               hora_inicio: str, hora_fim: str) -> bool:
    """
    Atualiza hora_inicio_intervalo e hora_fim_intervalo do registro do dia.
    Retorna True se o registro foi encontrado e atualizado.
    """
    conn = conectar()
    try:
        cur = conn.execute(
            """UPDATE registros_ponto
               SET hora_inicio_intervalo = ?, hora_fim_intervalo = ?
               WHERE data = ? AND id_pessoa = ?""",
            (hora_inicio, hora_fim, data, id_pessoa),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def ponto_registrar_saida(data: str, id_pessoa: int, hora_saida: str) -> bool:
    """
    Atualiza hora_saida do registro do dia.
    Retorna True se o registro foi encontrado e atualizado.
    """
    conn = conectar()
    try:
        cur = conn.execute(
            """UPDATE registros_ponto
               SET hora_saida = ?
               WHERE data = ? AND id_pessoa = ?""",
            (hora_saida, data, id_pessoa),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def ponto_buscar(data: str, id_pessoa: int) -> sqlite3.Row | None:
    """Retorna o registro de ponto de uma pessoa em uma data, ou None."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM registros_ponto WHERE data = ? AND id_pessoa = ?",
            (data, id_pessoa),
        ).fetchone()
    finally:
        conn.close()


def ponto_listar_por_data(data: str) -> list:
    """Retorna todos os registros de ponto de uma data, com nome e tipo da pessoa."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT rp.*, p.nome, p.tipo
               FROM registros_ponto rp
               JOIN cad_pessoas p ON p.id = rp.id_pessoa
               WHERE rp.data = ?
               ORDER BY p.nome""",
            (data,),
        ).fetchall()
    finally:
        conn.close()


def ponto_listar_periodo(id_pessoa: int, data_inicio: str, data_fim: str) -> list:
    """Retorna os registros de ponto de uma pessoa em um intervalo de datas."""
    conn = conectar()
    try:
        return conn.execute(
            """SELECT * FROM registros_ponto
               WHERE id_pessoa = ? AND data BETWEEN ? AND ?
               ORDER BY data""",
            (id_pessoa, data_inicio, data_fim),
        ).fetchall()
    finally:
        conn.close()


def ponto_calcular_horas(
    hora_entrada: str,
    hora_saida: str,
    hora_ini_intervalo: str = None,
    hora_fim_intervalo: str = None,
    carga_horaria: float = 8.0,
) -> dict:
    """
    Calcula horas trabalhadas e extras a partir dos registros de ponto.
    Retorna dict com horas_brutas, minutos_intervalo, horas_liquidas,
    horas_extras, completo e erro.
    """
    from datetime import datetime, timedelta

    if not hora_entrada or not hora_saida:
        return {
            "horas_brutas":      0.0,
            "minutos_intervalo": 0,
            "horas_liquidas":    0.0,
            "horas_extras":      0.0,
            "completo":          False,
            "erro":              "Entrada ou saída não registrada",
        }

    try:
        fmt    = "%H:%M"
        entrada = datetime.strptime(hora_entrada, fmt)
        saida   = datetime.strptime(hora_saida,   fmt)

        if saida < entrada:
            saida += timedelta(days=1)

        horas_brutas = (saida - entrada).total_seconds() / 3600

        if hora_ini_intervalo and hora_fim_intervalo:
            ini_int = datetime.strptime(hora_ini_intervalo, fmt)
            fim_int = datetime.strptime(hora_fim_intervalo, fmt)
            if fim_int < ini_int:
                fim_int += timedelta(days=1)
            minutos_intervalo = int((fim_int - ini_int).total_seconds() / 60)
        else:
            minutos_intervalo = 60

        horas_liquidas = horas_brutas - minutos_intervalo / 60
        horas_extras   = horas_liquidas - carga_horaria

        return {
            "horas_brutas":      round(horas_brutas, 2),
            "minutos_intervalo": minutos_intervalo,
            "horas_liquidas":    round(horas_liquidas, 2),
            "horas_extras":      round(horas_extras, 2),
            "completo":          True,
            "erro":              None,
        }
    except Exception as ex:
        return {
            "horas_brutas":      0.0,
            "minutos_intervalo": 0,
            "horas_liquidas":    0.0,
            "horas_extras":      0.0,
            "completo":          False,
            "erro":              str(ex),
        }


def ponto_resumo_mensal(
    id_pessoa: int,
    data_inicio: str,
    data_fim: str,
    salario_base: float = 0.0,
    diaria_valor: float = 0.0,
    tipo_salario: str = "FIXO",
    carga_horaria: float = 8.0,
) -> dict:
    """
    Calcula resumo de horas do mês para uma pessoa.
    Retorna dict com totais de horas, valor das extras e lista de detalhes por dia.
    """
    conn = conectar()
    try:
        registros = conn.execute(
            """SELECT * FROM registros_ponto
               WHERE id_pessoa = ? AND data BETWEEN ? AND ?
               ORDER BY data""",
            (id_pessoa, data_inicio, data_fim),
        ).fetchall()
    finally:
        conn.close()

    if tipo_salario == "FIXO":
        valor_hora = salario_base / 220 if salario_base > 0 else 0.0
    elif tipo_salario == "DIARIO":
        valor_hora = diaria_valor / carga_horaria if diaria_valor > 0 else 0.0
    else:
        valor_hora = 0.0

    valor_adicional  = valor_hora * 0.5
    valor_hora_extra = valor_hora + valor_adicional

    detalhes        = []
    total_brutas    = 0.0
    total_liquidas  = 0.0
    total_extras    = 0.0
    total_faltantes = 0.0
    dias_completos  = 0

    for r in registros:
        calc = ponto_calcular_horas(
            r["hora_entrada"],
            r["hora_saida"],
            r["hora_inicio_intervalo"],
            r["hora_fim_intervalo"],
            carga_horaria,
        )
        if calc["completo"]:
            dias_completos  += 1
            total_brutas    += calc["horas_brutas"]
            total_liquidas  += calc["horas_liquidas"]
            if calc["horas_extras"] > 0:
                total_extras    += calc["horas_extras"]
            else:
                total_faltantes += abs(calc["horas_extras"])

        detalhes.append({
            "data":         r["data"],
            "hora_entrada": r["hora_entrada"],
            "hora_saida":   r["hora_saida"],
            "hora_ini_int": r["hora_inicio_intervalo"],
            "hora_fim_int": r["hora_fim_intervalo"],
            **calc,
        })

    return {
        "dias_com_ponto":        len(registros),
        "dias_completos":        dias_completos,
        "total_horas_brutas":    round(total_brutas,    2),
        "total_horas_liquidas":  round(total_liquidas,  2),
        "total_horas_extras":    round(total_extras,    2),
        "total_horas_faltantes": round(total_faltantes, 2),
        "valor_hora_normal":     round(valor_hora,       2),
        "valor_adicional_extra": round(valor_adicional,  2),
        "valor_total_extras":    round(total_extras * valor_hora_extra, 2),
        "detalhes":              detalhes,
    }


# ══════════════════════════════════════════════
#  AUXILIAR — pré-população de escala pelo grade
# ══════════════════════════════════════════════

def escala_pre_popular_do_dia(data_iso: str) -> int:
    """
    Para cada pessoa ativa que tem aquela data como dia fixo de trabalho
    (weekday do Python == dia_semana cadastrado) e ainda NÃO tem registro
    em escalas_trabalho para aquela data, insere com tipo='TRABALHOU'.
    Retorna a quantidade de registros inseridos.
    """
    from datetime import date as _date
    dia_semana_alvo = _date.fromisoformat(data_iso).weekday()

    conn = conectar()
    try:
        candidatos = conn.execute(
            """SELECT df.id_pessoa
               FROM cad_dias_fixos df
               JOIN cad_pessoas p ON p.id = df.id_pessoa
               WHERE df.dia_semana = ?
                 AND p.status_ativo = 1
                 AND NOT EXISTS (
                     SELECT 1 FROM escalas_trabalho e
                     WHERE e.data = ? AND e.id_pessoa = df.id_pessoa
                 )""",
            (dia_semana_alvo, data_iso),
        ).fetchall()

        inseridos = 0
        for row in candidatos:
            conn.execute(
                """INSERT OR IGNORE INTO escalas_trabalho (data, id_pessoa, tipo)
                   VALUES (?, ?, 'TRABALHOU')""",
                (data_iso, row["id_pessoa"]),
            )
            inseridos += 1

        conn.commit()
        return inseridos
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CÁLCULO DE PAGAMENTO — ENTREGADOR
# ══════════════════════════════════════════════

def calcular_pagamento_entregador(id_pessoa: int, data: str) -> dict:
    """
    Calcula o pagamento de um entregador em um dia específico.
    Retorna um dict com:
      - total_entregas : quantidade de pedidos com repasse vinculados a esta pessoa
      - soma_taxas     : soma dos repasse_entregador desses pedidos
      - diaria         : diaria_valor da pessoa se total_entregas > 0, senão 0
      - corridas_extras: soma de movimentações com categoria 'Corrida Extra'
      - vales          : soma de movimentações com categoria 'Vale'
      - total_liquido  : diaria + soma_taxas + corridas_extras - vales
    """
    conn = conectar()
    try:
        # Busca o valor de diária cadastrado para este entregador
        pessoa = conn.execute(
            "SELECT diaria_valor, tipo_salario FROM cad_pessoas WHERE id = ?", (id_pessoa,)
        ).fetchone()
        diaria_valor = pessoa["diaria_valor"] if pessoa else 0.0
        tipo_salario = pessoa["tipo_salario"] if pessoa else ""

        # Fallback: entregadores cadastrados antes da lógica de diária usam 40.0
        if tipo_salario == "ENTREGADOR" and diaria_valor == 0.0:
            diaria_valor = 40.0

        # Conta pedidos onde esta pessoa foi operadora e há repasse registrado
        row_entr = conn.execute(
            """SELECT COUNT(*)                              AS qtd,
                      COALESCE(SUM(repasse_entregador), 0) AS soma
               FROM vendas_pedidos
               WHERE data = ? AND id_operador = ? AND repasse_entregador > 0""",
            (data, id_pessoa)
        ).fetchone()
        total_entregas = row_entr["qtd"]
        soma_taxas     = row_entr["soma"]

        # Diária só é paga se houve pelo menos 1 entrega no dia
        diaria = diaria_valor if total_entregas > 0 else 0.0

        # Corridas extras vinculadas a esta pessoa no dia
        row_extras = conn.execute(
            """SELECT COALESCE(SUM(me.valor), 0) AS total
               FROM movimentacoes_extras me
               JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
               WHERE me.data = ? AND me.id_pessoa = ? AND ce.descricao = 'Corrida Extra'""",
            (data, id_pessoa)
        ).fetchone()
        corridas_extras = row_extras["total"] if row_extras else 0.0

        # Vales sacados por esta pessoa no dia
        row_vales = conn.execute(
            """SELECT COALESCE(SUM(me.valor), 0) AS total
               FROM movimentacoes_extras me
               JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
               WHERE me.data = ? AND me.id_pessoa = ? AND ce.descricao = 'Vale'""",
            (data, id_pessoa)
        ).fetchone()
        vales = row_vales["total"] if row_vales else 0.0

        return {
            "total_entregas":  total_entregas,
            "soma_taxas":      soma_taxas,
            "diaria":          diaria,
            "corridas_extras": corridas_extras,
            "vales":           vales,
            "total_liquido":   diaria + soma_taxas + corridas_extras - vales,
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — fiados
# ══════════════════════════════════════════════

def fiado_inserir(data: str, nome_cliente: str, valor: float,
                  descricao: str = None, obs: str = None) -> int:
    """Registra um novo fiado. Retorna o id gerado."""
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO fiados (data_lancamento, nome_cliente, valor, descricao, obs)
               VALUES (?, ?, ?, ?, ?)""",
            (data, nome_cliente, valor, descricao, obs),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def fiado_listar(apenas_abertos: bool = True) -> list:
    """Lista fiados. Se apenas_abertos=True, filtra pago=0."""
    conn = conectar()
    try:
        sql = "SELECT * FROM fiados"
        if apenas_abertos:
            sql += " WHERE pago = 0"
        sql += " ORDER BY pago ASC, data_lancamento DESC"
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def fiado_quitar(id_fiado: int, data_pagamento: str) -> bool:
    """Marca o fiado como quitado. Retorna True se encontrado."""
    conn = conectar()
    try:
        cur = conn.execute(
            "UPDATE fiados SET pago = 1, data_pagamento = ? WHERE id = ?",
            (data_pagamento, id_fiado),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def fiado_buscar(id_fiado: int) -> sqlite3.Row | None:
    """Retorna um fiado pelo id, ou None."""
    conn = conectar()
    try:
        return conn.execute(
            "SELECT * FROM fiados WHERE id = ?", (id_fiado,)
        ).fetchone()
    finally:
        conn.close()


def fiado_excluir(id_fiado: int) -> bool:
    """Remove um fiado pelo id. Retorna True se excluído."""
    conn = conectar()
    try:
        cur = conn.execute("DELETE FROM fiados WHERE id = ?", (id_fiado,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def fiado_total_aberto() -> float:
    """Retorna a soma dos valores de fiados ainda não quitados."""
    conn = conectar()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(valor), 0) AS total FROM fiados WHERE pago = 0"
        ).fetchone()
        return row["total"] if row else 0.0
    finally:
        conn.close()


def fluxo_caixa_listar_lancamentos(data_inicio: str, data_fim: str) -> list:
    """
    Retorna extrato cronológico de lançamentos do caixa no período.
    Inclui: troco inicial, vendas (pedidos), extras (exceto Pagamento) e
    movimentações de categoria Pagamento.
    Colunas: data, hora, seq, ref_id, tipo, descricao,
             entrada, saida, metodo, canal, nome_pessoa
    """
    conn = conectar()
    try:
        sql = """
            WITH pag_count AS (
                SELECT id_pedido, COUNT(*) AS qtd_pags
                FROM vendas_pagamentos
                GROUP BY id_pedido
            )
            SELECT
                fcd.data,
                '00:00'           AS hora,
                1                 AS seq,
                NULL              AS ref_id,
                'TROCO_INICIAL'   AS tipo,
                'Troco inicial'   AS descricao,
                fcd.troco_inicial AS entrada,
                0.0               AS saida,
                'Dinheiro'        AS metodo,
                NULL              AS canal,
                NULL              AS nome_pessoa
            FROM fluxo_caixa_diario fcd
            WHERE fcd.data BETWEEN ? AND ?

            UNION ALL

            SELECT
                p.data,
                COALESCE(p.hora, '23:59')  AS hora,
                2                           AS seq,
                p.id                        AS ref_id,
                'VENDA'                     AS tipo,
                'Pedido #' || p.id ||
                    CASE WHEN COALESCE(pc.qtd_pags, 1) > 1
                         THEN ' (' || pc.qtd_pags || ' pagtos)'
                         ELSE ''
                    END                     AS descricao,
                p.valor_total               AS entrada,
                0.0                         AS saida,
                NULL                        AS metodo,
                p.canal                     AS canal,
                NULL                        AS nome_pessoa
            FROM vendas_pedidos p
            LEFT JOIN pag_count pc ON pc.id_pedido = p.id
            WHERE p.data BETWEEN ? AND ?

            UNION ALL

            SELECT
                me.data,
                NULL    AS hora,
                3       AS seq,
                me.id   AS ref_id,
                'EXTRA' AS tipo,
                ce.descricao || COALESCE(' — ' || cp.nome, '') AS descricao,
                CASE WHEN me.fluxo = 'ENTRADA' THEN me.valor ELSE 0.0 END AS entrada,
                CASE WHEN me.fluxo = 'SAIDA'   THEN me.valor ELSE 0.0 END AS saida,
                me.metodo  AS metodo,
                NULL       AS canal,
                cp.nome    AS nome_pessoa
            FROM movimentacoes_extras me
            LEFT JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
            LEFT JOIN cad_pessoas cp ON cp.id = me.id_pessoa
            WHERE me.data BETWEEN ? AND ?
              AND ce.descricao != 'Pagamento'

            UNION ALL

            SELECT
                me.data,
                NULL        AS hora,
                4           AS seq,
                me.id       AS ref_id,
                'PAGAMENTO' AS tipo,
                ce.descricao || COALESCE(' — ' || cp.nome, '') AS descricao,
                CASE WHEN me.fluxo = 'ENTRADA' THEN me.valor ELSE 0.0 END AS entrada,
                CASE WHEN me.fluxo = 'SAIDA'   THEN me.valor ELSE 0.0 END AS saida,
                me.metodo  AS metodo,
                NULL       AS canal,
                cp.nome    AS nome_pessoa
            FROM movimentacoes_extras me
            LEFT JOIN cad_categorias_extra ce ON ce.id = me.id_categoria
            LEFT JOIN cad_pessoas cp ON cp.id = me.id_pessoa
            WHERE me.data BETWEEN ? AND ?
              AND ce.descricao = 'Pagamento'

            ORDER BY data, hora, seq, ref_id
        """
        return conn.execute(
            sql,
            (data_inicio, data_fim,
             data_inicio, data_fim,
             data_inicio, data_fim,
             data_inicio, data_fim)
        ).fetchall()
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — estoque_categorias
# ══════════════════════════════════════════════

def estoque_categoria_inserir(nome: str) -> int:
    conn = conectar()
    try:
        cur = conn.execute(
            "INSERT INTO estoque_categorias (nome) VALUES (?)", (nome,)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def estoque_categoria_listar(apenas_ativas: bool = True) -> list:
    conn = conectar()
    try:
        sql = "SELECT * FROM estoque_categorias"
        if apenas_ativas:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def estoque_categoria_atualizar(id_cat: int, **campos) -> bool:
    if not campos:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in campos)
    valores    = list(campos.values()) + [id_cat]
    conn = conectar()
    try:
        cur = conn.execute(
            f"UPDATE estoque_categorias SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — estoque_produtos
# ══════════════════════════════════════════════

def estoque_produto_inserir(
    nome: str,
    id_categoria: int | None,
    unidade: str,
    preco_custo: float,
    quantidade_atual: float,
    quantidade_minima: float,
) -> int:
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO estoque_produtos
               (nome, id_categoria, unidade, preco_custo,
                quantidade_atual, quantidade_minima)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nome, id_categoria, unidade, preco_custo,
             quantidade_atual, quantidade_minima),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def estoque_produto_buscar(id_produto: int):
    conn = conectar()
    try:
        return conn.execute(
            """SELECT ep.*, ec.nome AS nome_categoria
               FROM estoque_produtos ep
               LEFT JOIN estoque_categorias ec ON ec.id = ep.id_categoria
               WHERE ep.id = ?""",
            (id_produto,),
        ).fetchone()
    finally:
        conn.close()


def estoque_produto_listar(
    apenas_ativos: bool = True,
    id_categoria: int | None = None,
) -> list:
    conn = conectar()
    try:
        conds  = []
        params = []
        if apenas_ativos:
            conds.append("ep.ativo = 1")
        if id_categoria is not None:
            conds.append("ep.id_categoria = ?")
            params.append(id_categoria)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        return conn.execute(
            f"""SELECT ep.*,
                       ec.nome AS nome_categoria,
                       CASE WHEN ep.quantidade_atual <= ep.quantidade_minima
                            THEN 1 ELSE 0 END AS abaixo_minimo
               FROM estoque_produtos ep
               LEFT JOIN estoque_categorias ec ON ec.id = ep.id_categoria
               {where}
               ORDER BY ep.nome""",
            params,
        ).fetchall()
    finally:
        conn.close()


def estoque_produto_atualizar(id_produto: int, **campos) -> bool:
    if not campos:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in campos)
    valores    = list(campos.values()) + [id_produto]
    conn = conectar()
    try:
        cur = conn.execute(
            f"UPDATE estoque_produtos SET {set_clause} WHERE id = ?", valores
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CRUD — estoque_movimentacoes
# ══════════════════════════════════════════════

def estoque_mov_inserir(
    data: str,
    id_produto: int,
    tipo: str,
    quantidade: float,
    preco_custo: float,
    motivo: str | None = None,
    obs: str | None = None,
) -> int:
    from datetime import datetime
    hora        = datetime.now().strftime("%H:%M")
    valor_total = quantidade * preco_custo
    conn = conectar()
    try:
        cur = conn.execute(
            """INSERT INTO estoque_movimentacoes
               (data, hora, id_produto, tipo, quantidade,
                preco_custo, valor_total, motivo, obs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data, hora, id_produto, tipo, quantidade,
             preco_custo, valor_total, motivo, obs),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def estoque_mov_listar(
    data_inicio: str,
    data_fim: str,
    id_produto: int | None = None,
    tipo: str | None = None,
) -> list:
    conn = conectar()
    try:
        conds  = ["em.data BETWEEN ? AND ?"]
        params = [data_inicio, data_fim]
        if id_produto is not None:
            conds.append("em.id_produto = ?")
            params.append(id_produto)
        if tipo is not None:
            conds.append("em.tipo = ?")
            params.append(tipo)
        where = "WHERE " + " AND ".join(conds)
        return conn.execute(
            f"""SELECT em.*, ep.nome AS nome_produto, ep.unidade
               FROM estoque_movimentacoes em
               JOIN estoque_produtos ep ON ep.id = em.id_produto
               {where}
               ORDER BY em.data DESC, em.hora DESC, em.id DESC""",
            params,
        ).fetchall()
    finally:
        conn.close()


def estoque_mov_excluir(id_mov: int) -> bool:
    conn = conectar()
    try:
        row = conn.execute(
            "SELECT id_produto FROM estoque_movimentacoes WHERE id = ?",
            (id_mov,),
        ).fetchone()
        if not row:
            return False
        id_produto = row["id_produto"]
        conn.execute("DELETE FROM estoque_movimentacoes WHERE id = ?", (id_mov,))
        # Recalcula quantidade_atual ignorando triggers (que já dispararam)
        conn.execute(
            """UPDATE estoque_produtos
               SET quantidade_atual = (
                   SELECT COALESCE(SUM(
                       CASE tipo
                           WHEN 'ENTRADA' THEN quantidade
                           WHEN 'SAIDA'   THEN -quantidade
                           ELSE 0
                       END
                   ), 0)
                   FROM estoque_movimentacoes
                   WHERE id_produto = ?
               )
               WHERE id = ?""",
            (id_produto, id_produto),
        )
        # Para AJUSTE a lógica acima é incorreta — o último AJUSTE define a base.
        # Recalcula corretamente: encontra o último AJUSTE e aplica entradas/saídas após ele.
        ultimo_ajuste = conn.execute(
            """SELECT id, quantidade FROM estoque_movimentacoes
               WHERE id_produto = ? AND tipo = 'AJUSTE'
               ORDER BY data DESC, hora DESC, id DESC
               LIMIT 1""",
            (id_produto,),
        ).fetchone()
        if ultimo_ajuste:
            base = ultimo_ajuste["quantidade"]
            delta = conn.execute(
                """SELECT COALESCE(SUM(
                       CASE tipo WHEN 'ENTRADA' THEN quantidade
                                 WHEN 'SAIDA'   THEN -quantidade
                                 ELSE 0 END
                   ), 0) AS d
                   FROM estoque_movimentacoes
                   WHERE id_produto = ? AND id > ?""",
                (id_produto, ultimo_ajuste["id"]),
            ).fetchone()["d"]
            conn.execute(
                "UPDATE estoque_produtos SET quantidade_atual = ? WHERE id = ?",
                (base + delta, id_produto),
            )
        conn.commit()
        return True
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  CONSULTAS — alertas e valor
# ══════════════════════════════════════════════

def estoque_produtos_abaixo_minimo() -> list:
    conn = conectar()
    try:
        return conn.execute(
            """SELECT ep.*, ec.nome AS nome_categoria
               FROM estoque_produtos ep
               LEFT JOIN estoque_categorias ec ON ec.id = ep.id_categoria
               WHERE ep.ativo = 1
                 AND ep.quantidade_atual <= ep.quantidade_minima
               ORDER BY ep.nome""",
        ).fetchall()
    finally:
        conn.close()


def estoque_valor_total() -> float:
    conn = conectar()
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(quantidade_atual * preco_custo), 0) AS total
               FROM estoque_produtos WHERE ativo = 1"""
        ).fetchone()
        return row["total"] if row else 0.0
    finally:
        conn.close()


# ══════════════════════════════════════════════
#  INICIALIZAÇÃO AO IMPORTAR
# ══════════════════════════════════════════════

inicializar_banco()


# ══════════════════════════════════════════════
#  RECRIAÇÃO COMPLETA (apaga tudo do zero)
# ══════════════════════════════════════════════

def recriar_banco_zerado():
    """
    Apaga o arquivo .db e todos os arquivos WAL/SHM auxiliares do SQLite,
    depois recria todas as tabelas e popula os dados iniciais do zero.
    Só deve ser chamada via `python database.py --reset`.
    """
    for ext in ("", "-wal", "-shm"):
        caminho = DB_PATH + ext
        if os.path.exists(caminho):
            os.remove(caminho)
            print(f"Removido: {caminho}")
    inicializar_banco()
    print(f"Banco recriado do zero em: {DB_PATH}")


# ══════════════════════════════════════════════
#  EXECUÇÃO DIRETA
# ══════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--reset" in sys.argv:
        recriar_banco_zerado()
    else:
        inicializar_banco()
        conn = conectar()
        try:
            n = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
            ).fetchone()[0]
        finally:
            conn.close()
        print(f"Banco inicializado. {n} tabelas verificadas.")
