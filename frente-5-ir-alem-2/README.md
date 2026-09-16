# Frente 5 — Ir Além 2: RPA, IA e dados híbridos

**Disciplina de referência:** AIRPA, Fase 5, Cap. 2 "Do Banco de Dados à Automação Inteligente"  
**Apoio:** Governança (Cap. 7) para rastreabilidade e PCV (Cap. 10) para o vocabulário de entidades  
**Tipo:** expansão (fora da nota base de 10 pontos da Parte 1 e 2)

## O que o robô faz

Um robô em Python roda em ciclos. A cada ciclo ele lê no SQLite as leituras de pressão e frequência cardíaca que
ainda não foram analisadas, calcula a adesão ao tratamento, procura anomalias com Isolation Forest, aplica regras
clínicas, interpreta as mensagens que os pacientes enviaram e grava os alertas. Cada ciclo é uma execução com
`execucao_id` próprio, registrada no MongoDB com parâmetros, versões, métricas e um evento por ação.

```text
simulador (dispositivo da Fase 3)
      |
      v
SQLite: pacientes, leituras_sinais, adesao_tratamento
      |
      v
robot.py (ciclo periódico) --- vocabulário @sinal_alerta/@sintoma/@medicamento da skill Watson (Frente 1)
      |
      +--> Isolation Forest (scikit-learn) + regras clínicas + interpretação de texto
      |
      +--> SQLite: analises_leitura e alertas (uma transação por ciclo)
      |
      v
MongoDB: execucoes, eventos, mensagens_pacientes  -->  resumo_execucoes.py (Map/Reduce, rastro, gráficos)
```

Tudo é simulação acadêmica: pacientes fictícios, dados gerados e alertas que não substituem avaliação médica.

## Decisões (todas do material)

| Parte | Escolha | Onde está no material |
|---|---|---|
| Banco relacional | SQLite com `sqlite3`, DDL/DML parametrizada, WAL e `synchronous=NORMAL` | Cap. 2, seções 2 a 6 |
| Banco não relacional | MongoDB 6 em Docker, `pymongo` e Map/Reduce | Cap. 2, seções 7.7 a 7.11 |
| IA nos sinais vitais | Isolation Forest com engenharia de atributos e contaminação calibrada | Cap. 2, seção 5 |
| IA no texto | Entidades com sinônimos, as mesmas da skill Watson da Frente 1 | PCV, Cap. 10 |
| Rastreabilidade | `execucao_id`, versões, parâmetros e hash dos dados de treino | Governança, Cap. 7 |
| Gráficos | Seaborn: dispersão típica × atípica e barras de alertas | Cap. 2, seção 5; Cap. 7 |

Por que cada escolha, o que foi descartado (PostgreSQL, Redis) e os números da calibração estão no
[relatório técnico](../docs/relatorio_ir_alem2_rpa.md).

## Estrutura

```text
frente-5-ir-alem-2/
|-- robot.py                 # CLI: laço periódico do robô
|-- preparar_ambiente.py     # CLI: cria os bancos com dados simulados (--reset recria)
|-- resumo_execucoes.py      # CLI: execuções, Map/Reduce, rastro de alerta e gráficos
|-- ciclo_robo.py            # um ciclo: lê, analisa, grava alertas e registra eventos
|-- ia_anomalia.py           # atributos + Isolation Forest
|-- regras_clinicas.py       # limiares de pressão, FC e adesão (iguais aos da Frente 1)
|-- interpretacao_texto.py   # vocabulário da skill Watson, negação simples
|-- banco_relacional.py      # SQLite: conexão, DDL, consultas e transação do ciclo
|-- banco_nosql.py           # MongoDB: execuções, eventos, mensagens e Map/Reduce
|-- simulador.py             # pacientes fictícios, 30 dias de leituras, mensagens
|-- graficos.py              # gráficos Seaborn
|-- config.py                # leitura do .env
|-- schema_relacional.sql    # estrutura do banco relacional (entregável)
|-- estrutura_nosql.json     # coleções, índices e documentos de exemplo (entregável)
|-- docker-compose.yml       # MongoDB 6
|-- requirements.txt
|-- pytest.ini
|-- .env.example
`-- tests/                   # 110 testes (107 sem Docker + 3 de integração com o MongoDB)
```

## Como rodar

Requisitos: Python 3.12 e Docker Desktop (ou outro Docker com Compose).

```bash
cd frente-5-ir-alem-2
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # opcional: os valores padrão já batem com o docker-compose
docker compose up -d                 # MongoDB em 127.0.0.1:27017
```

1. Criar os bancos com dados simulados (8 pacientes, 480 leituras, 240 registros diários de adesão e 7 mensagens):

   ```bash
   python preparar_ambiente.py            # use --reset para apagar e recriar
   ```

2. Rodar o robô. O primeiro ciclo varre o histórico; os seguintes pegam só o que chegou:

   ```bash
   python robot.py --ciclos 3 --intervalo 10 --simular-chegada 4
   python robot.py --ciclos 0 --intervalo 60      # contínuo, Ctrl+C para parar
   ```

3. Conferir o resultado:

   ```bash
   python resumo_execucoes.py                     # execuções, alertas por tipo (Map/Reduce) e por paciente
   python resumo_execucoes.py --alerta 6          # rastro: alerta -> leitura -> análise -> execução -> eventos
   python resumo_execucoes.py --graficos saida    # PNG em saida/
   ```

4. Parar o MongoDB quando terminar: `docker compose down` (os dados ficam no volume `dados_mongo`).

Saída do primeiro ciclo, sempre igual com a semente padrão:

```text
Ciclo 1 | 2026-09-15 22:51:31 UTC
  Execução 6f247cd9-2eb0-4c6b-8dfa-9bb52131f9af
  Leituras analisadas: 480 | modelo treinado: sim | atípicas pela IA: 12
  Mensagens: 6 interpretada(s), 1 rejeitada(s)
  Alertas gerados: 13 (baixa_adesao=1, bradicardia=1, crise_hipertensiva=1, padrao_atipico=2, pressao_baixa=1, ...)
  [CRITICA] PAC-004 crise_hipertensiva (regra+ia): PA 188/112 mmHg na faixa de crise hipertensiva (a partir de 180/120). ...
  [CRITICA] PAC-004 sinal_alerta_relatado (texto): Mensagem do paciente cita sinal de alerta: dor no peito. ...
  [ALTA] PAC-008 bradicardia (regra): FC de 44 bpm abaixo de 50 bpm em repouso.
  [ALTA] PAC-005 pressao_baixa (regra+ia): PA 84/54 mmHg abaixo de 90/60. ...
  [ALTA] PAC-003 taquicardia (regra+ia): FC de 138 bpm acima de 100 bpm em repouso.
  8 alerta(s) moderado(s). Detalhes: python resumo_execucoes.py
```

## Testes

```bash
pytest -q
```

Os testes unitários usam SQLite temporário e `mongomock`, sem Docker. Os três testes de `test_integracao_mongodb.py`
rodam contra o MongoDB do `docker-compose` (Map/Reduce no servidor, fuso UTC e ciclo completo) e são pulados se o
banco não estiver no ar.

## Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---|---|
| `SQLITE_PATH` | `dados/cardioia_rpa.db` | arquivo do banco relacional (fica fora do Git) |
| `MONGO_URI` | `mongodb://admin:admin@localhost:27017/?authSource=admin` | conexão do robô |
| `MONGO_DB` | `cardioia_rpa` | banco do robô no MongoDB |
| `MONGO_USUARIO` / `MONGO_SENHA` | `admin` / `admin` | usuário criado pelo `docker-compose.yml` |
| `SKILL_WATSON_PATH` | `../frente-1-watson/cardioia-skill.json` | vocabulário de entidades |

A senha padrão é a do exemplo do material e só vale para o container local, publicado em `127.0.0.1`. O `.env` está
no `.gitignore`.

## Contrato com as outras frentes

- **Frente 1:** o robô lê `@sinal_alerta`, `@sintoma` e `@medicamento` direto de `cardioia-skill.json` e registra o
  hash do arquivo em cada execução. As faixas de pressão e frequência são as mesmas das respostas do assistente.
- **Frentes 2 e 3:** `mensagens_pacientes` aceita os campos `session_id` e `intent` que o `POST /api/chat` devolve.
  Nesta entrega as mensagens vêm do simulador.
- **Fase 3:** os sinais simulados seguem o cenário de monitoramento em casa, não a CNN da Fase 4.

## Entregáveis

- [x] Código funcional da automação: `robot.py` e módulos
- [x] Estrutura do banco relacional: [`schema_relacional.sql`](schema_relacional.sql)
- [x] Estrutura do banco não relacional: [`estrutura_nosql.json`](estrutura_nosql.json) e [`docker-compose.yml`](docker-compose.yml)
- [x] Relatório técnico: [`docs/relatorio_ir_alem2_rpa.md`](../docs/relatorio_ir_alem2_rpa.md)
- [x] Evidências: [`assets/evidencias/`](../assets/evidencias/README.md) (gráficos 11 e 12)

## Limitações

- Dados simulados e limiares gerais para adultos, sem ajuste individual por prescrição.
- O Isolation Forest não usa rótulos: a calibração foi feita na base simulada e precisaria de validação com equipe
  clínica em dados reais.
- A interpretação de texto não tem fuzzy match nem entende negação complexa.
- SQLite aceita um escritor por vez; vários robôs em máquinas diferentes pediriam PostgreSQL.
- O robô foi pensado para uma instância por banco: ao iniciar, ele marca como `interrompida` qualquer execução que
  tenha ficado aberta, inclusive a de outra instância que esteja rodando naquele momento.
