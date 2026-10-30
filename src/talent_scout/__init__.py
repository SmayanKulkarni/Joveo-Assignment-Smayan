import os

# LangGraph reads this once at import, and any talent_scout.* import runs this file first.
os.environ["LANGGRAPH_STRICT_MSGPACK"] = "true"
