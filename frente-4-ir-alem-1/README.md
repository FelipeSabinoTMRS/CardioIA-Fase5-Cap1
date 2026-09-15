# Frente 4 - Ir AlÃ©m 1: IA generativa e extraÃ§Ã£o clÃ­nica

Esta frente demonstra como transformar um texto clÃ­nico fictÃ­cio e nÃ£o estruturado em um JSON padronizado usando IA generativa. O modelo recebe instruÃ§Ãµes explÃ­citas para nÃ£o completar, inferir ou inventar informaÃ§Ãµes ausentes.

> Projeto exclusivamente acadÃªmico. A saÃ­da nÃ£o constitui diagnÃ³stico, orientaÃ§Ã£o mÃ©dica ou atendimento de emergÃªncia.

## O que foi implementado

- leitura de texto digitado ou de arquivo `.txt`;
- extraÃ§Ã£o com a API Gemini;
- resposta estruturada por schema Pydantic;
- campos ausentes representados por listas vazias ou `null`;
- separaÃ§Ã£o de informaÃ§Ãµes afirmadas e negadas;
- validaÃ§Ã£o automÃ¡tica antes de salvar o JSON;
- exemplos clÃ­nicos totalmente fictÃ­cios.

## Estrutura

```text
frente-4-ir-alem-1/
|-- .env.example
|-- extracao_clinica.py
|-- requirements.txt
|-- README.md
`-- exemplos/
    |-- caso_01.txt
    |-- caso_02.txt
    `-- caso_03.txt
```

O relatÃ³rio da frente estÃ¡ em `docs/relatorio_ir_alem1_ia_generativa.pdf`.

## InstalaÃ§Ã£o

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

## ExecuÃ§Ã£o

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

## Campos do JSON

| Campo | ConteÃºdo |
|---|---|
| `sintomas` | sintomas afirmados no texto |
| `fatores_risco` | fatores de risco expressamente mencionados |
| `medicamentos` | medicamentos citados |
| `sinais_vitais` | pressÃ£o arterial, frequÃªncia cardÃ­aca e saturaÃ§Ã£o |
| `alertas` | sinais de alerta expressamente afirmados |
| `informacoes_negadas` | condiÃ§Ãµes que o texto declara ausentes |
| `fonte` | origem acadÃªmica do conteÃºdo |
| `observacao` | aviso sobre a limitaÃ§Ã£o da extraÃ§Ã£o |

## EstratÃ©gia contra alucinaÃ§Ãµes

O prompt exige fidelidade literal ao texto, proÃ­be diagnÃ³stico e inferÃªncias e define como representar dados ausentes. AlÃ©m disso, a resposta da API Ã© solicitada em JSON conforme um schema tipado. O Pydantic valida o resultado antes da exibiÃ§Ã£o ou gravaÃ§Ã£o.

Mesmo com essas barreiras, uma IA generativa pode errar. Por isso, a saÃ­da deve sempre ser revisada por uma pessoa e nÃ£o pode ser usada para decisÃµes clÃ­nicas reais.

