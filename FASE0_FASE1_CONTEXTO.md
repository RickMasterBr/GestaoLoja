# Reforma de Movimentações/Caixa — Fase 0 e Fase 1

**Status:** concluídas e aplicadas em produção
**Commits:** `ab1a19f` (trava de ambiente), `77f1157` (schema + migração de dados)
**Data de aplicação em produção:** 2026-08-27

Este documento existe para que ninguém — humano ou agente — repita os erros já cometidos e corrigidos aqui. Leia antes de mexer em `database.py`, em `cad_categorias_extra`/`cad_fornecedores`/`movimentacoes_extras`, ou em qualquer coisa que toque o banco de produção.

---

## 1. O problema original

A tela de Movimentações (`views/extras.py`) tinha gargalos relatados pela operação:

- Formulário genérico, sem separar visualmente entrada/saída.
- Sem opção para prestador de serviço terceiro (manutenção) — operador era forçado a selecionar o próprio nome como "funcionário" pra conseguir salvar.
- Reposição de estoque/compras exigia selecionar funcionário em vez de fornecedor. Isso gerava categorias avulsas por fornecedor informal (ex.: "Sacolão da Vera", "Sacolão Naldo").
- Categoria "Pagamento" ambígua: confundida com pagamento de holerite de funcionário (que é feito por outra tela).
- Nenhuma integração com boletos/contas a pagar.
- Nenhum relatório agrupado (por fornecedor, categoria, método).

**Prova documental do problema:** lançamento ID 635, 2026-08-27, Jessica (gerente) selecionou o próprio nome, categoria "Pagamento", método PIX, R$ 550,00, obs "saída serralheiro" — porque não havia opção correta pra despesa de terceiro.

---

## 2. Erro nº 1 — nunca refatore em cima de trabalho não commitado

No início desta sessão, `views/extras.py` tinha um refactor parcial e **já reconhecidamente errado** escrito por cima de trabalho anterior testado e não commitado (nota avulsa, fixes de boleto, N+1 de Entregadores, holerite flexível, etc.). Isso criou hunks entrelaçados difíceis de separar.

**Correção aplicada:** antes de qualquer código novo, sempre:
1. `git status` / `git diff` e classificar cada hunk (trabalho concluído vs. refactor em andamento).
2. Confirmar via `git log` que trabalho concluído já está em commit alcançável pelo HEAD — não assumir de memória.
3. Se o refactor errado estiver isolado, descartar. Se estiver entrelaçado num arquivo, considerar preservar numa branch de descarte (ex.: `descarte/refactor-mov-v1`) só para consulta, e reescrever do zero em cima do HEAD limpo.

**Regra permanente:** nunca inicie uma reestruturação grande sem primeiro rodar `git status` e classificar o que já existe.

---

## 3. Erro nº 2 — o ambiente de dev escrevia no banco de produção

### O que aconteceu
`database.py` resolvia o caminho do banco assim: **se o Google Drive estivesse montado (`G:\...`) e o arquivo existisse, usava direto** — não havia nenhuma verificação de que a execução era "dev" ou "produção". O modo de teste (`GESTAOLOJA_TESTE`) era opt-in; o padrão era produção.

Consequência real: um boot de desenvolvimento, sem querer, gravou 4 categorias novas (`Retirada (Nova Yaki)`, `Manutenção / Serviços`, `Aporte / Troco`, `Compra Fornecedor / Insumos`) direto no `loja_caixa.db` real, via `_popular_dados_iniciais`. O dano ficou restrito a essas 4 linhas (0 usos vinculados, `integrity_check` ok, nenhuma tabela residual) — mas o mecanismo que permitiu isso era grave: se alguma migração de recriação de tabela (`DROP TABLE` + `RENAME`) tivesse rodado nesse mesmo boot, o estrago seria de outra ordem, num arquivo sincronizado por Google Drive Mirror com a loja em uso ao vivo.

### Correção aplicada (commit `ab1a19f`)
- **Inversão de padrão:** o sistema agora assume desenvolvimento por padrão. Produção só é acessada se houver autorização explícita.
- **Autorização por arquivo marcador** (`loja_producao.flag`), gerado pelo processo de build de produção — não configurado manualmente por máquina (isso seria esquecível). Variável de ambiente `GESTAOLOJA_PROD=1` existe só como via secundária de emergência.
- **Falha ruidosa:** se o Drive for detectado sem autorização de produção, o processo aborta com `MessageBoxW` nativo do Windows (visível mesmo em EXE sem console) e `sys.exit(1)`. Nunca cai silenciosamente para banco local.
- **Retentativa com timeout no boot de produção legítimo:** o Drive pode montar `G:\` com atraso na inicialização do Windows. `_localizar_banco_producao` espera em loop (30s / intervalo 2s) e, se esgotar, oferece diálogo "Repetir/Cancelar" — nunca finge que o banco local (vazio) é produção.
- **Proteção de escrita:** `_popular_dados_iniciais` agora verifica `not _vazia("cad_pessoas")` e retorna imediatamente se a base já tem dados. Seed automático só roda em banco 100% virgem.
- **`loja_producao.flag` no `.gitignore`** — nunca pode ser versionado, ou qualquer clone de dev herdaria autorização de produção.
- Testado contra 5 cenários (dev sem Drive, dev com Drive sem autorização, produção legítima, `GESTAOLOJA_TESTE` normal, `GESTAOLOJA_TESTE` apontando erroneamente pro Drive) — todos passaram.

### Regra permanente
- **Nunca rode scripts soltos contra `database.py` sem `GESTAOLOJA_TESTE` setado explicitamente na sessão do terminal.**
- Qualquer novo processo automático (backup, tarefa agendada) que só venha a existir no futuro precisa reavaliar o timeout de retentativa — hoje não há teto duro porque não existe nenhum processo desassistido; se isso mudar, adicionar teto de tentativas com saída automática.
- `_popular_dados_iniciais` não é mais o lugar para introduzir categorias/dados novos em produção. Qualquer alteração de dados em base já populada exige migração explícita e idempotente (ver seção 5).

---

## 4. Ambiente de teste — sempre validar contra cópia real, não banco virgem

`GESTAOLOJA_TESTE` criava um banco do zero, com o schema mais recente do `CREATE TABLE IF NOT EXISTS`. Isso significa que **nenhuma migração idempotente (`ALTER TABLE` condicional) era realmente exercitada** — um banco novo já nasce com a coluna. Foi assim que a suposição inicial errada ("falta `ALTER TABLE` para `id_fornecedor`") passou despercebida — a função já existia, só não estava sendo testada contra um banco antigo de verdade.

**Regra permanente:** para testar qualquer migração de schema, sempre copiar o `loja_caixa.db` real de produção (nunca abrir o original — usar `?mode=ro` ou cópia física) e rodar a migração nessa cópia. Um banco criado do zero não representa o estado real da loja.

---

## 5. Padrão obrigatório para qualquer migração de schema/dados daqui em diante

Todo `ALTER TABLE` ou `UPDATE` em massa em produção segue este processo, sem exceção:

1. **Levantamento primeiro, sem escrever nada** — `PRAGMA table_info`, contagens de uso real, distribuição de valores, tudo antes de desenhar o schema.
2. **Migração como função idempotente e nomeada** (ex.: `_migrar_schema_fase1(conn)`), chamada dentro de `inicializar_banco()`, nunca como script solto.
3. **Transação atômica manual** (`conn.isolation_level = None`, `BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK` explícito) — nunca depender de autocommit implícito do Python.
4. **Toda alteração é aditiva.** `ALTER TABLE ADD COLUMN` com `DEFAULT`, nunca `DROP TABLE` / recriação de tabela em produção. Isso é o que garante que um EXE antigo, rodando ao mesmo tempo em outro PC da loja, não quebre ao ler o mesmo arquivo.
5. **SQLite não aceita `UNIQUE` inline em `ALTER TABLE ADD COLUMN`.** Usar `ADD COLUMN` sem constraint + `CREATE UNIQUE INDEX` separado (aceita múltiplos `NULL` automaticamente).
6. **Qualquer atribuição de dado por `WHERE descricao = '...'` precisa validar `rowcount == 1`** e abortar com erro claro se não bater — nunca deixar um `UPDATE` que não encontrou nada passar em silêncio.
7. **Teste de rollback obrigatório antes de aplicar em produção:** introduzir um defeito de propósito (ex.: descrição com espaço extra) numa cópia, confirmar que a exceção dispara E que o `ROLLBACK` desfaz literalmente tudo (DDL e DML) — verificado com `PRAGMA table_info` antes/depois, não por suposição.
8. **Backup fresco imediatamente antes de aplicar em produção** — cópia do `.db` (+ `-wal`/`-shm` se existirem) tirada nos segundos anteriores à execução real, fora da pasta do Drive, com timestamp no nome.
9. **Avisar quem usa o sistema ao vivo** (a gerente, no caso) para não haver lançamento concorrente durante a execução.
10. **Pós-aplicação:** `PRAGMA integrity_check`, conferir o estado final da tabela, e rodar um teste de fumaça abrindo a tela afetada com o EXE/código atual (sem alterações) pra confirmar que nada quebrou.
11. **Commitar o código da migração imediatamente**, mesmo já aplicada — nunca deixar produção migrada e o repositório sem o código correspondente.

---

## 6. Estado final do schema (aplicado em produção em 2026-08-27)

### `cad_categorias_extra` — colunas novas
| Coluna | Tipo | Default | Notnull |
|---|---|---|---|
| `ativo` | INTEGER | 1 | sim |
| `codigo` | TEXT | NULL | não |
| `usa_fornecedor` | INTEGER | 0 | sim |
| `min_perfil` | TEXT | 'OPERADOR' | sim |

Índice: `CREATE UNIQUE INDEX ux_categorias_codigo ON cad_categorias_extra(codigo)`.

### Categorias — estado final
| ID | Descrição | Fluxo | `codigo` | `ativo` | `usa_fornecedor` | `min_perfil` |
|---|---|---|---|---|---|---|
| 1 | Vale | SAIDA | vale | ATIVO | não | OPERADOR |
| 2 | Sangria | SAIDA | sangria | ATIVO | não | OPERADOR |
| 3 | Consumo | NEUTRO | consumo | ATIVO | não | OPERADOR |
| 4 | Corrida Extra | NEUTRO | corrida_extra | ATIVO | não | OPERADOR |
| 5 | Reentrega | NEUTRO | reentrega | ATIVO | não | OPERADOR |
| 6 | Fiado | ENTRADA | fiado | ATIVO | não | OPERADOR |
| 7 | Pagamento | SAIDA | pagamento_pessoal | **INATIVO** | não | OPERADOR |
| 8 | Outros | ENTRADA | outros | ATIVO | não | OPERADOR |
| 249 | Reposição de Estoque | SAIDA | — | **INATIVO** | não | OPERADOR |
| 251–254 | Sacolão Naldo / Vera / palhada / Rio minas | SAIDA | — | **INATIVO** | não | OPERADOR |
| 255 | Empréstimo Parcela | SAIDA | emprestimo_parcela | ATIVO | não | OPERADOR |
| 256 | Retirada Adriana | SAIDA | — | **INATIVO** | não | OPERADOR |
| 257 | Pagamento Fornecedor | SAIDA | — | **INATIVO** | não | OPERADOR |
| 258 | Compra Fornecedor Informal | SAIDA | — | **INATIVO** | não | OPERADOR |
| 259 | Retirada (Nova Yaki) | SAIDA | retirada_socia | ATIVO | não | **GERENTE** |
| 260 | Manutenção / Serviços | SAIDA | manutencao | ATIVO | **sim** | OPERADOR |
| 261 | Aporte / Troco | ENTRADA | aporte | ATIVO | não | OPERADOR |
| 262 | Compra Fornecedor / Insumos | SAIDA | compra_fornecedor | ATIVO | **sim** | OPERADOR |

**Categorias 260 e 262 são as únicas canônicas para fluxo de fornecedor/manutenção.** Não recriar categorias equivalentes — isso reintroduziria o problema original ("Sacolão da Vera").

**Categorias inativas nunca foram deletadas** — preservam FK e histórico. `ativo = 0` só remove da seleção de novos lançamentos.

### `cad_fornecedores` — coluna nova
| Coluna | Tipo | Default | Notnull |
|---|---|---|---|
| `tipo` | TEXT | 'PRODUTO' | sim |

Valores esperados: `PRODUTO`, `SERVICO`, `OUTRO`. Os 10 fornecedores existentes ficaram todos como `PRODUTO` — nenhum foi reclassificado ainda. **Prestadores de serviço/manutenção (eletricista, técnico de freezer, etc.) devem ser cadastrados aqui com `tipo = 'SERVICO'`**, não em texto livre em `obs`.

### `movimentacoes_extras` — índices novos
`ix_mov_fornecedor` (`id_fornecedor`), `ix_mov_categoria` (`id_categoria`), `ix_mov_data_fluxo` (`data, fluxo`), além do `ix_mov_data` pré-existente.

Coluna `id_fornecedor` (FK para `cad_fornecedores`) **já existia antes desta fase**, adicionada por `_migrar_fornecedor_extras` em commit anterior.

### Migração de dados aplicada
- 5 dos 6 lançamentos da categoria 256 (Retirada Adriana) migrados para 259 (Retirada Nova Yaki): IDs 564, 567, 570, 574, 575.
- **Registro ID 561 (Jessica, R$ 300,00, 2026-08-03, PIX, sem obs) foi propositalmente NÃO migrado** — destoa do padrão dos outros 5 (que eram todos `id_pessoa = Adriana Dona`). Permanece na categoria 256 (agora inativa, mas preservada) até confirmação da gerente sobre o que esse lançamento realmente foi.

---

## 7. Decisões de negócio já confirmadas (não reabrir sem necessidade)

- **Digitação do valor:** `150` → `150,00` (centavos por último, não primeiro). Ainda não implementado na UI — fica para a etapa da tela.
- **Permissão:** categoria "Retirada (Nova Yaki)" e relatório de gastos totais são restritos a `GERENTE`/`ADMIN`. Operador comum (ex.: Adilson) não vê nem lança.
- **Categoria "Pagamento" (ID 7)** sai da seleção manual **para todo mundo**, não é questão de perfil — ela continua sendo gravada automaticamente por `views/funcionarios.py` (holerite) e `views/entregadores.py` (diárias) via `WHERE descricao = 'Pagamento'`, sem depender da tela de Movimentações.
- **"Retirada Adriana" e "Retirada (Nova Yaki)" são a mesma coisa** — Adriana é a sócia/dona.

---

## 8. Infraestrutura de permissão já existente (não recriar)

O sistema já tem:
- `cad_pessoas.pin` (PIN de 4 dígitos) e `cad_pessoas.perfil_acesso` (`OPERADOR` / `GERENTE` / `ADMIN`, hierarquia nessa ordem).
- `database.sessao_iniciar(id_pessoa, nome, perfil)`, `sessao_obter()`, `sessao_tem_acesso(perfil_minimo)`.
- Usuários reais confirmados: Richard (ADMIN), Jessica (GERENTE), Adilson (OPERADOR).
- O menu lateral (`main.py`) já filtra telas por `min_perfil`. A tela de Movimentações em si nunca consultava a sessão — é isso que a Fase 3 precisa passar a fazer, usando a coluna `min_perfil` de `cad_categorias_extra` recém-criada para filtrar as opções exibidas.

---

## 9. Dados de uso real que devem orientar a Fase 3 (tela)

De ~581 lançamentos históricos auditados:
- "Pagamento" (203 usos) e "Vale" (194) somam a maior parte do volume — ambos ligados a `id_pessoa`, 100% preenchido. "Pagamento" nunca foi lixeira de despesa genérica; era pagamento de pessoa mesmo, mal rotulado.
- Fornecedores cadastrados (`cad_fornecedores`): 10, **zero vínculos** em `movimentacoes_extras` até a migração. O relatório "gastos por fornecedor" nasce vazio e só ganha conteúdo depois que a tela nova entrar em uso — não é sinal de que a feature é desnecessária, é sinal de que hoje não existe caminho pra lançar isso.
- Método de pagamento (`metodo`, hoje campo texto solto): apenas `PIX`, `Dinheiro`, `Fiado` e `NULL` — sem dispersão de digitação. Porém **38,6% dos lançamentos históricos não têm método preenchido**. Vale considerar tornar obrigatório na tela nova.
- `Fiado` está cadastrado como método de pagamento, mas semanticamente é ausência de pagamento — atenção ao montar totalizador por método pra não contar fiado como dinheiro recebido.

---

## 10. Pendências em aberto para a Fase 2 (boletos) e Fase 3 (tela)

- Registro ID 561 aguardando confirmação da gerente sobre sua real natureza.
- `.spec` do PyInstaller estava quebrado (`datas=[]` não empacota assets do Flet; `version=` com caminho obsoleto de outra máquina) — bloqueia geração de qualquer build novo de produção. Não resolvido nesta sessão; precisa correr em paralelo, sem depender da Fase 2/3.
- Funções `excel_movimentacoes` e `gerar_pdf_movimentacoes`, escritas no refactor descartado, foram preservadas na branch `descarte/refactor-mov-v1` só como referência de consulta para a Fase 3 — não estão em produção nem devem ser reaproveitadas sem revisão.
- Nenhuma alteração de UI foi feita ainda em `views/extras.py`. A Fase 1 tratou exclusivamente de schema e infraestrutura de banco.
