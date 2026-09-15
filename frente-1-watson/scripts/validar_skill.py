"""Confere a consistência do JSON da skill antes de importar no Watson (sem rede).

Verifica: IDs de nós únicos, pais e irmãos existentes, alvos de jump válidos,
intents e entities citadas nas condições existentes, mínimo de exemplos por
intent, exemplos repetidos entre intents e variáveis de contexto usadas nas
respostas que nunca são definidas.

Uso:
    python scripts/validar_skill.py [caminho/do/json]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PADRAO = Path(__file__).resolve().parents[1] / "cardioia-skill.json"
MIN_EXEMPLOS = 10
VARIAVEIS_DO_SISTEMA = {"metadata", "timezone", "error"}


def validar(skill: dict) -> list[str]:
    erros: list[str] = []
    intents = {i["intent"] for i in skill["intents"]}
    entities = {e["entity"] for e in skill["entities"]}
    nodes = skill["dialog_nodes"]
    ids = [n["dialog_node"] for n in nodes]
    por_id = {n["dialog_node"]: n for n in nodes}

    if len(ids) != len(set(ids)):
        erros.append("IDs de nós duplicados: " + ", ".join(sorted({i for i in ids if ids.count(i) > 1})))

    vistos: dict[str, str] = {}
    for intent in skill["intents"]:
        if len(intent["examples"]) < MIN_EXEMPLOS:
            erros.append(f"#{intent['intent']} tem só {len(intent['examples'])} exemplos (mínimo {MIN_EXEMPLOS})")
        for ex in intent["examples"]:
            chave = ex["text"].strip().lower()
            if chave in vistos and vistos[chave] != intent["intent"]:
                erros.append(f"exemplo \"{ex['text']}\" repetido em #{vistos[chave]} e #{intent['intent']}")
            vistos[chave] = intent["intent"]

    definidas = set(VARIAVEIS_DO_SISTEMA)
    for n in nodes:
        definidas.update((n.get("context") or {}).keys())

    irmaos_por_pai: dict[str | None, list[str]] = {}
    for n in nodes:
        nid = n["dialog_node"]
        pai = n.get("parent")
        if pai and pai not in por_id:
            erros.append(f"{nid}: pai inexistente {pai}")
        irmao = n.get("previous_sibling")
        if irmao and (irmao not in por_id or por_id[irmao].get("parent") != pai):
            erros.append(f"{nid}: previous_sibling {irmao} inválido")
        irmaos_por_pai.setdefault(pai, []).append(nid)

        passo = n.get("next_step") or {}
        if passo.get("behavior") == "jump_to" and passo.get("dialog_node") not in por_id:
            erros.append(f"{nid}: jump para nó inexistente {passo.get('dialog_node')}")

        condicao = n.get("conditions", "")
        for intent in re.findall(r"#([\w-]+)", condicao):
            if intent not in intents:
                erros.append(f"{nid}: intent #{intent} não existe")
        for entity in re.findall(r"@([\w-]+)", condicao):
            if entity not in entities:
                erros.append(f"{nid}: entity @{entity} não existe")

        respostas = json.dumps(n.get("output", {}), ensure_ascii=False)
        for var in re.findall(r"\$([A-Za-z_]\w*)", respostas + condicao):
            if var not in definidas:
                erros.append(f"{nid}: variável ${var} usada mas nunca definida")

    for pai, filhos in irmaos_por_pai.items():
        primeiros = [f for f in filhos if not por_id[f].get("previous_sibling")]
        if len(primeiros) != 1:
            erros.append(f"pai {pai or 'raiz'}: {len(primeiros)} nós sem previous_sibling (esperado 1)")

    raiz = irmaos_por_pai.get(None, [])
    if raiz and por_id[raiz[-1]].get("conditions") != "anything_else":
        erros.append("o último nó da raiz deveria ser anything_else")
    return erros


def main() -> int:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else PADRAO
    skill = json.loads(caminho.read_text(encoding="utf-8"))
    erros = validar(skill)
    exemplos = sum(len(i["examples"]) for i in skill["intents"])
    print(f"{caminho.name}: {len(skill['intents'])} intents ({exemplos} exemplos), "
          f"{len(skill['entities'])} entities, {len(skill['dialog_nodes'])} dialog nodes")
    for erro in erros:
        print(f"  ERRO: {erro}")
    print("OK" if not erros else f"{len(erros)} problema(s)")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
