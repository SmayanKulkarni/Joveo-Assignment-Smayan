from langgraph.config import get_stream_writer


def emit(event: dict) -> None:
    try:
        get_stream_writer()(event)
    except RuntimeError:  # the Gateway and Tiers also run outside a graph, in tests and smokes
        pass
