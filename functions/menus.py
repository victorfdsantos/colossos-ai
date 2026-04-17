"""
Menus do Colossos.

Todos os menus centralizados aqui.
Para adicionar um novo menu: crie a função send_* e importe onde precisar.
O main.py e outros módulos só chamam funções deste arquivo — nunca montam
listas de opções diretamente.
"""

from messenger import send_menu, send_message
from action_logger import log_action

# ---------------------------------------------------------------------------
# Rótulos canônicos — use estas constantes para comparar no main.py
# e em qualquer módulo que precise detectar a opção escolhida.
# ---------------------------------------------------------------------------

# Menu principal
OPT_MONTAR_DIETA   = "montar dieta"
OPT_MONTAR_TREINO  = "montar plano de treino"
OPT_EDITAR_PERFIL  = "editar perfil"

# Menu editar perfil
OPT_EDIT_NOME      = "alterar nome"
OPT_EDIT_IDADE     = "alterar idade"
OPT_EDIT_PESO      = "alterar peso"
OPT_EDIT_ALTURA    = "alterar altura"
OPT_EDIT_OBJETIVO  = "alterar objetivo"
OPT_EDIT_VOLTAR    = "voltar"


# ---------------------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------------------

def send_main_menu(telegram_id: str, db, nome: str = "") -> None:
    """Menu principal exibido após onboarding e ao retornar de qualquer fluxo."""
    greeting = f", *{nome}*" if nome else ""
    log_action(db, telegram_id, "menu_principal_exibicao", "Exibicao")
    send_menu(
        telegram_id,
        f"O que você gostaria de fazer{greeting}?",
        ["Montar Dieta", "Montar Plano de Treino", "Editar Perfil"],
    )


# ---------------------------------------------------------------------------
# Menu de edição de perfil
# ---------------------------------------------------------------------------

def send_edit_profile_menu(telegram_id: str, db) -> None:
    """Menu com os campos do onboarding que o usuário pode editar."""
    log_action(db, telegram_id, "menu_editar_perfil_exibicao", "Exibicao")
    send_menu(
        telegram_id,
        "✏️ O que deseja alterar?",
        ["Alterar Nome", "Alterar Idade", "Alterar Peso", "Alterar Altura", "Alterar Objetivo", "Voltar"],
    )


# ---------------------------------------------------------------------------
# Mensagem de opção inválida genérica (reutilizável)
# ---------------------------------------------------------------------------

def send_invalid_option(telegram_id: str) -> None:
    send_message(telegram_id, "❌ Opção não reconhecida. Por favor, use os botões disponíveis.")