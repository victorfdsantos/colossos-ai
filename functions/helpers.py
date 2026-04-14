import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def call_gemini(prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str:
    """Wrapper centralizado para todas as chamadas ao Gemini Flash."""
    try:
        import google.generativeai as genai
        import os

        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        return response.text
    except Exception as e:
        print(f"Gemini error: {e}")
        return "Desculpe, tive um problema ao processar sua pergunta. Tente novamente."

def send_telegram_message(chat_id: str, text: str) -> None:
    """Envia mensagem ao usuário via Telegram Bot API com suporte a Markdown."""
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"Telegram send error: {e}")
