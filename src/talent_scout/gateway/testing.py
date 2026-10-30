from talent_scout.gateway.types import Fetch, FetchResult


class FakeGateway:
    """Returns canned FetchResults in order and records the Fetches it was given."""

    def __init__(self, results: list[FetchResult]):
        self._results = list(results)
        self.fetches: list[Fetch] = []

    async def __aenter__(self) -> "FakeGateway":
        return self

    async def __aexit__(self, *exc) -> None:
        pass

    async def fetch(self, f: Fetch) -> FetchResult:
        self.fetches.append(f)
        return self._results.pop(0)
