import datetime as dt
import re
from typing import Optional
import requests
from bs4 import BeautifulSoup

from .base import BaseFetcher, FetchResult

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)

class RequestsFetcher(BaseFetcher):
    def fetch(self, url: str, timeout_sec: int = 15) -> FetchResult:
        headers = {"User-Agent": _USER_AGENT, "Accept-Language": "cs,en;q=0.8"}
        resp = requests.get(url, headers=headers, timeout=timeout_sec)
        final_url = str(resp.url)
        status = int(resp.status_code)

        html: Optional[str] = None
        text: Optional[str] = None

        if resp.ok and resp.text:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            raw_text = soup.get_text("\n")
            text = _normalize_text(raw_text)

        return FetchResult(
            url=url,
            status_code=status,
            final_url=final_url,
            html=html,
            text=text,
            fetched_at=dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )

def _normalize_text(s: str) -> str:
    s = re.sub(r"\u00a0", " ", s)          
    s = re.sub(r"[ \t\x0b\x0c\r]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)     
    return s.strip()
