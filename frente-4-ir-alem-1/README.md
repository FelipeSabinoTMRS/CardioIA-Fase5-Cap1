# Frente 4 — Ir Além 1: IA generativa e extração clínica

**Disciplina de referência:** IA Generativa e prompting  
**Tipo:** expansão (fora da nota base de 10 pontos da Parte 1 e 2)

## Objetivo

Expandir o assistente para interpretar conteúdo clínico não estruturado com modelos de linguagem, no padrão das aulas, e devolver a informação em formato estruturado (JSON).

## O que fazer

1. Usar técnicas de prompting e IA generativa apresentadas em aula.
2. Receber um texto clínico simulado (prontuário curto, mensagem do paciente ou laudo fictício). Opcionalmente, uma imagem simulada se o material da disciplina cobrir isso.
3. Extrair campos relevantes: sintomas, fatores de risco, medicamentos, sinais vitais mencionados e sinais de alerta.
4. Validar a saída em JSON. O modelo não inventa dado que não está no texto.
5. Explicar o fluxo em PDF.

## Exemplo de saída

```json
{
  "sintomas": ["falta de ar", "cansaço"],
  "fatores_risco": ["hipertensao", "tabagismo"],
  "medicamentos": ["losartana"],
  "sinais_vitais": {
    "pressao_arterial": "150/90",
    "frequencia_cardiaca": null
  },
  "alertas": ["mencao a dor no peito"],
  "fonte": "texto_simulado",
  "observacao": "Extracao academica. Nao substitui avaliacao medica."
}
```

## Organização sugerida

```text
frente-4-ir-alem-1/
|-- README.md
|-- extracao_clinica.ipynb
`-- exemplos/
    `-- laudo_simulado.txt
```

O PDF final vai para `docs/relatorio_ir_alem1_ia_generativa.pdf`.

## Contrato com as outras frentes

- Pode reutilizar as entities da Frente 1 como nomes de campos do JSON.
- Integração no Flask (Frente 2) é desejável, não obrigatória para este Ir Além.
- A Frente 5 pode persistir o JSON extraído no banco não relacional como metadado do processo.

## Entregáveis

- Notebook ou código Python com a implementação.
- Documento em PDF explicando o fluxo usado no projeto.

## Critérios do enunciado

- Uso correto das técnicas vistas em aula.
- Estruturação adequada da saída.
- Clareza na explicação do processo.

## Fora desta frente

Skill do Watson, tela de chat e o robô RPA da Frente 5.
