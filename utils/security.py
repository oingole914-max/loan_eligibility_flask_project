"""Small security helpers used by authentication routes."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse


def is_safe_redirect_url(target: str | None, host_url: str) -> bool:
    """Allow only redirects to the same application host."""
    if not target:
        return False
    target = target.replace("\\", "")
    reference = urlparse(host_url)
    candidate = urlparse(urljoin(host_url, target))
    return (
        candidate.scheme in {"http", "https"}
        and reference.netloc == candidate.netloc
        and bool(candidate.path)
    )
