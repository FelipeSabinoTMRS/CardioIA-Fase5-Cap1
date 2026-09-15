# Frente 3 — Interface, repositório e vídeo

**Disciplina de referência:** prototipação visual e boas práticas de projeto  
**Peso na nota base:** 2 pontos (interface funcional) + organização do repositório + vídeo

## Objetivo

Interface simples para o paciente conversar com o Assistente Cardiológico. O chat envia a mensagem ao Flask da Frente 2, que fala com o Watson da Frente 1. Não há mock na entrega.

## Estrutura

```text
frente-3-frontend/
|-- README.md
|-- index.html
|-- styles.css
`-- app.js
```

O Flask (`frente-2-backend/app.py`) serve estes arquivos na mesma origem:

| Rota | Arquivo |
|---|---|
| `GET /` | `index.html` |
| `GET /styles.css` | `styles.css` |
| `GET /app.js` | `app.js` |
| `GET /assets/...` | logo e evidências da raiz do repo |

Não abra o `index.html` direto no navegador (origem `file://`). O `fetch` para `/api/chat` só funciona com o backend no ar.

## Como rodar

1. Preencher `frente-2-backend/.env` com as credenciais do Watson (veja o README da Frente 2).
2. Subir o backend:

```bash
cd frente-2-backend
source .venv/bin/activate          # se o venv ainda não existir, siga o README da Frente 2
python app.py
```

3. Abrir http://127.0.0.1:5050

A página de teste antiga do backend continua em http://127.0.0.1:5050/teste.

## O que a tela faz

- Mostra o aviso de simulação acadêmica o tempo todo.
- Confere `GET /api/health` ao abrir (conectado / sem credencial / backend offline).
- Envia `POST /api/chat` com `{ "message", "session_id" }` e reutiliza o `session_id` para manter o contexto.
- Exibe a resposta do Watson (`response` / `reply`) e, abaixo, a intent e as entidades do turno.
- Botões de atalho para o roteiro do vídeo: saudação, sintoma, emergência e fora de escopo.

A primeira fala do CardioIA na tela é o mesmo texto do nó **Bem-vindo** da skill. As demais respostas vêm só da API.

## Entregáveis

- Interface funcional integrada ao backend: esta pasta + rotas no Flask.
- Repositório organizado: README desta frente e seção de execução no README principal.
- Vídeo de até 3 minutos: roteiro em [`docs/roteiro_video.md`](../docs/roteiro_video.md). O link entra no README principal depois da gravação.

## Fora desta frente

Skill do Watson, cliente da API IBM, notebook de extração e robô RPA.
