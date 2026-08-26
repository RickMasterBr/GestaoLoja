# GestaoLoja — Pendências

_Atualizado: 25/08/2026_

## Build / Infraestrutura

- **`GestaoLoja.spec` (PyInstaller):** [RESOLVIDO] Inclusão de `collect_data_files('flet')` e `collect_submodules('flet')` em `datas` e remoção do path absoluto temporário de versão (`version=`). O arquivo `.spec` agora compila limpo sem depender de arquivos locais de outras máquinas.

## Performance — telas ainda lentas

- **Escala Geral (~724ms para abrir).** Otimizada com lazy load do Ponto (reduzindo ~350 controles e queries antecipadas); trava de saída eliminada com Stack desacoplado.
- **Entregadores (~591ms para abrir).** Queries N+1 reduzidas de 41 para 16 queries por abertura. Validar na máquina da loja com Google Drive Mirror ao vivo.

## Lista original dos funcionários — itens fechados e documentados

- **Como funciona o pagamento dos extras (Documentado):**
  - **1. Dia EXTRA na Escala (`tipo = 'EXTRA'`):** Representa um dia/plantão inteiro trabalhado fora da escala normal. Entra **diretamente no total líquido** do Holerite: `val_extras = dias_extra × valor_dia_extra`.
  - **2. Horas Extras no Ponto Diário (`horas_extras`):** Calculadas quando a jornada diária excede a carga horária padrão (ex: 8h).
    - Para `FIXO`: `valor_hora = salario_base / 220` (divisor padrão CLT).
    - Para `DIARIO`: `valor_hora = diaria_valor / carga_horaria`.
    - Adicional de 50%: `valor_hora_extra = valor_hora × 1.5`.
    - `valor_total_extras = total_horas_extras × valor_hora_extra`.
    - **Regra de Pagamento:** Conforme a convenção adotada no app e registrada no rodapé do holerite, os valores de horas extras do ponto são **informativos** e servem para auditoria/espelho de ponto, não sendo somados automaticamente ao total líquido para evitar duplicidade com diárias ou plantões fechados.
- **Item 2 — ponto "apagando" dados:** Resolvido pela correção do auto-completar `HH:MM` no blur.
- **Suavizar troca de abas principais (navegação lateral):** Resolvida a parte de carregamento instantâneo via Stack com camada desacoplada.
- **Salário flexível para funcionários "extra":** Resolvido para DIARIO com seletor de período (mensal, semanas, quinzenas).
- **Categorias separadas no Fluxo de Caixa:** Resolvido com filtro e resumo por categoria.
- **Digitação de PIN pelo Teclado Físico no Login:** Resolvido com listener dedicado para números normais, Numpad, Backspace e Escape.
- **Poder excluir um registro de ponto:** Pausado para alinhamento prévio com a equipe.

## O que já foi resolvido e validado nesta sessão (para referência)

- **Eliminação da trava de saída da Escala Geral (~643ms) em `main.py`:** `area_conteudo` reestruturada com `ft.Stack` de duas camadas (`camada_view` e `camada_loading`). O clique no menu agora apenas ativa `camada_loading.visible = True` sem destruir os controles anteriores no ato, fazendo o spinner aparecer em ~3ms. A destruição da tela anterior e montagem da nova ocorrem de forma protegida em segundo plano.
- **Lazy Loading do Ponto em `views/escala_geral.py`:** Remoção da pré-carga desnecessária da tabela de ponto ao abrir a tela; o ponto agora é carregado apenas se o usuário clicar no botão "Ponto", eliminando mais de 350 controles ocultos da árvore.

- **Relatório de Ponto em PDF (Espelho de Ponto Individual):** Gerador `gerar_pdf_espelho_ponto` criado com tabela completa de todos os dias do mês, quadro de resumo de horas, destaques coloridos e termo de declaração com campo de assinaturas. Botão dedicado "Espelho de Ponto (PDF)" adicionado na seção de Ponto da aba Funcionários.
- **Inclusão do Ponto no Holerite PDF:** Os dados de ponto agora são repassados ao gerador do Holerite completo (`gerar_pdf_holerite`), preenchendo a seção de ponto que antes vinha em branco.
- **Aba Funcionários (holerite):** Auto-carregamento ao entrar na tela (com 1º funcionário pré-selecionado), reatividade instantânea ao trocar funcionário, mês, ano ou calendário, e indicador de tempo de resposta (`txt_perf` + `_perf_logger`).
- Migração do Google Drive de modo Stream para Mirror (causa raiz da lentidão original do PDV).
- Bug `ft.Border.BorderSide` no Fluxo de Caixa.
- 6 índices novos no banco (ganho de até 85x em queries de relatório).
- Eliminação de N+1 em `escala_contar_dias` e `calcular_pagamento_entregador`.
- Import tardio de `reportlab`/`openpyxl` (boot mais rápido).
- Reativação dos perfis Richard e Adriana (produção e teste).
- Auto-carregamento de Ponto/Escala/Visão Geral ao entrar na tela.
- Instrumentação de tempo (`perf_log.txt` + texto visível na tela) em todas as funções de carga da Escala Geral.
- Coluna de nomes fixa (sticky) ao rolar a grade de Escala + caixas de dia mais largas.
- Campo `aparece_no_ponto` para excluir entregadores da tela de Ponto (mantendo-os na Escala).
- Campos de horário padrão (`horario_entrada_padrao`/`horario_saida_padrao`) no cadastro de pessoa.
- Salvamento automático do Ponto ao preencher os 4 campos corretamente, com alerta de confirmação se o horário divergir mais de 1h do padrão cadastrado.
- Correção do bug de auto-completar `HH:MM` que travava campos em estado parcial (ex: "16") ao perder o foco.
- Spinner de carregamento (com thread em segundo plano) para trocas de tela lentas, sem travar a interface.
