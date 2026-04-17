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
    log_action(db, telegram_id, "menu_principal_exibicao", "Exibicao")
    send_message(
        telegram_id,
        f"{nome if nome else ''} me diga rapidamente o que você quer fazer.\n"
        "Posso te ajudar com dieta, treino e edição de perfil.\n\n"
        "Se quiser ver todas as opções, digite *!help*.\n"
        "Ou, se preferir navegar com botões, digite *!botoes*."
    )

# ---------------------------------------------------------------------------
# Menu secundario
# ---------------------------------------------------------------------------
def send_main_menu_secundary(telegram_id: str, db, nome: str = "") -> None:
    """Menu Secundario exibido caso o usuario tenha dificuldade com a digitação"""
    greeting = f", *{nome}*" if nome else ""
    log_action(db, telegram_id, "menu_secundario_exibicao", "Exibicao")
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


# ---------------------------------------------------------------------------
# Mensagem de ajuda com !help
# ---------------------------------------------------------------------------

def send_help_message(telegram_id: str, nome: str = "") -> None:
    """Lista todas as funcionalidades disponíveis. Acionada por !help ou intent ajuda."""
    greeting = f"*{nome}*, aqui" if nome else "Aqui"
    send_message(
        telegram_id,
        f"{greeting} está tudo que posso fazer por você:\n\n"
        "🥗 *Dieta*\n"
        "→ _\"montar minha dieta\"_, _\"quero um plano alimentar\"_\n\n"
        "💪 *Treino*\n"
        "→ _\"montar meu treino\"_, _\"quero ir à academia\"_\n\n"
        "✏️ *Editar perfil*\n"
        "→ _\"editar perfil\"_ — abre o menu completo\n"
        "→ _\"mudar minha idade para 28\"_ — vai direto ao campo\n"
        "→ _\"alterar meu peso\"_, _\"trocar meu objetivo\"_ etc.\n\n"
        "É só me dizer o que quer! 😊",
    )