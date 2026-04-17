"""
Setup de Treino do Colossos.

Fluxo acionado quando o usuário escolhe "Montar Plano de Treino" no menu principal.
Coleta as preferências de treino e salva no perfil do usuário.

Steps:
  training_setup_nivel → training_setup_dias → training_setup_concluido

Sem IA — puro Python.
"""

from messenger import send_message, send_menu
from action_logger import log_action

# ---------------------------------------------------------------------------
# Steps deste módulo
# ---------------------------------------------------------------------------
STEP_NIVEL     = "training_setup_nivel"
STEP_DIAS      = "training_setup_dias"
STEP_CONCLUIDO = "training_setup_concluido"

NIVEL_MAP = {
    "iniciante":     "iniciante",
    "intermediário": "intermediario",
    "avançado":      "avancado",
}

DIAS_VALIDOS = {"1", "2", "3", "4", "5", "6", "7"}


# ---------------------------------------------------------------------------
# Ponto de entrada — chamado pelo main.py
# ---------------------------------------------------------------------------

def process_training_setup(telegram_id: str, text: str, user_doc, db) -> None:
    """Processa o fluxo de configuração de treino."""

    data     = user_doc.to_dict() if user_doc.exists else {}
    step     = data.get("current_setup_step", STEP_NIVEL)
    user_ref = db.collection("users").document(telegram_id)

    # ------------------------------------------------------------------
    # NÍVEL — primeira entrada neste fluxo
    # ------------------------------------------------------------------
    if step == STEP_NIVEL:
        _ask_nivel(telegram_id, db)
        user_ref.set({"current_setup_step": f"{STEP_NIVEL}_aguarda"}, merge=True)
        return

    if step == f"{STEP_NIVEL}_aguarda":
        result = _parse_option(text, NIVEL_MAP)
        if not result["ok"]:
            send_menu(telegram_id, result["error"] + "\n\nQual o seu nível?",
                      ["Iniciante", "Intermediário", "Avançado"])
            return
        log_action(db, telegram_id, "training_setup_nivel_Selecao", "menu_selecao", result["value"])
        user_ref.set({"experience": result["value"],
                      "current_setup_step": STEP_DIAS}, merge=True)

        log_action(db, telegram_id, "training_setup_dias_exibicao", "Exibicao")
        send_menu(
            telegram_id,
            "Quantos dias da semana você pode ir à academia?",
            ["1", "2", "3", "4", "5", "6", "7"],
        )
        return

    # ------------------------------------------------------------------
    # DIAS
    # ------------------------------------------------------------------
    if step == STEP_DIAS:
        dias = text.strip()
        if dias not in DIAS_VALIDOS:
            send_menu(telegram_id, "❌ Escolha entre 1 e 7 dias:",
                      ["1", "2", "3", "4", "5", "6", "7"])
            return
        nome = data.get("name", "")
        log_action(db, telegram_id, "training_setup_dias_Selecao", "menu_selecao", int(dias))
        user_ref.set(
            {
                "gym_days_per_week":       int(dias),
                "current_setup_step":      STEP_CONCLUIDO,
                "training_setup_complete": True,
            },
            merge=True,
        )
        log_action(db, telegram_id, "training_setup_concluido", "Concluido")

        send_message(
            telegram_id,
            f"✅ Perfeito, *{nome}*! Tenho tudo que preciso para montar seu plano de treino.\n\n"
            "Em breve seu treino personalizado estará pronto! 💪",
        )

        # Volta ao menu principal
        from menus import send_main_menu
        send_main_menu(telegram_id, db, nome)
        return

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    user_ref.set({"current_setup_step": STEP_NIVEL}, merge=True)
    send_message(telegram_id, "Ops, algo deu errado. Vamos recomeçar o setup de treino! 🔄")
    _ask_nivel(telegram_id, db)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _ask_nivel(telegram_id: str, db) -> None:
    log_action(db, telegram_id, "training_setup_nivel_exibicao", "Exibicao")
    send_menu(
        telegram_id,
        "Vamos montar seu plano de treino! 💪\n\nQual o seu nível de academia?",
        ["Iniciante", "Intermediário", "Avançado"],
    )


def _parse_option(text: str, valid_map: dict) -> dict:
    key = text.strip().lower()
    if key in valid_map:
        return {"ok": True, "value": valid_map[key]}
    return {"ok": False, "error": "❌ Opção inválida. Escolha uma das opções disponíveis."}