const API_CHAT = "/api/chat";
const API_HEALTH = "/api/health";

const WELCOME =
    "Olá! Eu sou o CardioIA, assistente virtual de atendimento inicial em saúde do coração. " +
    "Posso ajudar a: relatar sintomas, entender valores de pressão, batimentos e saturação, " +
    "tirar dúvidas gerais sobre medicamentos, explicar exames do coração, " +
    "simular o agendamento de uma consulta e dar dicas de prevenção. " +
    "Lembrete: sou uma simulação acadêmica e não substituo avaliação médica. " +
    "Em caso de dor no peito ou falta de ar intensa, ligue 192.";

let sessionId = null;
let sending = false;

function $(id) {
    return document.getElementById(id);
}

function setStatus(kind, text) {
    const el = $("status");
    el.className = "status status-" + kind;
    el.textContent = text;
}

function addBubble(role, text, meta) {
    const box = $("messages");
    const article = document.createElement("article");
    article.className = "bubble bubble-" + role;

    const who = document.createElement("span");
    who.className = "who";
    who.textContent = role === "user" ? "Você" : role === "error" ? "Sistema" : "CardioIA";

    const body = document.createElement("p");
    body.textContent = text;

    article.appendChild(who);
    article.appendChild(body);

    if (meta) {
        const extra = document.createElement("span");
        extra.className = "meta";
        extra.textContent = meta;
        article.appendChild(extra);
    }

    box.appendChild(article);
    box.parentElement.scrollTop = box.parentElement.scrollHeight;
}

function formatMeta(data) {
    const parts = [];
    if (data.intent) {
        const confidence = typeof data.confidence === "number" ? " " + data.confidence.toFixed(2) : "";
        parts.push("intent: " + data.intent + confidence);
    }
    if (Array.isArray(data.entities) && data.entities.length) {
        parts.push(
            "entidades: " +
                data.entities
                    .map(function (item) {
                        return (item.entity || "?") + "=" + (item.value || "?");
                    })
                    .join(", ")
        );
    }
    return parts.join(" · ");
}

function setBusy(isBusy) {
    sending = isBusy;
    $("userInput").disabled = isBusy;
    $("sendBtn").disabled = isBusy;
    $("sendBtn").textContent = isBusy ? "Enviando..." : "Enviar";
}

async function checkHealth() {
    try {
        const res = await fetch(API_HEALTH);
        const data = await res.json();
        if (data.watson_configured) {
            setStatus("ok", "Assistente conectado");
            return;
        }
        setStatus("warn", "Backend no ar, Watson sem credencial");
    } catch (err) {
        setStatus("err", "Backend offline");
    }
}

async function sendMessage(preset) {
    if (sending) return;

    const input = $("userInput");
    const text = (preset || input.value || "").trim();
    if (!text) return;

    addBubble("user", text);
    input.value = "";
    setBusy(true);

    try {
        const res = await fetch(API_CHAT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, session_id: sessionId }),
        });
        const data = await res.json();

        if (!res.ok) {
            const detail = data.detail ? " (" + data.detail + ")" : "";
            addBubble("error", (data.error || "Falha ao falar com o assistente.") + detail);
            if (res.status === 503) {
                setStatus("warn", "Backend no ar, Watson sem credencial");
            }
            return;
        }

        sessionId = data.session_id || sessionId;
        addBubble("bot", data.response || data.reply || "(sem texto de resposta)", formatMeta(data));
        setStatus("ok", "Assistente conectado");
    } catch (err) {
        addBubble("error", "Não foi possível alcançar o backend. Suba o Flask da Frente 2.");
        setStatus("err", "Backend offline");
    } finally {
        setBusy(false);
        input.focus();
    }
}

function init() {
    addBubble("bot", WELCOME);
    checkHealth();

    $("chatForm").addEventListener("submit", function (event) {
        event.preventDefault();
        sendMessage();
    });

    document.querySelectorAll("#suggestions button").forEach(function (button) {
        button.addEventListener("click", function () {
            sendMessage(button.getAttribute("data-text"));
        });
    });
}

init();
