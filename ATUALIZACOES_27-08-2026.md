# Relatório de Atualizações e Registro Técnico — 27/08/2026

Este documento registra todas as alterações arquiteturais, correções de segurança, mudanças de schema e migrações de dados executadas no projeto **Gestão Loja** na data de 27/08/2026.

---

## 1. Contexto e Causa Raiz dos Problemas Anteriores

### 1.1 O Incidente de Abertura Indevida do Banco de Produção em Desenvolvimento
* **Causa Raiz**: A função `_encontrar_banco()` em `database.py` verificava prioritariamente os caminhos da unidade `G:\` (Google Drive) e conectava silenciosamente na base de produção se a unidade estivesse montada no computador do desenvolvedor.
* **Efeito Colateral**: Durante execuções locais de desenvolvimento, a rotina `_popular_dados_iniciais()` rodou contra o banco real da loja, inserindo as categorias `259` a `262` diretamente na base de produção.
* **Ausência de Logs**: O aplicativo não emitia mensagens visíveis sobre qual arquivo (`LOCAL` vs. `GOOGLE DRIVE`) estava aberto.

### 1.2 Fragmentação e Poluição de Categorias no Caixa
* **Duplicação de compras**: Foram criadas no passado múltiplas categorias para a mesma finalidade contábil (*"Compra Fornecedor Informal"*, *"Pagamento Fornecedor"*, *"Reposição de Estoque"* e *"Compra Fornecedor / Insumos"*).
* **Fornecedores no cadastro de pessoas/categorias**: Falta de distinção entre funcionários e prestadores/fornecedores informais gerava categorias com nomes de pessoas (ex.: *"Sacolão Vera"*, *"Sacolão Naldo"*, *"Retirada Adriana"*).

---

## 2. Fase 0 — Contenção e Trava Permanente de Segurança

### 2.1 Padrão Invertido para Desenvolvimento Seguro
* Por padrão, a aplicação **SEMPRE opera em banco local** (`loja_caixa.db` na raiz da aplicação) ou em modo de teste isolado (`GESTAOLOJA_TESTE`).
* O acesso ao Google Drive de produção passou a exigir autorização explícita via **arquivo marcador `loja_producao.flag`** colocado ao lado do executável no momento do build de produção (com a variável de ambiente `GESTAOLOJA_PROD=1` disponível para emergências de suporte).

### 2.2 Bloqueio Ruidoso com Diálogo Nativo
* Se o sistema detectar os caminhos do Google Drive em uma máquina que **não** possua autorização de produção, ele **aborta imediatamente**.
* No executável sem console (`--noconsole`), a parada exibe uma janela modal nativa do Windows (`ctypes.windll.user32.MessageBoxW` com `MB_ICONERROR`), impedindo o aplicativo de operar em silêncio.

### 2.3 Proteção contra Race Condition no Boot da Loja
* No Windows dos computadores da loja, o executável pode iniciar antes que o Google Drive Desktop termine de montar a unidade `G:`.
* Implementada a rotina `_localizar_banco_producao(timeout_segundos=30, intervalo=2.0)`:
  - Realiza espera ativa por até 30 segundos testando a montagem da unidade.
  - Se o timeout expirar, exibe diálogo nativo com botões **"Repetir" / "Cancelar"** (`MB_RETRYCANCEL`).
  - Ao clicar em "Repetir", reinicia o ciclo de espera; ao clicar em "Cancelar", encerra via `sys.exit(1)`.
  - **Nunca faz fallback silencioso para um banco local vazio em máquinas de produção**.

### 2.4 Proteção de Escrita no Seed Inicial
* Em `_popular_dados_iniciais(conn)`, adicionada guarda estrita:
  ```python
  if not _vazia("cad_pessoas"):
      return
  ```
* Se o banco já possuir pessoas cadastradas (base viva de produção ou teste com histórico), **nenhum dado inicial é reinserido**. Novas categorias ou dados devem entrar exclusivamente via migrações idempotentes e versionadas.

---

## 3. Fase 1 — Schema, Migração e Consolidação de Dados

### 3.1 Auditoria do Controle de Acesso Existente
* Comprovado que o sistema já possui autenticação por PIN de 4 dígitos e papéis em `cad_pessoas`:
  - `ADMIN` (ex.: Richard, ID 1)
  - `GERENTE` (ex.: Jessica, ID 4)
  - `OPERADOR` (ex.: Adilson, ID 3)
* A sessão ativa fica disponível globalmente via `database.sessao_obter()` e `database.sessao_tem_acesso(perfil_minimo)`.

### 3.2 Alterações de Schema Aplicadas em `cad_categorias_extra` e `cad_fornecedores`

| Tabela | Alteração | Detalhe Técnico |
| :--- | :--- | :--- |
| `cad_categorias_extra` | `ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1` | Permite desativar categorias legadas sem deletá-las do banco. |
| `cad_categorias_extra` | `ADD COLUMN codigo TEXT DEFAULT NULL` | Chave imutável do sistema (evita acoplamento por descrição). |
| `cad_categorias_extra` | `CREATE UNIQUE INDEX ux_categorias_codigo ON cad_categorias_extra(codigo)` | Unicidade estrita para chaves não-nulas; permite múltiplos `NULL`. |
| `cad_categorias_extra` | `ADD COLUMN usa_fornecedor INTEGER NOT NULL DEFAULT 0` | Identifica se a categoria exige/vincula fornecedor no formulário. |
| `cad_categorias_extra` | `ADD COLUMN min_perfil TEXT NOT NULL DEFAULT 'OPERADOR'` | Permite restringir categorias gerenciais no banco de dados. |
| `cad_fornecedores` | `ADD COLUMN tipo TEXT NOT NULL DEFAULT 'PRODUTO'` | Diferencia fornecedores de `PRODUTO`, prestadores de `SERVICO` e `OUTRO`. |
| `movimentacoes_extras` | `CREATE INDEX ix_mov_fornecedor ON movimentacoes_extras(id_fornecedor)` | Otimização de consultas agrupadas por fornecedor. |
| `movimentacoes_extras` | `CREATE INDEX ix_mov_categoria ON movimentacoes_extras(id_categoria)` | Otimização de filtros por categoria. |
| `movimentacoes_extras` | `CREATE INDEX ix_mov_data_fluxo ON movimentacoes_extras(data, fluxo)` | Acelera relatórios de entradas/saídas por período. |

> **Nota Técnica sobre SQLite**: O SQLite não permite `ALTER TABLE ADD COLUMN ... UNIQUE` diretamente (retorna erro `Cannot add a UNIQUE column`). A abordagem correta é adicionar a coluna sem a constraint e em seguida criar o índice `CREATE UNIQUE INDEX`.

### 3.3 Tabela Final de Categorias Consolidadas em Produção

| ID | Descrição | Fluxo | Código Imutável | Ativo | Fornecedor | Perfil Mínimo | Observação |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | Vale | SAIDA | `vale` | **1** | 0 | OPERADOR | Operacional diário |
| **2** | Sangria | SAIDA | `sangria` | **1** | 0 | OPERADOR | Retirada para cofre/banco |
| **3** | Consumo | NEUTRO | `consumo` | **1** | 0 | OPERADOR | Consumo de equipe com 20% |
| **4** | Corrida Extra | NEUTRO | `corrida_extra` | **1** | 0 | OPERADOR | Motoboy |
| **5** | Reentrega | NEUTRO | `reentrega` | **1** | 0 | OPERADOR | Motoboy |
| **6** | Fiado | ENTRADA | `fiado` | **1** | 0 | OPERADOR | Recebimento de fiados |
| **7** | Pagamento | SAIDA | `pagamento_pessoal` | **0** | 0 | OPERADOR | **Inativada para seleção manual** (gravada por holerite) |
| **8** | Outros | ENTRADA | `outros` | **1** | 0 | OPERADOR | Entradas/saídas gerais |
| **249** | Reposição de Estoque | SAIDA | — | **0** | 0 | OPERADOR | Inativada (11 históricos preservados) |
| **251** | Sacolão Naldo | SAIDA | — | **0** | 0 | OPERADOR | Inativada (3 históricos preservados) |
| **252** | Sacolão Vera | SAIDA | — | **0** | 0 | OPERADOR | Inativada (0 usos) |
| **253** | Sacolão palhada | SAIDA | — | **0** | 0 | OPERADOR | Inativada (0 usos) |
| **254** | Rio minas | SAIDA | — | **0** | 0 | OPERADOR | Inativada (0 usos) |
| **255** | Empréstimo Parcela | SAIDA | `emprestimo_parcela` | **1** | 0 | OPERADOR | Mantida ativa para parcelas/ifood |
| **256** | Retirada Adriana | SAIDA | — | **0** | 0 | OPERADOR | Inativada (Registro 561 preservado) |
| **257** | Pagamento Fornecedor | SAIDA | — | **0** | 0 | OPERADOR | Inativada (0 usos) |
| **258** | Compra Fornecedor Informal | SAIDA | — | **0** | 0 | OPERADOR | Inativada (0 usos) |
| **259** | Retirada (Nova Yaki) | SAIDA | `retirada_socia` | **1** | 0 | **GERENTE** | **Restrita à gerência / sócias** |
| **260** | Manutenção / Serviços | SAIDA | `manutencao` | **1** | **1** | OPERADOR | Prestadores terceiros (freezer, eletricista) |
| **261** | Aporte / Troco | ENTRADA | `aporte` | **1** | 0 | OPERADOR | Suprimento de troco |
| **262** | Compra Fornecedor / Insumos | SAIDA | `compra_fornecedor` | **1** | **1** | OPERADOR | **Única categoria canônica de compras** |

### 3.4 Migração de Dados e Tratamento do Registro 561
* **5 lançamentos** da categoria `256` (*"Retirada Adriana"*) foram migrados para a categoria canônica `259` (*"Retirada (Nova Yaki)"*).
* **Registro 561 (R$ 300,00, PIX em 2026-08-03 lançado em nome de Jessica)**: Foi explicitamente **isolado** e mantido na categoria `256` até confirmação de negócio pela gerência.

---

## 4. Testes de Robustez e Procedimento de Segurança

### 4.1 Teste de Rollback Atômico em Falha
* No Python `sqlite3`, o driver padrão executa commits implícitos antes de comandos DDL.
* Para garantir transacionalidade real, a migração `_migrar_schema_fase1(conn)` força `conn.isolation_level = None` e encapsula tudo em `BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK`.
* **Validação**: Ao simular uma falha proposital (renomeação de `"Vale"` para `"Vale "`), 100% das alterações (DDL de tabelas, índices e updates) foram revertidas instantaneamente pelo SQLite, comprovado via `PRAGMA table_info`.

### 4.2 Backups Criados e Preservados
* `backups_producao/loja_caixa_BACKUP_PROD_20260827_155053.db` (1.425.408 bytes)
* `backups_producao/loja_caixa_BACKUP_IMEDIATO_20260827_155148.db` (1.425.408 bytes)

### 4.3 Verificação de Integridade Pós-Aplicação
* A migração foi executada no Google Drive em **0,08s**.
* Executado `PRAGMA integrity_check`: retorno **`['ok']`**.
* Teste de fumaça: a versão em produção da aplicação continuou operando sem quebra de compatibilidade.

---

## 5. Histórico de Commits desta Sessão

1. **`ab1a19f`** — `feat(database): Implementa trava permanente de seguranca para ambiente de producao, retentativa ativa de boot e protecao contra escrita acidental`
2. **`77f1157`** — `feat(database): Adiciona migracao de schema e dados da Fase 1 (aplicada em producao em 2026-08-27)`

Ambos os commits foram enviados e sincronizados com `origin/main` no GitHub.
