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

## 5. Fase 2 — Integração de Boletos, Vínculo de Parcela e Estorno Atômico

### 5.1 Alteração de Schema e Chave Estrangeira
* **Adição da Coluna**: `movimentacoes_extras.id_boleto_parcela` (INTEGER, NULL, FK para `cad_boletos_parcelas(id) ON DELETE SET NULL`).
* **Índice**: Criado `CREATE INDEX ix_mov_boleto_parcela ON movimentacoes_extras(id_boleto_parcela)`.
* **Foreign Keys**: Garantida a execução de `PRAGMA foreign_keys = ON` na abertura de cada conexão em `database.conectar()`.

### 5.2 Correções de Integração de Boletos e Contas
1. **`_registrar_saida_boleto`**:
   - Categoria atualizada de 257 (inativada) para **262** (`compra_fornecedor`).
   - Grava `id_fornecedor = b['id_fornecedor']` (evita `NULL`).
   - Grava `id_boleto_parcela = id_parcela` vinculando a saída à parcela específica quitada.
2. **`boleto_quitar_parcela` e `boleto_quitar`**:
   - Atualizadas para passar `id_parcela=id_parcela` explicitamente para `_registrar_saida_boleto`.
3. **Bloqueio de Exclusão Rastreável em `boleto_excluir`**:
   - Se qualquer parcela do boleto tiver movimentação real de caixa vinculada em `movimentacoes_extras.id_boleto_parcela`, a exclusão é bloqueada impedindo a perda de rastreabilidade financeira.
4. **Estorno Atômico em `mov_extra_excluir`**:
   - Se o registro excluído no caixa estiver vinculado a uma parcela (`id_boleto_parcela IS NOT NULL`), o sistema estorna atomicamente a parcela (`pago = 0`, `data_pago = NULL`, `valor_pago = 0.0`) e reabre o boleto (`status = 'ABERTO'`).

### 5.3 Aplicação em Produção da Fase 2
* Criada e executada a migração idempotente `_migrar_schema_fase2(conn)` chamada em `inicializar_banco()`.
* Aplicada com sucesso no Google Drive em **27/08/2026**. `PRAGMA integrity_check` retornou **`['ok']`**.

---

## 6. Fase 3 — Reestruturação da Tela de Movimentações (`views/extras.py`)

### 6.1 Interface Operacional e Usabilidade
* **Seletor de Fluxo Superior**: Botões visuais `[ ⬆ Saídas / Despesas ]`, `[ ⬇ Entradas / Troco ]`, `[ 📋 Pagar Boletos ]` e `[ 📊 Relatórios & Gastos ]`.
* **Preservação Estrita de Fluxo**: O valor gravado em `movimentacoes_extras.fluxo` provém 100% de `categoria['fluxo']`. Categorias como `Consumo`, `Corrida Extra` e `Reentrega` são gravadas inviolavelmente como `NEUTRO`.
* **Formatação de Valor**: Suporte a digitação direta (`150` -> `150,00`) acionado tanto no `on_blur` quanto no `on_submit` (tecla Enter).
* **Dropdown Dinâmico e Modal de Fornecedores**: Seleção estrita por ID com botão de atalho `[+]` que abre o modal `_dialogo_novo_fornecedor` sem sair do fluxo de caixa.
* **Quitação Direta de Boletos**: Aba integrada listando parcelas a vencer/vencidas nos próximos 60 dias com botão "Quitar" e lançamento automático de saída.
* **Compatibilidade `sqlite3.Row`**: Conversão universal para dicionários (`dict(r)`), prevenindo erros de `.get()` em drivers SQLite padrão.

### 6.2 Correção do Build do Executável (`GestaoLoja.spec`)
* Corrigido o empacotamento de assets do Flet via `collect_data_files('flet')` na lista `datas`.
* Removida a referência legada ao arquivo obsoleto `file_version_info.txt`.
* Compilação real com PyInstaller testada e concluída com sucesso (gerado `dist/GestaoLoja/GestaoLoja.exe` de 27,5 MB).

---

## 7. Fase 3 (Etapa 4) — Relatórios & Gastos, Exportações e Controle de Acesso

### 7.1 Controle de Acesso Estrito por Perfil
* O botão `[ 📊 Relatórios & Gastos ]` e todos os relatórios financeiros consolidados respeitam a permissão `database.sessao_tem_acesso("GERENTE")`.
* **Operador (Adilson)**: Aba de relatórios e KPIs de gastos totais **100% ocultos**.
* **Gerente (Jessica) / Admin (Richard)**: Acesso completo aos filtros de período, KPIs, resumos e exportações.

### 7.2 Backend Agregador (`database.mov_extra_relatorio_periodo`)
* Implementada consulta analítica e agregada única retornando:
  - **Totais Gerais**: Entradas, Saídas, Saldo Líquido, Saídas em Dinheiro (Gaveta), Saídas em PIX e Neutro.
  - **Resumo por Categoria**: Quantidade e valor consolidado por subtipo.
  - **Gastos por Fornecedor (Saídas)**: Agrupamento estrito por `id_fornecedor` e fornecedores canônicos.
  - **Resumo por Forma de Pagamento**: Agrupamento por método (`PIX`, `Dinheiro`, etc.).
  - **Extrato Analítico**: Lista cronológica de todos os lançamentos do período.

### 7.3 Layout e UX da Aba de Relatórios
* **Filtros Rápidos de Período**: Botões `[ Hoje ]`, `[ 7 Dias ]`, `[ Mês Atual ]`, `[ Mês Anterior ]` e seletores com `DatePicker`.
* **Cards Visuais de KPI**: 6 contêineres com ícones e cores temáticas de saldo e fluxo.
* **Tabelas de Resumo Lado a Lado**: Montadas com `ft.ResponsiveRow` (`col={"sm": 12, "md": 6, "lg": 4}`), posicionando as tabelas de Categoria, Fornecedor e Método lado a lado em telas normais.
* **Extrato Analítico Paginado**:
  - Inicia **recolhido por padrão** para manter a tela limpa e veloz.
  - Ao expandir, pagina os lançamentos de **20 em 20 registros**, com botões `[ ◀ Anterior ]` e `[ Próxima ▶ ]` e contadores de página.
* **Módulos de Exportação**:
  - **Excel**: `relatorios.excel_gerador.excel_movimentacoes` (Gera planilha XLSX formatada com abas e cores).
  - **PDF**: `relatorios.pdf_gerador.gerar_pdf_movimentacoes` (Gera relatório em A4 com tabelas ReportLab).

### 7.4 Validação de Dados no Formulário
* Adicionada validação de campo obrigatório para `dd_metodo` em todos os lançamentos de fluxo real (`SAIDA` / `ENTRADA`), impedindo novos registros em "Não informado".

---

## 8. Feature — Escala de Turnos Mensal (Planejamento Visual e Impressão para Mural)

### 8.1 Contexto e Objetivo Operacional
A gerência montava manualmente em papel uma escala mensal de quais colaboradoras trabalham em quais dias da semana e turnos (DIA / NOITE), passando a limpo para fixação física no mural do estabelecimento. Desenvolvemos uma solução visual dedicada no sistema integrada ao banco de dados e com gerador de PDF para impressão direta.

### 8.2 Schema do Banco de Dados (`database.py`)
Criada a migração idempotente `_migrar_schema_escala_turnos(conn)` que define a tabela dedicada de turnos:
* **Tabela `escala_turnos_planejamento`**:
  - `id`: Chave primária autoincremento.
  - `data`: Data do turno (`YYYY-MM-DD`).
  - `id_pessoa`: FK para `cad_pessoas(id)` com `ON DELETE CASCADE` (para funcionárias cadastradas).
  - `nome_avulso`: Texto livre para diaristas e extras avulsos sem cadastro formal.
  - `turno`: `CHECK(turno IN ('DIA', 'NOITE'))`.
  - `funcao`: Texto livre para papel desempenhado por extras (para funcionárias cadastradas, o cargo oficial vem via `LEFT JOIN cad_pessoas`).
  - `chk_escala_identificacao`: Constraint que exige que **OU** `id_pessoa` **OU** `nome_avulso` esteja preenchido (exclusão mútua estrita).
* **Índices de Integridade e Performance**:
  - `ux_escala_pessoa_turno`: Garante unicidade por pessoa cadastrada e turno. Impede duplicidade no mesmo turno, mas permite "dobras" (mesma pessoa no DIA e na NOITE na mesma data).
  - `ux_escala_avulso_turno`: Garante unicidade case-insensitive para extras avulsos.
  - `ix_escala_turnos_data`: Índice de busca por data e mês.

### 8.3 Interface de Usuário (`views/escala_turnos.py`)
* **Calendário Mensal (Master-Detail)**:
  - **Lado Esquerdo (60%)**: Grade de semanas (`calendar.Calendar(firstweekday=6)`). Cada card de dia exibe o resumo dos turnos de relance (`DIA: Amanda, Yasmin` / `NOITE: Bernardo`), com realce de borda para o dia selecionado e dia atual. Sem emojis, em conformidade visual com o app.
  - **Lado Direito (40%)**: Painel do dia selecionado listando todas as colaboradoras escaladas divididas em `Turno DIA` e `Turno NOITE`, com badges de destaque `EXTRA` para diaristas avulsas e botão de exclusão individual.
* **Modal de Inclusão (`AlertDialog`)**:
  - Botão fixo `+ Adicionar Pessoa` no topo do painel do dia, mantendo a lista de pessoas rolável e livre de interferências visuais.
  - Modal com auto-dimensionamento exato (`ft.Column(tight=True)`), contendo Dropdown de funcionárias ativas + opção *"Outro / Extra Avulso"*, seletores de turno `[ Turno DIA ]` / `[ Turno NOITE ]` e botões Cancelar / Salvar.
* **Controle de Acesso por Perfil**:
  - **GERENTE / ADMIN**: Controle completo de inclusão, exclusão e impressão de escala.
  - **OPERADOR**: Modo somente-leitura. Botão de adicionar e ícones de exclusão ocultos, substituídos por nota informativa.

### 8.4 Geração de PDF para Mural (`relatorios/pdf_gerador.py`)
* Implementada a função `gerar_pdf_escala_turnos(ano, mes, dados, abrir_ao_concluir=True)`.
* Formato **A4 Paisagem (Landscape)** com ReportLab.
* Grade de 7 colunas (DOM a SÁB) ocupando a folha inteira, com cabeçalho azul corporativo e listas formatadas de `DIA:` e `NOITE:`.
* Abertura automática no visualizador padrão do Windows para impressão imediata via `Ctrl+P`.

### 8.5 Item no Menu Principal (`main.py`)
* Adicionado o item `"Escala de Turnos"` com ícone `ft.Icons.BADGE_OUTLINED` e `min_perfil: "OPERADOR"`.

---

## 9. Correção de Ambiguidade de Data em Movimentações Extras (`views/extras.py`)

### 9.1 Diagnóstico de Risco Operacional
* No formulário *"Nova Saída de Caixa"*, a função de gravação utilizava `tf_data.value`, que era o mesmo campo de filtro posicionado no rodapé dentro de *"Extrato de Movimentações do Dia"*.
* Se o operador alterasse a data no rodapé para consultar o extrato de um dia anterior e depois lançasse uma saída no topo, a despesa era gravada silenciosamente na data do extrato anterior em vez de hoje.

### 9.2 Solução Implementada
* **Campo Explícito no Formulário (`tf_data_mov`)**: Adicionado o campo `Data do Lançamento *` com `DatePicker` dedicado na primeira linha do formulário ao lado do subtipo. Inicializa sempre com a data atual (`hoje_br`).
* **Isolamento do Extrato (`tf_data`)**: Renomeado para `Data do Extrato`. Mudar a data do extrato agora altera exclusivamente a consulta, sem afetar o formulário.
* **Gravação e Sincronização**: `_salvar()` lê exclusivamente `tf_data_mov.value`. Após gravar com sucesso, o extrato sincroniza automaticamente para a data gravada para exibição imediata e o formulário reseta para a data atual.

---

## 10. Ajuste de Layout na Tela de Funcionários (`views/funcionarios.py`)

### 10.1 Motivação e Diagnóstico
* Anteriormente, a grade completa de semanas × dias com Dropdowns em cada célula ocupava mais de 500px na vertical, empurrando o Holerite (conteúdo principal da tela) para fora do campo de visão imediato do usuário.
* Além disso, a linha de instrumentação de debug (`txt_perf`) ficava visível em produção em várias telas.

### 10.2 Solução Implementada
* **Resumo Compacto de Escala na Página Principal (`card_resumo_escala`)**:
  - Exibe badges visuais e organizados em uma única linha compacta: `Escala do Período: [ 22 trabalhados ] [ 6 folgas ] [ 2 faltas ] [ 1 feriado ] [ 0 extras ]` ao lado do botão `[ Ver / Editar Escala ]`.
* **Modal de Edição de Escala (`dlg_escala` — `AlertDialog`)**:
  - Abre a grade mensal completa (semanas × dias com dropdowns individuais por dia).
  - Sem altura fixa artificial, com `Column(tight=True, scroll=ft.ScrollMode.AUTO)`.
  - Ao fechar o modal (via `X` ou botão `[ Concluir e Atualizar Holerite ]`), os totais de escala e todo o holerite financeiro são recalculados e atualizados instantaneamente.
* **Visibilidade Direta do Holerite**:
  - O Card do Holerite do Período agora fica posicionado imediatamente abaixo dos filtros, 100% visível na tela sem necessidade de rolagem.
* **Ocultação de Debug em Produção (`txt_perf`)**:
  - As tags de tempo de execução (`txt_perf`) em `views/funcionarios.py`, `views/escala_geral.py`, `views/fluxo_caixa.py`, `views/pdv.py`, `views/relatorio_diario.py` e `views/relatorio_periodo.py` foram ocultadas por padrão via `visible=(database.config_obter("debug", "0") == "1")`.

---

## 11. Histórico Completo de Commits da Sessão (27/08/2026)

1. **`ab1a19f`** — `feat(database): Implementa trava permanente de seguranca para ambiente de producao, retentativa ativa de boot e protecao contra escrita acidental`
2. **`77f1157`** — `feat(database): Adiciona migracao de schema e dados da Fase 1 (aplicada em producao em 2026-08-27)`
3. **`43ffc2a`** — `feat(extras): Reestrutura tela de Movimentações de Caixa com fluxo por botões, subtipos ativos, quitação de boletos e permissões`
4. **`db81aa9`** — `feat(extras): Adiciona aba de Relatórios & Consulta de Movimentações com KPIs, exportacao Excel/PDF e controle de perfil`
5. **`e30120f`** — `fix(extras): Corrige layout de renderizacao das tabelas de resumo e extrato analitico na aba de Relatorios`
6. **`a5748ef`** — `feat(extras): Aplica 4 ajustes de relatorios, validacao de metodo e layout responsivo com extrato paginado`
7. **`9d288f0`** — `docs: atualiza documentacao tecnica com relatorios da Fase 3 e correcoes operacionais`
8. **`8ec495d`** — `feat(escala): implementa Escala de Turnos mensal com modal, suporte a extras e PDF mural A4`
9. **`42ca190`** — `fix(escala_turnos): remove altura artificial do modal e ajusta auto-dimensionamento`
10. **`8ae157f`** — `fix(extras): adiciona campo explicito de data no formulario de movimentacoes e isola do filtro do extrato`
11. **`4237340`** — `docs: atualiza ATUALIZACOES_27-08-2026.md com Escala de Turnos e correcao de data em extras`
12. **`5f7597c`** — `feat(funcionarios): compacta resumo de escala com modal de edicao e oculta debug perf em producao`

Todos os commits foram testados, validados e sincronizados com a branch `main` no repositório remoto.

