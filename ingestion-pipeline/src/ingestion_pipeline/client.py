import os
from typing import Optional


def get_client(base_url: str, default_headers: Optional[dict] = None):
    """
    Get a gateway client based on the implementation of the service.

    Thius is wrong we should think more about this and discuss in meeting.
    """
    headers = default_headers or {}
    if os.getenv("CLIENT_DEPENDENCY", "llama-stack") == "ogx-ai":
        from ogx_client import OgxClient

        return OgxClient(base_url=base_url, default_headers=headers)

    from llama_stack_client import LlamaStackClient

    return LlamaStackClient(base_url=base_url, default_headers=headers)
