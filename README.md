# Faculdade de Informática e Administração Paulista

<p align="center">
  <img src="assets/logo-fiap.png" alt="FIAP" width="40%">
</p>

# CardioIA — Fase 5: Assistente Cardiológico Inteligente

**FIAP | Tecnólogo em Inteligência Artificial | Fase 5 | Capítulo 1**

## Grupo 49

| Integrante | GitHub | Frente |
|---|---|---|
| Juan Felipe Voltolini | [@juanvoltolini-rm562890](https://github.com/juanvoltolini-rm562890) | 1. Watson Assistant |
| Marco Aurélio Eberhardt Assumpção | [@marcofiap](https://github.com/marcofiap) | 2. Backend Flask |
| Felipe Sabino da Silva | [@FelipeSabinoTMRS](https://github.com/FelipeSabinoTMRS) | 3. Interface e vídeo |
| Paulo Henrique Senise | [@PauloSenise](https://github.com/PauloSenise) | 4. Ir Além 1 |
| Luiz Henrique Ribeiro de Oliveira | [@Luiz-FIAP](https://github.com/Luiz-FIAP) | 5. Ir Além 2 |

## Descrição

Este repositório implementa a fase **Assistente Cardiológico Inteligente: Experiência do Paciente**, continuidade do projeto CardioIA. Nas etapas anteriores o grupo trabalhou dados, risco cardiológico, monitoramento IoT e visão computacional. Nesta fase o foco passa a ser a **comunicação inteligente** com o paciente, usando processamento de linguagem natural e o IBM Watson Assistant, conforme a disciplina PCV.

O objetivo é um protótipo funcional de chatbot que:

- interage em linguagem natural, simulando um atendimento inicial em saúde;
- integra NLP e automação no padrão das aulas;
- organiza a informação clínica de forma compreensível;
- oferece uma interface simples para a conversa.

O assistente é uma simulação acadêmica. Ele não substitui avaliação médica.

## Relação com as fases anteriores

A Fase 5 continua o **produto** CardioIA, não o código da Fase 4. O repositório anterior permanece como entrega de visão computacional. Aqui o módulo novo é o assistente conversacional. A unificação dos módulos em uma plataforma única fica para a Fase 7.

| Fase | Repositório | O que reaproveitamos |
|---|---|---|
| 2 | [CardioIA-FIAP](https://github.com/marcofiap/CardioIA-FIAP) | cenário de sintomas e risco |
| 3 | [CardioIA-Fase3-Cap1](https://github.com/marcofiap/CardioIA-Fase3-Cap1) | sinais vitais e monitoramento (Ir Além 2) |
| 4 | [CardioIA-Fase4-Cap1](https://github.com/juanvoltolini-rm562890/CardioIA-Fase4-Cap1) | padrão de README, Flask e interface |

Não entram neste repositório: CNN, VGG16, dataset de raio-X nem o Flask de inferência de imagem.

## Arquitetura da solução

```text
paciente -> interface (Frente 3)
                |
                v
         backend Flask (Frente 2)
                |
                v
      IBM Watson Assistant (Frente 1)

expansões:
  texto clinico -> IA generativa -> JSON (Frente 4 / Ir Além 1)
  sinais no SQL -> robô RPA + IA -> logs no NoSQL (Frente 5 / Ir Além 2)
```

## Frentes de trabalho

Cada pessoa escolhe uma frente. O detalhe está no README da pasta.

| Frente | Pasta | Entrega principal | Nota |
|---|---|---|---|
| 1. Watson Assistant | [`frente-1-watson/`](frente-1-watson/README.md) | intents, entities, dialog, JSON e relatório do fluxo | 3 pts (fluxo) |
| 2. Backend Flask | [`frente-2-backend/`](frente-2-backend/README.md) | API Python integrada ao Watson | 2 pts (integração) |
| 3. Interface e vídeo | [`frente-3-frontend/`](frente-3-frontend/README.md) | tela de chat, repo organizado e vídeo até 3 min | 2 pts (interface) |
| 4. Ir Além 1 | [`frente-4-ir-alem-1/`](frente-4-ir-alem-1/README.md) | extração clínica com IA generativa (notebook + PDF) | expansão |
| 5. Ir Além 2 | [`frente-5-ir-alem-2/`](frente-5-ir-alem-2/README.md) | RPA + SQL + NoSQL + alertas | expansão |

Organização e clareza do código (2 pts) e documentação (1 pt) são de todo o grupo. Trabalho em equipe no formato 4 a 5 pessoas vale 1 ponto extra.

As Frentes 1, 2 e 3 fecham a nota base. As Frentes 4 e 5 são os Ir Além e entram na mesma entrega.

## Estrutura de pastas

```text
.
|-- assets/
|   |-- logo-fiap.png
|   `-- evidencias/            # prints e capturas da entrega
|-- docs/                      # relatórios e roteiro do vídeo
|-- frente-1-watson/           # skill Watson (JSON + modelagem)
|-- frente-2-backend/          # Flask + API do Watson
|-- frente-3-frontend/         # interface de chat e vídeo
|-- frente-4-ir-alem-1/        # IA generativa e extração clínica
|-- frente-5-ir-alem-2/        # RPA, IA e dados híbridos
`-- README.md
```

## Como executar a interface

A Frente 3 é HTML/CSS/JS servida pelo Flask da Frente 2, na mesma origem.

```bash
cd frente-2-backend
source .venv/bin/activate
# .env com WA_API_KEY, WA_URL e WA_ASSISTANT_ID (veja frente-2-backend/README.md)
python app.py
```

Abrir http://127.0.0.1:5050. Não abra o `index.html` direto no disco: o chat depende de `/api/chat`.

Roteiro do vídeo: [`docs/roteiro_video.md`](docs/roteiro_video.md).

## Como trabalhar neste repositório

1. Uma branch por frente: `frente-1`, `frente-2`, `frente-3`, `frente-4`, `frente-5`.
2. Pull request para `main`. Não commitar direto na `main` depois do setup inicial.
3. Credenciais só em `.env` (o arquivo está no `.gitignore`).
4. Cada frente atualiza o próprio README quando o código existir.
5. Relatórios vão para `docs/`. Prints vão para `assets/evidencias/`.

## Critérios de avaliação (enunciado)

| Critério | Pontos |
|---|---|
| Implementação do fluxo conversacional | 3 |
| Integração correta entre backend e assistente | 2 |
| Interface funcional de interação | 2 |
| Organização e clareza do código | 2 |
| Documentação da solução | 1 |
| Trabalho em equipe (grupo de 4 a 5) | 1 (extra) |

## Checklist do enunciado

- [x] Assistente modelado no Watson Assistant (intents, entities, dialog nodes)
- [x] Fluxo com respostas contextualizadas e tratamento de exceção
- [x] Backend Flask integrado à API do Watson
- [x] Interface funcional (HTML ou React Native)
- [ ] Repositório GitHub organizado (tornar público na hora da entrega)
- [x] Vídeo de até 3 minutos
- [x] Relatório curto do fluxo conversacional
- [x] Ir Além 1: extração clínica com IA generativa + PDF
- [ ] Ir Além 2: RPA + bancos relacional e não relacional + relatório técnico

## Documentação adicional

- [`docs/README.md`](docs/README.md) — onde cada relatório deve ser gravado
- [`frente-1-watson/README.md`](frente-1-watson/README.md)
- [`frente-2-backend/README.md`](frente-2-backend/README.md)
- [`frente-3-frontend/README.md`](frente-3-frontend/README.md)
- [`frente-4-ir-alem-1/README.md`](frente-4-ir-alem-1/README.md)
- [`frente-5-ir-alem-2/README.md`](frente-5-ir-alem-2/README.md)

## Links para entrega

- GitHub: <https://github.com/FelipeSabinoTMRS/CardioIA-Fase5-Cap1>
- Interface local: <http://127.0.0.1:5050>
- Vídeo (até 3 minutos): [Demonstração da interface no YouTube](https://youtu.be/Y3m6f8fgczU) — roteiro em [`docs/roteiro_video.md`](docs/roteiro_video.md)

## Observação acadêmica

Este projeto é uma simulação acadêmica. O assistente, as extrações por IA e os alertas do robô não substituem avaliação médica, validação clínica, certificação regulatória ou atendimento de emergência real.
