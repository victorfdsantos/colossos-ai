"""
Orquestrador principal do Colossos.

Roteamento:
  onboarding_complete = False  →  onboarding.py
  current_setup = "diet"       →  diet_setup.py
  current_setup = "training"   →  training_setup.py
  current_setup = "profile"    →  profile_edit.py
  menu principal               →  detecta opção via menus.py e inicia fluxo
  texto não reconhecido        →  exibe menu principal

Nenhuma lógica de negócio aqui — só roteamento.
"""

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore

from profile.onboarding import process_onboarding
from diet.diet_setup import process_diet_setup, STEP_ALERGIAS as DIET_STEP_INICIO
from training.training_setup import process_training_setup, STEP_NIVEL as TRAINING_STEP_INICIO
from profile.profile_edit import process_profile_edit, STEP_MENU as PROFILE_STEP_INICIO
from messenger import send_message
from menus import (
    send_main_menu,
    OPT_MONTAR_DIETA,
    OPT_MONTAR_TREINO,
    OPT_EDITAR_PERFIL,
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


# ---------------------------------------------------------------------------
# Endpoint principal
# ---------------------------------------------------------------------------

@https_fn.on_request()
def handle_message(req: https_fn.Request) -> https_fn.Response:
    body = req.get_json(silent=True)
    if not body or "message" not in body:
        return https_fn.Response("ok", status=200)

    db = _get_db()

    message     = body["message"]
    telegram_id = str(message["from"]["id"])
    text        = message.get("text", "").strip()

    ok = https_fn.Response("ok", status=200)

    if not text:
        send_message(telegram_id, "Por enquanto só consigo processar mensagens de texto. 😊")
        return ok

    user_ref  = db.collection("users").document(telegram_id)
    user_doc  = user_ref.get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    # ------------------------------------------------------------------
    # 1. Onboarding não concluído
    # ------------------------------------------------------------------
    if not user_data.get("onboarding_complete"):
        process_onboarding(telegram_id, text, user_doc, db)
        return ok

    # ------------------------------------------------------------------
    # 2. Fluxo ativo (diet / training / profile)
    # ------------------------------------------------------------------
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
        process_profile_edit(telegram_id, text, user_doc, db)
        return ok   # profile_edit limpa current_setup internamente

    # ------------------------------------------------------------------
    # 3. Seleção no menu principal
    # ------------------------------------------------------------------
    text_lower = text.lower()

    if text_lower == OPT_MONTAR_DIETA:
        user_ref.set(
            {"current_setup": "diet", "current_setup_step": DIET_STEP_INICIO},
            merge=True,
        )
        process_diet_setup(telegram_id, text, user_ref.get(), db)
        return ok

    if text_lower == OPT_MONTAR_TREINO:
        user_ref.set(
            {"current_setup": "training", "current_setup_step": TRAINING_STEP_INICIO},
            merge=True,
        )
        process_training_setup(telegram_id, text, user_ref.get(), db)
        return ok

    if text_lower == OPT_EDITAR_PERFIL:
        user_ref.set(
            {"current_setup": "profile", "current_setup_step": PROFILE_STEP_INICIO},
            merge=True,
        )
        process_profile_edit(telegram_id, text, user_ref.get(), db)
        return ok

    # ------------------------------------------------------------------
    # 4. Texto não reconhecido → menu principal
    # ------------------------------------------------------------------
    nome = user_data.get("name", "")
    send_main_menu(telegram_id, db, nome)
    return ok


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _clear_setup_if_done(user_ref, complete_flag: str) -> None:
    """Limpa current_setup quando o fluxo concluiu."""
    fresh = user_ref.get().to_dict() or {}
    if fresh.get(complete_flag):
        user_ref.set({"current_setup": None}, merge=True)