# GestaoLoja — Contexto do Projeto

## O que é

App desktop de gestão de loja (PDV, caixa, estoque, funcionários, ponto, relatórios),
escrito em **Python + Flet**. Roda como EXE nos PCs da loja, compartilhando um banco
**SQLite** (`loja_caixa.db`) sincronizado via **Google Drive** (modo Mirror, não Stream).

- Entrada: `main.py` — monta o `NavigationRail` lateral e carrega as views sob demanda
  (todas importadas no topo do arquivo, não lazy).
- Views: `views/*.py` — uma por tela (pdv, escala_geral, fluxo_caixa, relatorio_diario,
  relatorio_periodo, funcionarios, entregadores, estoque, fornecedores, parametros, login,
  extras).
- Acesso a dados: `database.py` — toda a lógica de banco, incluindo migrações idempotentes
  (`_migrar_*`) chamadas dentro de `inicializar_banco()`, que roda no nível de import do
  módulo.
- Relatórios: `relatorios/pdf_gerador.py` (reportlab) e `relatorios/excel_gerador.py`
  (openpyxl) — imports carregados sob demanda dentro de cada função geradora (`_carregar()`
  idempotente), não no topo do arquivo, para não pesar o boot.

## Ambiente de teste (importante — nunca testar direto em produção)

- Variável de ambiente `GESTAOLOJA_TESTE` aponta para um banco `.db` isolado.
  `database.py` tem um bloco `if _CAMINHO_TESTE:` que substitui `_encontrar_banco()`
  quando essa variável está setada.
- Banco de teste real (dentro da pasta sincronizada do Drive, para testar o
  comportamento de sincronização também): `C:\GestaoLoja\Meu Drive\loja_app\loja_caixa_teste.db`
- Banco de produção real: `C:\GestaoLoja\Meu Drive\loja_app\loja_caixa.db` (NUNCA
  escrever aqui sem backup prévio e confirmação explícita — é o banco que os PCs da
  loja usam ao vivo).
- `C:\GestaoLoja\Meu Drive\...` é o espelho local real (modo Mirror do Google Drive);
  `G:\Meu Drive\...` e `G:\.shortcut-targets-by-id\...` são views virtuais do mesmo
  arquivo — confirmado por hash idêntico. Prefira sempre o caminho `C:\` direto.
- Ao ler/escrever diretamente no banco fora do app (scripts avulsos), usar `sqlite3`
  puro e **não importar `database.py`** — importar dispara `inicializar_banco()` no
  nível de módulo, que cria índices como efeito colateral (indesejado ao inspecionar
  produção).

## Padrões de instrumentação de performance já estabelecidos

- Logger reaproveitado: `_perf_logger = logging.getLogger("perf")` (mesmo logger em
  todos os arquivos, todos gravam no mesmo `perf_log.txt`).
- Padrão de linha: `_perf_logger.debug(f"{'rotulo':<55} {ms:8.1f} ms")`.
- Em telas com botão de ação (ex: "Gerar", "Salvar"), também existe um `ft.Text
  txt_perf` visível na UI (size=11, cinza, itálico) mostrando "Total: Xms | HH:MM:SS"
  — mesmo padrão em `pdv.py`, `relatorio_diario.py`, `relatorio_periodo.py`,
  `fluxo_caixa.py`, `escala_geral.py`.

## Decisões de arquitetura já tomadas nesta sessão (não reabrir sem motivo)

- **Causa raiz da lentidão original:** Google Drive em modo Stream (I/O virtual) →
  migrado para Mirror (cópia local real). Resolveu o PDV.
- **6 índices SQLite** criados via `_criar_indices()` em `database.py`, idempotentes
  (`IF NOT EXISTS`), chamados dentro de `inicializar_banco()`.
- **N+1 eliminados** via funções `_lote`/`_periodo` que buscam tudo de uma vez com
  `GROUP BY` em vez de laço com conexão por iteração — ver `escala_contar_dias_periodo()`
  e `calcular_pagamento_entregadores_lote()` em `database.py` como modelo a seguir para
  qualquer N+1 novo encontrado.
- **Imports pesados** (reportlab, openpyxl) são lazy, carregados dentro de função via
  `_carregar()` idempotente que popula variáveis de módulo — não mover para o topo do
  arquivo de novo.
- **Troca de tela em `main.py`** (`carregar_view()`) usa spinner + `page.run_thread()`
  para não travar a UI em telas pesadas, com contador de "geração" para descartar
  resultado de navegação obsoleta e trava contra clique duplo no mesmo índice.

## Áreas conhecidas como lentas (não resolvidas ainda)

- **Escala Geral** (~724ms para abrir) — soma de 3 funções de carga (Escala + Ponto +
  Visão Geral), mas ainda sobra tempo não explicado.
- **Entregadores** (~591ms) — não investigada.
- Sair da tela Escala Geral trava a UI por ~643ms antes do spinner aparecer (custo de
  desmontar ~1.200 controles Dropdown da grade).

## Pendências abertas (ver relatório completo em `GestaoLoja_pendencias.md`)

- `GestaoLoja.spec` (PyInstaller) quebrado — não empacota assets do Flet, EXE gerado
  não abre. Investigar antes do próximo build de produção.
- Ponto "apagando" dados (provavelmente já resolvido por correção de bug de
  auto-completar horário, mas não confirmado com quem reportou).
- Aba Funcionários: trocar nome/período ainda exige clique manual em "Carregar".
- Salário flexível para funcionários "extra" (periodicidade de pagamento ajustável).
- Lógica de pagamento de horas extras — revisar/explicar.
- Categorias separadas no Fluxo de Caixa.
- Relatório de ponto em PDF por funcionário, gerado na aba Funcionários.
- Incluir esse relatório de ponto no relatório geral existente.
- Poder excluir um registro de ponto (linha mais recente) na aba Funcionários.

## Convenções do projeto

- Todo texto de interface e comentários em português (pt-BR).
- Migrações de schema sempre idempotentes, verificando `PRAGMA table_info` antes de
  `ALTER TABLE`.
- Campos de horário usam formato `HH:MM` em `TEXT`, com validação (00-23:00-59) antes
  de salvar e auto-formatação ao digitar (`_formatar_hora_input`) + auto-completar ao
  perder o foco (`_completar_hora_input`) — ver `views/escala_geral.py` como referência
  canônica, replicada também em `views/parametros.py`.
- Horas decimais são exibidas para o usuário como "XhYYmin" (função `_fmt_horas`), nunca
  como decimal cru — cálculo interno continua em float, só a exibição muda.
