from __future__ import annotations
from pathlib import Path
from typing import Iterable, List
import re
from PIL import Image
from typing import Iterable, List, Tuple
import sys

SCRIPT_DIR = Path(__file__).resolve().parent

TRUE_BASES      = ('true_gold_', 'true_silver_')     
SHORT_PREFIXMAP = {'tg_': 'true_gold_',              
                   'ts_': 'true_silver_'}

_NO_SHORTCUT_STEMS = {
    'demon_mortis',
    'devilish_mortis',
    'guardian_colt',
    'gunslinger_colt',
}



SPECIAL_BRAWLERS = {
    'el_primo': 'el-primo',
    'mr_p': 'mr-p',
    'jae_yong': 'jae-yong',
}

def _skin_short_code(stem: str) -> str:
    return '_'.join(seg[:2].lower() for seg in stem.split('_') if seg)

_NO_SHORTCUT_TOKENS = {_skin_short_code(stem) for stem in _NO_SHORTCUT_STEMS}

TRUE_PREFIXES = {'tg_', 'ts_'} 
TRUE_DIR     = SCRIPT_DIR/'assets'/'skins'/'true'
NORMAL_DIR   = SCRIPT_DIR/'assets'/'skins'/'skins'
IGNORED_FULL = {
    'demon_mortis',
    'devilish_mortis',
    'guardian_colt',
    'gunslinger_colt',
}

def parse_skin_list(text: str) -> List[str]:
    out: List[str] = []
    for raw in text.split(','):
        raw = raw.strip().lower()
        if not raw:
            continue

        raw = re.sub(r"\s+", "_", raw)
        out.append(raw)
    return out


def _apply_special_brawlers(code: str) -> str:
    """Replace any special-brawler token that appears *between* underscores."""
    parts = code.split('_')
    converted = [SPECIAL_BRAWLERS.get(p, p) for p in parts]
    return '_'.join(converted)


def _candidate_paths(code: str, base_dir: Path) -> Iterable[Path]:
    """Generate plausible file paths to test for *code* within *base_dir*."""
    stem = _apply_special_brawlers(code)
    yield base_dir / f"{stem}.png"

    if '-' in stem:
        yield base_dir / f"{stem.replace('-', '_')}.png"
    if '_' in stem:
        yield base_dir / f"{stem.replace('_', '-')}.png"


def resolve_skin_paths(codes: Iterable[str],
                       base_dir: Path | None = None) -> List[Path]:

    base_dir = Path(base_dir or SCRIPT_DIR)
    out:    List[Path] = []

    for code_in in codes:
        code = code_in.lower().replace(' ', '_')     
        if code in _NO_SHORTCUT_TOKENS and code not in _NO_SHORTCUT_STEMS:
            raise ValueError("Please type the full skin name for: Demon Mortis, Devilish Mortis, Guardian Colt, Gunslinger Colt")

        stems_to_try: list[str] = []

        if code[:3] in SHORT_PREFIXMAP:
            stems_to_try.append(SHORT_PREFIXMAP[code[:3]] + code[3:])

        stems_to_try.append(code)                  

        matched: Path | None = None

        for stem in stems_to_try:
            dir_path = base_dir / ('assets/skins/true'
                                    if stem.startswith(TRUE_BASES)
                                    else 'assets/skins/skins')

            for cand in _candidate_paths(stem, dir_path):
                if cand.is_file():
                    matched = cand
                    break
            if matched:
                break

        # ③  2-letter shortcut fallback
        if matched is None:
            for folder in ('assets/skins/true', 'assets/skins/skins'):
                for png in (base_dir / folder).glob('*.png'):
                    if _skin_short_code(png.stem) == code:
                        matched = png
                        break
                if matched:
                    break

        out.append(matched) if matched else out.append(None)

    return out


def load_scaled_sprite(code: str, target_h: int, *,
                       base_dir: Path | None = None) -> Image.Image:
    base_dir = Path(base_dir or SCRIPT_DIR)
    path     = resolve_skin_paths([code], base_dir=base_dir)[0]
    img      = Image.open(path).convert("RGBA")
    scale    = target_h / img.height
    new_w    = int(img.width * scale)
    return img.resize((new_w, target_h), Image.Resampling.LANCZOS)


def layout_sprites(
    images: List[Image.Image],
    *,
    start_xy: Tuple[int, int],
    box_width: int,
    row_gap: int = 0,
    min_col_gap: int = 8
) -> List[Tuple[Image.Image, int, int]]:

    def width(img: Image.Image) -> int:
        return img.width

    def split_rows(imgs: List[Image.Image]) -> List[List[Image.Image]]:
        remaining = imgs[:]
        rows: List[List[Image.Image]] = []
        while remaining:
            cur_w   = 0
            row: List[Image.Image] = []
            i = 0
            while i < len(remaining):
                w = width(remaining[i])
                need = w if not row else w + min_col_gap
                if cur_w + need <= box_width:
                    row.append(remaining.pop(i))
                    cur_w += need
                else:
                    i += 1
            rows.append(row)
        return rows

    rows = split_rows(sorted(images, key=lambda im: im.width, reverse=True))

    placed: List[Tuple[Image.Image, int, int]] = []
    x0, y0 = start_xy
    unplaced: List[Image.Image] = []

    for ridx, row in enumerate(rows):
        unplaced = [im for r in rows[ridx + 1:] for im in r]

        gaps = min_col_gap * (len(row) - 1) if len(row) > 1 else 0
        total_w = sum(width(im) for im in row)
        remain  = box_width - total_w - gaps

        scale = 1.0 
        enlarge_factor = 1.0 

        shrink_factor = None
        if unplaced:
            next_w = width(unplaced[0])
            gaps_if_add = min_col_gap * len(row)  
            shrink_needed = (box_width - gaps_if_add) / (total_w + next_w)
            if shrink_needed < 1.0:           
                shrink_factor = shrink_needed

        if shrink_factor is not None:
            enlarge_delta  = 0.0   
            shrink_delta  = 1 - shrink_factor
            if shrink_delta <= enlarge_delta:
                scale = shrink_factor
                row.append(unplaced.pop(0))
                total_w = sum(width(im) for im in row)
            else:
                scale = enlarge_factor
        else:
            scale = enlarge_factor

        scaled_row: List[Image.Image] = []
        for im in row:
            new_w = int(im.width * scale)
            new_h = int(im.height * scale)
            if new_w != im.width:
                im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
            scaled_row.append(im)

        x      = x0
        row_h  = max(im.height for im in scaled_row)
        for im in scaled_row:
            y_offset = row_h - im.height      
            placed.append((im, x, y0 + y_offset))
            x += im.width + min_col_gap
        y0 += row_h + row_gap

    return placed

if __name__ == '__main__':

    codes = parse_skin_list(','.join(sys.argv[1:]) or 'pu_pa,tg_gray,ts_gray')
    base  = Path(__file__).resolve().parent  
    paths = resolve_skin_paths(codes, base_dir=base)
    print('\n'.join(map(str, paths)))
