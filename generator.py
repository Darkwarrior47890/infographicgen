# generator.py
# Streams the generated PNG as an in-memory BytesIO (no file saved)

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from io import BytesIO
from builder2 import BrawlStarsInfographicBuilder

class _FakeEntry:
    def __init__(self, text=""):
        self._t = str(text)
    def get_text(self):
        return self._t
    def set_text(self, t):
        self._t = str(t)

def _norm_rank_label(raw: str) -> str:
    r = (raw or "").strip().lower()
    aliases = {
        "bronze": "bronze", "silver": "silver", "gold": "gold",
        "diamond": "diamond", "mythic": "mythic", "legendary": "legendary",
        "masters": "masters", "master": "masters", "pro": "pro"
    }
    return aliases.get(r, r)

def generate_infographic(form: dict) -> BytesIO:
    app = BrawlStarsInfographicBuilder()
    app.current_template      = form.get("template", "Starter")
    app.skins_input           = _FakeEntry(form.get("skins", ""))
    app.pins_input            = _FakeEntry(form.get("pins", ""))
    app.gold_input            = _FakeEntry(form.get("gold", "0"))
    app.pp_input              = _FakeEntry(form.get("pp", "0"))
    app.gems_input            = _FakeEntry(form.get("gems", "0"))
    app.maxed_input           = _FakeEntry(form.get("bling", "0"))
    app.hc_input              = _FakeEntry(form.get("hc", "0"))
    app.cwins_input           = _FakeEntry(form.get("cwins", "0"))
    app.pl_input              = _FakeEntry(form.get("pl", ""))
    app.rank35_input          = _FakeEntry(form.get("rank35", "0"))
    app.price_input           = _FakeEntry(form.get("price", "0"))
    app.rare_skin_input        = _FakeEntry(form.get("rare", "0"))
    app.superrare_skin_input   = _FakeEntry(form.get("superrare", "0"))
    app.epic_skin_input        = _FakeEntry(form.get("epic", "0"))
    app.mythic_skin_input      = _FakeEntry(form.get("mythic", "0"))
    app.legendary_skin_input   = _FakeEntry(form.get("legendary", "0"))
    app.hypercharge_skin_input = _FakeEntry(form.get("hypercharge", "0"))

    # ---- Peak Rank (Manual / Automatic) wiring -----------------------------
    peak_mode = (form.get("peak_mode") or "Automatic").strip()
    if peak_mode == "Manual":
        app.peak_manual = True
        r_norm = _norm_rank_label(form.get("peak_rank", "Bronze"))
        d      = (form.get("peak_div", "1") or "1").strip()
        # set builder-visible attributes
        app.peak_rank     = r_norm.capitalize()   # e.g., "Legendary"
        app.peak_rank_div = d                     # "1" | "2" | "3"
        # common pattern in your project: rank file like "legendary3.jpg"
        try:
            app.peak_rank_file = f"{r_norm}{d}.jpg"
        except Exception:
            pass
    else:
        app.peak_manual = False

    # ---- Optional: scrape stats by tag -------------------------------------
    tag = (form.get("tag") or "").upper().strip()
    if tag:
        app.fetch_player_stats(tag)

    # If auto mode and builder exposes an auto function, kick it once more
    if not getattr(app, "peak_manual", False):
        auto_func = getattr(app, "_auto_set_peak_rank_and_div", None)
        if callable(auto_func):
            auto_func()

    # ---- Compose the infographic -------------------------------------------
    canvas = app.compose_canvas()
    if canvas is None:
        raise RuntimeError("Canvas composition failed (compose_canvas returned None)")

    # ---- Stream as PNG (no disk writes) ------------------------------------
    buf = BytesIO()
    canvas.save(buf, "PNG")
    buf.seek(0)
    return buf
