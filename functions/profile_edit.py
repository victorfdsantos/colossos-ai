"""
Edição de perfil do Colossos.

Permite ao usuário alterar os campos coletados no onboarding:
  Nome, Idade, Peso, Altura, Objetivo.

Fluxo:
  menu_editar_perfil → usuário escolhe campo → digita novo valor
  → confirmação → salva + atualiza onboarding_updated_at → menu principal

Sem IA.
"""

import re
from datetime import datetime, timezone

from messenger import send_message, send_menu
from action_logger import log_action
from menus import (
    send_edit_profile_menu,
    send_invalid_option,
    OPT_EDIT_NOME,
    OPT_EDIT_IDADE,
    OPT_EDIT_PESO,
    OPT_EDIT_ALTURA,
    OPT_EDIT_OBJETIVO,
    OPT_EDIT_VOLTAR,
)

# ---------------------------------------------------------------------------
# Steps deste módulo
# ---------------------------------------------------------------------------
STEP_MENU          = "profile_edit_menu"
STEP_AGUARDA_VALOR = "profile_edit_aguarda_valor"  
STEP_CONFIRMA      = "profile_edit_confirma"

# ---------------------------------------------------------------------------
# Constantes de validação (espelham onboarding.py)
# ---------------------------------------------------------------------------
NOME_MIN_CHARS = 2
NOME_MAX_CHARS = 40
NOME_REGEX     = re.compile(r"^[A-Za-zÀ-ÿ\s\-]+$")

OBJETIVO_MAP = {
    "hipertrofia":    "hipertrofia",
    "emagrecimento":  "emagrecimento",
    "ganho de massa": "ganho_de_massa",
}

OBJETIVO_LABEL = {
    "hipertrofia":    "Hipertrofia",
    "emagrecimento":  "Emagrecimento",
    "ganho_de_massa": "Ganho de Massa",
}

# Mapa: campo interno → (label amigável, campo no Firestore)
FIELD_META = {
    OPT_EDIT_NOME:     ("nome",     "name"),
    OPT_EDIT_IDADE:    ("idade",    "age"),
    OPT_EDIT_PESO:     ("peso",     "weight_kg"),
    OPT_EDIT_ALTURA:   ("altura",   "height_cm"),
    OPT_EDIT_OBJETIVO: ("objetivo", "goal"),
}

# ---------------------------------------------------------------------------
# Validadores por campo
# ---------------------------------------------------------------------------

def _validate(field_key: str, text: str) -> dict:
    """Valida o novo valor conforme o campo sendo editado."""
    if field_key == OPT_EDIT_NOME:
        t = text.strip()
        if len(t) < NOME_MIN_CHARS:
            return {"ok": False, "error": f"❌ Nome muito curto. Mínimo {NOME_MIN_CHARS} caracteres."}
        if len(t) > NOME_MAX_CHARS:
            return {"ok": False, "error": f"❌ Nome muito longo. Máximo {NOME_MAX_CHARS} caracteres."}
        if not NOME_REGEX.match(t):
            return {"ok": False, "error": "❌ Nome inválido. Use apenas letras e espaços."}
        return {"ok": True, "value": t.title()}

    if field_key == OPT_EDIT_IDADE:
        try:
            match = re.search(r"\d+[.,]?\d*", text)
            if not match:
                raise ValueError
            
            age = int(float(match.group().replace(",", ".")))
            
            if not (10 <= age <= 100):
                raise ValueError
            return {"ok": True, "value": age}
        except ValueError:
            return {"ok": False, "error": "❌ Idade inválida. Informe apenas o número, ex: *25*"}

    if field_key == OPT_EDIT_PESO:
        try:
            match = re.search(r"\d+[.,]?\d*", text)
            if not match:
                raise ValueError

            w = int(float(match.group().replace(",", ".")))

            if not (30 <= w <= 300):
                raise ValueError
            return {"ok": True, "value": w}
        except ValueError:
            return {"ok": False, "error": "❌ Peso inválido. Informe em quilogramas, ex: *83* ou *83.5*"}

    if field_key == OPT_EDIT_ALTURA:
        try:
            match = re.search(r"\d+[.,]?\d*", text)
            if not match:
                raise ValueError

            h = int(float(match.group().replace(",", ".")))

            if not (100 <= h <= 250):
                raise ValueError
            return {"ok": True, "value": h}
        except ValueError:
            return {"ok": False, "error": "❌ Altura inválida. Informe em centímetros, ex: *178*"}

    if field_key == OPT_EDIT_OBJETIVO:
        key = text.strip().lower()
        if key in OBJETIVO_MAP:
            return {"ok": True, "value": OBJETIVO_MAP[key]}
        return {"ok": False, "error": "❌ Opção inválida. Escolha uma das opções disponíveis."}

    return {"ok": False, "error": "❌ Campo desconhecido."}


def _format_value(field_key: str, value) -> str:
    """Formata o valor para exibição na confirmação."""
    if field_key == OPT_EDIT_OBJETIVO:
        return OBJETIVO_LABEL.get(value, str(value))
    if field_key == OPT_EDIT_ALTURA:
        return f"{value} cm"
    if field_key == OPT_EDIT_PESO:
        return f"{value} kg"
    if field_key == OPT_EDIT_IDADE:
        return f"{value} anos"
    return str(value)


def _ask_new_value(telegram_id: str, db, field_key: str) -> None:
    """Solicita o novo valor para o campo escolhido."""
    prompts = {
        OPT_EDIT_NOME:     "Digite seu novo nome:",
        OPT_EDIT_IDADE:    "Digite sua nova idade:\n_Exemplo: 25_",
        OPT_EDIT_PESO:     "Digite seu novo peso em kg:\n_Exemplo: 83.5_",
        OPT_EDIT_ALTURA:   "Digite sua nova altura em cm:\n_Exemplo: 178_",
        OPT_EDIT_OBJETIVO: None,   # usa botões
    }
    log_action(db, telegram_id, f"profile_edit_{field_key}_exibicao", "Exibicao")
    if field_key == OPT_EDIT_OBJETIVO:
        send_menu(telegram_id, "Qual seu novo objetivo?",
                  ["Hipertrofia", "Emagrecimento", "Ganho de Massa"])
    else:
        send_message(telegram_id, prompts[field_key])


# ---------------------------------------------------------------------------
# Ponto de entrada — chamado pelo main.py
# ---------------------------------------------------------------------------

def process_profile_edit(telegram_id: str, text: str, user_doc, db) -> None:
    """Processa o fluxo de edição de perfil."""

    data     = user_doc.to_dict() if user_doc.exists else {}
    step     = data.get("current_setup_step", STEP_MENU)
    user_ref = db.collection("users").document(telegram_id)
    nome     = data.get("name", "")

    # ------------------------------------------------------------------
    # MENU de edição
    # ------------------------------------------------------------------
    if step == STEP_MENU:
        send_edit_profile_menu(telegram_id, db)
        user_ref.set({"current_setup_step": f"{STEP_MENU}_aguarda"}, merge=True)
        return

    if step == f"{STEP_MENU}_aguarda":
        resp = text.strip().lower()

        if resp == OPT_EDIT_VOLTAR:
            log_action(db, telegram_id, "profile_edit_Selecao", "menu_selecao", "Voltar")
            user_ref.set({"current_setup": None, "current_setup_step": None}, merge=True)
            return

        if resp not in FIELD_META:
            send_invalid_option(telegram_id)
            send_edit_profile_menu(telegram_id, db)
            return

        log_action(db, telegram_id, "profile_edit_Selecao", "menu_selecao", resp)
        user_ref.set(
            {"current_setup_step": STEP_AGUARDA_VALOR, "editing_field": resp},
            merge=True,
        )
        _ask_new_value(telegram_id, db, resp)
        return

    # ------------------------------------------------------------------
    # AGUARDA novo valor digitado
    # ------------------------------------------------------------------
    if step == STEP_AGUARDA_VALOR:
        field_key = data.get("editing_field", "")
        result    = _validate(field_key, text)

        if not result["ok"]:
            send_message(telegram_id, result["error"])
            _ask_new_value(telegram_id, db, field_key)
            return

        # Guarda valor pendente e pede confirmação
        user_ref.set(
            {"pending_edit_value": result["value"], "current_setup_step": STEP_CONFIRMA},
            merge=True,
        )
        label     = FIELD_META[field_key][0]
        formatted = _format_value(field_key, result["value"])
        log_action(db, telegram_id, f"profile_edit_{field_key}_valor", "Input", result["value"])

        send_menu(
            telegram_id,
            f"Confirma a alteração?\n\n*{label.capitalize()}*: {formatted}",
            ["Confirmar", "Cancelar"],
        )
        return

    # ------------------------------------------------------------------
    # CONFIRMAÇÃO da edição
    # ------------------------------------------------------------------
    if step == STEP_CONFIRMA:
        resp = text.strip().lower()

        if resp == "cancelar":
            log_action(db, telegram_id, "profile_edit_confirmacao", "menu_selecao", "Cancelar")
            user_ref.set(
                {"current_setup_step": f"{STEP_MENU}_aguarda", "editing_field": None, "pending_edit_value": None},
                merge=True,
            )
            send_message(telegram_id, "Alteração cancelada.")
            send_edit_profile_menu(telegram_id, db)
            return

        if resp != "confirmar":
            send_menu(telegram_id, "❌ Use os botões para confirmar ou cancelar.",
                      ["Confirmar", "Cancelar"])
            return

        field_key   = data.get("editing_field", "")
        firestore_field = FIELD_META[field_key][1]
        new_value   = data.get("pending_edit_value")

        log_action(db, telegram_id, "profile_edit_confirmacao", "menu_selecao", "Confirmar")
        user_ref.set(
            {
                firestore_field:          new_value,
                "onboarding_updated_at":  datetime.now(timezone.utc),
                "current_setup":          None,
                "current_setup_step":     None,
                "editing_field":          None,
                "pending_edit_value":     None,
            },
            merge=True,
        )
        log_action(db, telegram_id, f"profile_edit_{field_key}_concluido", "Concluido", new_value)

        # Atualiza nome local se foi o campo editado
        if field_key == OPT_EDIT_NOME:
            nome = new_value

        send_message(telegram_id, f"✅ *{FIELD_META[field_key][0].capitalize()}* atualizado com sucesso!")
        return

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    user_ref.set({"current_setup_step": STEP_MENU}, merge=True)
    send_message(telegram_id, "Ops, algo deu errado. 🔄")
    send_edit_profile_menu(telegram_id, db)