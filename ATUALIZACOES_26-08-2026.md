# 📋 Atualizações e Melhorias — Sessão 26/08/2026

**Projeto:** Gestão Loja (`loja_app`)  
**Data:** 26 de Agosto de 2026  
**Repositório:** [https://github.com/RickMasterBr/GestaoLoja.git](https://github.com/RickMasterBr/GestaoLoja.git)  
**Branch:** `main`  
**Status no Remoto:** Todos os commits validados e sincronizados com sucesso.

---

## 🚀 1. Novas Funcionalidades e Melhorias

### ⌨️ Digitação do PIN pelo Teclado Físico na Tela de Login
- **Arquivo modificado:** `views/login.py` (Commit: `c4f6e36`)
- **O que mudou:**
  - Após clicar no perfil do colaborador, o PIN de 4 dígitos agora pode ser digitado **diretamente pelo teclado físico** (tanto os números da fileira superior `0-9` quanto o teclado numérico lateral *Numpad*).
  - Tecla **`Backspace`**: apaga o último dígito inserido.
  - Tecla **`Escape` (Esc)**: cancela e retorna para a tela de seleção de colaboradores.
  - Os círculos de preenchimento continuam atualizando em tempo real e a verificação é disparada automaticamente no 4º dígito.
  - O ouvinte de teclado é desativado imediatamente após o login (`page.on_keyboard_event = None`), evitando qualquer conflito com campos de texto do PDV ou de outras telas.

---

### ⚡ Eliminação da Trava de Saída da Escala Geral
- **Arquivos modificados:** `main.py`, `views/escala_geral.py` (Commit: `762b00a`)
- **Problema resolvido:** Ao trocar de tela saindo da Escala Geral, a interface ficava congelada por ~643ms destruindo a grade de ~1.200 controles de forma síncrona antes do spinner de carregamento aparecer.
- **O que mudou:**
  1. **Em `main.py`:** A `area_conteudo` foi reestruturada como um `ft.Stack` com duas camadas (`camada_view` e `camada_loading`). Ao clicar em qualquer menu, o sistema apenas ativa `camada_loading.visible = True` (~3ms), exibindo o spinner de "Carregando..." **instantaneamente**. A desmontagem da tela anterior e construção da nova ocorrem de forma protegida em segundo plano pela thread de trabalho.
  2. **Em `views/escala_geral.py`:** Implementado *lazy loading* na seção de Ponto. A tela não gera mais os mais de 350 controles da tabela de ponto na inicialização se a seção estiver oculta; o Ponto é consultado e construído apenas se o usuário clicar no botão "Ponto".

---

### 📦 Correção do Build do Executável (PyInstaller)
- **Arquivo modificado:** `GestaoLoja.spec` (Commit: `7c0148e`)
- **Problema resolvido:** O arquivo de especificação `.spec` continha um caminho fixo de uma pasta temporária de outro computador (`version='C:\Users\Richard\...'`) que causava erro de build em qualquer outro PC, e `datas=[]` não incluía os arquivos internos e metadados do Flet.
- **O que mudou:**
  - Remoção do caminho absoluto quebrado.
  - Inclusão automática de arquivos de runtime e submódulos do Flet via `collect_data_files('flet')` e `collect_submodules('flet')`, permitindo que o executável seja gerado e abra normalmente.

---

### 🔒 Higiene e Segurança do Repositório Git
- **Ação realizada:** Commit `afa5e74`
- **O que mudou:**
  - Os bancos SQLite `loja.db` e `loja_caixa.db` foram desrastreados do repositório remoto via `git rm --cached`.
  - Os arquivos continuam existindo e operando normalmente no disco local da máquina, mas agora respeitam a regra `*.db` do `.gitignore`, protegendo os dados de caixa e clientes de exposição pública.

---

### 📚 Documentação das Regras de Negócio — Pagamento de Extras
- **Arquivo modificado:** `GestaoLoja_pendencias.md` (Commit: `7ec9337`)
- **Esclarecimento consolidado:**
  1. **Dia EXTRA na Escala (`tipo = 'EXTRA'`):** Representa um plantão ou dia inteiro trabalhado fora da escala normal. Entra **diretamente no total líquido do Holerite**:
     `Valor Extras = dias_extra * valor_dia_extra`
  2. **Horas Extras no Ponto Diário (`horas_extras`):** Calculadas quando a jornada diária excede a carga padrão (ex: 8h):
     - Para `FIXO`: `valor_hora = salario_base / 220` (divisor padrão CLT).
     - Para `DIARIO`: `valor_hora = diaria_valor / carga_horaria`.
     - Adicional de 50%: `valor_hora_extra = valor_hora * 1.5`.
     - **Regra de Pagamento:** Os valores de horas extras do ponto são de caráter **informativo** e para espelho de ponto/auditoria, não inflando automaticamente o salário líquido para evitar pagamento duplicado com dias extras já lançados na escala.

---

## 📝 2. Histórico de Commits desta Rodada no GitHub

| Commit | Mensagem / Descrição |
|---|---|
| `7ec9337` | `docs: Atualiza pendencias com resolucao do build spec e detalhamento das regras de extras` |
| `7c0148e` | `fix(build): Corrige GestaoLoja.spec incluindo datas do Flet e removendo path absoluto de version` |
| `afa5e74` | `chore: Remove loja.db e loja_caixa.db do rastreamento do Git` |
| `c4f6e36` | `feat: Permite digitacao do PIN pelo teclado fisico na tela de login` |
| `762b00a` | `perf: Elimina trava de saida da Escala Geral com Stack desacoplado e lazy load do ponto` |

---

*Arquivo gerado para registro e contextualização da equipe.*
