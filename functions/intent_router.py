"""
Roteador de intenção do Colossos.

Usa o Gemini para classificar o que o usuário quer fazer com base
em linguagem natural, eliminando a necessidade de botões no menu principal.

Retorna uma intent canônica (str) ou None se não reconheceu.
"""

import json
from helpers import call_gemini

# ---------------------------------------------------------------------------
# Intents disponíveis — adicione aqui quando criar novos fluxos
# ---------------------------------------------------------------------------
INTENT_MONTAR_DIETA    = "montar_dieta"
INTENT_MONTAR_TREINO   = "montar_treino"
INTENT_EDITAR_PERFIL   = "editar_perfil"

# Sub-intents de edição de perfil — levam direto ao campo
INTENT_EDITAR_NOME     = "editar_nome"
INTENT_EDITAR_IDADE    = "editar_idade"
INTENT_EDITAR_PESO     = "editar_peso"
INTENT_EDITAR_ALTURA   = "editar_altura"
INTENT_EDITAR_OBJETIVO = "editar_objetivo"

INTENT_AJUDA           = "ajuda"
INTENT_NAVEGACAO       = "navegacao" 
INTENT_OLA             = "ola"
INTENT_TEXTO_LONGO     = "texto_longo"
INTENT_DESCONHECIDO    = "desconhecido"

# ---------------------------------------------------------------------------
# Descrição das intents para o prompt
# ---------------------------------------------------------------------------
_INTENT_DESCRIPTIONS = """
- montar_dieta: usuário quer criar, montar ou ver sua dieta / plano alimentar
- montar_treino: usuário quer criar, montar ou ver seu treino / plano de treino / academia
- editar_perfil: usuário quer editar ou alterar dados do perfil (sem especificar qual campo)
- editar_nome: usuário quer alterar especificamente o nome
- editar_idade: usuário quer alterar especificamente a idade
- editar_peso: usuário quer alterar especificamente o peso
- editar_altura: usuário quer alterar especificamente a altura
- editar_objetivo: usuário quer alterar especificamente o objetivo (hipertrofia, emagrecimento etc)
- ola: quando o usuario mandar um ola, oi, bom dia ou algo relacionado a uma primeira interação do dia
- desconhecido: nenhuma das anteriores
"""

_SYSTEM_PROMPT = f"""Você é um classificador de intenções para um bot de academia chamado Colossos.
Dado o texto do usuário, retorne SOMENTE um objeto JSON com a chave "intent" contendo
exatamente um dos valores abaixo (sem explicação, sem markdown):

{_INTENT_DESCRIPTIONS}

Exemplos:
- "quero fazer minha dieta" → {{"intent": "montar_dieta"}}
- "muda minha idade para 28" → {{"intent": "editar_idade"}}
- "o que você faz?" → {{"intent": "ajuda"}}
- "oi" → {{"intent": "desconhecido"}}
"""


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def classify_intent(text: str) -> str:
    """
    Classifica a intenção do usuário.

    Args:
        text: Mensagem do usuário.

    Returns:
        Uma das constantes INTENT_* definidas acima.
    """
    prompt = f"{_SYSTEM_PROMPT}\n\nTexto do usuário: {text}"
    if len(text) < 300:
        if text == "!help": 
            return INTENT_AJUDA
        elif text == "!botoes":
            return INTENT_NAVEGACAO
        else:
            try:
                raw = call_gemini(prompt, temperature=0.0, max_tokens=50)
                # Remove possíveis blocos de código que o modelo insira mesmo pedindo para não
                clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                data = json.loads(clean)
                intent = data.get("intent", INTENT_DESCONHECIDO)

                # Garante que só retorna intents conhecidas
                known = {
                    INTENT_MONTAR_DIETA, INTENT_MONTAR_TREINO,
                    INTENT_EDITAR_PERFIL,
                    INTENT_EDITAR_NOME, INTENT_EDITAR_IDADE, INTENT_EDITAR_PESO,
                    INTENT_EDITAR_ALTURA, INTENT_EDITAR_OBJETIVO, INTENT_OLA, INTENT_DESCONHECIDO,
                }
                return intent if intent in known else INTENT_DESCONHECIDO

            except Exception as e:
                print(f"[intent_router] classify error: {e} | raw: {raw!r}")
                return INTENT_DESCONHECIDO
    else:
        return INTENT_TEXTO_LONGO