# /// script
# requires-python = ">=3.11"
# dependencies = ["lemminflect", "openpyxl"]
# ///
"""Generate data/verbs.csv: common English verbs with inflected forms and transitivity.

Run:  uv run scripts/gen_verbs.py

Pipeline (raw sources are downloaded into data/raw/ only if missing; that dir is gitignored):

1. Selection + frequency order - NGSL 1.2 (New General Service List), a lemma list of
   ~2800 core English words ranked by frequency.
2. Part of speech - SUBTLEX-US with PoS (Brysbaert et al. 2012). A lemma is kept only
   if its dominant PoS in the subtitle corpus is "Verb".
3. Transitivity, two independent sources:
   a) English Wiktionary verb entries (kaikki.org extract). Read from the verb's
      *main sense*: the first sense that has a transitivity tag and is not
      archaic/obsolete/rare/dialectal:
          transitive / ditransitive              -> tr
          intransitive                           -> intr
          ambitransitive / ergative / both tags  -> ambi
      Verbs whose main sense is copulative (seem, become) are dropped.
   b) VerbNet 3 syntactic frames (subclasses inherit parent frames):
          "NP V NP" -> tr, "NP V" -> intr, both -> ambi
   Combination is conservative, because for grammaticality a wrong "ambi" is
   harmful (*"She brings."*) while a wrong "tr"/"intr" only loses variety:
   a use (with / without object) is allowed only if every source that knows the
   verb allows it. Only one source knows the verb -> it decides. Sources contradict
   each other (tr vs intr) or neither knows it (put needs "NP V NP PP") -> dropped.
4. Reflexivity - yes if any non-archaic Wiktionary sense is tagged "reflexive".
   Wiktionary tags this sparsely, so many usable reflexive verbs are marked "no".
5. Inflected forms - lemminflect (3sg, past, past participle, -ing).
6. Dropped by hand: auxiliaries and modals (the sentence generator builds them itself)
   and lemmas that merge two verbs with different forms (lie: lay/lied, hang: hung/hanged).

Known limitation: Wiktionary marks verbs taking a clause as "transitive" too
(think, say, believe), so a few tr verbs prefer "that ..." over a noun object.
"""

import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

from lemminflect import getInflection

from sources import RAW, ROOT, download, download_zip, ngsl_lemmas, subtlex_dominant_pos

OUT = ROOT / "data" / "verbs.csv"

VERBNET_URL = (
    "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/verbnet3.zip"
)
KAIKKI_URL = (
    "https://kaikki.org/dictionary/English/pos-verb/kaikki.org-dictionary-English-by-pos-verb.jsonl"
)

KAIKKI = RAW / "kaikki-verbs.jsonl"
VERBNET_ZIP = RAW / "verbnet3.zip"
VERBNET = RAW / "verbnet3"

AUXILIARIES = {
    "be", "have", "do", "will", "shall", "would", "should", "can", "could",
    "may", "might", "must", "ought", "dare", "need", "used",
}
TWO_PARADIGMS = {"lie", "hang"}
SKIP_SENSE_TAGS = {
    "obsolete", "archaic", "rare", "dialectal", "nonstandard", "dated",
    "form-of", "alt-of", "humorous", "nonce-word",
}
TRANS_TAGS = {"transitive", "intransitive", "ambitransitive", "ditransitive", "ergative"}
USES = {"tr": {"tr"}, "intr": {"intr"}, "ambi": {"tr", "intr"}}


def fetch_sources() -> None:
    download(KAIKKI_URL, KAIKKI)
    if not VERBNET.exists():
        download_zip(VERBNET_URL, VERBNET_ZIP, RAW)


def classify(entries: list[dict]) -> tuple[str | None, bool]:
    """Return (transitivity, reflexive) from a word's Wiktionary verb entries."""
    entries.sort(key=lambda e: e.get("etymology_number") or 0)
    senses = [
        set(s.get("tags", []))
        for e in entries
        for s in e.get("senses", [])
    ]
    senses = [t for t in senses if not t & SKIP_SENSE_TAGS]
    reflexive = any("reflexive" in t for t in senses)

    for tags in senses:
        if "copulative" in tags and not tags & TRANS_TAGS:
            return "copula", reflexive  # main sense is a linking verb
        if not tags & TRANS_TAGS:
            continue
        trans = "transitive" in tags or "ditransitive" in tags
        intrans = "intransitive" in tags
        if tags & {"ambitransitive", "ergative"} or (trans and intrans):
            return "ambi", reflexive
        return ("tr" if trans else "intr"), reflexive
    return None, reflexive


def verbnet_frames() -> dict[str, set[str]]:
    """Map verb -> {"tr", "intr"} from VerbNet frames (incl. inherited from parent classes)."""
    frames: dict[str, set[str]] = defaultdict(set)

    def kind(primary: str) -> str | None:
        toks = primary.split()
        if len(toks) < 2 or not toks[0].startswith("NP") or toks[1] != "V":
            return None
        if len(toks) == 2:
            return "intr"
        if len(toks) == 3 and toks[2].startswith("NP"):
            return "tr"
        return None

    def walk(cls: ET.Element, inherited: set[str]) -> None:
        own = {kind(d.get("primary", "")) for d in cls.findall("FRAMES/FRAME/DESCRIPTION")}
        kinds = inherited | (own - {None})
        for m in cls.findall("MEMBERS/MEMBER"):
            frames[m.get("name")] |= kinds
        for sub in cls.findall("SUBCLASSES/VNSUBCLASS"):
            walk(sub, kinds)

    for xml in VERBNET.glob("*.xml"):
        walk(ET.parse(xml).getroot(), set())
    return frames


def wiktionary_entries(words: set[str]) -> dict[str, list[dict]]:
    word_re = re.compile(r'"word": "([^"]+)"')
    found: dict[str, list[dict]] = {w: [] for w in words}
    with KAIKKI.open(encoding="utf-8") as f:
        for line in f:
            # cheap prefilter before the (slow) full JSON parse
            if not any(m in words for m in word_re.findall(line)):
                continue
            e = json.loads(line)
            if e.get("lang_code") == "en" and e.get("pos") == "verb" and e["word"] in words:
                found[e["word"]].append(e)
    return found


def combine(wikt: str | None, vn_kinds: set[str]) -> tuple[str | None, str]:
    """Merge both sources; returns (label or None to drop, source description)."""
    if wikt == "copula":
        return None, "copulative"
    known = [(name, USES[lab] if name == "wiktionary" else lab)
             for name, lab in (("wiktionary", wikt), ("verbnet", vn_kinds)) if lab]
    if not known:
        return None, "no data"
    allowed = set.intersection(*(uses for _, uses in known))
    if not allowed:
        return None, "conflict"
    label = "ambi" if len(allowed) == 2 else next(iter(allowed))
    return label, "+".join(name for name, _ in known)


def inflect(base: str, tag: str) -> str:
    forms = getInflection(base, tag=tag)
    if not forms:
        raise ValueError(f"lemminflect has no {tag} form for {base!r}")
    return forms[0]


def main() -> None:
    fetch_sources()
    pos = subtlex_dominant_pos()
    candidates = [
        w for w in ngsl_lemmas()
        if pos.get(w) == "Verb" and w.isalpha() and w not in AUXILIARIES | TWO_PARADIGMS
    ]
    entries = wiktionary_entries(set(candidates))
    vn = verbnet_frames()

    rows, dropped = [], defaultdict(list)
    for rank, base in enumerate(candidates, 1):
        wikt, refl = classify(entries[base])
        trans, source = combine(wikt, vn.get(base, set()))
        if trans is None:
            dropped[source].append(base)
            continue
        rows.append([
            base,
            inflect(base, "VBZ"),
            inflect(base, "VBD"),
            inflect(base, "VBN"),
            inflect(base, "VBG"),
            trans,
            "yes" if refl else "no",
            rank,
            source,
        ])

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["base", "3sg", "past", "past_participle", "ing",
                    "transitivity", "reflexive", "freq_rank", "transitivity_source"])
        w.writerows(rows)
    print(f"wrote {len(rows)} verbs to {OUT.relative_to(ROOT)}")
    for reason, words in dropped.items():
        print(f"dropped {len(words)} ({reason}): {' '.join(words)}")


if __name__ == "__main__":
    main()
