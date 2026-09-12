# Frente 5 — Ir Além 2: RPA, IA e dados híbridos

**Disciplina de referência:** AIRPA  
**Tipo:** expansão (fora da nota base de 10 pontos da Parte 1 e 2)

## Objetivo

Simular um robô que monitora dados clínicos estruturados, interpreta texto e registra alertas de forma rastreável, usando banco relacional e não relacional juntos.

## O que fazer

1. Criar dados clínicos simulados (pressão arterial, frequência cardíaca e adesão ao tratamento) em banco relacional (SQLite ou PostgreSQL).
2. Ler esses dados periodicamente com um fluxo automatizado em Python (RPA / job).
3. Usar banco não relacional (MongoDB ou equivalente aceito na disciplina) para logs de execução, mensagens textuais e metadados.
4. Aplicar técnica simples de IA vista em aula para achar padrão, anomalia ou situação que peça atenção.
5. Registrar alertas com data, regra disparada, dado de origem e identificador da execução.

## Fluxo sugerido

```text
banco relacional (sinais e adesao)
        |
        v
   job periodico (RPA)
        |
        +--> regra / modelo simples de anomalia
        |
        +--> alerta (se houver)
        |
        v
banco nao relacional (logs, mensagens, metadados)
```

## Organização sugerida

```text
frente-5-ir-alem-2/
|-- README.md
|-- requirements.txt
|-- robot.py
|-- schema_relacional.sql
|-- seed_dados.sql
`-- ia_anomalia.py
```

O relatório técnico vai para `docs/relatorio_ir_alem2_rpa.md`.

## Contrato com as outras frentes

- Os sinais simulados conversam com o cenário da Fase 3 (monitoramento), não com a CNN da Fase 4.
- A intent ou o texto do paciente (Frentes 1 e 3) pode ser gravado no banco não relacional como mensagem.
- O JSON da Frente 4 pode ser um metadado do processo. Isso é encaixe, não dependência.

## Entregáveis

- Código funcional da automação (Python).
- Estrutura dos bancos relacional e não relacional.
- Relatório técnico com o fluxo, as decisões de projeto e a integração entre RPA, IA e dados.

## Critérios do enunciado

- Implementação correta do fluxo de automação.
- Uso adequado dos dois tipos de banco.
- Aplicação coerente das técnicas de IA estudadas.
- Clareza do código e do relatório.

## Fora desta frente

Builder do Watson, Flask do chat e notebook de extração da Frente 4.
