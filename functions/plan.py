import json
from datetime import datetime
from helpers import call_gemini

def generate_plan(telegram_id: str, db) -> str:
    user = db.collection("users").document(telegram_id).get().to_dict()

    # Carrega bases (filtrando por alergias e nível)
    allergies = user.get("allergies", [])
    foods = [
        d.to_dict() for d in db.collection("foods").stream()
        if not any(a in d.to_dict().get("tags", []) for a in allergies)
    ]
    exercises = [
        d.to_dict() for d in db.collection("exercises").stream()
        if d.to_dict().get("difficulty") in (user["experience"], "iniciante")
    ]

    food_names = [f["name"] for f in foods]
    ex_names   = [e["name"] for e in exercises]

    prompt = f"""Crie um plano SEMANAL de treino e dieta em JSON.
                Perfil: {json.dumps(user, ensure_ascii=False)}
                Alimentos disponíveis: {json.dumps(food_names, ensure_ascii=False)}
                Exercícios disponíveis: {json.dumps(ex_names, ensure_ascii=False)}
                Formato obrigatório:
                {{
                "diet_plan": {{"seg": {{"cafe": [...], "almoco": [...], "lanche": [...], "jantar": [...]}}, ...}},
                "training_plan": {{"seg": {{"type": "A", "exercises": [{{"name": "...", "sets": 4, "reps": 12, "rest_sec": 60}}]}}, ...}}
                }}
                Retorne APENAS JSON válido, sem texto adicional."""

    raw = call_gemini(prompt, max_tokens=2000)
    clean_json = raw.replace("```json", "").replace("```", "").strip()

    try:
        plan = json.loads(clean_json)
    except json.JSONDecodeError:
        return "Não consegui gerar o plano agora. Tente novamente em instantes."

    db.collection("plans").document(telegram_id).set({
        **plan,
        "telegram_id": telegram_id,
        "generated_at": datetime.utcnow()
    })

    return _format_plan_summary(plan)

def _format_plan_summary(plan: dict) -> str:
    lines = ["✅ *Plano gerado com sucesso!*\n"]
    lines.append("*Treinos da semana:*")
    for day, t in plan.get("training_plan", {}).items():
        ex_list = ", ".join(e["name"] for e in t.get("exercises", [])[:3])
        lines.append(f"  {day.capitalize()}: {ex_list}...")
    lines.append("\nMe pergunte sobre qualquer dia para ver detalhes!")
    return "\n".join(lines)
