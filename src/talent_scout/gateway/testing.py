from talent_scout.gateway.types import Fetch, FetchResult
from talent_scout.kernel.types import Source


class FakeGateway:
    """Returns canned FetchResults in order and records the Fetches it was given. An Exception in the list is raised instead."""

    def __init__(self, results: list[FetchResult | Exception]):
        self._results = list(results)
        self.fetches: list[Fetch] = []
        self.sources: list[Source] = []  # which source each Fetch was asked of
        self.left: dict[Source, int | None] = {}  # settable; a source not listed is unmetered

    async def __aenter__(self) -> "FakeGateway":
        return self

    async def __aexit__(self, *exc) -> None:
        pass

    def calls_left(self, source: Source) -> int | None:
        return self.left.get(source)

    async def fetch(self, f: Fetch, source: Source) -> FetchResult:
        self.fetches.append(f)
        self.sources.append(source)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
