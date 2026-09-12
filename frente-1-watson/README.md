# Frente 1 — Watson Assistant (fluxo conversacional)

**Disciplina de referência:** PCV — Chatbots e Virtual Agents  
**Peso na nota base:** 3 pontos (implementação do fluxo conversacional) + parte da documentação

## Objetivo

Modelar o Assistente Cardiológico Inteligente no IBM Watson Assistant, com atendimento inicial em saúde por linguagem natural.

O assistente ajuda o paciente a entender informações de saúde. Ele não fecha diagnóstico, não substitui médico e não inventa conduta clínica.

## O que fazer

1. Criar o assistente na plataforma IBM Watson Assistant, no padrão das aulas.
2. Definir intents, entities e dialog nodes de um fluxo de triagem inicial.
3. Escrever respostas contextualizadas e um fallback para quando a intenção não for reconhecida.
4. Tratar urgência: dor no peito, falta de ar intensa ou desmaio devem direcionar para emergência.
5. Exportar a configuração do assistente (JSON) e versionar nesta pasta.
6. Escrever o relatório curto do fluxo (1 a 2 páginas) em `docs/relatorio_fluxo_conversacional.md`.

## Intents sugeridas

| Intent | Exemplo de fala do paciente |
|---|---|
| `saudacao` | Oi, boa tarde |
| `sintomas` | Estou com falta de ar e cansaço |
| `sinais_vitais` | Minha pressão deu 15 por 9 |
| `medicamentos` | Posso tomar o remédio da pressão agora? |
| `exame` | O que significa o laudo do meu exame? |
| `agendamento` | Quero marcar retorno com o cardiologista |
| `emergencia` | Estou com dor forte no peito |
| `despedida` | Obrigado, era só isso |
| `fora_de_escopo` | Qual o placar do jogo? |

Ajuste nomes e exemplos ao material da disciplina. Inclua utterances de treino suficientes para o classificador.

## Entities sugeridas

- sintoma (`dor no peito`, `falta de ar`, `palpitação`, `tontura`, `inchaço`)
- sinal_vital (`pressão`, `frequência cardíaca`, `saturação`)
- medicamento (`losartana`, `atenolol`, `aas` — lista simulada)
- periodo (`hoje`, `ontem`, `de manhã`)

## Contrato com as outras frentes

- A Frente 2 consome este assistente pela API. Entregue skill ID, URL e o JSON exportado.
- A Frente 3 só mostra o que o Watson responder. O tom das mensagens se resolve aqui.
- A Frente 4 pode reutilizar entidades clínicas no JSON extraído por IA generativa.
- A Frente 5 pode registrar no log a intent detectada em cada turno.

## Entregáveis

- Arquivo de exportação do assistente (JSON) nesta pasta.
- Relatório curto do fluxo em `docs/relatorio_fluxo_conversacional.md`.
- Prints do builder (intents, entities e um caminho de diálogo) em `assets/evidencias/`.

## Fora desta frente

Implementação Flask, tela de chat, notebook de IA generativa e robô RPA.
