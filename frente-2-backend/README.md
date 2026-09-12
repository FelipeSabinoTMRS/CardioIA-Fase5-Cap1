# Frente 2 — Backend Flask + API do Watson

**Disciplina de referência:** PCV e integração de APIs  
**Peso na nota base:** 2 pontos (integração backend e assistente) + parte da organização do código

## Objetivo

Subir uma API simples em Flask que recebe a mensagem do usuário, envia ao Watson Assistant e devolve a resposta para a interface.

## O que fazer

1. Criar a aplicação Flask com um endpoint de conversa (exemplo: `POST /api/chat`).
2. Integrar a API do IBM Watson Assistant com a skill exportada pela Frente 1.
3. Manter sessão/contexto do diálogo entre as mensagens do mesmo usuário.
4. Expor um `GET /api/health` para a Frente 3 e o vídeo validarem que o backend está no ar.
5. Usar apenas `.env` para apikey, URL e skill ID. Nada de credencial no Git.
6. Documentar no README desta pasta como instalar e subir o servidor.

## Contrato da API (sugestão)

```text
POST /api/chat
{
  "session_id": "opcional-na-primeira-chamada",
  "message": "Estou com falta de ar"
}

200
{
  "session_id": "abc123",
  "intent": "sintomas",
  "reply": "Texto devolvido pelo Watson"
}
```

A Frente 3 depende desse contrato. Se mudar o JSON, avise quem estiver na interface.

## Organização sugerida

```text
frente-2-backend/
|-- README.md
|-- .env.example
|-- requirements.txt
|-- app.py
`-- watson_client.py
```

## Contrato com as outras frentes

- Frente 1 entrega o assistente publicado e o JSON.
- Frente 3 consome `/api/chat` e `/api/health`.
- Frente 4 pode ganhar depois um endpoint opcional de extração (`POST /api/extract`), sem bloquear a nota base.
- Frente 5 não precisa deste Flask para o robô RPA, mas pode reutilizar o mesmo paciente simulado.

## Entregáveis

- Código Python do backend.
- `requirements.txt` e `.env.example`.
- Instruções de execução nesta pasta.

## Fora desta frente

Modelagem de intents no Watson, HTML/React Native e os dois Ir Além.

## Observação de segurança

Credenciais do Watson ficam só no `.env` local. O `.gitignore` da raiz já bloqueia esse arquivo.
