# GestaoLoja — Pendências

_Atualizado: 25/08/2026_

## Build / Infraestrutura

- **`GestaoLoja.spec` (PyInstaller) quebrado.** `datas=[]` não empacota os assets do Flet — o EXE gerado a partir dele não abre. Também tem um caminho `version=` apontando para uma pasta temporária de outra máquina/usuário ("Richard"), que não existe neste PC. O EXE atual em produção provavelmente foi gerado por outro processo (possivelmente `flet pack`), não por este `.spec` diretamente. **Precisa ser investigado e corrigido antes do próximo build de produção.**

## Performance — telas ainda lentas

- **Escala Geral (~724ms para abrir).** Boa parte já explicada pela soma das 3 funções de carga (Escala + Ponto + Visão Geral, todas instrumentadas), mas ainda sobra uma diferença não explicada entre a soma das partes e o tempo total medido.
- **Entregadores (~591ms para abrir).** Ainda não investigada.
- **Saída da tela Escala Geral trava a UI por ~643ms** antes do spinner de carregamento aparecer — custo de desmontar a grade de ~1.200 controles (Dropdowns) da tela anterior. O spinner resolve a *entrada* nas telas lentas, mas não essa trava específica de *saída*.

## Lista original dos funcionários — itens ainda não fechados

- **Item 2 — ponto "apagando" dados.** Provavelmente já resolvido como efeito colateral da correção do bug de auto-completar `HH:MM` no blur (campo ficava travado em algo como "16" sem virar "16:00"). Vale confirmar com quem reportou o problema originalmente.
- **Suavizar troca de abas principais (navegação lateral):** resolvida apenas a parte de "carregando" (spinner + thread em segundo plano). A suavidade visual da transição em si (animação) não foi endereçada.
- **Salário flexível para funcionários "extra"** (pagamento semanal, periodicidade ajustável). Não iniciado — adiado para próxima etapa a pedido do Richard.
- **Como funciona o pagamento dos extras.** Lógica de cálculo ainda não revisada nem explicada em detalhe.
- **Categorias separadas no Fluxo de Caixa.** Não iniciado.
- **Poder excluir um registro de ponto** (a linha mais embaixo da tabela de ponto, na aba Funcionários, ao selecionar o funcionário). Pausado para alinhamento prévio com a equipe.

## O que já foi resolvido e validado nesta sessão (para referência)

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
