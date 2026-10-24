"""
Add derived style tags to fonts.json.

Google's API gives only five categories (sans-serif, serif, display,
handwriting, monospace), which is too coarse to find a comic face or a slab.
Google's own website shows richer tags, but those come from an endpoint that
is not part of the public API.

So these tags are derived here from the family name and category. Google font
names are unusually descriptive ("Alfa Slab One", "Comic Neue", "Pirata One"),
which makes name matching accurate for the obvious styles and silent for the
rest. A font matches zero or more tags; nothing is guessed when there is no
evidence for it.

    python3 add_tags.py ../fonts.json
"""

import json, pathlib, re, sys, collections

# tag -> (name patterns, categories it may apply to, explicit family names)
RULES = {
    "slab": (r"\bslab\b|\brockwell\b", {"serif", "display"},
             {"Arvo", "Bitter", "Rokkitt", "Zilla Slab", "Josefin Slab", "Crete Round",
              "Kadwa", "Aleo", "Coustard", "Enriqueta", "Patua One", "Bevan"}),
    "script": (r"\bscript\b|\bcursive\b|\bhandwriting\b|\bsignature\b|\bcalligraph",
               {"handwriting", "display", "serif"},
               {"Dancing Script", "Great Vibes", "Sacramento", "Parisienne", "Allura",
                "Tangerine", "Pinyon Script", "Italianno", "Alex Brush", "Satisfy",
                "Yellowtail", "Lobster", "Courgette", "Cookie", "Niconne", "Norican"}),
    "marker": (r"\bmarker\b|\bbrush\b|\bpen\b|\bink\b|\bsharpie\b|\bcrayon\b|\bchalk\b",
               {"handwriting", "display"},
               {"Permanent Marker", "Rock Salt", "Caveat Brush", "Shadows Into Light",
                "Gloria Hallelujah", "Nanum Pen Script", "Reenie Beanie"}),
    "comic": (r"\bcomic\b|\bcartoon\b|\bbubble\b|\bchewy\b|\bbangers\b|\bluckiest\b|\bfredoka\b|"
              r"\bbaloo\b|\bjolly\b|\bsilly\b|\bgoofy\b|\bcandy\b|\bsugar\b|\bbungee\b",
              {"handwriting", "display", "sans-serif"},
              {"Comic Neue", "Bangers", "Chewy", "Luckiest Guy", "Bubblegum Sans",
               "Boogaloo", "Lilita One", "Titan One", "Sniglet", "Grandstander",
               "Fredoka", "Schoolbell", "Short Stack", "Mali", "Itim", "Patrick Hand",
               "Gaegu", "Jua", "Dongle", "Gamja Flower", "Single Day", "Sue Ellen Francisco",
               "Coming Soon", "Architects Daughter", "Shantell Sans", "Delicious Handrawn",
               "Gochi Hand", "Kalam", "Nerko One", "Shrikhand", "Modak", "Passion One",
               "Fugaz One", "Sigmar One", "Bowlby One", "Chango", "Lemon", "Ribeye",
               "Macondo", "Mountains of Christmas", "Creepster", "Eater", "Nosifer"}),
    "blackletter": (r"\bfraktur\b|\bgotisch\b|\bblackletter\b|\bgothic ?script\b|\bpirata\b",
                    {"display", "serif", "handwriting"},
                    {"UnifrakturMaguntia", "UnifrakturCook", "Pirata One", "Grenze Gotisch",
                     "Almendra", "Metal Mania", "New Rocker", "Eagle Lake"}),
    "stencil": (r"\bstencil\b|\bstardos\b", {"display", "sans-serif", "serif"},
                {"Big Shoulders Stencil Display", "Saira Stencil One", "Wallpoet"}),
    "pixel": (r"\bpixel\b|\bbitmap\b|\bdot ?matrix\b|\bvt323\b|\bsilkscreen\b|\bpress ?start\b",
              {"display", "monospace"},
              {"Press Start 2P", "Silkscreen", "VT323", "Pixelify Sans", "Workbench",
               "Nova Square", "Jacquard 12", "Micro 5"}),
    "rounded": (r"\brounded\b|\bround\b|\bsoft\b|\bnunito\b|\bbaloo\b|\bdongle\b",
                {"sans-serif", "display", "handwriting"},
                {"Quicksand", "Comfortaa", "Nunito", "Nunito Sans", "Varela Round",
                 "M PLUS Rounded 1c", "Sniglet", "Dosis", "Hind", "Signika", "Fredoka",
                 "Lexend", "Asap", "Poppins", "Rubik", "Livvic", "Sarabun", "Mitr",
                 "Chivo", "Catamaran", "Mulish", "Karla", "Jost", "Outfit"}),
    "condensed": (r"\bcondensed\b|\bnarrow\b|\bcompressed\b|\bextended\b|\bexpanded\b",
                  {"sans-serif", "serif", "display"},
                  {"Oswald", "Anton", "Bebas Neue", "Teko", "Fjalla One", "Archivo Narrow",
                   "Pathway Gothic One", "Six Caps", "Khand", "Saira Condensed"}),
    "outline": (r"\boutline\b|\bshadow\b|\binline\b|\bhollow\b|\bengrav|\bstroke\b",
                {"display"},
                {"Bungee Shade", "Bungee Outline", "Londrina Outline", "Codystar",
                 "Rubik Puddles", "Vast Shadow", "Shadows Into Light Two"}),
    "mono": (r"\bmono\b|\bcode\b|\btypewriter\b|\bcourier\b", {"monospace", "display", "sans-serif"},
             set()),
    "display-decorative": (r"\bdecor|\bornament|\bfancy\b|\bdeco\b|\bvintage\b|\bretro\b|\bwestern\b|"
                           r"\bgrunge\b|\bcircus\b|\bcarnival\b|\bneon\b|\bglitch\b|\bsketch\b|"
                           r"\bspray\b|\bdrip\b|\bvibes\b|\bhorror\b|\bghost\b",
                           {"display"}, set()),
    "serif-didone": (r"\bdidone\b|\bbodoni\b|\bdidact\b", {"serif", "display"},
                     {"Playfair Display", "Bodoni Moda", "Abril Fatface", "Prata",
                      "Gilda Display", "Rozha One", "Yeseva One", "Ultra"}),
    "serif-old-style": (r"\bgaramond\b|\bcaslon\b|\bjenson\b", {"serif"},
                        {"EB Garamond", "Cormorant Garamond", "Cardo", "Gentium Book Plus",
                         "Crimson Text", "Crimson Pro", "Sorts Mill Goudy", "Junicode",
                         "Libre Baskerville", "Lora", "Vollkorn", "Spectral"}),
}

LABELS = {
    "slab": "Slab serif", "script": "Script & cursive", "marker": "Brush & marker",
    "comic": "Comic & playful", "blackletter": "Blackletter", "stencil": "Stencil",
    "pixel": "Pixel & bitmap", "rounded": "Rounded", "condensed": "Condensed & extended",
    "outline": "Outline & shadow", "mono": "Monospace", "display-decorative": "Decorative",
    "serif-didone": "High contrast serif", "serif-old-style": "Old style serif",
}


def tags_for(name, category):
    out = []
    low = name.lower()
    for tag, (pattern, cats, families) in RULES.items():
        if category not in cats:
            continue
        if name in families or re.search(pattern, low):
            out.append(tag)
    # a monospace family is always mono, whatever it is called
    if category == "monospace" and "mono" not in out:
        out.append("mono")
    return out


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "fonts.json")
    fonts = json.loads(path.read_text())
    counts = collections.Counter()
    for f in fonts:
        t = tags_for(f["n"], f["c"])
        if t:
            f["t"] = t
            counts.update(t)
        else:
            f.pop("t", None)
    path.write_text(json.dumps(fonts, separators=(",", ":"), ensure_ascii=False))
    width = max(len(LABELS[t]) for t in counts)
    for tag, n in counts.most_common():
        print(f"  {LABELS[tag]:<{width}}  {n:>4}")
    print(f"{sum(1 for f in fonts if f.get('t'))} of {len(fonts)} families tagged")
    print(f"wrote {path} ({path.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
