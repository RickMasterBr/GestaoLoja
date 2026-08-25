# Diagnóstico de performance — telas fora do PDV

**Data:** 24/08/2026
**Banco usado:** cópia isolada do banco real da loja (1 MB, 5.327 pedidos / 5.604 pagamentos),
via `GESTAOLOJA_TESTE`. O banco da loja **não foi tocado** (apenas copiado para leitura).
**Método:** cada tela aberta 2x na mesma sessão, com instrumentação `_t()` em import,
cada query SQL, construção dos controles Flet e `page.update()`.

> Nenhuma lógica de negócio foi alterada. Nenhuma otimização foi aplicada.

---

## Resumo executivo

As três hipóteses foram testadas. O resultado:

| Hipótese | Veredito |
|---|---|
| 1. Custo de import na 1ª abertura (lazy import) | **Descartada.** Não existe lazy import: `main.py` importa todas as views no topo. Custo por tela: 1–3 ms, e pago no boot, não no clique. |
| 2. Queries pesadas sem índice | **CONFIRMADA — é a causa dominante.** O banco não tem **nenhum índice explícito**. `relatorio_periodo` gasta ~1,3 s de SQL por relatório. |
| 3. Renderização Flet pesada | **CONFIRMADA — é a segunda causa.** `escala_geral` (1.227 controles) e `parametros` (1.151 controles) gastam 100–300 ms só em `page.update()`. |

E um achado não previsto:

> **`views/fluxo_caixa.py` está quebrada**, não lenta. Linhas
> [138](views/fluxo_caixa.py#L138) e [844](views/fluxo_caixa.py#L844) chamam
> `ft.Border.BorderSide`, que não existe no Flet 0.86. Clicar em "Gerar" lança
> `AttributeError` e a tela simplesmente não responde — o que o usuário
> percebe como travamento. Todas as outras views usam o correto `ft.BorderSide`.

---

## 1. Custo de import — hipótese 1 descartada

`main.py` linhas [44–59](main.py#L44-L59) faz `from views import (dashboard, pdv, extras, ...)`
no topo do módulo. **Todas as 14 views são importadas no boot**, antes da primeira tela.
Não há import sob demanda em lugar nenhum.

Custo de import medido, com as dependências já aquecidas:

| Módulo | 1ª vez | 2ª vez |
|---|---|---|
| views.extras | 1,9 ms | 0,006 ms |
| views.fluxo_caixa | 2,5 ms | 0,007 ms |
| views.escala_geral | 173,8 ms | 0,007 ms |
| views.estoque | 1,4 ms | 0,004 ms |
| views.relatorio_diario | 1,0 ms | 0,007 ms |
| views.relatorio_periodo | 1,0 ms | 0,006 ms |
| views.funcionarios | 1,0 ms | 0,005 ms |
| views.entregadores | 0,8 ms | 0,005 ms |
| views.fornecedores | 0,8 ms | 0,004 ms |
| views.parametros | 1,7 ms | 0,007 ms |

E as dependências pesadas, que são o custo real do boot:

| Dependência | 1ª vez |
|---|---|
| flet | 224,7 ms |
| reportlab.platypus | 203,5 ms |
| openpyxl | 289,0 ms |
| database | 17,0 ms |

**Bloco de import inteiro de `main.py`, em processo novo: 813 / 817 / 898 ms** (3 medições).

Os ~174 ms de `views.escala_geral` são o primeiro `ft.dropdown.Option` construído em
nível de módulo, que dispara carregamento preguiçoso interno do Flet — cobrado uma vez,
no boot, por quem vier primeiro.

`reportlab` + `openpyxl` (~490 ms) são carregados porque
`relatorios/pdf_gerador.py` e `relatorios/excel_gerador.py` importam essas bibliotecas
no topo, e 6 views importam esses módulos no topo. Isso pesa **no boot**, não ao trocar de tela.

**Conclusão:** na 2ª abertura o import é literalmente 0,000 ms (medido). Se o usuário
percebe lentidão na 1ª *e* na 2ª abertura da mesma tela, não é import.

---

## 2. Medições por tela

Todos os tempos em ms. `build` = `view(page)` retornar (inclui as queries).
`update` = `page.update()`. `conn` = número de conexões SQLite abertas.

| Tela | Rodada | import | build | update | SQL | queries | conn | controles Flet |
|---|---|---|---|---|---|---|---|---|
| extras | 1 | 2,1 | 179,3 | 11,9 | 18,0 | 6 | 6 | 33 |
| extras | 2 | **0,0** | 27,3 | 12,6 | 12,1 | 6 | 6 | 33 |
| fluxo_caixa | 1 | 476,3 | 43,0 | 18,6 | 0,0 | 0 | 0 | 58 |
| fluxo_caixa | 2 | **0,0** | 3,3 | 11,5 | 0,0 | 0 | 0 | 58 |
| ↳ *ação "Gerar" (Diário)* | 2 | – | 21,5 | incl. | 6,5 | 1 | 1 | 99 |
| ↳ *ação "Gerar" (Período)* | 2 | – | 22,0 | incl. | 4,2 | 1 | 1 | 155 |
| escala_geral | 1 | 5,0 | 114,8 | **299,9** | 8,6 | 2 | 2 | **1.227** |
| escala_geral | 2 | **0,0** | 50,1 | **210,6** | 3,6 | 2 | 2 | **1.227** |
| ↳ *ação trocar p/ seção Ponto* | 2 | – | 62,6 | incl. | 0,0 | 0 | 0 | 1.227 |
| estoque | 1 | 1,6 | 150,2 | 40,3 | 24,9 | 10 | 10 | 177 |
| estoque | 2 | **0,0** | 108,5 | 30,6 | 20,0 | 10 | 10 | 177 |
| relatorio_diario | 1 | 1,2 | 129,9 | 26,2 | 62,9 | 67 | 19 | 257 |
| relatorio_diario | 2 | **0,0** | 83,0 | 21,4 | 39,5 | 67 | 19 | 257 |
| relatorio_periodo | 1 | 1,1 | 1,4 | 4,5 | 0,0 | 0 | 0 | 15 |
| relatorio_periodo | 2 | **0,0** | 0,7 | 3,9 | 0,0 | 0 | 0 | 15 |
| ↳ *ação "Gerar" (mês corrente)* | 1 | – | **3.144,1** | incl. | **2.839,7** | 171 | 89 | 876 |
| ↳ *ação "Gerar" (mês corrente)* | 2 | – | **1.468,9** | incl. | **1.319,8** | 171 | 89 | 876 |
| ↳ *ação "Gerar" (90 dias)* | 2 | – | **1.451,9** | incl. | 1.291,7 | 171 | 89 | 876 |
| ↳ *ação "Gerar" (365 dias)* | 2 | – | **1.498,5** | incl. | 1.336,1 | 171 | 89 | 876 |
| funcionarios | 1 | 0,9 | 6,1 | 7,1 | 2,2 | 1 | 1 | 10 |
| funcionarios | 2 | **0,0** | 3,8 | 5,3 | 1,5 | 1 | 1 | 10 |
| ↳ *ação "Carregar"* | 2 | – | 60,3 | incl. | 7,5 | 15 | 5 | 373 |
| entregadores | 1 | 1,2 | 95,6 | 46,0 | 32,6 | 57 | 7 | 524 |
| entregadores | 2 | **0,0** | 51,7 | 33,4 | 17,7 | 57 | 7 | 524 |
| fornecedores | 1 | 0,9 | 30,3 | 26,3 | 3,2 | 1 | 1 | 216 |
| fornecedores | 2 | **0,0** | 17,3 | 18,7 | 1,7 | 1 | 1 | 216 |
| parametros | 1 | 1,6 | 58,8 | 69,3 | 14,5 | 9 | 9 | 1.151 |
| parametros | 2 | **0,0** | 58,3 | **103,4** | 14,8 | 9 | 9 | **1.151** |

Observações importantes:

- **Rodada 2 não é mais rápida que a rodada 1** em nenhuma tela, fora o import (que zera).
  O custo é recalculado a cada abertura. Não existe "primeira vez cara, depois barato".
- **`relatorio_periodo` custa o mesmo para 1 mês, 90 dias e 365 dias** (~1,45 s).
  Essa é a assinatura de um problema de plano de execução (full scan) e de N+1,
  não de volume de dados no período.
- Abrir conexão está **barato**: 0,45–1,8 ms por conexão no Mirror local. As 89 conexões
  de `relatorio_periodo` somam ~40 ms — não é o gargalo (mas seria no modo Stream antigo).

---

## 3. Queries lentas e EXPLAIN QUERY PLAN

### 3.1 O banco não tem nenhum índice explícito

```
=== INDICES EXISTENTES ===
cad_bairros           sqlite_autoindex_cad_bairros_1          (auto: UNIQUE/PK)
cad_canais            sqlite_autoindex_cad_canais_1           (auto: UNIQUE/PK)
cad_categorias_extra  sqlite_autoindex_cad_categorias_extra_1 (auto: UNIQUE/PK)
cad_configuracoes     sqlite_autoindex_cad_configuracoes_1    (auto: UNIQUE/PK)
cad_dias_fixos        sqlite_autoindex_cad_dias_fixos_1       (auto: UNIQUE/PK)
cad_metodos_pag       sqlite_autoindex_cad_metodos_pag_1      (auto: UNIQUE/PK)
cad_plataformas       sqlite_autoindex_cad_plataformas_1      (auto: UNIQUE/PK)
escalas_trabalho      sqlite_autoindex_escalas_trabalho_1     (auto: UNIQUE/PK)
estoque_categorias    sqlite_autoindex_estoque_categorias_1   (auto: UNIQUE/PK)
fluxo_caixa_diario    sqlite_autoindex_fluxo_caixa_diario_1   (auto: UNIQUE/PK)
registros_ponto       sqlite_autoindex_registros_ponto_1      (auto: UNIQUE/PK)
```

Só existem os índices automáticos de `UNIQUE`/`PK`. As duas maiores tabelas —
**`vendas_pedidos` (5.327 linhas) e `vendas_pagamentos` (5.604 linhas) — não têm
índice nenhum**, nem auto. Assim como `movimentacoes_extras` (570) e `logs_auditoria` (1.403).

### 3.2 As três queries que dominam `relatorio_periodo`

**Query 1 — Resumo por Canal ([relatorio_periodo.py:271](views/relatorio_periodo.py#L271))**

```sql
SELECT canal,
       SUM(CASE WHEN NOT EXISTS(
           SELECT 1 FROM vendas_pagamentos vp2
           WHERE vp2.id_pedido = p.id AND (vp2.cortesia = 1 OR vp2.metodo = 'Fiado')
       ) THEN 1 ELSE 0 END) AS qtd, ...
FROM vendas_pedidos p
WHERE p.data BETWEEN ? AND ?
GROUP BY canal HAVING ... ORDER BY canal
```

```
EXPLAIN QUERY PLAN:
SCAN p                              <-- vendas_pedidos inteira, sem índice em data
USE TEMP B-TREE FOR GROUP BY
CORRELATED SCALAR SUBQUERY 1
SCAN vp2                            <-- 5.604 linhas varridas POR PEDIDO
CORRELATED SCALAR SUBQUERY 2
SCAN vp                             <-- de novo
CORRELATED SCALAR SUBQUERY 3
SCAN vp2                            <-- e de novo
```

Três subqueries correlacionadas, cada uma varrendo `vendas_pagamentos` inteira para
cada linha de `vendas_pedidos`. É O(n×m).

**Query 2 — Resumo por Método de Pagamento**

```
CO-ROUTINE pag_count
SCAN vendas_pagamentos              <-- scan
USE TEMP B-TREE FOR GROUP BY
SCAN vp                             <-- scan
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
CORRELATED SCALAR SUBQUERY 4
SCAN vp2                            <-- scan por linha
...
SCAN vp3                            <-- scan por linha
```

**Query 3 — Resumo Geral ([relatorio_periodo.py:181](views/relatorio_periodo.py#L181))**

```
USE TEMP B-TREE FOR count(DISTINCT)
SCAN p                              <-- sem índice em vendas_pedidos.data
CORRELATED SCALAR SUBQUERY 1
SCAN vp                             <-- 5.604 linhas por pedido
```

### 3.3 Quanto os índices resolveriam (medido, não estimado)

Rodei as mesmas queries em **duas cópias descartáveis** do banco de teste — uma como
está hoje, outra com os índices candidatos criados. Nada foi aplicado ao app nem ao
banco da loja.

| Query | Sem índice | Com índice | Ganho | SCAN depois |
|---|---|---|---|---|
| Resumo por Canal | **667,5 ms** | **2,3 ms** | **294x** | nenhum |
| Resumo por Método de Pagamento | **411,6 ms** | **5,3 ms** | **77x** | só covering index |
| Resumo Geral do Período | **186,3 ms** | **0,8 ms** | **230x** | nenhum |
| Repasse por entregador (`data`+`id_operador`) | 0,2 ms | 0,006 ms | 32x | nenhum |
| Bruto online/máquina por canal | 3,7 ms | 1,8 ms | 2,1x | covering index |
| Total movimentações extras por período | 0,05 ms | 0,02 ms | 2,0x | nenhum |
| **TOTAL (todas as queries do relatório)** | **1.211,5 ms** | **14,2 ms** | **85x** | |

Criar os 6 índices levou **26 ms** e o arquivo do banco praticamente não cresceu.

Índices que produziram esse resultado:

```sql
CREATE INDEX ix_pag_pedido      ON vendas_pagamentos(id_pedido);   -- o mais importante
CREATE INDEX ix_ped_data        ON vendas_pedidos(data);
CREATE INDEX ix_ped_data_oper   ON vendas_pedidos(data, id_operador);
CREATE INDEX ix_mov_data        ON movimentacoes_extras(data);
CREATE INDEX ix_esc_pessoa_data ON escalas_trabalho(id_pessoa, data, tipo);
CREATE INDEX ix_log_data        ON logs_auditoria(data_hora);
```

`vendas_pagamentos(id_pedido)` sozinho responde pela maior parte do ganho: é a coluna
usada em todo `EXISTS(... WHERE vp.id_pedido = p.id)` e em todo `JOIN ... ON p.id = vp.id_pedido`.

---

## 4. Padrão N+1 (não se resolve com índice)

Independente de índice, três telas fazem uma query por item dentro de um laço,
**abrindo uma conexão nova a cada chamada**:

| Tela | Função | Chamadas por abertura | Local |
|---|---|---|---|
| relatorio_periodo | `database.escala_contar_dias()` | **84** (21 internos × 4 tipos) | [relatorio_periodo.py:699-708](views/relatorio_periodo.py#L699-L708) |
| relatorio_diario | `database.calcular_pagamento_entregador()` | **10** | [relatorio_diario.py:447-448](views/relatorio_diario.py#L447-L448) |
| entregadores | `database.calcular_pagamento_entregador()` | **5** (57 queries no total) | [entregadores.py](views/entregadores.py) |

`escala_contar_dias` é rápida por chamada (0,03 ms, já usa o autoindex de
`escalas_trabalho`), mas 84 chamadas × (abrir conexão + PRAGMA + query + fechar)
custam **133 ms** medidos — 10% do tempo do relatório de período.

`estoque` tem o mesmo padrão em menor escala: `estoque_categoria_listar()` e
`estoque_produto_listar()` são chamadas 4x cada na montagem da tela, 10 conexões no total.

---

## 5. Renderização Flet — hipótese 3

Custo de `page.update()` cresce direto com o número de controles na árvore:

| Tela | Controles | `page.update()` | ms por 100 controles |
|---|---|---|---|
| escala_geral | 1.227 | 210–300 ms | ~19 ms |
| parametros | 1.151 | 69–103 ms | ~8 ms |
| entregadores | 524 | 33–46 ms | ~7 ms |
| relatorio_periodo (após Gerar) | 876 | incluso na ação | – |
| fornecedores | 216 | 19–26 ms | ~10 ms |
| estoque | 177 | 31–40 ms | ~19 ms |
| relatorio_diario | 257 | 21–26 ms | ~9 ms |
| extras | 33 | 12 ms | – |

`escala_geral` monta uma grade mensal inteira: ~1.227 controles, sendo a maior parte
`ft.Dropdown` por célula (dias × funcionários). É o maior custo puro de render do app,
e é 100% Flet — as duas queries da tela somam 3,6 ms.

`parametros` monta as **7 abas de uma vez** ([parametros.py:1356-1362](views/parametros.py#L1356-L1362)),
mesmo que o usuário só veja uma.

---

## 6. Diagnóstico final por tela

| Tela | Custo hoje (2ª abertura) | Causa dominante |
|---|---|---|
| **relatorio_periodo** | **~1.470 ms ao clicar Gerar** | **Falta de índice** (1.265 ms em 3 queries com SCAN) + N+1 de 84 chamadas (133 ms) |
| **escala_geral** | ~260 ms | **Render Flet** (1.227 controles). SQL irrelevante (3,6 ms) |
| **parametros** | ~160 ms | **Render Flet** (1.151 controles, 7 abas montadas de uma vez) |
| **relatorio_diario** | ~105 ms | N+1 (`calcular_pagamento_entregador` ×10, 19 conexões) + render (257 controles) |
| **estoque** | ~140 ms | Queries repetidas 4x (10 conexões) + render |
| **entregadores** | ~85 ms | N+1 (57 queries / 7 conexões) + render (524 controles) |
| **extras** | ~40 ms | Aceitável. `pessoa_listar()` chamada 3x |
| **fornecedores** | ~36 ms | Aceitável (render de 216 controles) |
| **funcionarios** | ~65 ms ao Carregar | Aceitável |
| **fluxo_caixa** | **quebrada** | `AttributeError: ft.Border.BorderSide` — ver abaixo |

### O bug de `fluxo_caixa`

```
views/fluxo_caixa.py:138:  horizontal_lines=ft.Border.BorderSide(1, ft.Colors.GREY_600)
views/fluxo_caixa.py:844:  horizontal_lines=ft.Border.BorderSide(1, ft.Colors.GREY_600)
```

No Flet 0.86 `ft.Border` só expõe `all`, `copy`, `only`, `symmetric`. O correto é
`ft.BorderSide`, que é o que **todas as outras 6 views usam**
(`entregadores.py:56`, `extras.py:304`, `funcionarios.py:95`, `pdv.py:345`,
`relatorio_diario.py:52`, `relatorio_periodo.py:77`).

Consequência: clicar em "Gerar" na tela Fluxo Caixa lança exceção dentro do
`on_click`, que não é capturada pelo `try/except` de `carregar_view()` em `main.py`
(esse só protege a montagem da tela). A tela fica sem responder — indistinguível de
lentidão para o usuário. Com um shim aplicado só na medição, a tela é **rápida**
(21 ms, 1 query, 6,5 ms de SQL).

---

## 7. Ordem de ataque sugerida (não implementado)

1. **Corrigir `ft.Border.BorderSide` → `ft.BorderSide`** em `fluxo_caixa.py:138` e `:844`.
   Duas palavras, destrava a tela inteira.
2. **Criar os 6 índices.** ~85x no conjunto das queries de relatório, 26 ms de custo único, sem
   mudança de lógica. Maior ganho por esforço de todo o diagnóstico.
3. **Eliminar os N+1** (`escala_contar_dias` ×84, `calcular_pagamento_entregador` ×10/×5):
   uma query agregada com `GROUP BY id_pessoa` em vez de laço, e uma conexão reaproveitada.
4. **Render Flet**: montar abas sob demanda em `parametros`, e reduzir/virtualizar a grade
   de `escala_geral`.
5. **Boot**: mover `reportlab`/`openpyxl` para import dentro da função de exportação
   (~490 ms do startup). Só afeta o tempo de abrir o app, não a troca de telas.

---

## 8. Como reverter a instrumentação

Tudo o que foi adicionado está em **arquivos novos**. Nenhum arquivo existente do app
foi modificado. Para remover o diagnóstico por completo:

```
del perf_instr.py
del perf_imports.py
del perf_driver.py
del perf_diag.txt
del relatorio_perf.md
del relatorio_perf.json
del DIAGNOSTICO_PERF.md
```

`database.py`, `main.py` e todas as `views/*.py` estão exatamente como estavam —
o `_t()` original continua intacto e não foi alterado.

Dois arquivos de log **cresceram** durante as medições, porque são escritos pelo
próprio código já existente do app (não pela instrumentação nova):

- `perf_log.txt` — o `FileHandler` de `database.py` faz append a cada execução;
- `perf_loja.txt` — o logger raiz configurado em [views/pdv.py:17](views/pdv.py#L17)
  captura o debug do Flet.

Ambos só receberam linhas das rodadas contra o **banco de teste**, nenhum dado da loja.
Podem ser truncados à vontade.

### Ressalva sobre os números

Os tempos da seção 2 incluem a sobrecarga da própria instrumentação (wrapper em cada
função de `database.py` + proxy de cursor), então são **limites superiores**. Os números
da seção 3.3 vêm de execução limpa, sem instrumentação, e são os confiáveis para SQL.
A conclusão relativa (o que é caro em relação ao quê) é a mesma nos dois.
