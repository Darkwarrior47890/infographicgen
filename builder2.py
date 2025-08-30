import json, time, pathlib, urllib.request, sys, os, platform, subprocess, tempfile, textwrap


import pygame
import pygame_gui
from pygame_gui.windows import UIMessageWindow
from pygame_gui.windows import UIConfirmationDialog
import os
import sys
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
try:                                   
    import Levenshtein
except ImportError:                  
    from difflib import SequenceMatcher
    class _Levenshtein:              
        @staticmethod
        def ratio(a: str, b: str) -> float:
            return SequenceMatcher(None, a, b).ratio()
    Levenshtein = _Levenshtein

from pathlib import Path
import requests
import re
import traceback
import platform
import subprocess
from skin_utils import *
from pygame_gui.elements import UITextEntryBox

import cloudscraper

if sys.platform.lower() in ("darwin", "macos"):     
    os.environ["SDL_HINT_VIDEO_HIGHDPI_DISABLED"] = "0"



def _pin_short_code(stem: str) -> str:
    parts = [p for p in stem.split('_') if p.isalpha()]
    return '_'.join(p[:2] for p in parts).lower()

if getattr(sys, "frozen", False):               
    BASE_DIR = Path(sys._MEIPASS)               
else:                                           
    BASE_DIR = Path(__file__).resolve().parent 

BRAWL_API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6ImM2NWMyOWQwLTE5NjktNDRiNC1iMWYwLTU2MDU1MGM2OTU4YiIsImlhdCI6MTc1Mzk5MjE1Niwic3ViIjoiZGV2ZWxvcGVyL2Q5ODhjODg5LTNmZTAtMGIyYi0wYTE5LWQ1YzhhNTY5ZWExYSIsInNjb3BlcyI6WyJicmF3bHN0YXJzIl0sImxpbWl0cyI6W3sidGllciI6ImRldmVsb3Blci9zaWx2ZXIiLCJ0eXBlIjoidGhyb3R0bGluZyJ9LHsiY2lkcnMiOlsiNDUuNzkuMjE4Ljc5Il0sInR5cGUiOiJjbGllbnQifV19.Ds6VEeGd8geEkjXGSra8oJdld62w0NImD5yEJG02fpXSCBoa1bOgDjSMhyAcoRE8Pu7IWhP_sfBsWzi1cSpRHg"
HEADERS         = {'Authorization': f'Bearer {BRAWL_API_TOKEN}'}
API_BASE_URL    = "https://api.brawlstars.com/v1/players"
YELLOW = '#ECC403'
GREEN = '#18A53C'
FONT_PATH = BASE_DIR / "assets" / "fonts" / "Anton-Regular.ttf"
TROPHY_BLANK_PATH = BASE_DIR / "assets" / "profile" / "trophies.jpg"
WINS_PANEL_PATH = BASE_DIR / "assets" / "profile" / "wins.jpg" 
BRAWLYTIX_URL = "https://brawlytix.com/profile/{tag}"


def resize_image(image, target_width, target_height):
            img_width, img_height = image.size
            
            scale = min(target_width / img_width, target_height / img_height)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

if not FONT_PATH.is_file():
    raise FileNotFoundError(f"Font not found: {FONT_PATH}")



class BrawlStarsInfographicBuilder:
    def __init__(self):

        pygame.init()
        
        self.WINDOW_SIZE = (1400, 950)
        self.screen = pygame.display.set_mode(self.WINDOW_SIZE)
        pygame.display.set_caption("Brawl Stars Infographic Builder")
        
        self.manager = pygame_gui.UIManager(self.WINDOW_SIZE)
        
        self.current_template = None
        self.cached_crops = {}
        self.skin_index = {}
        self.pin_index = {}
        self.status_message = "Ready"
        self.status_colour = "#00FF00" 
        self.current_trophies  = 0
        self.highest_trophies  = 0
        self.wins_3v3          = 0
        self.wins_solo         = 0
        self.wins_duo          = 0
        self.rank_peak_pts     = 0
        self.rank_current_pts  = 0
        self.p11_count         = 0
        self.p10_count         = 0
        self.current_rank = 'Bronze' 
        self.peak_manual     = False
        self.peak_rank = 'Bronze'  
        self.current_rank_div = '1'  
        self.peak_rank_div    = '1'
        self.current_rank_file = 'bronze1.jpg'  
        self.peak_rank_file = 'bronze1.jpg'  
        self.account_age_years = 0      
        self.max_win_streak    = 0  
        self.fame_rank         = ""  
        self.brawlers_unlocked   = 0   
        self.total_brawlers   = 0
        self.credits_to_next_fame = 0     
        self.cwins_input   = None 
        self.pl_input      = None   
        self.rank35_input  = None
        self.prestige_points = 0

        self.template_paths = {
            'Starter': BASE_DIR/'templates'/'template_starter.jpg',
            'Epic': BASE_DIR/'templates'/'template_epic.jpg', 
            'Mythic': BASE_DIR/'templates'/'template_mythic.jpg',
            'Legendary': BASE_DIR/'templates'/'template_legendary.jpg'
        }
        
        self.crop_regions = {
            'trophies': (100, 200, 800, 400),
            'ranked': (100, 650, 800, 300), 
            'wins': (100, 1000, 800, 350),
            'old_stats': (50, 100, 900, 600)
        }
        
        self.paste_regions = {
            'trophies': (2320, 450, 900, 700),
            'ranked': (1920, 1250, 1100, 600),
            'wins': (2800, 1100, 600, 900),
            'old_stats': (1000, 300, 900, 600),
            'skins_top':    (250, 3600, 1635, 280), 
            'skins_bottom': (250, 3850, 1635, 280), 
        }
        
        self.skin_grid = {'x': 200, 'y': 700, 'width': 1892, 'height': 2000, 'icon_size': 300}
        self.pin_grid = {'x': 140, 'y': 2967, 'width': 2100, 'height': 473, 'icon_size': 120}
        
        self.load_gui()
        self.build_asset_indices()
        
    def load_gui(self):
        y_pos = 20
        
        self.title_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(400, y_pos, 400, 40),
            text='Brawl Stars Infographic Builder',
            manager=self.manager
        )
        y_pos += 60
 

        y_pos += 30

        self.peak_mode_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, y_pos, 150, 30),
            text='Peak Rank Input:',
            manager=self.manager
        )

        self.peak_mode_dropdown = pygame_gui.elements.UIDropDownMenu(
            relative_rect=pygame.Rect(180, y_pos, 200, 30),
            options_list=['Automatic', 'Manual'],
            starting_option='Automatic',
            manager=self.manager
        )
        y_pos += 35

        self.peak_hint = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(180, y_pos, 420, 22),
            text='Use Manual if peak was achieved in the new ranked system',
            manager=self.manager,
            object_id='#hint'
        )
        y_pos += 30
        self.rank_dropdown_peak = pygame_gui.elements.UIDropDownMenu(
            relative_rect=pygame.Rect(180, y_pos, 200, 30),
            options_list=['Bronze', 'Silver', 'Gold', 'Diamond', 'Mythic', 'Legendary', 'Masters', 'Pro'],
            starting_option='Bronze',
            manager=self.manager
        )
        self.rank_div_dropdown_peak = pygame_gui.elements.UIDropDownMenu(
            relative_rect=pygame.Rect(390, y_pos, 80, 30),
            options_list=['1', '2', '3'],
            starting_option='1',
            manager=self.manager
        )
        y_pos += 50
        
        self.template_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, y_pos, 150, 30),
            text='Account Rating:',
            manager=self.manager
        )
        
        self.template_dropdown = pygame_gui.elements.UIDropDownMenu(
            relative_rect=pygame.Rect(180, y_pos, 200, 30),
            options_list=['Starter', 'Epic', 'Mythic', 'Legendary'],
            starting_option='Starter',
            manager=self.manager
        )
        y_pos += 50
        
        self.player_tag_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, y_pos, 150, 25),
            text='Player Tag:',
            manager=self.manager
        )

        self.player_tag_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(150, y_pos, 200, 25),
            manager=self.manager,
            placeholder_text='Player Tag'
        )
        y_pos += 35
        
        y_pos += 40
        
        self.skins_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(40, 310, 100, 25),
            text='Skins:',
            manager=self.manager
        )
        
        self.skins_input = UITextEntryBox(
            pygame.Rect(150, 310, 420, 90),  
            '',                     
            self.manager,               
            object_id='#skins_input' 
        )
        y_pos += 60
        
        self.pins_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(40, y_pos, 100, 25),
            text='Pins:',
            manager=self.manager
        )
        
        self.pins_input = UITextEntryBox(
            pygame.Rect(150, y_pos, 420, 90),  
            '',                                
            self.manager,
            object_id='#pins_input'           
        )
        y_pos += 100
        
        self.stats_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, y_pos, 150, 30),
            text='Stats:',
            manager=self.manager
        )
        y_pos += 40
        
        stat_fields = [
            ('Gold:', 'gold_input'),
            ('Power Points:', 'pp_input'),
            ('Gems:', 'gems_input'),
            ('Bling:', 'maxed_input')
        ]
        
        x_offset = 40
        for label_text, field_name in stat_fields:
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x_offset, y_pos, 120, 25),
                text=label_text,
                manager=self.manager
            )
            
            field = pygame_gui.elements.UITextEntryLine(
                relative_rect=pygame.Rect(x_offset + 125, y_pos, 80, 25),
                manager=self.manager,
                placeholder_text='0'
            )
            setattr(self, field_name, field)
            x_offset += 200
            
        y_pos += 35
        
        stat_fields2 = [
            ('Hypercharges:', 'hc_input'),
            ('Challenge Wins:', 'cwins_input'),
            ('Power League:',   'pl_input'),
            ("Rank 35's:",      'rank35_input'),
            ('Price:', 'price_input')
        ]
        
        x_offset = 40
        for label_text, field_name in stat_fields2:
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x_offset, y_pos, 120, 25),
                text=label_text,
                manager=self.manager
            )
            
            field = pygame_gui.elements.UITextEntryLine(
                relative_rect=pygame.Rect(x_offset + 125, y_pos, 80, 25),
                manager=self.manager,
                placeholder_text='0'
            )
            setattr(self, field_name, field)
            x_offset += 200
            
        y_pos += 60

        self.skin_counts_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, y_pos, 150, 30),
            text='Skins owned:',
            manager=self.manager
        )
        y_pos += 40

        skin_fields = [
            ('Rare:',        'rare_skin_input'),
            ('Super-Rare:',  'superrare_skin_input'),
            ('Epic:',        'epic_skin_input'),
            ('Mythic:',      'mythic_skin_input'),
            ('Legendary:',   'legendary_skin_input'),
            ('Hypercharge:', 'hypercharge_skin_input'),
        ]

        x_left = 40
        col_w  = 200
        for idx, (label_text, attr_name) in enumerate(skin_fields):
            col   = idx % 3
            row_y = y_pos + (idx // 3) * 35 

            pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect(x_left + col*col_w, row_y, 120, 25),
                text=label_text,
                manager=self.manager
            )

            field = pygame_gui.elements.UITextEntryLine(
                relative_rect=pygame.Rect(x_left + col*col_w + 125, row_y, 60, 25),
                manager=self.manager,
                placeholder_text='0'
            )
            setattr(self, attr_name, field)
        
        y_pos += 120
        self.generate_btn = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(550, y_pos, 200, 40),
            text='Generate Infographic',
            manager=self.manager
        )
        y_pos += 60
        
        self.status_bar = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(70, y_pos - 10, 1160, 30),
            text=f'Status: {self.status_message}',
            manager=self.manager
        )
        
    def build_asset_indices(self):
        try:
            skins_path = Path(BASE_DIR/'assets'/'skins')
            if skins_path.exists():
                for png_file in skins_path.glob('*.png'):
                    name = png_file.stem.replace('_', ' ').title()
                    initialism = ''.join([word[0].upper() for word in name.split()])
                    self.skin_index[name.lower()] = str(png_file)
                    self.skin_index[initialism.lower()] = str(png_file)
                     
            pins_path = BASE_DIR / 'assets' / 'pins'
            if pins_path.exists():
                for png_file in pins_path.rglob('*.png'):  
                    stem   = png_file.stem               
                    words  = stem.split('_')

                    self.pin_index[stem.lower()] = str(png_file)

                    full_name = ' '.join(words).title()
                    self.pin_index[full_name.lower()] = str(png_file)

                    init = ''.join(w[0] for w in words)
                    self.pin_index[init.lower()] = str(png_file)

                    short = _pin_short_code(stem)
                    self.pin_index[short] = str(png_file)
                    
            self.update_status(f"Loaded {len(self.skin_index)//2} skins, {len(self.pin_index)//2} pins", "#00FF00")
            
        except Exception as e:
            self.update_status(f"Error building asset indices: {str(e)}", "#FF0000")

    def _auto_set_peak_rank_and_div(self):

        if self.peak_manual:
            return   

        pts = self.rank_peak_pts or 0

        ranges = [
            (0,    500,  "bronze1"),
            (500,  1000, "bronze2"),
            (1000, 1500, "bronze3"),
            (1500, 2000, "silver1"),
            (2000, 2500, "silver2"),
            (2500, 3000, "silver3"),
            (3000, 3500, "gold1"),
            (3500, 4000, "gold2"),
            (4000, 4500, "gold3"),
            (4500, 5000, "diamond1"),
            (5000, 5500, "diamond2"),
            (5500, 6000, "diamond3"),
            (6000, 6500, "mythic1"),
            (6500, 7000, "mythic2"),
            (7000, 7500, "mythic3"),
            (7500, 8000, "legendary1"),
            (8000, 8500, "legendary2"),
            (8500, 9000, "legendary3"),
            (9000, float('inf'), "masters1"),
        ]

        tag = "bronze1"
        for low, high, lbl in ranges:
            if low <= pts < high:
                tag = lbl
                break

        m = re.match(r"([a-z]+)(\d)", tag)
        self.peak_rank     = m.group(1)        
        self.peak_rank_div = m.group(2)        
        self.peak_rank_file = f"{tag}.jpg"

        try:
            self.rank_dropdown_peak.set_selected_option(self.peak_rank.capitalize())
            self.rank_div_dropdown_peak.set_selected_option(self.peak_rank_div)
        except Exception:
            pass   

    def _auto_set_current_rank_and_div(self):
        ranges = [
            (0,    250,  "bronze1"),
            (250,  500,  "bronze2"),
            (500,  750,  "bronze3"),
            (750,  1000, "silver1"),
            (1000, 1250, "silver2"),
            (1250, 1500, "silver3"),
            (1500, 2000, "gold1"),
            (2000, 2500, "gold2"),
            (2500, 3000, "gold3"),
            (3000, 3500, "diamond1"),
            (3500, 4000, "diamond2"),
            (4000, 4500, "diamond3"),
            (4500, 5000, "mythic1"),
            (5000, 5500, "mythic2"),
            (5500, 6000, "mythic3"),
            (6000, 6750, "legendary1"),
            (6750, 7500, "legendary2"),
            (7500, 8250, "legendary3"),
            (8250, 9250, "masters1"),
            (9250, 10250,"masters2"),
            (10250,11250,"masters3"),
            (11250,float('inf'), "pro"),        
        ]

        tag = "bronze1"       
        for low, high, label in ranges:
            if low <= self.rank_current_pts < high:
                tag = label
                break

        m = re.match(r"([a-z]+)(\d*)", tag)
        tier = m.group(1)              
        div  = m.group(2) or ""       

        self.current_rank       = tier        
        self.current_rank_div   = div     
        self.current_rank_file  = f"{tag}.jpg" 


    def fetch_player_stats(self, tag: str) -> bool:
        import html as ihtml
        try:
            # ---------------------------------------------------------------
            # 1)  scrape the main numbers from Brawlytix  ─ unchanged
            # ---------------------------------------------------------------
            url = f"https://brawlytix.com/profile/{tag.lstrip('#').upper()}"
            raw = requests.get(url, timeout=10).text

            txt = re.sub(r"<[^>]*>", " ", raw)
            txt = ihtml.unescape(txt)
            txt = re.sub(r"\s+", " ", txt)

            def _num(pattern: str) -> int | None:
                m = re.search(pattern, txt, re.I)
                return int(m.group(1).replace(",", "")) if m else None

            cur_trophies  = _num(r"\bTrophies\s+([0-9,]+)\b")
            high_trophies = _num(r"\bHighest\s+Trophies\s+([0-9,]+)\b")

            wins_3v3      = _num(r"\b3v3\s+Victories\s+([0-9,]+)\b")
            wins_solo     = _num(r"\bSolo\s+Victories\s+([0-9,]+)\b")
            wins_duo      = _num(r"\bDuo\s+Victories\s+([0-9,]+)\b")

            p11_count_bt  = _num(r"\bPower\s+11\s+Brawlers\s+([0-9,]+)\b")
            unlocked_pair = re.search(r"\bBrawlers\s+Unlocked\s+([0-9,]+)\s*/\s*([0-9,]+)", txt, re.I)

            if cur_trophies  is not None: self.current_trophies   = cur_trophies
            if high_trophies is not None: self.highest_trophies  = high_trophies

            if wins_3v3  is not None: self.wins_3v3    = wins_3v3
            if wins_solo is not None: self.wins_solo   = wins_solo
            if wins_duo  is not None: self.wins_duo    = wins_duo

            if p11_count_bt is not None:  self.p11_count         = p11_count_bt
            if unlocked_pair:
                self.brawlers_unlocked = int(unlocked_pair.group(1).replace(",", ""))
                self.total_brawlers    = int(unlocked_pair.group(2).replace(",", ""))

            # ---------------------------------------------------------------
            # 2)  extra pass over Brawlace to compute P-10 (and fresh P-11)
            # ---------------------------------------------------------------
            try:

                HEADERS = {
                    "Authorization": f"Bearer {BRAWL_API_TOKEN}"   # ← keep the token you already store
                }
                url_bs = f"https://bsproxy.royaleapi.dev/v1/players/%23{tag.lstrip('#').upper()}"

                data = requests.get(url_bs, headers=HEADERS, timeout=10).json()

                # Every brawler comes with its current power level
                self.p10_count = sum(1 for b in data.get("brawlers", []) if b.get("power") == 10)

                self.update_status(f"RoyaleAPI proxy: P10 = {self.p10_count}", "#00FF00")

            except Exception as e_bl:
                self.update_status(f"Brawlace scrape skipped: {e_bl}", "#CC7700")
                print("Brawlace scrape skipped:", e_bl)

            self.update_status("Player stats scraped from Brawlytix (P-10 via Brawlace)", "#00FF00")
            self.fetch_rank_stats(tag)
            return True

        except Exception as e:
            self.update_status(f"Brawlytix scrape failed: {e}", "#FF0000")
            return False
    
    def fetch_rank_stats(self, tag: str) -> None:
        import re
        import html as ihtml      
        try:
            url  = f"https://brawlytix.com/profile/{tag.lstrip('#').upper()}"
            raw  = requests.get(url, timeout=10).text

            txt = re.sub(r"<[^>]*>", " ", raw)
            txt = ihtml.unescape(txt)
            txt = re.sub(r"\s+", " ", txt)

            cur  = re.search(r"Current Ranked Points\s*([\d,]+)",  txt, re.I)
            peak = re.search(r"Highest Ranked Points\s*([\d,]+)",  txt, re.I)
            age    = re.search(r"Account Age\s*(\d+)\s*years", txt, re.I)
            streak = re.search(r"Max Win Streak\s*(\d+)",        txt, re.I)
            fame   = re.search(r"Fame Rank\s*([A-Za-z]+\s*\d+)", txt, re.I)
            credit = re.search(r"Credits\s+to\s+next\s+Fame[^0-9]*([\d,]+)", txt, re.I)
            prestige = re.search(r"Prestige\s*([0-9]+)", txt, re.I)

            if prestige:
               self.prestige_points = int(prestige.group(1).replace(",", ""))

            if cur:   self.rank_current_pts  = int(cur.group(1).replace(",", ""))
            if peak:  self.rank_peak_pts     = int(peak.group(1).replace(",", ""))
            if age:   self.account_age_years = int(age.group(1))
            if streak:
                self.max_win_streak    = int(streak.group(1))
                print(self.max_win_streak)
            if fame:  self.fame_rank         = fame.group(1).title()
            if credit:
                self.credits_to_next_fame = int(credit.group(1).replace(",", ""))

            self._auto_set_current_rank_and_div()
            self._auto_set_peak_rank_and_div()

        except Exception as e:
            self.update_status(f"Ranked scrape failed: {e}", "#CC7700")


    def draw_power_block(self, canvas, box_xywh,
                         font_path=str(FONT_PATH),
                         font_size=105,
                         fill_color=YELLOW,
                         stroke_color="black",
                         stroke_width=3,
                         gap_px=None):

        p11_value = str(self.p11_count)
        p10_value = str(self.p10_count)
        hc_value  = self.hc_input.get_text() or "0"

        draw = ImageDraw.Draw(canvas)
        font = (ImageFont.truetype(font_path, font_size)
                if os.path.exists(font_path)
                else ImageFont.load_default())

        stats = [
            ("POWER11:",     p11_value),
            ("POWER10:",     p10_value),
            ("HYPERCHARGE:", hc_value),
        ]

        line_sizes = []
        for label, val in stats:
            text = f"{label} {val}"
            l, t, r, b = draw.textbbox((0, 0), text, font=font)
            line_sizes.append((text, r-l, b-t))

        if gap_px is None:
            gap_px = int(font_size * 0.25)

        total_h = sum(h for _, _, h in line_sizes) + gap_px*(len(stats)-1)
        x0, y0, w0, h0 = box_xywh
        cur_y = y0 + (h0 - total_h) / 2

        for text, tw, th in line_sizes:
            tx = x0 + (w0 - tw) / 2
            for dx in range(-stroke_width, stroke_width+1):
                for dy in range(-stroke_width, stroke_width+1):
                    if dx or dy:
                        draw.text((int(tx+dx), int(cur_y+dy)),
                                  text, font=font, fill=stroke_color)
            draw.text((int(tx), int(cur_y)), text, font=font, fill=fill_color)
            cur_y += th + gap_px


        


            
    def update_status(self, message, colour="#00FF00"):
        self.status_message = message
        self.status_colour = colour
        self.status_bar.set_text(f'Status: {message}')
            
    def crop_stat_panels(self, source_image, regions_to_crop):
        try:
            for region_name in regions_to_crop:
                if region_name in self.crop_regions:
                    x, y, w, h = self.crop_regions[region_name]
                    img_w, img_h = source_image.size
                    x = min(x, img_w - w) if x + w <= img_w else max(0, img_w - w)
                    y = min(y, img_h - h) if y + h <= img_h else max(0, img_h - h)
                    w = min(w, img_w - x)
                    h = min(h, img_h - y)
                    
                    cropped = source_image.crop((x, y, x + w, y + h))
                    self.cached_crops[region_name] = cropped
                    
        except Exception as e:
            self.update_status(f"Error cropping panels: {str(e)}", "#FF0000")
            
    def match_assets(self, tokens, asset_type):
        matched_files = []
        index = self.skin_index if asset_type == 'skins' else self.pin_index
        
        for token in tokens:
            token = token.strip().lower()
            if not token:
                continue
                
            matched_file = None
            
            if token in index:
                matched_file = index[token]
            else:
                best_match = None
                best_ratio = 0
                
                for key in index.keys():
                    ratio = Levenshtein.ratio(token, key)
                    if ratio >= 0.8 and ratio > best_ratio:
                        best_ratio = ratio
                        best_match = key
                        
                if best_match:
                    matched_file = index[best_match]
                    
            if matched_file:
                matched_files.append(matched_file)
            else:
                matched_files.append(None) 
                self.update_status(f"Warning: Could not match '{token}' in {asset_type}", "#FFAA00")
                
        return matched_files
        

    def compose_currency_row(self, canvas,
                            box_x: int, box_w: int,
                            top_y:  int, bottom_y: int):
        
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(str(FONT_PATH), 80) 

        ICON_DIR = BASE_DIR/"assets"/"icons"
        padding = 10 

        specs = {
        "gems":  {"file":"gem.png",  "size":(100,100),  "input":self.gems_input},
        "gold":  {"file":"coin.png", "size":(115,100),"input":self.gold_input},
        "pp":    {"file":"pp.png",   "size":(100,100),  "input":self.pp_input},
        "maxed": {"file":"bling.png","size":(100,100),  "input":self.maxed_input},
        }

        top_stats = ["gems","gold","pp"]
        blocks = []
        for stat in top_stats:
            s = specs[stat]
            icon = Image.open(str(ICON_DIR/s["file"])).convert("RGBA")
            icon = icon.resize(s["size"], Image.LANCZOS)
            text = (s["input"].get_text() or "0").strip()
            bbox = draw.textbbox((0, 0), text, font=font) 
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            bw = s["size"][0] + padding + tw
            blocks.append({
                "stat":stat, "icon":icon, "text":text,
                "icon_size":s["size"], "text_size":(tw,th),
                "block_w":bw
            })

        total_w = sum(b["block_w"] for b in blocks)
        n = len(blocks)
        gap_w = (box_w - total_w) / (n - 1) if n > 1 else 0

        x = box_x
        for b in blocks:
            ix, iy = int(x), top_y
            icon_w, icon_h = b["icon_size"]

            canvas.paste(b["icon"], (ix, iy), b["icon"])

            text_x   = ix + icon_w + padding
            text_y_mid = iy + icon_h // 2

            draw.text(
                (text_x, text_y_mid),
                b["text"],
                font=font,
                fill=YELLOW,
                anchor="lm"
            )

            x += b["block_w"] + gap_w

        m  = specs["maxed"]
        icon = Image.open(str(ICON_DIR/m["file"])).convert("RGBA")
        icon = icon.resize(m["size"], Image.LANCZOS)
        text = (m["input"].get_text() or "0").strip()
        bbox = draw.textbbox((0, 0), text, font=font)   
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        bw = m["size"][0] + padding + tw
        bx = box_x + (box_w - bw)/2
        by = bottom_y
        canvas.paste(icon, (int(bx), by), icon)
        val_x = int(bx) + m["size"][0] + padding
        val_y_mid = by + m["size"][1]//2
        draw.text((val_x, val_y_mid),
                text,
                font=font,
                fill=YELLOW,
                anchor="lm")

    def _draw_centered_text(self, draw, font_size, msg, box_xywh,
                            font_ratio=0.8,
                            fill="#FFFFFF",
                            stroke="black",
                            stroke_w=3):

        x, y, w, h = box_xywh
        fsize = int(h * font_ratio)
        font  = ImageFont.truetype(str(BASE_DIR/"assets"/"fonts"/"LilitaOne-Regular.ttf"), font_size)

        l, t, r, b = draw.textbbox((0, 0), msg, font=font)
        tw, th = r - l, b - t
        tx = x + (w - tw) // 2
        ty = y + (h - th) // 2

        for dx in range(-stroke_w, stroke_w + 1):
            for dy in range(-stroke_w, stroke_w + 1):
                if dx or dy:
                    draw.text((tx + dx, ty + dy), msg, font=font, fill=stroke)

        draw.text((tx, ty), msg, font=font, fill=fill)

    def draw_trophy_panel(self, canvas):

        try:
            blank = Image.open(TROPHY_BLANK_PATH).convert("RGBA")
            bx, by, bw, bh = self.paste_regions['trophies'] 
            sw, sh = blank.size
            scale  = min(bw / sw, bh / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            blank  = blank.resize((nw, nh), Image.Resampling.LANCZOS)

            px = bx + (bw - nw) // 2
            py = by + (bh - nh) // 2
            canvas.paste(blank, (px, py), blank)

            draw = ImageDraw.Draw(canvas)
            top_rel = (0.16, 0.14, 0.78, 0.24)   
            bot_rel = (0.16, 0.64, 0.78, 0.24)   

            for rel, val in zip((top_rel, bot_rel),
                                (self.current_trophies,
                                 self.highest_trophies)):
                rx, ry, rw, rh = rel
                box = (
                    px + int(rx * nw),
                    py + int(ry * nh),
                    int(rw * nw),
                    int(rh * nh),
                )
                self._draw_centered_text(draw, 120, str(val), box)

        except Exception as e:
            self.update_status(f"Error drawing trophies: {e}", "#FFAA00")

    def paste_rank_images(self, canvas, current_image, peak_image):
        current_rank_pos = (2065, 1505) 
        peak_rank_pos = (2065, 1730)    
        
        canvas.paste(current_image, current_rank_pos, current_image)  
        canvas.paste(peak_image, peak_rank_pos, peak_image) 

    def draw_skin_tier_rows(self, canvas):
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(str(FONT_PATH), 160)   
        padding = 10                                 

        ICON_DIR = BASE_DIR / "assets" / "icons"
        spec = {
            "rareskin":        {"file":"rareskin.jpg",        "input":self.rare_skin_input},
            "superrareskin":   {"file":"superrareskin.jpg",   "input":self.superrare_skin_input},
            "epicskin":        {"file":"epicskin.jpg",        "input":self.epic_skin_input},
            "mythicskin":      {"file":"mythicskin.jpg",      "input":self.mythic_skin_input},
            "legendaryskin":   {"file":"legendaryskin.jpg",   "input":self.legendary_skin_input},
            "hyperchargeskin": {"file":"hyperchargeskin.jpg", "input":self.hypercharge_skin_input},
        }

        rows = [
            ("rareskin","superrareskin","epicskin"),
            ("mythicskin","legendaryskin","hyperchargeskin"),
        ]
        for row_idx, keys in enumerate(rows):
            x, y, w, h = self.paste_regions["skins_top" if row_idx==0 else "skins_bottom"]

            blocks = []
            for key in keys:
                ico = Image.open(str(ICON_DIR/spec[key]["file"])).convert("RGBA")
                icon_size = int(h * 0.9)             
                ico = ico.resize((icon_size, icon_size), Image.LANCZOS)
                raw = (spec[key]["input"].get_text() or "0").strip()
                val = f": {raw}"
                tw, th = draw.textbbox((0,0), val, font=font)[2:]
                block_w = h + padding + tw
                blocks.append({"icon":ico, "text":val, "text_size":(tw,th), "block_w":block_w})

            total = sum(b["block_w"] for b in blocks)
            gap = (w - total) / (len(blocks)-1) if len(blocks)>1 else 0
            cx = x
            for b in blocks:
                canvas.paste(b["icon"], (int(cx), y), b["icon"])
                nx = int(cx + h + padding)
                ny = y + icon_size // 2                
                draw.text((nx, ny), b["text"],
          font=font, fill=YELLOW, anchor="lm")   
                cx += b["block_w"] + gap

    def draw_special_stats_block(self, canvas):
        BOX_X, BOX_Y, BOX_W, BOX_H = 2255, 1910, 1005, 690
        ROW_H          = BOX_H // 3
        ICON_PADDING_X = 20       
        GAP_ICON_TEXT  = 25           
        YELLOW_RGB     = (236, 196,   3, 255)   
        FONT_PATH      = BASE_DIR / "assets" / "fonts" / "Anton-Regular.ttf"
        ICON_DIR       = BASE_DIR / "assets" / "icons"

        rows = [
            ("rank35.jpg",      f": {self.rank35_input.get_text() or '0'}"),
            ("powerleague.jpg", f": {self.pl_input.get_text() or '—'}"),
            ("esport.jpg",     f": {self.cwins_input.get_text() or '0'} wins"),
        ]

        draw = ImageDraw.Draw(canvas)

        for idx, (icon_name, label_text) in enumerate(rows):
            top_y = BOX_Y + idx * ROW_H
            mid_y = top_y + ROW_H // 2

            icon_path = ICON_DIR / icon_name
            if not icon_path.is_file():
                continue
            icon = Image.open(icon_path).convert("RGBA")

            target_h  = int(ROW_H * 0.95)
            scale     = target_h / icon.height
            icon_size = (int(icon.width * scale), target_h)
            icon      = icon.resize(icon_size, Image.LANCZOS)

            icon_x = BOX_X + ICON_PADDING_X
            icon_y = mid_y - icon_size[1] // 2
            canvas.alpha_composite(icon, (icon_x, icon_y))

            text_x = icon_x + icon_size[0] + GAP_ICON_TEXT
            max_w  = (BOX_X + BOX_W) - text_x - 10

            font_size = int(ROW_H * 0.75)
            while font_size >= 14:
                font = ImageFont.truetype(str(FONT_PATH), font_size)
                tw = font.getbbox(label_text)[2]
                if tw <= max_w:
                    break
                font_size -= 2

            draw.text(
                (text_x, mid_y),          
                label_text,
                font=font,
                fill=YELLOW_RGB,
                anchor="lm"                
            )



    def draw_account_and_brawlers_info(self, canvas):
        BOX_X, BOX_Y, BOX_W, BOX_H = 1960, 3525, 1300, 500
        ROW_H = BOX_H // 2
        ICON_PAD_X = 25
        TEXT_PAD_X = 15
        YELLOW_RGB = (236, 196, 3, 255)  
        FONT_PATH = BASE_DIR / "assets" / "fonts" / "Anton-Regular.ttf"

        account_made = 2025 - self.account_age_years

        total_brawlers = self.total_brawlers

        draw = ImageDraw.Draw(canvas)

        text1 = f"Account Made: {account_made}"
        text_x1 = BOX_X + ICON_PAD_X
        max_w1 = (BOX_X + BOX_W) - text_x1 - 10

        font_size = ROW_H - 40
        while font_size >= 14:
            font = ImageFont.truetype(str(FONT_PATH), font_size)
            bbox = font.getbbox(text1)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if tw <= max_w1:
                break
            font_size -= 2

        text_y1 = BOX_Y + ROW_H // 2 - th // 2
        draw.text((text_x1, text_y1), text1, font=font, fill=YELLOW_RGB)

        text2 = f"Brawlers ({self.brawlers_unlocked}/{total_brawlers})"
        text_x2 = BOX_X + ICON_PAD_X
        max_w2 = (BOX_X + BOX_W) - text_x2 - 10

        font_size = ROW_H - 40
        while font_size >= 14:
            font = ImageFont.truetype(str(FONT_PATH), font_size)
            bbox = font.getbbox(text2)  
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if tw <= max_w2:
                break
            font_size -= 2

        text_y2 = BOX_Y + ROW_H + ROW_H // 2 - th // 2
        draw.text((text_x2, text_y2), text2, font=font, fill=YELLOW_RGB)

    def draw_fame_rank_icon(self, canvas, x, y,):
        FAME_DIR = BASE_DIR / "assets" / "fames"  
        YELLOW_RGB = (236, 196, 3, 255)  
        FONT_PATH = BASE_DIR / "assets" / "fonts" / "Anton-Regular.ttf"

        if self.fame_rank == "Global 1" and self.credits_to_next_fame == 2000:
            return  
        
        fame_icon_name = self.fame_rank.replace(" ", "").lower() + ".jpg"
        fame_icon_path = FAME_DIR / fame_icon_name

        if not fame_icon_path.is_file():
            print(fame_icon_path)
            print(f"Warning: Fame icon for {self.fame_rank} not found.")
            return

        fame_icon = Image.open(fame_icon_path).convert("RGBA")
        target_h = 500 
        scale = target_h / fame_icon.height
        fame_icon_size = (int(fame_icon.width * scale), target_h)

        fame_icon = fame_icon.resize(fame_icon_size, Image.LANCZOS)

        canvas.alpha_composite(fame_icon, (x, y))
        
    def fame_offset(self):
        FAME_DIR = BASE_DIR / "assets" / "fames"  

        if self.fame_rank == "Global 1" and self.credits_to_next_fame == 2000:
            return  
        
        fame_icon_name = self.fame_rank.replace(" ", "").lower() + ".jpg"
        fame_icon_path = FAME_DIR / fame_icon_name

        if not fame_icon_path.is_file():
            print(f"Warning: Fame icon for {self.fame_rank} not found.")
            return

        fame_icon = Image.open(fame_icon_path).convert("RGBA")
        target_h = 500  
        scale = target_h / fame_icon.height
        fame_icon_size = (int(fame_icon.width * scale), target_h)
        fame_offset = (fame_icon.width * scale) // 2
        return int(fame_offset)

        

    def draw_winstreak_icon(self, canvas, x, y):

        WINSTREAK_PATH = BASE_DIR / "assets" / "fames" / "winstreak.jpg"
        FONT_PATH = BASE_DIR / "assets" / "fonts" / "LilitaOne-Regular.ttf"
        TARGET_HEIGHT = 400  
        WHITE_RGB = ("#FFF9E7")

        winstreak_icon = Image.open(WINSTREAK_PATH).convert("RGBA")
        scale = TARGET_HEIGHT / winstreak_icon.height
        icon_size = (int(winstreak_icon.width * scale), TARGET_HEIGHT)
        winstreak_icon = winstreak_icon.resize(icon_size, Image.LANCZOS)

        canvas.alpha_composite(winstreak_icon, (x, y))

        text = f"{self.max_win_streak}"
        if len(text) <= 2:
            font_size = 180  
        elif len(text) == 3:
            font_size = 150
        else:
            font_size = 120
        font = ImageFont.truetype(str(FONT_PATH), font_size)

        draw = ImageDraw.Draw(canvas)
        bbox = draw.textbbox((0, 0), text, font=font) 
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = x + (icon_size[0] - tw) // 2 
        text_y = y + (TARGET_HEIGHT - th) // 2 

        offset = 10  
        for dx in [-offset, 0, offset]:
            for dy in [-offset, 0, offset]:
                if dx != 0 or dy != 0:  
                    draw.text((text_x + dx, text_y + dy), text, font=font, fill="#9B0C00")

        draw.text((text_x, text_y), text, font=font, fill=WHITE_RGB)
    
    def draw_prestige_icon(self, canvas, x, y):

        PRESTIGE_PATH = BASE_DIR / "assets" / "icons" / "prestige.jpg"
        FONT_PATH = BASE_DIR / "assets" / "fonts" / "LilitaOne-Regular.ttf"
        TARGET_HEIGHT = 500  
        WHITE_RGB = (255, 255, 255, 255)
        BLACK_RGB = (0, 0, 0, 255)  

        prestige_icon = Image.open(PRESTIGE_PATH).convert("RGBA")
        scale = TARGET_HEIGHT / prestige_icon.height
        icon_size = (int(prestige_icon.width * scale), TARGET_HEIGHT)
        prestige_icon = prestige_icon.resize(icon_size, Image.LANCZOS)
        

        canvas.alpha_composite(prestige_icon, (x, y))

        text = f"{self.prestige_points}"  

        font_size = int(icon_size[1] * 0.40)
        font      = ImageFont.truetype(str(FONT_PATH), font_size)

        draw      = ImageDraw.Draw(canvas)
        cx = x + icon_size[0] // 2
        cy = y + icon_size[1] // 2
        cy -= int(icon_size[1] * 0.03)
        cx -= int(icon_size[1] * 0.03)

        while True:
            bbox = font.getbbox(text, anchor="mm")           
            tw   = bbox[2] - bbox[0]
            if tw <= icon_size[0] * 0.5 or font_size <= 20:
                break                                
            font_size -= 2
            font = ImageFont.truetype(str(FONT_PATH), font_size)

        th     = bbox[3] - bbox[1]
        text_x = x + (icon_size[0] - tw) // 2
        text_y = y + (icon_size[1] - th) // 2

        outline = 7                                
        for dx in (-outline, 0, outline):
            for dy in (-outline, 0, outline):
                if dx or dy:
                    draw.text((cx+dx, cy+dy), text,
                          font=font, fill=BLACK_RGB, anchor="mm")

        draw.text((cx, cy), text, font=font, fill=WHITE_RGB, anchor="mm")

    def _apply_watermark(self, canvas):
        """Paste templates/watermark.png in the bottom-right corner."""
        wm_path = BASE_DIR / "templates" / "watermark.png"
        if not wm_path.is_file():
            return                       # silent if designer forgot the file

        wm = Image.open(wm_path).convert("RGBA")


        x = (canvas.width  - wm.width)  // 2
        y = (canvas.height - wm.height) // 2
        canvas.alpha_composite(wm, (x, y))




    def compose_canvas(self):
        try:
            template_path = self.template_paths[self.current_template]
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"Template not found: {template_path}")
                
            canvas = Image.open(template_path).convert('RGBA')
            current_rank_image_path = Path(BASE_DIR) / "assets" / "profile" / self.current_rank_file
            current_rank_image = Image.open(current_rank_image_path).convert("RGBA")
            current_rank_resized = resize_image(current_rank_image, 230, 230)
            
            peak_rank_image_path = Path(BASE_DIR) / "assets" / "profile" / self.peak_rank_file
            peak_rank_image = Image.open(peak_rank_image_path).convert("RGBA")
            peak_rank_resized = resize_image(peak_rank_image, 230, 230)  
            

            for region_name, crop in self.cached_crops.items():
                if region_name in self.paste_regions:
                    x, y, w, h = self.paste_regions[region_name]
                    resized_crop = crop.resize((w, h), Image.Resampling.LANCZOS)
                    canvas.paste(resized_crop, (x, y))
            self.draw_trophy_panel(canvas)  
            self.draw_stats_text(canvas)
            self.draw_wins_block(canvas)
            self.draw_ranked_block(canvas)
            self.paste_rank_images(canvas, current_rank_resized, peak_rank_resized)
            self.draw_skin_tier_rows(canvas)
            self.draw_special_stats_block(canvas)
            self.draw_account_and_brawlers_info(canvas)
            fame_icon_file = BASE_DIR / "assets" / "fames" / (self.fame_rank.replace(" ", "").lower() + ".jpg")

            if self.credits_to_next_fame and fame_icon_file.is_file():   # <- new guard
                offset = self.fame_offset() or 0
                self.draw_fame_rank_icon(canvas, 2183 - offset, 2450)
            self.draw_winstreak_icon(canvas, 2035, 3225)
            if self.prestige_points > 0:
                self.draw_prestige_icon(canvas, 1900,4300)

            draw = ImageDraw.Draw(canvas)

            font_value = ImageFont.truetype(str(FONT_PATH), 240)  

            price_str = (self.price_input.get_text() or "0").strip()

            value_text = f"{price_str}\u20ac"

            value_x, value_y = 1300, 4265


            draw.text((value_x, value_y), value_text, font=font_value, fill=GREEN)

            self.compose_icon_grid(canvas, 'skins')
            self.compose_icon_grid(canvas, 'pins')
            
            self.compose_currency_row(canvas,
                          box_x=2300, box_w=900,
                          top_y= 3300, bottom_y=3425)
            
            self._apply_watermark(canvas) 
            
            return canvas
            
        except Exception as e:
            self.update_status(f"Error composing canvas: {str(e)}", "#FF0000")
            return None
            
    def draw_stats_text(self, canvas):
        try:

            power_box = (2300, 2850, 900, 290)

            self.draw_power_block(
                canvas,
                power_box,
                font_path=str(FONT_PATH),
                font_size=150
            )

        except Exception as e:
            traceback.print_exc()
            raise


    def draw_wins_block(self, canvas):

        try:
            x, y, w, h = self.paste_regions['wins']   

            overlay = Image.open(str(WINS_PANEL_PATH)).convert("RGBA")
            r = min(w / overlay.width, h / overlay.height)
            new_w, new_h = int(overlay.width * r), int(overlay.height * r)
            overlay = overlay.resize((new_w, new_h), Image.Resampling.LANCZOS)
            ox = x + (w - new_w) // 2
            oy = y + (h - new_h) // 2
            canvas.paste(overlay, (ox, oy), overlay)

            row_h = new_h // 3
            field_x = ox + int(new_w * 0.25)    
            field_x2 = ox + int(new_w * 0.28)
            field_w = int(new_w * 0.55)      
            rects = [
                (field_x2, oy + int(row_h * 0.06), field_w, int(row_h * 0.9)), 
                (field_x, oy + int(row_h * 1.05), field_w, int(row_h * 0.9)),  
                (field_x, oy + int(row_h * 2.05), field_w, int(row_h * 0.9)),  
            ]

            draw = ImageDraw.Draw(canvas)
            for box, val in zip(rects, (self.wins_3v3, self.wins_solo, self.wins_duo)):
                self._draw_centered_text(draw, 70, str(val), box, font_ratio=0.75)

        except Exception as e:
            self.update_status(f"Error drawing wins block: {e}", "#FFA00A")

    def draw_ranked_block(self, canvas):

        try:
            x, y, w, h = self.paste_regions['ranked'] 

            blank = Image.open(BASE_DIR / 'assets' / 'profile' / 'ranked1.jpg').convert("RGBA")
            sw, sh = blank.size
            scale = min(w / sw, h / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            nw = int(nw * 1.4)
            nh = int(nh * 1.2)
            blank = blank.resize((nw+30, nh), Image.Resampling.LANCZOS)

            px = (x + (w - nw) // 2) - 30
            py = y + (h - nh) // 2
            canvas.paste(blank, (px, py), blank)

            draw = ImageDraw.Draw(canvas)
            font = ImageFont.truetype(str(FONT_PATH), 150) 

            current_elo = str(self.rank_current_pts) if self.rank_current_pts else "0"
            peak_elo = str(self.rank_peak_pts) if self.rank_peak_pts else "0"

            top_box = (px + 20, py + 205, nw, nh // 2) 
            bottom_box = (px + 20, py + nh - 580 // 2, nw, nh // 2) 

            self._draw_centered_text(draw, 85, current_elo, top_box, font_ratio=0.6)

            self._draw_centered_text(draw, 85, peak_elo, bottom_box, font_ratio=0.6)

        except Exception as e:
            self.update_status(f"Error drawing ranked Elo block: {e}", "#FFAA00")




    def compose_icon_grid(self, canvas, icon_type):
        MIN_SCALE = 0.7
        try:
            grid   = self.skin_grid if icon_type == 'skins' else self.pin_grid
            entry  = self.skins_input if icon_type == 'skins' else self.pins_input

            if icon_type == 'pins':
                tokens = [t.strip().lower() for t in self.pins_input.get_text().split(',') if t.strip()]
                if not tokens:
                    return
                
                seen: set[str] = set()
                uniq_tokens: list[str] = []
                for tok in tokens:
                    if tok in seen:
                        continue          
                    seen.add(tok)
                    uniq_tokens.append(tok)

                tokens = uniq_tokens        

                paths   = self.match_assets(tokens, 'pins')
                missing = [tok for tok, p in zip(tokens, paths)
           if p is None or not Path(p).is_file()]
                if missing:
                    self.popup = UIMessageWindow(
                        rect=pygame.Rect((300, 300), (500, 220)),
                        manager=self.manager,
                        window_title="Missing Pins",
                        html_message="The following pin images could not be found:<br><br>"
                                    + "<br>".join(missing) +
                                    "<br><br>Generation has been aborted."
                    )
                    raise

                def _layout_at_height(h_px: int):
                    sprites = []
                    for p in paths:
                        img   = Image.open(p).convert("RGBA")
                        k     = h_px / img.height
                        sprites.append(
                            img.resize((int(img.width * k), h_px), Image.LANCZOS)
                        )
                    return layout_sprites(
                        sprites,
                        start_xy    = (self.pin_grid['x'], self.pin_grid['y']),
                        box_width   = self.pin_grid['width'],
                        row_gap     = 10,
                        min_col_gap = 10,
                    )


                MAX_H   = int(self.pin_grid['height'] * 0.95)  
                MIN_H   = 30                                  
                STEP    = 4                                

                placed  = _layout_at_height(MAX_H)
                span_h  = max(y + im.height for im, x, y in placed) - self.pin_grid['y']

                cur_h = MAX_H
                while span_h > self.pin_grid['height'] and cur_h > MIN_H:
                    cur_h -= STEP
                    placed = _layout_at_height(cur_h)
                    span_h = max(y + im.height for im, x, y in placed) - self.pin_grid['y']

                for im, x, y in placed:
                    canvas.paste(im, (x, y), im)

                return 

            if icon_type == 'skins':
                tokens = parse_skin_list(self.skins_input.get_text())
                if not tokens:
                    return
                uniq, seen = [], set()
                for t in tokens:
                    if t not in seen:
                        uniq.append(t);  seen.add(t)
                tokens = uniq

                try:
                    paths = resolve_skin_paths(tokens, base_dir=BASE_DIR)
                except ValueError as e:
                    self.popup = UIMessageWindow(
                        rect=pygame.Rect((300, 300), (400, 180)),
                        manager=self.manager,
                        window_title="Full Name Required",
                        html_message=str(e).replace(",", "<br>")  # formats the skin names nicely
                    )
                    raise
                missing = [tok for tok, p in zip(tokens, paths)
           if p is None or not Path(p).is_file()]
                if missing:
                    self.popup = UIMessageWindow(
                        rect=pygame.Rect((300, 300), (500, 220)),
                        manager=self.manager,
                        window_title="Missing Skins",
                        html_message="The following skin images could not be found:<br><br>"
                                    + "<br>".join(missing) +
                                    "<br><br>Generation has been aborted."
                    )
                    raise
                
                BIG_FACTOR = 1.3

                def _is_big(p: Path) -> bool:
                    stem = Path(p).stem.lower()
                    if stem.startswith('true_gold_'):           
                        return True

                    SPECIAL_STEMS = {
                        'merchant_gale', 'mecha_paladin_surge', 'super_ranger_brock',
                        'starr_poco', 'trixie_colette',
                    }
                    return Path(p).stem in SPECIAL_STEMS

                originals = [Image.open(p).convert("RGBA") for p in paths]

            def _layout(h_px: int):

                sprites = []
                for img, fp in zip(originals, paths):
                    extra = BIG_FACTOR if _is_big(fp) else 1.0        
                    target_h = int(h_px * extra)                 
                    k = target_h / img.height
                    sprites.append(
                        img.resize((int(img.width * k), target_h), Image.LANCZOS)
                    )
                placed = layout_sprites(
                    sprites,
                    start_xy    = (grid['x'], grid['y']),
                    box_width   = grid['width'],
                    row_gap     = 10,
                    min_col_gap = 10,
                )

                rows: dict[int, list[tuple[Image.Image, int, int]]] = {}
                for im, x, y in placed:
                    rows.setdefault(y, []).append((im, x, y))

                new_placed = []
                for row_y, row_items in rows.items():
                    row_height = max(im.height for im, _, _ in row_items)
                    for im, x, y in row_items:
                        new_y = row_y + (row_height - im.height)  
                        new_placed.append((im, x, new_y))

                span = max(y + im.height for im, x, y in new_placed) - grid['y']
                return new_placed, span


            box_h   = grid['height']
            h       = grid['icon_size']       
            placed, span = _layout(h)

            while span < 0.70 * box_h and h < box_h:
                h      = int(h * 1.15)            
                placed, span = _layout(h)

            if span > box_h:
                h      = int(h / 1.15)
                placed, span = _layout(h)

            for im, x, y in placed:
                canvas.paste(im, (x, y), im)
            return


        except Exception as e:
            self.update_status(f"Error composing {icon_type} grid: {e}", "#FF0000")
            raise
            
    def save_output(self, canvas):
        try:
            output_dir = Path(BASE_DIR/'output')
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_infographic.png"
            output_path = output_dir / filename

            canvas.save(str(output_path), 'PNG')
            
            self.update_status(f"Infographic saved to {output_path}", "#00FF00")

            self.confirm_dialog = UIConfirmationDialog(
                rect=pygame.Rect((300, 300), (400, 200)),
                manager=self.manager,
                action_long_desc="Infographic saved successfully!\n\nOpen output folder?",
                window_title="Success",
                action_short_name="Open Folder"
            )
            

                    
            
        except Exception as e:
            self.update_status(f"Error saving output: {str(e)}", "#FF0000")
            
    def run(self):
        clock = pygame.time.Clock()
        running = True

        self.current_template = 'Starter'
        
        while running:
            time_delta = clock.tick(60) / 1000.0
            tag_text = self.player_tag_input.get_text()
            upper    = tag_text.upper()
            if tag_text != upper:
                self.player_tag_input.set_text(upper)

            pl_text  = self.pl_input.get_text()
            pl_upper = pl_text.upper()
            if pl_text != pl_upper:
                self.pl_input.set_text(pl_upper)



            self.manager.update(time_delta)
            self.manager.draw_ui(self.screen)
            pygame.display.update()
            for event in pygame.event.get():
                self.manager.process_events(event)
                if event.type == pygame.QUIT:
                    running = False
                    
                if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                    if event.ui_element == self.template_dropdown:
                        self.current_template = event.text
                        self.update_status(f"Template changed to {event.text}", "#00FF00")
                    
                    elif event.ui_element == self.peak_mode_dropdown:
                        if event.text == 'Automatic':
                            self.peak_manual = False
                            self.update_status("Peak rank now set automatically", "#00FF00")
                            self._auto_set_peak_rank_and_div()
                        else:                  
                            self.peak_manual = True
                            self.update_status("Peak rank will be taken from dropdowns", "#00FF00")

                    elif event.ui_element == self.rank_dropdown_peak:
                        self.peak_manual = True
                        self.peak_rank = event.text 
                        self.peak_rank_file = f"{self.peak_rank}{self.peak_rank_div}.jpg" 
                        self.update_status(f"Peak rank changed to {event.text}", "#00FF00")

                    elif event.ui_element == self.rank_div_dropdown_peak:
                        self.peak_manual = True
                        self.peak_rank_div = event.text
                        self.peak_rank_file = f"{self.peak_rank}{self.peak_rank_div}.jpg" 
                        self.update_status(f"Peak division set to {event.text}", "#00FF00")
                        
                if event.type == pygame_gui.UI_BUTTON_PRESSED:

                    if event.ui_element == self.generate_btn:
                        tag = self.player_tag_input.get_text()
                        if not tag:
                            self.update_status("Enter a playertag first")
                            continue
                        self.fetch_player_stats(tag)
                        canvas = self.compose_canvas()
                        if canvas:
                            self.save_output(canvas)

                if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
                    if event.ui_element == self.confirm_dialog:
                        output_dir = Path(BASE_DIR/'output')
                        output_dir.mkdir(exist_ok=True)
                        if platform.system() == 'Windows':
                            subprocess.run(['explorer', str(output_dir.absolute())])
                        elif platform.system() in {'Darwin', 'MacOS'}:  
                            subprocess.run(['open', str(output_dir.absolute())])

                        else:  
                            subprocess.run(['xdg-open', str(output_dir.absolute())])
                                    
            
                
            
            self.screen.fill((30, 30, 30))
            self.manager.draw_ui(self.screen)
            
            pygame.display.flip()
            
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    app = BrawlStarsInfographicBuilder()
    app.run()