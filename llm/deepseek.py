import httpx
import json
import os
from typing import AsyncGenerator

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
API_KEY        = os.getenv("DEEPSEEK_API_KEY", "")

# ── Singleton HTTP client (instanciated once at startup) ──────────────────────
_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialized. Call init_http_client() at startup.")
    return _client


def init_http_client():
    global _client
    _client = httpx.AsyncClient(
        base_url=DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://naps.ma",
            "X-Title": "Chatbot NAPS",
        },
        timeout=httpx.Timeout(30.0, read=60.0),
    )
    print("[OK] HTTP client initialized")


async def close_http_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


# ── Core call (non-streaming) ─────────────────────────────────────────────────

async def call_llm(messages: list[dict], max_tokens: int = 800) -> str:
    """Non-streaming LLM call. Returns full response text with automatic free fallback."""
    client = get_http_client()
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }
    try:
        resp = await client.post("chat/completions", json=payload)
        if resp.status_code == 402:
            print("[WARNING] OpenRouter 402 Payment Required: Insufficient balance. Retrying with free model...")
            payload["model"] = "google/gemma-4-31b-it:free"
            resp = await client.post("chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] OpenRouter API error ({e.response.status_code}): {e.response.text}")
        if e.response.status_code in [402, 404, 429, 502, 503]:
            # Try once more with free model as absolute backup
            try:
                payload["model"] = "google/gemma-4-26b-a4b-it:free"
                resp = await client.post("chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as ex:
                print(f"[ERROR] Free model fallback failed: {ex}")
            return "Désolé, le service de chat est temporairement indisponible (Solde OpenRouter insuffisant)."
        return "Désolé, le service de chat rencontre des difficultés techniques avec l'API OpenRouter."
    except json.JSONDecodeError:
        print(f"[ERROR] OpenRouter returned invalid JSON")
        return "Désolé, le service de chat a reçu une réponse invalide."
    except Exception as e:
        print(f"[ERROR] OpenRouter call failed: {e}")
        # Try once more with free model as absolute backup
        try:
            payload["model"] = "openrouter/free"
            resp = await client.post("chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as ex:
            print(f"[ERROR] Free model fallback failed: {ex}")
        return "Désolé, le service de chat rencontre des difficultés de connexion."


async def call_llm_short(prompt: str, max_tokens: int = 150) -> str:
    """Short call for classification / reranking — temp=0, fast."""
    client = get_http_client()
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False,
    }
    try:
        resp = await client.post("chat/completions", json=payload)
        if resp.status_code in [402, 404, 429, 502, 503]:
            print("[WARNING] OpenRouter 402 in short call. Retrying with free model...")
            payload["model"] = "google/gemma-4-31b-it:free"
            resp = await client.post("chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ERROR] Short call error: {e}")
        # Final absolute fallback
        try:
            payload["model"] = "google/gemma-4-26b-a4b-it:free"
            resp = await client.post("chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            raise e


# ── Streaming call ────────────────────────────────────────────────────────────

async def stream_llm(messages: list[dict], max_tokens: int = 800) -> AsyncGenerator[str, None]:
    """
    Streaming LLM call via SSE.
    Yields text chunks as they arrive from DeepSeek or Gemma fallback.
    """
    client = get_http_client()
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": True,
    }
    try:
        async with client.stream("POST", "chat/completions", json=payload) as response:
            if response.status_code == 402:
                print("[WARNING] OpenRouter 402: Insufficient balance. Retrying stream with free model google/gemma-4-31b-it:free...")
                payload["model"] = "google/gemma-4-31b-it:free"
                # Open new stream with free model
                async with client.stream("POST", "chat/completions", json=payload) as fallback_response:
                    if fallback_response.status_code in [402, 404, 429, 502, 503]:
                        print("[WARNING] Primary free fallback failed. Trying gemma-4-26b-a4b-it:free (non-streaming)...")
                        payload["model"] = "google/gemma-4-26b-a4b-it:free"
                        payload["stream"] = False
                        try:
                            resp = await client.post("chat/completions", json=payload)
                            resp.raise_for_status()
                            data = resp.json()
                            text = data["choices"][0]["message"]["content"].strip()
                            if text:
                                yield text
                            return
                        except Exception:
                            print("[WARNING] Secondary free fallback failed. Trying absolute final openrouter/free...")
                            payload["model"] = "openrouter/free"
                            try:
                                resp = await client.post("chat/completions", json=payload)
                                resp.raise_for_status()
                                data = resp.json()
                                text = data["choices"][0]["message"]["content"].strip()
                                if text:
                                    yield text
                                return
                            except Exception:
                                yield "Le réseau est très chargé. Pouvez-vous répéter votre message dans quelques instants ?"
                                return

                    fallback_response.raise_for_status()
                    async for line in fallback_response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError):
                            continue
                return

            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:].strip()
                if raw == "[DONE]":
                    break
                try:
                    chunk = json.loads(raw)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError):
                    continue
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] stream_llm status error: {e}")
        if e.response.status_code == 402:
            yield "Désolé, le service de chat est temporairement indisponible (Solde OpenRouter insuffisant)."
        else:
            yield "Désolé, le service de chat rencontre des difficultés techniques (Erreur HTTP)."
    except Exception as e:
        print(f"[ERROR] stream_llm error: {e}")
        yield "Désolé, le service de chat rencontre des difficultés de connexion."

