"""
Orquestrador principal do Colossos.

Roteamento:
  onboarding_complete = False  →  onboarding.py
  current_setup = "diet"       →  diet_setup.py
  current_setup = "training"   →  training_setup.py
  current_setup = "profile"    →  profile_edit.py
  texto livre                  →  intent_router.py classifica e despacha
"""

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore

from onboarding import process_onboarding
from diet_setup import process_diet_setup, STEP_ALERGIAS as DIET_STEP_INICIO
from training_setup import process_training_setup, STEP_NIVEL as TRAINING_STEP_INICIO
from profile_edit import (
    process_profile_edit,
    STEP_MENU as PROFILE_STEP_INICIO,
    STEP_AGUARDA_VALOR as PROFILE_STEP_AGUARDA,
)
from messenger import send_message
from menus import send_help_message, send_main_menu_secundary, send_main_menu
from intent_router import (
    classify_intent,
    INTENT_MONTAR_DIETA,
    INTENT_MONTAR_TREINO,
    INTENT_EDITAR_PERFIL,
    INTENT_EDITAR_NOME,
    INTENT_EDITAR_IDADE,
    INTENT_EDITAR_PESO,
    INTENT_EDITAR_ALTURA,
    INTENT_EDITAR_OBJETIVO,
    INTENT_AJUDA,
    INTENT_OLA,
    INTENT_NAVEGACAO
)
from menus import OPT_EDIT_NOME, OPT_EDIT_IDADE, OPT_EDIT_PESO, OPT_EDIT_ALTURA, OPT_EDIT_OBJETIVO

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
# Mapa: intent de edição direta → campo do profile_edit
# ---------------------------------------------------------------------------
_EDIT_FIELD_MAP = {
    INTENT_EDITAR_NOME:     OPT_EDIT_NOME,
    INTENT_EDITAR_IDADE:    OPT_EDIT_IDADE,
    INTENT_EDITAR_PESO:     OPT_EDIT_PESO,
    INTENT_EDITAR_ALTURA:   OPT_EDIT_ALTURA,
    INTENT_EDITAR_OBJETIVO: OPT_EDIT_OBJETIVO,
}


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
    # 2. Fluxo ativo — usuário já está no meio de um setup
    #    Neste caso NÃO passa pelo roteador: vai direto para o handler.
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
        return ok

    # ------------------------------------------------------------------
    # 3. Nenhum fluxo ativo → classifica intenção via LLM
    # ------------------------------------------------------------------
    intent = classify_intent(text)
    nome   = user_data.get("name", "")

    # --- Dieta ---
    if intent == INTENT_MONTAR_DIETA:
        user_ref.set(
            {"current_setup": "diet", "current_setup_step": DIET_STEP_INICIO},
            merge=True,
        )
        process_diet_setup(telegram_id, text, user_ref.get(), db)
        return ok

    # --- Treino ---
    if intent == INTENT_MONTAR_TREINO:
        user_ref.set(
            {"current_setup": "training", "current_setup_step": TRAINING_STEP_INICIO},
            merge=True,
        )
        process_training_setup(telegram_id, text, user_ref.get(), db)
        return ok

    # --- Editar perfil (menu genérico) ---
    if intent == INTENT_EDITAR_PERFIL:
        user_ref.set(
            {"current_setup": "profile", "current_setup_step": PROFILE_STEP_INICIO},
            merge=True,
        )
        process_profile_edit(telegram_id, text, user_ref.get(), db)
        return ok

    # --- Editar campo específico diretamente ---
    if intent in _EDIT_FIELD_MAP:
        field_key = _EDIT_FIELD_MAP[intent]
        # Pula o menu de seleção e vai direto para aguardar o valor
        user_ref.set(
            {
                "current_setup":       "profile",
                "current_setup_step":  PROFILE_STEP_AGUARDA,
                "editing_field":       field_key,
            },
            merge=True,
        )
        # Reutiliza o handler — ele vai cair no step AGUARDA_VALOR
        process_profile_edit(telegram_id, text, user_ref.get(), db)
        return ok

    # --- Ajuda ---
    if intent == INTENT_AJUDA:
        send_help_message(telegram_id, nome)
        return ok
    
    # --- Navegação ---
    if intent == INTENT_NAVEGACAO:
        send_main_menu_secundary(telegram_id, db, nome)
        return ok

    # --- Ola ---
    if intent == INTENT_OLA:
        send_message(
            telegram_id,
            "Olá!",
        )
        send_main_menu(telegram_id, db, nome)
        return ok

    # --- Desconhecido ---
    send_message(
        telegram_id,
        "Não entendi muito bem. 😅\n\n"
        "Você pode me dizer o que quer fazer, ou enviar *!help* para ver tudo que sei fazer.",
    )
    return ok


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _clear_setup_if_done(user_ref, complete_flag: str) -> None:
    """Limpa current_setup quando o fluxo concluiu."""
    fresh = user_ref.get().to_dict() or {}
    if fresh.get(complete_flag):
        user_ref.set({"current_setup": None}, merge=True)