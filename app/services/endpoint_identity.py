from __future__ import annotations

from typing import Optional


def build_endpoint_urn(
    service_name: Optional[str],
    endpoint_name: Optional[str],
) -> Optional[str]:
    if not service_name or not endpoint_name:
        return None
    return f"urn:endpoint:{service_name}:{endpoint_name}"
