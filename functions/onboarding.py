"""
Onboarding do Colossos — coleta do perfil base.

Fluxo:
  welcome → nome → objetivo → altura → peso → idade
  → confirmacao (exibe resumo) → concluido + menu principal

Sem IA. Menus centralizados em menus.py.
"""

import re
from datetime import datetime, timezone

from messenger import send_message, send_menu
from action_logger import log_action
from menus import send_main_menu

# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
STEP_WELCOME       = "welcome"
STEP_NOME          = "nome"
STEP_NOME_AGUARDA  = "nome_aguarda"
STEP_OBJETIVO      = "objetivo"
STEP_ALTURA        = "altura"
STEP_PESO          = "peso"
STEP_IDADE         = "idade"
STEP_CONFIRMACAO   = "confirmacao"
STEP_CONCLUIDO     = "concluido"

# ---------------------------------------------------------------------------
# Constantes de validação
# ---------------------------------------------------------------------------
NOME_MIN_CHARS = 2
NOME_MAX_CHARS = 40
# Permite letras (incluindo acentuadas), espaços e hífens — nada mais
NOME_REGEX     = re.compile(r"^[A-Za-zÀ-ÿ\s\-]+$")

OBJETIVO_MAP = {
    "hipertrofia":    "hipertrofia",
    "emagrecimento":  "emagrecimento",
    "ganho de massa": "ganho_de_massa",
}

OBJETIVO_LABEL = {
    "hipertrofia":   "Hipertrofia",
    "emagrecimento": "Emagrecimento",
    "ganho_de_massa": "Ganho de Massa",
}

# ---------------------------------------------------------------------------
# Validações puras (sem IA)
# ---------------------------------------------------------------------------

def _parse_nome(text: str) -> dict:
    t = text.strip()
    if len(t) < NOME_MIN_CHARS:
        return {"ok": False, "error": f"❌ Nome muito curto. Mínimo {NOME_MIN_CHARS} caracteres."}
    if len(t) > NOME_MAX_CHARS:
        return {"ok": False, "error": f"❌ Nome muito longo. Máximo {NOME_MAX_CHARS} caracteres."}
    if not NOME_REGEX.match(t):
        return {"ok": False, "error": "❌ Nome inválido. Use apenas letras e espaços."}
    return {"ok": True, "value": t.title()}


def _parse_altura(text: str) -> dict:
    try:
        h = int(float(text.strip().replace(",", ".")))
        if not (100 <= h <= 250):
            raise ValueError
        return {"ok": True, "value": h}
    except ValueError:
        return {"ok": False, "error": "❌ Altura inválida. Informe em centímetros, ex: *178*"}


def _parse_peso(text: str) -> dict:
    try:
        w = round(float(text.strip().replace(",", ".")), 1)
        if not (30 <= w <= 300):
            raise ValueError
        return {"ok": True, "value": w}
    except ValueError:
        return {"ok": False, "error": "❌ Peso inválido. Informe em quilogramas, ex: *83* ou *83.5*"}


def _parse_idade(text: str) -> dict:
    try:
        age = int(text.strip())
        if not (10 <= age <= 100):
            raise ValueError
        return {"ok": True, "value": age}
    except ValueError:
        return {"ok": False, "error": "❌ Idade inválida. Informe apenas o número, ex: *25*"}


def _parse_option(text: str, valid_map: dict) -> dict:
    key = text.strip().lower()
    if key in valid_map:
        return {"ok": True, "value": valid_map[key]}
    return {"ok": False, "error": "❌ Opção inválida. Escolha uma das opções disponíveis."}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _build_confirmation_text(data: dict) -> str:
    """Monta o resumo do perfil para confirmação."""
    objetivo_raw = data.get("goal", "")
    objetivo_str = OBJETIVO_LABEL.get(objetivo_raw, objetivo_raw.replace("_", " ").title())
    return (
        "📋 *Confira seus dados antes de confirmar:*\n\n"
        f"👤 Nome: *{data.get('name', '—')}*\n"
        f"🎯 Objetivo: *{objetivo_str}*\n"
        f"📏 Altura: *{data.get('height_cm', '—')} cm*\n"
        f"⚖️ Peso: *{data.get('weight_kg', '—')} kg*\n"
        f"🎂 Idade: *{data.get('age', '—')} anos*\n\n"
        "Está tudo certo?"
    )


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------

def process_onboarding(telegram_id: str, text: str, user_doc, db) -> None:
    """Chamado pelo main.py enquanto onboarding_complete=False."""

    data     = user_doc.to_dict() if user_doc.exists else {}
    step     = data.get("onboarding_step", STEP_WELCOME)
    user_ref = db.collection("users").document(telegram_id)

    # ------------------------------------------------------------------
    # WELCOME
    # ------------------------------------------------------------------
    if step == STEP_WELCOME:
        user_ref.set({"telegram_id": telegram_id, "onboarding_step": STEP_NOME}, merge=True)
        log_action(db, telegram_id, "onboarding_inicial", "Exibicao")
        send_menu(
            telegram_id,
            "Olá! Eu sou o *Colossos*, seu agente esportivo 💪\n\n"
            "Vou te ajudar a montar seu treino e sua dieta personalizados.\n\n"
            "Vamos começar?",
            ["Sim", "Não"],
        )
        return

    # ------------------------------------------------------------------
    # NOME — processa resposta ao "Vamos começar?"
    # ------------------------------------------------------------------
    if step == STEP_NOME:
        resp = text.strip().lower()
        if resp == "não":
            log_action(db, telegram_id, "onboarding_inicial_Selecao", "Selecao", "Não")
            send_message(telegram_id, "Sem problemas! 😊 Quando quiser, é só me chamar.")
            return

        log_action(db, telegram_id, "onboarding_inicial_Selecao", "Selecao", "Sim")
        log_action(db, telegram_id, "nome_exibicao", "Exibicao")
        send_message(telegram_id, "Ótimo! 🎉 Como você quer ser chamado?")
        user_ref.set({"onboarding_step": STEP_NOME_AGUARDA}, merge=True)
        return

    # ------------------------------------------------------------------
    # NOME — aguarda digitação
    # ------------------------------------------------------------------
    if step == STEP_NOME_AGUARDA:
        result = _parse_nome(text)
        if not result["ok"]:
            send_message(telegram_id, result["error"])
            return
        nome = result["value"]
        log_action(db, telegram_id, "nome_Selecao", "Input", nome)
        user_ref.set({"name": nome, "onboarding_step": STEP_OBJETIVO}, merge=True)

        log_action(db, telegram_id, "objetivo_exibicao", "Exibicao")
        send_menu(
            telegram_id,
            f"Prazer, *{nome}*! 💪\n\nQual é o seu objetivo?",
            ["Hipertrofia", "Emagrecimento", "Ganho de Massa"],
        )
        return

    # ------------------------------------------------------------------
    # OBJETIVO
    # ------------------------------------------------------------------
    if step == STEP_OBJETIVO:
        result = _parse_option(text, OBJETIVO_MAP)
        if not result["ok"]:
            send_menu(telegram_id, result["error"] + "\n\nQual é o seu objetivo?",
                      ["Hipertrofia", "Emagrecimento", "Ganho de Massa"])
            return
        log_action(db, telegram_id, "objetivo_Selecao", "menu_selecao", result["value"])
        user_ref.set({"goal": result["value"], "onboarding_step": STEP_ALTURA}, merge=True)

        log_action(db, telegram_id, "altura_exibicao", "Exibicao")
        send_message(telegram_id, "Qual a sua altura em centímetros?\n_Exemplo: 178_")
        return

    # ------------------------------------------------------------------
    # ALTURA
    # ------------------------------------------------------------------
    if step == STEP_ALTURA:
        result = _parse_altura(text)
        if not result["ok"]:
            send_message(telegram_id, result["error"])
            return
        log_action(db, telegram_id, "altura_Selecao", "Input", result["value"])
        user_ref.set({"height_cm": result["value"], "onboarding_step": STEP_PESO}, merge=True)

        log_action(db, telegram_id, "peso_exibicao", "Exibicao")
        send_message(telegram_id, "Qual o seu peso em quilogramas?\n_Exemplo: 83_")
        return

    # ------------------------------------------------------------------
    # PESO
    # ------------------------------------------------------------------
    if step == STEP_PESO:
        result = _parse_peso(text)
        if not result["ok"]:
            send_message(telegram_id, result["error"])
            return
        log_action(db, telegram_id, "peso_Selecao", "Input", result["value"])
        user_ref.set({"weight_kg": result["value"], "onboarding_step": STEP_IDADE}, merge=True)

        log_action(db, telegram_id, "idade_exibicao", "Exibicao")
        send_message(telegram_id, "Qual a sua idade?\n_Exemplo: 25_")
        return

    # ------------------------------------------------------------------
    # IDADE
    # ------------------------------------------------------------------
    if step == STEP_IDADE:
        result = _parse_idade(text)
        if not result["ok"]:
            send_message(telegram_id, result["error"])
            return
        log_action(db, telegram_id, "idade_Selecao", "Input", result["value"])
        user_ref.set({"age": result["value"], "onboarding_step": STEP_CONFIRMACAO}, merge=True)

        # Recarrega data com a idade recém-gravada para exibir no resumo
        updated_data = {**data, "age": result["value"]}
        log_action(db, telegram_id, "confirmacao_exibicao", "Exibicao")
        send_menu(
            telegram_id,
            _build_confirmation_text(updated_data),
            ["Confirmar", "Recomeçar"],
        )
        return

    # ------------------------------------------------------------------
    # CONFIRMAÇÃO
    # ------------------------------------------------------------------
    if step == STEP_CONFIRMACAO:
        resp = text.strip().lower()

        if resp == "recomeçar":
            log_action(db, telegram_id, "confirmacao_Selecao", "menu_selecao", "Recomeçar")
            # Apaga dados do perfil e reinicia do nome
            user_ref.set(
                {
                    "name": None, "goal": None, "height_cm": None,
                    "weight_kg": None, "age": None,
                    "onboarding_step": STEP_NOME,
                },
                merge=True,
            )
            log_action(db, telegram_id, "nome_exibicao", "Exibicao")
            send_message(telegram_id, "Tudo bem, vamos recomeçar! 🔄\n\nComo você quer ser chamado?")
            user_ref.set({"onboarding_step": STEP_NOME_AGUARDA}, merge=True)
            return

        if resp != "confirmar":
            send_menu(telegram_id, "❌ Use os botões para confirmar ou recomeçar.",
                      ["Confirmar", "Recomeçar"])
            return

        now = _now_utc()
        log_action(db, telegram_id, "confirmacao_Selecao", "menu_selecao", "Confirmar")
        user_ref.set(
            {
                "onboarding_step":       STEP_CONCLUIDO,
                "onboarding_complete":   True,
                "onboarding_created_at": now,
                "onboarding_updated_at": now,
            },
            merge=True,
        )
        log_action(db, telegram_id, "onboarding_concluido", "Concluido")

        nome = data.get("name", "")
        send_message(
            telegram_id,
            f"Perfeito, *{nome}*! 🙌\n\n"
            "Recebi todas as suas informações básicas.\n"
            "A partir daqui posso te ajudar a montar seu treino e sua dieta de forma personalizada.",
        )
        send_main_menu(telegram_id, db, nome)
        return

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    user_ref.set({"onboarding_step": STEP_WELCOME}, merge=True)
    send_message(telegram_id, "Ops, algo deu errado. Vamos recomeçar! 🔄")