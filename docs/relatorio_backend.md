# Relatório da Frente 2 — Integração Flask + API do Watson Assistant

**Projeto:** CardioIA Fase 5 — Assistente Cardiológico Inteligente  
**Frente:** 2 (backend)  
**Referência didática:** PCV, Cap. 10 "Arquitetura Cognitiva dos LLMs Modernos", seção sobre Watson Assistant e Flask

## 1. Objetivo

Construir o backend que liga a interface do paciente (Frente 3) ao assistente modelado no IBM watsonx Assistant
(Frente 1). O backend recebe uma mensagem em linguagem natural, envia ao Watson pela API v2, interpreta a resposta
(texto, intenção, entidades) e devolve tudo em JSON para a interface.

## 2. Arquitetura

```text
paciente -> interface HTML (Frente 3)
               |  POST /api/chat {"message", "session_id"}
               v
        app.py (Flask)
               |  WatsonAssistantClient (watson_client.py)
               |  SDK ibm-watson: IAMAuthenticator + AssistantV2
               v
        watsonx Assistant (Frente 1: intents, entities, dialog)
```

Componentes:

- `app.py`: cria a aplicação Flask (`create_app`), com as rotas `GET /` (página de teste), `GET /api/health` e
  `POST /api/chat`. O cliente do Watson é injetável, o que permite testar as rotas sem rede.
- `watson_client.py`: encapsula autenticação IAM, criação e remoção de sessão, envio de mensagem e a extração
  de `output.intents`, `output.entities` e `output.generic`, na mesma forma do Código-fonte 10 do material.
- `templates/index.html`: página HTML/JS mínima baseada no Código-fonte 6 do material, usada para testar o backend
  e mostrar a intenção reconhecida em cada turno.
- `scripts/smoke_chat.py`: conversa pelo terminal com as credenciais reais.

## 3. Fluxo de uma mensagem

1. A interface envia `{"message": "...", "session_id": null}`.
2. Sem `session_id`, o backend chama `create_session` no Watson e guarda o identificador.
3. O backend chama `message` com `{"message_type": "text", "text": ...}`.
4. A resposta é interpretada: o texto dos nós de diálogo (`generic[].text`) é unido em uma frase; a intenção de
   maior confiança e as entidades detectadas são devolvidas junto.
5. A interface recebe `{"response", "reply", "session_id", "intent", "confidence", "entities"}` e reenvia o
   `session_id` no próximo turno, mantendo o contexto no Watson.

Se o Watson responder 404 para a sessão (expirou por inatividade), o backend cria outra sessão, reenvia a mesma
mensagem uma vez e devolve o novo `session_id`. Mensagem vazia responde 400; credenciais ausentes, 503; falha
na API da IBM, 502 com o detalhe devolvido pelo serviço.

## 4. Decisões de projeto

| Decisão | Motivo |
|---|---|
| Manter `response` no JSON e acrescentar `reply`, `intent`, `session_id` | `response` é o contrato do material; os demais campos atendem a Frente 3 e dão rastreabilidade à Frente 5 |
| Reutilizar sessão em vez de criar uma por mensagem | O material cria uma sessão por chamada; o README da frente pede contexto entre turnos |
| Variáveis `WA_API_KEY`, `WA_URL`, `WA_ASSISTANT_ID` | Mesmos nomes do Código-fonte 10 |
| `WA_ENVIRONMENT_ID` opcional com fallback para a rota antiga | O SDK 11.x exige environment ID; a rota `/v2/assistants/{id}/sessions` do material continua disponível quando só há o assistant ID |
| `python-dotenv` para carregar o `.env` | Apenas conveniência de configuração; a leitura continua por `os.getenv`, como no material. Nenhuma credencial vai para o Git |
| Python 3.12 | O SDK é testado até o 3.11; a máquina do grupo tem 3.14 por padrão, e o 3.12 foi o mais novo validado |

## 5. Verificação

Sem credenciais (feito):

- `pytest -q`: 16 testes cobrindo parse da resposta, uso do SDK com e sem environment ID, sessão expirada,
  erros de API e todas as rotas Flask com cliente falso.
- Servidor no ar sem `.env`: `/api/health` responde `watson_configured: false`; `/api/chat` responde 503 com a
  instrução de preencher o `.env`; mensagem vazia responde 400; `/` renderiza a página com o aviso de simulação.

Com credenciais (feito em 13/09/2026, instância `cardioia-assistant`, plano Lite, região us-south, experiência clássica
com a skill `cardioia-skill` contendo a intent `#saudacao` e o nó "Anything else"):

- `python scripts/smoke_chat.py "Olá" "bom dia" "qual o placar do jogo"`: os dois primeiros turnos retornaram a
  intent `saudacao` com confiança 1.0 e a resposta do nó de diálogo; o terceiro caiu no fallback ("Eu não entendi...").
  Os três turnos usaram a mesma sessão, criada e encerrada pelo script.
- Servidor Flask com `.env` real: `/api/health` respondeu `watson_configured: true`; `POST /api/chat` sem
  `session_id` criou a sessão e reconheceu `#saudacao`; a segunda chamada reutilizou o `session_id`; uma chamada com
  `session_id` inválido foi recuperada com nova sessão, sem erro para o cliente.
- A chamada usou a rota antiga (`WA_ENVIRONMENT_ID` vazio), confirmando que `message` funciona no plano Lite.
- Print da página de teste em `assets/evidencias/` (a gerar pelo grupo).

## 6. Situação da plataforma IBM (verificada em 13/09/2026)

- O catálogo do IBM Cloud mantém o plano **Lite** do watsonx Assistant ativo; o plano **Trial** de 30 dias citado
  no material está inativo. A instância do grupo deve ser criada no Lite.
- A experiência clássica (Dialog skill) continua disponível pelo menu "Switch to classic experience".
- A documentação lista a API v2 entre os recursos do plano Plus. Na prática, confirmado em 13/09/2026: `create_session`
  e `message` funcionam no Lite; `list_assistants` (e, segundo a comunidade, `/logs`) respondem
  "API is not supported on lite plan".
- Contas novas do IBM Cloud pedem cartão de crédito, salvo cadastro com Feature Code acadêmico (IBM SkillsBuild).

## 7. Limitações e próximos passos

- Sem CORS por padrão; se a Frente 3 servir a interface de outra origem, habilitar.
- O assistente é uma simulação acadêmica e não substitui avaliação médica.
- Próximos passos: a Frente 1 substitui a skill placeholder pela skill completa (mesmo assistant ID); a Frente 3
  liga a interface final ao `POST /api/chat`; anexar prints em `assets/evidencias/`.
