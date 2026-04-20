"""
Onboarding e edição de perfil do Colossos.

O fluxo é declarado em FIELDS — uma lista ordenada de campos.
Cada campo sabe como perguntar, validar e onde salvar no Firestore.

Onboarding novo  → percorre FIELDS do início ao fim.
Edição de campo  → pula direto para o campo indicado em `editing_field`.

Um único ponto de entrada: process_onboarding().
"""

import re
from datetime import datetime, timezone

from messenger import send_message, send_menu
from action_logger import log_action
from menus import send_main_menu

# ---------------------------------------------------------------------------
# Validadores
# ---------------------------------------------------------------------------

def _parse_nome(text):
    t = text.strip()
    if len(t) < 2 or len(t) > 40:
        return {"ok": False, "error": "❌ Nome inválido. Use entre 2 e 40 caracteres."}
    if not re.match(r"^[A-Za-zÀ-ÿ\s\-]+$", t):
        return {"ok": False, "error": "❌ Nome inválido. Use apenas letras e espaços."}
    return {"ok": True, "value": t.title()}

def _parse_objetivo(text):
    opts = {"hipertrofia": "hipertrofia", "emagrecimento": "emagrecimento", "ganho de massa": "ganho_de_massa"}
    v = opts.get(text.strip().lower())
    return {"ok": True, "value": v} if v else {"ok": False, "error": "❌ Escolha uma das opções."}

def _parse_altura(text):
    try:
        v = int(float(re.search(r"[\d.,]+", text).group().replace(",", ".")))
        if not (100 <= v <= 250): raise ValueError
        return {"ok": True, "value": v}
    except:
        return {"ok": False, "error": "❌ Altura inválida. Informe em cm, ex: *178*"}

def _parse_peso(text):
    try:
        v = round(float(re.search(r"[\d.,]+", text).group().replace(",", ".")), 1)
        if not (30 <= v <= 300): raise ValueError
        return {"ok": True, "value": v}
    except:
        return {"ok": False, "error": "❌ Peso inválido. Informe em kg, ex: *83.5*"}

def _parse_idade(text):
    try:
        v = int(re.search(r"\d+", text).group())
        if not (10 <= v <= 100): raise ValueError
        return {"ok": True, "value": v}
    except:
        return {"ok": False, "error": "❌ Idade inválida. Informe apenas o número, ex: *25*"}


# ---------------------------------------------------------------------------
# Declaração dos campos — ordem = ordem do onboarding
# ---------------------------------------------------------------------------

FIELDS = [
    {
        "key":      "name",
        "label":    "nome",
        "ask":      "Como você quer ser chamado?",
        "validate": _parse_nome,
        "type":     "text",
    },
    {
        "key":      "goal",
        "label":    "objetivo",
        "ask":      "Qual é o seu objetivo?",
        "validate": _parse_objetivo,
        "type":     "menu",
        "options":  ["Hipertrofia", "Emagrecimento", "Ganho de Massa"],
        "display":  {"hipertrofia": "Hipertrofia", "emagrecimento": "Emagrecimento", "ganho_de_massa": "Ganho de Massa"},
    },
    {
        "key":      "height_cm",
        "label":    "altura",
        "ask":      "Qual a sua altura em centímetros?\n_Exemplo: 178_",
        "validate": _parse_altura,
        "type":     "text",
        "unit":     "cm",
    },
    {
        "key":      "weight_kg",
        "label":    "peso",
        "ask":      "Qual o seu peso em quilogramas?\n_Exemplo: 83_",
        "validate": _parse_peso,
        "type":     "text",
        "unit":     "kg",
    },
    {
        "key":      "age",
        "label":    "idade",
        "ask":      "Qual a sua idade?\n_Exemplo: 25_",
        "validate": _parse_idade,
        "type":     "text",
        "unit":     "anos",
    },
]

# Lookup rápido por key
_FIELD_BY_KEY = {f["key"]: f for f in FIELDS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ask(telegram_id, field):
    """Envia a pergunta do campo — texto livre ou menu de opções."""
    if field["type"] == "menu":
        send_menu(telegram_id, field["ask"], field["options"])
    else:
        send_message(telegram_id, field["ask"])

def _display_value(field, value):
    """Formata o valor para exibição (confirmação, resumo)."""
    if "display" in field:
        return field["display"].get(value, value)
    if "unit" in field:
        return f"{value} {field['unit']}"
    return str(value)

def _next_field(current_key):
    """Retorna o próximo campo na sequência, ou None se for o último."""
    keys = [f["key"] for f in FIELDS]
    idx  = keys.index(current_key)
    return FIELDS[idx + 1] if idx + 1 < len(FIELDS) else None

def _build_summary(data):
    icons = {"name": "👤", "goal": "🎯", "height_cm": "📏", "weight_kg": "⚖️", "age": "🎂"}
    lines = ["📋 *Confira seus dados antes de confirmar:*\n"]
    for f in FIELDS:
        value = data.get(f["key"], "—")
        shown = _display_value(f, value) if value != "—" else "—"
        lines.append(f"{icons[f['key']]} {f['label'].capitalize()}: *{shown}*")
    lines.append("\nEstá tudo certo?")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Ponto de entrada único
# ---------------------------------------------------------------------------

def process_onboarding(telegram_id, text, user_doc, db):
    """
    Onboarding novo e edição de perfil num único fluxo.

    Steps no Firestore (onboarding_step):
      "welcome"          → boas-vindas iniciais
      "awaiting_<key>"   → aguardando resposta para o campo <key>
      "confirm_new"      → confirmação do onboarding completo
      "confirm_edit"     → confirmação de edição de campo único
      "concluido"        → perfil completo, fluxo inativo
    """
    data     = user_doc.to_dict() if user_doc.exists else {}
    step     = data.get("onboarding_step", "welcome")
    user_ref = db.collection("users").document(telegram_id)
    nome     = data.get("name", "")

    # ------------------------------------------------------------------
    # Boas-vindas
    # ------------------------------------------------------------------
    if step == "welcome":
        log_action(db, telegram_id, "onboarding_inicial", "Exibicao")
        user_ref.set({"telegram_id": telegram_id, "onboarding_step": "awaiting_start"}, merge=True)
        send_menu(telegram_id,
            "Olá! Eu sou o *Colossos*, seu agente esportivo 💪\n\n"
            "Vou te ajudar a montar seu treino e sua dieta personalizados.\n\n"
            "Vamos começar?",
            ["Sim", "Não"])
        return

    if step == "awaiting_start":
        if text.strip().lower() == "não":
            send_message(telegram_id, "Sem problemas! 😊 Quando quiser, é só me chamar.")
            return
        first = FIELDS[0]
        user_ref.set({"onboarding_step": f"awaiting_{first['key']}"}, merge=True)
        log_action(db, telegram_id, f"onboarding_{first['key']}_exibicao", "Exibicao")
        _ask(telegram_id, first)
        return

    # ------------------------------------------------------------------
    # Coleta de campo — serve tanto para onboarding novo quanto para edição
    # ------------------------------------------------------------------
    if step.startswith("awaiting_"):
        key   = step.removeprefix("awaiting_")
        field = _FIELD_BY_KEY.get(key)

        if not field:
            user_ref.set({"onboarding_step": "welcome"}, merge=True)
            send_message(telegram_id, "Ops, algo deu errado. Vamos recomeçar! 🔄")
            return

        result = field["validate"](text)
        if not result["ok"]:
            send_message(telegram_id, result["error"])
            _ask(telegram_id, field)
            return

        log_action(db, telegram_id, f"onboarding_{key}_selecao", "input", result["value"])
        user_ref.set({field["key"]: result["value"]}, merge=True)

        if data.get("editing_field"):
            # Edição — vai para confirmação de campo único
            user_ref.set({"onboarding_step": "confirm_edit", "pending_edit_value": result["value"]}, merge=True)
            shown = _display_value(field, result["value"])
            send_menu(telegram_id,
                f"Confirma a alteração?\n\n*{field['label'].capitalize()}*: {shown}",
                ["Confirmar", "Cancelar"])

        else:
            # Onboarding novo — avança para o próximo campo ou vai para confirmação final
            next_f = _next_field(key)
            if next_f:
                user_ref.set({"onboarding_step": f"awaiting_{next_f['key']}"}, merge=True)
                log_action(db, telegram_id, f"onboarding_{next_f['key']}_exibicao", "Exibicao")
                _ask(telegram_id, next_f)
            else:
                user_ref.set({"onboarding_step": "confirm_new"}, merge=True)
                log_action(db, telegram_id, "onboarding_confirmacao_exibicao", "Exibicao")
                send_menu(telegram_id, _build_summary({**data, field["key"]: result["value"]}), ["Confirmar", "Recomeçar"])
        return

    # ------------------------------------------------------------------
    # Confirmação — onboarding novo
    # ------------------------------------------------------------------
    if step == "confirm_new":
        resp = text.strip().lower()

        if resp == "recomeçar":
            reset = {f["key"]: None for f in FIELDS}
            reset["onboarding_step"] = f"awaiting_{FIELDS[0]['key']}"
            user_ref.set(reset, merge=True)
            send_message(telegram_id, "Tudo bem, vamos recomeçar! 🔄")
            _ask(telegram_id, FIELDS[0])
            return

        if resp != "confirmar":
            send_menu(telegram_id, "❌ Use os botões.", ["Confirmar", "Recomeçar"])
            return

        now = datetime.now(timezone.utc)
        user_ref.set({
            "onboarding_step":       "concluido",
            "onboarding_complete":   True,
            "onboarding_created_at": now,
            "onboarding_updated_at": now,
        }, merge=True)
        log_action(db, telegram_id, "onboarding_concluido", "Concluido")
        send_message(telegram_id,
            f"Perfeito, *{nome}*! 🙌\n\n"
            "Recebi todas as suas informações básicas.\n"
            "A partir daqui posso te ajudar a montar seu treino e sua dieta de forma personalizada.")
        send_main_menu(telegram_id, db, nome)
        return

    # ------------------------------------------------------------------
    # Confirmação — edição de campo único
    # ------------------------------------------------------------------
    if step == "confirm_edit":
        resp = text.strip().lower()

        if resp == "cancelar":
            user_ref.set({
                "current_setup": None, "current_setup_step": None,
                "editing_field": None, "pending_edit_value": None,
                "onboarding_step": "concluido",
            }, merge=True)
            send_message(telegram_id, "Alteração cancelada.")
            send_main_menu(telegram_id, db, nome)
            return

        if resp != "confirmar":
            send_menu(telegram_id, "❌ Use os botões.", ["Confirmar", "Cancelar"])
            return

        field     = _FIELD_BY_KEY.get(data.get("editing_field", ""))
        new_value = data.get("pending_edit_value")
        if field:
            log_action(db, telegram_id, f"edit_{field['key']}_concluido", "Concluido", new_value)
            nome_final = new_value if field["key"] == "name" else nome
            user_ref.set({
                "onboarding_updated_at": datetime.now(timezone.utc),
                "current_setup":         None,
                "current_setup_step":    None,
                "editing_field":         None,
                "pending_edit_value":    None,
                "onboarding_step":       "concluido",
            }, merge=True)
            send_message(telegram_id, f"✅ *{field['label'].capitalize()}* atualizado com sucesso!")
            send_main_menu(telegram_id, db, nome_final)
        return