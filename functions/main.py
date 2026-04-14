import json
from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore
from onboarding import process_onboarding
from intent import detect_intent
from diet import handle_diet, query_food
from training import handle_training, query_exercise
from plan import generate_plan
from helpers import send_telegram_message

_app = None
_db = None

def get_db():
    global _app, _db
    if _app is None:
        _app = initialize_app()
        _db = firestore.client()
    return _db

@https_fn.on_request()
def handle_message(req: https_fn.Request) -> https_fn.Response:
    body = req.get_json(silent=True)
    if not body or "message" not in body:
        return https_fn.Response("ok", status=200)

    db = get_db()

    message = body["message"]
    telegram_id = str(message["from"]["id"])
    text = message.get("text", "")

    # Responde Telegram imediatamente (evita retry por timeout)
    response = https_fn.Response("ok", status=200)

    user_ref = db.collection("users").document(telegram_id)
    user_doc = user_ref.get()

    # Onboarding
    if not user_doc.exists or not user_doc.to_dict().get("onboarding_complete"):
        process_onboarding(telegram_id, text, user_doc, db)
        return response

    # Roteamento por intenção
    intent = detect_intent(text)
    reply = ""

    if intent == "diet":          reply = handle_diet(text, telegram_id, db)
    elif intent == "training":    reply = handle_training(text, telegram_id, db)
    elif intent == "food_info":   reply = query_food(text, db)
    elif intent == "exercise_info": reply = query_exercise(text, db)
    elif intent == "food_swap":   reply = handle_diet(text, telegram_id, db)
    elif intent == "exercise_swap": reply = handle_training(text, telegram_id, db)
    elif intent == "generate_plan": reply = generate_plan(telegram_id, db)
    else: reply = "Pode me perguntar sobre seu treino ou dieta!"

    send_telegram_message(telegram_id, reply)
    return response
