# Evidências

Pasta para prints, capturas do Watson Assistant, da interface, do fluxo RPA e do vídeo.

Arquivos desta pasta entram no README principal e nos relatórios de cada frente quando a entrega estiver pronta.

## Frente 1 — Watson Assistant (experiência clássica, 14/09/2026)

| Arquivo | O que mostra |
|---|---|
| `01-intents.png` | As 12 intents da `cardioia-skill`, com descrição e número de exemplos |
| `02-intent-emergencia.png` | Intent `#emergencia` e seus exemplos de treino |
| `03-entities.png` | Entities criadas (`@sinal_alerta`, `@sintoma`, `@pressao_medida`...) |
| `04-dialog.png` | Raiz da árvore de diálogo: Bem-vindo, Emergência, Saudação, Sinais vitais... |
| `04b-dialog-sinais-vitais.png` | Nós filhos de Sinais vitais com operadores de `@sys-number` |
| `05-no-emergencia.png` | Nó Emergência: condição `#emergencia \|\| @sinal_alerta`, contexto e resposta |
| `06-try-it-triagem.png` | Try it: tontura → desde ontem → forte → resumo organizado |
| `07-try-it-emergencia.png` | Try it: palpitação e, no meio da triagem, aperto no peito → orientação 192 |

## Frente 3 — Interface (a anexar depois do vídeo)

| Arquivo | O que mostrar |
|---|---|
| `08-interface-chat.png` | Tela inicial com aviso acadêmico e status conectado |
| `09-interface-triagem.png` | Triagem de palpitação até o resumo |
| `10-interface-emergencia.png` | Resposta de emergência / 192 |
