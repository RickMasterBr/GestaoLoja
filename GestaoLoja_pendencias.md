# GestaoLoja — Pendências e Histórico

_Atualizado: 26/08/2026_

## 📌 Pendências em Aberto / Próximos Passos

1. **Reformulação do Módulo de Estoque (Conferência Rápida de Prateleira):**
   - Substituir o modelo contábil/burocrático atual por uma ferramenta prática de 2 minutos no app (estilo a lista que a equipe já envia no WhatsApp), com cálculo automático de consumo e botão de copiar resumo formatado para o grupo da loja.
   - *Status:* Aguardando aprovação do plano de implementação.

2. **Exclusão de Registro de Ponto:**
   - Adicionar botão de exclusão de batida de ponto com diálogo de confirmação e restrição para perfis `GERENTE` e `ADMIN`.
   - *Status:* Pausado para decisão da gerência.

3. **Performance ao Vivo na Máquina da Loja:**
   - Validar tempos de abertura de Entregadores e Escala Geral diretamente no ambiente de produção com Google Drive em modo Mirror.

---

## ✅ O que já foi concluído e validado (Histórico Consolidado)

### ⚙️ Interface, Usabilidade e Padronização Visual
- **Padronização com Modais em Formulários de Cadastro (`ft.AlertDialog`):**
  - **Parâmetros > Pessoas:** Removido o formulário gigante estático; tela focada na tabela imediata; botão `[ + Novo Colaborador ]` abrindo modal atômico com 4 abas (*Funcional*, *Acesso & PIN*, *Dados Pessoais*, *Dias Fixos*).
  - **Parâmetros > Bairros:** Formulário estático removido; cabeçalho com contagem e botão `[ + Novo Bairro ]`, com modal `dlg_bairro` para inclusão e edição rápida.
  - **Parâmetros > Métodos de Pagamento:** Tabela no topo com totalizador e botão `[ + Novo Método ]`, com modal `dlg_metodo`.
  - **Parâmetros > Categorias Extras:** Tabela no topo com badges de fluxo e botão `[ + Nova Categoria ]`, com modal `dlg_categoria`.
  - **Fornecedores:** Removido o card estático do meio da tela; tabela limpa com botão `[ + Novo Fornecedor ]` e modal unificado para cadastro e edição.
  - **Fiados:** Removido formulário do topo; tabela imediata com totalizador em aberto e botão `[ + Novo Fiado ]` com modal `dlg_fiado`.
- **Barra Lateral Retrátil (`main.py`):**
  - Modos compacto (58px) e expandido (180px), liberando mais de 50px de largura útil.
  - Altura compactada para 38px/item, **eliminando 100% a barra de rolagem vertical** em qualquer resolução.
  - Persistência da preferência do usuário no banco (`menu_expandido`).
- **Dashboard Executivo 2×2 (`views/dashboard.py`):**
  - Presença compacta com contadores coloridos (*Trabalhando, Folga, Falta, Pendente*) e modal de lançamento focado.
  - Exclusão automática de entregadores e funcionários com `aparece_no_ponto == 0`.
  - Card de Contas a Pagar / Boletos com aging (vencendo hoje, atrasados e próximos 7 dias).
  - Barra de Ações Rápidas no topo (sem emojis, com ícones corporativos sóbrios).
  - Correção de bugs de acesso a colunas `sqlite3.Row` e suporte a aliases de navegação (`page.navegar()`).
- **Módulo de Calendário & Agenda Operacional (`views/agenda.py`):**
  - Tabela `cad_agenda` com migração idempotente e CRUD completo.
  - Grid mensal interativo (7 colunas) com destaques para hoje e dia selecionado, badges automáticos de boletos a vencer e contagem de lembretes.
  - Painel diário lateral com detalhamento de boletos e checklist de tarefas (com risco dinâmico no texto em tempo real).
  - Modal categorizado (*Lembrete*, *Entrega*, *Manutenção*, *Financeiro*).

### ⌨️ Autenticação e Segurança
- **Login com PIN pelo Teclado Físico (`views/login.py`):**
  - Suporte completo a números da fileira superior e teclado numérico lateral (*Numpad*), com `Backspace` e `Escape`. Listener desativado imediatamente após o login.
- **Segurança de Bancos de Dados:**
  - `loja.db` e `loja_caixa.db` removidos do rastreamento do Git via `git rm --cached` e blindados pelo `.gitignore`.
  - Ambiente de teste isolado `loja_caixa_teste.db` via variável `GESTAOLOJA_TESTE` para execução de testes sem riscos à produção.

### ⚡ Performance, Navegação e Infraestrutura
- **Transição Instantânea de Telas (`main.py`):**
  - `area_conteudo` desacoplada com `ft.Stack` de 2 camadas (`camada_view` e `camada_loading`). O clique no menu exibe o spinner em ~3ms sem travar a interface.
- **Lazy Loading da Escala Geral (`views/escala_geral.py`):**
  - Remoção da pré-carga desnecessária de mais de 350 controles da tabela de ponto.
- **Relatórios em PDF:**
  - Gerador do Espelho de Ponto Individual (`gerar_pdf_espelho_ponto`) com quadro de horas e campo de assinaturas.
  - Inclusão dos dados de ponto no Holerite PDF (`gerar_pdf_holerite`).
- **Correção do Build PyInstaller (`GestaoLoja.spec`):**
  - Inclusão de `collect_data_files('flet')` e `collect_submodules('flet')` e remoção de path absoluto quebrado.
- **Banco de Dados:**
  - 6 novos índices criados no SQLite (ganho de até 85x em relatórios).
  - Eliminação de queries N+1 em `escala_contar_dias` e cálculo de motoboys.
  - Salvamento automático de ponto com validação e alerta de divergência de horário padrão.
