# CONTEXTO.md — Gestão Loja (loja_app)

> Documento de retomada de projeto, gerado por leitura integral do código-fonte em 2026-08-20.
> Onde não foi possível confirmar algo só lendo o código, está marcado explicitamente como **não confirmado**.

---

## 1. Visão geral do negócio

O sistema é um **PDV / gestão de caixa e operação para uma lanchonete/restaurante com delivery** (o nome genérico "Gestão Loja" é usado na própria UI; não há indicação de qual seja o nome real da loja — provavelmente configurado em tempo de uso via `Parâmetros > Nome da Loja`). Ele roda **localmente em um computador Windows da loja**, um usuário por vez.

### Problema que resolve
Substitui controles manuais (planilha/papel) para:
- Lançar vendas por múltiplos canais: mesa, retirada no balcão, delivery com motoboy próprio, e delivery via plataformas terceirizadas (iFood — duas contas/lojas separadas "iFood1"/"iFood2" —, 99Food e Keeta).
- Fechar o caixa físico diariamente, conferindo dinheiro em espécie contra o esperado pelo sistema.
- Controlar escala de trabalho e ponto de funcionários e entregadores, e calcular holerite/pagamento de diária.
- Controlar fiado de clientes, vale/sangria/consumo interno, estoque de insumos e contas a pagar de fornecedores (boletos).
- Gerar relatórios diários/por período em PDF/Excel/CSV para prestação de contas.

### Módulos principais (telas)
Dashboard, PDV (lançamento de pedidos), Movimentações e Caixa (extras), Relatório Diário, Relatório de Período, Fluxo de Caixa (extrato + histórico de divergências), Fiados, Funcionários (escala + holerite individual), Escala Geral (grade mensal de toda a equipe + ponto diário), Entregadores (painel de pagamento diário/semanal), Estoque, Fornecedores (+ boletos), Parâmetros (cadastros e configuração do sistema).

### Fluxo de uso típico do dia a dia
1. **Login** com seleção de usuário + PIN de 4 dígitos (tela touch-friendly, tipo totem).
2. Ao longo do dia, o **operador** lança pedidos no **PDV** (canal, valor, pagamento(s), operador, bairro/taxas quando aplicável) e registra **movimentações extras** (vale, sangria, consumo, corrida extra, reentrega, pagamento a funcionário, reposição de estoque).
3. No **Dashboard**, a equipe registra a **presença do dia** (escala + horário de entrada/saída) e há alertas de estoque baixo e boletos vencendo.
4. No fim do turno, no **Relatório Diário**, o responsável informa o troco inicial e o valor contado na gaveta; o sistema calcula a diferença ("Salvar Fechamento"). Há um modo opcional de **"fechamento cego"** em que o operador não vê o saldo teórico antes de confirmar a contagem (reduz viés/fraude).
5. O operador então usa o botão **"Encerrar Turno"**, um assistente de 2 etapas que verifica se pedidos foram lançados, se o caixa foi fechado e se todas as pessoas ativas têm presença registrada no dia, antes de permitir confirmar.
6. Periodicamente (dono/gerente), consulta **Relatório de Período**, **Entregadores** e **Funcionários** para conferir repasses de plataforma, pagar entregadores/funcionários e exportar relatórios.

---

## 2. Arquitetura técnica

### Stack
- **Linguagem:** Python (bytecode compilado indica **Python 3.14**, via `__pycache__/*.cpython-314.pyc`).
- **UI:** [Flet](https://flet.dev) (`import flet as ft`, `ft.app(target=_iniciar_app)`) — GUI declarativa desktop, tema dark/light alternável.
- **Banco de dados:** SQLite puro via `sqlite3` da stdlib (sem ORM). `conn.row_factory = sqlite3.Row`. Modo `WAL`.
- **Geração de relatórios:** `openpyxl` (Excel) e `reportlab` (PDF).
- **Empacotamento:** PyInstaller (`GestaoLoja.spec` → `dist/GestaoLoja.exe`), one-folder/one-file Windows, sem console (`console=False`).
- **Dependências Windows-only:** `ctypes.windll.kernel32` (fecha o processo abruptamente ao fechar a janela — `page.on_disconnect`), `os.startfile` (abrir PDFs/planilhas exportados), `subprocess` com `tasklist`/`taskkill` para matar instâncias anteriores do próprio `.exe` (evitar duplicidade de processo). **O app não roda em Linux/macOS sem adaptação.**

### Estrutura de pastas
```
loja_app/
├── main.py                  # entrada: janela, navegação lateral, login, encerramento de turno
├── database.py              # TODO o acesso a dados (schema, migrações, CRUD, regras) — 3644 linhas
├── limpar_dados_teste.py    # script avulso de manutenção (apaga dados de teste < 2026-04-01)
├── GestaoLoja.spec          # spec do PyInstaller
├── views/                   # 1 arquivo por tela Flet
│   ├── login.py, dashboard.py, pdv.py, extras.py,
│   ├── relatorio_diario.py, relatorio_periodo.py, fluxo_caixa.py,
│   ├── fiados.py, funcionarios.py, escala_geral.py, entregadores.py,
│   └── estoque.py, fornecedores.py, parametros.py
├── calculos/                # funcionarios.py e plataformas.py — VAZIOS (ver seção 5)
├── relatorios/
│   ├── excel_gerador.py     # ExcelBuilder + funções excel_*()
│   └── pdf_gerador.py       # helpers reportlab + funções gerar_pdf_*()
├── exports/                 # saída de CSV/holerite gerados em runtime (git rastreia 1 exemplo)
├── build/, dist/            # artefatos do PyInstaller (ver seção 5 sobre rastreamento indevido)
├── loja.db, loja_caixa.db   # bancos SQLite (ver seção 5 — dados reais rastreados no git!)
└── perf_log.txt, perf_loja.txt  # logs de instrumentação de performance (grandes, rastreados)
```

### Como rodar localmente
Não há `requirements.txt`, `pyproject.toml` nem `Pipfile` no repositório — as dependências foram inferidas 100% dos `import`s:
```
pip install flet openpyxl reportlab
```
(Possivelmente também `pywin32`, indicado pelo módulo `pyimod04_pywin32.pyc` presente nos artefatos de build do PyInstaller — **não confirmado** se é dependência direta do app ou apenas do runtime do PyInstaller/Flet.)

Depois:
```
python main.py
```
Na primeira execução (`if __name__ == "__main__":`), `main.py` mata instâncias anteriores do `.exe`, chama `database.inicializar_banco()` (cria tabelas, roda migrações idempotentes, popula dados de referência) e sobe o app Flet.

Para resetar o banco do zero: `python database.py --reset`.

### Deploy / empacotamento
`GestaoLoja.spec` gera um executável único `GestaoLoja.exe` (nome do produto), sem console, sem ícone customizado (`icon` não definido no `EXE(...)`), `datas=[]` e `binaries=[]` vazios (nenhum asset externo é empacotado — o app depende de arquivos ao lado do `.exe` em runtime: `loja_caixa.db`, pasta `exports/`). O campo `version=` do spec aponta para um caminho temporário específico da máquina do desenvolvedor (`C:\Users\Richard\AppData\Local\Temp\...`), o que sugere que o build é feito manualmente na máquina do autor, não via CI.

---

## 3. Modelo de dados

Todas as tabelas são criadas em `database.py::_criar_tabelas()` e evoluídas por ~13 funções `_migrar_*` idempotentes (checam `PRAGMA table_info` / SQL do `sqlite_master` antes de alterar; para mudanças de `CHECK` constraint — que o SQLite não suporta via `ALTER` — a tabela é recriada e os dados copiados).

### Entidades e relacionamentos (visão simplificada)

```
cad_pessoas (funcionários e entregadores; 1 tabela para os dois tipos)
 ├─ pin, perfil_acesso  → login/permissão
 ├─ tipo_salario FIXO|DIARIO|ENTREGADOR, salario_base, diaria_valor
 ├─ valor_extra/valor_feriado/valor_falta, carga_horaria_diaria → cálculo de holerite
 └─ 1:N cad_dias_fixos (grade semanal fixa por dia_semana)
    1:N escalas_trabalho (data, tipo: TRABALHOU/FALTA/FOLGA/FERIADO/EXTRA — UNIQUE por dia+pessoa)
    1:N registros_ponto (entrada/saída/intervalo por dia — UNIQUE por dia+pessoa)
    1:N movimentacoes_extras (como id_pessoa)
    1:N vendas_pedidos (como id_operador)

cad_bairros ── taxa_cobrada, repasse_entregador → 1:N vendas_pedidos (id_bairro)

cad_plataformas (iFood1, iFood2, 99Food, Keeta — CHECK fecha o nome nesses 4 valores)
 └─ comissao_pct, taxa_transacao_pct, subsídio, custo logístico por faixa de km (só 99Food usa),
    dia_repasse — consultada por nome (LIKE 'iFood1%' etc.) para casar com vendas_pedidos.canal

cad_canais (catálogo dos canais aceitos em vendas_pedidos.canal)
 └─ requer_bairro, tem_comissao, entregador_plataforma (canais "_Deles")

cad_metodos_pag (Dinheiro, Crédito, Débito, PIX, VA, VR, Voucher, Fiado, iFood, 99Food, Keeta)
 └─ tipo: FISICO | PLATAFORMA | BENEFICIO | CORTESIA

cad_categorias_extra (Vale, Sangria, Consumo, Corrida Extra, Reentrega, Fiado, Pagamento,
                       Reposição de Estoque, Outros)
 └─ fluxo: ENTRADA | SAIDA | NEUTRO

vendas_pedidos (1 linha por pedido; canal restrito por CHECK a 15 valores fixos)
 └─ 1:N vendas_pagamentos (split de pagamento; cortesia por linha)
 └─ 1:1 (opcional) fiados.id_pedido (quando um dos pagamentos é "Fiado")

movimentacoes_extras (vale/sangria/consumo/corrida extra/reentrega/pagamento/reposição/outros)
 └─ id_pessoa (opcional), id_categoria, id_fornecedor (opcional), fluxo, metodo, valor

fluxo_caixa_diario (PK = data) — troco_inicial, total_especie_entradas/saidas (calculados),
                     saldo_teorico (calculado), saldo_gaveta_real (conferido), diferenca

fiados — data_lancamento, nome_cliente, valor, pago, data_pagamento, id_pedido (opcional)

estoque_categorias 1:N estoque_produtos 1:N estoque_movimentacoes (ENTRADA|SAIDA|AJUSTE)
 └─ triggers SQL (trg_estoque_entrada/saida/ajuste) recalculam quantidade_atual automaticamente

cad_fornecedores 1:N cad_boletos (AVISTA|BOLETO|PARCELADO) 1:N cad_boletos_parcelas
                 1:N movimentacoes_extras (id_fornecedor, opcional)

logs_auditoria — trilha de auditoria (ação, tabela, id_registro, antes/depois, usuário)
cad_configuracoes — chave/valor (nome_loja, tema, diaria_padrao_entregador,
                                  limite_divergencia_caixa, fechamento_cego)
```

### Triggers e regras de integridade embutidas no schema
- **Estoque:** `trg_estoque_entrada/saida/ajuste` mantêm `estoque_produtos.quantidade_atual` sincronizada automaticamente a cada `INSERT` em `estoque_movimentacoes`. Ao **excluir** uma movimentação (`estoque_mov_excluir`), a quantidade é recalculada manualmente em Python (soma entradas/saídas desde o último AJUSTE) — os triggers não cobrem `DELETE`.
- **Canais "_Deles":** `trg_zerar_taxas_deles_insert/update` zeram `taxa_entrega`/`repasse_entregador` automaticamente sempre que o canal termina em `_Deles` (entregador é da própria plataforma, não da loja) — redundante com a validação já feita em Python (`canal_usa_entregador_proprio`), como camada de segurança dupla.

### Regras de negócio centrais

**Fechamento de caixa** (`fluxo_caixa_recalcular` / `fluxo_caixa_fechar`): soma pagamentos em "Dinheiro" de pedidos não-cortesia + entradas em espécie de `movimentacoes_extras` − saídas em espécie, mais o troco inicial = `saldo_teorico`. `diferenca = saldo_gaveta_real (contado) − saldo_teorico`. Se `abs(diferenca) > limite_divergencia_caixa` (config, padrão R$ 5,00), a UI mostra um banner de alerta (sobra/falta).

**Cálculo de repasse de plataforma** (implementado **dentro das views**, não em `calculos/` — ver seção 5): bruto do canal é dividido em "pago online" (métodos que não são Crédito/Débito/PIX/Dinheiro/VA/VR/Voucher — ou seja, o cliente pagou pela própria plataforma) vs "recebido na maquininha". Sobre o valor online incide `comissao_pct` + `taxa_transacao_pct`; sobre o valor na maquininha incide só `comissao_pct`; soma-se um `subsidio` fixo por pedido; para 99Food subtrai-se ainda um custo logístico (`custo_logistico_maximo` por pedido — os demais campos de faixa por km existem no schema mas **não são usados em nenhum cálculo visto no código**, não confirmado se são vestigiais ou usados em fluxo não encontrado).

**Holerite/folha** (implementado **dentro de `views/funcionarios.py`**, não em `calculos/`): `total_líquido = base (salário fixo OU diária × dias pagos) + (dias EXTRA × valor_extra) + (dias FERIADO × valor_feriado) − (dias FALTA × valor_falta) − soma de Vales − 80% da soma de Consumos`. Ponto (entrada/saída/intervalo) gera cálculo de horas extras/faltantes **apenas informativo** (não entra no total líquido) — `valor_hora = salário/220` (fixo) ou `diária/carga_horária` (diário), extra = 150% da hora normal.

**Pagamento de entregador** (`calcular_pagamento_entregador`): `diária (só se houve ≥1 entrega no dia) + soma dos repasse_entregador dos pedidos do dia + Corridas Extra − Vales`. Entregadores cadastrados sem `diaria_valor` definido caem no fallback hardcoded de R$ 40,00 (repetido em pelo menos 4 lugares do código — `database.py`, `entregadores.py`, `relatorio_diario.py`, `relatorio_periodo.py`).

---

## 4. Módulos em detalhe

| View | O que faz | Principais funções de `database.py` | Observações |
|---|---|---|---|
| `login.py` | Seleção de usuário (lista quem tem PIN cadastrado e perfil ≠ SEM_ACESSO) + teclado numérico para PIN de 4 dígitos. Se ninguém tiver PIN cadastrado, permite "Entrar sem autenticação" como ADMIN. | `usuario_listar_ativos`, `usuario_autenticar`, `sessao_iniciar` | Sem "esqueci senha"; reset de PIN só via tela de Parâmetros por um ADMIN. |
| `dashboard.py` | Resumo do dia (vendas por canal, status do caixa), alertas de estoque baixo e boletos vencendo, e formulário de presença/ponto de todos ativos. | `fluxo_caixa_recalcular`, `escala_pre_popular_do_dia`, `escala_registrar`, `ponto_registrar_*`, `estoque_produtos_abaixo_minimo`, `boletos_vencidos_hoje` | Pré-popula escala do dia a partir dos "dias fixos" cadastrados por pessoa. |
| `pdv.py` | Lançamento de pedidos: canal, valor, split de pagamentos, operador, bairro/taxas (condicional ao canal), edição/exclusão, filtro, e edição em lote de data. Fortemente instrumentado com logging de performance em `perf_loja.txt`/`perf_log.txt`. | `pedido_salvar_completo`, `pedido_atualizar`, `pagamento_*`, `fiado_inserir` (automático quando método = Fiado) | Cria fiado automaticamente ao selecionar método "Fiado"; valida soma dos pagamentos ≈ valor total (tolerância R$0,05). |
| `extras.py` | Lançamento de movimentações (vale, sangria, consumo, corrida extra, reentrega, pagamento, outros), com campos condicionais por categoria (pessoa, método) via dicionário `_CAT_CONFIG`. | `mov_extra_*`, `categoria_extra_listar` | Consumo recebe automaticamente uma observação "(desconto 20% aplicado no holerite)". |
| `relatorio_diario.py` | Fechamento do dia: resumo por canal, por método de pagamento, detalhamento por plataforma (com cálculo de comissão/repasse embutido — ver seção 3), entregadores do dia, caixa/troco (com modo "fechamento cego"), extras do dia, fiados/cortesias do dia. Exporta PDF/Excel. | `pedido_totais_por_data`, `fluxo_caixa_fechar`, `calcular_pagamento_entregador`, `mov_extra_listar_por_data` | Contém a lógica de negócio de comissão de plataforma **duplicada** com `relatorio_periodo.py` (mesma função `_conteudo_plataforma` quase idêntica nos dois arquivos). |
| `relatorio_periodo.py` | Mesma lógica do diário, agregada por intervalo de datas; adiciona projeção de datas de repasse (próxima quarta para 99Food/Keeta, ciclo quinzenal dia 5/20 para iFood) e resumo de funcionários no período. Exporta CSV/PDF/Excel. | idem + `escala_contar_dias` | — |
| `fluxo_caixa.py` | Extrato cronológico do caixa (3 abas: Diário, Período, Histórico de divergências) com saldo acumulado por lançamento. Permite editar observação de fechamentos passados. Exporta CSV/PDF/Excel. | `fluxo_caixa_listar_lancamentos`, `fluxo_caixa_historico_divergencias` | — |
| `fiados.py` | CRUD de fiados + quitação com data de pagamento. | `fiado_listar`, `fiado_quitar`, `fiado_atualizar/excluir` | — |
| `funcionarios.py` | Grade de escala mensal (dropdown por dia) + holerite individual completo com detalhamento (vales, consumos, ocorrências) e seção de ponto (se não for entregador). Botão para registrar o pagamento do salário do mês (cria uma `movimentacoes_extras` categoria "Pagamento", idempotente por mês). Exporta CSV/Excel/PDF. | `escala_listar_por_pessoa`, `ponto_resumo_mensal`, `pessoa_buscar` | **Contém a lógica de cálculo de holerite inline** (ver seção 5 — `calculos/funcionarios.py` está vazio). |
| `escala_geral.py` | Duas seções alternáveis: (1) Escala mensal — grade individual editável e "Visão Geral" comparativa de todas as pessoas com métricas (dias com equipe, média/dia, quem mais faltou, horas extras); (2) Ponto diário — tabela editável de entrada/intervalo/saída por pessoa com cálculo de horas ao salvar. | `escala_registrar/excluir`, `ponto_registrar_*`, `ponto_calcular_horas` | — |
| `entregadores.py` | Painel do dia (repasse, diária, extras, vales, total a pagar, com botão Registrar/Estornar pagamento — estorno só para ADMIN), acumulado da semana (7 dias), histórico de corridas extras/reentregas, detalhamento diário por entregador. Exporta Excel/PDF. | `calcular_pagamento_entregador`, `mov_extra_inserir` | **Contém a lógica de cálculo de repasse de entregador duplicada em SQL inline** além da função central `calcular_pagamento_entregador`. |
| `estoque.py` | 3 abas: Estoque (visão com alertas e ações rápidas ENTRADA/SAÍDA/AJUSTE, com opção de vincular a uma "reposição" que gera automaticamente uma saída de caixa), Movimentações (histórico filtrável, exporta CSV/Excel/PDF), Cadastro (categorias e produtos). | `estoque_produto_*`, `estoque_mov_*`, `reposicao_registrar` | — |
| `fornecedores.py` | CRUD de fornecedores + gestão de boletos (à vista/boleto único/parcelado, com geração automática de parcelas mensais respeitando meses com menos dias). | `fornecedor_*`, `boleto_*` | — |
| `parametros.py` | 7 abas: Pessoas (cadastro completo — dados de holerite, PIN, perfil de acesso, dias fixos, dados pessoais), Bairros, Plataformas (comissão/taxa/subsídio/dia de repasse por plataforma), Métodos de Pagamento, Categorias Extras, Configurações Gerais (nome da loja, diária padrão, limite de divergência, fechamento cego), Auditoria (log com filtro, exportação CSV, limpeza de logs antigos). | praticamente todo o `database.py` CRUD de cadastro + `log_listar/limpar_antigos` | Tela mais extensa (1384 linhas); acesso restrito a ADMIN via `main.py`. |

**Dependências entre módulos:** todas as views dependem de `database.py`; `relatorio_diario/periodo`, `fluxo_caixa`, `funcionarios`, `entregadores` e `estoque` também importam de `relatorios/excel_gerador.py` e `relatorios/pdf_gerador.py`. Não há dependência de `calculos/` em nenhuma view (módulo vazio, ver próxima seção). `main.py` importa todas as views e monta a navegação; não há roteamento por URL (é um app desktop de página única com troca de `Container.content`).

---

## 5. Estado atual do projeto

### O que funciona
Pela leitura do código, o fluxo principal (login → PDV → extras → fechamento de caixa → relatórios → escala/ponto → estoque → fornecedores/boletos → parâmetros) está **implementado de ponta a ponta**, com validações de formulário, confirmações de exclusão, logs de auditoria na maioria das ações sensíveis, e exportação funcional em 3 formatos (CSV, Excel via `openpyxl`, PDF via `reportlab`). O histórico de migrações mostra um schema que evoluiu de forma incremental e cuidadosa (idempotente, com recriação segura de tabelas quando o SQLite não suporta `ALTER COLUMN`).

### Achados relevantes / débitos técnicos

1. **`calculos/funcionarios.py` e `calculos/plataformas.py` estão completamente vazios (0 bytes).** Apesar do nome sugerir que concentrariam a regra de cálculo de holerite e de comissão/repasse de plataforma, essa lógica na verdade está **implementada diretamente dentro das views** (`views/funcionarios.py` para holerite; `views/relatorio_diario.py` e `views/relatorio_periodo.py`, de forma **duplicada quase palavra-por-palavra**, para comissão de plataforma; `database.py::calcular_pagamento_entregador` mais lógica SQL duplicada em `views/entregadores.py` para repasse de entregador). Isso é o maior indício de refatoração interrompida/planejada e não concluída no projeto.

2. **O repositório git rastreia o banco de dados real e arquivos de log grandes.** Apesar de existir um commit "Remove banco de dados do repositório" (2b56c22), o `.gitignore` atual está corrompido na última linha (`*.pyc* . d b  ` em vez de, aparentemente, padrões separados para `*.pyc` e `*.db`) e **hoje `git ls-files` confirma que `loja.db`, `loja_caixa.db` (banco ativo, ~100 KB, com dados reais), `perf_log.txt` e `perf_loja.txt` (log de performance de ~2,6 MB) e todos os `__pycache__/*.pyc` continuam rastreados no repositório.** Isso é potencialmente um problema de privacidade (dados de vendas, funcionários, PINs — ainda que os PINs estejam armazenados como hash SHA-256) e de repositório inchado.
3. **Nenhum teste automatizado** — não há `test_*.py`, `pytest`, `unittest` em lugar nenhum do projeto.
4. **Nenhum `requirements.txt`/`pyproject.toml`** — dependências precisam ser inferidas dos imports (ver seção 2).
5. **Bug potencial em `verificar_encerramento_turno`:** o caixa é considerado "fechado" checando `saldo_gaveta_real != 0`. Se o fechamento legítimo do dia resultar em gaveta com saldo real R$ 0,00 (ex.: loja fechou sem caixa físico ou tudo foi retirado), o sistema vai reportar incorretamente que o caixa "ainda não foi fechado".
6. **"Encerrar Turno" é puramente informativo/de auditoria** — `registrar_encerramento_turno` apenas grava uma linha em `logs_auditoria`; nenhuma tabela recebe um flag de "turno encerrado" e nada impede edições posteriores nos dados daquele dia. Não há bloqueio real de dados após o encerramento.
7. **Duplicação de constantes/lógica entre views:** o dicionário `CANAL_NOMES` (nomes amigáveis dos 15 canais) está copiado idêntico em `dashboard.py`, `pdv.py`, `relatorio_diario.py` e `relatorio_periodo.py`; os helpers `_fechar`/`_confirmar_exclusao` (diálogo de confirmação de exclusão) estão copiados em `pdv.py`, `extras.py` e `parametros.py`; o fallback de diária de entregador (R$ 40,00) está hardcoded em pelo menos 4 lugares.
8. **`database.py` tem instrumentação de performance pesada em produção** (`_t()` context manager grava em `perf_log.txt` a cada operação; `pdv.py` também escreve em `perf_loja.txt` via `logging`), sugerindo que o time esteve investigando um problema de lentidão. Os dois arquivos de log já somam ~2,7 MB e crescem a cada execução — atualmente commitados no git (ver item 2).
9. **`sessao_tem_acesso()` está definida em `database.py` mas não é chamada por nenhuma view** — o controle de acesso por tela é feito de forma paralela e duplicada em `main.py` (`_hierarquia` local reimplementada).
10. Campos de custo logístico por faixa de km em `cad_plataformas` (`custo_logistico_km1..km4`, `custo_logistico_extra_por_km`) existem no schema e são editáveis (implicitamente, via `plataforma_atualizar` com `**campos`, embora a UI de Parâmetros não exponha esses campos especificamente) mas **não encontrei nenhum cálculo que os utilize** — só `custo_logistico_maximo` é usado (fixo, só para 99Food). Podem ser vestígio de um cálculo mais granular planejado e não implementado, ou usados por script/uso não coberto pela leitura.
11. `GestaoLoja.spec` não define ícone (`icon` ausente do bloco `EXE`) e o campo `version=` referencia um caminho de arquivo temporário específico da máquina do autor — o build parece ser manual, não reprodutível/CI.

### O que está incompleto/quebrado
Não identifiquei nenhuma tela sem função ou fluxo visivelmente quebrado ao ler o código (sem `TODO`/`FIXME`/`XXX` em lugar nenhum do código-fonte). O maior "incompleto" é estrutural: o módulo `calculos/` existe na árvore de pastas mas nunca foi de fato usado (item 1 acima).

---

## 6. Autenticação e permissões

- **Login por PIN numérico de 4 dígitos**, associado a uma pessoa (`cad_pessoas`). O PIN é armazenado como hash SHA-256 (`_hash_pin`, sem salt — aceitável para uma aplicação desktop local single-tenant, mas **não confirmado** se essa é uma decisão consciente de segurança).
- **Perfis:** `SEM_ACESSO` (excluído da lista de login) < `OPERADOR` < `GERENTE` < `ADMIN`. Hierarquia numérica: `{"SEM_ACESSO": 0, "OPERADOR": 1, "GERENTE": 2, "ADMIN": 3}`.
- Cada tela em `main.py::TELAS` declara um `min_perfil`; o menu lateral só lista (e a rota só instância) as telas cujo perfil mínimo é ≤ ao perfil da sessão logada. Restrições observadas: **Parâmetros** exige ADMIN; **Relatório de Período**, **Fluxo de Caixa**, **Funcionários**, **Estoque**, **Fornecedores** exigem GERENTE; as demais (Dashboard, PDV, Extras, Relatório Diário, Escala Geral, Entregadores, Fiados) exigem apenas OPERADOR.
- **Estorno de pagamento de entregador** é a única ação vista com checagem de perfil *dentro* de uma view (`entregadores.py`, `eh_admin = sessao.get("perfil_acesso") == "ADMIN"`), em vez de depender só do gate de menu.
- **Sessão é apenas em memória** (`_sessao_atual`, dict no módulo `database.py`), válida só durante a execução do processo — reinicia ao fechar o app. Não há timeout de sessão nem "lembrar usuário".
- Se **nenhuma pessoa tiver PIN cadastrado**, o login é pulado e o app entra como ADMIN sem autenticação — comportamento de bootstrap para o primeiro uso.
- Toda troca de tela reconstrói o menu a partir de `telas_perm`; **não há uma segunda verificação de permissão dentro das próprias views** (exceto o caso de estorno citado acima) — o modelo de confiança assume que quem tem acesso físico ao processo em execução já passou pelo gate do menu.

---

## 7. Integrações externas

Confirmado pela leitura de código (não presumido):

- **iFood, 99Food, Keeta não têm integração de API alguma.** Não há nenhuma chamada HTTP/`requests`/webhook no projeto. Os pedidos feitos nessas plataformas são **lançados manualmente** no PDV como canais de venda (`iFood1_Delivery`, `iFood1_Retirada`, etc.); a "integração" é puramente cadastral (comissão/taxa/subsídio configurados em `Parâmetros > Plataformas` e usados só para calcular estimativas de repasse localmente).
- **Google Drive** é usado apenas como um **compartilhamento de arquivo via pasta sincronizada no disco** (não API do Google Drive): `database.py` tenta, nesta ordem, dois caminhos fixos (`G:\Meu Drive\loja_app\loja_caixa.db` e um caminho de atalho do Drive por ID de pasta), e cai para o banco local (`loja_caixa.db` ao lado do `.exe`) se nenhum existir. Isso permite que o mesmo banco SQLite seja compartilhado entre computadores via sincronização de arquivos do cliente Google Drive instalado no Windows — **não há nenhuma lógica de merge/lock/resolução de conflito** além de `PRAGMA wal_checkpoint(PASSIVE)` no botão "Sincronizar" (força o SQLite a reler o arquivo do disco). Escritas concorrentes de duas instâncias abertas ao mesmo tempo em máquinas diferentes **não são coordenadas** pelo aplicativo — o risco de conflito/corrupção fica por conta do próprio Google Drive.
- Não há envio de e-mail, SMS, notificação push nem qualquer outro serviço de terceiros.

---

## 8. Histórico e decisões

Histórico de commits (`git log --oneline`), do mais antigo ao mais novo:
1. `4d94942` Projeto Completo
2. `c8dc97d` Implementando novas funcionalidades
3. `2f0c07d` Implementando PIN
4. `239b5d7` Implemtando melhorias
5. `026d8b7` Corrigindo bugs
6. `661144e` Corrigindo bugs
7. `06f757c` Remove pastas de build do tracking (remoção de ~73 mil linhas de artefatos do PyInstaller que haviam sido commitados por engano)
8. `50b51b6` Adiciona .gitignore
9. `c566e37` Implementando funcionalidades
10. `2b56c22` Remove banco de dados do repositório (mas, como visto na seção 5, o banco continua sendo rastreado hoje)
11. `efc0561` Novas Melhorias (commit mais recente, hoje) — inclui expansão de `database.py` (+311 linhas) e `pdv.py` (+87 linhas), além da adição de `perf_log.txt`/`perf_loja.txt`, reforçando a hipótese de que o time estava investigando performance do PDV.

Todos os commits são do mesmo autor (`Richard Lopes` / `richardlopesstrougo@gmail.com`), sugerindo um projeto pessoal/solo, provavelmente do próprio dono ou gerente da loja (reforçado pelo arquivo `exports/holerite_Richard_032026.csv`, um holerite de teste gerado para "Richard").

**Evolução do schema** (visível pelas 13 funções `_migrar_*`, todas idempotentes) mostra decisões de produto tomadas ao longo do tempo:
- PIN e perfil de acesso (`_migrar_acesso`) foram adicionados **depois** do schema original — login por PIN não fez parte do design inicial (bate com o commit `2f0c07d Implementando PIN`).
- A categoria "Consumo" e as categorias "Corrida Extra"/"Reentrega" originalmente usavam fluxo `SAIDA`, e foram corrigidas para `NEUTRO` (`_migrar_fluxo_neutro`, `_migrar_consumo_neutro`) — indício de que a equipe percebeu que esses valores não deveriam impactar diretamente entrada/saída de caixa, e sim ser tratados à parte (holerite com desconto de 80% para consumo, por exemplo).
- Campos de holerite (`valor_extra`, `valor_feriado`, `valor_falta`, `carga_horaria_diaria`), dados pessoais (CPF/RG/nascimento/telefone/endereço) e vínculo de fornecedor em movimentações extras e no estoque também foram adicionados depois do schema original — o produto começou mais simples (só operação de caixa) e foi crescendo para módulos de RH e suprimentos.
- `vendas_pedidos.nome_cliente` e `fiados.id_pedido` são as duas migrações mais recentes, sugerindo que a identificação de cliente e o vínculo direto fiado↔pedido foram necessidades que surgiram tarde no desenvolvimento.

---

## 9. Perguntas em aberto

Itens que só o dono do projeto pode esclarecer — não é possível confirmar só lendo o código:

1. **`calculos/funcionarios.py` e `calculos/plataformas.py` vazios foram esquecidos de uma refatoração, ou são só um esqueleto para um trabalho futuro de "extrair a lógica de negócio das views"?** Vale decidir se a lógica duplicada hoje nas views deve ser migrada para lá.
2. **O banco de dados real (`loja_caixa.db`) e os logs de performance ainda estão sendo commitados no git — isso é intencional (backup via git) ou um vazamento de dados não percebido?** Recomendo fortemente corrigir o `.gitignore` (linha corrompida) e rodar `git rm --cached` nesses arquivos caso não seja intencional, avaliando se é necessário reescrever o histórico por conter dados sensíveis (nomes de clientes/funcionários, valores financeiros).
3. **O "Encerrar Turno" deveria travar edições no dia encerrado?** Hoje ele só grava um log de auditoria; não há bloqueio de fato. Confirmar se esse é o comportamento desejado ou se falta implementar um trava real.
4. **Os campos de custo logístico por faixa de km em `cad_plataformas` (`custo_logistico_km1..km4`, `custo_logistico_extra_por_km`) são vestígio de uma funcionalidade abandonada, ou há algum fluxo de uso (talvez manual, fora do código) que os utiliza?**
5. **Existe algum plano de sincronização multi-loja/multi-usuário além do compartilhamento de arquivo via Google Drive?** O modelo atual não tem lock nem resolução de conflito — convém confirmar se mais de um computador acessa o mesmo banco ao mesmo tempo na prática, e se já houve algum incidente de conflito/corrupção.
6. **Qual é o nome real da loja e o segmento exato (lanchonete? pizzaria? hamburgueria?)** — o código é genérico ("Gestão Loja") e não guarda esse dado em nenhum lugar fixo, só na configuração `nome_loja`.
7. **iFood1 vs iFood2** — são duas lojas/CNPJs diferentes no iFood, dois pontos de atendimento, ou uma segunda conta por algum outro motivo operacional (ex.: fallback quando uma conta cai)? O código trata como duas plataformas independentes e idênticas em configuração padrão.
8. **Por que há tanta instrumentação de performance (`_t()`, `perf_log.txt`, `perf_loja.txt`, logging detalhado em `pdv.py`) ativa por padrão, mesmo fora de debug?** Sugere um problema de lentidão real sendo investigado — vale perguntar se já foi resolvido e se essa instrumentação pode ser removida/desligada por configuração antes de considerar o app "pronto".
9. **Não há testes automatizados** — é uma escolha consciente (app pequeno, mudanças sempre testadas manualmente) ou uma lacuna que o dono gostaria de endereçar?
