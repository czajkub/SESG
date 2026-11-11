# /// script
# requires-python = ">=3.11"
# dependencies = ["lemminflect", "openpyxl"]
# ///
"""Generate data/nouns.csv: common English nouns with plural, countability and a/an.

Run:  uv run scripts/gen_nouns.py

Pipeline (raw sources are downloaded into data/raw/ only if missing; that dir is gitignored):

1. Selection + frequency order - NGSL 1.2, top LIMIT lemmas whose dominant PoS in
   SUBTLEX-US is "Noun" (same as gen_verbs.py).
2. Wiktionary noun entries - per-word files from kaikki.org (the full noun dump is
   1.9 GB, so only the selected words are fetched; only their English noun entries
   are cached in data/raw/kaikki-nouns/).
3. Countability - two signals from Wiktionary:
   a) the headword line of the first noun entry,
      e.g. "water (countable and uncountable, plural waters)":
          countable                       -> countable    (a dog, dogs)
          uncountable                     -> uncountable  (information; no a/an, no plural)
          countable and uncountable       -> both         (a coffee / coffee)
          plural only (en-plural noun)    -> plural_only  (clothes)
      plus: main sense "plural of X" or "normally plural"
                                          -> plural_only  (people, police, data: plural verb)
   b) the countability tags of the main (first non-archaic) sense.
   Combined conservatively: a use is allowed only if both allow it (the headword says
   "both" for boy/house because of rare senses; water's main sense is uncountable).
4. Plural - Wiktionary headword plural; lemminflect as fallback.
5. use_an - true if the word starts with a vowel *sound*, from Wiktionary IPA
   (an hour, a university); spelling-based fallback if no IPA is available.
"""

import csv
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from lemminflect import getInflection

from sources import RAW, ROOT, USER_AGENT, ngsl_lemmas, subtlex_dominant_pos

LIMIT = 500  # how many of the most frequent nouns to process

OUT = ROOT / "data" / "nouns.csv"
CACHE = RAW / "kaikki-nouns"
KAIKKI_WORD_URL = "https://kaikki.org/dictionary/English/meaning/{a}/{ab}/{word}.jsonl"

SKIP_SENSE_TAGS = {
    "obsolete", "archaic", "rare", "dialectal", "nonstandard", "dated",
    "form-of", "alt-of", "humorous", "nonce-word",
}
USES = {"countable": {"countable"}, "uncountable": {"uncountable"},
        "both": {"countable", "uncountable"}}
# only these fields are cached; full entries carry megabytes of translations
KEEP_KEYS = ("word", "pos", "lang_code", "etymology_number", "head_templates", "forms", "sounds")

IPA_VOWELS = set("aeiouæɑɒɔəɛɜɪʊʌɐøœɘɵɞɨʉɯɤ")
IPA_SKIP = set("/[ˈˌ.(")


def slim(entry: dict) -> dict:
    out = {k: entry[k] for k in KEEP_KEYS if k in entry}
    out["senses"] = [{"tags": s["tags"]} if "tags" in s else {} for s in entry.get("senses", [])]
    return out


def wiktionary_nouns(word: str) -> list[dict]:
    """English noun entries for `word`, fetched once and cached."""
    path = CACHE / f"{word}.jsonl"
    if not path.exists():
        url = KAIKKI_WORD_URL.format(a=word[0], ab=word[:2], word=word)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req) as resp:
                lines = resp.read().decode("utf-8").splitlines()
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            lines = []
        keep = [slim(e) for l in lines
                if (e := json.loads(l)).get("lang_code") == "en" and e.get("pos") == "noun"]
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(e) + "\n" for e in keep), encoding="utf-8")
        time.sleep(0.2)  # be polite to kaikki.org
    entries = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    entries.sort(key=lambda e: e.get("etymology_number") or 0)
    return entries


def headword(entries: list[dict]) -> tuple[str, str] | None:
    """(template name, expansion) of the first noun headword line."""
    for e in entries:
        for h in e.get("head_templates", []):
            if h.get("name", "").startswith("en-"):
                return h["name"], h.get("expansion", "")
    return None


def headword_countability(template: str, expansion: str) -> str:
    if template == "en-plural noun" or "plural only" in expansion:
        return "plural_only"
    if "countable and uncountable" in expansion:
        return "both"
    if "uncountable" in expansion:
        return "uncountable"
    return "countable"


def main_sense_countability(entries: list[dict]) -> str | None:
    """Countability tag of the first non-archaic sense, None if it is untagged."""
    for e in entries:
        for s in e.get("senses", []):
            tags = set(s.get("tags", []))
            if tags & SKIP_SENSE_TAGS:
                continue
            c, u = "countable" in tags, "uncountable" in tags
            return "both" if c and u else "countable" if c else "uncountable" if u else None
    return None


def countability(head: tuple[str, str], entries: list[dict]) -> str:
    """Conservative: a use (with a/an + plural, or bare) is allowed only if both the
    headword line and the main sense allow it. Wiktionary often marks the headword
    "countable and uncountable" because of one rare sense (boy, house)."""
    hw = headword_countability(*head)
    first = next((set(s.get("tags", [])) for e in entries for s in e.get("senses", [])), set())
    # people (= plural of person), police, data: singular-looking, plural verb
    if "plural-normally" in first or {"form-of", "plural"} <= first:
        return "plural_only"
    main = main_sense_countability(entries)
    if hw == "plural_only" or main is None:
        return hw
    allowed = USES[hw] & USES[main]
    if not allowed:  # sources contradict each other; trust the main sense
        return main
    return "both" if len(allowed) == 2 else next(iter(allowed))


def plural(word: str, entries: list[dict]) -> str:
    for e in entries:
        for f in e.get("forms", []):
            if f.get("tags") == ["plural"]:
                return f["form"]
        break  # only trust the first (main) entry
    forms = getInflection(word, tag="NNS")
    return forms[0] if forms else word + "s"


def starts_with_vowel_sound(word: str, entries: list[dict]) -> tuple[bool, str]:
    for e in entries:
        for s in e.get("sounds", []):
            ipa = s.get("ipa")
            if not ipa:
                continue
            first = next((c for c in ipa if c not in IPA_SKIP), None)
            if first:
                return first in IPA_VOWELS, "ipa"
    return word[0] in "aeiou", "spelling"


def main() -> None:
    pos = subtlex_dominant_pos()
    candidates = [w for w in ngsl_lemmas() if pos.get(w) == "Noun" and w.isalpha()][:LIMIT]

    rows, dropped, stats = [], [], Counter()
    for i, word in enumerate(candidates, 1):
        print(f"\r[{i}/{len(candidates)}] {word:<20}", end="", file=sys.stderr)
        entries = wiktionary_nouns(word)
        head = headword(entries)
        if head is None:
            dropped.append(word)
            continue
        count = countability(head, entries)
        an, an_source = starts_with_vowel_sound(word, entries)
        stats[count] += 1
        stats[f"an from {an_source}"] += 1
        rows.append([
            word,
            "" if count in ("uncountable", "plural_only") else plural(word, entries),
            count,
            "true" if an else "false",
            i,
        ])
    print(file=sys.stderr)

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["noun", "plural", "countability", "use_an", "freq_rank"])
        w.writerows(rows)
    print(f"wrote {len(rows)} nouns to {OUT.relative_to(ROOT)}")
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(stats.items())))
    if dropped:
        print(f"dropped {len(dropped)} (no Wiktionary noun entry): {' '.join(dropped)}")


if __name__ == "__main__":
    main()
