from typing import Literal, get_args

Placement = Literal["clarity", "relevance", "critic"]
PLACEMENTS = get_args(Placement)

# Untuned: every cut starts at 0.5 until the evals/jev sweep exists (docs/lld/future-scope.md).
# Keys are matched as prefixes of the model id Jev returns, which is a dated snapshot.
CUTS: dict[str, dict[Placement, float]] = {
    "typesafe/jev-1.14": {"clarity": 0.5, "relevance": 0.5, "critic": 0.5},
    "llm:cheap": {"clarity": 0.5, "relevance": 0.5, "critic": 0.5},
}


class UnknownJevModel(LookupError):
    pass


def cut_for(cuts: dict[str, dict[Placement, float]], model: str, placement: Placement) -> float:
    # Longest prefix wins so a more specific key can override a shorter one.
    key = max((k for k in cuts if model.startswith(k)), key=len, default=None)
    if key is None:
        raise UnknownJevModel(f"no cut configured for Jev model '{model}'")
    return cuts[key][placement]
