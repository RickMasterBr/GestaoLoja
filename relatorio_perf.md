# Diagnostico de performance por tela

Banco de teste: `C:\Users\User\AppData\Local\Temp\claude\c--Users-User-Downloads-GitHub-Loja-APP-20260820T170425Z-1-001-GitHub-Loja-APP\90753208-bb6f-4424-8a32-eab5cd0cdaf4\scratchpad\perf\teste_loja.db`


## 1. Resumo por tela (ms)

| Tela | Rodada | import | build (view()) | page.update() | SQL total | # queries | # conexoes | # controles Flet |
|---|---|---|---|---|---|---|---|---|
| extras | 1 | 2.1 | 179.3 | 11.9 | 18.0 | 6 | 6 | 33 |
| fluxo_caixa | 1 | 476.3 | 43.0 | 18.6 | 0.0 | 0 | 0 | 58 |
| fluxo_caixa -> *Gerar (aba Diario)* | 1 | (acao) | 47.9 | (incluso) | 5.8 | 1 | 1 | 99 |
| fluxo_caixa -> *Gerar (aba Periodo)* | 1 | (acao) | 31.1 | (incluso) | 6.7 | 1 | 1 | 155 |
| escala_geral | 1 | 5.0 | 114.8 | 299.9 | 8.6 | 2 | 2 | 1227 |
| escala_geral -> *Trocar para secao Ponto* | 1 | (acao) | 73.9 | (incluso) | 0.0 | 0 | 0 | 1227 |
| estoque | 1 | 1.6 | 150.2 | 40.3 | 24.9 | 10 | 10 | 177 |
| relatorio_diario | 1 | 1.2 | 129.9 | 26.2 | 62.9 | 67 | 19 | 257 |
| relatorio_periodo | 1 | 1.1 | 1.4 | 4.5 | 0.0 | 0 | 0 | 15 |
| relatorio_periodo -> *Gerar Relatorio (mes corrente)* | 1 | (acao) | 3144.1 | (incluso) | 2839.7 | 171 | 89 | 876 |
| relatorio_periodo -> *Gerar Relatorio (90 dias)* | 1 | (acao) | 2248.5 | (incluso) | 2030.0 | 171 | 89 | 876 |
| relatorio_periodo -> *Gerar Relatorio (365 dias)* | 1 | (acao) | 1860.5 | (incluso) | 1622.3 | 171 | 89 | 876 |
| funcionarios | 1 | 0.9 | 6.1 | 7.1 | 2.2 | 1 | 1 | 10 |
| funcionarios -> *Carregar (1o funcionario, mes corrente)* | 1 | (acao) | 106.1 | (incluso) | 15.7 | 15 | 5 | 373 |
| entregadores | 1 | 1.2 | 95.6 | 46.0 | 32.6 | 57 | 7 | 524 |
| fornecedores | 1 | 0.9 | 30.3 | 26.3 | 3.2 | 1 | 1 | 216 |
| parametros | 1 | 1.6 | 58.8 | 69.3 | 14.5 | 9 | 9 | 1151 |
| extras | 2 | 0.0 | 27.3 | 12.6 | 12.1 | 6 | 6 | 33 |
| fluxo_caixa | 2 | 0.0 | 3.3 | 11.5 | 0.0 | 0 | 0 | 58 |
| fluxo_caixa -> *Gerar (aba Diario)* | 2 | (acao) | 21.5 | (incluso) | 6.5 | 1 | 1 | 99 |
| fluxo_caixa -> *Gerar (aba Periodo)* | 2 | (acao) | 22.0 | (incluso) | 4.2 | 1 | 1 | 155 |
| escala_geral | 2 | 0.0 | 50.1 | 210.6 | 3.6 | 2 | 2 | 1227 |
| escala_geral -> *Trocar para secao Ponto* | 2 | (acao) | 62.6 | (incluso) | 0.0 | 0 | 0 | 1227 |
| estoque | 2 | 0.0 | 108.5 | 30.6 | 20.0 | 10 | 10 | 177 |
| relatorio_diario | 2 | 0.0 | 83.0 | 21.4 | 39.5 | 67 | 19 | 257 |
| relatorio_periodo | 2 | 0.0 | 0.7 | 3.9 | 0.0 | 0 | 0 | 15 |
| relatorio_periodo -> *Gerar Relatorio (mes corrente)* | 2 | (acao) | 1468.9 | (incluso) | 1319.8 | 171 | 89 | 876 |
| relatorio_periodo -> *Gerar Relatorio (90 dias)* | 2 | (acao) | 1451.9 | (incluso) | 1291.7 | 171 | 89 | 876 |
| relatorio_periodo -> *Gerar Relatorio (365 dias)* | 2 | (acao) | 1498.5 | (incluso) | 1336.1 | 171 | 89 | 876 |
| funcionarios | 2 | 0.0 | 3.8 | 5.3 | 1.5 | 1 | 1 | 10 |
| funcionarios -> *Carregar (1o funcionario, mes corrente)* | 2 | (acao) | 60.3 | (incluso) | 7.5 | 15 | 5 | 373 |
| entregadores | 2 | 0.0 | 51.7 | 33.4 | 17.7 | 57 | 7 | 524 |
| fornecedores | 2 | 0.0 | 17.3 | 18.7 | 1.7 | 1 | 1 | 216 |
| parametros | 2 | 0.0 | 58.3 | 103.4 | 14.8 | 9 | 9 | 1151 |

## 2. Detalhe por tela


### extras (rodada 1)

- import: **2.1 ms** | build: **179.3 ms** | update: **11.9 ms** | SQL: **18.0 ms** | controles: **33**
- construcao Python/Flet fora do SQL: **154.7 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.pessoa_listar()` | 3 | 21.0 |
| `database.categoria_extra_listar()` | 1 | 6.5 |
| `database.metodo_pag_listar()` | 1 | 5.4 |
| `database.mov_extra_listar_por_data()` | 1 | 5.0 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 3 | 9.5 |
| `SQL exec SELECT * FROM cad_categorias_extra ORDER` | 1 | 3.1 |
| `SQL exec SELECT * FROM cad_metodos_pag ORDER BY n` | 1 | 2.7 |
| `SQL exec SELECT me.*, cp.nome AS nome_pessoa, ce.` | 1 | 2.4 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 AND` | 3 | 0.3 |
| `SQL fetchall SELECT * FROM cad_categorias_extra ORDER` | 1 | 0.1 |
| `SQL fetchall SELECT * FROM cad_metodos_pag ORDER BY n` | 1 | 0.0 |
| `SQL fetchall SELECT me.*, cp.nome AS nome_pessoa, ce.` | 1 | 0.0 |

### fluxo_caixa (rodada 1)

- import: **476.3 ms** | build: **43.0 ms** | update: **18.6 ms** | SQL: **0.0 ms** | controles: **58**
- construcao Python/Flet fora do SQL: **43.0 ms**

### fluxo_caixa -> acao: Gerar (aba Diario) (rodada 1)

- total da acao: **47.9 ms** | SQL: **5.8 ms** | queries: **1** | conexoes: **1** | controles na tela depois: **99**
- Python/Flet fora do SQL (inclui page.update() interno): **40.6 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.fluxo_caixa_listar_lancamentos()` | 1 | 10.4 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 5.7 |
| `SQL fetchall WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 0.0 |

### fluxo_caixa -> acao: Gerar (aba Periodo) (rodada 1)

- total da acao: **31.1 ms** | SQL: **6.7 ms** | queries: **1** | conexoes: **1** | controles na tela depois: **155**
- Python/Flet fora do SQL (inclui page.update() interno): **22.3 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.fluxo_caixa_listar_lancamentos()` | 1 | 11.8 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 6.7 |
| `SQL fetchall WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 0.0 |

### escala_geral (rodada 1)

- import: **5.0 ms** | build: **114.8 ms** | update: **299.9 ms** | SQL: **8.6 ms** | controles: **1227**
- construcao Python/Flet fora do SQL: **103.7 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.pessoa_listar()` | 1 | 9.1 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 4.2 |
| `SQL exec SELECT data, id_pessoa, tipo FROM escala` | 1 | 3.8 |
| `SQL fetchall SELECT data, id_pessoa, tipo FROM escala` | 1 | 0.4 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 0.2 |

### escala_geral -> acao: Trocar para secao Ponto (rodada 1)

- total da acao: **73.9 ms** | SQL: **0.0 ms** | queries: **0** | conexoes: **0** | controles na tela depois: **1227**
- Python/Flet fora do SQL (inclui page.update() interno): **73.9 ms**

### estoque (rodada 1)

- import: **1.6 ms** | build: **150.2 ms** | update: **40.3 ms** | SQL: **24.9 ms** | controles: **177**
- construcao Python/Flet fora do SQL: **113.3 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.estoque_produto_listar()` | 4 | 25.2 |
| `database.estoque_categoria_listar()` | 4 | 20.0 |
| `database.estoque_produtos_abaixo_minimo()` | 1 | 6.1 |
| `database.estoque_valor_total()` | 1 | 4.3 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT ep.*, ec.nome AS nome_categoria,` | 4 | 11.3 |
| `SQL exec SELECT * FROM estoque_categorias WHERE a` | 3 | 6.9 |
| `SQL exec SELECT ep.*, ec.nome AS nome_categoria F` | 1 | 2.6 |
| `SQL exec SELECT * FROM estoque_categorias ORDER B` | 1 | 2.0 |
| `SQL exec SELECT COALESCE(SUM(quantidade_atual * p` | 1 | 2.0 |
| `SQL fetchall SELECT ep.*, ec.nome AS nome_categoria,` | 4 | 0.1 |
| `SQL fetchall SELECT * FROM estoque_categorias WHERE a` | 3 | 0.0 |
| `SQL fetchall SELECT * FROM estoque_categorias ORDER B` | 1 | 0.0 |
| `SQL fetchone SELECT COALESCE(SUM(quantidade_atual * p` | 1 | 0.0 |
| `SQL fetchall SELECT ep.*, ec.nome AS nome_categoria F` | 1 | 0.0 |

### relatorio_diario (rodada 1)

- import: **1.2 ms** | build: **129.9 ms** | update: **26.2 ms** | SQL: **62.9 ms** | controles: **257**
- construcao Python/Flet fora do SQL: **49.8 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.calcular_pagamento_entregador()` | 10 | 57.4 |
| `database.config_obter()` | 2 | 7.4 |
| `database.fluxo_caixa_recalcular()` | 1 | 7.4 |
| `database.plataforma_listar()` | 1 | 3.5 |
| `database.fluxo_caixa_abrir()` | 1 | 3.1 |
| `database.pessoa_listar()` | 1 | 3.1 |
| `database.mov_extra_listar_por_data()` | 1 | 2.6 |
| `database.fluxo_caixa_buscar()` | 1 | 2.3 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT diaria_valor, tipo_salario FROM c` | 10 | 16.7 |
| `SQL exec SELECT COUNT(*) AS qtd, COALESCE(SUM(rep` | 10 | 10.4 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 4.9 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 3.8 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 20 | 3.6 |
| `SQL exec SELECT valor FROM cad_configuracoes WHER` | 2 | 3.4 |
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 2.6 |
| `SQL exec SELECT COALESCE(SUM(vp.valor), 0) FROM v` | 1 | 2.5 |
| `SQL exec SELECT COUNT(*) AS qtd, COALESCE(SUM(val` | 4 | 2.0 |
| `SQL exec SELECT * FROM cad_plataformas ORDER BY n` | 1 | 1.9 |

### relatorio_periodo (rodada 1)

- import: **1.1 ms** | build: **1.4 ms** | update: **4.5 ms** | SQL: **0.0 ms** | controles: **15**
- construcao Python/Flet fora do SQL: **1.4 ms**

### relatorio_periodo -> acao: Gerar Relatorio (mes corrente) (rodada 1)

- total da acao: **3144.1 ms** | SQL: **2839.7 ms** | queries: **171** | conexoes: **89** | controles na tela depois: **876**
- Python/Flet fora do SQL (inclui page.update() interno): **218.6 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.escala_contar_dias()` | 84 | 289.2 |
| `database.pessoa_listar()` | 2 | 9.7 |
| `database.plataforma_listar()` | 1 | 5.2 |
| `database.config_obter()` | 1 | 4.2 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL fetchall SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 1273.8 |
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 925.2 |
| `SQL exec SELECT COUNT(DISTINCT p.id) AS total_ped` | 1 | 328.5 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 84 | 139.5 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 110.6 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 25.7 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 52 | 5.0 |
| `SQL exec SELECT COUNT(*) AS total_entregas, COALE` | 10 | 4.5 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 2 | 4.3 |
| `SQL exec SELECT COALESCE(SUM(vp.valor), 0) AS fat` | 1 | 4.1 |

### relatorio_periodo -> acao: Gerar Relatorio (90 dias) (rodada 1)

- total da acao: **2248.5 ms** | SQL: **2030.0 ms** | queries: **171** | conexoes: **89** | controles na tela depois: **876**
- Python/Flet fora do SQL (inclui page.update() interno): **159.7 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.escala_contar_dias()` | 84 | 201.6 |
| `database.config_obter()` | 1 | 5.6 |
| `database.pessoa_listar()` | 2 | 5.5 |
| `database.plataforma_listar()` | 1 | 2.2 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL fetchall SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 860.7 |
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 649.4 |
| `SQL exec SELECT COUNT(DISTINCT p.id) AS total_ped` | 1 | 321.1 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 84 | 96.6 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 61.3 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 15.7 |
| `SQL exec SELECT COUNT(*) AS total_entregas, COALE` | 10 | 3.8 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 52 | 3.6 |
| `SQL exec SELECT COALESCE(SUM(p.taxa_entrega), 0)` | 6 | 3.0 |
| `SQL exec SELECT valor FROM cad_configuracoes WHER` | 1 | 2.8 |

### relatorio_periodo -> acao: Gerar Relatorio (365 dias) (rodada 1)

- total da acao: **1860.5 ms** | SQL: **1622.3 ms** | queries: **171** | conexoes: **89** | controles na tela depois: **876**
- Python/Flet fora do SQL (inclui page.update() interno): **177.6 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.escala_contar_dias()` | 84 | 207.9 |
| `database.config_obter()` | 1 | 10.7 |
| `database.pessoa_listar()` | 2 | 5.7 |
| `database.plataforma_listar()` | 1 | 3.6 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL fetchall SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 625.7 |
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 532.9 |
| `SQL exec SELECT COUNT(DISTINCT p.id) AS total_ped` | 1 | 250.4 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 84 | 101.7 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 67.5 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 15.6 |
| `SQL exec SELECT valor FROM cad_configuracoes WHER` | 1 | 5.6 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 52 | 3.6 |
| `SQL exec SELECT COUNT(*) AS total_entregas, COALE` | 10 | 3.1 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 2 | 2.6 |

### funcionarios (rodada 1)

- import: **0.9 ms** | build: **6.1 ms** | update: **7.1 ms** | SQL: **2.2 ms** | controles: **10**
- construcao Python/Flet fora do SQL: **2.9 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.pessoa_listar()` | 1 | 5.1 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 2.2 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 0.1 |

### funcionarios -> acao: Carregar (1o funcionario, mes corrente) (rodada 1)

- total da acao: **106.1 ms** | SQL: **15.7 ms** | queries: **15** | conexoes: **5** | controles na tela depois: **373**
- Python/Flet fora do SQL (inclui page.update() interno): **84.6 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.ponto_resumo_mensal()` | 1 | 12.6 |
| `database.escala_listar_por_pessoa()` | 2 | 11.7 |
| `database.ponto_calcular_horas()` | 6 | 7.1 |
| `database.pessoa_buscar()` | 1 | 6.3 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM escalas_trabalho WHERE id_` | 2 | 5.8 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 4 | 3.6 |
| `SQL exec SELECT * FROM cad_pessoas WHERE id = ?` | 1 | 2.7 |
| `SQL exec SELECT * FROM registros_ponto WHERE id_p` | 1 | 2.3 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 2 | 0.4 |
| `SQL exec SELECT me.data, me.valor, me.obs FROM mo` | 2 | 0.2 |
| `SQL fetchall SELECT * FROM escalas_trabalho WHERE id_` | 2 | 0.2 |
| `SQL exec SELECT data, tipo FROM escalas_trabalho` | 1 | 0.1 |
| `SQL exec SELECT COUNT(*) FROM movimentacoes_extra` | 1 | 0.1 |
| `SQL fetchall SELECT * FROM registros_ponto WHERE id_p` | 1 | 0.1 |

### entregadores (rodada 1)

- import: **1.2 ms** | build: **95.6 ms** | update: **46.0 ms** | SQL: **32.6 ms** | controles: **524**
- construcao Python/Flet fora do SQL: **56.4 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.calcular_pagamento_entregador()` | 5 | 29.4 |
| `database.pessoa_listar()` | 1 | 6.4 |
| `database.sessao_obter()` | 1 | 0.1 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT diaria_valor, tipo_salario FROM c` | 5 | 8.7 |
| `SQL exec SELECT COUNT(*) AS qtd, COALESCE(SUM(rep` | 10 | 7.4 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 3.0 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 20 | 2.7 |
| `SQL exec SELECT COUNT(DISTINCT data) AS dias FROM` | 5 | 2.4 |
| `SQL exec SELECT p.data, COUNT(*) AS entregas, COA` | 5 | 2.3 |
| `SQL exec SELECT COALESCE(SUM(p.taxa_entrega), 0)` | 2 | 1.8 |
| `SQL exec SELECT id FROM cad_categorias_extra WHER` | 1 | 1.5 |
| `SQL exec SELECT COALESCE(SUM(p.repasse_entregador` | 2 | 1.1 |
| `SQL exec SELECT COUNT(*) FROM movimentacoes_extra` | 5 | 0.5 |

### fornecedores (rodada 1)

- import: **0.9 ms** | build: **30.3 ms** | update: **26.3 ms** | SQL: **3.2 ms** | controles: **216**
- construcao Python/Flet fora do SQL: **26.0 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.fornecedor_listar()` | 1 | 6.5 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM cad_fornecedores WHERE ati` | 1 | 3.2 |
| `SQL fetchall SELECT * FROM cad_fornecedores WHERE ati` | 1 | 0.1 |

### parametros (rodada 1)

- import: **1.6 ms** | build: **58.8 ms** | update: **69.3 ms** | SQL: **14.5 ms** | controles: **1151**
- construcao Python/Flet fora do SQL: **38.1 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.config_obter()` | 4 | 10.7 |
| `database.pessoa_listar()` | 1 | 6.6 |
| `database.plataforma_listar()` | 1 | 4.2 |
| `database.bairro_listar()` | 1 | 3.7 |
| `database.categoria_extra_listar()` | 1 | 3.5 |
| `database.metodo_pag_listar()` | 1 | 2.7 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT valor FROM cad_configuracoes WHER` | 4 | 5.0 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 ORDE` | 1 | 3.1 |
| `SQL exec SELECT * FROM cad_plataformas ORDER BY n` | 1 | 1.8 |
| `SQL exec SELECT * FROM cad_bairros ORDER BY nome_` | 1 | 1.7 |
| `SQL exec SELECT * FROM cad_metodos_pag ORDER BY n` | 1 | 1.3 |
| `SQL exec SELECT * FROM cad_categorias_extra ORDER` | 1 | 1.3 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 ORDE` | 1 | 0.2 |
| `SQL fetchall SELECT * FROM cad_bairros ORDER BY nome_` | 1 | 0.0 |
| `SQL fetchone SELECT valor FROM cad_configuracoes WHER` | 4 | 0.0 |
| `SQL fetchall SELECT * FROM cad_categorias_extra ORDER` | 1 | 0.0 |

### extras (rodada 2)

- import: **0.0 ms** | build: **27.3 ms** | update: **12.6 ms** | SQL: **12.1 ms** | controles: **33**
- construcao Python/Flet fora do SQL: **10.8 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.pessoa_listar()` | 3 | 12.7 |
| `database.categoria_extra_listar()` | 1 | 5.5 |
| `database.metodo_pag_listar()` | 1 | 3.7 |
| `database.mov_extra_listar_por_data()` | 1 | 3.6 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 3 | 5.5 |
| `SQL exec SELECT * FROM cad_categorias_extra ORDER` | 1 | 2.9 |
| `SQL exec SELECT * FROM cad_metodos_pag ORDER BY n` | 1 | 1.7 |
| `SQL exec SELECT me.*, cp.nome AS nome_pessoa, ce.` | 1 | 1.7 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 AND` | 3 | 0.2 |
| `SQL fetchall SELECT * FROM cad_categorias_extra ORDER` | 1 | 0.0 |
| `SQL fetchall SELECT * FROM cad_metodos_pag ORDER BY n` | 1 | 0.0 |
| `SQL fetchall SELECT me.*, cp.nome AS nome_pessoa, ce.` | 1 | 0.0 |

### fluxo_caixa (rodada 2)

- import: **0.0 ms** | build: **3.3 ms** | update: **11.5 ms** | SQL: **0.0 ms** | controles: **58**
- construcao Python/Flet fora do SQL: **3.3 ms**

### fluxo_caixa -> acao: Gerar (aba Diario) (rodada 2)

- total da acao: **21.5 ms** | SQL: **6.5 ms** | queries: **1** | conexoes: **1** | controles na tela depois: **99**
- Python/Flet fora do SQL (inclui page.update() interno): **13.2 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.fluxo_caixa_listar_lancamentos()` | 1 | 10.7 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 6.5 |
| `SQL fetchall WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 0.0 |

### fluxo_caixa -> acao: Gerar (aba Periodo) (rodada 2)

- total da acao: **22.0 ms** | SQL: **4.2 ms** | queries: **1** | conexoes: **1** | controles na tela depois: **155**
- Python/Flet fora do SQL (inclui page.update() interno): **16.4 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.fluxo_caixa_listar_lancamentos()` | 1 | 7.2 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 4.2 |
| `SQL fetchall WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 0.0 |

### escala_geral (rodada 2)

- import: **0.0 ms** | build: **50.1 ms** | update: **210.6 ms** | SQL: **3.6 ms** | controles: **1227**
- construcao Python/Flet fora do SQL: **45.2 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.pessoa_listar()` | 1 | 3.2 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT data, id_pessoa, tipo FROM escala` | 1 | 1.8 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 1.5 |
| `SQL fetchall SELECT data, id_pessoa, tipo FROM escala` | 1 | 0.2 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 0.1 |

### escala_geral -> acao: Trocar para secao Ponto (rodada 2)

- total da acao: **62.6 ms** | SQL: **0.0 ms** | queries: **0** | conexoes: **0** | controles na tela depois: **1227**
- Python/Flet fora do SQL (inclui page.update() interno): **62.6 ms**

### estoque (rodada 2)

- import: **0.0 ms** | build: **108.5 ms** | update: **30.6 ms** | SQL: **20.0 ms** | controles: **177**
- construcao Python/Flet fora do SQL: **81.1 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.estoque_categoria_listar()` | 4 | 18.1 |
| `database.estoque_produto_listar()` | 4 | 15.6 |
| `database.estoque_produtos_abaixo_minimo()` | 1 | 4.0 |
| `database.estoque_valor_total()` | 1 | 3.3 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT ep.*, ec.nome AS nome_categoria,` | 4 | 7.1 |
| `SQL exec SELECT * FROM estoque_categorias WHERE a` | 3 | 5.8 |
| `SQL exec SELECT * FROM estoque_categorias ORDER B` | 1 | 3.6 |
| `SQL exec SELECT ep.*, ec.nome AS nome_categoria F` | 1 | 1.9 |
| `SQL exec SELECT COALESCE(SUM(quantidade_atual * p` | 1 | 1.6 |
| `SQL fetchall SELECT * FROM estoque_categorias WHERE a` | 3 | 0.0 |
| `SQL fetchall SELECT ep.*, ec.nome AS nome_categoria,` | 4 | 0.0 |
| `SQL fetchall SELECT * FROM estoque_categorias ORDER B` | 1 | 0.0 |
| `SQL fetchone SELECT COALESCE(SUM(quantidade_atual * p` | 1 | 0.0 |
| `SQL fetchall SELECT ep.*, ec.nome AS nome_categoria F` | 1 | 0.0 |

### relatorio_diario (rodada 2)

- import: **0.0 ms** | build: **83.0 ms** | update: **21.4 ms** | SQL: **39.5 ms** | controles: **257**
- construcao Python/Flet fora do SQL: **32.5 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.calcular_pagamento_entregador()` | 10 | 31.6 |
| `database.config_obter()` | 2 | 5.5 |
| `database.fluxo_caixa_recalcular()` | 1 | 3.8 |
| `database.plataforma_listar()` | 1 | 2.7 |
| `database.pessoa_listar()` | 1 | 2.7 |
| `database.fluxo_caixa_abrir()` | 1 | 2.4 |
| `database.mov_extra_listar_por_data()` | 1 | 1.9 |
| `database.fluxo_caixa_buscar()` | 1 | 1.8 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT diaria_valor, tipo_salario FROM c` | 10 | 9.2 |
| `SQL exec SELECT COUNT(*) AS qtd, COALESCE(SUM(rep` | 10 | 6.3 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 3.0 |
| `SQL exec SELECT valor FROM cad_configuracoes WHER` | 2 | 2.6 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 2.3 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 20 | 2.0 |
| `SQL exec SELECT COALESCE(SUM(vp.valor), 0) FROM v` | 1 | 1.9 |
| `SQL exec SELECT COUNT(*) FROM ( SELECT id_pedido` | 1 | 1.6 |
| `SQL exec SELECT * FROM cad_plataformas ORDER BY n` | 1 | 1.5 |
| `SQL exec SELECT COUNT(*) AS qtd, COALESCE(SUM(val` | 4 | 1.4 |

### relatorio_periodo (rodada 2)

- import: **0.0 ms** | build: **0.7 ms** | update: **3.9 ms** | SQL: **0.0 ms** | controles: **15**
- construcao Python/Flet fora do SQL: **0.7 ms**

### relatorio_periodo -> acao: Gerar Relatorio (mes corrente) (rodada 2)

- total da acao: **1468.9 ms** | SQL: **1319.8 ms** | queries: **171** | conexoes: **89** | controles na tela depois: **876**
- Python/Flet fora do SQL (inclui page.update() interno): **109.4 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.escala_contar_dias()` | 84 | 133.4 |
| `database.pessoa_listar()` | 2 | 7.5 |
| `database.config_obter()` | 1 | 2.5 |
| `database.plataforma_listar()` | 1 | 2.0 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL fetchall SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 534.7 |
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 421.4 |
| `SQL exec SELECT COUNT(DISTINCT p.id) AS total_ped` | 1 | 218.2 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 84 | 64.7 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 45.4 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 13.4 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 AND` | 2 | 3.7 |
| `SQL exec SELECT COUNT(*) AS total_entregas, COALE` | 10 | 3.2 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 52 | 2.6 |
| `SQL exec SELECT COALESCE(SUM(p.taxa_entrega), 0)` | 6 | 2.2 |

### relatorio_periodo -> acao: Gerar Relatorio (90 dias) (rodada 2)

- total da acao: **1451.9 ms** | SQL: **1291.7 ms** | queries: **171** | conexoes: **89** | controles na tela depois: **876**
- Python/Flet fora do SQL (inclui page.update() interno): **119.7 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.escala_contar_dias()` | 84 | 137.3 |
| `database.config_obter()` | 1 | 3.9 |
| `database.pessoa_listar()` | 2 | 3.7 |
| `database.plataforma_listar()` | 1 | 2.2 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL fetchall SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 528.5 |
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 429.6 |
| `SQL exec SELECT COUNT(DISTINCT p.id) AS total_ped` | 1 | 191.2 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 84 | 67.7 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 39.8 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 14.9 |
| `SQL exec SELECT COUNT(*) AS total_entregas, COALE` | 10 | 3.2 |
| `SQL exec SELECT COALESCE(SUM(p.taxa_entrega), 0)` | 6 | 2.8 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 52 | 2.7 |
| `SQL exec SELECT valor FROM cad_configuracoes WHER` | 1 | 1.9 |

### relatorio_periodo -> acao: Gerar Relatorio (365 dias) (rodada 2)

- total da acao: **1498.5 ms** | SQL: **1336.1 ms** | queries: **171** | conexoes: **89** | controles na tela depois: **876**
- Python/Flet fora do SQL (inclui page.update() interno): **122.7 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.escala_contar_dias()` | 84 | 139.2 |
| `database.pessoa_listar()` | 2 | 3.7 |
| `database.config_obter()` | 1 | 3.3 |
| `database.plataforma_listar()` | 1 | 2.2 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL fetchall SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 558.1 |
| `SQL exec WITH pag_count AS ( SELECT id_pedido, CO` | 1 | 426.4 |
| `SQL exec SELECT COUNT(DISTINCT p.id) AS total_ped` | 1 | 205.9 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 84 | 69.8 |
| `SQL exec SELECT canal, SUM(CASE WHEN NOT EXISTS(` | 1 | 42.8 |
| `SQL exec WITH pc AS ( SELECT id_pedido, COUNT(*)` | 4 | 13.7 |
| `SQL exec SELECT COUNT(*) AS total_entregas, COALE` | 10 | 3.1 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 52 | 2.7 |
| `SQL exec SELECT COALESCE(SUM(p.taxa_entrega), 0)` | 6 | 2.4 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 2 | 1.6 |

### funcionarios (rodada 2)

- import: **0.0 ms** | build: **3.8 ms** | update: **5.3 ms** | SQL: **1.5 ms** | controles: **10**
- construcao Python/Flet fora do SQL: **1.6 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.pessoa_listar()` | 1 | 3.1 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 1.4 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 0.0 |

### funcionarios -> acao: Carregar (1o funcionario, mes corrente) (rodada 2)

- total da acao: **60.3 ms** | SQL: **7.5 ms** | queries: **15** | conexoes: **5** | controles na tela depois: **373**
- Python/Flet fora do SQL (inclui page.update() interno): **48.2 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.escala_listar_por_pessoa()` | 2 | 5.4 |
| `database.ponto_resumo_mensal()` | 1 | 5.3 |
| `database.pessoa_buscar()` | 1 | 3.4 |
| `database.ponto_calcular_horas()` | 6 | 0.7 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM escalas_trabalho WHERE id_` | 2 | 2.5 |
| `SQL exec SELECT * FROM registros_ponto WHERE id_p` | 1 | 1.5 |
| `SQL exec SELECT COUNT(*) FROM escalas_trabalho WH` | 4 | 1.4 |
| `SQL exec SELECT * FROM cad_pessoas WHERE id = ?` | 1 | 1.4 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 2 | 0.2 |
| `SQL exec SELECT me.data, me.valor, me.obs FROM mo` | 2 | 0.1 |
| `SQL fetchall SELECT * FROM escalas_trabalho WHERE id_` | 2 | 0.1 |
| `SQL exec SELECT data, tipo FROM escalas_trabalho` | 1 | 0.1 |
| `SQL exec SELECT COUNT(*) FROM movimentacoes_extra` | 1 | 0.0 |
| `SQL fetchall SELECT * FROM registros_ponto WHERE id_p` | 1 | 0.0 |

### entregadores (rodada 2)

- import: **0.0 ms** | build: **51.7 ms** | update: **33.4 ms** | SQL: **17.7 ms** | controles: **524**
- construcao Python/Flet fora do SQL: **30.6 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.calcular_pagamento_entregador()` | 5 | 13.8 |
| `database.pessoa_listar()` | 1 | 3.2 |
| `database.sessao_obter()` | 1 | 0.1 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT COUNT(*) AS qtd, COALESCE(SUM(rep` | 10 | 4.1 |
| `SQL exec SELECT diaria_valor, tipo_salario FROM c` | 5 | 4.0 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 AND` | 1 | 1.6 |
| `SQL exec SELECT id FROM cad_categorias_extra WHER` | 1 | 1.6 |
| `SQL exec SELECT p.data, COUNT(*) AS entregas, COA` | 5 | 1.5 |
| `SQL exec SELECT COUNT(DISTINCT data) AS dias FROM` | 5 | 1.4 |
| `SQL exec SELECT COALESCE(SUM(me.valor), 0) AS tot` | 20 | 1.3 |
| `SQL exec SELECT COALESCE(SUM(p.taxa_entrega), 0)` | 2 | 1.0 |
| `SQL exec SELECT COALESCE(SUM(p.repasse_entregador` | 2 | 0.7 |
| `SQL exec SELECT COUNT(*) FROM movimentacoes_extra` | 5 | 0.3 |

### fornecedores (rodada 2)

- import: **0.0 ms** | build: **17.3 ms** | update: **18.7 ms** | SQL: **1.7 ms** | controles: **216**
- construcao Python/Flet fora do SQL: **14.9 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.fornecedor_listar()` | 1 | 3.5 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT * FROM cad_fornecedores WHERE ati` | 1 | 1.7 |
| `SQL fetchall SELECT * FROM cad_fornecedores WHERE ati` | 1 | 0.0 |

### parametros (rodada 2)

- import: **0.0 ms** | build: **58.3 ms** | update: **103.4 ms** | SQL: **14.8 ms** | controles: **1151**
- construcao Python/Flet fora do SQL: **38.0 ms**

Funcoes de database.py mais caras:

| funcao | chamadas | ms |
|---|---|---|
| `database.config_obter()` | 4 | 11.7 |
| `database.categoria_extra_listar()` | 1 | 7.5 |
| `database.bairro_listar()` | 1 | 3.7 |
| `database.pessoa_listar()` | 1 | 3.5 |
| `database.plataforma_listar()` | 1 | 3.0 |
| `database.metodo_pag_listar()` | 1 | 2.8 |

Queries mais caras:

| query | chamadas | ms |
|---|---|---|
| `SQL exec SELECT valor FROM cad_configuracoes WHER` | 4 | 5.6 |
| `SQL exec SELECT * FROM cad_categorias_extra ORDER` | 1 | 2.7 |
| `SQL exec SELECT * FROM cad_bairros ORDER BY nome_` | 1 | 1.9 |
| `SQL exec SELECT * FROM cad_pessoas WHERE 1=1 ORDE` | 1 | 1.6 |
| `SQL exec SELECT * FROM cad_plataformas ORDER BY n` | 1 | 1.4 |
| `SQL exec SELECT * FROM cad_metodos_pag ORDER BY n` | 1 | 1.3 |
| `SQL fetchall SELECT * FROM cad_pessoas WHERE 1=1 ORDE` | 1 | 0.1 |
| `SQL fetchall SELECT * FROM cad_bairros ORDER BY nome_` | 1 | 0.0 |
| `SQL fetchall SELECT * FROM cad_categorias_extra ORDER` | 1 | 0.0 |
| `SQL fetchone SELECT valor FROM cad_configuracoes WHER` | 4 | 0.0 |

## 3. EXPLAIN QUERY PLAN das queries mais custosas


#### 4749.0 ms total (12 exec) - telas: relatorio_periodo

```sql
SELECT canal, SUM(CASE WHEN NOT EXISTS( SELECT 1 FROM vendas_pagamentos vp2 WHERE vp2.id_pedido = p.id AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado') ) THEN 1 ELSE 0 END) AS qtd, COALESCE(SUM( CASE WHEN EXISTS( SELECT 1 FROM vendas_pagamentos vp WHERE vp.id_pedido = p.id AND (vp.cortesia = 1 OR vp.metodo = 'Fiado') ) THEN 0.0 ELSE p.valor_total END ), 0) AS valor_total FROM vendas_pedidos p WHERE p.data BETWEEN ? AND ? GROUP BY canal HAVING SUM(CASE WHEN NOT EXISTS( SELECT 1 FROM vendas_pagamentos vp2 WHERE vp2.id_pedido = p.id AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado') ) THEN 1 ELSE 0 END) > 0 ORDER BY canal
```
```
SCAN p
USE TEMP B-TREE FOR GROUP BY
CORRELATED SCALAR SUBQUERY 1
SCAN vp2
CORRELATED SCALAR SUBQUERY 2
SCAN vp
CORRELATED SCALAR SUBQUERY 3
SCAN vp2
```

#### 3385.4 ms total (12 exec) - telas: relatorio_periodo

```sql
WITH pag_count AS ( SELECT id_pedido, COUNT(*) AS qtd, SUM(valor) AS soma_pag FROM vendas_pagamentos GROUP BY id_pedido ) SELECT vp.metodo, COALESCE(m.tipo, 'OUTROS') AS tipo, COUNT(DISTINCT CASE WHEN NOT EXISTS( SELECT 1 FROM vendas_pagamentos vp3 WHERE vp3.id_pedido = p.id AND (vp3.cortesia = 1 OR vp3.metodo = 'Fiado') ) THEN p.id ELSE NULL END) AS qtd_pedidos, COALESCE(SUM( CASE WHEN pc.qtd = 1 THEN p.valor_total WHEN vp.id = ( SELECT MIN(id) FROM vendas_pagamentos WHERE id_pedido = vp.id_pedido ) THEN vp.valor + (p.valor_total - pc.soma_pag) ELSE vp.valor END ), 0) AS total FROM vendas_pagamentos vp JOIN vendas_pedidos p ON p.id = vp.id_pedido JOIN pag_count pc ON pc.id_pedido = vp.id_pedido LEFT JOIN cad_metodos_pag m ON m.nome = vp.metodo WHERE p.data BETWEEN ? AND ? AND COALESCE(m.tipo, 'OUTROS') != 'CORTESIA' AND vp.metodo != 'Fiado' AND NOT EXISTS ( SELECT 1 FROM vendas_pagamentos vp2 WHERE vp2.id_pedido = p.id AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado') ) GROUP BY vp.metodo, m.tipo ORDER BY m.tipo, vp.metodo
```
```
CO-ROUTINE pag_count
SCAN vendas_pagamentos
USE TEMP B-TREE FOR GROUP BY
SCAN vp
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
CORRELATED SCALAR SUBQUERY 4
SCAN vp2
BLOOM FILTER ON pc (id_pedido=?)
SEARCH pc USING AUTOMATIC COVERING INDEX (id_pedido=?)
SEARCH m USING INDEX sqlite_autoindex_cad_metodos_pag_1 (nome=?) LEFT-JOIN
USE TEMP B-TREE FOR GROUP BY
CORRELATED SCALAR SUBQUERY 2
SCAN vp3
CORRELATED SCALAR SUBQUERY 3
SEARCH vendas_pagamentos
USE TEMP B-TREE FOR count(DISTINCT)
USE TEMP B-TREE FOR ORDER BY
```

#### 1515.6 ms total (12 exec) - telas: relatorio_periodo

```sql
SELECT COUNT(DISTINCT p.id) AS total_pedidos, COALESCE(SUM(p.valor_total), 0) AS valor_bruto, COALESCE(SUM( CASE WHEN EXISTS( SELECT 1 FROM vendas_pagamentos vp WHERE vp.id_pedido = p.id AND vp.cortesia = 1 ) THEN p.valor_total ELSE 0 END ), 0) AS total_cortesias FROM vendas_pedidos p WHERE p.data BETWEEN ? AND ?
```
```
USE TEMP B-TREE FOR count(DISTINCT)
SCAN p
CORRELATED SCALAR SUBQUERY 1
SCAN vp
```

#### 550.4 ms total (1024 exec) - telas: funcionarios, relatorio_periodo

```sql
SELECT COUNT(*) FROM escalas_trabalho WHERE id_pessoa = ? AND data BETWEEN ? AND ? AND tipo = ?
```
```
SEARCH escalas_trabalho USING INDEX sqlite_autoindex_escalas_trabalho_1 (data>? AND data<?)
```

#### 99.6 ms total (48 exec) - telas: relatorio_periodo

```sql
WITH pc AS ( SELECT id_pedido, COUNT(*) AS qtd FROM vendas_pagamentos GROUP BY id_pedido ) SELECT COALESCE(SUM(CASE WHEN vp.metodo NOT IN (?,?,?,?,?,?,?) THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END ELSE 0 END), 0) AS bruto_online, COALESCE(SUM(CASE WHEN vp.metodo IN (?,?,?,?,?,?,?) THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END ELSE 0 END), 0) AS bruto_maq FROM vendas_pagamentos vp JOIN vendas_pedidos p ON p.id = vp.id_pedido JOIN pc ON pc.id_pedido = vp.id_pedido WHERE p.data BETWEEN ? AND ? AND p.canal LIKE ?
```
```
CO-ROUTINE pc
SCAN vendas_pagamentos
USE TEMP B-TREE FOR GROUP BY
SCAN vp
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
BLOOM FILTER ON pc (id_pedido=?)
SEARCH pc USING AUTOMATIC COVERING INDEX (id_pedido=?)
```

#### 38.9 ms total (60 exec) - telas: entregadores, relatorio_diario

```sql
SELECT diaria_valor, tipo_salario FROM cad_pessoas WHERE id = ?
```
```
SEARCH cad_pessoas USING INTEGER PRIMARY KEY (rowid=?)
```

#### 31.9 ms total (36 exec) - telas: parametros, relatorio_diario, relatorio_periodo

```sql
SELECT valor FROM cad_configuracoes WHERE chave = ?
```
```
SEARCH cad_configuracoes USING INDEX sqlite_autoindex_cad_configuracoes_1 (chave=?)
```

#### 24.5 ms total (60 exec) - telas: entregadores, relatorio_diario

```sql
SELECT COUNT(*) AS qtd, COALESCE(SUM(repasse_entregador), 0) AS soma FROM vendas_pedidos WHERE data = ? AND id_operador = ? AND repasse_entregador > 0
```
```
SCAN vendas_pedidos
```

#### 23.2 ms total (8 exec) - telas: fluxo_caixa

```sql
WITH pag_count AS ( SELECT id_pedido, COUNT(*) AS qtd_pags FROM vendas_pagamentos GROUP BY id_pedido ) SELECT fcd.data, '00:00' AS hora, 1 AS seq, NULL AS ref_id, 'TROCO_INICIAL' AS tipo, 'Troco inicial' AS descricao, fcd.troco_inicial AS entrada, 0.0 AS saida, 'Dinheiro' AS metodo, NULL AS canal, NULL AS nome_pessoa FROM fluxo_caixa_diario fcd WHERE fcd.data BETWEEN ? AND ? UNION ALL SELECT p.data, COALESCE(p.hora, '23:59') AS hora, 2 AS seq, p.id AS ref_id, 'VENDA' AS tipo, 'Pedido #' || p.id || CASE WHEN COALESCE(pc.qtd_pags, 1) > 1 THEN ' (' || pc.qtd_pags || ' pagtos)' ELSE '' END AS descricao, p.valor_total AS entrada, 0.0 AS saida, NULL AS metodo, p.canal AS canal, NULL AS nome_pessoa FROM vendas_pedidos p LEFT JOIN pag_count pc ON pc.id_pedido = p.id WHERE p.data BETWEEN ? AND ? UNION ALL SELECT me.data, NULL AS hora, 3 AS seq, me.id AS ref_id, 'EXTRA' AS tipo, ce.descricao || COALESCE(' — ' || cp.nome, '') AS descricao, CASE WHEN me.fluxo = 'ENTRADA' THEN me.valor ELSE 0.0 END AS entrada, CASE WHEN me.fluxo = 'SAIDA' THEN me.valor ELSE 0.0 END AS saida, me.metodo AS metodo, NULL AS canal, cp.nome AS nome_pessoa FROM movimentacoes_extras me LEFT JOIN cad_categorias_extra ce ON ce.id = me.id_categoria LEFT JOIN cad_pessoas cp ON cp.id = me.id_pessoa WHERE me.data BETWEEN ? AND ? AND ce.descricao != 'Pagamento' UNION ALL SELECT me.data, NULL AS hora, 4 AS seq, me.id AS re
```
```
MERGE (UNION ALL)
LEFT
MERGE (UNION ALL)
LEFT
SEARCH fcd USING INDEX sqlite_autoindex_fluxo_caixa_diario_1 (data>? AND data<?)
USE TEMP B-TREE FOR LAST 3 TERMS OF ORDER BY
RIGHT
MATERIALIZE pag_count
SCAN vendas_pagamentos
USE TEMP B-TREE FOR GROUP BY
SCAN p
BLOOM FILTER ON pc (id_pedido=?)
SEARCH pc USING AUTOMATIC COVERING INDEX (id_pedido=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
RIGHT
MERGE (UNION ALL)
LEFT
SCAN me
SEARCH ce USING INTEGER PRIMARY KEY (rowid=?)
SEARCH cp USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
RIGHT
SEARCH ce USING COVERING INDEX sqlite_autoindex_cad_categorias_extra_1 (descricao=?)
SCAN me
SEARCH cp USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```

#### 21.9 ms total (28 exec) - telas: relatorio_diario, relatorio_periodo

```sql
SELECT * FROM cad_pessoas WHERE 1=1 AND tipo = ? ORDER BY nome
```
```
SCAN cad_pessoas
USE TEMP B-TREE FOR ORDER BY
```

#### 21.5 ms total (120 exec) - telas: relatorio_periodo

```sql
SELECT COUNT(*) AS total_entregas, COALESCE(SUM(repasse_entregador), 0) AS soma_taxas, COUNT(DISTINCT data) AS dias_com_entrega FROM vendas_pedidos WHERE data BETWEEN ? AND ? AND id_operador = ? AND repasse_entregador > 0
```
```
USE TEMP B-TREE FOR count(DISTINCT)
SCAN vendas_pedidos
```

#### 18.6 ms total (16 exec) - telas: entregadores, extras, funcionarios

```sql
SELECT * FROM cad_pessoas WHERE 1=1 AND status_ativo = 1 AND tipo = ? ORDER BY nome
```
```
SCAN cad_pessoas
USE TEMP B-TREE FOR ORDER BY
```

#### 16.0 ms total (20 exec) - telas: parametros, relatorio_diario, relatorio_periodo

```sql
SELECT * FROM cad_plataformas ORDER BY nome
```
```
SCAN cad_plataformas USING INDEX sqlite_autoindex_cad_plataformas_1
```

#### 12.8 ms total (12 exec) - telas: estoque

```sql
SELECT * FROM estoque_categorias WHERE ativo = 1 ORDER BY nome
```
```
SCAN estoque_categorias USING INDEX sqlite_autoindex_estoque_categorias_1
```

#### 12.5 ms total (332 exec) - telas: entregadores, relatorio_periodo

```sql
SELECT COALESCE(SUM(me.valor), 0) AS total FROM movimentacoes_extras me JOIN cad_categorias_extra ce ON ce.id = me.id_categoria WHERE me.data BETWEEN ? AND ? AND me.id_pessoa = ? AND ce.descricao = 'Vale'
```
```
SEARCH ce USING COVERING INDEX sqlite_autoindex_cad_categorias_extra_1 (descricao=?)
SCAN me
```

#### 11.5 ms total (48 exec) - telas: relatorio_periodo

```sql
SELECT COUNT(*) AS qtd, COALESCE(SUM(valor_total), 0) AS bruto FROM vendas_pedidos WHERE data BETWEEN ? AND ? AND canal LIKE ?
```
```
SCAN vendas_pedidos
```

#### 11.5 ms total (12 exec) - telas: relatorio_periodo

```sql
SELECT COALESCE(SUM(vp.valor), 0) AS fat_real FROM vendas_pagamentos vp JOIN vendas_pedidos p ON p.id = vp.id_pedido JOIN cad_metodos_pag m ON m.nome = vp.metodo WHERE p.data BETWEEN ? AND ? AND vp.cortesia = 0 AND m.tipo != 'CORTESIA' AND vp.metodo != 'Voucher'
```
```
SCAN vp
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
SEARCH m USING INDEX sqlite_autoindex_cad_metodos_pag_1 (nome=?)
```

#### 11.4 ms total (60 exec) - telas: relatorio_periodo

```sql
SELECT COALESCE(SUM(p.taxa_entrega), 0) AS total FROM vendas_pedidos p LEFT JOIN cad_canais c ON c.nome = p.canal WHERE p.data BETWEEN ? AND ? AND p.id_operador = ? AND COALESCE(c.entregador_plataforma, 0) = 0
```
```
SCAN p
SEARCH c USING INDEX sqlite_autoindex_cad_canais_1 (nome=?) LEFT-JOIN
```

#### 11.3 ms total (8 exec) - telas: escala_geral, extras

```sql
SELECT * FROM cad_pessoas WHERE 1=1 AND status_ativo = 1 ORDER BY nome
```
```
SCAN cad_pessoas
USE TEMP B-TREE FOR ORDER BY
```

#### 10.6 ms total (8 exec) - telas: estoque

```sql
SELECT ep.*, ec.nome AS nome_categoria, CASE WHEN ep.quantidade_atual <= ep.quantidade_minima THEN 1 ELSE 0 END AS abaixo_minimo FROM estoque_produtos ep LEFT JOIN estoque_categorias ec ON ec.id = ep.id_categoria ORDER BY ep.nome
```
```
SCAN ep
SEARCH ec USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```

#### 10.1 ms total (12 exec) - telas: relatorio_periodo

```sql
SELECT COUNT(*) FROM ( SELECT id_pedido FROM vendas_pagamentos vp JOIN vendas_pedidos p ON p.id = vp.id_pedido WHERE p.data BETWEEN ? AND ? AND vp.cortesia = 0 AND vp.metodo != 'Fiado' GROUP BY id_pedido HAVING COUNT(*) > 1 AND COUNT(DISTINCT vp.metodo) > 1 )
```
```
CO-ROUTINE (subquery-1)
SCAN vp
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
USE TEMP B-TREE FOR GROUP BY
USE TEMP B-TREE FOR count(DISTINCT)
SCAN (subquery-1)
```

#### 10.1 ms total (8 exec) - telas: extras, parametros

```sql
SELECT * FROM cad_categorias_extra ORDER BY descricao
```
```
SCAN cad_categorias_extra USING INDEX sqlite_autoindex_cad_categorias_extra_1
```

#### 8.6 ms total (8 exec) - telas: funcionarios

```sql
SELECT * FROM escalas_trabalho WHERE id_pessoa = ? AND data BETWEEN ? AND ? ORDER BY data
```
```
SEARCH escalas_trabalho USING INDEX sqlite_autoindex_escalas_trabalho_1 (data>? AND data<?)
```

#### 8.6 ms total (252 exec) - telas: relatorio_periodo

```sql
SELECT COALESCE(SUM(me.valor), 0) AS total FROM movimentacoes_extras me JOIN cad_categorias_extra ce ON ce.id = me.id_categoria WHERE me.data BETWEEN ? AND ? AND me.id_pessoa = ? AND ce.descricao = 'Consumo'
```
```
SEARCH ce USING COVERING INDEX sqlite_autoindex_cad_categorias_extra_1 (descricao=?)
SCAN me
```

#### 8.1 ms total (16 exec) - telas: relatorio_diario

```sql
WITH pc AS ( SELECT id_pedido, COUNT(*) AS qtd FROM vendas_pagamentos GROUP BY id_pedido ) SELECT COALESCE(SUM(CASE WHEN vp.metodo NOT IN (?,?,?,?,?,?,?) THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END ELSE 0 END), 0) AS bruto_online, COALESCE(SUM(CASE WHEN vp.metodo IN (?,?,?,?,?,?,?) THEN CASE WHEN pc.qtd=1 THEN p.valor_total ELSE vp.valor END ELSE 0 END), 0) AS bruto_maq FROM vendas_pagamentos vp JOIN vendas_pedidos p ON p.id = vp.id_pedido JOIN pc ON pc.id_pedido = vp.id_pedido WHERE p.data = ? AND p.canal LIKE ?
```
```
CO-ROUTINE pc
SCAN vendas_pagamentos
USE TEMP B-TREE FOR GROUP BY
SCAN vp
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
BLOOM FILTER ON pc (id_pedido=?)
SEARCH pc USING AUTOMATIC COVERING INDEX (id_pedido=?)
```

#### 7.9 ms total (8 exec) - telas: estoque

```sql
SELECT ep.*, ec.nome AS nome_categoria, CASE WHEN ep.quantidade_atual <= ep.quantidade_minima THEN 1 ELSE 0 END AS abaixo_minimo FROM estoque_produtos ep LEFT JOIN estoque_categorias ec ON ec.id = ep.id_categoria WHERE ep.ativo = 1 ORDER BY ep.nome
```
```
SCAN ep
SEARCH ec USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```

#### 7.1 ms total (8 exec) - telas: extras, parametros

```sql
SELECT * FROM cad_metodos_pag ORDER BY nome
```
```
SCAN cad_metodos_pag USING INDEX sqlite_autoindex_cad_metodos_pag_1
```

#### 6.7 ms total (16 exec) - telas: entregadores, relatorio_periodo

```sql
SELECT COALESCE(SUM(p.taxa_entrega), 0) AS total FROM vendas_pedidos p LEFT JOIN cad_canais c ON c.nome = p.canal WHERE p.data BETWEEN ? AND ? AND COALESCE(c.entregador_plataforma, 0) = 0
```
```
SCAN p
SEARCH c USING INDEX sqlite_autoindex_cad_canais_1 (nome=?) LEFT-JOIN
```

#### 6.3 ms total (4 exec) - telas: escala_geral

```sql
SELECT data, id_pessoa, tipo FROM escalas_trabalho WHERE data BETWEEN ? AND ?
```
```
SEARCH escalas_trabalho USING INDEX sqlite_autoindex_escalas_trabalho_1 (data>? AND data<?)
```

#### 6.2 ms total (8 exec) - telas: extras, relatorio_diario

```sql
SELECT me.*, cp.nome AS nome_pessoa, ce.descricao AS categoria FROM movimentacoes_extras me LEFT JOIN cad_pessoas cp ON cp.id = me.id_pessoa LEFT JOIN cad_categorias_extra ce ON ce.id = me.id_categoria WHERE me.data = ? ORDER BY me.id
```
```
SCAN me
SEARCH cp USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
SEARCH ce USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
```

#### 6.1 ms total (4 exec) - telas: relatorio_diario

```sql
SELECT canal, SUM(CASE WHEN NOT EXISTS( SELECT 1 FROM vendas_pagamentos vp2 WHERE vp2.id_pedido = p.id AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado') ) THEN 1 ELSE 0 END) AS qtd, COALESCE(SUM( CASE WHEN EXISTS( SELECT 1 FROM vendas_pagamentos vp WHERE vp.id_pedido = p.id AND (vp.cortesia = 1 OR vp.metodo = 'Fiado') ) THEN 0.0 ELSE p.valor_total END ), 0) AS valor_liquido FROM vendas_pedidos p WHERE p.data = ? GROUP BY canal HAVING SUM(CASE WHEN NOT EXISTS( SELECT 1 FROM vendas_pagamentos vp2 WHERE vp2.id_pedido = p.id AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado') ) THEN 1 ELSE 0 END) > 0 ORDER BY canal
```
```
SCAN p
USE TEMP B-TREE FOR GROUP BY
CORRELATED SCALAR SUBQUERY 1
SCAN vp2
CORRELATED SCALAR SUBQUERY 2
SCAN vp
CORRELATED SCALAR SUBQUERY 3
SCAN vp2
```

#### 5.6 ms total (60 exec) - telas: entregadores, relatorio_diario

```sql
SELECT COALESCE(SUM(me.valor), 0) AS total FROM movimentacoes_extras me JOIN cad_categorias_extra ce ON ce.id = me.id_categoria WHERE me.data = ? AND me.id_pessoa = ? AND ce.descricao = 'Corrida Extra'
```
```
SEARCH ce USING COVERING INDEX sqlite_autoindex_cad_categorias_extra_1 (descricao=?)
SCAN me
```

#### 5.6 ms total (4 exec) - telas: estoque

```sql
SELECT * FROM estoque_categorias ORDER BY nome
```
```
SCAN estoque_categorias USING INDEX sqlite_autoindex_estoque_categorias_1
```

#### 5.1 ms total (4 exec) - telas: parametros

```sql
SELECT * FROM cad_pessoas WHERE 1=1 ORDER BY nome
```
```
SCAN cad_pessoas
USE TEMP B-TREE FOR ORDER BY
```

#### 5.0 ms total (4 exec) - telas: fornecedores

```sql
SELECT * FROM cad_fornecedores WHERE ativo = 1 ORDER BY nome ASC
```
```
SCAN cad_fornecedores
USE TEMP B-TREE FOR ORDER BY
```

#### 4.4 ms total (4 exec) - telas: estoque

```sql
SELECT ep.*, ec.nome AS nome_categoria FROM estoque_produtos ep LEFT JOIN estoque_categorias ec ON ec.id = ep.id_categoria WHERE ep.ativo = 1 AND ep.quantidade_atual <= ep.quantidade_minima ORDER BY ep.nome
```
```
SCAN ep
SEARCH ec USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```

#### 4.3 ms total (4 exec) - telas: relatorio_diario

```sql
SELECT COALESCE(SUM(vp.valor), 0) FROM vendas_pagamentos vp JOIN vendas_pedidos p ON p.id = vp.id_pedido WHERE p.data = ? AND vp.metodo = 'Dinheiro' AND vp.cortesia = 0
```
```
SCAN vp
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
```

#### 4.1 ms total (4 exec) - telas: funcionarios

```sql
SELECT * FROM cad_pessoas WHERE id = ?
```
```
SEARCH cad_pessoas USING INTEGER PRIMARY KEY (rowid=?)
```

#### 4.1 ms total (20 exec) - telas: entregadores

```sql
SELECT COUNT(*) AS qtd, COALESCE(SUM(repasse_entregador), 0) AS soma_taxas FROM vendas_pedidos WHERE data BETWEEN ? AND ? AND id_operador = ? AND repasse_entregador > 0
```
```
SCAN vendas_pedidos
```

#### 4.0 ms total (20 exec) - telas: entregadores

```sql
SELECT p.data, COUNT(*) AS entregas, COALESCE(SUM(p.repasse_entregador), 0) AS soma_repasses, COALESCE(SUM(p.taxa_entrega), 0) AS soma_taxas_clientes FROM vendas_pedidos p LEFT JOIN cad_canais c ON c.nome = p.canal WHERE p.data BETWEEN ? AND ? AND p.id_operador = ? AND p.repasse_entregador > 0 AND COALESCE(c.entregador_plataforma, 0) = 0 GROUP BY p.data ORDER BY p.data
```
```
SCAN p
SEARCH c USING INDEX sqlite_autoindex_cad_canais_1 (nome=?) LEFT-JOIN
USE TEMP B-TREE FOR GROUP BY
```