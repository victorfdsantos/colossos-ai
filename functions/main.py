"""
Orquestrador principal do Colossos.

Roteamento:
  onboarding_complete = False  →  onboarding.py  (fluxo novo)
  current_setup = "diet"       →  diet_setup.py
  current_setup = "training"   →  training_setup.py
  current_setup = "profile"    →  onboarding.py  (edição de campo)
  texto livre                  →  intent_router.py classifica e despacha
"""

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore

from onboarding import process_onboarding, FIELDS
from diet_setup import process_diet_setup, STEP_ALERGIAS as DIET_STEP_INICIO
from training_setup import process_training_setup, STEP_NIVEL as TRAINING_STEP_INICIO
from messenger import send_message
from menus import send_help_message, send_main_menu, send_main_menu_secundary, send_edit_profile_menu
from intent_router import (
    classify_intent,
    INTENT_MONTAR_DIETA, INTENT_MONTAR_TREINO,
    INTENT_EDITAR_PERFIL,
    INTENT_EDITAR_NOME, INTENT_EDITAR_IDADE, INTENT_EDITAR_PESO,
    INTENT_EDITAR_ALTURA, INTENT_EDITAR_OBJETIVO,
    INTENT_AJUDA, INTENT_OLA, INTENT_NAVEGACAO,
)

# ---------------------------------------------------------------------------
# Inicialização única do Firebase
# ---------------------------------------------------------------------------
_app = None
_db  = None

def _get_db():
    global _app, _db
    if _app is None:
        _app = initialize_app()
        _db  = firestore.client()
    return _db

# Mapa: intent → key do campo em FIELDS
_FIELD_KEYS = {f["label"]: f["key"] for f in FIELDS}
_INTENT_TO_FIELD = {
    INTENT_EDITAR_NOME:     _FIELD_KEYS["nome"],
    INTENT_EDITAR_IDADE:    _FIELD_KEYS["idade"],
    INTENT_EDITAR_PESO:     _FIELD_KEYS["peso"],
    INTENT_EDITAR_ALTURA:   _FIELD_KEYS["altura"],
    INTENT_EDITAR_OBJETIVO: _FIELD_KEYS["objetivo"],
}

# ---------------------------------------------------------------------------
# Endpoint principal
# ---------------------------------------------------------------------------

@https_fn.on_request()
def handle_message(req: https_fn.Request) -> https_fn.Response:
    body = req.get_json(silent=True)
    if not body or "message" not in body:
        return https_fn.Response("ok", status=200)

    db          = _get_db()
    message     = body["message"]
    telegram_id = str(message["from"]["id"])
    text        = message.get("text", "").strip()
    ok          = https_fn.Response("ok", status=200)

    if not text:
        send_message(telegram_id, "Por enquanto só consigo processar mensagens de texto. 😊")
        return ok

    user_ref  = db.collection("users").document(telegram_id)
    user_doc  = user_ref.get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    # 1. Onboarding não concluído
    if not user_data.get("onboarding_complete"):
        process_onboarding(telegram_id, text, user_doc, db)
        return ok

    # 2. Fluxo ativo — vai direto ao handler
    current_setup = user_data.get("current_setup")

    if current_setup == "diet":
        process_diet_setup(telegram_id, text, user_doc, db)
        _clear_setup_if_done(user_ref, "diet_setup_complete")
        return ok

    if current_setup == "training":
        process_training_setup(telegram_id, text, user_doc, db)
        _clear_setup_if_done(user_ref, "training_setup_complete")
        return ok

    if current_setup == "profile":
        process_onboarding(telegram_id, text, user_doc, db)
        return ok

    # 3. Sem fluxo ativo — classifica intenção
    intent = classify_intent(text)
    nome   = user_data.get("name", "")

    if intent == INTENT_MONTAR_DIETA:
        user_ref.set({"current_setup": "diet", "current_setup_step": DIET_STEP_INICIO}, merge=True)
        process_diet_setup(telegram_id, text, user_ref.get(), db)
        return ok

    if intent == INTENT_MONTAR_TREINO:
        user_ref.set({"current_setup": "training", "current_setup_step": TRAINING_STEP_INICIO}, merge=True)
        process_training_setup(telegram_id, text, user_ref.get(), db)
        return ok

    if intent == INTENT_EDITAR_PERFIL:
        # Abre o menu de seleção de campo
        user_ref.set({"current_setup": "profile", "onboarding_step": "edit_menu_aguarda"}, merge=True)
        send_edit_profile_menu(telegram_id, db)
        return ok

    if intent in _INTENT_TO_FIELD:
        # Pula direto para o campo específico
        field_key = _INTENT_TO_FIELD[intent]
        user_ref.set({
            "current_setup":      "profile",
            "onboarding_step":    f"awaiting_{field_key}",
            "editing_field":      field_key,
        }, merge=True)
        process_onboarding(telegram_id, text, user_ref.get(), db)
        return ok

    if intent == INTENT_AJUDA:
        send_help_message(telegram_id, nome)
        return ok

    if intent == INTENT_NAVEGACAO:
        send_main_menu_secundary(telegram_id, db, nome)
        return ok

    if intent == INTENT_OLA:
        send_message(telegram_id, "Olá!")
        send_main_menu(telegram_id, db, nome)
        return ok

    send_message(telegram_id,
        "Não entendi muito bem. 😅\n\n"
        "Você pode me dizer o que quer fazer, ou enviar *!help* para ver tudo que sei fazer.")
    return ok


def _clear_setup_if_done(user_ref, complete_flag):
    fresh = user_ref.get().to_dict() or {}
    if fresh.get(complete_flag):
        user_ref.set({"current_setup": None}, merge=True)