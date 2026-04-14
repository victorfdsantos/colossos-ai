from helpers import send_telegram_message

QUESTIONS = [
    {"field": None,         "ask": "Olá! Sou o Colossos. Qual é o seu nome?"},
    {"field": "name",       "ask": "Qual é a sua altura em cm? (ex: 178)"},
    {"field": "height_cm",  "ask": "Qual é o seu peso em kg? (ex: 82)"},
    {"field": "weight_kg",  "ask": "Objetivo:\n1 - Hipertrofia\n2 - Emagrecimento\n3 - Condicionamento"},
    {"field": "goal",       "ask": "Nível:\n1 - Iniciante\n2 - Intermediário\n3 - Avançado"},
    {"field": "experience", "ask": "Tem alergia alimentar? (ex: lactose) ou responda: não"},
    {"field": "allergies",  "ask": None},  # finalizador
]

GOAL_MAP = {"1": "hipertrofia", "2": "emagrecimento", "3": "condicionamento"}
EXP_MAP  = {"1": "iniciante",   "2": "intermediario", "3": "avancado"}

def parse_answer(step: int, text: str) -> dict:
    """Valida e converte a resposta do usuário para o step atual."""
    text = text.strip()
    if step == 1:  # nome
        if len(text) < 2: return {"valid": False, "error": "Por favor, informe seu nome."}
        return {"valid": True, "data": {"name": text}}
    if step == 2:  # altura
        try:
            h = int(text)
            if not (100 <= h <= 250): raise ValueError
            return {"valid": True, "data": {"height_cm": h}}
        except ValueError:
            return {"valid": False, "error": "Informe a altura em cm (ex: 178)."}
    if step == 3:  # peso
        try:
            w = float(text.replace(",", "."))
            return {"valid": True, "data": {"weight_kg": w}}
        except ValueError:
            return {"valid": False, "error": "Informe o peso em kg (ex: 82.5)."}
    if step == 4:  # objetivo
        if text not in GOAL_MAP: return {"valid": False, "error": "Responda 1, 2 ou 3."}
        return {"valid": True, "data": {"goal": GOAL_MAP[text]}}
    if step == 5:  # nível
        if text not in EXP_MAP: return {"valid": False, "error": "Responda 1, 2 ou 3."}
        return {"valid": True, "data": {"experience": EXP_MAP[text]}}
    if step == 6:  # alergias
        allergies = [] if text.lower() == "não" else [a.strip() for a in text.split(",")]
        return {"valid": True, "data": {"allergies": allergies}}
    return {"valid": True, "data": {}}

def process_onboarding(telegram_id: str, text: str, user_doc, db):
    data = user_doc.to_dict() if user_doc.exists else {}
    step = data.get("onboarding_step", 0)
    user_ref = db.collection("users").document(telegram_id)

    if step > 0:
        result = parse_answer(step, text)
        if not result["valid"]:
            send_telegram_message(telegram_id, result["error"])
            return
        user_ref.set({**result["data"], "telegram_id": telegram_id,
                       "onboarding_step": step + 1}, merge=True)
        step += 1
    else:
        user_ref.set({"telegram_id": telegram_id, "onboarding_step": 1}, merge=True)

    if step >= len(QUESTIONS):
        user_ref.set({"onboarding_complete": True}, merge=True)
        send_telegram_message(telegram_id,
            "✅ Cadastro concluído! Pode me perguntar sobre treinos ou dieta.")
        return

    send_telegram_message(telegram_id, QUESTIONS[step]["ask"])