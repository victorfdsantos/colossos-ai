"""
Registro de histórico de ações no Firestore.

Módulo separado para que onboarding.py, diet_setup.py e training_setup.py
possam importar sem criar dependências circulares.
"""

from datetime import datetime, timezone


def log_action(db, telegram_id: str, category: str, action: str, value=None) -> None:
    """Salva um passo em users/{id}/onboarding_history.

    Args:
        db:          Cliente Firestore.
        telegram_id: ID do usuário.
        category:    Nome da tela/etapa (ex: "nome_exibicao").
        action:      Tipo da ação ("Exibicao", "Input", "menu_selecao", ...).
        value:       Valor capturado (opcional).
    """
    db.collection("users").document(telegram_id) \
      .collection("onboarding_history") \
      .add({
          "category":  category,
          "action":    action,
          "value":     value,
          "timestamp": datetime.now(timezone.utc),
      })