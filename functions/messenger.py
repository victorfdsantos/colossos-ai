"""
Camada de abstração de mensageiro.
Para trocar Telegram por WhatsApp (ou outro canal), basta:
  1. Criar whatsapp.py com as mesmas funções
  2. Alterar o import em messenger.py
  3. Nenhum outro arquivo precisa mudar.
"""
from telegram_adapter import send_text, send_buttons

def send_message(chat_id: str, text: str) -> None:
    """Envia mensagem de texto simples."""
    send_text(chat_id, text)

def send_menu(chat_id: str, text: str, options: list[str]) -> None:
    """Envia mensagem com opções de botão.
    
    Args:
        chat_id: ID do destinatário.
        text: Texto exibido acima dos botões.
        options: Lista de rótulos dos botões.
    """
    send_buttons(chat_id, text, options)