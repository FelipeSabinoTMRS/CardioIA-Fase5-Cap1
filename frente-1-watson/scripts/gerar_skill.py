"""Gera o JSON da Dialog skill do CardioIA (experiência clássica do Watson Assistant).

O arquivo gerado (``frente-1-watson/cardioia-skill.json``) segue o formato de
exportação da skill clássica e pode ser importado em
Skills -> Create skill -> Dialog skill -> Upload skill.

Só usa recursos apresentados no PCV (Fase 5, Cap. 10, seção 1.6): intents,
entities com sinônimos e patterns (regex), entidades de sistema, nós e nós
filhos, operadores de entidade, jump to, variáveis de contexto (inclusive
``.literal``), variações de resposta e o nó ``anything_else``. Exceções pontuais:
``intents[0].confidence`` na saída dos fluxos e ``reformatDateTime`` na data.

Modelar em código deixa a revisão do grupo legível no PR. A fonte de verdade
continua sendo a skill no Watson: depois de importar e ajustar pela interface,
exporte de novo e substitua o JSON.

Uso:
    python scripts/gerar_skill.py
"""

from __future__ import annotations

import json
from pathlib import Path

SAIDA = Path(__file__).resolve().parents[1] / "cardioia-skill.json"

AVISO = "Lembrete: sou uma simulação acadêmica e não substituo avaliação médica."
EMERGENCIA = (
    "ATENÇÃO: dor no peito, falta de ar intensa, desmaio ou sinais como boca torta, "
    "fala enrolada e fraqueza de um lado do corpo podem indicar uma emergência. "
    "Ligue agora para o SAMU (192) ou vá ao pronto-socorro mais próximo. "
    "Não dirija sozinho e, se puder, peça ajuda a alguém por perto. "
    "Este assistente é uma simulação acadêmica e não substitui atendimento médico."
)
MENU = (
    "Posso ajudar a: relatar sintomas, entender valores de pressão, batimentos e saturação, "
    "tirar dúvidas gerais sobre medicamentos, explicar exames do coração, "
    "simular o agendamento de uma consulta e dar dicas de prevenção."
)

# ---------------------------------------------------------------------------
# Intents (#)
# ---------------------------------------------------------------------------

INTENTS: dict[str, tuple[str, list[str]]] = {
    "saudacao": ("Paciente cumprimenta ou inicia a conversa", [
        "Oi", "Olá", "Bom dia", "Boa tarde", "Boa noite", "Oi, tudo bem?",
        "Olá, preciso de ajuda", "E aí", "Oi CardioIA", "Olá, alguém aí?",
        "Bom dia, tudo bem com você?", "Oii",
    ]),
    "sintomas": ("Paciente relata um sintoma que não é sinal de alarme", [
        "Estou sentindo cansaço", "Tenho sentido tontura", "Meu coração está acelerado",
        "Estou com palpitação", "Minhas pernas estão inchadas", "Sinto um pouco de falta de ar quando subo escada",
        "Estou com dor de cabeça", "Ando muito cansado ultimamente", "Sinto o coração batendo forte às vezes",
        "Meus tornozelos incharam", "Estou me sentindo fraco", "Tenho um sintoma para relatar",
        "Não estou me sentindo bem",
    ]),
    "sinais_vitais": ("Paciente informa ou pergunta sobre pressão, batimentos ou saturação", [
        "Minha pressão deu 15 por 9", "Medi a pressão e deu 12 por 8", "Minha pressão está 140 por 90",
        "Meus batimentos estão em 110", "Minha frequência cardíaca está 55", "A saturação deu 93",
        "Pressão 13 por 8 é normal?", "Qual a pressão ideal?", "Quero informar minha pressão",
        "Meu batimento cardíaco está alto?", "Medi o pulso e deu 98", "Minha pressão está alta",
        "Qual frequência cardíaca é normal?",
    ]),
    "medicamentos": ("Dúvidas sobre remédios, dose, esquecimento ou efeitos", [
        "Posso tomar o remédio da pressão agora?", "Esqueci de tomar a losartana", "Qual a dose do atenolol?",
        "Posso parar de tomar o remédio?", "Esse remédio dá tontura?", "Posso tomar AAS com dipirona?",
        "Tomei o remédio duas vezes sem querer", "Quero saber sobre meu medicamento",
        "O remédio do coração pode ser tomado à noite?", "Estou sem o meu remédio",
        "Posso trocar a marca do remédio?", "Tenho dúvida sobre a medicação",
    ]),
    "exames": ("Dúvidas sobre exames cardiológicos e resultados", [
        "O que é um ecocardiograma?", "Para que serve o eletrocardiograma?", "O que significa o laudo do meu exame?",
        "Vou fazer um teste ergométrico, como funciona?", "O que é Holter?", "Preciso de jejum para o exame?",
        "Meu colesterol deu alto no exame", "Como é feito o MAPA?", "Pode me explicar meu exame?",
        "Quais exames avaliam o coração?", "Recebi o resultado do exame", "O médico pediu um cateterismo, o que é isso?",
    ]),
    "agendamento": ("Paciente quer marcar ou remarcar consulta", [
        "Quero marcar retorno com o cardiologista", "Preciso agendar uma consulta", "Quero marcar uma consulta",
        "Tem horário com o médico amanhã?", "Gostaria de remarcar minha consulta", "Como faço para agendar?",
        "Quero uma consulta na próxima semana", "Marcar consulta de cardiologia", "Preciso ver um médico",
        "Pode agendar para mim?", "Quero consulta com nutricionista", "Quero agendar um horário",
    ]),
    "prevencao": ("Dicas de hábitos saudáveis e prevenção cardiovascular", [
        "Como cuidar do coração?", "O que devo comer para baixar a pressão?", "Quais exercícios são bons para o coração?",
        "Como prevenir infarto?", "Posso comer sal?", "Dicas para uma vida saudável",
        "Como diminuir o colesterol?", "Fumar faz mal ao coração?", "Quanto tempo devo caminhar por dia?",
        "Beber álcool afeta a pressão?", "O que é bom para a saúde do coração?", "Como reduzir o risco de doença cardíaca?",
    ]),
    "emergencia": ("Sinais de alarme que exigem atendimento imediato", [
        "Estou com dor forte no peito", "Não consigo respirar", "Meu peito está apertando muito",
        "Acho que estou infartando", "Meu pai desmaiou", "Estou com muita falta de ar",
        "Dor no peito que vai para o braço", "A boca ficou torta e a fala enrolada", "Estou passando muito mal",
        "Socorro", "É uma emergência", "Meu braço esquerdo está dormente e o peito dói",
        "Estou sufocando",
    ]),
    "ajuda": ("Paciente pergunta o que o assistente faz", [
        "O que você faz?", "Me ajuda", "Quais são as opções?", "Como você pode me ajudar?",
        "Menu", "O que posso perguntar?", "Ajuda", "Quem é você?", "Para que serve esse chat?",
        "Não sei o que perguntar",
    ]),
    "cancelar": ("Paciente desiste da ação em andamento", [
        "Cancelar", "Deixa pra lá", "Desisto", "Não quero mais", "Esquece",
        "Parar", "Quero cancelar", "Muda de assunto", "Voltar ao início", "Não precisa mais",
    ]),
    "despedida": ("Paciente agradece ou encerra a conversa", [
        "Obrigado", "Obrigada, era só isso", "Tchau", "Até logo", "Valeu",
        "Muito obrigado pela ajuda", "Era só isso", "Até mais", "Encerrar conversa", "Boa noite, obrigado",
    ]),
    "fora_de_escopo": ("Assuntos sem relação com saúde cardiológica", [
        "Qual o placar do jogo?", "Me conta uma piada", "Qual a previsão do tempo?", "Quanto está o dólar?",
        "Qual a capital da França?", "Me recomenda um filme", "Como faço um bolo de chocolate?",
        "Quem ganhou a eleição?", "Qual o melhor celular?", "Me ajuda com a lição de matemática",
        "Onde fica o shopping mais próximo?",
    ]),
}

# ---------------------------------------------------------------------------
# Entities (@)
# ---------------------------------------------------------------------------

# valor -> sinônimos (fuzzy matching ligado, como no exemplo @cidade)
ENTITIES_SINONIMOS: dict[str, dict[str, list[str]]] = {
    "sinal_alerta": {
        "dor no peito": ["dor forte no peito", "aperto no peito", "peito apertando", "peito doendo", "dor torácica", "dor no coração"],
        "falta de ar intensa": ["não consigo respirar", "muita falta de ar", "falta de ar forte", "sufocando", "sem ar"],
        "desmaio": ["desmaiei", "desmaiou", "perdi a consciência", "apaguei"],
        "sinais de AVC": ["boca torta", "fala enrolada", "braço dormente", "fraqueza de um lado", "rosto paralisado"],
    },
    "sintoma": {
        "falta de ar": ["fôlego curto", "dispneia", "cansaço para respirar"],
        "cansaço": ["cansado", "cansada", "fadiga", "fraqueza", "fraco", "fraca", "exausto"],
        "palpitação": ["palpitações", "coração acelerado", "coração disparado", "batedeira", "taquicardia"],
        "tontura": ["tonto", "tonta", "vertigem", "zonzo", "zonza"],
        "inchaço": ["inchado", "inchada", "pernas inchadas", "tornozelo inchado", "edema"],
        "dor de cabeça": ["cefaleia", "cabeça doendo", "enxaqueca"],
    },
    "sinal_vital": {
        "pressão": ["pressão arterial", "pressão alta", "pressão baixa"],
        "frequência cardíaca": ["batimentos", "batimento", "pulso", "bpm"],
        "saturação": ["oxigenação", "oxigênio", "oxímetro", "saturação de oxigênio"],
    },
    "medicamento": {
        "losartana": ["losartan", "losartana potássica"],
        "atenolol": [],
        "AAS": ["aspirina", "ácido acetilsalicílico"],
        "enalapril": [],
        "hidroclorotiazida": ["diurético"],
        "sinvastatina": ["estatina", "remédio do colesterol"],
    },
    "exame": {
        "eletrocardiograma": ["ECG", "eletro"],
        "ecocardiograma": ["ecocardiografia", "ultrassom do coração"],
        "teste ergométrico": ["teste de esteira", "ergometria"],
        "Holter": ["holter 24 horas"],
        "MAPA": ["monitorização ambulatorial da pressão"],
        "exame de sangue": ["colesterol", "hemograma", "glicemia", "triglicerídeos"],
    },
    "periodo": {
        "hoje": ["agora", "hoje de manhã", "hoje cedo", "há algumas horas", "faz umas horas"],
        "ontem": ["desde ontem", "ontem à noite"],
        "há alguns dias": ["há dias", "faz uns dias", "uns dias", "essa semana", "dois dias", "três dias"],
        "há mais de uma semana": ["uma semana", "semana passada", "duas semanas", "há semanas"],
        "há mais de um mês": ["um mês", "meses", "faz tempo", "há muito tempo"],
    },
    "intensidade": {
        "leve": ["fraquinha", "pouca", "pouco", "suportável"],
        "moderada": ["média", "mais ou menos", "razoável", "moderado"],
        "forte": ["muito forte", "intensa", "insuportável", "demais"],
    },
    "especialidade": {
        "cardiologia": ["cardiologista", "cardio", "médico do coração"],
        "clínico geral": ["clínica geral", "clínico", "médico de família"],
        "nutrição": ["nutricionista", "nutrólogo"],
    },
    "turno": {
        "manhã": ["de manhã", "pela manhã", "cedo"],
        "tarde": ["à tarde", "de tarde", "pela tarde"],
        "noite": ["à noite", "de noite"],
    },
}

# valor -> padrões regex (fuzzy desligado, como no exemplo @cep)
ENTITIES_PADROES: dict[str, dict[str, list[str]]] = {
    "pressao_medida": {"pressao_medida": [r"\b\d{1,3}\s*(por|x|X)\s*\d{1,3}\b"]},
}

SYSTEM_ENTITIES = ["sys-number", "sys-date"]

# ---------------------------------------------------------------------------
# Árvore de diálogo
# ---------------------------------------------------------------------------

NODES: list[dict] = []
PERGUNTA_SEM_CONDICAO = "false"  # nós alcançados só por jump


def texto(*variacoes: str, politica: str = "sequential") -> dict:
    return {
        "generic": [{
            "response_type": "text",
            "values": [{"text": v} for v in variacoes],
            "selection_policy": politica,
        }]
    }


def no(dialog_node: str, titulo: str, condicao: str, resposta: dict | None = None, *,
       parent: str | None = None, contexto: dict | None = None, proximo: dict | None = None) -> str:
    node = {"type": "standard", "dialog_node": dialog_node, "title": titulo, "conditions": condicao,
            "output": resposta or {}}
    if parent:
        node["parent"] = parent
    if contexto:
        node["context"] = contexto
    if proximo:
        node["next_step"] = proximo
    NODES.append(node)
    return dialog_node


def pular(destino: str, selector: str = "body") -> dict:
    """Jump to. ``body`` = responder o nó destino; ``condition`` = avaliar a condição dele."""
    return {"behavior": "jump_to", "dialog_node": destino, "selector": selector}


AVALIAR_FILHOS = {"behavior": "skip_user_input"}

# Enquanto o bot espera uma resposta, estes assuntos saem do fluxo e voltam para a raiz.
# Respostas curtas ("forte", "amanhã") ganham intents fracas por acaso (ex.: #saudacao 0.28),
# por isso a saída exige confiança alta.
OUTRO_ASSUNTO = "(" + " || ".join([
    "#cancelar", "#saudacao", "#sintomas", "#sinais_vitais", "#medicamentos", "#exames",
    "#agendamento", "#prevencao", "#ajuda", "#despedida", "#fora_de_escopo",
]) + ") && intents[0].confidence > 0.6"


def pergunta(dialog_node: str, titulo: str, texto_pergunta: str, captura: str, contexto: dict,
             destino: str, texto_repetir: str) -> None:
    """Nó que faz uma pergunta e trata a resposta nos filhos (padrão "Caso São Paulo").

    Filhos, avaliados de cima para baixo:
      1. urgência       -> nó Emergência
      2. resposta ok    -> salva em variável de contexto e pula para o próximo passo
      3. outro assunto  -> volta para a raiz (evita "toca do coelho")
      4. anything_else  -> explica e repete a pergunta
    """
    no(dialog_node, titulo, PERGUNTA_SEM_CONDICAO, texto(texto_pergunta))
    no(f"{dialog_node}_urgencia", "Urgência", "#emergencia || @sinal_alerta", parent=dialog_node,
       proximo=pular("emergencia"))
    no(f"{dialog_node}_ok", "Resposta reconhecida", captura, parent=dialog_node,
       contexto=contexto, proximo=pular(destino))
    no(f"{dialog_node}_outro_assunto", "Outro assunto", OUTRO_ASSUNTO, parent=dialog_node,
       proximo=pular("emergencia", "condition"))
    no(f"{dialog_node}_repetir", "Resposta não reconhecida", "anything_else", texto(texto_repetir),
       parent=dialog_node, proximo=pular(dialog_node))


# Bem-vindo --------------------------------------------------------------------
no("bem_vindo", "Bem-vindo", "welcome", texto(
    "Olá! Eu sou o CardioIA, assistente virtual de atendimento inicial em saúde do coração. "
    f"{MENU} {AVISO} Em caso de dor no peito ou falta de ar intensa, ligue 192."))

# Emergência: primeiro nó depois do welcome, para ter prioridade -------------
no("emergencia", "Emergência", "#emergencia || @sinal_alerta", texto(EMERGENCIA),
   contexto={"alerta_emergencia": True})

# Saudação -------------------------------------------------------------------
no("saudacao", "Saudação", "#saudacao", texto(
    f"Olá! Sou o CardioIA. {MENU} Como posso ajudar hoje?",
    "Oi! Aqui é o CardioIA. Me conte o que está sentindo ou qual é a sua dúvida.",
    politica="random"))

# Sinais vitais ----------------------------------------------------------------
# Para "15 por 9" e "150 por 90", o primeiro @sys-number é a sistólica.
no("sinais_vitais", "Sinais vitais", "#sinais_vitais || @pressao_medida", proximo=AVALIAR_FILHOS)

no("pa_crise", "Pressão muito elevada",
   "@pressao_medida && (@sys-number >= 180 || (@sys-number >= 18 && @sys-number < 30))",
   texto("Você informou pressão de $pressao. Esse valor é muito elevado. "
         "Se houver dor no peito, falta de ar, dor de cabeça forte, visão turva ou fraqueza, ligue 192 ou vá ao pronto-socorro agora. "
         "Mesmo sem sintomas, procure atendimento hoje. " + AVISO),
   parent="sinais_vitais", contexto={"pressao": "@pressao_medida.literal", "alerta_emergencia": True})
no("pa_elevada", "Pressão elevada",
   "@pressao_medida && (@sys-number >= 140 || (@sys-number >= 14 && @sys-number < 30))",
   texto("Você informou pressão de $pressao, acima da referência de 14 por 9 (140/90 mmHg). "
         "Descanse 5 minutos sentado, meça de novo e anote. Se continuar alta, fale com seu médico. "
         "Não altere a dose do remédio por conta própria. " + AVISO),
   parent="sinais_vitais", contexto={"pressao": "@pressao_medida.literal"})
no("pa_baixa", "Pressão baixa",
   "@pressao_medida && ((@sys-number >= 5 && @sys-number < 9) || (@sys-number >= 50 && @sys-number < 90))",
   texto("Você informou pressão de $pressao, um valor baixo. Sente-se ou deite-se e beba água. "
         "Se tiver tontura forte, desmaio ou confusão, procure atendimento. " + AVISO),
   parent="sinais_vitais", contexto={"pressao": "@pressao_medida.literal"})
no("pa_referencia", "Pressão na referência", "@pressao_medida",
   texto("Você informou pressão de $pressao, dentro da faixa de referência para adultos (abaixo de 14 por 9). "
         "Continue medindo com regularidade e siga as orientações do seu médico. " + AVISO),
   parent="sinais_vitais", contexto={"pressao": "@pressao_medida.literal"})

no("fc_extrema", "Frequência cardíaca extrema",
   "@sinal_vital:(frequência cardíaca) && (@sys-number > 150 || @sys-number < 40)",
   texto("Frequência cardíaca de $frequencia_cardiaca bpm em repouso é um valor preocupante. "
         "Se vier com tontura, desmaio, dor no peito ou falta de ar, ligue 192. Procure atendimento hoje. " + AVISO),
   parent="sinais_vitais", contexto={"frequencia_cardiaca": "@sys-number", "alerta_emergencia": True})
no("fc_alterada", "Frequência cardíaca fora da referência",
   "@sinal_vital:(frequência cardíaca) && (@sys-number > 100 || @sys-number < 50)",
   texto("Frequência cardíaca de $frequencia_cardiaca bpm está fora da faixa usual em repouso (cerca de 50 a 100 bpm). "
         "Repouse, meça de novo e comente com seu médico, principalmente se sentir palpitação ou tontura. " + AVISO),
   parent="sinais_vitais", contexto={"frequencia_cardiaca": "@sys-number"})
no("fc_referencia", "Frequência cardíaca na referência", "@sinal_vital:(frequência cardíaca) && @sys-number",
   texto("Frequência cardíaca de $frequencia_cardiaca bpm está dentro da faixa usual em repouso (cerca de 50 a 100 bpm). " + AVISO),
   parent="sinais_vitais", contexto={"frequencia_cardiaca": "@sys-number"})

no("sat_baixa", "Saturação baixa", "@sinal_vital:saturação && @sys-number < 92",
   texto("Saturação de $saturacao% está baixa. Se houver falta de ar, lábios arroxeados ou confusão, "
         "ligue 192 ou vá ao pronto-socorro. " + AVISO),
   parent="sinais_vitais", contexto={"saturacao": "@sys-number", "alerta_emergencia": True})
no("sat_referencia", "Saturação informada", "@sinal_vital:saturação && @sys-number",
   texto("Saturação de $saturacao%. Em adultos saudáveis o esperado costuma ficar entre 95% e 100%; "
         "valores um pouco abaixo merecem acompanhamento médico. " + AVISO),
   parent="sinais_vitais", contexto={"saturacao": "@sys-number"})

no("sinais_sem_valor", "Sem valor informado", "anything_else", texto(
    "Posso ajudar a entender seus valores. Envie assim: \"minha pressão deu 13 por 8\", "
    "\"meus batimentos estão em 80\" ou \"saturação 97\". Referências gerais para adultos em repouso: "
    "pressão abaixo de 14 por 9, frequência cardíaca entre 50 e 100 bpm e saturação entre 95% e 100%. " + AVISO),
   parent="sinais_vitais")

# Medicamentos ---------------------------------------------------------------
no("medicamentos", "Medicamentos", "#medicamentos", proximo=AVALIAR_FILHOS)
no("medicamento_citado", "Caso medicamento citado", "@medicamento", texto(
    "Sobre $medicamento: não posso indicar dose, horário nem troca de remédio. "
    "Siga a receita, não suspenda por conta própria e confirme dúvidas com seu médico ou farmacêutico. "
    "Se esqueceu uma dose, não dobre a próxima sem orientação. Se tomou a mais e está passando mal, procure atendimento. " + AVISO),
   parent="medicamentos", contexto={"medicamento": "@medicamento"})
no("medicamento_geral", "Outros medicamentos", "anything_else", texto(
    "Não posso indicar dose, horário nem troca de remédio. Siga a receita, não suspenda nem dobre doses por conta própria "
    "e leve suas dúvidas ao médico ou farmacêutico. Se tiver reação como falta de ar, inchaço no rosto ou desmaio, ligue 192. " + AVISO),
   parent="medicamentos")

# Exames -----------------------------------------------------------------------
EXAMES = {
    "eletrocardiograma": "O eletrocardiograma (ECG) registra a atividade elétrica do coração em poucos minutos e ajuda a avaliar o ritmo cardíaco.",
    "ecocardiograma": "O ecocardiograma é um ultrassom do coração que mostra o tamanho das cavidades, a força de contração e as válvulas.",
    "teste ergométrico": "O teste ergométrico avalia o coração durante esforço na esteira ou bicicleta, com monitoramento do ECG e da pressão.",
    "Holter": "O Holter grava o ECG por 24 horas ou mais durante a rotina, para identificar arritmias que não aparecem em um exame rápido.",
    "MAPA": "O MAPA mede a pressão automaticamente várias vezes ao longo de 24 horas, inclusive durante o sono.",
    "exame de sangue": "Exames de sangue como colesterol, triglicerídeos e glicemia ajudam a estimar o risco cardiovascular.",
}
no("exames", "Exames", "#exames", proximo=AVALIAR_FILHOS)
for i, (nome, descricao) in enumerate(EXAMES.items(), start=1):
    no(f"exame_{i}", f"Caso {nome}", f"@exame:({nome})", texto(
        f"{descricao} O preparo e a interpretação do resultado devem ser confirmados com o médico que pediu o exame. {AVISO}"),
       parent="exames", contexto={"exame": "@exame"})
no("exame_geral", "Outros exames", "anything_else", texto(
    "Posso explicar para que servem eletrocardiograma, ecocardiograma, teste ergométrico, Holter, MAPA e exames de sangue. "
    "Não interpreto laudos: leve o resultado ao seu médico. Qual exame você quer entender?"),
   parent="exames")

# Agendamento simulado: especialidade -> data -> turno -> resumo ----------------
no("agendamento", "Agendamento (simulado)", "#agendamento", proximo=AVALIAR_FILHOS,
   contexto={"especialidade": None, "data_consulta": None, "turno": None})
no("agendamento_com_especialidade", "Especialidade já informada", "@especialidade", parent="agendamento",
   contexto={"especialidade": "@especialidade"}, proximo=pular("perguntar_data"))
no("agendamento_sem_especialidade", "Especialidade não informada", "anything_else", parent="agendamento",
   proximo=pular("perguntar_especialidade"))

no("resumo_agendamento", "Resumo do agendamento", PERGUNTA_SEM_CONDICAO, texto(
    "Pedido de agendamento registrado (simulação): especialidade $especialidade, dia <? $data_consulta.reformatDateTime('dd/MM/yyyy') ?>, turno $turno. "
    "Nenhuma consulta real foi marcada. Se os sintomas piorarem antes da consulta, procure atendimento."))

# Prevenção --------------------------------------------------------------------
no("prevencao", "Prevenção", "#prevencao", texto(
    "Algumas medidas gerais que protegem o coração: reduzir o sal e os ultraprocessados, preferir frutas, verduras e grãos integrais, "
    "fazer atividade física com liberação médica (cerca de 150 minutos por semana), não fumar, moderar o álcool, "
    "dormir bem e manter pressão, glicemia e colesterol acompanhados. " + AVISO))

# Ajuda, cancelar, despedida, fora de escopo ------------------------------------
no("ajuda", "Ajuda", "#ajuda", texto(
    f"{MENU} Por exemplo: \"estou com tontura\", \"minha pressão deu 14 por 9\" ou \"quero marcar consulta\". {AVISO}"))
no("cancelar", "Cancelar", "#cancelar", texto("Tudo bem, cancelei. Em que mais posso ajudar?"))
no("despedida", "Despedida", "#despedida", texto(
    "Por nada! Cuide-se. Se sentir dor no peito ou falta de ar intensa, ligue 192. Até logo!",
    "Foi um prazer ajudar. Lembre-se de levar suas dúvidas ao seu médico. Até mais!",
    politica="random"))
no("fora_de_escopo", "Fora de escopo", "#fora_de_escopo", texto(
    f"Esse assunto está fora do que eu sei fazer. Sou um assistente de saúde do coração. {MENU}"))

# Triagem de sintomas: sintoma -> período -> intensidade -> resumo ---------------
# Fica depois das outras intents para também capturar só a entidade ("tontura").
no("sintomas", "Triagem de sintomas", "#sintomas || @sintoma", proximo=AVALIAR_FILHOS,
   contexto={"sintoma": None, "periodo": None, "intensidade": None})
no("sintomas_com_sintoma", "Sintoma já informado", "@sintoma", parent="sintomas",
   contexto={"sintoma": "@sintoma"}, proximo=pular("perguntar_periodo"))
no("sintomas_sem_sintoma", "Sintoma não informado", "anything_else", parent="sintomas",
   proximo=pular("perguntar_sintoma"))

# Nós de pergunta (condição false: só entram por jump) -----------------------------
pergunta("perguntar_sintoma", "Perguntar sintoma",
         "Qual sintoma você está sentindo? (cansaço, tontura, palpitação, inchaço, falta de ar ou dor de cabeça)",
         "@sintoma", {"sintoma": "@sintoma"}, "perguntar_periodo",
         "Não reconheci esse sintoma.")
pergunta("perguntar_periodo", "Perguntar período",
         "Entendi: $sintoma. Desde quando você sente isso? (hoje, ontem, alguns dias, mais de uma semana ou mais de um mês)",
         "@periodo", {"periodo": "@periodo"}, "perguntar_intensidade",
         "Não entendi o período.")
pergunta("perguntar_intensidade", "Perguntar intensidade",
         "E qual a intensidade: leve, moderada ou forte?",
         "@intensidade", {"intensidade": "@intensidade"}, "resumo_sintomas",
         "Não entendi a intensidade.")

RESUMO = "Resumo do que você relatou: sintoma $sintoma, início $periodo, intensidade $intensidade."
no("resumo_sintomas", "Resumo dos sintomas", PERGUNTA_SEM_CONDICAO, proximo=AVALIAR_FILHOS)
no("resumo_forte", "Caso intensidade forte", "$intensidade == 'forte'", texto(
    f"{RESUMO} Um sintoma forte merece avaliação presencial ainda hoje. "
    "Se aparecer dor no peito, falta de ar intensa ou desmaio, ligue 192. " + AVISO),
   parent="resumo_sintomas")
no("resumo_persistente", "Caso sintoma persistente", "$periodo == 'há mais de uma semana' || $periodo == 'há mais de um mês'", texto(
    f"{RESUMO} Como o sintoma já dura algum tempo, vale marcar uma consulta. "
    "Posso simular o agendamento: diga \"quero marcar consulta\". " + AVISO),
   parent="resumo_sintomas")
no("resumo_leve", "Outros casos", "anything_else", texto(
    f"{RESUMO} Anote quando o sintoma aparece e o que estava fazendo, e comente com seu médico. "
    "Se piorar ou surgir dor no peito ou falta de ar intensa, procure atendimento. " + AVISO),
   parent="resumo_sintomas")

pergunta("perguntar_especialidade", "Perguntar especialidade",
         "Vamos simular o agendamento. Com qual especialidade? (cardiologia, clínico geral ou nutrição)",
         "@especialidade", {"especialidade": "@especialidade"}, "perguntar_data",
         "Não reconheci a especialidade.")
pergunta("perguntar_data", "Perguntar data",
         "Para qual dia? (por exemplo: amanhã, segunda-feira ou 20/10)",
         "@sys-date", {"data_consulta": "@sys-date"}, "perguntar_turno",
         "Não entendi a data.")
pergunta("perguntar_turno", "Perguntar turno",
         "Prefere manhã, tarde ou noite?",
         "@turno", {"turno": "@turno"}, "resumo_agendamento",
         "Não entendi o turno.")

# Em outros casos: variações sequenciais escalam a ajuda -------------------------
no("em_outros_casos", "Em outros casos", "anything_else", texto(
    "Desculpe, não entendi. Pode dizer de outro jeito?",
    "Ainda não entendi. Tente algo como \"estou com tontura\" ou \"minha pressão deu 13 por 8\".",
    f"Não consegui entender. {MENU} Se for algo urgente, ligue 192."))


def encadear_irmaos(nodes: list[dict]) -> None:
    """Preenche ``previous_sibling`` na ordem de declaração, por nó pai."""
    ultimo: dict[str | None, str] = {}
    for node in nodes:
        pai = node.get("parent")
        if pai in ultimo:
            node["previous_sibling"] = ultimo[pai]
        ultimo[pai] = node["dialog_node"]


def montar_skill() -> dict:
    nodes = NODES
    encadear_irmaos(nodes)
    entities = [
        {
            "entity": nome,
            "values": [{"type": "synonyms", "value": v, "synonyms": s} for v, s in valores.items()],
            "fuzzy_match": True,
        }
        for nome, valores in ENTITIES_SINONIMOS.items()
    ]
    entities += [
        {
            "entity": nome,
            "values": [{"type": "patterns", "value": v, "patterns": p} for v, p in valores.items()],
            "fuzzy_match": False,
        }
        for nome, valores in ENTITIES_PADROES.items()
    ]
    entities += [{"entity": nome, "values": []} for nome in SYSTEM_ENTITIES]
    return {
        "name": "cardioia-skill",
        "description": "CardioIA Fase 5 - atendimento inicial em saúde cardiológica (simulação acadêmica)",
        "language": "pt-br",
        "intents": [
            {"intent": nome, "description": desc, "examples": [{"text": t} for t in exemplos]}
            for nome, (desc, exemplos) in INTENTS.items()
        ],
        "entities": entities,
        "dialog_nodes": nodes,
        "counterexamples": [],
        "system_settings": {"disambiguation": {"enabled": False}},
        "learning_opt_out": True,
        "metadata": {"api_version": {"major_version": "v1", "minor_version": "2021-06-14"}},
        "webhooks": [],
    }


if __name__ == "__main__":
    skill = montar_skill()
    SAIDA.write_text(json.dumps(skill, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{SAIDA.name}: {len(skill['intents'])} intents, {len(skill['entities'])} entities, "
          f"{len(skill['dialog_nodes'])} dialog nodes")
