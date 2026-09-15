import os
import re
import json
import urllib.request
import urllib.error
import ollama

DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_MODEL = os.getenv("CHAT_MODEL", "llama3.2:1b")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def query_llm(
    messages: list[dict],
    temperature: float = 0.1,
    provider: str = None,
) -> str:
    """
    Unified LLM provider abstraction supporting Ollama (default), OpenAI, and Anthropic Claude.
    Falls back gracefully to local Ollama if API keys are unconfigured or placeholder.
    """
    prov = (provider or os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)).lower().strip()

    if prov in ("openai", "gpt"):
        return _query_openai(messages, temperature)
    elif prov in ("anthropic", "claude"):
        return _query_anthropic(messages, temperature)
    else:
        return _query_ollama(messages, temperature)


def _query_ollama(messages: list[dict], temperature: float) -> str:
    model_name = os.getenv("CHAT_MODEL", OLLAMA_MODEL)
    print(f"[LLM Provider] [OLLAMA CALL] Making call 1 of 1 to local Ollama (model='{model_name}', temperature={temperature})...")
    response = ollama.chat(
        model=model_name,
        messages=messages,
        options={
            "temperature": temperature,
            "num_ctx": 4096,
            "num_predict": 96,
        },
    )
    answer = response["message"]["content"].strip()
    return re.sub(r"<\|output\|>", "", answer).strip()


def _query_openai(messages: list[dict], temperature: float) -> str:
    api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY).strip()
    if not api_key or api_key.lower() in ("demo", "mock", "placeholder", "your_openai_api_key"):
        return _query_ollama(messages, temperature)

    try:
        url = "https://api.openai.com/v1/chat/completions"
        payload = json.dumps({
            "model": os.getenv("OPENAI_MODEL", OPENAI_MODEL),
            "messages": messages,
            "temperature": temperature,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            return re.sub(r"<\|output\|>", "", content).strip()
    except Exception as exc:
        print(f"[LLM Provider Warning] OpenAI request failed ({exc}). Falling back to Ollama.")
        return _query_ollama(messages, temperature)


def _query_anthropic(messages: list[dict], temperature: float) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY).strip()
    if not api_key or api_key.lower() in ("demo", "mock", "placeholder", "your_anthropic_api_key"):
        return _query_ollama(messages, temperature)

    try:
        url = "https://api.anthropic.com/v1/messages"
        system_content = ""
        user_messages = []

        for m in messages:
            if m["role"] == "system":
                system_content += m["content"] + "\n"
            else:
                user_messages.append({"role": m["role"], "content": m["content"]})

        payload_dict = {
            "model": os.getenv("ANTHROPIC_MODEL", ANTHROPIC_MODEL),
            "max_tokens": 2048,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_content.strip():
            payload_dict["system"] = system_content.strip()

        payload = json.dumps(payload_dict).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["content"][0]["text"].strip()
            return re.sub(r"<\|output\|>", "", content).strip()
    except Exception as exc:
        print(f"[LLM Provider Warning] Anthropic request failed ({exc}). Falling back to Ollama.")
        return _query_ollama(messages, temperature)
