"""
Adaptador Telegram.
Todo código específico do Telegram fica isolado aqui.
Para migrar para WhatsApp: crie whatsapp_adapter.py com send_text() e send_buttons(),
depois atualize o import em messenger.py.
"""
import os
import requests

_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_API   = f"https://api.telegram.org/bot{_TOKEN}"


def send_text(chat_id: str, text: str) -> None:
    """Envia mensagem de texto simples com suporte a Markdown."""
    try:
        requests.post(
            f"{_API}/sendMessage",
            json={
                "chat_id":    chat_id,
                "text":       text,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[telegram] send_text error: {e}")


def send_buttons(chat_id: str, text: str, options: list[str]) -> None:
    """Envia mensagem com teclado de botões (ReplyKeyboardMarkup).

    Cada opção vira um botão. O teclado some após o usuário tocar
    (one_time_keyboard=True) e é redimensionado ao conteúdo.
    """
    keyboard = [[{"text": opt}] for opt in options]
    try:
        requests.post(
            f"{_API}/sendMessage",
            json={
                "chat_id":      chat_id,
                "text":         text,
                "parse_mode":   "Markdown",
                "reply_markup": {
                    "keyboard":          keyboard,
                    "resize_keyboard":   True,
                    "one_time_keyboard": True,
                },
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[telegram] send_buttons error: {e}")


def remove_keyboard(chat_id: str, text: str) -> None:
    """Remove o teclado customizado após coleta de dados livres."""
    try:
        requests.post(
            f"{_API}/sendMessage",
            json={
                "chat_id":      chat_id,
                "text":         text,
                "parse_mode":   "Markdown",
                "reply_markup": {"remove_keyboard": True},
            },
            timeout=10,
        )
    except Exception as e:
        print(f"[telegram] remove_keyboard error: {e}")