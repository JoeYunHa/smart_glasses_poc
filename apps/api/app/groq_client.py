# Compatibility shim — source modules now import from app.llm_client directly.
# Tests that patch 'app.groq_client.call_vlm' continue to work through this re-export.
from app.llm_client import call_vlm as call_vlm  # noqa: F401
