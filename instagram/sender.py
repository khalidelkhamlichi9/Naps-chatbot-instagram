import os
import httpx

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID", "")

_PLACEHOLDERS = frozenset({
    "",
    "your_page_access_token_here",
    "your_instagram_page_id_here",
    "your_page_id",
})


def _graph_base_url() -> str:
    """Instagram Login tokens (IGA…) use graph.instagram.com; Page tokens use Facebook Graph."""
    if ACCESS_TOKEN.startswith("IGA") or ACCESS_TOKEN.startswith("IG"):
        return "https://graph.instagram.com/v21.0"
    return "https://graph.facebook.com/v21.0"


def credentials_ready() -> bool:
    return (
        ACCESS_TOKEN not in _PLACEHOLDERS
        and PAGE_ID not in _PLACEHOLDERS
    )


_sender_client: httpx.AsyncClient | None = None


def init_sender_client():
    global _sender_client
    _sender_client = httpx.AsyncClient(
        base_url=_graph_base_url(),
        timeout=httpx.Timeout(15.0),
    )


async def close_sender_client():
    global _sender_client
    if _sender_client:
        await _sender_client.aclose()
        _sender_client = None


async def send_instagram_message(recipient_id: str, text: str) -> bool:
    """Send a text DM via Instagram Graph API."""
    if not _sender_client:
        print("[WARN] Sender client not initialized")
        return False

    if not credentials_ready():
        print(
            "[ERROR] INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_PAGE_ID missing in .env"
        )
        return False

    chunks = _split_message(text, max_length=1000)

    for chunk in chunks:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": chunk},
        }
        # Instagram Login API
        if ACCESS_TOKEN.startswith("IGA") or ACCESS_TOKEN.startswith("IG"):
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            params = None
        else:
            headers = None
            params = {"access_token": ACCESS_TOKEN}

        # Instagram Login tokens: POST /me/messages (doc Meta IG API)
        path = "/me/messages" if (ACCESS_TOKEN.startswith("IGA") or ACCESS_TOKEN.startswith("IG")) else f"/{PAGE_ID}/messages"

        try:
            resp = await _sender_client.post(
                path,
                json=payload,
                params=params,
                headers=headers,
            )
            if resp.status_code != 200:
                print(f"[ERROR] Instagram send error: {resp.status_code} — {resp.text}")
                return False
        except httpx.HTTPError as e:
            print(f"[ERROR] Instagram HTTP error: {e}")
            return False

    return True


def _split_message(text: str, max_length: int = 1000) -> list[str]:
    if len(text) <= max_length:
        return [text]

    parts = []
    while len(text) > max_length:
        split_at = text.rfind(". ", 0, max_length)
        if split_at == -1:
            split_at = max_length
        parts.append(text[:split_at + 1].strip())
        text = text[split_at + 1:].strip()

    if text:
        parts.append(text)
    return parts
