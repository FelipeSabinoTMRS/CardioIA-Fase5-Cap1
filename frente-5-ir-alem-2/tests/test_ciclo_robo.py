"""Testes do ciclo do robô: SQLite em disco temporário + MongoDB em memória (mongomock)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import mongomock
import pytest

import banco_relacional as br
import simulador
from banco_nosql import RegistroNoSQL
from ciclo_robo import executar_ciclo
from ia_anomalia import DetectorAnomalias, Pontuacao, ResultadoDeteccao
from interpretacao_texto import carregar_vocabulario
from regras_clinicas import LIMIARES

SKILL_WATSON = Path(__file__).resolve().parents[2] / "frente-1-watson" / "cardioia-skill.json"
AGORA = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


class DetectorFixo:
    """Dublê do detector: marca como anômalas só as leituras informadas (isola a lógica do ciclo)."""

    def __init__(self, anomalas=(), treinado=True, erro=None):
        self.anomalas = set(anomalas)
        self.treinado = treinado
        self.erro = erro

    def parametros(self):
        return {"algoritmo": "fixo"}

    def avaliar(self, features, ids_para_pontuar):
        if self.erro:
            raise self.erro
        if not self.treinado:
            return ResultadoDeteccao(treinado=False, metadados={"motivo": "histórico insuficiente"})
        pontuacoes = {
            int(i): Pontuacao(score=-0.2 if i in self.anomalas else 0.1, anomalia=i in self.anomalas)
            for i in ids_para_pontuar
        }
        return ResultadoDeteccao(treinado=True, pontuacoes=pontuacoes, metadados={"hash_dataset": "abc"})


@pytest.fixture(scope="module")
def vocabulario():
    return carregar_vocabulario(SKILL_WATSON)


@pytest.fixture
def amb(tmp_path, vocabulario):
    con = br.conectar(tmp_path / "ciclo.db")
    br.criar_schema(con)
    ids = br.inserir_pacientes(con, [
        {"codigo": codigo, "nome_ficticio": f"Paciente {codigo}", "idade": 60, "condicao_base": "hipertensão",
         "medicamento_continuo": "losartana", "criado_em": br.iso_utc(AGORA)}
        for codigo in ("PAC-001", "PAC-002")
    ])
    registro = RegistroNoSQL(mongomock.MongoClient()["cardioia_rpa_teste"])

    def ciclo(detector=None, agora=AGORA):
        return executar_ciclo(con, registro, vocabulario, detector=detector or DetectorFixo(), agora=agora)

    def leitura(codigo="PAC-001", sistolica=120, diastolica=80, fc=70, horas_antes=1, agora=AGORA):
        br.inserir_leituras(con, [{
            "paciente_id": ids[codigo], "medido_em": br.iso_utc(agora - timedelta(hours=horas_antes)),
            "pressao_sistolica": sistolica, "pressao_diastolica": diastolica,
            "frequencia_cardiaca": fc, "origem": "teste",
        }])
        return con.execute("SELECT MAX(id) FROM leituras_sinais").fetchone()[0]

    def alertas():
        return [dict(r) for r in con.execute("SELECT * FROM alertas ORDER BY id")]

    yield SimpleNamespace(con=con, registro=registro, ids=ids, ciclo=ciclo, leitura=leitura, alertas=alertas)
    con.close()


def test_ciclo_analisa_pendentes_gera_alerta_e_nao_reprocessa(amb):
    amb.leitura(sistolica=120, diastolica=80)
    crise = amb.leitura(sistolica=186, diastolica=110)
    amb.leitura(sistolica=125, diastolica=82)

    resumo = amb.ciclo()

    assert resumo.leituras_analisadas == 3
    assert resumo.alertas_por_tipo == {"crise_hipertensiva": 1}
    (alerta,) = amb.alertas()
    assert alerta["leitura_id"] == crise
    assert alerta["execucao_id"] == resumo.execucao_id
    assert alerta["origem_deteccao"] == "regra"

    segundo = amb.ciclo(agora=AGORA + timedelta(minutes=1))
    assert segundo.leituras_analisadas == 0
    assert segundo.alertas_gerados == 0
    assert len(amb.alertas()) == 1


def test_execucao_registra_parametros_versoes_metricas_e_eventos(amb, vocabulario):
    amb.leitura(sistolica=186, diastolica=110)

    resumo = amb.ciclo()

    execucao = amb.registro.buscar_execucao(resumo.execucao_id)
    assert execucao["status"] == "concluida"
    assert execucao["versao_robo"]
    assert execucao["parametros"]["limiares"] == LIMIARES
    assert execucao["parametros"]["vocabulario"]["hash_skill"] == vocabulario.hash_skill
    assert execucao["ambiente"]["scikit_learn"]
    assert execucao["metricas"]["alertas_gerados"] == 1
    assert execucao["modelo"] == {"hash_dataset": "abc"}
    tipos = [e["tipo"] for e in amb.registro.eventos_da_execucao(resumo.execucao_id)]
    assert tipos == ["leituras_lidas", "modelo_treinado", "alerta_gerado"]


def test_regra_confirmada_pela_ia_vira_um_unico_alerta_regra_mais_ia(amb):
    crise = amb.leitura(sistolica=186, diastolica=110)

    amb.ciclo(detector=DetectorFixo(anomalas=[crise]))

    (alerta,) = amb.alertas()
    assert alerta["tipo"] == "crise_hipertensiva"
    assert alerta["origem_deteccao"] == "regra+ia"
    assert alerta["score_anomalia"] == -0.2


def test_ia_sozinha_gera_alerta_de_padrao_atipico(amb):
    atipica = amb.leitura(sistolica=138, diastolica=88, fc=96)

    resumo = amb.ciclo(detector=DetectorFixo(anomalas=[atipica]))

    (alerta,) = amb.alertas()
    assert alerta["tipo"] == "padrao_atipico"
    assert alerta["origem_deteccao"] == "ia"
    assert alerta["severidade"] == "moderada"
    assert "Padrão atípico" in alerta["descricao"]
    assert resumo.anomalias_ia == 1


def test_sem_historico_suficiente_o_ciclo_segue_so_com_as_regras(amb):
    crise = amb.leitura(sistolica=186, diastolica=110)

    resumo = amb.ciclo(detector=DetectorAnomalias(minimo_amostras=50))

    assert not resumo.modelo_treinado
    assert [a["tipo"] for a in amb.alertas()] == ["crise_hipertensiva"]
    analise = amb.con.execute("SELECT score_anomalia, anomalia_ia FROM analises_leitura WHERE leitura_id = ?",
                              (crise,)).fetchone()
    assert tuple(analise) == (None, None)
    tipos = [e["tipo"] for e in amb.registro.eventos_da_execucao(resumo.execucao_id)]
    assert "modelo_nao_treinado" in tipos


def test_baixa_adesao_gera_um_alerta_por_paciente_e_so_repete_depois_de_24h(amb):
    br.inserir_adesao(amb.con, [
        {"paciente_id": amb.ids["PAC-002"], "data": (AGORA.date() - timedelta(days=k)).isoformat(),
         "doses_prescritas": 2, "doses_tomadas": 1 if k % 2 else 0}
        for k in range(7)
    ])
    amb.leitura("PAC-002", horas_antes=3)
    amb.leitura("PAC-002", horas_antes=2)

    amb.ciclo()
    amb.leitura("PAC-002", horas_antes=0, agora=AGORA + timedelta(hours=1))
    amb.ciclo(agora=AGORA + timedelta(hours=1))

    adesao = [a for a in amb.alertas() if a["tipo"] == "baixa_adesao"]
    assert len(adesao) == 1
    assert "21%" in adesao[0]["descricao"]

    depois = AGORA + timedelta(hours=25)
    amb.leitura("PAC-002", horas_antes=0, agora=depois)
    amb.ciclo(agora=depois)
    assert len([a for a in amb.alertas() if a["tipo"] == "baixa_adesao"]) == 2


def test_pressao_elevada_recorrente_vira_um_alerta_por_paciente_com_a_leitura_mais_recente(amb):
    amb.leitura(sistolica=145, diastolica=92, horas_antes=3)
    amb.leitura(sistolica=150, diastolica=95, horas_antes=2)
    mais_recente = amb.leitura(sistolica=148, diastolica=94, horas_antes=1)

    amb.ciclo()

    (alerta,) = amb.alertas()
    assert alerta["tipo"] == "pressao_elevada"
    assert alerta["leitura_id"] == mais_recente
    assert "3 leituras" in alerta["descricao"]

    depois = AGORA + timedelta(hours=2)
    amb.leitura(sistolica=152, diastolica=96, horas_antes=0, agora=depois)
    amb.ciclo(agora=depois)
    assert len(amb.alertas()) == 1
    assert amb.con.execute("SELECT COUNT(*) FROM analises_leitura").fetchone()[0] == 4


def test_evento_agudo_continua_gerando_um_alerta_por_leitura(amb):
    amb.leitura(sistolica=186, diastolica=110, horas_antes=2)
    amb.leitura(sistolica=190, diastolica=115, horas_antes=1)

    amb.ciclo()

    assert [a["tipo"] for a in amb.alertas()] == ["crise_hipertensiva", "crise_hipertensiva"]


def test_mensagem_com_sinal_de_alerta_gera_alerta_critico_ligado_a_mensagem(amb):
    (mensagem_id,) = amb.registro.inserir_mensagens([
        {"paciente_codigo": "PAC-001", "texto": "Senti um aperto no peito agora há pouco", "recebida_em": AGORA},
    ])

    resumo = amb.ciclo()

    (alerta,) = amb.alertas()
    assert alerta["tipo"] == "sinal_alerta_relatado"
    assert alerta["severidade"] == "critica"
    assert alerta["origem_deteccao"] == "texto"
    assert alerta["mensagem_id"] == mensagem_id
    mensagem = amb.registro.buscar_mensagem(mensagem_id)
    assert mensagem["status"] == "processada"
    assert mensagem["alerta_id"] == alerta["id"]
    assert mensagem["execucao_id"] == resumo.execucao_id
    assert mensagem["interpretacao"]["sinais_alerta"] == ["dor no peito"]


def test_mensagem_sem_termo_clinico_e_processada_sem_alerta(amb):
    (mensagem_id,) = amb.registro.inserir_mensagens([
        {"paciente_codigo": "PAC-002", "texto": "Queria confirmar a consulta", "recebida_em": AGORA},
    ])

    amb.ciclo()

    assert amb.alertas() == []
    mensagem = amb.registro.buscar_mensagem(mensagem_id)
    assert mensagem["status"] == "processada"
    assert mensagem["alerta_id"] is None


def test_mensagem_sem_texto_e_rejeitada_sem_travar_os_proximos_ciclos(amb):
    (mensagem_id,) = amb.registro.inserir_mensagens([{"paciente_codigo": "PAC-001", "recebida_em": AGORA}])

    resumo = amb.ciclo()

    assert resumo.status == "concluida"
    assert resumo.mensagens_rejeitadas == 1
    mensagem = amb.registro.buscar_mensagem(mensagem_id)
    assert mensagem["status"] == "rejeitada"
    assert "sem texto" in mensagem["motivo"]
    assert amb.registro.buscar_mensagens_pendentes(limite=10) == []


def test_mensagem_com_id_proprio_do_chat_e_processada(amb):
    # O contrato com as Frentes 2 e 3 permite gravar turnos do chat com _id próprio.
    amb.registro.db.mensagens_pacientes.insert_one({
        "_id": "turno-chat-1", "status": "pendente", "paciente_codigo": "PAC-001",
        "texto": "Estou com dor no peito", "recebida_em": AGORA, "session_id": "sessao-watson-1",
        "intent": "emergencia",
    })

    amb.ciclo()

    (alerta,) = amb.alertas()
    assert alerta["mensagem_id"] == "turno-chat-1"
    mensagem = amb.registro.buscar_mensagem("turno-chat-1")
    assert mensagem["status"] == "processada"
    assert mensagem["alerta_id"] == alerta["id"]


def test_mensagem_de_paciente_fora_do_cadastro_e_rejeitada(amb):
    (mensagem_id,) = amb.registro.inserir_mensagens([
        {"paciente_codigo": "PAC-999", "texto": "Estou com dor no peito", "recebida_em": AGORA},
    ])

    resumo = amb.ciclo()

    assert amb.alertas() == []
    mensagem = amb.registro.buscar_mensagem(mensagem_id)
    assert mensagem["status"] == "rejeitada"
    assert "cadastro" in mensagem["motivo"]
    assert resumo.mensagens_rejeitadas == 1
    tipos = [e["tipo"] for e in amb.registro.eventos_da_execucao(resumo.execucao_id)]
    assert "mensagem_rejeitada" in tipos


def test_falha_no_meio_do_ciclo_marca_erro_e_nao_grava_analise(amb):
    amb.leitura(sistolica=186, diastolica=110)

    with pytest.raises(RuntimeError, match="modelo quebrou"):
        amb.ciclo(detector=DetectorFixo(erro=RuntimeError("modelo quebrou")))

    (execucao,) = amb.registro.ultimas_execucoes(limite=5)
    assert execucao["status"] == "erro"
    assert execucao["erro"]["mensagem"] == "modelo quebrou"
    assert amb.con.execute("SELECT COUNT(*) FROM analises_leitura").fetchone()[0] == 0


def test_ciclo_sem_dados_novos_conclui_com_metricas_zeradas(amb):
    resumo = amb.ciclo()

    assert resumo.status == "concluida"
    assert (resumo.leituras_analisadas, resumo.mensagens_processadas, resumo.alertas_gerados) == (0, 0, 0)
    assert not resumo.modelo_treinado


def test_alerta_e_rastreavel_ate_a_execucao_e_ao_evento_no_mongodb(amb):
    amb.leitura(sistolica=186, diastolica=110)
    amb.ciclo()
    (alerta,) = amb.alertas()

    rastro = br.rastrear_alerta(amb.con, alerta["id"])
    execucao = amb.registro.buscar_execucao(rastro["alerta"]["execucao_id"])
    eventos = amb.registro.eventos_da_execucao(execucao["_id"])

    evento = next(e for e in eventos if e["tipo"] == "alerta_gerado")
    assert evento["detalhes"]["alerta_id"] == alerta["id"]
    assert evento["detalhes"]["leitura_id"] == rastro["leitura"]["id"]
    assert evento["detalhes"]["paciente_codigo"] == "PAC-001"


def test_simulacao_completa_encontra_os_cenarios_planejados(tmp_path, vocabulario):
    con = br.conectar(tmp_path / "simulacao.db")
    br.criar_schema(con)
    dados = simulador.gerar_historico(AGORA)
    ids = br.inserir_pacientes(con, dados.pacientes)
    br.inserir_leituras(con, simulador.com_ids(dados.leituras, ids))
    br.inserir_adesao(con, simulador.com_ids(dados.adesao, ids))
    registro = RegistroNoSQL(mongomock.MongoClient()["cardioia_rpa_simulacao"])
    registro.inserir_mensagens(simulador.mensagens_iniciais(AGORA))

    resumo = executar_ciclo(con, registro, vocabulario, detector=DetectorAnomalias(), agora=AGORA)

    assert resumo.leituras_analisadas == len(dados.leituras)
    assert resumo.modelo_treinado
    assert {"crise_hipertensiva", "taquicardia", "bradicardia", "pressao_baixa", "baixa_adesao",
            "sinal_alerta_relatado", "sintoma_relatado", "padrao_atipico"} <= set(resumo.alertas_por_tipo)
    # Calibração da contaminação: a IA sozinha só aponta as duas leituras atípicas planejadas do PAC-007.
    atipicos = con.execute(
        """SELECT p.codigo, l.pressao_sistolica FROM alertas a
           JOIN pacientes p ON p.id = a.paciente_id JOIN leituras_sinais l ON l.id = a.leitura_id
           WHERE a.tipo = 'padrao_atipico' ORDER BY l.medido_em"""
    ).fetchall()
    assert [tuple(r) for r in atipicos] == [("PAC-007", 138), ("PAC-007", 136)]
    elevada_por_paciente = con.execute(
        "SELECT MAX(n) FROM (SELECT COUNT(*) AS n FROM alertas WHERE tipo = 'pressao_elevada' GROUP BY paciente_id)"
    ).fetchone()[0]
    assert elevada_por_paciente == 1
    con.close()
