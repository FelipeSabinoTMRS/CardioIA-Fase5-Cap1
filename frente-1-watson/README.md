# Frente 1 — Watson Assistant (fluxo conversacional)

**Disciplina de referência:** PCV — Chatbots e Virtual Agents (Fase 5, Cap. 10, seção 1.6)  
**Peso na nota base:** 3 pontos (implementação do fluxo conversacional) + parte da documentação

## Objetivo

Modelar o Assistente Cardiológico Inteligente no IBM Watson Assistant (experiência clássica, Dialog skill), com
atendimento inicial em saúde por linguagem natural.

O assistente ajuda o paciente a entender informações de saúde. Ele não fecha diagnóstico, não substitui médico e
não inventa conduta clínica. Dor no peito, falta de ar intensa, desmaio e sinais de AVC levam sempre à orientação
de ligar 192.

## Estrutura

```text
frente-1-watson/
|-- cardioia-skill.json        # skill para importar no Watson (formato de exportação da Dialog skill)
`-- scripts/
    |-- gerar_skill.py         # modelagem da skill em Python -> gera o JSON
    |-- validar_skill.py       # checagem offline da árvore (IDs, jumps, intents, entities, variáveis)
    `-- testar_fluxo.py        # conversas-roteiro contra a skill publicada, via cliente da Frente 2
```

O relatório do fluxo está em [`docs/relatorio_fluxo_conversacional.md`](../docs/relatorio_fluxo_conversacional.md).

## O que a skill tem

Só recursos apresentados no material: intents, entities (sinônimos, pattern regex e de sistema), nós e nós filhos,
operadores de entidade, jump to, variáveis de contexto (inclusive `.literal`), variações de resposta e `anything_else`.

| Intent | Exemplo | O que o diálogo faz |
|---|---|---|
| `#saudacao` | Oi, boa tarde | Apresenta o assistente e o menu |
| `#sintomas` | Estou com tontura | Triagem: sintoma → desde quando → intensidade → resumo |
| `#sinais_vitais` | Minha pressão deu 15 por 9 | Classifica pressão, frequência cardíaca ou saturação |
| `#medicamentos` | Esqueci de tomar a losartana | Orientação geral, sem dose; cita o remédio reconhecido |
| `#exames` | O que é um ecocardiograma? | Explica o exame citado; não interpreta laudo |
| `#agendamento` | Quero marcar com o cardiologista | Agendamento simulado: especialidade → data → turno → resumo |
| `#prevencao` | Como cuidar do coração? | Dicas gerais de hábitos |
| `#emergencia` | Estou com dor forte no peito | Orienta 192 (prioridade sobre todos os nós) |
| `#ajuda` | O que você faz? | Menu com exemplos |
| `#cancelar` | Deixa pra lá | Sai de qualquer fluxo em andamento |
| `#despedida` | Obrigado, era só isso | Encerra com lembrete de segurança |
| `#fora_de_escopo` | Qual o placar do jogo? | Explica o escopo |

Entities: `@sinal_alerta`, `@sintoma`, `@sinal_vital`, `@medicamento`, `@exame`, `@periodo`, `@intensidade`,
`@especialidade`, `@turno`, `@pressao_medida` (regex `15 por 9`), `@sys-number`, `@sys-date`.

## Como importar no Watson

A skill já está publicada na `cardioia-skill` da instância `cardioia-assistant` (a mesma do backend). Para montar em
outra conta, por exemplo para estudar ou tirar prints:

1. IBM Cloud → instância do watsonx Assistant (plano Lite) → Launch watsonx Assistant → experiência clássica.
2. Skills → Create skill → Dialog skill → aba **Upload skill** → selecionar `cardioia-skill.json`.
3. Assistants → Create assistant → Add dialog skill. Para trocar a skill de um assistant existente:
   bloco Dialog → ⋮ → **Swap skill** (o Assistant ID não muda, então o `.env` do backend continua valendo).
4. Aguardar o treinamento terminar e testar no **Try it**.
5. Se ajustar algo pela interface, exporte de novo (Skills → ⋮ → Download) e substitua o JSON desta pasta.

## Como regenerar e testar

```bash
cd frente-1-watson
python scripts/gerar_skill.py      # recria cardioia-skill.json
python scripts/validar_skill.py    # checagem offline, sem credencial
```

Com a skill publicada e o `.env` da Frente 2 preenchido:

```bash
python scripts/testar_fluxo.py     # 10 roteiros (28 turnos): emergência, triagem, sinais vitais, agendamento...
```

## Contrato com as outras frentes

- **Frente 2** consome o assistente pelo mesmo `WA_ASSISTANT_ID`. As respostas usam só `response_type: text`.
- **Frente 3** mostra o texto devolvido. O tom das mensagens se resolve aqui.
- **Frente 4** pode reaproveitar `@sintoma`, `@medicamento` e `@sinal_alerta` como vocabulário da extração.
- **Frente 5** pode gravar a intent de cada turno; `$alerta_emergencia` marca turnos que pediram 192.

## Entregáveis

- [x] Modelagem da skill (`scripts/gerar_skill.py`) e JSON importável (`cardioia-skill.json`)
- [x] Relatório curto do fluxo em `docs/relatorio_fluxo_conversacional.md`
- [x] Publicado na `cardioia-skill` oficial e testado (14/09/2026): 10 roteiros, 28 turnos, todos corretos
- [ ] Prints do builder (intents, entities e um caminho de diálogo) em `assets/evidencias/`
