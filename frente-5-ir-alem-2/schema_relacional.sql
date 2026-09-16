-- Estrutura do banco relacional da Frente 5 (SQLite).
-- DDL no padrão do Cap. 2 de AIRPA: CREATE TABLE IF NOT EXISTS, chaves primárias
-- e estrangeiras, CHECK para valores impossíveis e índices alinhados às consultas do robô.
-- Datas em texto ISO 8601 (UTC), como recomenda o material para comparação e índice.
-- Dados 100% simulados: pacientes têm código e nome fictício.

PRAGMA foreign_keys = ON;

-- Pacientes do programa de monitoramento (pseudonimizados).
CREATE TABLE IF NOT EXISTS pacientes (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo               TEXT    NOT NULL UNIQUE,              -- ex.: PAC-001
    nome_ficticio        TEXT    NOT NULL,
    idade                INTEGER NOT NULL CHECK (idade BETWEEN 18 AND 110),
    condicao_base        TEXT,
    medicamento_continuo TEXT,
    criado_em            TEXT    NOT NULL
);

-- Sinais vitais medidos em casa (cenário de monitoramento da Fase 3). Dado bruto: o robô só lê.
CREATE TABLE IF NOT EXISTS leituras_sinais (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id         INTEGER NOT NULL REFERENCES pacientes(id),
    medido_em           TEXT    NOT NULL,
    pressao_sistolica   INTEGER NOT NULL CHECK (pressao_sistolica BETWEEN 50 AND 300),
    pressao_diastolica  INTEGER NOT NULL CHECK (pressao_diastolica BETWEEN 30 AND 200),
    frequencia_cardiaca INTEGER NOT NULL CHECK (frequencia_cardiaca BETWEEN 20 AND 250),
    origem              TEXT    NOT NULL DEFAULT 'simulador',
    CHECK (pressao_sistolica > pressao_diastolica)
);
CREATE INDEX IF NOT EXISTS idx_leituras_medido_em ON leituras_sinais (medido_em);
CREATE INDEX IF NOT EXISTS idx_leituras_paciente_medido_em ON leituras_sinais (paciente_id, medido_em);

-- Adesão ao tratamento: doses prescritas e tomadas por dia.
CREATE TABLE IF NOT EXISTS adesao_tratamento (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id      INTEGER NOT NULL REFERENCES pacientes(id),
    data             TEXT    NOT NULL,                          -- YYYY-MM-DD
    doses_prescritas INTEGER NOT NULL CHECK (doses_prescritas > 0),
    doses_tomadas    INTEGER NOT NULL CHECK (doses_tomadas >= 0),
    UNIQUE (paciente_id, data),
    CHECK (doses_tomadas <= doses_prescritas)
);
CREATE INDEX IF NOT EXISTS idx_adesao_data ON adesao_tratamento (data);

-- Resultado da análise de cada leitura (equivale à tabela de validação do pipeline do material).
-- Uma linha por leitura: é o que marca a leitura como processada, sem alterar o dado bruto.
CREATE TABLE IF NOT EXISTS analises_leitura (
    leitura_id     INTEGER PRIMARY KEY REFERENCES leituras_sinais(id),
    execucao_id    TEXT    NOT NULL,                            -- _id da execução no MongoDB
    analisado_em   TEXT    NOT NULL,
    adesao_7d      REAL CHECK (adesao_7d BETWEEN 0 AND 1),
    score_anomalia REAL,                                        -- decision_function (< 0 = atípico)
    anomalia_ia    INTEGER CHECK (anomalia_ia IN (0, 1))         -- NULL quando o modelo não rodou
);
CREATE INDEX IF NOT EXISTS idx_analises_execucao ON analises_leitura (execucao_id);

-- Alertas para a equipe de cuidado. Cada um aponta para a origem e para a execução do robô.
CREATE TABLE IF NOT EXISTS alertas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id     INTEGER NOT NULL REFERENCES pacientes(id),
    leitura_id      INTEGER REFERENCES leituras_sinais(id),     -- alerta de sinal vital
    mensagem_id     TEXT,                                       -- _id da mensagem no MongoDB
    execucao_id     TEXT    NOT NULL,
    tipo            TEXT    NOT NULL,
    severidade      TEXT    NOT NULL CHECK (severidade IN ('moderada', 'alta', 'critica')),
    origem_deteccao TEXT    NOT NULL CHECK (origem_deteccao IN ('regra', 'ia', 'regra+ia', 'texto')),
    descricao       TEXT    NOT NULL,
    score_anomalia  REAL,
    status          TEXT    NOT NULL DEFAULT 'aberto'
                    CHECK (status IN ('aberto', 'em_analise', 'resolvido', 'descartado')),
    criado_em       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alertas_paciente_tipo_criado ON alertas (paciente_id, tipo, criado_em);
CREATE INDEX IF NOT EXISTS idx_alertas_execucao ON alertas (execucao_id);
-- Idempotência: reprocessar a mesma leitura ou mensagem não duplica alerta.
CREATE UNIQUE INDEX IF NOT EXISTS uq_alertas_leitura_tipo ON alertas (leitura_id, tipo)
    WHERE leitura_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_alertas_mensagem_tipo ON alertas (mensagem_id, tipo)
    WHERE mensagem_id IS NOT NULL;
