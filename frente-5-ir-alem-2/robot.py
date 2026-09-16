"""Robô de monitoramento do CardioIA (Frente 5, Ir Além 2).

Roda ciclos periódicos: a cada intervalo, lê as leituras novas no SQLite,
detecta anomalias, interpreta mensagens, grava alertas e registra tudo no
MongoDB. Um ciclo com erro não derruba o robô: fica registrado e o próximo
ciclo tenta de novo.

Uso:
    python robot.py --ciclos 3 --intervalo 10 --simular-chegada 4
    python robot.py --ciclos 0 --intervalo 60      # contínuo, Ctrl+C para parar
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from itertools import count

import banco_relacional as br
import simulador
from banco_nosql import MongoIndisponivel, RegistroNoSQL
from ciclo_robo import VERSAO_ROBO, ResumoCiclo, executar_ciclo
from config import Config, configurar_saida_utf8, ocultar_senha
from interpretacao_texto import carregar_vocabulario

MAXIMO_ALERTAS_GRAVES_NA_TELA = 10


def main(argv: list[str] | None = None) -> int:
    configurar_saida_utf8()
    parser = argparse.ArgumentParser(description="Robô RPA de monitoramento cardiológico (simulação acadêmica).")
    parser.add_argument("--ciclos", type=int, default=3, help="quantidade de ciclos; 0 roda até Ctrl+C (padrão: 3)")
    parser.add_argument("--intervalo", type=float, default=10, help="segundos entre ciclos (padrão: 10)")
    parser.add_argument("--simular-chegada", type=int, default=0, metavar="N",
                        help="insere N leituras simuladas antes de cada ciclo (padrão: 0)")
    args = parser.parse_args(argv)
    cfg = Config.carregar()

    if not cfg.sqlite_path.exists():
        print(f"Banco relacional não encontrado em {cfg.sqlite_path}. Rode antes: python preparar_ambiente.py")
        return 1
    try:
        registro = RegistroNoSQL.conectar(cfg.mongo_uri, cfg.mongo_db)
    except MongoIndisponivel as exc:
        print(exc)
        return 2
    vocabulario = carregar_vocabulario(cfg.skill_watson)

    print(f"CardioIA | robô de monitoramento {VERSAO_ROBO} | simulação acadêmica, não substitui avaliação médica")
    print(f"  SQLite  {cfg.sqlite_path}")
    print(f"  MongoDB {ocultar_senha(cfg.mongo_uri)} (banco {cfg.mongo_db})")
    print(f"  Vocabulário da skill Watson: {len(vocabulario.termos)} termos (hash {vocabulario.hash_skill})")
    interrompidas = registro.marcar_execucoes_interrompidas(datetime.now(timezone.utc))
    if interrompidas:
        print(f"  {interrompidas} execução(ões) da rodada anterior ficou(aram) aberta(s) e foi(ram) marcada(s) "
              "como interrompida(s).")

    con = br.conectar(cfg.sqlite_path)
    falhas = 0
    try:
        for numero in count(1):
            agora = datetime.now(timezone.utc).replace(microsecond=0)
            print(f"\nCiclo {numero} | {agora:%Y-%m-%d %H:%M:%S} UTC")
            try:
                if args.simular_chegada:
                    novas = simulador.gerar_novas_leituras(agora, args.simular_chegada)
                    br.inserir_leituras(con, simulador.com_ids(novas, br.ids_por_codigo(con)))
                    print(f"  + {len(novas)} leituras novas chegaram do simulador")
                resumo = executar_ciclo(con, registro, vocabulario, agora=agora)
                _imprimir_resumo(con, resumo)
            except Exception as exc:
                falhas += 1
                print(f"  ERRO no ciclo: {exc.__class__.__name__}: {exc}. O robô segue para o próximo ciclo.")
            if args.ciclos and numero >= args.ciclos:
                break
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nRobô interrompido pelo usuário (Ctrl+C).")
    finally:
        con.close()
    return 1 if falhas else 0


def _imprimir_resumo(con, resumo: ResumoCiclo) -> None:
    print(f"  Execução {resumo.execucao_id}")
    if resumo.leituras_analisadas:
        print(f"  Leituras analisadas: {resumo.leituras_analisadas} | modelo treinado: "
              f"{'sim' if resumo.modelo_treinado else 'não (histórico insuficiente)'} | "
              f"atípicas pela IA: {resumo.anomalias_ia}")
    else:
        print("  Leituras: sem leituras novas para analisar")
    print(f"  Mensagens: {resumo.mensagens_processadas} interpretada(s), "
          f"{resumo.mensagens_rejeitadas} rejeitada(s)")
    tipos = ", ".join(f"{tipo}={total}" for tipo, total in sorted(resumo.alertas_por_tipo.items()))
    print(f"  Alertas gerados: {resumo.alertas_gerados}" + (f" ({tipos})" if tipos else ""))

    alertas = br.alertas_da_execucao(con, resumo.execucao_id)
    graves = [a for a in alertas if a["severidade"] in ("critica", "alta")]
    for alerta in graves[:MAXIMO_ALERTAS_GRAVES_NA_TELA]:
        print(f"  [{alerta['severidade'].upper()}] {alerta['paciente_codigo']} {alerta['tipo']} "
              f"({alerta['origem_deteccao']}): {alerta['descricao']}")
    if len(graves) > MAXIMO_ALERTAS_GRAVES_NA_TELA:
        print(f"  ... e mais {len(graves) - MAXIMO_ALERTAS_GRAVES_NA_TELA} alertas graves")
    moderados = len(alertas) - len(graves)
    if moderados:
        print(f"  {moderados} alerta(s) moderado(s). Detalhes: python resumo_execucoes.py")
    print(f"  Duração: {resumo.duracao_s:.2f} s")


if __name__ == "__main__":
    raise SystemExit(main())
