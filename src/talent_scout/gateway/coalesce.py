import re

from talent_scout.kernel.types import Posting, Source


def _words(text: str | None) -> list[str]:
    return re.sub(r"\W+", " ", (text or "").lower()).split()


def _key(p: Posting):
    # Best first: USAJOBS (close date, full text, real pay), then newest, then lowest key.
    return (p.source != Source.usajobs, -p.posted_at.toordinal(), p.key)


def _agree(a: list[str], b: list[str]) -> bool:
    short, long = sorted((a, b), key=len)
    return long[: len(short)] == short


def _same_pay(a: Posting, b: Posting) -> bool:
    return a.salary == b.salary or any(p.salary and p.salary.predicted for p in (a, b))


def coalesce(postings: list[Posting]) -> tuple[list[Posting], dict[str, list[str]]]:
    # The trailing word is dropped because a truncated snippet may end mid-word.
    norm = [(_words(p.title), _words(p.company), _words(p.description)[:-1]) for p in postings]
    kept: list[int] = []
    merged: dict[str, list[str]] = {}
    # ponytail: pairwise scan against survivors, fine for a few hundred Postings.
    for i in sorted(range(len(postings)), key=lambda i: _key(postings[i])):
        for j in kept:
            if norm[i][:2] == norm[j][:2] and _agree(norm[i][2], norm[j][2]) and _same_pay(postings[i], postings[j]):
                merged.setdefault(postings[j].key, []).append(postings[i].key)
                break
        else:
            kept.append(i)
    return [postings[i] for i in sorted(kept)], merged
