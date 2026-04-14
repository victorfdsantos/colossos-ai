import json
from datetime import datetime
from helpers import call_gemini, send_telegram_message

DAYS_PT = {0:"seg",1:"ter",2:"qua",3:"qui",4:"sex",5:"sab",6:"dom"}

def handle_diet(text: str, telegram_id: str, db) -> str:
    user = db.collection("users").document(telegram_id).get().to_dict()
    plan_doc = db.collection("plans").document(telegram_id).get()
    plan = plan_doc.to_dict().get("diet_plan") if plan_doc.exists else None

    # Busca alimentos mencionados na pergunta
    mentioned_foods = _fetch_mentioned_foods(text, db)

    today = DAYS_PT[datetime.now().weekday()]

    prompt = f"""Você é o Colossos, agente de nutrição esportiva.
                Perfil: {user["name"]}, {user["weight_kg"]}kg, objetivo: {user["goal"]}, alergias: {", ".join(user.get("allergies", [])) or "nenhuma"}.
                Dia atual: {today}.s
                Plano alimentar semanal: {json.dumps(plan, ensure_ascii=False)}
                Alimentos consultados: {json.dumps(mentioned_foods, ensure_ascii=False)}
                Pergunta: {text}
                Responda de forma direta e prática. Use listas ao listar refeições. Máximo 300 palavras."""

    return call_gemini(prompt)

def _fetch_mentioned_foods(text: str, db) -> list:
    """Busca no Firestore dados de alimentos mencionados no texto."""
    # Versão simples: busca por palavras-chave no texto
    foods_ref = db.collection("foods").stream()
    result = []
    text_lower = text.lower()
    for doc in foods_ref:
        food = doc.to_dict()
        if food["name"].lower() in text_lower:
            result.append(food)
    return result

def query_food(text: str, db) -> str:
    # Extrai nome do alimento via Gemini (chamada leve)
    food_name = call_gemini(
        f'Extraia apenas o nome do alimento mencionado nesta frase (sem mais nada): "{text}"',
        temperature=0, max_tokens=20
    ).strip().lower()

    # Busca no Firestore (comparação simples por nome)
    foods = db.collection("foods").stream()
    for doc in foods:
        food = doc.to_dict()
        if food_name in food["name"].lower():
            return _format_food_info(food)

    # Fallback: Gemini responde com dados gerais
    return call_gemini(
        f"Informe os dados nutricionais por 100g de: {food_name}. Seja conciso e use formato de lista."
    )

def _format_food_info(food: dict) -> str:
    return (
        f"🥗 *{food['name']}* (por 100g)\n"
        f"Calorias: {food['calories_per_100g']} kcal\n"
        f"Proteína: {food['protein_g']}g\n"
        f"Carboidratos: {food['carbs_g']}g\n"
        f"Gordura: {food['fat_g']}g\n"
        f"Fibras: {food.get('fiber_g', '-')}g\n"
        + (f"↔️ Substitutos: {', '.join(food['common_substitutes'])}"
           if food.get("common_substitutes") else "")
    )

