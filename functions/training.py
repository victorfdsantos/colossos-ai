import json
from datetime import datetime
from helpers import call_gemini

DAYS_PT = {0:"seg",1:"ter",2:"qua",3:"qui",4:"sex",5:"sab",6:"dom"}

def handle_training(text: str, telegram_id: str, db) -> str:
    user = db.collection("users").document(telegram_id).get().to_dict()
    plan_doc = db.collection("plans").document(telegram_id).get()
    plan = plan_doc.to_dict().get("training_plan") if plan_doc.exists else None

    mentioned_exercises = _fetch_mentioned_exercises(text, db)
    today = DAYS_PT[datetime.now().weekday()]

    prompt = f"""Você é o Colossos, agente de treino esportivo.
                Perfil: {user["name"]}, nível {user["experience"]}, objetivo: {user["goal"]}.
                Dia atual: {today}.
                Plano de treino semanal: {json.dumps(plan, ensure_ascii=False)}
                Exercícios consultados: {json.dumps(mentioned_exercises, ensure_ascii=False)}
                Pergunta: {text}
                Seja direto. Ao listar exercícios inclua séries x repetições. Máximo 300 palavras."""

    return call_gemini(prompt)

def _fetch_mentioned_exercises(text: str, db) -> list:
    exercises_ref = db.collection("exercises").stream()
    result = []
    text_lower = text.lower()
    for doc in exercises_ref:
        ex = doc.to_dict()
        if ex["name"].lower() in text_lower:
            result.append(ex)
    return result

def query_exercise(text: str, db) -> str:
    ex_name = call_gemini(
        f'Extraia apenas o nome do exercício mencionado (sem mais nada): "{text}"',
        temperature=0, max_tokens=20
    ).strip().lower()

    exercises = db.collection("exercises").stream()
    for doc in exercises:
        ex = doc.to_dict()
        if ex_name in ex["name"].lower():
            return _format_exercise_info(ex)

    return call_gemini(
        f"Explique como executar o exercício: {ex_name}. "
        f"Inclua músculos trabalhados, execução e dicas de segurança. Seja conciso."
    )

def _format_exercise_info(ex: dict) -> str:
    lines = [
        f"💪 *{ex['name']}*",
        f"Músculo: {ex['muscle_group']}  |  Equipamento: {ex['equipment']}",
        f"Nível: {ex['difficulty']}",
        "",
        f"📋 *Execução:* {ex['description']}",
        f"💡 *Dica:* {ex['tips']}",
    ]
    if ex.get("similar_exercises"):
        lines.append(f"↔️ *Similares:* {', '.join(ex['similar_exercises'])}")
    return "\n".join(lines)
