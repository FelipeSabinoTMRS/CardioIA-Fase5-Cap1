"""Resumo das execuções do robô e rastro completo de um alerta.

Uso:
    python resumo_execucoes.py                     # execuções, alertas por tipo e por paciente
    python resumo_execucoes.py --alerta 12         # do alerta até a execução, parâmetros e eventos
    python resumo_execucoes.py --graficos saida    # gráficos Seaborn em PNG
"""

from __future__ import annotations

import argparse
from pathlib import Path

import banco_relacional as br
import graficos
from banco_nosql import MongoIndisponivel, RegistroNoSQL
from config import Config, configurar_saida_utf8

CAMPOS_LONGOS = {"features"}
EVENTOS_GERAIS = {"leituras_lidas", "modelo_treinado", "modelo_nao_treinado", "erro"}


def main(argv: list[str] | None = None) -> int:
    configurar_saida_utf8()
    parser = argparse.ArgumentParser(description="Resumo das execuções e rastreabilidade dos alertas.")
    parser.add_argument("--ultimas", type=int, default=5, help="execuções recentes a listar (padrão: 5)")
    parser.add_argument("--alerta", type=int, help="id do alerta no SQLite para mostrar o rastro completo")
    parser.add_argument("--graficos", metavar="PASTA", help="salva os gráficos em PNG nesta pasta")
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

    con = br.conectar(cfg.sqlite_path)
    try:
        if args.alerta is not None:
            return _rastrear(con, registro, args.alerta)
        _execucoes(registro, args.ultimas)
        _alertas(con, registro)
        if args.graficos:
            for caminho in graficos.gerar(con, Path(args.graficos)):
                print(f"Gráfico salvo em {caminho}")
        return 0
    finally:
        con.close()


def _execucoes(registro: RegistroNoSQL, limite: int) -> None:
    print("Execuções recentes (MongoDB, coleção execucoes)")
    for execucao in registro.ultimas_execucoes(limite):
        metricas = execucao.get("metricas") or {}
        print(f"  {execucao['inicio']:%Y-%m-%d %H:%M:%S}  {execucao['status']:<12} "
              f"{execucao.get('duracao_s') or 0:>6.2f} s  {metricas.get('leituras_analisadas', 0):>4} leituras  "
              f"{metricas.get('alertas_gerados', 0):>3} alertas  {execucao['_id']}")


def _alertas(con, registro: RegistroNoSQL) -> None:
    print("\nAlertas por tipo (Map/Reduce no MongoDB sobre a coleção eventos)")
    totais = registro.resumo_alertas_por_tipo()
    for tipo, total in sorted(totais.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {tipo:<24}{total:>5}")
    if not totais:
        print("  nenhum alerta registrado")

    print("\nAlertas abertos por paciente (SQLite, tabela alertas)")
    abertos = br.resumo_alertas_abertos(con)
    print(abertos.to_string(index=False) if not abertos.empty else "  nenhum alerta aberto")


def _resumir(detalhes: dict) -> str:
    texto = ", ".join(f"{chave}={valor}" for chave, valor in detalhes.items() if chave not in CAMPOS_LONGOS)
    return texto if len(texto) <= 180 else texto[:177] + "..."


def _rastrear(con, registro: RegistroNoSQL, alerta_id: int) -> int:
    rastro = br.rastrear_alerta(con, alerta_id)
    if rastro is None:
        print(f"Alerta {alerta_id} não encontrado no SQLite.")
        return 1

    alerta, paciente = rastro["alerta"], rastro["paciente"]
    print(f"Rastro do alerta {alerta_id}")
    print("\n[SQLite] alertas")
    print(f"  {alerta['tipo']} | severidade {alerta['severidade']} | origem {alerta['origem_deteccao']} | "
          f"status {alerta['status']} | criado em {alerta['criado_em']}")
    print(f"  {alerta['descricao']}")
    print("\n[SQLite] pacientes")
    print(f"  {paciente['codigo']} ({paciente['condicao_base']}, uso contínuo de {paciente['medicamento_continuo']})")

    if rastro["leitura"]:
        leitura = rastro["leitura"]
        print("\n[SQLite] leituras_sinais")
        print(f"  leitura {leitura['id']} medida em {leitura['medido_em']}: PA {leitura['pressao_sistolica']}/"
              f"{leitura['pressao_diastolica']} mmHg, FC {leitura['frequencia_cardiaca']} bpm "
              f"(origem {leitura['origem']})")
    if rastro["analise"]:
        analise = rastro["analise"]
        print("\n[SQLite] analises_leitura")
        print(f"  score {analise['score_anomalia']} | anomalia_ia {analise['anomalia_ia']} | "
              f"adesão 7 dias {analise['adesao_7d']}")
    if alerta["mensagem_id"]:
        mensagem = registro.buscar_mensagem(alerta["mensagem_id"])
        if mensagem:
            print("\n[MongoDB] mensagens_pacientes")
            print(f"  \"{mensagem['texto']}\"")
            print(f"  interpretação: {mensagem.get('interpretacao')}")

    execucao = registro.buscar_execucao(alerta["execucao_id"])
    print("\n[MongoDB] execucoes")
    if execucao is None:
        print(f"  execução {alerta['execucao_id']} não encontrada (o MongoDB foi limpo?)")
        return 0
    parametros = execucao.get("parametros") or {}
    print(f"  {execucao['_id']} | status {execucao['status']} | início {execucao['inicio']:%Y-%m-%d %H:%M:%S} | "
          f"robô {execucao.get('versao_robo')} | regras {parametros.get('versao_regras')}")
    modelo = execucao.get("modelo") or {}
    if modelo.get("hash_dataset"):
        print(f"  modelo {modelo.get('algoritmo')} | contaminação {modelo.get('contaminacao')} | "
              f"{modelo.get('n_amostras')} amostras | hash dos dados {modelo['hash_dataset'][:16]}")

    print("\n[MongoDB] eventos da execução ligados a este alerta")
    for evento in registro.eventos_da_execucao(execucao["_id"]):
        if _evento_do_alerta(evento, alerta):
            print(f"  {evento['registrado_em']:%H:%M:%S} {evento['tipo']}: {_resumir(evento['detalhes'])}")
    return 0


def _evento_do_alerta(evento: dict, alerta: dict) -> bool:
    """Eventos gerais do ciclo, o evento do próprio alerta e, se houver, o da mensagem de origem."""
    if evento["tipo"] in EVENTOS_GERAIS:
        return True
    detalhes = evento["detalhes"]
    if evento["tipo"] == "alerta_gerado":
        return detalhes.get("alerta_id") == alerta["id"]
    return bool(alerta["mensagem_id"]) and detalhes.get("mensagem_id") == alerta["mensagem_id"]


if __name__ == "__main__":
    raise SystemExit(main())
