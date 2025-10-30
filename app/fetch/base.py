from dataclasses import dataclass
from typing import Optional

@dataclass
class FetchResult:
    url: str
    status_code: int
    final_url: str
    html: Optional[str]
    text: Optional[str]
    fetched_at: str  # ISO 8601

class BaseFetcher:
    def fetch(self, url: str, timeout_sec: int = 15) -> FetchResult:
        raise NotImplementedError
