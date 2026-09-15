# Frente 4 - Ir Além 1: IA generativa e extração clínica

Esta frente demonstra como transformar um texto clínico fictício e não estruturado em um JSON padronizado usando IA generativa. O modelo recebe instruções explícitas para não completar, inferir ou inventar informações ausentes.

> Projeto exclusivamente acadêmico. A saída não constitui diagnóstico, orientação médica ou atendimento de emergência.

## O que foi implementado

- leitura de texto digitado ou de arquivo `.txt`;
- extração com a API Gemini;
- resposta estruturada por schema Pydantic;
- campos ausentes representados por listas vazias ou `null`;
- separação de informações afirmadas e negadas;
- validações automáticas antes de salvar o JSON;
- exemplos clínicos totalmente fictícios.

## Estrutura

```text
frente-4-ir-alem-1/
|-- .env.example
|-- extracao_clinica.py
|-- test_extracao.py
|-- requirements.txt
|-- README.md
`-- exemplos/
    |-- caso_01.txt
    |-- caso_02.txt
    `-- caso_03.txt
```

O relatório da frente está em `docs/relatorio_ir_alem1_ia_generativa.pdf`.

## Instalação

Use Python 3.10 ou superior. No terminal, a partir desta pasta:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Copie `.env.example` para `.env` e preencha a chave criada no Google AI Studio:

```env
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-3.6-flash
```

Nunca envie o arquivo `.env` para o GitHub.

## Execução

Com um arquivo de exemplo:

```bash
python extracao_clinica.py --arquivo exemplos/caso_01.txt
```

Digitando o texto no terminal:

```bash
python extracao_clinica.py --texto "Paciente relata tontura e usa losartana."
```

Salvando a resposta:

```bash
python extracao_clinica.py --arquivo exemplos/caso_02.txt --saida resultado.json
```

O programa exibe o JSON validado e informa o arquivo criado quando `--saida` for usado.

## Testes

Os testes validam o schema localmente e não chamam a API (não precisam de chave):

```bash
pytest -q
```

## Campos do JSON

| Campo | Conteúdo |
|---|---|
| `sintomas` | sintomas afirmados no texto |
| `fatores_risco` | fatores de risco expressamente mencionados |
| `medicamentos` | medicamentos citados |
| `sinais_vitais` | pressão arterial, frequência cardíaca e saturação |
| `alertas` | sinais de alerta expressamente afirmados |
| `informacoes_negadas` | condições que o texto declara ausentes |
| `fonte` | origem acadêmica do conteúdo |
| `observacao` | aviso sobre a limitação da extração |

## Estratégia contra alucinações

O prompt exige fidelidade literal ao texto, proíbe diagnóstico e inferências e define como representar dados ausentes. Além disso, a resposta da API é solicitada em JSON conforme um schema tipado. O Pydantic valida o resultado antes da exibição ou gravação.

Mesmo com essas barreiras, uma IA generativa pode errar. Por isso, a saída deve sempre ser revisada por uma pessoa e não pode ser usada para decisões clínicas reais.

