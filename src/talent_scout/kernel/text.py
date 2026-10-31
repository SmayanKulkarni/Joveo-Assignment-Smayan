import re

LEGAL_SUFFIXES = frozenset({"inc", "llc", "ltd", "limited", "pvt", "private", "corp", "corporation", "co", "plc", "gmbh"})


def fold(s: str) -> str:
    # Keeps + and # so C, C++ and C# stay three skills.
    return " ".join(re.sub(r"[^\w+#]+", " ", s.casefold()).split())


def employer_key(company: str | None) -> str | None:
    words = fold(company or "").split()
    while len(words) > 1 and words[-1] in LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words) or None


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"
