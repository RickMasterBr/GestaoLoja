# 🗺️ Plano de Modernização: Barra Retrátil & Novo Dashboard

**Data de Criação:** 26/08/2026  
**Objetivo:** Otimizar a utilização do espaço em tela, eliminar a necessidade de rolagem vertical no menu e no dashboard, e transformar o Dashboard na torre de controle executiva da loja.

---

## 1. Barra Lateral Retrátil (`main.py`)

### Problema Atual
- Largura fixa de 110px.
- Cada botão usa layout vertical (`ft.Column([Icon, Text])`), com altura ~60px.
- 13 botões resultam em >700px de altura, forçando uma barra de rolagem vertical em telas comuns de balcão (1366×768).

### Solução
- **Modo Compacto (Padrão/Recolhido - 56px de largura):**
  - Exibe apenas os ícones centralizados (`size=20`) com `tooltip` ao passar o mouse.
  - Altura por item: ~38px.
  - Altura total dos 13 itens: ~494px (zero rolagem vertical).
  - Ganha mais de 50px de largura para a área de conteúdo útil.
- **Modo Expandido (180px de largura):**
  - Layout horizontal: `ft.Row([Icon, Text])` com ícone à esquerda e nome da tela à direita.
  - Altura por item: ~38px (também cabe sem rolagem).
- **Botão de Alternância (Toggle):**
  - Ícone discreto no topo da barra (`ft.Icons.MENU` ou `ft.Icons.CHEVRON_LEFT`/`RIGHT`).
  - Preferência salva em banco (`database.config_obter("menu_expandido", "0")`).

---

## 2. Novo Dashboard Executivo (`views/dashboard.py`)

### Problemas Atuais
- A lista de Presença de Hoje é aberta diretamente na tela com todos os funcionários em linhas verticais, ocupando mais de 50% da altura da tela.
- Entregadores aparecem indevidamente na lista de presença (infringindo a regra de que entregador não bate ponto na loja).
- Falta de visão unificada e rápida de Contas a Pagar / Boletos do dia.
- Falta de atalhos de ações rápidas para operações frequentes.

### Solução
1. **Filtro de Pessoas na Presença:**
   - Excluir entregadores e colaboradores com `aparece_no_ponto == 0`.
2. **Card Compacto de Presença + Modal:**
   - Card principal exibe resumo rápido: Presentes, Folgas, Faltas e Pendentes.
   - Botão **"Lançar Presença"** abre um diálogo modal (`ft.AlertDialog`) limpo e focado, liberando todo o espaço da página principal.
3. **Card Integrado de Contas a Pagar / Boletos:**
   - Exibição de boletos com vencimento para hoje, valor total a pagar no dia e alertas de vencidos.
   - Ação rápida para quitar ou visualizar detalhes.
4. **Barra de Ações Rápidas (Atalhos):**
   - Atalhos no topo para: Novo Pedido (PDV), Fluxo de Caixa, Relatório Diário (PDF), Fornecedores e Estoque.
5. **Grade Modular 2×2:**
   - Topo: Barra com data, atualizar e atalhos rápidos.
   - Linha 1: [ Vendas do Dia ] e [ Status do Caixa & Gaveta ].
   - Linha 2: [ Contas a Pagar / Boletos ] e [ Equipe & Presença Compacta ].
   - Rodapé: Alertas Proativos de Estoque e Boletos Críticos (visíveis apenas quando acionados).

---

## 3. Roteiro de Execução

1. [x] Criar este documento de plano (`PLANO_DASHBOARD_SIDEBAR.md`).
2. [ ] Implementar a Barra Lateral Retrátil em `main.py`.
3. [ ] Implementar o Card de Boletos e Ações Rápidas no `views/dashboard.py`.
4. [ ] Implementar o Modal de Presença com filtro de entregadores no `views/dashboard.py`.
5. [ ] Reestruturar o layout em grid 2×2 modular.
6. [ ] Validar compilação e rodar testes de integração.
7. [ ] Conferir `git diff` e commitar/pushar para o GitHub.
