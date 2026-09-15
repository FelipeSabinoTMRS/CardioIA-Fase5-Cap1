# Frente 2 — Backend Flask + API do Watson Assistant

**Disciplina de referência:** PCV (Processamento de Linguagem Natural, Chatbots & Virtual Agents), Cap. 10  
**Peso na nota base:** 2 pontos (integração backend e assistente) + parte da organização do código

## O que este backend faz

Recebe a mensagem do paciente pela interface (Frente 3), envia ao IBM watsonx Assistant (Frente 1) pela API v2
e devolve a resposta interpretada: texto, intenção reconhecida, confiança, entidades e o `session_id` para
manter o contexto da conversa.

```text
interface (Frente 3) --POST /api/chat--> app.py --SDK ibm-watson--> watsonx Assistant (Frente 1)
```

A implementação segue o exemplo Flask + Watson do material (Cap. 10, Código-fonte 10): `IAMAuthenticator`,
`AssistantV2`, `set_service_url`, `create_session` e `message`, com credenciais lidas de variáveis de ambiente
`WA_API_KEY`, `WA_URL` e `WA_ASSISTANT_ID`.

## Estrutura

```text
frente-2-backend/
|-- app.py                 # Flask: GET / (Frente 3), GET /teste, GET /api/health, POST /api/chat
|-- watson_client.py       # cliente do Watson (sessão, mensagem, parse da resposta)
|-- templates/index.html   # página de teste do backend em /teste
|-- scripts/smoke_chat.py  # conversa real pelo terminal com as credenciais do .env
|-- tests/                 # pytest sem rede (SDK e cliente substituídos por dublês)
|-- requirements.txt
|-- pytest.ini
`-- .env.example
```

## Como rodar

Requisitos: Python 3.10 a 3.12 (o SDK `ibm-watson` é testado até o 3.11; validamos com 3.12) e uma instância
do watsonx Assistant no IBM Cloud (ver "Como obter as credenciais").

```bash
cd frente-2-backend
python3.12 -m venv .venv            # ou: uv venv --python 3.12 .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # preencher WA_API_KEY, WA_URL, WA_ASSISTANT_ID (e WA_ENVIRONMENT_ID, se houver)
python app.py                       # http://127.0.0.1:5050  (interface da Frente 3 em /)
```

Testes (não precisam de credenciais nem de internet):

```bash
pytest -q
```

Conversa real pelo terminal, para validar a integração antes de ligar a interface:

```bash
python scripts/smoke_chat.py "Olá" "Estou com dor no peito" "qual o placar do jogo"
```

## Contrato da API

`GET /api/health`

```json
{"status": "ok", "service": "cardioia-backend", "watson_configured": true}
```

`POST /api/chat`

```json
{"message": "Estou com falta de ar", "session_id": null}
```

`session_id` é opcional na primeira chamada. Reenvie o valor devolvido nas chamadas seguintes para manter o
contexto. Se a sessão expirar por inatividade no Watson, o backend cria outra e devolve o novo `session_id`.

Resposta `200`:

```json
{
  "response": "Entendi que você está com falta de ar. Há quanto tempo isso acontece?",
  "reply": "Entendi que você está com falta de ar. Há quanto tempo isso acontece?",
  "session_id": "5f3c...",
  "intent": "sintomas",
  "confidence": 0.93,
  "entities": [{"entity": "sintoma", "value": "falta de ar", "confidence": 1.0}]
}
```

`response` mantém o contrato do material da disciplina; `reply`, `intent` e `session_id` atendem o contrato
combinado com a Frente 3.

Erros: `400` mensagem vazia, `503` credenciais ausentes no `.env`, `502` falha na API do Watson (o campo
`detail` traz a mensagem devolvida pela IBM).

## Variáveis de ambiente

| Variável | Obrigatória | Onde encontrar |
|---|---|---|
| `WA_API_KEY` | sim | IBM Cloud → instância do watsonx Assistant → Service credentials → `apikey` |
| `WA_URL` | sim | idem, campo `url` (ex.: `https://api.us-south.assistant.watson.cloud.ibm.com`) |
| `WA_ASSISTANT_ID` | sim | watsonx Assistant → Assistant settings → "Assistant IDs and API details" → View details |
| `WA_ENVIRONMENT_ID` | não | mesma tela, "Draft environment ID" ou "Live environment ID" |
| `WA_VERSION` | não | data da versão da API v2; padrão `2021-06-14`, como no material |
| `FLASK_PORT` | não | padrão `5050` |

Sobre `WA_ENVIRONMENT_ID`: o SDK `ibm-watson` 11.x passou a exigir o environment ID nas rotas de sessão. Se a
variável estiver preenchida, o backend usa os métodos do SDK. Se estiver vazia, usa a rota antiga
`/v2/assistants/{assistant_id}/sessions`, que é a mesma do código do material (só `assistant_id`).

## Como obter as credenciais (Etapa 0)

1. **Conta IBM Cloud.** Sem cartão: gerar um Feature Code acadêmico no IBM SkillsBuild Software Downloads
   (`ibm.com/academic`, com o e-mail FIAP: Topics → IBM Cloud → Software → IBM Cloud Feature Code → Request) e
   cadastrar em `cloud.ibm.com/registration` com "Register with a Code". Com cartão: conta Pay-As-You-Go comum,
   que continua gratuita nos serviços de plano Lite. Guia em português: `linktr.ee/sb4collegeptbr`.
2. **Instância.** Catálogo → "watsonx Assistant" → região Dallas (us-south) → plano **Lite** → Create.
   O plano Trial de 30 dias citado no material não está mais no catálogo.
3. **Credenciais.** Na página do serviço, "Service credentials" → `apikey` e `url`.
4. **Experiência clássica.** "Launch watsonx Assistant" → menu da conta (canto superior direito) →
   "Switch to classic experience", como no Cap. 10.
5. **Skill e assistant.** Skills → Create skill → Dialog skill → Brazilian Portuguese. Assistants → Create
   assistant → adicionar a skill. Assistant settings → "Assistant IDs and API details" → copiar os IDs.
6. Preencher o `.env` (o arquivo está no `.gitignore`).

## Contrato com as outras frentes

- **Frente 1** entrega a skill publicada no assistant apontado por `WA_ASSISTANT_ID`.
- **Frente 3** é servida em `GET /` (`frente-3-frontend/`). Consome `POST /api/chat` e `GET /api/health`
  na mesma origem, então não precisa de CORS. A página de teste do backend ficou em `/teste`.
- **Frente 5** pode gravar `intent` e `session_id` de cada turno no banco não relacional.

## Limitações conhecidas

- A documentação da IBM lista a API v2 como recurso do plano Plus. Confirmado em 13/09/2026: `create_session` e
  `message` funcionam no Lite; `list_assistants` responde "API is not supported on lite plan".
- Sem CORS por padrão, alinhado ao exemplo do material (front servido pelo próprio Flask).
- Simulação acadêmica: o assistente não substitui avaliação médica.
