import hashlib
import sqlite3
from functools import lru_cache
from pathlib import Path

from langchain_core.caches import RETURN_VAL_TYPE, BaseCache
from langchain_core.globals import set_llm_cache
from langchain_core.load import dumps, loads

from talent_scout.kernel.settings import Settings


class _LLMCache(BaseCache):
    def __init__(self, db: sqlite3.Connection):
        self._db = db

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        row = self._db.execute("SELECT response FROM llm WHERE prompt=? AND llm=?", (prompt, llm_string)).fetchone()
        return loads(row[0], allowed_objects="core") if row else None

    def update(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        self._db.execute("INSERT OR REPLACE INTO llm VALUES (?, ?, ?)", (prompt, llm_string, dumps(list(return_val))))
        self._db.commit()

    def clear(self, **kwargs) -> None:
        self._db.execute("DELETE FROM llm")
        self._db.commit()

    # SQLite is local and fast, so skip the default thread-pool hop for async callers.
    async def alookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        return self.lookup(prompt, llm_string)

    async def aupdate(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        self.update(prompt, llm_string, return_val)

    async def aclear(self, **kwargs) -> None:
        self.clear()


class Replay:
    """One SQLite file holding recorded LLM and Jev responses."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS llm (prompt TEXT, llm TEXT, response TEXT, PRIMARY KEY (prompt, llm));"
            "CREATE TABLE IF NOT EXISTS jev (chain TEXT, request_sha TEXT, response TEXT, PRIMARY KEY (chain, request_sha));"
        )
        self.llm = _LLMCache(self._db)

    def get_jev(self, chain: str, request_json: str) -> str | None:
        row = self._db.execute("SELECT response FROM jev WHERE chain=? AND request_sha=?", (chain, _sha(request_json))).fetchone()
        return row[0] if row else None

    def put_jev(self, chain: str, request_json: str, response_json: str) -> None:
        self._db.execute("INSERT OR REPLACE INTO jev VALUES (?, ?, ?)", (chain, _sha(request_json), response_json))
        self._db.commit()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# Cached per path so the LLM cache and Jev share one connection.
@lru_cache
def open_replay(path: Path) -> Replay:
    return Replay(path)


def install_llm_cache(settings: Settings) -> None:
    # Unset means off: touch nothing, so no file is created and no cache is installed.
    if settings.replay_cache is not None:
        set_llm_cache(open_replay(settings.replay_cache).llm)
