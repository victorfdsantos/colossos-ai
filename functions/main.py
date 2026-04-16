"""
Orquestrador principal do Colossos.

Responsabilidades:
  1. Receber o webhook do canal de mensagens.
  2. Identificar o usuário.
  3. Rotear para o módulo correto:

     ┌─ onboarding_complete = False  →  onboarding.py
     │
     └─ onboarding_complete = True
          ├─ current_setup = "diet"      →  diet_setup.py
          ├─ current_setup = "training"  →  training_setup.py
          ├─ menu principal              →  detecta opção e inicia setup
          └─ (demais agentes — próximas iterações)

Nenhuma lógica de negócio aqui — só roteamento.
"""

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore

from onboarding import process_onboarding, send_main_menu
from diet_setup import process_diet_setup, STEP_ALERGIAS as DIET_STEP_INICIO
from training_setup import process_training_setup, STEP_NIVEL as TRAINING_STEP_INICIO
from messenger import send_message

# Valores normalizados das opções do menu principal
_MENU_DIETA  = "montar dieta"
_MENU_TREINO = "montar plano de treino"

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
    # 1. Onboarding ainda não concluído
    # ------------------------------------------------------------------
    if not user_data.get("onboarding_complete"):
        process_onboarding(telegram_id, text, user_doc, db)
        return ok

    # ------------------------------------------------------------------
    # 2. Usuário está no meio de um setup de dieta
    # ------------------------------------------------------------------
    if user_data.get("current_setup") == "diet":
        process_diet_setup(telegram_id, text, user_doc, db)

        # Limpa o setup ativo quando concluído
        if user_ref.get().to_dict().get("diet_setup_complete"):
            user_ref.set({"current_setup": None}, merge=True)
        return ok

    # ------------------------------------------------------------------
    # 3. Usuário está no meio de um setup de treino
    # ------------------------------------------------------------------
    if user_data.get("current_setup") == "training":
        process_training_setup(telegram_id, text, user_doc, db)
        
        if user_ref.get().to_dict().get("training_setup_complete"):
            user_ref.set({"current_setup": None}, merge=True)
        return ok

    # ------------------------------------------------------------------
    # 4. Menu principal — detecta opção escolhida
    # ------------------------------------------------------------------
    text_lower = text.lower()

    if text_lower == _MENU_DIETA:
        user_ref.set(
            {"current_setup": "diet", "current_setup_step": DIET_STEP_INICIO},
            merge=True,
        )
        # Recarrega user_doc com o step recém-gravado
        process_diet_setup(telegram_id, text, user_ref.get(), db)
        return ok

    if text_lower == _MENU_TREINO:
        user_ref.set(
            {"current_setup": "training", "current_setup_step": TRAINING_STEP_INICIO},
            merge=True,
        )
        process_training_setup(telegram_id, text, user_ref.get(), db)
        return ok

    # ------------------------------------------------------------------
    # 5. Mensagem não reconhecida → exibe menu principal
    # ------------------------------------------------------------------
    nome = user_data.get("name", "")
    send_main_menu(telegram_id, db, nome)
    return ok