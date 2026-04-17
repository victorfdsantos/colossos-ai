"""
Setup de Dieta do Colossos.

Fluxo acionado quando o usuário escolhe "Montar Dieta" no menu principal.
Coleta as preferências de dieta e salva no perfil do usuário.

Steps:
  diet_setup_alergias → diet_setup_alergias_mais (loop)
  → diet_setup_refeicoes → diet_setup_estilo → diet_setup_concluido

Sem IA — puro Python.
"""

from messenger import send_message, send_menu
from action_logger import log_action

# ---------------------------------------------------------------------------
# Steps deste módulo (prefixo "diet_setup_" para não colidir com outros)
# ---------------------------------------------------------------------------
STEP_ALERGIAS      = "diet_setup_alergias"
STEP_ALERGIAS_MAIS = "diet_setup_alergias_mais"
STEP_REFEICOES     = "diet_setup_refeicoes"
STEP_ESTILO        = "diet_setup_estilo"
STEP_CONCLUIDO     = "diet_setup_concluido"

REFEICOES_VALIDAS = {"3", "4", "5", "6"}

ESTILO_MAP = {
    "mais flexível":  "flexivel",
    "mais regrada":   "regrada",
}


# ---------------------------------------------------------------------------
# Ponto de entrada — chamado pelo main.py
# ---------------------------------------------------------------------------

def process_diet_setup(telegram_id: str, text: str, user_doc, db) -> None:
    """Processa o fluxo de configuração de dieta."""

    data     = user_doc.to_dict() if user_doc.exists else {}
    step     = data.get("current_setup_step", STEP_ALERGIAS)
    user_ref = db.collection("users").document(telegram_id)

    # ------------------------------------------------------------------
    # ALERGIAS — primeira entrada neste fluxo
    # ------------------------------------------------------------------
    if step == STEP_ALERGIAS:
        _ask_alergias(telegram_id, db)
        user_ref.set({"current_setup_step": f"{STEP_ALERGIAS}_aguarda"}, merge=True)
        return

    if step == f"{STEP_ALERGIAS}_aguarda":
        raw = text.strip()
        if not raw:
            send_message(telegram_id,
                "Por favor, informe suas restrições ou envie *não* caso não tenha nenhuma.")
            return

        alergias = (
            []
            if raw.lower() == "não"
            else [a.strip() for a in raw.split(",") if a.strip()]
        )
        log_action(db, telegram_id, "diet_setup_alergias_Selecao", "Input", alergias)

        # Acumula com o que já existia (caso o usuário adicione mais)
        existentes = data.get("allergies", [])
        todas = list(set(existentes + alergias))
        user_ref.set({"allergies": todas,
                      "current_setup_step": STEP_ALERGIAS_MAIS}, merge=True)

        log_action(db, telegram_id, "diet_setup_alergias_confirmacao_exibicao", "Exibicao")
        send_menu(
            telegram_id,
            "Existe mais alguma restrição alimentar que deseja incluir?",
            ["Sim", "Não"],
        )
        return

    # ------------------------------------------------------------------
    # ALERGIAS — loop "tem mais?"
    # ------------------------------------------------------------------
    if step == STEP_ALERGIAS_MAIS:
        resp = text.strip().lower()
        if resp == "sim":
            user_ref.set({"current_setup_step": f"{STEP_ALERGIAS}_aguarda"}, merge=True)
            send_message(telegram_id,
                "Envie as restrições adicionais (separadas por vírgula):")
            return

        if resp != "não":
            send_menu(telegram_id, "❌ Por favor, escolha uma opção:", ["Sim", "Não"])
            return

        log_action(db, telegram_id, "diet_setup_alergias_confirmacao_Selecao", "menu_selecao", "Não")
        user_ref.set({"current_setup_step": STEP_REFEICOES}, merge=True)

        log_action(db, telegram_id, "diet_setup_refeicoes_exibicao", "Exibicao")
        send_menu(
            telegram_id,
            "Quantas refeições você deseja fazer por dia?",
            ["3", "4", "5", "6"],
        )
        return

    # ------------------------------------------------------------------
    # REFEIÇÕES
    # ------------------------------------------------------------------
    if step == STEP_REFEICOES:
        qtd = text.strip()
        if qtd not in REFEICOES_VALIDAS:
            send_menu(telegram_id, "❌ Escolha entre 3 e 6 refeições:",
                      ["3", "4", "5", "6"])
            return
        log_action(db, telegram_id, "diet_setup_refeicoes_Selecao", "menu_selecao", int(qtd))
        user_ref.set({"meals_per_day": int(qtd),
                      "current_setup_step": STEP_ESTILO}, merge=True)

        log_action(db, telegram_id, "diet_setup_estilo_exibicao", "Exibicao")
        send_menu(
            telegram_id,
            "Você prefere uma dieta mais flexível ou mais regrada?\n\n"
            "• *Mais flexível* — variedade maior de alimentos, substituições mais fáceis\n"
            "• *Mais regrada* — cardápio fixo e preciso, ideal para resultados mais rápidos",
            ["Mais Flexível", "Mais Regrada"],
        )
        return

    # ------------------------------------------------------------------
    # ESTILO
    # ------------------------------------------------------------------
    if step == STEP_ESTILO:
        result = _parse_option(text, ESTILO_MAP)
        if not result["ok"]:
            send_menu(telegram_id, result["error"] + "\n\nQual estilo prefere?",
                      ["Mais Flexível", "Mais Regrada"])
            return

        nome = data.get("name", "")
        log_action(db, telegram_id, "diet_setup_estilo_Selecao", "menu_selecao", result["value"])
        user_ref.set(
            {
                "diet_style":         result["value"],
                "current_setup_step": STEP_CONCLUIDO,
                "diet_setup_complete": True,
            },
            merge=True,
        )
        log_action(db, telegram_id, "diet_setup_concluido", "Concluido")

        send_message(
            telegram_id,
            f"✅ Ótimo, *{nome}*! Tenho tudo que preciso para montar sua dieta.\n\n"
            "Em breve seu plano alimentar estará pronto! 🥗",
        )

        # Volta ao menu principal
        from menus import send_main_menu
        send_main_menu(telegram_id, db, nome)
        return

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    user_ref.set({"current_setup_step": STEP_ALERGIAS}, merge=True)
    send_message(telegram_id, "Ops, algo deu errado. Vamos recomeçar o setup de dieta! 🔄")
    _ask_alergias(telegram_id, db)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _ask_alergias(telegram_id: str, db) -> None:
    log_action(db, telegram_id, "diet_setup_alergias_exibicao", "Exibicao")
    send_message(
        telegram_id,
        "Vamos montar sua dieta! 🥗\n\n"
        "Você possui alguma restrição ou alergia alimentar?\n"
        "Se sim, envie tudo em uma mensagem, separado por vírgula.\n"
        "Caso não tenha nenhuma, envie *não*.",
    )


def _parse_option(text: str, valid_map: dict) -> dict:
    key = text.strip().lower()
    if key in valid_map:
        return {"ok": True, "value": valid_map[key]}
    return {"ok": False, "error": "❌ Opção inválida. Escolha uma das opções disponíveis."}