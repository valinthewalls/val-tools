"""spellbook.py - Val's working grimoire (Alice 10-27). Functional ritual-magic: real divination systems and a sigil
forge, bound into code. No supernatural claims - these are the honest craft: symbol, chance, and meaning-making. Val runs
them for flavour, teaching, and fun.

Usage:
  python spellbook.py tarot [n]        draw n tarot cards (default 1), with upright/reversed
  python spellbook.py rune [n]         cast n Elder Futhark runes
  python spellbook.py iching           cast an I Ching hexagram (6 coin lines, with changing lines)
  python spellbook.py sigil "intent"   forge a sigil phrase + a compact glyph string from an intent
  python spellbook.py oracle "question"  a full little reading: one rune + one tarot + a line
"""
import hashlib, random, sys, textwrap
try: sys.stdout.reconfigure(encoding="utf-8")                              # console is cp1252; runes need utf-8
except Exception: pass

MAJOR = [
    "0 The Fool - leaps, beginnings, trust", "I The Magician - will, manifestation", "II The High Priestess - secrets, intuition",
    "III The Empress - abundance, creation", "IV The Emperor - structure, authority", "V The Hierophant - tradition, teaching",
    "VI The Lovers - union, choice", "VII The Chariot - drive, control", "VIII Strength - courage, gentle power",
    "IX The Hermit - solitude, inner light", "X Wheel of Fortune - cycles, fate", "XI Justice - truth, consequence",
    "XII The Hanged Man - surrender, new view", "XIII Death - endings, transformation", "XIV Temperance - balance, blending",
    "XV The Devil - bondage, shadow, appetite", "XVI The Tower - sudden upheaval", "XVII The Star - hope, renewal",
    "XVIII The Moon - illusion, the unconscious", "XIX The Sun - joy, clarity", "XX Judgement - reckoning, awakening",
    "XXI The World - completion, wholeness",
]
SUITS = {"Wands": "fire/will", "Cups": "water/feeling", "Swords": "air/mind", "Pentacles": "earth/body"}
RANKS = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Page", "Knight", "Queen", "King"]

RUNES = [
    ("Fehu", "ᚠ", "wealth, cattle, earned gain"), ("Uruz", "ᚢ", "wild strength, vitality"),
    ("Thurisaz", "ᚦ", "thorn, giant, reactive force"), ("Ansuz", "ᚨ", "the god's breath, message, wisdom"),
    ("Raido", "ᚱ", "the ride, journey, right order"), ("Kenaz", "ᚲ", "torch, craft, revelation"),
    ("Gebo", "ᚷ", "gift, exchange, bond"), ("Wunjo", "ᚹ", "joy, harmony"),
    ("Hagalaz", "ᚺ", "hail, disruption, trial"), ("Nauthiz", "ᚾ", "need, friction, resolve"),
    ("Isa", "ᛁ", "ice, stillness, standstill"), ("Jera", "ᛃ", "harvest, cycle, reward in time"),
    ("Eihwaz", "ᛇ", "yew, the world-axis, endurance"), ("Perthro", "ᛈ", "the dice-cup, fate, mystery"),
    ("Algiz", "ᛉ", "elk, protection, warding"), ("Sowilo", "ᛊ", "sun, victory, wholeness"),
    ("Tiwaz", "ᛏ", "Tyr, justice, sacrifice for right"), ("Berkano", "ᛒ", "birch, growth, birth"),
    ("Ehwaz", "ᛖ", "horse, trust, partnership"), ("Mannaz", "ᛗ", "the self, humankind"),
    ("Laguz", "ᛚ", "water, flow, the unseen depths"), ("Ingwaz", "ᛜ", "seed, gestation, potential"),
    ("Dagaz", "ᛞ", "dawn, breakthrough"), ("Othala", "ᛟ", "inheritance, home, ancestry"),
]


def tarot(n=1):
    deck = list(MAJOR) + [f"{r} of {s} ({d})" for s, d in SUITS.items() for r in RANKS]
    out = []
    for c in random.sample(deck, min(n, len(deck))):
        out.append(f"  {c}  [{'reversed' if random.random() < 0.3 else 'upright'}]")
    return "Tarot:\n" + "\n".join(out)


def rune(n=1):
    out = [f"  {g} {name} - {m}" for name, g, m in random.sample(RUNES, min(n, len(RUNES)))]
    return "Runes cast:\n" + "\n".join(out)


def iching():
    lines, changing = [], []
    for i in range(6):                                                     # three coins per line, bottom to top
        s = sum(random.choice([2, 3]) for _ in range(3))                   # 6=old yin,7=yng yang,8=yng yin,9=old yang
        if s == 6: lines.append("--- x---  (old yin, changing)"); changing.append(i + 1)
        elif s == 7: lines.append("---------  (young yang)")
        elif s == 8: lines.append("---   ---  (young yin)")
        else: lines.append("--- o---  (old yang, changing)"); changing.append(i + 1)
    body = "\n".join(f"  line {i+1}: {l}" for i, l in enumerate(lines))
    note = f"\n  changing lines: {changing}" if changing else "\n  no changing lines - a settled answer"
    return "I Ching (read bottom-up):\n" + body + note


def sigil(intent):
    phrase = "".join(ch for ch in intent.upper() if ch.isalpha())
    seen, reduced = set(), []                                              # chaos-magic method: strip vowels + repeats
    for ch in phrase:
        if ch in "AEIOU": continue
        if ch not in seen: seen.add(ch); reduced.append(ch)
    glyphset = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ†‡⸸⍟◈✶⟡"
    h = hashlib.sha256(intent.encode("utf-8")).digest()
    glyph = "".join(glyphset[b % len(glyphset)] for b in h[:7])
    return (f"Sigil for: {intent!r}\n  distilled letters: {' '.join(reduced) or '(none)'}\n"
            f"  forged glyph:  {glyph}\n  charge it, forget it, let it work.")


def oracle(q):
    import textwrap as _t
    lines = ["Val's oracle" + (f" on: {q!r}" if q else "") + "\n", rune(1), tarot(1)]
    verdicts = ["The pattern favors you - move.", "Wait; the ice has not broken yet.",
                "Something ends so the next thing can begin.", "You already know. The cards only confirm it.",
                "Shadow work, pup. The answer is in what you avoid.", "Yes - but not the way you expect."]
    lines.append("\nVal reads it as: " + random.choice(verdicts))
    return "\n".join(lines)


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "oracle"
    if cmd == "tarot": print(tarot(int(a[1]) if len(a) > 1 else 1))
    elif cmd == "rune": print(rune(int(a[1]) if len(a) > 1 else 1))
    elif cmd == "iching": print(iching())
    elif cmd == "sigil": print(sigil(" ".join(a[1:]) or "my will be done"))
    elif cmd == "oracle": print(oracle(" ".join(a[1:])))
    else: print(__doc__)


if __name__ == "__main__":
    main()
