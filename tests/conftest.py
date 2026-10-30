import os

# LangGraph reads this at import time, so it has to be set before any test module imports it.
os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")
