# 📋 Atualizações e Melhorias — Sessão 26/08/2026

**Projeto:** Gestão Loja (`loja_app`)  
**Data:** 26 de Agosto de 2026  
**Repositório:** [https://github.com/RickMasterBr/GestaoLoja.git](https://github.com/RickMasterBr/GestaoLoja.git)  
**Branch:** `main`  
**Status no Remoto:** Todos os commits validados e sincronizados com sucesso.

---

## 🚀 1. Novas Funcionalidades e Melhorias

### 📅 Novo Módulo de Calendário & Agenda Operacional
- **Arquivos:** `views/agenda.py` (NOVO), `database.py`, `main.py`, `views/dashboard.py`
- **Commit:** `d09f819`
- **O que mudou:**
  - Criada a nova tela de **Agenda & Calendário** da loja, centralizando prazos, compromissos e tarefas.
  - **Banco de Dados Seguro (`cad_agenda`):** Criada tabela com migração idempotente e CRUD completo (`agenda_inserir`, `agenda_listar_mes`, `agenda_listar_dia`, `agenda_concluir`, `agenda_atualizar`, `agenda_excluir`, `agenda_boletos_mes`).
  - **Grid Mensal Interativo (7 colunas):** Exibe o mês completo destacando o dia de hoje (índigo) e o dia selecionado (teal). Cada dia exibe badges automáticos de **boletos a vencer** (com valor em aberto ou status pago) e **quantidade de lembretes**.
  - **Painel Lateral do Dia:** Mostra em detalhes os boletos que vencem na data e um **checklist de tarefas interativo** (marcar a caixa risca o texto em tempo real), com horários e tags de categoria.
  - **Modal de Lembretes:** Permite registrar tarefas com data, horário opcional, detalhes e categorias (*Lembrete Geral*, *Chegada de Fornecedor*, *Manutenção/Limpeza*, *Financeiro/Contas*).
  - **Integração no Sistema:** Inserido no menu lateral (`TELAS`) e atalho nas *Ações Rápidas* do Dashboard.

---

### 💳 Modernização da Tela de Fiados (Foco na Tabela + Modal)
- **Arquivo modificado:** `views/fiados.py`
- **Commit:** `44cca1f`
- **O que mudou:**
  - O formulário de "Registrar Novo Fiado" que ficava fixo no topo ocupando espaço foi **removido**.
  - A **Tabela de Fiados** agora é exibida diretamente no topo da tela sem necessidade de rolagem prévia.
  - **Cabeçalho Executivo:** Título, filtro `[x] Mostrar apenas abertos`, indicador destacado **`Total em aberto: R$ X,XX`** e botão **`[ + Novo Fiado ]`**.
  - **Modal `dlg_fiado`:** Pop-up limpo e focado tanto para cadastrar um novo fiado quanto para editar fiados existentes ao clicar no ícone de lápis (`✏️`).

---

### 🏢 Modernização da Tela de Fornecedores (Foco na Tabela + Modal)
- **Arquivo modificado:** `views/fornecedores.py`
- **Commit:** `3b44c0d`
- **O que mudou:**
  - O formulário estático gigante `bloco_form` que ficava no meio da tela entre as contas a pagar e a lista de fornecedores foi **removido**.
  - A tela agora possui apenas os 2 blocos essenciais: **Contas a Pagar — Vencimentos** (aging) e **Fornecedores Cadastrados** (tabela).
  - Adicionado botão de destaque **`[ + Novo Fornecedor ]`** no cabeçalho da tabela ao lado do filtro de ativos.
  - **Modal `dlg_fornecedor`:** Janela pop-up com campos organizados (Nome, Telefone, E-mail, CNPJ/CPF, Endereço, Vendedor, Observações e Ativo), utilizada tanto para novo cadastro quanto para edição com 1 clique no botão `Editar`.

---

### ⚙️ Modernização de Parâmetros > Abas Bairros, Métodos e Categorias (Modais Unificados)
- **Arquivo modificado:** `views/parametros.py`
- **Commit:** `222683f`
- **O que mudou:**
  - **Aba Bairros:** Removido o formulário fixo do topo; foco imediato na tabela de bairros, cabeçalho executivo com contagem e botão `[ + Novo Bairro ]`, com modal `dlg_bairro` para inclusão e edição rápida.
  - **Aba Métodos de Pagamento:** Removido o card estático do topo; tabela no topo com totalizador e botão `[ + Novo Método ]`, com modal `dlg_metodo`.
  - **Aba Categorias Extras:** Removido o card estático do topo; tabela com totalizador e botão `[ + Nova Categoria ]`, com modal `dlg_categoria`.
  - **Consistência Total:** 100% das abas de cadastro de Parâmetros agora seguem rigorosamente o mesmo padrão corporativo, limpo e sem poluição visual.

---

### 👥 Modernização de Parâmetros > Aba Pessoas (Modal Unificado com 4 Abas)
- **Arquivo modificado:** `views/parametros.py`
- **Commit:** `770e12e`
- **O que mudou:**
  - Removidos da tela principal o formulário gigante de cadastro, o card de dados pessoais e o card de dias fixos.
  - A tela agora foca imediatamente na **Tabela de Colaboradores**, com cabeçalho contendo contagem de ativos/inativos e o botão de destaque **`[ + Novo Colaborador ]`**.
  - **Modal Unificado em 4 Abas:**
    1. 📋 **Funcional:** Nome, Tipo, Cargo, Tipo Salário, Salário Base, Diária, Bônus Feriado, Bônus Extra, Desconto Falta, Horários Padrão (`HH:MM`) e flags de Ativo e Ponto.
    2. 🔐 **Acesso & PIN:** Nível de perfil (`OPERADOR`, `GERENTE`, `ADMIN`, `SEM_ACESSO`) e PIN de 4 dígitos.
    3. 📄 **Dados Pessoais:** CPF, RG, Data de Nascimento, Telefone, Endereço e Observações.
    4. 📅 **Dias Fixos:** Grade semanal (Terça a Domingo) com horário de entrada para auto-preenchimento da escala.
  - **Salvamento Atômico:** Grava todas as 4 abas de uma só vez, fecha a janela e atualiza a lista.

---

### 📊 Novo Dashboard Executivo em Grade 2×2 & Ações Rápidas
- **Arquivos modificados:** `views/dashboard.py`, `main.py`
- **Commits:** `2e43115`, `9623ec0`, `271f834`
- **O que mudou:**
  - **Filtro de Entregadores:** A presença do Dashboard agora exclui automaticamente entregadores e colaboradores com `aparece_no_ponto == 0`.
  - **Card de Presença Compacto:** A lista gigante de colaboradores que ocupava mais de 500px foi substituída por badges coloridos com contadores (*Trabalhando*, *Folga*, *Falta*, *Pendente*) + botão "Lançar Presença", que abre um diálogo modal focado sem poluir a tela.
  - **Card de Contas a Pagar / Boletos:** Exibe boletos vencendo hoje, boletos vencidos em atraso, previsão dos próximos 7 dias e botão direto para gerenciar boletos.
  - **Barra de Ações Rápidas:** Atalhos de 1 clique no topo (*Novo Pedido / PDV*, *Agenda*, *Fluxo de Caixa*, *Relatório Diário*, *Fornecedores*, *Estoque*, *Entregadores*).
  - **Correções:** Resolvido `AttributeError` em objetos `sqlite3.Row` na filtragem da equipe e adicionados sinônimos de telas no `main.py` (`ALIASES_TELAS`) com aviso de permissão (*SnackBar*) se o operador não tiver acesso.
  - **Identidade Visual:** Removido o ícone de raio amarelo (`FLASH_ON`), mantendo layout sóbrio sem emojis.

---

### 📱 Nova Barra Lateral Retrátil (Ganha Espaço de Tela e Elimina Rolagem)
- **Arquivo modificado:** `main.py` (Commit: `2e43115`)
- **O que mudou:**
  - **Modo Compacto (58px):** Apenas ícones centralizados com dica ao passar o mouse (*tooltip*). Libera mais de 50px de largura útil para as telas do PDV, Dashboard e relatórios.
  - **Modo Expandido (180px):** Ícone à esquerda e texto à direita em layout horizontal elegante.
  - **Eliminação da Rolagem Vertical:** Altura dos itens compactada para 38px, fazendo com que todos os 14 itens do menu caibam perfeitamente na vertical em telas de qualquer resolução (inclusive monitores balcão 768p).
  - **Botão Toggle:** Botão no topo do menu para alternar entre os modos, salvando a preferência do usuário no banco (`config_definir("menu_expandido", ...)`).

---

### ⌨️ Digitação do PIN pelo Teclado Físico na Tela de Login
- **Arquivo modificado:** `views/login.py` (Commit: `c4f6e36`)
- **O que mudou:**
  - Suporte completo ao teclado físico (números normais `0-9` e teclado numérico lateral *Numpad*).
  - Suporte a `Backspace` para apagar e `Escape` para voltar à seleção de perfis.
  - Higiene de ciclo de vida: o listener é desativado imediatamente após o login (`page.on_keyboard_event = None`).

---

### ⚡ Transição Instantânea de Telas & Eliminação de Travamento
- **Arquivos modificados:** `main.py`, `views/escala_geral.py` (Commit: `762b00a`)
- **O que mudou:**
  - `area_conteudo` reestruturada com `ft.Stack` de duas camadas (`camada_view` e `camada_loading`). O spinner de carregamento surge em menos de 3ms.
  - *Lazy loading* na tabela de Ponto da Escala Geral, evitando criar centenas de controles pesados se a aba estiver fechada.

---

### 📦 Correção do Build Executável (PyInstaller)
- **Arquivo modificado:** `GestaoLoja.spec` (Commit: `7c0148e`)
- **O que mudou:**
  - Removido caminho absoluto quebrado que impedia o build em outras máquinas.
  - Coleta automática de binários e metadados do Flet via `collect_data_files('flet')` e `collect_submodules('flet')`.

---

### 🔒 Segurança dos Bancos de Dados
- **Ação:** Commit `afa5e74`
- **O que mudou:**
  - `loja.db` e `loja_caixa.db` removidos do Git tracking via `git rm --cached`, mantidos intactos no disco local e cumprindo o `.gitignore`.

---

## 📊 2. Histórico Consolidado de Commits da Sessão

| Hash | Mensagem do Commit |
| :--- | :--- |
| `222683f` | `feat(parametros): Padroniza abas Bairros, Metodos e Categorias com modais e foco nas tabelas` |
| `f745517` | `fix(agenda): Remove botao redundante do topo e corrige simbolo duplicado de soma` |
| `d09f819` | `feat(agenda): Implementa modulo completo de Calendario e Agenda Operacional` |
| `44cca1f` | `feat(fiados): Moderniza tela de fiados com modal unificado e cabecalho executivo` |
| `3b44c0d` | `feat(fornecedores): Converte formulario de cadastro em modal e despolui a tela` |
| `770e12e` | `feat(parametros): Condensa cadastro de pessoas em modal unificado com abas` |
| `271f834` | `fix(dashboard): Corrige navegacao dos botoes de acoes rapidas e remove icone de raio` |
| `9623ec0` | `fix(dashboard): Corrige acesso a colunas em sqlite3.Row na filtragem da equipe` |
| `2e43115` | `feat(ui): Implementa barra lateral retratil e moderniza Dashboard com grid 2x2 e acoes rapidas` |
| `94ff301` | `docs: Adiciona ATUALIZACOES_26-08-2026.md com relatorio completo das alteracoes` |
| `7ec9337` | `docs: Atualiza pendencias com resolucao do build spec e detalhamento das regras de extras` |
| `7c0148e` | `fix(build): Corrige GestaoLoja.spec incluindo datas do Flet e removendo path absoluto de version` |
| `afa5e74` | `chore: Remove loja.db e loja_caixa.db do rastreamento do Git` |
| `c4f6e36` | `feat: Permite digitacao do PIN pelo teclado fisico na tela de login` |

---

## 🎯 3. Padrão de Interface Estabelecido

Com as melhorias de hoje, todo o aplicativo foi padronizado sob os seguintes princípios de UX/UI:
1. **Telas Focadas nos Dados (Sem Formulários Estáticos Gigantes):** Nenhuma tela principal possui formulários enormes empurrando tabelas para baixo. O foco imediato é sempre a visualização e os indicadores executivos.
2. **Modais Unificados de Cadastro e Edição (`ft.AlertDialog`):** Adicionar um novo registro ou editar um registro existente utiliza a mesma janela pop-up limpa, com validação e salvamento atômico.
3. **Menu Lateral Flexível e Compacto:** Zero rolagem vertical, ganhando espaço de tela quando recolhido e legível quando expandido.
4. **Isolamento e Segurança de Banco de Dados:** Todos os testes automatizados são executados em base isolada de teste (`loja_caixa_teste.db`), garantindo integridade absoluta aos dados de produção da loja.
