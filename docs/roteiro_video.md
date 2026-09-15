# Roteiro do vídeo — Frente 3

**Duração:** até 3 minutos  
**O que filmar:** a interface em http://127.0.0.1:5050 com o backend e o Watson no ar. Sem mock.

Antes de gravar: `python app.py` em `frente-2-backend/`, `.env` preenchido, selo da tela em "Assistente conectado".

| Tempo | Ação | Fala sugerida | O que precisa aparecer |
|---|---|---|---|
| 0:00–0:20 | Abrir a tela | "Esta é a interface do CardioIA. O aviso de simulação acadêmica fica visível o tempo todo." | Cabeçalho, aviso vermelho, status conectado |
| 0:20–0:40 | Clicar em **Saudação** (ou digitar `Oi`) | "O paciente inicia o atendimento." | Bolha do usuário e resposta de menu do Watson |
| 0:40–1:30 | Digitar `tenho sentido palpitação` → `faz uns dias` → `forte` | "Em seguida vem a triagem: sintoma, período e intensidade. O assistente devolve um resumo organizado." | Três turnos e o resumo da skill |
| 1:30–2:10 | Digitar `estou com dor forte no peito` | "Se aparece sinal de emergência, o fluxo manda ligar 192." | Resposta de urgência / SAMU |
| 2:10–2:40 | Digitar `qual o placar do jogo` | "Fora de escopo cai no fallback, sem inventar resposta clínica." | Resposta de fora de escopo |
| 2:40–3:00 | Mostrar a intent embaixo da última resposta | "Cada turno traz a intent reconhecida pelo Watson. O código está no GitHub." | Meta `intent:` e, se der, a URL do repo |

Se o tempo apertar, corte a fala e mantenha os quatro fluxos: saudação, triagem, emergência e fallback.

## Depois de gravar

1. Publicar (YouTube não listado ou link da FIAP).
2. Colar o link na seção "Links para entrega" do README principal.
3. Salvar 2 ou 3 prints em `assets/evidencias/` (`08-interface-chat.png`, `09-interface-triagem.png`, `10-interface-emergencia.png`).
