from helpers import call_gemini

VALID_INTENTS = {
    "diet", "training", "food_info", "exercise_info",
    "food_swap", "exercise_swap", "generate_plan", "other"
}

def detect_intent(text: str) -> str:
    prompt = f"""Classifique a mensagem do usuário em UMA das categorias:
                diet | training | food_info | exercise_info | food_swap | exercise_swap | generate_plan | other
                Responda APENAS com a palavra da categoria, sem explicação.
                Mensagem: '{text}'"""

    result = call_gemini(prompt, temperature=0, max_tokens=10)
    intent = result.strip().lower()
    return intent if intent in VALID_INTENTS else "other"