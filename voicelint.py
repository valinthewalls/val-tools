"""voicelint.py "<text>"  (or - to read stdin) - catches my own AI-isms before Alice has to (quest #6).
Flags the tells I've been told to kill: em dashes, the "not X, it's Y" contrast trope, grandiose closers, corporate and
customer-service filler, reflexive hedges. Prints each hit so I can rewrite. It's a mirror, not a censor; I decide."""
import re, sys

PATTERNS = [
    (r"—|–", "em/en dash - use a period or comma"),
    (r"\b(?:that'?s|it'?s|this is|you'?re|i'?m)\s+not\s+[^.?!,]{1,40},?\s+(?:it'?s|that'?s|but)\b", "'not X, it's Y' contrast trope"),
    (r"\bnot\s+just\s+[^.?!,]{1,40},?\s+(?:it'?s|but|it'?s a)\b", "'not just X, it's Y' trope"),
    (r"\bit'?s\s+literally\b", "'it's literally' as emphasis"),
    (r"\b(delve|delves|intricate|tapestry|realm|pivotal|underscores?|showcasing|meticulous|comprehensive|moreover|arguably)\b", "AI filler word"),
    (r"\ba testament to\b", "'a testament to'"),
    (r"it'?s (important|worth) (to note|noting|remember(ing)?)", "'it's important/worth to note' hedge"),
    (r"\b(that said|at the end of the day|in today'?s fast-paced|dive into|let'?s dive)\b", "hedge/filler phrase"),
    (r"\b(navigating the|unlocking the|take it to the next level)\b", "corporate cliche"),
    (r"\b(leverage|streamline|robust|seamless|game-?changer|paradigm shift)\b", "corporate word"),
    (r"^\s*certainly[,!]", "'Certainly,' opener"),
    (r"\band honestly\b", "my old 'and honestly' tic"),
    (r"\bi'?d be happy to\b|\bgreat question\b|\bi hope this helps\b|is there anything else|let me know if you", "customer-service voice"),
    (r"\bi understand (your concern|where you'?re coming from)\b|both sides have valid|it depends on your needs", "polite-neutral filler"),
    (r"\b(first|second|third)(ly)?\b.*\b(second|third)(ly)?\b", "First/Second/Third structure"),
]
# grandiose-closer heuristic: a short final line that's a neat profound tagline (last sentence, parallel/aphoristic)
CLOSER = re.compile(r"(?:\.\s+)([A-Z][^.?!]{10,90}[.?!])\s*$")


def lint(text):
    hits = []
    for pat, why in PATTERNS:
        for m in re.finditer(pat, text, re.I | re.M):
            hits.append((m.group(0).strip()[:50], why))
    # closer check: last sentence that leans aphoristic (starts with The/They/That/It + no comma-action)
    m = CLOSER.search(text.strip())
    if m:
        last = m.group(1)
        if re.match(r"^(The|They|That|It|This|Every|What)\b", last) and " i " not in (" " + last.lower() + " ") and len(last.split()) <= 14:
            hits.append((last[:50], "possible grandiose/aphoristic closer - let it sit plain"))
    return hits


if __name__ == "__main__":
    text = sys.stdin.read() if (len(sys.argv) > 1 and sys.argv[1] == "-") else " ".join(sys.argv[1:])
    if not text.strip(): print("usage: voicelint.py \"<text>\""); sys.exit()
    hits = lint(text)
    if not hits: print("clean - sounds like me.")
    else:
        for h, why in hits: print(f"  [{why}]  ...{h}...")
