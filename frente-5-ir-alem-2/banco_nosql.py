"""Camada não relacional do robô (MongoDB via ``pymongo``), no padrão do Cap. 2 de AIRPA.

Coleções do banco ``cardioia_rpa``:

- ``execucoes``: um documento por ciclo do robô, com status, parâmetros,
  versões do ambiente e métricas. O ``_id`` é o ``execucao_id`` que também
  aparece nas tabelas ``analises_leitura`` e ``alertas`` do SQLite.
- ``eventos``: log de cada ação do robô. O campo ``detalhes`` muda conforme o
  tipo de evento, e é justamente essa flexibilidade que motiva o NoSQL aqui.
- ``mensagens_pacientes``: mensagens textuais e o resultado da interpretação.

As operações seguem o CRUD do material (``insert_one``, ``find``,
``update_one``) e o resumo usa Map/Reduce, como na seção 7.11.
"""

from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import OperationFailure, PyMongoError

COLECOES = ("execucoes", "eventos", "mensagens_pacientes")

MAP_ALERTAS = """
function () {
  emit(this.detalhes.tipo_alerta, 1);
}
"""

REDUCE_ALERTAS = """
function (chave, valores) {
  var total = 0;
  for (var i = 0; i < valores.length; i++) {
    total += valores[i];
  }
  return total;
}
"""


class MongoIndisponivel(RuntimeError):
    """O MongoDB não respondeu. Sem log não há rastreabilidade, então o robô não roda."""


class RegistroNoSQL:
    def __init__(self, db):
        self.db = db

    @classmethod
    def conectar(cls, uri: str, nome_db: str, timeout_ms: int = 3000) -> RegistroNoSQL:
        cliente = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms, tz_aware=True)
        try:
            cliente.admin.command("ping")
        except PyMongoError as exc:
            cliente.close()
            raise MongoIndisponivel(
                "MongoDB indisponível. Suba o banco com `docker compose up -d` na pasta "
                f"frente-5-ir-alem-2 e confira MONGO_URI no .env. Detalhe: {exc.__class__.__name__}"
            ) from exc
        registro = cls(cliente[nome_db])
        registro.criar_indices()
        return registro

    def criar_indices(self) -> None:
        self.db.execucoes.create_index([("inicio", DESCENDING)])
        self.db.execucoes.create_index([("status", ASCENDING)])
        self.db.eventos.create_index([("execucao_id", ASCENDING), ("registrado_em", ASCENDING)])
        self.db.eventos.create_index([("tipo", ASCENDING)])
        self.db.mensagens_pacientes.create_index([("status", ASCENDING), ("recebida_em", ASCENDING)])

    # Execuções -----------------------------------------------------------------------------------

    def iniciar_execucao(self, execucao_id: str, inicio: datetime, **campos) -> None:
        self.db.execucoes.insert_one({"_id": execucao_id, "status": "em_execucao", "inicio": inicio, **campos})

    def concluir_execucao(self, execucao_id: str, fim: datetime, duracao_s: float, **campos) -> None:
        self.db.execucoes.update_one(
            {"_id": execucao_id},
            {"$set": {"status": "concluida", "fim": fim, "duracao_s": duracao_s, **campos}},
        )

    def falhar_execucao(self, execucao_id: str, erro: Exception, fim: datetime, duracao_s: float) -> None:
        detalhe = {"tipo": erro.__class__.__name__, "mensagem": str(erro)}
        self.db.execucoes.update_one(
            {"_id": execucao_id},
            {"$set": {"status": "erro", "fim": fim, "duracao_s": duracao_s, "erro": detalhe}},
        )
        self.registrar_evento(execucao_id, "erro", detalhe, fim)

    def marcar_execucoes_interrompidas(self, quando: datetime) -> int:
        """Ciclos que ficaram em aberto (robô derrubado no meio) viram ``interrompida``."""
        resultado = self.db.execucoes.update_many(
            {"status": "em_execucao"},
            {"$set": {"status": "interrompida", "fim": quando}},
        )
        return resultado.modified_count

    def buscar_execucao(self, execucao_id: str) -> dict | None:
        return self.db.execucoes.find_one({"_id": execucao_id})

    def ultimas_execucoes(self, limite: int) -> list[dict]:
        return list(self.db.execucoes.find().sort("inicio", DESCENDING).limit(limite))

    # Eventos -------------------------------------------------------------------------------------

    def registrar_evento(self, execucao_id: str, tipo: str, detalhes: dict, quando: datetime) -> None:
        self.db.eventos.insert_one(
            {"execucao_id": execucao_id, "tipo": tipo, "registrado_em": quando, "detalhes": detalhes}
        )

    def registrar_eventos(self, execucao_id: str, tipo: str, lista_detalhes: list[dict], quando: datetime) -> None:
        if not lista_detalhes:
            return
        self.db.eventos.insert_many([
            {"execucao_id": execucao_id, "tipo": tipo, "registrado_em": quando, "detalhes": detalhes}
            for detalhes in lista_detalhes
        ])

    def eventos_da_execucao(self, execucao_id: str) -> list[dict]:
        cursor = self.db.eventos.find({"execucao_id": execucao_id}, {"_id": 0})
        return list(cursor.sort([("registrado_em", ASCENDING), ("_id", ASCENDING)]))

    # Mensagens -----------------------------------------------------------------------------------

    def inserir_mensagens(self, mensagens: list[dict]) -> list[str]:
        documentos = [{"status": "pendente", **mensagem} for mensagem in mensagens]
        resultado = self.db.mensagens_pacientes.insert_many(documentos)
        return [str(_id) for _id in resultado.inserted_ids]

    def buscar_mensagens_pendentes(self, limite: int) -> list[dict]:
        cursor = self.db.mensagens_pacientes.find({"status": "pendente"})
        return list(cursor.sort("recebida_em", ASCENDING).limit(limite))

    @staticmethod
    def _chave(mensagem_id: str):
        """O robô guarda o ``_id`` como texto. Turnos do chat podem ter id próprio, não ObjectId."""
        return ObjectId(mensagem_id) if ObjectId.is_valid(mensagem_id) else mensagem_id

    def buscar_mensagem(self, mensagem_id: str) -> dict | None:
        return self.db.mensagens_pacientes.find_one({"_id": self._chave(mensagem_id)})

    def concluir_mensagem(self, mensagem_id: str, status: str, execucao_id: str, quando: datetime,
                          **campos) -> None:
        self.db.mensagens_pacientes.update_one(
            {"_id": self._chave(mensagem_id)},
            {"$set": {"status": status, "execucao_id": execucao_id, "processada_em": quando, **campos}},
        )

    # Resumo --------------------------------------------------------------------------------------

    def resumo_alertas_por_tipo(self, usar_map_reduce: bool = True) -> dict[str, int]:
        """Total de alertas por tipo a partir do log de eventos.

        Usa Map/Reduce como no material. O comando é considerado legado desde o
        MongoDB 5.0 e não roda em servidores com JavaScript desligado; nesses
        casos o servidor responde com erro e o resumo usa o pipeline de agregação
        equivalente.
        """
        if usar_map_reduce:
            try:
                resposta = self.db.command(
                    "mapReduce", "eventos",
                    map=MAP_ALERTAS, reduce=REDUCE_ALERTAS,
                    query={"tipo": "alerta_gerado"}, out={"inline": 1},
                )
                return {item["_id"]: int(item["value"]) for item in resposta["results"]}
            except OperationFailure:
                pass
        grupos = self.db.eventos.aggregate([
            {"$match": {"tipo": "alerta_gerado"}},
            {"$group": {"_id": "$detalhes.tipo_alerta", "total": {"$sum": 1}}},
        ])
        return {grupo["_id"]: grupo["total"] for grupo in grupos}

    def apagar_tudo(self) -> None:
        for nome in COLECOES:
            self.db.drop_collection(nome)
