#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCFM05 Reborn — interface gráfica (Tkinter, sem dependências).
Rode com o FM2005 aberto e o save carregado. Precisa de administrador.
Nada é escrito no jogo sem clicar em "Salvar no jogo" (ou marcar um congelamento).
"""
import os, sys, struct, json, datetime
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcfm
from lang import T, LANG, set_lang, LANGS, ATTR_ES, COACH_ES, MOVES_ES

VERSION = "v1.0 FINAL"
BUILD = "10/10/2026 00:05 (BRT)"
AUTHOR = "g0ldenboy & Claude AI"
mcfm.T = T   # mensagens do motor também traduzidas
from mcfm import PLAYER, PREF_MOVES, SKILLS, POSITIONS, NEWPOS, ALL_SKILL_OFFSETS, RAW_SKILLS, SKILL_RANGE, PERSONALITY, fm_date, to_fm_date, strip_accents, poff, pd

GROUPS = {
    "Técnicos": ["Corners", "Crossing", "Dribbling", "Finishing", "FirstTouch", "Freekicks", "Heading", "LongShots",
                 "LongThrows", "Marking", "Passing", "PenaltyTaking", "Tackling", "Technique"],
    "Mentais": ["Aggression", "Anticipation", "Bravery", "Composure", "Concentration", "Creativity", "Decisions",
                "Determination", "Flair", "Influence", "OffTheBall", "Positioning", "Teamwork", "Workrate"],
    "Físicos": ["Acceleration", "Agility", "Balance", "Jumping", "NaturalFitness", "Pace", "Stamina", "Strength"],
    "Goleiro": ["AerialAbility", "CommandOfArea", "Communication", "Eccentricity", "Handling", "Kicking", "OneOnOnes",
                "Reflexes", "RushingOut", "TendencyToPunch", "Throwing"],
    "Ocultos / pés": ["Consistency", "Dirtiness", "ImportantMatches", "InjuryProneness", "Versatility", "LeftFoot", "RightFoot"],
    "Personalidade": PERSONALITY,
    "Posições": list(POSITIONS.keys()),
    "Posições novas (a confirmar)": list(NEWPOS.keys()),
}
PT = {"Corners": "Cantos", "Crossing": "Cruzamentos", "Dribbling": "Finta", "Finishing": "Finalização", "FirstTouch": "Primeiro toque",
      "Freekicks": "Livres", "Heading": "Cabeceamento", "LongShots": "Remates de longe", "LongThrows": "Lançamentos", "Marking": "Marcação",
      "Passing": "Passe", "PenaltyTaking": "Pênaltis", "Tackling": "Desarme", "Technique": "Técnica", "Aggression": "Agressividade",
      "Anticipation": "Antecipação", "Bravery": "Bravura", "Composure": "Compostura", "Concentration": "Concentração",
      "Creativity": "Criatividade", "Decisions": "Decisões", "Determination": "Determinação", "Flair": "Instinto", "Influence": "Influência",
      "OffTheBall": "Sem bola", "Positioning": "Posicionamento", "Teamwork": "Trabalho de equipa", "Workrate": "Índice de trabalho",
      "Acceleration": "Aceleração", "Agility": "Agilidade", "Balance": "Equilíbrio", "Jumping": "Impulsão", "NaturalFitness": "Cond. física natural",
      "Pace": "Velocidade", "Stamina": "Resistência", "Strength": "Força", "AerialAbility": "Jogo aéreo", "CommandOfArea": "Comando de área",
      "Communication": "Comunicação", "Eccentricity": "Excentricidade", "Handling": "Mãos", "Kicking": "Pontapé", "OneOnOnes": "Um contra um",
      "Reflexes": "Reflexos", "RushingOut": "Saída da baliza", "TendencyToPunch": "Tendência a socar", "Throwing": "Lançamento c/ mão",
      "Consistency": "Consistência", "Dirtiness": "Sujeira", "ImportantMatches": "Jogos importantes", "InjuryProneness": "Propensão a lesão",
      "Versatility": "Versatilidade", "LeftFoot": "Pé esquerdo", "RightFoot": "Pé direito",
      "Adaptability": "Adaptabilidade", "Ambition": "Ambição", "Controversy": "Polêmica", "Loyalty": "Lealdade",
      "Pressure": "Pressão", "Professionalism": "Profissionalismo", "Sportsmanship": "Esportividade", "Temperament": "Temperamento",
      "Goalkeeper": "Guarda-redes", "Sweeper": "Líbero", "Defender": "Defesa", "DefensiveMidfielder": "Médio defensivo", "Midfielder": "Médio",
      "AttackingMidfielder": "Médio ofensivo", "Attacker": "Atacante", "WingBack": "Ala", "FreeRole": "Ação livre", "Right": "Direita",
      "Centre": "Centro", "Left": "Esquerda",
      "DefenderLeft": "Defesa esquerda", "DefenderCentre": "Defesa central", "DefenderRight": "Defesa direita", "DMCentre": "Médio def. central",
      "MidLeft": "Médio esquerdo", "MidCentre": "Médio centro", "MidRight": "Médio direito", "AMLeft": "Médio of. esquerdo",
      "AMCentre": "Médio of. centro", "AMRight": "Médio of. direito", "Striker": "Avançado centro", "WingBackLeft": "Médio-ala esquerdo",
      "WingBackRight": "Médio-ala direito"}
def attr_name(k):
    """Nome do atributo/posição para a tela: português pela tabela PT, espanhol pela ATTR_ES, inglês separando o nome interno (FirstTouch -> First Touch)."""
    if LANG == "en" or (LANG == "es" and k not in ATTR_ES):
        import re as _re
        return _re.sub(r"(?<=[a-z])(?=[A-Z])", " ", k).replace("Freekicks", "Free kicks").replace("Workrate", "Work rate")
    if LANG == "es":
        return ATTR_ES[k]
    return PT.get(k, k)


def coach_name(key, pt, en):
    """Nome de atributo de treino (staff) no idioma da interface."""
    return en if LANG == "en" else COACH_ES.get(key, en) if LANG == "es" else pt


def move_name(b, nm):
    """Nome de movimento preferido no idioma da interface (nm = 'Português (English)')."""
    if LANG == "es":
        return MOVES_ES[b] if b < len(MOVES_ES) else "bit %d (no usado)" % b
    if LANG == "en":
        return nm[nm.index("(") + 1:].rstrip(")") if "(" in nm else nm.replace("não usado", "unused")
    return nm


OPS = {"": None, "=": lambda a, b: a == b, ">": lambda a, b: a > b, "<": lambda a, b: a < b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b}
GAME_DATE_VT = 0x00E0EF14
FAV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favoritos.json")
FREEZE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "congelados.json")


def to_int(s, default=None):
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return default


class Engine:
    def __init__(self, progress=lambda m: None):
        pid = mcfm.find_pid(mcfm.PROCESS_NAME)
        if not pid:
            raise RuntimeError(T('O fm2005.exe não está aberto. Abra o jogo e carregue o save.'))
        self.proc = mcfm.Proc(pid)
        self.game = mcfm.Game(self.proc)
        progress(T('Varrendo jogadores...'))
        self.players = self.game.scan()
        self.freezer = mcfm.Freezer(self.proc)
        self.by_addr = {q["addr"]: q for q in self.players}
        progress(T('Lendo data do jogo...'))
        self.game_date = self._find_game_date()
        progress(T('Lendo países...'))
        self.nation_names = {}
        for n in self.game.scan_objs(self.game.VTABLES["NATION"]):
            self.nation_names[n] = self.game._name_at(n, [32, 8])
        self.nation_continent, self.continents = {}, []
        for n in self.nation_names:
            cont = self.proc.u32(n + 144)   # NATION+144 -> CONTINENT (vtable 00E5AC34); nome em +28 -> +8
            name = (self.game._name_at(cont, [28, 8]) or self.game._name_at(cont, [40, 8])) if cont and 0x01000000 < cont < 0x7FFF0000 else ""
            if not self.game._utf16_ok(name): name = ""
            self.nation_continent[n] = name
            if name and name not in self.continents: self.continents.append(name)
        self.continents.sort()
        progress(T('Lendo competições...'))
        self.comps = []
        for c in self.game.comps(""):
            c["nation"] = self.nation_names.get(self.proc.u32(c["addr"] + 72), "")
            c["kind"] = self.comp_kind(c)
            c["rep0"] = self.comp_values(c["addr"])["rep"]
            self.comps.append(c)
        # nível das ligas: dentro de cada país, ordena as ligas por reputação (1 = maior); empate = mesmo nível
        by_nation = {}
        for c in self.comps:
            if c["kind"] == "liga":
                by_nation.setdefault(c["nation"], []).append(c)
        for lst in by_nation.values():
            level, last = 0, None
            for c in sorted(lst, key=lambda x: -x["rep0"]):
                if c["rep0"] != last:
                    level += 1; last = c["rep0"]
                c["level"] = level
        progress(T('Lendo dados dos jogadores...'))
        self.cache = {}
        for q in self.players:
            b = self.proc.read(q["addr"], mcfm.PLAYER_STRUCT_SIZE + pd(q))
            if len(b) < 300 + pd(q):
                continue
            dob_raw = struct.unpack_from("<I", b, PLAYER["DateOfBirth"] + pd(q))[0]
            self.cache[q["addr"]] = dict(
                ca=struct.unpack_from("<h", b, 20)[0], pa=struct.unpack_from("<h", b, 22)[0],
                age=self._age(dob_raw), nat=self.nation_names.get(struct.unpack_from("<I", b, 256 + pd(q))[0], ""))
        progress(T('Montando elencos...'))
        self.squads, self.player_club, self.teams = {}, {}, []
        self._build_squads()
        self.favorites = []
        self._load_favs()

    # --- data do jogo (classe GAME_DATE)
    GAME_DATE_ADDR = 0x01017028  # SI_DATE global lido pelo código do jogo (fm2005.exe @00658CC0)

    def _find_game_date(self):
        """1) objeto SI_DATE global em endereço fixo; 2) fallback: data mais frequente entre os
        carimbos SI_SHORT_DATE do calendário (= dia anterior) + 1."""
        b = self.proc.read(self.GAME_DATE_ADDR, 12)
        if len(b) == 12 and struct.unpack_from("<I", b, 0)[0] == self.game.VTABLES["SI_DATE"]:
            day, y = struct.unpack_from("<HH", b, 4)
            if 2004 <= y <= 2040 and day < 366:
                return datetime.date(y, 1, 1) + datetime.timedelta(days=day)
        import re
        from collections import Counter
        c = Counter()
        rx = re.compile(b"\xb4\xd3\xc4\x00(..)(..)", re.DOTALL)
        for base, d in self.game._blobs():
            for m in rx.finditer(d):
                day = struct.unpack("<H", m.group(1))[0]; y = struct.unpack("<H", m.group(2))[0]
                if 2004 <= y <= 2040 and day < 366:
                    c[(y, day)] += 1
        if c:
            (y, d), n = c.most_common(1)[0]
            if n >= 50:
                return datetime.date(y, 1, 1) + datetime.timedelta(days=d + 1)
        return datetime.date(2004, 7, 1)

    def set_game_date(self, dt):
        self.game_date = dt
        for q in self.players:
            if q["addr"] in self.cache:
                b = self.proc.read(poff(q, PLAYER["DateOfBirth"]), 4)
                if len(b) == 4:   # jogador pode ter sido liberado da memória (aposentou / virada de temporada)
                    self.cache[q["addr"]]["age"] = self._age(struct.unpack("<I", b)[0])

    def _age(self, raw):
        y, d = raw >> 16, raw & 0xFFFF
        if not (1900 < y < 2100 and d < 366):
            return 0
        dob = datetime.date(y, 1, 1) + datetime.timedelta(days=d)
        return int((self.game_date - dob).days // 365.25)

    # --- elencos
    def _build_squads(self):
        g, p = self.game, self.proc
        for team in g.scan_objs(g.VTABLES["TEAM"]):
            club = p.u32(team + 44)
            if not club:
                continue
            kind = p.u8(team + 48)
            name = g._name_at(club, [32, 8])
            if not name:
                continue
            self.teams.append(dict(team=team, club=club, name=name, kind=kind))
            hdr = p.read(team, 256)
            best = []
            for off in range(0, 252, 4):
                v = struct.unpack_from("<I", hdr, off)[0]
                if not (0x01000000 < v < 0x7FFF0000):
                    continue
                for data in (v, p.u32(v + 4) or 0):
                    if not (0x01000000 < data < 0x7FFF0000):
                        continue
                    buf = p.read(data, 4 * 64)
                    found = []
                    for i in range(0, len(buf) - 3, 4):
                        a = struct.unpack_from("<I", buf, i)[0]
                        if a in self.by_addr:
                            found.append(self.by_addr[a])
                        elif found or i >= 12:
                            break
                    if len(found) > len(best):
                        best = found
            if best:
                lst = self.squads.setdefault(club, [])
                for q in best:
                    if q["addr"] not in [x["addr"] for x in lst]:
                        lst.append(q)
                        self.player_club.setdefault(q["addr"], name)

    def current_contract(self, pl):
        cs = self.game.contracts(pl)
        if not cs:
            return None
        club_name = self.club_of(pl)
        for c in cs:
            if self.game._name_at(c["club"], [32, 8]) == club_name:
                return c
        return cs[0]

    def club_of(self, pl):
        return self.player_club.get(pl["addr"], "")

    def main_clubs(self):
        seen = {}
        for c in self.teams:
            if c["kind"] == 0:
                seen.setdefault(c["club"], c)
        return list(seen.values())

    # --- filtros
    def filter_players(self, text, age=None, ca=None, pa=None, nat="", club=""):
        t = strip_accents(text).lower()
        n = strip_accents(nat).lower()
        cl = strip_accents(club).lower()
        out = []
        for q in self.players:
            if t and t not in q["key"]:
                continue
            if cl and cl not in strip_accents(self.club_of(q)).lower():
                continue
            c = self.cache.get(q["addr"])
            if not c:
                continue
            ok = True
            for (op, val), key in ((age, "age"), (ca, "ca"), (pa, "pa")):
                if op and val is not None and not OPS[op](c[key], val):
                    ok = False; break
            if ok and n and n not in strip_accents(c["nat"]).lower():
                ok = False
            if ok:
                out.append(q)
        return out

    def club_values(self, c):
        g, p = self.game, self.proc
        club, team = c["club"], c["team"]
        fin = p.u32(club + 212)
        full = bool(fin) and p.u32(fin) == g.VTABLES["CLUB_FINANCE"]
        k = g.CURRENCY
        return dict(rep=struct.unpack("<H", p.read(team + 92, 2))[0], training=p.u8(club + 168), academy=p.u8(club + 164),
                    youth=p.u8(club + 165), status=p.u8(club + 167),
                    avg=p.i32(club + 172), min=p.i32(club + 176), max=p.i32(club + 180),
                    balance=int(p.i32(fin + 4) * k) if fin else None,
                    transfer=int(p.i32(fin + 16) * k) if full else None, remaining=int(p.i32(fin + 20) * k) if full else None,
                    wage=int(p.i32(fin + 116) * k) if full else None, used=int(p.i32(fin + 124) * k) if full else None,
                    wage_left=int((p.i32(fin + 116) - p.i32(fin + 124)) * k) if full else None, full=full)

    def apply_club(self, c, vals, nolimit=False):
        """Escreve no clube os campos preenchidos (vazios são ignorados). Valores de dinheiro como o jogo mostra.
        nolimit=True deixa reputação até 65535 e instalações até 255 (experimental)."""
        g, p = self.game, self.proc
        club, team = c["club"], c["team"]
        v = {k: to_int(x) for k, x in vals.items()}
        rep_max, tr_max = (65535, 127) if nolimit else (10000, 20)   # nunca 255: como byte com sinal vira -1 e corrompe o jogo
        if v.get("rep") is not None: p.write(team + 92, struct.pack("<H", max(0, min(rep_max, v["rep"]))))
        if v.get("status") is not None: p.w_u8(club + 167, max(1, min(3, v["status"])))
        if v.get("training") is not None: p.w_u8(club + 168, max(0, min(tr_max, v["training"])))
        if v.get("academy") is not None: p.w_u8(club + 164, max(0, min(tr_max, v["academy"])))
        if v.get("youth") is not None: p.w_u8(club + 165, max(0, min(tr_max, v["youth"])))
        for key, off in (("avg", 172), ("min", 176), ("max", 180)):
            if v.get(key) is not None: p.write(club + off, struct.pack("<i", v[key]))
        fin = p.u32(club + 212); k = g.CURRENCY
        if fin and v.get("balance") is not None:
            p.write(fin + 4, struct.pack("<i", int(v["balance"] / k)))
        if fin and p.u32(fin) == g.VTABLES["CLUB_FINANCE"]:
            for key, off in (("transfer", 16), ("remaining", 20), ("wage", 116)):
                if v.get(key) is not None:
                    p.write(fin + off, struct.pack("<i", int(v[key] / k)))

    def club_nation(self, c):
        n = self.proc.u32(c["club"] + 160)
        return self.nation_names.get(n, "") if n else ""

    def filter_clubs(self, text, crit, nation=""):
        t, nt = strip_accents(text).lower(), strip_accents(nation).lower()
        out = []
        for c in self.main_clubs():
            if t and t not in strip_accents(c["name"]).lower():
                continue
            if nt and nt not in strip_accents(self.club_nation(c)).lower():
                continue
            v = self.club_values(c)
            ok = True
            for key, (op, val) in crit.items():
                if op and val is not None:
                    if v.get(key) is None or not OPS[op](v[key], val):
                        ok = False; break
            if ok:
                out.append(c)
        return out

    NATION_FIELDS = {"rep": (196, "u16"), "dev": (172, "u8"), "importance": (174, "u8"), "league": (175, "u8"), "economy": (177, "u8")}

    def nation_values(self, a):
        p = self.proc
        return dict(rep=struct.unpack("<H", p.read(a + 196, 2))[0], dev=p.u8(a + 172), importance=p.u8(a + 174),
                    league=p.u8(a + 175), economy=p.u8(a + 177))

    def apply_nation(self, a, vals, nolimit=False):
        p = self.proc
        v = {k: to_int(x) for k, x in vals.items()}
        if v.get("rep") is not None: p.write(a + 196, struct.pack("<H", max(0, min(65535 if nolimit else 10000, v["rep"]))))
        mx = 127 if nolimit else 20   # nunca 255 (vira -1 e corrompe o jogo)
        for k in ("dev", "importance", "league", "economy"):
            if v.get(k) is not None:
                p.w_u8(a + self.NATION_FIELDS[k][0], max(0, min(mx, v[k])))

    def filter_nations(self, text, crit, continent=""):
        t = strip_accents(text).lower()
        out = []
        for a, name in self.nation_names.items():
            if not name or (t and t not in strip_accents(name).lower()):
                continue
            if continent and self.nation_continent.get(a, "") != continent:
                continue
            v = self.nation_values(a)
            ok = True
            for key, (op, val) in crit.items():
                if op and val is not None and not OPS[op](v[key], val):
                    ok = False; break
            if ok:
                out.append(dict(addr=a, name=name, rep=v["rep"]))
        return out

    COMP_REP = 96  # COMP+96 int32 = reputação 0-20 (Série A 15, Rio 13, SP 14, Copa do Brasil 14 — a confirmar no editor)

    def comp_values(self, a):
        return dict(rep=self.proc.i32(a + self.COMP_REP))

    def apply_comp(self, a, vals, nolimit=False):
        v = to_int(vals.get("rep"))
        if v is not None:
            self.proc.write(a + self.COMP_REP, struct.pack("<i", max(0, min(127 if nolimit else 20, v))))

    COMP_KINDS = [("", "Todos"), ("liga", "Liga"), ("copa", "Copa nacional"), ("supercopa", "Supercopa"), ("copa_liga", "Copa da liga"),
                  ("internacional", "Internacional / continental"), ("amistoso", "Amistoso"), ("base", "Base / reservas")]

    @staticmethod
    def comp_kind(c):
        """Classifica pelo nome da classe do jogo (ex.: ITA_A, ITA_CUP, EUR_CHAMPIONS_LEAGUE) + país."""
        n = c.get("cls", "").upper()
        if any(k in n for k in ("FRIENDLY",)): return "amistoso"
        if any(k in n for k in ("UNDER", "U19", "U21", "U20", "U17", "YOUTH", "RESERVE", "JUNIOR", "PRIMAVERA")): return "base"
        if any(k in n for k in ("CHAMPIONS_LEAGUE", "UEFA", "INTERTOTO", "LIBERTADORES", "SUDAMERICANA", "MERCOSUR", "WWCLUB", "INTER_", "WC_", "EUR_", "CONCACAF", "AFC_", "CAF_", "OFC_", "WORLD", "OLYMPIC", "COPA_AMERICA", "EURO_", "ASIAN", "AFRICAN", "GOLD_CUP", "CONFEDERATION", "ROYAL_LEAGUE")) or not c.get("nation"):
            return "internacional"
        if "SUPER_CUP" in n or "SUPERCUP" in n or "CHARITY" in n or "COMMUNITY" in n: return "supercopa"
        if "LEAGUE_CUP" in n or "LGE_CUP" in n: return "copa_liga"
        if "CUP" in n or "TROPHY" in n or "SHIELD" in n or "COPA" in n or "POKAL" in n or "COUPE" in n: return "copa"
        return "liga"

    def filter_comps(self, text, nation, crit, kind="", level=""):
        t, nt = strip_accents(text).lower(), strip_accents(nation).lower()
        out = []
        for c in self.comps:
            if t and t not in strip_accents(c["name"]).lower():
                continue
            if nt and nt not in strip_accents(c["nation"]).lower():
                continue
            if kind and c.get("kind") != kind:
                continue
            if level:
                lv = c.get("level")
                if lv is None or (level == "5+" and lv < 5) or (level != "5+" and lv != int(level)):
                    continue
            v = self.comp_values(c["addr"])
            ok = True
            for key, (op, val) in crit.items():
                if op and val is not None and not OPS[op](v[key], val):
                    ok = False; break
            if ok:
                out.append(dict(c, rep=v["rep"]))
        return out

    # --- congelar campos de clube / país / competição
    CLUB_SPECS = {"rep": ("team", 92, "<H", T('Reputação')), "status": ("club", 167, "B", T('Status')), "training": ("club", 168, "B", T('Treino')),
                  "academy": ("club", 164, "B", T('Academia')), "youth": ("club", 165, "B", T('Jovens')),
                  "avg": ("club", 172, "<i", T('Público médio')), "min": ("club", 176, "<i", T('Público mín')), "max": ("club", 180, "<i", T('Público máx')),
                  "balance": ("fin", 4, "<i", T('Saldo')), "transfer": ("fin", 16, "<i", T('Orç. transferências')),
                  "remaining": ("fin", 20, "<i", T('Restante transf.')), "wage": ("fin", 116, "<i", T('Orç. salarial'))}
    NATION_SPECS = {"rep": (196, "<H", T('Reputação')), "dev": (172, "B", T('Desenvolvimento')), "importance": (174, "B", T('Importância')),
                    "league": (175, "B", T('Nível liga')), "economy": (177, "B", T('Fator econômico'))}

    def _pack(self, fmt, v, nolimit):
        if fmt == "B": v = max(0, min(127 if nolimit else 20, v))
        elif fmt == "<H": v = max(0, min(65535 if nolimit else 10000, v))
        return struct.pack(fmt, v)

    def freeze_club(self, c, vals, nolimit=False):
        n = 0
        for key, (where, off, fmt, lab) in self.CLUB_SPECS.items():
            v = to_int(vals.get(key))
            if v is None:
                continue
            if where == "fin":
                raw = int(v / self.game.CURRENCY)
                res = (lambda club=c["club"], off=off: (self.proc.u32(club + 212) + off) if self.proc.u32(club + 212) else None)
                data = struct.pack(fmt, raw)
            else:
                base = c["team"] if where == "team" else c["club"]
                res = (lambda b=base + off: b)
                data = self._pack(fmt, v, nolimit) if fmt != "<i" else struct.pack(fmt, v)
            self.freezer.add("club:%08X:%s" % (c["club"], key), T('Clube %s — %s = %s') % (c["name"], lab, v), res, data); n += 1
            self.remember("club:%08X:%s" % (c["club"], key), kind="club", ident=c["name"], what=key, value=v, nolimit=nolimit)
        return n

    def freeze_nation(self, a, name, vals, nolimit=False):
        n = 0
        for key, (off, fmt, lab) in self.NATION_SPECS.items():
            v = to_int(vals.get(key))
            if v is None:
                continue
            self.freezer.add("nation:%08X:%s" % (a, key), T('País %s — %s = %s') % (name, lab, v), (lambda b=a + off: b), self._pack(fmt, v, nolimit)); n += 1
            self.remember("nation:%08X:%s" % (a, key), kind="nation", ident=name, what=key, value=v, nolimit=nolimit)
        return n

    def freeze_comp(self, c, vals, nolimit=False):
        v = to_int(vals.get("rep"))
        if v is None:
            return 0
        v = max(0, min(127 if nolimit else 20, v))
        self.freezer.add("comp:%08X:rep" % c["addr"], T('Competição %s — Reputação = %s') % (c["name"], v), (lambda b=c["addr"] + 96: b), struct.pack("<i", v))
        self.remember("comp:%08X:rep" % c["addr"], kind="comp", ident=c["name"], what="rep", value=v, nolimit=nolimit)
        return 1

    def freeze_staff_attr(self, st, key, value):
        g = self.game
        d = self.proc.u32(st["addr"] + g.STAFF["DataPtr"])
        for off, k, pt, en, fine in g.COACH_ATTRS:
            if k == key and d:
                fk = "staff:%08X:%s" % (st["addr"], k)
                self.freezer.add(fk, "%s — %s = %d" % (st["name"], coach_name(k, pt, en), value), (lambda a=d + off: a), struct.pack("<b", g.coach_raw(value, fine)))
                self.remember(fk, kind="staff", ident="%s|%s" % (st["name"], st["dob"]), what=k, value=value)
                return True
        return False

    def freeze_board(self, h, m, v, what="board"):
        off = 52 if what == "fans" else 28
        key = "human:%08X:%s" % (h["addr"], what)
        lab = T("%s — confiança da torcida = %d") if what == "fans" else T("%s — confiança da diretoria = %d")
        self.freezer.add(key, lab % (h["name"], v), (lambda a=m + off: a), struct.pack("<H", max(0, min(10000, v))))
        self.remember(key, kind="human", ident=h["name"], what=what, value=v)

    # --- persistência dos congelamentos (congelados.json): identidade por nome, recriados ao carregar
    def freeze_export(self):
        meta = getattr(self, "freeze_meta", {})
        out = []
        with self.freezer.lock:
            for k, it in self.freezer.items.items():
                if k in meta:
                    m = dict(meta[k]); m["data"] = it["data"].hex(); out.append(m)
        return out

    def freeze_restore(self, entries):
        """Recria congelamentos salvos. Devolve (recriados, não encontrados)."""
        ok, miss = 0, []
        by_fav = {self._fav_key(q): q for q in self.players}
        clubs = {c["name"]: c for c in self.main_clubs()}
        nations = {n: a for a, n in self.nation_names.items()}
        comps = {c["name"]: c for c in self.comps}
        staff = None; humans = None
        for m in entries:
            try:
                kind = m.get("kind")
                if kind == "player":
                    pl = by_fav.get(m["ident"])
                    if not pl: miss.append(m["ident"]); continue
                    self.set_freeze(pl, m["what"], True, m.get("value"))
                    if m["what"] == "attrs" and m.get("data"):
                        with self.freezer.lock:
                            it = self.freezer.items.get(self.key(pl, "attrs"))
                            if it: it["data"] = bytes.fromhex(m["data"])
                elif kind == "club":
                    c = clubs.get(m["ident"])
                    if not c: miss.append(m["ident"]); continue
                    self.freeze_club(c, {m["what"]: m["value"]}, m.get("nolimit", False))
                elif kind == "nation":
                    a = nations.get(m["ident"])
                    if not a: miss.append(m["ident"]); continue
                    self.freeze_nation(a, m["ident"], {m["what"]: m["value"]}, m.get("nolimit", False))
                elif kind == "comp":
                    c = comps.get(m["ident"])
                    if not c: miss.append(m["ident"]); continue
                    self.freeze_comp(c, {"rep": m["value"]}, m.get("nolimit", False))
                elif kind == "staff":
                    if staff is None: staff = {"%s|%s" % (s["name"], s["dob"]): s for s in self.game.staff()}
                    st = staff.get(m["ident"])
                    if not st: miss.append(m["ident"]); continue
                    self.freeze_staff_attr(st, m["what"], int(m["value"]))
                elif kind == "human":
                    if humans is None: humans = {h["name"]: h for h in self.game.humans()}
                    h = humans.get(m["ident"])
                    md = self.game.manager_details(h["team"]) if h else None
                    if not md: miss.append(m["ident"]); continue
                    self.freeze_board(h, md, int(m["value"]), m.get("what", "board"))
                else:
                    continue
                ok += 1
            except Exception:
                miss.append(str(m.get("ident")))
        return ok, miss

    def freeze_field(self, kind, obj, key, value, nolimit=False):
        """Congela um único campo de clube/país/competição (value = número digitado)."""
        if kind == "club":
            return self.freeze_club(obj, {key: value}, nolimit)
        if kind == "nation":
            return self.freeze_nation(obj["addr"], obj["name"], {key: value}, nolimit)
        return self.freeze_comp(obj, {key: value}, nolimit)

    def obj_key(self, kind, obj):
        if kind == "club":
            return "club:%08X:" % obj["club"]
        return "%s:%08X:" % (kind, obj["addr"])

    def is_frozen_field(self, kind, obj, key):
        return (self.obj_key(kind, obj) + key) in self.freezer.items

    def unfreeze_prefix(self, prefix):
        with self.freezer.lock:
            for k in [k for k in self.freezer.items if k.startswith(prefix)]:
                self.freezer.items.pop(k, None)

    # --- favoritos (persistem em favoritos.json por id+nome)
    def _fav_key(self, q):
        return "%s|%s" % (self.proc.i32(q["addr"] + PLAYER["Id"]), q["name"])

    def _load_favs(self):
        try:
            keys = set(json.load(open(FAV_FILE, encoding="utf-8")))
        except Exception:
            return
        for q in self.players:
            if self._fav_key(q) in keys:
                self.favorites.append(q)

    def save_favs(self):
        try:
            json.dump([self._fav_key(q) for q in self.favorites], open(FAV_FILE, "w", encoding="utf-8"), ensure_ascii=False)
        except Exception:
            pass

    # --- congelamentos
    def key(self, pl, what):
        return "%08X:%s" % (pl["addr"], what)

    def frozen(self, pl, what):
        return self.key(pl, what) in self.freezer.items

    def remember(self, key, **meta):
        """Guarda como recriar um congelamento em outra sessão (identidade por nome, não por endereço)."""
        if not hasattr(self, "freeze_meta"):
            self.freeze_meta = {}
        self.freeze_meta[key] = meta

    def set_freeze(self, pl, what, on, value=None):
        k = self.key(pl, what)
        if not on:
            with self.freezer.lock:
                self.freezer.items.pop(k, None)
            return
        self.remember(k, kind="player", ident=self._fav_key(pl), what=what, value=value)
        g, p = self.game, self.proc
        a = pl["addr"]
        if what == "cond":
            v = max(0, min(10000, value if value is not None else 10000))
            self.freezer.add(k, T('%s — condição %d') % (pl["name"], v), (lambda a=a: a + PLAYER["Condition"]), struct.pack("<h", int(v)))
        elif what == "morale":
            v = max(1, min(127, value if value is not None else 20))
            self.freezer.add(k, T('%s — moral %d') % (pl["name"], v), (lambda a=a: a + PLAYER["Morale"]), struct.pack("<H", v))
        elif what == "attrs":
            lo, hi = SKILL_RANGE
            sk = g.skills_base(pl)
            if sk:
                self.freezer.add(k, T('%s — atributos') % pl["name"], (lambda q=pl: g.skills_base(q) + lo), p.read(sk + lo, hi - lo))
        elif what.startswith("skill:"):
            name = what[6:]
            if name in PERSONALITY:
                v = max(0, min(255, value if value is not None else 20))
                def res(a=a, i=PERSONALITY.index(name)):
                    pdp = p.u32(poff(pl, PLAYER["PersonDataPtr"])); return pdp + 24 + i if pdp else None
                self.freezer.add(k, "%s — %s = %d" % (pl["name"], attr_name(name), v), res, struct.pack("<B", v))
            else:
                v = value if value is not None else 20
                shown = v
                if name in RAW_SKILLS and 1 <= v <= 20:
                    v = mcfm.display_to_raw(v)          # valor do jogo -> escala fina
                v = max(-128, min(127, v))
                self.freezer.add(k, "%s — %s = %s" % (pl["name"], attr_name(name), shown),
                                 (lambda q=pl, off=ALL_SKILL_OFFSETS[name]: (g.skills_base(q) + off) if g.skills_base(q) else None), struct.pack("<b", v))
        elif what == "heal":
            def res(a=a):
                s = p.u32(a + PLAYER["StatusPtr"]); return s + 12 if s else None
            self.freezer.add(k, T('%s — sem lesão') % pl["name"], res, b"\x00")
        elif what == "unban":
            def res(a=a):
                s = p.u32(a + PLAYER["StatusPtr"]); return s + 24 if s else None
            self.freezer.add(k, T('%s — sem suspensão') % pl["name"], res, b"\x00")

    def freeze_list(self):
        with self.freezer.lock:
            return [(k, it["label"]) for k, it in self.freezer.items.items()]


# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.eng = None
        self.title(T('MCFM05 Reborn — FM 2005'))
        # tamanho padrão ~1350x860; se você redimensionar, o tamanho fica salvo em janela.json e é reaberto igual
        self.geo_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "janela.json")
        self.saved_geo = None
        try:
            self.saved_geo = json.load(open(self.geo_file)).get("geometry_v2")
        except Exception:
            pass
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.cur_player = self.cur_club = self.cur_nation = self.cur_comp = None
        self.cur_contract = None
        self.mass_target = ("fav", None)
        topbar = ttk.Frame(self); topbar.pack(fill="x", padx=6, pady=4)
        self.btn_load = ttk.Button(topbar, text=T('⟳  Carregar do jogo (FM 2005 aberto, save carregado)'), command=self.load_engine)
        self.btn_load.pack(side="left")
        ttk.Label(topbar, text=T("Idioma / Language")).pack(side="right", padx=(8, 2))
        self.lang_var = tk.StringVar(value=dict(LANGS).get(LANG, "English"))
        cb = ttk.Combobox(topbar, textvariable=self.lang_var, values=[n for _, n in LANGS], width=10, state="readonly"); cb.pack(side="right")
        cb.bind("<<ComboboxSelected>>", lambda e: (set_lang(next(c for c, n in LANGS if n == self.lang_var.get())), messagebox.showinfo("MCFM05 Reborn", T("Reinicie o programa para aplicar o idioma."))))
        self.load_info = tk.StringVar(value=T('Nada carregado.'))
        ttk.Label(topbar, textvariable=self.load_info).pack(side="left", padx=10)
        ttk.Label(topbar, text=T('Data do jogo:')).pack(side="left", padx=(20, 2))
        self.date_var = tk.StringVar()
        ttk.Entry(topbar, textvariable=self.date_var, width=11).pack(side="left")
        ttk.Button(topbar, text=T('Corrigir data'), command=self.fix_date).pack(side="left", padx=4)

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True)
        self.nb = nb
        self.tab_players = ttk.Frame(nb); nb.add(self.tab_players, text=T('Jogadores'))
        self.tab_clubs = ttk.Frame(nb); nb.add(self.tab_clubs, text=T('Clubes'))
        self.tab_nations = ttk.Frame(nb); nb.add(self.tab_nations, text=T('Países'))
        self.tab_comps = ttk.Frame(nb); nb.add(self.tab_comps, text=T('Competições'))
        self.tab_staff = ttk.Frame(nb); nb.add(self.tab_staff, text=T('Staff'))
        self.tab_humans = ttk.Frame(nb); nb.add(self.tab_humans, text=T('Treinadores'))
        # Edição em massa: uma aba com sub-abas
        self.tab_massroot = ttk.Frame(nb); nb.add(self.tab_massroot, text=T('Edição em massa'))
        self.nb_mass = ttk.Notebook(self.tab_massroot); self.nb_mass.pack(fill="both", expand=True)
        self.tab_mass = ttk.Frame(self.nb_mass); self.nb_mass.add(self.tab_mass, text=T('Jogadores'))
        self.tab_cmass = ttk.Frame(self.nb_mass); self.nb_mass.add(self.tab_cmass, text=T('Clubes'))
        self.tab_nmass = ttk.Frame(self.nb_mass); self.nb_mass.add(self.tab_nmass, text=T('Países'))
        self.tab_kmass = ttk.Frame(self.nb_mass); self.nb_mass.add(self.tab_kmass, text=T('Competições'))
        self.tab_smass = ttk.Frame(self.nb_mass); self.nb_mass.add(self.tab_smass, text=T('Staff'))
        self.tab_ret = ttk.Frame(nb); nb.add(self.tab_ret, text=T('Aposentadorias'))
        self.tab_frozen = ttk.Frame(nb); nb.add(self.tab_frozen, text=T('Congelados'))
        self.tab_favs = ttk.Frame(nb); nb.add(self.tab_favs, text=T('★ Favoritos'))
        self.status = tk.StringVar(value=T("Pronto. Nada é alterado no jogo sem 'Salvar no jogo'. Salve o save antes de editar."))
        self.cmass, self.nmass, self.kmass, self.smass = [], [], [], []
        self.cur_comp = None
        self.build_players(); self.build_clubs(); self.build_nations(); self.build_comps(); self.build_staff(); self.build_humans(); self.build_favs(); self.build_ret(); self.build_mass(); self.build_cmass(); self.build_nmass(); self.build_kmass(); self.build_smass(); self.build_frozen()
        self.fit_window()
        self.after(5000, self.tick_date)
        bottom = ttk.Frame(self); bottom.pack(fill="x", side="bottom")
        ttk.Button(bottom, text="created by %s — %s %s" % (AUTHOR, VERSION, BUILD), command=self.show_about).pack(side="right", padx=6, pady=2)
        ttk.Label(bottom, textvariable=self.status, anchor="w").pack(side="left", fill="x", expand=True, padx=4)
        self.after(1500, self.refresh_frozen)

    def load_engine(self):
        if self.eng and self.eng.freeze_list():
            if not messagebox.askyesno(T('Recarregar'), T('Há congelamentos ativos; recarregar vai desligá-los. Continuar?')):
                return
        self.btn_load.config(state="disabled")
        try:
            def progress(m):
                self.load_info.set(m); self.update()
            self.eng = Engine(progress)
        except Exception as e:
            messagebox.showerror("MCFM05 Reborn", str(e)); self.load_info.set(T('Falhou: %s') % e)
            self.btn_load.config(state="normal"); return
        self.btn_load.config(state="normal", text=T('⟳  Recarregar do jogo'))
        self.load_info.set(T('%d jogadores, %d clubes, %d países, %d competições') % (len(self.eng.players), len(self.eng.squads), len(self.eng.nation_names), len(self.eng.comps)))
        self.date_var.set(self.eng.game_date.strftime("%d/%m/%Y"))
        self.cur_player = self.cur_club = self.cur_nation = self.cur_comp = None
        self.p_results = []; self.p_list.delete(0, "end"); self.c_list.delete(0, "end"); self.n_list.delete(0, "end")
        self.cmass.clear(); self.nmass.clear(); self.kmass.clear(); self.smass.clear(); self.refresh_mass(); self.refresh_cmass(); self.refresh_nmass(); self.refresh_kmass(); self.refresh_smass()
        self.staff_cache = None
        self.status.set(T("Carregado. Nada é alterado no jogo sem 'Salvar no jogo'. Salve o save antes de editar."))
        self.after(200, self.restore_freezes)

    def fix_date(self):
        if not self.eng:
            return
        try:
            dt = datetime.datetime.strptime(self.date_var.get().strip(), "%d/%m/%Y").date()
        except ValueError:
            messagebox.showerror(T('Data'), T('Use o formato dd/mm/aaaa.')); return
        self.eng.set_game_date(dt); self.status.set(T('Data do jogo definida: %s (idades recalculadas)') % dt.strftime("%d/%m/%Y"))
        if self.p_results: self.show_player_results()

    def fit_window(self):
        """Tamanho padrão: o necessário para mostrar a aba Jogadores inteira (atributos, posições, salvar), limitado à tela.
        Se o usuário já redimensionou alguma vez, usa o tamanho salvo em janela.json."""
        self.update_idletasks()
        # faz o canvas dos atributos pedir o tamanho real do conteúdo (senão ele não conta no tamanho da janela)
        self.attr_canvas.config(width=self.attr_grid.winfo_reqwidth() + 4, height=self.attr_grid.winfo_reqheight() + 4)
        self.update_idletasks()
        if self.saved_geo:
            self.geometry(self.saved_geo); return
        w = min(self.winfo_reqwidth() + 40, self.winfo_screenwidth() - 20)
        h = min(self.winfo_reqheight() + 40, self.winfo_screenheight() - 80)
        self.geometry("%dx%d+%d+%d" % (w, h, max(0, (self.winfo_screenwidth() - w) // 2), 10))

    def report_callback_exception(self, exc, val, tb):
        import traceback
        txt = "".join(traceback.format_exception(exc, val, tb))
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "erro.log"), "a", encoding="utf-8") as f:
                f.write(txt + "\n")
        except Exception:
            pass
        messagebox.showerror(T('MCFM05 Reborn — erro'), txt[-1200:])

    def _on_close(self):
        self.save_freezes()
        try:
            json.dump({"geometry_v2": self.geometry()}, open(self.geo_file, "w"))
        except Exception:
            pass
        self.destroy()

    def goto_mass(self, sub):
        self.nb.select(self.tab_massroot); self.nb_mass.select(sub)

    def need(self):
        if not self.eng:
            messagebox.showinfo("MCFM05 Reborn", T("Clique em 'Carregar do jogo' primeiro.")); return False
        self.sync_date()
        return True

    def sync_date(self):
        """Relê a data do jogo (ela muda enquanto você joga) e recalcula as idades se mudou."""
        try:
            d = self.eng._find_game_date()
        except Exception:
            return
        if d != self.eng.game_date:
            self.eng.set_game_date(d)
            self.date_var.set(d.strftime("%d/%m/%Y"))

    # ------------------------------------------------------------ util
    def crit_row(self, parent, row, label, var_op, var_val, width=8):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=3, pady=1)
        ttk.Combobox(parent, textvariable=var_op, values=list(OPS.keys()), width=3, state="readonly").grid(row=row, column=1)
        ttk.Entry(parent, textvariable=var_val, width=width).grid(row=row, column=2, padx=2)

    def crit(self, var_op, var_val):
        return (var_op.get(), to_int(var_val.get()))

    # ------------------------------------------------------------ Jogadores
    def build_players(self):
        f = self.tab_players
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        flt = ttk.LabelFrame(left, text=T('Busca e filtros (vazio = ignora)')); flt.pack(fill="x")
        ttk.Label(flt, text=T('Nome')).grid(row=0, column=0, sticky="e", padx=3)
        self.p_search = ttk.Entry(flt, width=24); self.p_search.grid(row=0, column=1, columnspan=2, sticky="w")
        self.p_search.bind("<Return>", lambda e: self.search_players())
        self.f_age_op, self.f_age = tk.StringVar(), tk.StringVar()
        self.f_ca_op, self.f_ca = tk.StringVar(), tk.StringVar()
        self.f_pa_op, self.f_pa = tk.StringVar(), tk.StringVar()
        self.crit_row(flt, 1, T('Idade'), self.f_age_op, self.f_age)
        self.crit_row(flt, 2, "CA", self.f_ca_op, self.f_ca)
        self.crit_row(flt, 3, "PA", self.f_pa_op, self.f_pa)
        ttk.Label(flt, text=T('Nacionalidade')).grid(row=4, column=0, sticky="e", padx=3)
        self.f_nat = ttk.Entry(flt, width=16); self.f_nat.grid(row=4, column=1, columnspan=2, sticky="w")
        ttk.Label(flt, text=T('Clube')).grid(row=5, column=0, sticky="e", padx=3)
        self.f_club = ttk.Entry(flt, width=16); self.f_club.grid(row=5, column=1, columnspan=2, sticky="w"); self.f_club.bind("<Return>", lambda e: self.search_players())
        ttk.Button(flt, text=T('Buscar / filtrar'), command=self.search_players).grid(row=6, column=0, columnspan=3, pady=4)
        self.p_list = tk.Listbox(left, width=58, height=30, selectmode="extended", exportselection=False)
        self.p_list.pack(fill="y", expand=True)
        self.p_list.bind("<<ListboxSelect>>", self.select_player)
        self.p_results = []
        b = ttk.Frame(left); b.pack(fill="x")
        ttk.Button(b, text=T('★ Adicionar selecionados aos favoritos'), command=self.add_favs).pack(side="left", pady=3)

        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.p_title = ttk.Label(right, text=T('Selecione um jogador'), font=("Segoe UI", 12, "bold")); self.p_title.pack(anchor="w")
        save = ttk.Frame(right); save.pack(side="bottom", fill="x", pady=6)   # sempre visível, embaixo
        ttk.Button(save, text=T('💾  Salvar no jogo (estado + dados + atributos deste jogador)'), command=self.save_player).pack(side="left")
        ttk.Button(save, text=T('Descartar (recarregar do jogo)'), command=self.load_player).pack(side="left", padx=8)

        dd = ttk.LabelFrame(right, text=T('Dados')); dd.pack(fill="x", pady=4)
        ttk.Label(dd, text=T('Nascimento (dd/mm/aaaa)')).grid(row=0, column=0, sticky="e", padx=4)
        self.v_dob = tk.StringVar(); ttk.Entry(dd, textvariable=self.v_dob, width=12).grid(row=0, column=1, sticky="w")
        ttk.Label(dd, text=T('Nacionalidade')).grid(row=0, column=2, sticky="e", padx=(16, 4))
        self.v_nat = tk.StringVar(); self.cb_nat = ttk.Combobox(dd, textvariable=self.v_nat, width=28); self.cb_nat.grid(row=0, column=3, sticky="w")
        ttk.Label(dd, text=T('(digite para procurar; precisa ser o nome exato de um país)'), foreground="#555").grid(row=0, column=4, padx=6)
        ttk.Button(dd, text=T('⚽ Movimentos preferidos…'), command=self.pick_moves).grid(row=0, column=5, padx=8)
        self.v_ret = tk.BooleanVar()
        ttk.Checkbutton(dd, text=T('Afastado do futebol internacional (aposentado da seleção)'), variable=self.v_ret).grid(row=1, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        self.v_retire = tk.BooleanVar()
        ttk.Checkbutton(dd, text=T('RET — vai se aposentar (desmarque para cancelar; marcar não é possível)'), variable=self.v_retire).grid(row=2, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        ttk.Label(dd, text=T('Se MARCAR alguém: salve o jogo e recarregue o save antes de continuar jogando. Desmarcar não precisa.'), foreground="#a55").grid(row=1, column=3, columnspan=2, sticky="w", padx=6)

        ct = ttk.LabelFrame(right, text=T("Contrato")); ct.pack(fill="x", pady=4)
        ttk.Label(ct, text=T("Clube")).grid(row=0, column=0, sticky="e", padx=4)
        self.v_cclub = tk.StringVar(); ttk.Label(ct, textvariable=self.v_cclub, width=26).grid(row=0, column=1, sticky="w")
        ttk.Label(ct, text=T("Salário / semana")).grid(row=0, column=2, sticky="e", padx=(16, 4))
        self.v_wage = tk.StringVar(); ttk.Entry(ct, textvariable=self.v_wage, width=10).grid(row=0, column=3, sticky="w")
        ttk.Label(ct, text=T("Início (dd/mm/aaaa)")).grid(row=0, column=4, sticky="e", padx=(16, 4))
        self.v_cstart = tk.StringVar(); ttk.Entry(ct, textvariable=self.v_cstart, width=11).grid(row=0, column=5, sticky="w")
        ttk.Label(ct, text=T("Fim (dd/mm/aaaa)")).grid(row=0, column=6, sticky="e", padx=(16, 4))
        self.v_cend = tk.StringVar(); ttk.Entry(ct, textvariable=self.v_cend, width=11).grid(row=0, column=7, sticky="w")
        ttk.Label(ct, text=T("(salário como o jogo mostra; o jogo arredonda a exibição)"), foreground="#555").grid(row=1, column=1, columnspan=5, sticky="w", padx=4)
        ttk.Label(ct, text=T("Transferir para")).grid(row=2, column=0, sticky="e", padx=4, pady=(4, 2))
        self.v_tclub = tk.StringVar(); e = ttk.Entry(ct, textvariable=self.v_tclub, width=26); e.grid(row=2, column=1, sticky="w")
        e.bind("<Return>", lambda ev: self.transfer_player())
        ttk.Button(ct, text=T("➡ Transferir (imediato, sem 'Salvar')"), command=self.transfer_player).grid(row=2, column=2, columnspan=2, sticky="w", padx=4)
        ttk.Label(ct, text=T("(digite parte do nome do clube; abre uma lista para escolher; o contrato atual passa para o clube novo)"), foreground="#555").grid(row=2, column=4, columnspan=4, sticky="w", padx=4)

        top = ttk.LabelFrame(right, text=T('Estado')); top.pack(fill="x", pady=4)
        self.v = {}
        for i, (k, lab) in enumerate([("cond", T('Condição (0-10000)')), ("morale", T('Moral (1-20)')), ("ca", "CA"), ("pa", "PA")]):
            ttk.Label(top, text=lab).grid(row=0, column=i * 2, sticky="e", padx=4, pady=2)
            self.v[k] = tk.StringVar(); ttk.Entry(top, textvariable=self.v[k], width=7).grid(row=0, column=i * 2 + 1, sticky="w")
        self.fz = {k: tk.BooleanVar() for k in ("cond", "attrs", "morale", "heal", "unban")}
        ttk.Checkbutton(top, text=T('Congelar condição no valor acima'), variable=self.fz["cond"], command=lambda: self.toggle_freeze("cond")).grid(row=1, column=0, columnspan=4, sticky="w", padx=4)
        ttk.Checkbutton(top, text=T('Congelar moral no valor acima'), variable=self.fz["morale"], command=lambda: self.toggle_freeze("morale")).grid(row=1, column=4, columnspan=4, sticky="w", padx=4)

        st = ttk.LabelFrame(right, text=T('Lesão / suspensão')); st.pack(fill="x", pady=4)
        self.p_inj = ttk.Label(st, text="-"); self.p_inj.grid(row=0, column=0, columnspan=4, sticky="w", padx=4)
        ttk.Button(st, text=T('Curar lesão'), command=lambda: self.heal(False)).grid(row=1, column=0, padx=4, pady=2)
        ttk.Button(st, text=T('Curar (forçado)'), command=lambda: self.heal(True)).grid(row=1, column=1, padx=4)
        ttk.Button(st, text=T('Remover suspensão'), command=self.unban).grid(row=1, column=2, padx=4)
        ttk.Checkbutton(st, text=T('Manter curado'), variable=self.fz["heal"], command=lambda: self.toggle_freeze("heal")).grid(row=2, column=0, sticky="w", padx=4)
        ttk.Checkbutton(st, text=T('Manter sem suspensão'), variable=self.fz["unban"], command=lambda: self.toggle_freeze("unban")).grid(row=2, column=1, sticky="w", padx=4)

        at = ttk.LabelFrame(right, text=T("Atributos — valor do jogo 1-20; 'bruto' = -128..127 (127 = sobre-humano). Personalidade: ordem provável, o jogo não a exibe"))
        at.pack(fill="both", expand=True, pady=4)
        self.raw_mode = tk.BooleanVar(value=False)
        bar = ttk.Frame(at); bar.pack(fill="x")
        ttk.Checkbutton(bar, text=T('bruto'), variable=self.raw_mode, command=self.load_player).pack(side="left", padx=4)
        ttk.Label(bar, text=T('Todos =')).pack(side="left", padx=(12, 2))
        self.all_val = tk.StringVar(); ttk.Entry(bar, textvariable=self.all_val, width=5).pack(side="left")
        ttk.Button(bar, text=T('Preencher todos'), command=lambda: self.fill_group(None, self.all_val.get())).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Restaurar backup'), command=self.restore).pack(side="left", padx=12)
        ttk.Checkbutton(bar, text=T('Congelar atributos'), variable=self.fz["attrs"], command=lambda: self.toggle_freeze("attrs")).pack(side="left", padx=10)
        ttk.Button(bar, text=T('❄ Congelar só alguns atributos…'), command=self.pick_freeze).pack(side="left", padx=4)
        # área rolável (barras aparecem se a janela for pequena)
        canvas = tk.Canvas(at, highlightthickness=0); self.attr_canvas = canvas
        vsb = ttk.Scrollbar(at, orient="vertical", command=canvas.yview); hsb = ttk.Scrollbar(at, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y"); hsb.pack(side="bottom", fill="x"); canvas.pack(side="left", fill="both", expand=True)
        grid = ttk.Frame(canvas); canvas.create_window((0, 0), window=grid, anchor="nw"); self.attr_grid = grid
        grid.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(-int(ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        self.sk, self.grp_val = {}, {}
        layout = {"Técnicos": (0, 0), "Mentais": (0, 1), "Físicos": (0, 2), "Personalidade": (1, 2), "Goleiro": (0, 3), "Ocultos / pés": (1, 3),
                  "Posições": (0, 4), "Posições novas (a confirmar)": (0, 5)}
        for gname, keys in GROUPS.items():
            r0, c0 = layout.get(gname, (0, 4))
            lf = ttk.LabelFrame(grid, text=T(gname)); lf.grid(row=r0, column=c0, sticky="nw", padx=3, pady=3)
            self.grp_val[gname] = tk.StringVar()
            ttk.Entry(lf, textvariable=self.grp_val[gname], width=5).grid(row=0, column=0, sticky="e")
            ttk.Button(lf, text=T('todos deste grupo'), command=lambda gn=gname: self.fill_group(gn, self.grp_val[gn].get())).grid(row=0, column=1, pady=2)
            for r, k in enumerate(keys, start=1):
                ttk.Label(lf, text=attr_name(k)).grid(row=r, column=0, sticky="e", padx=2)
                self.sk[k] = tk.StringVar()
                ttk.Entry(lf, textvariable=self.sk[k], width=5).grid(row=r, column=1, padx=2)

    def search_players(self):
        if not self.need(): return
        self.p_results = self.eng.filter_players(self.p_search.get(), self.crit(self.f_age_op, self.f_age),
                                                 self.crit(self.f_ca_op, self.f_ca), self.crit(self.f_pa_op, self.f_pa), self.f_nat.get(), self.f_club.get())
        self.show_player_results()

    def show_player_results(self):
        self.p_list.delete(0, "end")
        for q in self.p_results:
            c = self.eng.cache.get(q["addr"], {})
            self.p_list.insert("end", T('%s  [%s]  %s anos  CA %s / PA %s  %s') % (
                q["name"], self.eng.club_of(q), c.get("age", "?"), c.get("ca", "?"), c.get("pa", "?"), c.get("nat", "")))
        self.status.set(T('%d jogadores') % len(self.p_results))

    def selected_players(self):
        return [self.p_results[i] for i in self.p_list.curselection()]

    def select_player(self, _=None):
        sel = self.p_list.curselection()
        if not sel:
            return
        self.cur_player = self.p_results[sel[0]]
        self.load_player()

    def load_player(self):
        pl = self.cur_player
        if not pl:
            return
        g = self.eng.game
        inf = g.info(pl)
        c = self.eng.cache.get(pl["addr"], {})
        self.p_title.config(text=T('%s   (%s)   nasc. %s — %s anos — %s') % (pl["name"], self.eng.club_of(pl), inf["dob"], c.get("age", "?"), c.get("nat", "")))
        self.v["cond"].set(inf["condition"]); self.v["morale"].set(inf["morale"])
        self.v_dob.set(inf["dob"]); self.v_nat.set(c.get("nat", ""))
        self.v_ret.set(g.int_retired(pl)); self.v_retire.set(g.retiring(pl) or bool(g.retire_entries(pl)))
        ctr = self.eng.current_contract(pl)
        self.cur_contract = ctr
        if ctr:
            self.v_cclub.set(g._name_at(ctr["club"], [32, 8]) or "?")
            self.v_wage.set(int(round(ctr["wage"] * g.CURRENCY)))
            self.v_cstart.set(fm_date(ctr["start"])); self.v_cend.set(fm_date(ctr["end"]))
        else:
            self.v_cclub.set(T("(sem contrato)")); self.v_wage.set(""); self.v_cstart.set(""); self.v_cend.set("")
        if not self.cb_nat["values"]:
            self.cb_nat["values"] = sorted(n for n in self.eng.nation_names.values() if n)
        sk = g.skills_base(pl)
        if sk:
            for k, off in list(POSITIONS.items()) + list(NEWPOS.items()):
                self.sk[k].set(self.eng.proc.u8(sk + off))
        self.v["ca"].set(inf["ca"]); self.v["pa"].set(inf["pa"])
        self.p_inj.config(text=g.injuries(pl).replace("\n", "   |   "))
        for k, (d, raw) in inf["skills"].items():
            self.sk[k].set(raw if (self.raw_mode.get() and raw is not None) else d)
        for k, v in g.personality(pl).items():
            self.sk[k].set(v)
        for k in self.fz:
            self.fz[k].set(self.eng.frozen(pl, k))

    def fill_group(self, gname, val):
        if to_int(val) is None:
            return
        if to_int(val) > 20:
            self.raw_mode.set(True)
        keys = (list(SKILLS.keys()) + PERSONALITY) if gname is None else GROUPS[gname]   # "todos" não mexe nas posições
        for k in keys:
            self.sk[k].set(val)

    def save_player(self):
        if not self.need(): return
        pl = self.cur_player
        if not pl:
            return
        self.apply_to(pl, self.v["cond"].get(), self.v["morale"].get(), self.v["ca"].get(), self.v["pa"].get(),
                      {k: v.get() for k, v in self.sk.items()}, self.raw_mode.get())
        msg = self.apply_data(pl, self.v_dob.get(), self.v_nat.get())
        msg += self.apply_contract(pl)
        if self.v_ret.get() != self.eng.game.int_retired(pl):
            msg += "  | " + self.eng.game.set_int_retired(pl, self.v_ret.get())
        if not self.v_retire.get() and (self.eng.game.retiring(pl) or self.eng.game.retire_entries(pl)):
            n = self.eng.game.cancel_retirement(pl)
            msg += "  | " + T("aposentadoria cancelada (%d registro(s) removidos da lista do jogo)") % n
        self.status.set(T('Salvo no jogo: %s%s') % (pl["name"], msg))
        self.load_player()

    def transfer_player(self):
        """Escolhe o clube de destino numa lista e move o jogador selecionado (elenco, TEAM e contrato)."""
        if not self.need() or not self.cur_player: return
        pl = self.cur_player
        txt = strip_accents(self.v_tclub.get()).lower().strip()
        if not txt:
            messagebox.showinfo(T("Transferência"), T("Digite parte do nome do clube de destino.")); return
        opts = sorted([c for c in self.eng.main_clubs() if txt in strip_accents(c["name"]).lower()], key=lambda c: c["name"])
        if not opts:
            messagebox.showinfo(T("Transferência"), T("Nenhum clube encontrado com '%s'.") % self.v_tclub.get()); return
        win = tk.Toplevel(self); win.title(T("Transferir %s para…") % pl["name"]); win.transient(self); win.grab_set()
        ttk.Label(win, text=T("Escolha o clube de destino:")).pack(anchor="w", padx=8, pady=6)
        lb = tk.Listbox(win, width=50, height=min(20, max(5, len(opts))), exportselection=False); lb.pack(padx=8)
        for c in opts: lb.insert("end", "%s  [%s]" % (c["name"], self.eng.club_nation(c)))
        lb.selection_set(0)
        def go():
            sel = lb.curselection()
            if not sel: return
            c = opts[sel[0]]; win.destroy()
            if not messagebox.askyesno(T("Confirmar"), T("Transferir %s de %s para %s agora?\n(Salve o jogo antes. O jogador sai do elenco antigo e entra no novo.)") % (pl["name"], self.eng.club_of(pl) or "?", c["name"])): return
            ok, realloc = self.eng.game.transfer(pl, c["team"], c["club"], self.eng.current_contract(pl))
            if not ok:
                messagebox.showerror(T("Transferência"), T("Não consegui transferir (lista de elenco não reconhecida).")); return
            for lst in self.eng.squads.values():
                if pl in lst: lst.remove(pl)
            self.eng.squads.setdefault(c["club"], []).append(pl); self.eng.player_club[pl["addr"]] = c["name"]
            self.v_tclub.set(""); self.load_player(); self.show_player_results()
            self.status.set(T("%s transferido para %s") % (pl["name"], c["name"]))
            if realloc:
                messagebox.showinfo(T("Transferência"), T("A lista de elenco de %s estava cheia e foi realocada. Salve o jogo e recarregue o save antes de continuar jogando.") % c["name"])
            else:
                messagebox.showinfo(T("Transferência"), T("Feito. Abra o elenco do clube no jogo para conferir; se a tela não mudar, troque de tela ou avance um dia. Recomendado: salvar e recarregar o save."))
        bar = ttk.Frame(win); bar.pack(pady=8)
        ttk.Button(bar, text=T("✔ Transferir"), command=go).pack(side="left", padx=4)
        ttk.Button(bar, text=T("Cancelar"), command=win.destroy).pack(side="left", padx=4)
        lb.bind("<Double-1>", lambda e: go())

    def apply_contract(self, pl):
        ctr = getattr(self, "cur_contract", None)
        if not ctr:
            return ""
        p, g, msg = self.eng.proc, self.eng.game, ""
        w = to_int(self.v_wage.get())
        if w is not None:
            p.write(ctr["addr"] + 16, struct.pack("<i", max(0, int(w / g.CURRENCY))))
        for var, off, lab in ((self.v_cstart, 24, "início"), (self.v_cend, 32, "fim")):
            txt = var.get().strip()
            if not txt:
                continue
            try:
                d = datetime.datetime.strptime(txt, "%d/%m/%Y").date()
                p.write(ctr["addr"] + off, struct.pack("<I", to_fm_date(d)))
            except ValueError:
                msg += T("  (%s do contrato: data inválida, use dd/mm/aaaa)") % T(lab)
        return msg

    def apply_data(self, pl, dob, nat):
        """Nascimento e nacionalidade. Devolve texto de aviso (vazio se ok)."""
        p, a, msg = self.eng.proc, pl["addr"], ""
        dob = dob.strip()
        if dob:
            try:
                d = datetime.datetime.strptime(dob, "%d/%m/%Y").date()
                p.write(poff(pl, PLAYER["DateOfBirth"]), struct.pack("<I", to_fm_date(d)))
                if a in self.eng.cache:
                    self.eng.cache[a]["age"] = self.eng._age(to_fm_date(d))
            except ValueError:
                msg += T('  (data inválida, use dd/mm/aaaa — não alterada)')
        nat = nat.strip()
        if nat:
            addr = next((x for x, n in self.eng.nation_names.items() if n == nat), None)
            if addr is None:
                addr = next((x for x, n in self.eng.nation_names.items() if strip_accents(n).lower() == strip_accents(nat).lower()), None)
            if addr is None:
                msg += T("  (país '%s' não encontrado — nacionalidade não alterada)") % nat
            else:
                p.write(poff(pl, PLAYER["Nationality"]), struct.pack("<I", addr))
                if a in self.eng.cache:
                    self.eng.cache[a]["nat"] = self.eng.nation_names[addr]
        return msg

    def apply_to(self, pl, cond, morale, ca, pa, skills, raw):
        """Escreve no jogo um conjunto de valores (campos vazios são ignorados)."""
        g, p = self.eng.game, self.eng.proc
        a = pl["addr"]
        if to_int(cond) is not None: p.w_i16(a + PLAYER["Condition"], max(0, min(10000, to_int(cond))))
        if to_int(morale) is not None: p.write(a + PLAYER["Morale"], struct.pack("<H", max(1, min(127, to_int(morale)))))
        if to_int(ca) is not None: p.w_i16(a + 20, to_int(ca))
        if to_int(pa) is not None: p.w_i16(a + 22, to_int(pa))
        if any(to_int(v) is not None for v in skills.values()):
            g.backup(pl)
            for k, v in skills.items():
                iv = to_int(v)
                if iv is None:
                    continue
                if k in PERSONALITY:
                    g.set_personality(pl, k, max(1, min(127, iv)))   # 1-20 normal; até 127 experimental (255 corrompe)
                else:
                    # modo bruto marcado -> escreve o byte; senão trata como valor do jogo (1-20) e converte;
                    # fora de 1..20 só faz sentido como bruto
                    g.set_skill(pl, k, iv, raw=(raw or iv > 20 or iv < 1))
            if self.eng.frozen(pl, "attrs"):
                self.eng.set_freeze(pl, "attrs", True)
        if pl["addr"] in self.eng.cache:
            self.eng.cache[pl["addr"]]["ca"] = p.i16(a + 20); self.eng.cache[pl["addr"]]["pa"] = p.i16(a + 22)

    def restore(self):
        if self.cur_player:
            self.status.set(self.eng.game.restore(self.cur_player)); self.load_player()

    def heal(self, force):
        if self.cur_player:
            self.status.set(self.eng.game.heal(self.cur_player, force=force)); self.load_player()

    def unban(self):
        if self.cur_player:
            self.status.set(self.eng.game.unban(self.cur_player, force=True)); self.load_player()

    def toggle_freeze(self, what):
        if not self.need(): self.fz[what].set(False); return
        pl = self.cur_player
        if not pl:
            self.fz[what].set(False); return
        val = to_int(self.v["cond"].get()) if what == "cond" else to_int(self.v["morale"].get()) if what == "morale" else None
        self.eng.set_freeze(pl, what, self.fz[what].get(), val)
        self.status.set(T('Congelamento %s: %s') % (T('ligado') if self.fz[what].get() else T('desligado'), pl["name"]))

    def pick_freeze(self):
        """Janela para escolher atributo por atributo o que congelar neste jogador (nos valores dos campos)."""
        if not self.need(): return
        pl = self.cur_player
        if not pl:
            messagebox.showinfo(T('Congelar'), T('Selecione um jogador primeiro.')); return
        win = tk.Toplevel(self); win.title(T('Congelar atributos — %s') % pl["name"]); win.transient(self)
        ttk.Label(win, text=T('Marque os atributos. Eles serão congelados NO VALOR que está no campo da aba Jogadores\n(edite o campo antes, se quiser outro valor). Desmarcar = descongelar.'),
                  justify="left").pack(anchor="w", padx=8, pady=6)
        grid = ttk.Frame(win); grid.pack(padx=8)
        vars_ = {}
        for col, (gname, keys) in enumerate(GROUPS.items()):
            lf = ttk.LabelFrame(grid, text=T(gname)); lf.grid(row=0, column=col, sticky="n", padx=3, pady=3)
            for k in keys:
                vars_[k] = tk.BooleanVar(value=self.eng.frozen(pl, "skill:" + k))
                ttk.Checkbutton(lf, text=attr_name(k), variable=vars_[k]).pack(anchor="w")
            def allg(keys=keys, on=True): [vars_[k].set(on) for k in keys]
            r = ttk.Frame(lf); r.pack()
            ttk.Button(r, text=T('todos'), width=6, command=lambda keys=keys: allg(keys, True)).pack(side="left")
            ttk.Button(r, text=T('nenhum'), width=7, command=lambda keys=keys: allg(keys, False)).pack(side="left")
        def apply():
            n = 0
            for k, var in vars_.items():
                on = var.get()
                if on:
                    val = to_int(self.sk[k].get())
                    if val is None:
                        continue
                    self.eng.set_freeze(pl, "skill:" + k, True, val); n += 1
                elif self.eng.frozen(pl, "skill:" + k):
                    self.eng.set_freeze(pl, "skill:" + k, False)
            self.status.set(T('%s: %d atributos congelados') % (pl["name"], n)); win.destroy()
        bar = ttk.Frame(win); bar.pack(pady=8)
        ttk.Button(bar, text=T('✔ Aplicar'), command=apply).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Cancelar'), command=win.destroy).pack(side="left", padx=4)

    def pick_moves(self):
        if not self.need(): return
        pl = self.cur_player
        if not pl:
            messagebox.showinfo(T('Movimentos'), T('Selecione um jogador primeiro.')); return
        g = self.eng.game
        mask = g.pref_moves(pl)
        win = tk.Toplevel(self); win.title(T('Movimentos preferidos — %s') % pl["name"]); win.transient(self)
        ttk.Label(win, text=T('Marque/desmarque e clique Salvar. Os 48 nomes são os do editor oficial (bits 48-63 não são usados pelo jogo).'),
                  justify="left").pack(anchor="w", padx=8, pady=6)
        grid = ttk.Frame(win); grid.pack(padx=8)
        vars_ = {}
        for i, (b, nm) in enumerate(PREF_MOVES):
            nm = move_name(b, nm)
            vars_[b] = tk.BooleanVar(value=bool(mask >> b & 1))
            ttk.Checkbutton(grid, text="%2d  %s" % (b, nm), variable=vars_[b]).grid(row=i % 16, column=i // 16, sticky="w", padx=6)
        def save():
            m = 0
            for b, v in vars_.items():
                if v.get(): m |= 1 << b
            g.set_pref_moves(pl, m)
            self.status.set(T('Movimentos preferidos salvos: %s (0x%X)') % (pl["name"], m)); win.destroy()
        bar = ttk.Frame(win); bar.pack(pady=8)
        ttk.Button(bar, text=T('💾 Salvar no jogo'), command=save).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Cancelar'), command=win.destroy).pack(side="left", padx=4)

    def add_favs(self):
        if not self.need(): return
        n = 0
        for q in self.selected_players():
            if q["addr"] not in [x["addr"] for x in self.eng.favorites]:
                self.eng.favorites.append(q); n += 1
        self.eng.save_favs(); self.refresh_mass()
        self.status.set(T('%d adicionados aos favoritos (%d no total)') % (n, len(self.eng.favorites)))

    # ------------------------------------------------------------ Clubes
    def build_clubs(self):
        f = self.tab_clubs
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        flt = ttk.LabelFrame(left, text=T('Busca e filtros (vazio = ignora)')); flt.pack(fill="x")
        ttk.Label(flt, text=T('Nome')).grid(row=0, column=0, sticky="e", padx=3)
        self.c_search = ttk.Entry(flt, width=24); self.c_search.grid(row=0, column=1, columnspan=2, sticky="w")
        self.c_search.bind("<Return>", lambda e: self.search_clubs())
        self.cf = {}
        for i, (k, lab) in enumerate([("rep", T('Reputação')), ("training", T('Treino')), ("academy", T('Academia')), ("youth", T('Camadas jovens')),
                                      ("balance", T('Saldo')), ("remaining", T('Orç. transf. restante')), ("wage_left", T('Orç. salarial livre'))], start=1):
            self.cf[k] = (tk.StringVar(), tk.StringVar())
            self.crit_row(flt, i, lab, self.cf[k][0], self.cf[k][1], width=12)
        ttk.Label(flt, text=T("País")).grid(row=9, column=0, sticky="e", padx=3)
        self.c_nation = ttk.Entry(flt, width=24); self.c_nation.grid(row=9, column=1, columnspan=2, sticky="w"); self.c_nation.bind("<Return>", lambda e: self.search_clubs())
        ttk.Button(flt, text=T('Buscar / filtrar'), command=self.search_clubs).grid(row=10, column=0, columnspan=3, pady=4)
        self.c_list = tk.Listbox(left, width=58, height=30, selectmode="extended", exportselection=False); self.c_list.pack(fill="y", expand=True)
        self.c_list.bind("<<ListboxSelect>>", self.select_club)
        self.c_results = []
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.c_title = ttk.Label(right, text=T('Selecione um clube'), font=("Segoe UI", 12, "bold")); self.c_title.pack(anchor="w")
        box = ttk.LabelFrame(right, text=T('Clube')); box.pack(fill="x", pady=4)
        self.cv = {}
        for i, (k, lab) in enumerate([("rep", T('Reputação (0-10000)')), ("status", T('Status (1 prof / 2 semi / 3 amador)')),
                                      ("training", T('Condições de treino (0-20)')), ("academy", T('Academia (0-20)')), ("youth", T('Camadas jovens (0-20)')),
                                      ("avg", T('Público médio')), ("min", T('Público mínimo')), ("max", T('Público máximo'))]):
            ttk.Label(box, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.cv[k] = tk.StringVar(); ttk.Entry(box, textvariable=self.cv[k], width=12).grid(row=i, column=1, sticky="w")
        fin = ttk.LabelFrame(right, text=T('Finanças (como o jogo mostra; orçamentos só em clubes jogáveis)')); fin.pack(fill="x", pady=4)
        for i, (k, lab) in enumerate([("balance", T('Saldo')), ("transfer", T('Orçamento de transferências')), ("remaining", T('Restante')),
                                      ("wage", T('Orçamento salarial / semana')), ("used", T('Salários usados / semana (leitura)'))]):
            ttk.Label(fin, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.cv[k] = tk.StringVar(); ttk.Entry(fin, textvariable=self.cv[k], width=16).grid(row=i, column=1, sticky="w")
        self.c_nolimit = tk.BooleanVar()
        ttk.Checkbutton(right, text=T('sem limites (reputação até 65535, treino/academia/jovens até 127) — experimental; 255 corrompe o jogo'),
                        variable=self.c_nolimit).pack(anchor="w")
        bar = ttk.Frame(right); bar.pack(fill="x", pady=4)
        ttk.Button(bar, text=T('💾  Salvar no jogo (este clube)'), command=self.save_club).pack(side="left", padx=4)
        ttk.Button(bar, text=T('❄ Escolher o que congelar…'), command=lambda: self.pick_obj_freeze("club", [self.cur_club] if self.cur_club else [], self.cv, self.c_nolimit)).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Descongelar este clube'), command=lambda: self.cur_club and (self.eng.unfreeze_prefix("club:%08X:" % self.cur_club["club"]), self.status.set(T('Descongelado')))).pack(side="left", padx=4)
        ttk.Button(bar, text=T('➕ Adicionar selecionados à lista em massa'), command=self.add_cmass).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Descartar'), command=self.load_club).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Ver jogadores do clube'), command=self.club_players).pack(side="left", padx=12)
        ttk.Button(bar, text=T('Editar elenco em massa'), command=self.club_mass).pack(side="left", padx=4)
        ttk.Label(right, text=T('Treino = CLUB+168, Academia = +164, Camadas jovens = +165 (confirmado com o editor oficial, Santos 17/18/19).'),
                  foreground="#555").pack(anchor="w", pady=6)

    def search_clubs(self):
        if not self.need(): return
        crit = {k: self.crit(v[0], v[1]) for k, v in self.cf.items()}
        self.c_results = self.eng.filter_clubs(self.c_search.get(), crit, self.c_nation.get())
        self.c_list.delete(0, "end")
        for c in self.c_results:
            v = self.eng.club_values(c)
            self.c_list.insert("end", T('%s  rep %d  tr %d/ac %d/jov %d  (%d jog.)') % (c["name"], v["rep"], v["training"], v["academy"], v["youth"], len(self.eng.squads.get(c["club"], []))) + "  [%s]" % self.eng.club_nation(c))
        self.status.set(T('%d clubes') % len(self.c_results))

    def select_club(self, _=None):
        sel = self.c_list.curselection()
        if sel:
            self.cur_club = self.c_results[sel[0]]; self.load_club()

    def load_club(self):
        c = self.cur_club
        if not c:
            return
        v = self.eng.club_values(c)
        self.c_title.config(text=c["name"])
        for k in ("rep", "status", "training", "academy", "youth", "avg", "min", "max", "balance", "transfer", "remaining", "wage", "used"):
            self.cv[k].set("" if v.get(k) is None else v[k])

    def save_club(self):
        if not self.need(): return
        c = self.cur_club
        if not c:
            return
        try:
            self.eng.apply_club(c, {k: self.cv[k].get() for k in self.cv}, nolimit=self.c_nolimit.get())
            self.status.set(T('Salvo no jogo: %s') % c["name"])
        except ValueError:
            messagebox.showerror(T('Valor inválido'), T('Confira os números.'))
        self.load_club()

    def save_clubs_mass(self):
        if not self.need(): return
        sel = [self.c_results[i] for i in self.c_list.curselection()]
        if not sel:
            messagebox.showinfo(T('Em massa'), T('Selecione um ou mais clubes na lista (Ctrl/Shift + clique).')); return
        if not messagebox.askyesno(T('Confirmar'), T('Aplicar os campos preenchidos em %d clubes?') % len(sel)):
            return
        vals = {k: self.cv[k].get() for k in self.cv}
        for c in sel:
            self.eng.apply_club(c, vals)
        self.status.set(T('Salvo no jogo em %d clubes') % len(sel)); self.search_clubs()

    def club_players(self):
        if not self.need(): return
        if self.cur_club:
            self.p_results = sorted(self.eng.squads.get(self.cur_club["club"], []), key=lambda q: q["name"])
            self.show_player_results(); self.nb.select(self.tab_players)

    def club_mass(self):
        if not self.need(): return
        if self.cur_club:
            self.mass_target = ("club", self.cur_club); self.refresh_mass(); self.goto_mass(self.tab_mass)

    # ------------------------------------------------------------ Países
    def build_nations(self):
        f = self.tab_nations
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        flt = ttk.LabelFrame(left, text=T('Busca e filtro')); flt.pack(fill="x")
        ttk.Label(flt, text=T('Nome')).grid(row=0, column=0, sticky="e", padx=3)
        self.n_search = ttk.Entry(flt, width=24); self.n_search.grid(row=0, column=1, columnspan=2, sticky="w")
        self.n_search.bind("<Return>", lambda e: self.search_nations())
        self.nf = {}
        for i, (k, lab) in enumerate([("rep", T('Reputação')), ("importance", T('Importância')), ("dev", T('Desenvolvimento')),
                                      ("economy", T('Fator econômico')), ("league", T('Nível campeonato'))], start=1):
            self.nf[k] = (tk.StringVar(), tk.StringVar())
            self.crit_row(flt, i, lab, self.nf[k][0], self.nf[k][1])
        ttk.Label(flt, text=T('Continente')).grid(row=7, column=0, sticky="e", padx=3)
        self.n_cont = tk.StringVar(value=T("Todos"))
        self.cb_cont = ttk.Combobox(flt, textvariable=self.n_cont, values=[T("Todos")], width=18, state="readonly"); self.cb_cont.grid(row=7, column=1, columnspan=2, sticky="w")
        ttk.Button(flt, text=T('Buscar / filtrar'), command=self.search_nations).grid(row=8, column=0, columnspan=3, pady=4)
        self.n_list = tk.Listbox(left, width=44, height=30, selectmode="extended", exportselection=False); self.n_list.pack(fill="y", expand=True)
        self.n_list.bind("<<ListboxSelect>>", self.select_nation)
        self.n_results = []
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.n_title = ttk.Label(right, text=T('Selecione um país'), font=("Segoe UI", 12, "bold")); self.n_title.pack(anchor="w")
        box = ttk.LabelFrame(right, text=T('Campos (confirmados com o editor oficial: Alemanha / Argélia)')); box.pack(fill="x", pady=4)
        self.nv = {}
        for i, (k, lab) in enumerate([("rep", T('Reputação (0-10000; provável)')), ("importance", T('Importância de jogo (0-20)')),
                                      ("dev", T('Estado de desenvolvimento (1 desenvolvido / 2 em desenvolvimento / 3 terceiro mundo)')),
                                      ("economy", T('Fator econômico (0-20)')), ("league", T('Nível do campeonato (0-20)'))]):
            ttk.Label(box, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.nv[k] = tk.StringVar(); ttk.Entry(box, textvariable=self.nv[k], width=10).grid(row=i, column=1, sticky="w")
        self.n_nolimit = tk.BooleanVar()
        ttk.Checkbutton(right, text=T('sem limites (reputação até 65535, campos 0-20 até 127) — experimental'), variable=self.n_nolimit).pack(anchor="w")
        bar = ttk.Frame(right); bar.pack(fill="x", pady=4)
        ttk.Button(bar, text=T('💾  Salvar no jogo (este país)'), command=self.save_nation).pack(side="left", padx=4)
        ttk.Button(bar, text=T('❄ Escolher o que congelar…'), command=lambda: self.pick_obj_freeze("nation", [self.cur_nation] if self.cur_nation else [], self.nv, self.n_nolimit)).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Descongelar este país'), command=lambda: self.cur_nation and (self.eng.unfreeze_prefix("nation:%08X:" % self.cur_nation["addr"]), self.status.set(T('Descongelado')))).pack(side="left", padx=4)
        ttk.Button(bar, text=T('➕ Adicionar selecionados à lista em massa'), command=self.add_nmass).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Descartar'), command=self.select_nation).pack(side="left", padx=4)
        ttk.Label(right, text=T('Reputação = NATION+196 (não exibida pelo jogo). Importância +174, desenvolvimento +172, economia +177, nível +175.'),
                  foreground="#555").pack(anchor="w", pady=6)

    def search_nations(self):
        if not self.need(): return
        self.cb_cont.config(values=[T("Todos")] + self.eng.continents)
        cont = "" if self.n_cont.get() == T("Todos") else self.n_cont.get()
        self.n_results = self.eng.filter_nations(self.n_search.get(), {k: self.crit(v[0], v[1]) for k, v in self.nf.items()}, cont)
        self.n_results.sort(key=lambda n: -n["rep"])
        self.n_list.delete(0, "end")
        for n in self.n_results:
            v = self.eng.nation_values(n["addr"])
            self.n_list.insert("end", T("%s  rep %d  imp %d  dev %d  eco %d  liga %d") % (n["name"], v["rep"], v["importance"], v["dev"], v["economy"], v["league"]) + ("  [%s]" % self.eng.nation_continent.get(n["addr"]) if self.eng.nation_continent.get(n["addr"]) else ""))
        self.status.set(T('%d países') % len(self.n_results))

    def select_nation(self, _=None):
        sel = self.n_list.curselection()
        if sel:
            self.cur_nation = self.n_results[sel[0]]
        n = self.cur_nation
        if not n:
            return
        self.n_title.config(text=n["name"])
        for k, v in self.eng.nation_values(n["addr"]).items():
            self.nv[k].set(v)

    def save_nation(self):
        if not self.need(): return
        n = self.cur_nation
        if n:
            self.eng.apply_nation(n["addr"], {k: v.get() for k, v in self.nv.items()}, nolimit=self.n_nolimit.get())
            self.status.set(T('Salvo no jogo: %s') % n["name"]); self.select_nation()

    # ------------------------------------------------------------ Staff
    def coach_label(self, key):
        for off, k, pt, en, fine in self.eng.game.COACH_ATTRS:
            if k == key:
                return coach_name(k, pt, en)
        return key

    def build_staff(self):
        f = self.tab_staff
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        flt = ttk.LabelFrame(left, text=T("Busca e filtro")); flt.pack(fill="x")
        ttk.Label(flt, text=T("Nome")).grid(row=0, column=0, sticky="e", padx=3)
        self.s_search = ttk.Entry(flt, width=24); self.s_search.grid(row=0, column=1, sticky="w"); self.s_search.bind("<Return>", lambda e: self.search_staff())
        ttk.Label(flt, text=T("Clube")).grid(row=1, column=0, sticky="e", padx=3)
        self.s_club = ttk.Entry(flt, width=24); self.s_club.grid(row=1, column=1, sticky="w"); self.s_club.bind("<Return>", lambda e: self.search_staff())
        ttk.Label(flt, text=T("Nacionalidade")).grid(row=2, column=0, sticky="e", padx=3)
        self.s_nation = ttk.Entry(flt, width=24); self.s_nation.grid(row=2, column=1, sticky="w"); self.s_nation.bind("<Return>", lambda e: self.search_staff())
        ttk.Button(flt, text=T("Buscar / filtrar"), command=self.search_staff).grid(row=3, column=0, columnspan=2, pady=4)
        self.s_list = tk.Listbox(left, width=52, height=30, selectmode="extended", exportselection=False); self.s_list.pack(fill="y", expand=True)
        self.s_list.bind("<<ListboxSelect>>", self.select_staff)
        self.s_results = []; self.cur_staff = None; self.staff_cache = None
        ttk.Button(left, text=T("➕ Adicionar selecionados à lista em massa"), command=self.add_smass).pack(anchor="w", pady=3)
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.s_title = ttk.Label(right, text=T("Selecione um membro do staff"), font=("Segoe UI", 12, "bold")); self.s_title.pack(anchor="w")
        save = ttk.Frame(right); save.pack(side="bottom", fill="x", pady=6)
        ttk.Button(save, text=T("💾  Salvar no jogo (este membro do staff)"), command=self.save_staff).pack(side="left")
        ttk.Button(save, text=T("Descartar"), command=self.select_staff).pack(side="left", padx=8)
        ttk.Button(save, text=T("❄ Escolher atributos a congelar…"), command=self.pick_staff_freeze).pack(side="left", padx=8)
        dd = ttk.LabelFrame(right, text=T("Dados")); dd.pack(fill="x", pady=4)
        self.sv = {}
        for i, (k, lab, ro) in enumerate([("club", T("Clube"), True), ("nation", T("Nacionalidade"), True), ("dob", T("Nascimento"), True),
                                           ("ca", T("CA"), False), ("pa", T("PA"), False), ("wage", T("Salário / semana"), False),
                                           ("start", T("Início do contrato (dd/mm/aaaa)"), False), ("end", T("Fim do contrato (dd/mm/aaaa)"), False)]):
            ttk.Label(dd, text=lab).grid(row=i % 4, column=(i // 4) * 2, sticky="e", padx=4, pady=2)
            self.sv[k] = tk.StringVar()
            (ttk.Label(dd, textvariable=self.sv[k], width=24) if ro else ttk.Entry(dd, textvariable=self.sv[k], width=12)).grid(row=i % 4, column=(i // 4) * 2 + 1, sticky="w")
        at = ttk.LabelFrame(right, text=T("Atributos de treino (0-20; os do editor oficial)")); at.pack(fill="both", expand=True, pady=4)
        bar = ttk.Frame(at); bar.pack(fill="x")
        ttk.Label(bar, text=T("Todos =")).pack(side="left", padx=(6, 2))
        self.s_all = tk.StringVar(); ttk.Entry(bar, textvariable=self.s_all, width=5).pack(side="left")
        ttk.Button(bar, text=T("Preencher todos"), command=lambda: [v.set(self.s_all.get()) for v in self.sa.values()]).pack(side="left", padx=4)
        self.s_nolimit = tk.BooleanVar()
        ttk.Checkbutton(bar, text=T("sem limites (até 127; atributos finos até 42) — experimental"), variable=self.s_nolimit).pack(side="left", padx=12)
        grid = ttk.Frame(at); grid.pack(fill="both", expand=True)
        self.sa = {}
        attrs = self.eng.game.COACH_ATTRS if self.eng else mcfm.Game.COACH_ATTRS
        for i, (off, k, pt, en, fine) in enumerate(attrs):
            col, row = (0 if i < 17 else 2), (i if i < 17 else i - 17)
            ttk.Label(grid, text=coach_name(k, pt, en)).grid(row=row, column=col, sticky="e", padx=4)
            self.sa[k] = tk.StringVar(); ttk.Entry(grid, textvariable=self.sa[k], width=5).grid(row=row, column=col + 1, padx=(2, 20))
        pb = ttk.LabelFrame(right, text=T("Personalidade")); pb.pack(fill="x", pady=4)
        self.sp = {}
        for i, k in enumerate(PERSONALITY):
            ttk.Label(pb, text=attr_name(k)).grid(row=i % 2, column=(i // 2) * 2, sticky="e", padx=4)
            self.sp[k] = tk.StringVar(); ttk.Entry(pb, textvariable=self.sp[k], width=5).grid(row=i % 2, column=(i // 2) * 2 + 1, sticky="w")

    def load_staff_cache(self):
        if self.staff_cache is None:
            self.status.set(T("Lendo staff...")); self.update_idletasks()
            self.staff_cache = self.eng.game.staff()
        return self.staff_cache

    def search_staff(self):
        if not self.need(): return
        t, c, n = strip_accents(self.s_search.get()).lower(), strip_accents(self.s_club.get()).lower(), strip_accents(self.s_nation.get()).lower()
        self.s_results = [s for s in self.load_staff_cache() if (not t or t in strip_accents(s["name"]).lower()) and (not c or c in strip_accents(s["club_name"]).lower())
                          and (not n or n in strip_accents(s["nation"] or "").lower())]
        self.s_results.sort(key=lambda s: s["name"])
        self.s_list.delete(0, "end")
        for s in self.s_results:
            self.s_list.insert("end", "%s  [%s]  CA %s / PA %s  %s" % (s["name"], s["club_name"] or "-", s["ca"], s["pa"], s["nation"]))
        self.status.set(T("%d membros do staff") % len(self.s_results))

    def select_staff(self, _=None):
        sel = self.s_list.curselection()
        if sel:
            self.cur_staff = self.s_results[sel[0]]
        st = self.cur_staff
        if not st:
            return
        g = self.eng.game
        self.s_title.config(text="%s (%s)" % (st["name"], st["club_name"] or "-"))
        self.sv["club"].set(st["club_name"]); self.sv["nation"].set(st["nation"]); self.sv["dob"].set(st["dob"])
        self.sv["ca"].set(g.p.i16(st["addr"] + g.STAFF["CA"])); self.sv["pa"].set(g.p.i16(st["addr"] + g.STAFF["PA"]))
        c = g.staff_contract(st); st["contract"] = c
        self.sv["wage"].set(int(round(c["wage"] * g.CURRENCY)) if c else ""); self.sv["start"].set(fm_date(c["start"]) if c else ""); self.sv["end"].set(fm_date(c["end"]) if c else "")
        for k, v in g.staff_attrs(st).items(): self.sa[k].set(v)
        for k, v in g.staff_personality(st).items(): self.sp[k].set(v)

    def apply_staff(self, st, data, attrs, pers, nolimit=False):
        g, p = self.eng.game, self.eng.proc
        a = st["addr"]
        fine_of = {k: fine for off, k, pt, en, fine in g.COACH_ATTRS}
        if to_int(data.get("ca")) is not None: p.w_i16(a + g.STAFF["CA"], to_int(data["ca"]))
        if to_int(data.get("pa")) is not None: p.w_i16(a + g.STAFF["PA"], to_int(data["pa"]))
        c = st.get("contract") or g.staff_contract(st)
        if c:
            w = to_int(data.get("wage"))
            if w is not None: p.write(c["addr"] + 16, struct.pack("<i", max(0, int(w / g.CURRENCY))))
            for key, off in (("start", 24), ("end", 32)):
                txt = (data.get(key) or "").strip()
                if txt:
                    try: p.write(c["addr"] + off, struct.pack("<I", to_fm_date(datetime.datetime.strptime(txt, "%d/%m/%Y").date())))
                    except ValueError: pass
        for k, v in attrs.items():
            iv = to_int(v)
            if iv is not None:
                # sem limites: byte com sinal → máx 127 (nunca 255 = -1); atributos "finos" (raw = 5*v-85) → máx 42
                mx = (42 if fine_of.get(k) else 127) if nolimit else 20
                g.set_staff_attr(st, k, max(0, min(mx, iv)))
        pd = p.u32(a + g.STAFF["PersonData"])
        if pd:
            for k, v in pers.items():
                iv = to_int(v)
                if iv is not None: p.w_u8(pd + 24 + PERSONALITY.index(k), max(1, min(127, iv)))

    def save_staff(self):
        if not self.need() or not self.cur_staff: return
        self.apply_staff(self.cur_staff, {k: v.get() for k, v in self.sv.items()}, {k: v.get() for k, v in self.sa.items()}, {k: v.get() for k, v in self.sp.items()}, nolimit=self.s_nolimit.get())
        self.status.set(T("Salvo no jogo: %s") % self.cur_staff["name"]); self.select_staff()

    def pick_staff_freeze(self):
        if not self.need() or not self.cur_staff: return
        st, g = self.cur_staff, self.eng.game
        win = tk.Toplevel(self); win.title(T("Congelar — %s") % st["name"]); win.transient(self)
        ttk.Label(win, text=T("Marque os atributos. Eles serão congelados NO VALOR que está no campo (preencha antes). Desmarcar = descongelar."), justify="left").pack(anchor="w", padx=8, pady=6)
        grid = ttk.Frame(win); grid.pack(padx=8)
        vars_ = {}
        for i, (off, k, pt, en, fine) in enumerate(g.COACH_ATTRS):
            vars_[k] = tk.BooleanVar(value=("staff:%08X:%s" % (st["addr"], k)) in self.eng.freezer.items)
            ttk.Checkbutton(grid, text=coach_name(k, pt, en), variable=vars_[k]).grid(row=i % 17, column=i // 17, sticky="w", padx=6)
        def apply():
            d = g.p.u32(st["addr"] + g.STAFF["DataPtr"]); n = 0
            for off, k, pt, en, fine in g.COACH_ATTRS:
                key = "staff:%08X:%s" % (st["addr"], k)
                if vars_[k].get():
                    v = to_int(self.sa[k].get())
                    if v is None or not d: continue
                    self.eng.freeze_staff_attr(st, k, v); n += 1
                else:
                    with self.eng.freezer.lock: self.eng.freezer.items.pop(key, None)
            self.status.set(T("%s: %d atributos congelados") % (st["name"], n)); win.destroy()
        bar = ttk.Frame(win); bar.pack(pady=8)
        ttk.Button(bar, text=T("✔ Aplicar"), command=apply).pack(side="left", padx=4)
        ttk.Button(bar, text=T("Cancelar"), command=win.destroy).pack(side="left", padx=4)

    def add_smass(self):
        if not self.need(): return
        n = 0
        for i in self.s_list.curselection():
            x = self.s_results[i]
            if x["addr"] not in [y["addr"] for y in self.smass]:
                self.smass.append(x); n += 1
        self.refresh_smass(); self.status.set(T("%d adicionados (%d na lista)") % (n, len(self.smass))); self.goto_mass(self.tab_smass)

    def build_smass(self):
        f = self.tab_smass
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("Staff na lista"), font=("Segoe UI", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(left); row.pack(fill="x")
        ttk.Button(row, text=T("Remover selecionados"), command=self.remove_smass).pack(side="left")
        ttk.Button(row, text=T("Limpar lista"), command=lambda: (self.smass.clear(), self.refresh_smass())).pack(side="left", padx=4)
        self.sm_list = tk.Listbox(left, width=52, height=32, selectmode="extended", exportselection=False); self.sm_list.pack(fill="y", expand=True)
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T("Campos vazios NÃO são alterados. Vale para todos da lista."), font=("Segoe UI", 10, "bold")).pack(anchor="w")
        dd = ttk.LabelFrame(right, text=T("Dados")); dd.pack(fill="x", pady=4)
        self.smv = {}
        for i, (k, lab) in enumerate([("ca", T("CA")), ("pa", T("PA")), ("wage", T("Salário / semana")), ("end", T("Fim do contrato (dd/mm/aaaa)"))]):
            ttk.Label(dd, text=lab).grid(row=0, column=i * 2, sticky="e", padx=4); self.smv[k] = tk.StringVar(); ttk.Entry(dd, textvariable=self.smv[k], width=12).grid(row=0, column=i * 2 + 1)
        at = ttk.LabelFrame(right, text=T("Atributos de treino (0-20)")); at.pack(fill="x", pady=4)
        bar = ttk.Frame(at); bar.pack(fill="x")
        ttk.Label(bar, text=T("Todos =")).pack(side="left", padx=(6, 2)); self.sm_all = tk.StringVar(); ttk.Entry(bar, textvariable=self.sm_all, width=5).pack(side="left")
        ttk.Button(bar, text=T("Preencher todos"), command=lambda: [v.set(self.sm_all.get()) for v in self.sma.values()]).pack(side="left", padx=4)
        self.sm_nolimit = tk.BooleanVar()
        ttk.Checkbutton(bar, text=T("sem limites (até 127; atributos finos até 42) — experimental"), variable=self.sm_nolimit).pack(side="left", padx=12)
        grid = ttk.Frame(at); grid.pack(fill="x")
        self.sma = {}
        attrs = mcfm.Game.COACH_ATTRS
        for i, (off, k, pt, en, fine) in enumerate(attrs):
            col, row = (0 if i < 17 else 2), (i if i < 17 else i - 17)
            ttk.Label(grid, text=coach_name(k, pt, en)).grid(row=row, column=col, sticky="e", padx=4)
            self.sma[k] = tk.StringVar(); ttk.Entry(grid, textvariable=self.sma[k], width=5).grid(row=row, column=col + 1, padx=(2, 20))
        pb = ttk.LabelFrame(right, text=T("Personalidade")); pb.pack(fill="x", pady=4)
        self.smp = {}
        for i, k in enumerate(PERSONALITY):
            ttk.Label(pb, text=attr_name(k)).grid(row=i % 2, column=(i // 2) * 2, sticky="e", padx=4)
            self.smp[k] = tk.StringVar(); ttk.Entry(pb, textvariable=self.smp[k], width=5).grid(row=i % 2, column=(i // 2) * 2 + 1, sticky="w")
        ttk.Button(right, text=T("💾  Salvar no jogo (todos da lista)"), command=self.save_smass).pack(anchor="w", pady=6)

    def refresh_smass(self):
        self.sm_list.delete(0, "end")
        for x in self.smass:
            self.sm_list.insert("end", "%s  [%s]  CA %s / PA %s" % (x["name"], x.get("club_name") or "-", x.get("ca"), x.get("pa")))

    def remove_smass(self):
        for i in sorted(self.sm_list.curselection(), reverse=True): del self.smass[i]
        self.refresh_smass()

    def save_smass(self):
        if not self.need(): return
        data = {k: v.get() for k, v in self.smv.items()}; attrs = {k: v.get() for k, v in self.sma.items()}; pers = {k: v.get() for k, v in self.smp.items()}
        if not self.smass or not any(to_int(x) is not None for x in list(data.values()) + list(attrs.values()) + list(pers.values())) and not data.get("end", "").strip():
            messagebox.showinfo(T("Em massa"), T("Preencha pelo menos um campo.")); return
        if not messagebox.askyesno(T("Confirmar"), T("Aplicar os campos preenchidos em %d membros do staff?") % len(self.smass)): return
        for st in self.smass: self.apply_staff(st, data, attrs, pers, nolimit=self.sm_nolimit.get())
        self.status.set(T("Salvo em %d membros do staff") % len(self.smass)); self.refresh_smass()

    # ------------------------------------------------------------ Treinadores humanos
    def build_humans(self):
        f = self.tab_humans
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T("Treinadores humanos (você)"), font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Button(left, text=T("Procurar no jogo"), command=self.search_humans).pack(anchor="w", pady=3)
        self.h_list = tk.Listbox(left, width=44, height=20, exportselection=False); self.h_list.pack(fill="y", expand=True)
        self.h_list.bind("<<ListboxSelect>>", self.select_human)
        self.h_results = []; self.cur_human = None
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.h_title = ttk.Label(right, text=T("Selecione um treinador"), font=("Segoe UI", 12, "bold")); self.h_title.pack(anchor="w")
        box = ttk.LabelFrame(right, text=T("Dados")); box.pack(fill="x", pady=4)
        self.hv = {}
        rows = [("club", T("Clube"), True), ("nation", T("Nacionalidade"), True), ("dob", T("Nascimento"), False),
                ("wage", T("Salário / semana"), False), ("start", T("Início do contrato (dd/mm/aaaa)"), False), ("end", T("Fim do contrato (dd/mm/aaaa)"), False),
                ("board", T("Confiança da diretoria (0-10000)"), False), ("fans", T("Confiança da torcida (0-10000)"), False)]
        for i, (k, lab, ro) in enumerate(rows):
            ttk.Label(box, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.hv[k] = tk.StringVar()
            (ttk.Label(box, textvariable=self.hv[k]) if ro else ttk.Entry(box, textvariable=self.hv[k], width=14)).grid(row=i, column=1, sticky="w")
            if k == "fans":
                self.h_fz_fans = tk.BooleanVar()
                ttk.Checkbutton(box, text=T("❄ congelar torcida neste valor"), variable=self.h_fz_fans, command=self.toggle_fans_freeze).grid(row=i, column=2, sticky="w", padx=8)
        pb = ttk.LabelFrame(right, text=T("Personalidade")); pb.pack(fill="x", pady=4)
        self.hp = {}
        for i, k in enumerate(PERSONALITY):
            ttk.Label(pb, text=attr_name(k)).grid(row=i % 4, column=(i // 4) * 2, sticky="e", padx=4)
            self.hp[k] = tk.StringVar(); ttk.Entry(pb, textvariable=self.hp[k], width=5).grid(row=i % 4, column=(i // 4) * 2 + 1, sticky="w")
        cf = ttk.LabelFrame(right, text=T("Demissão (botões rápidos — aplicam na hora)")); cf.pack(fill="x", pady=4)
        self.h_mode = tk.StringVar(value="default")
        for val, lab in (("default", T("Padrão do jogo (sem mexer, sem congelar)")), ("safe", T("NÃO será demitido (diretoria 9500, congelada)")), ("sack", T("SERÁ demitido (diretoria 0, congelada — leva até ~180 dias)"))):
            ttk.Radiobutton(cf, text=lab, value=val, variable=self.h_mode, command=self.apply_board_mode).pack(anchor="w", padx=6)
        bar = ttk.Frame(right); bar.pack(fill="x", pady=6)
        ttk.Button(bar, text=T("💾  Salvar no jogo (este treinador)"), command=self.save_human).pack(side="left", padx=4)
        ttk.Button(bar, text=T("Descartar"), command=self.select_human).pack(side="left", padx=4)
        ttk.Label(right, text=T("Confiança (0-10000; novo treinador começa em 7250, padrão 5000). Os textos da tela 'Confiança do Clube' seguem esse número com atraso de alguns dias. O jogo só considera demitir quando a diretoria está em 4275 ou menos E você tem 180+ dias no cargo."), foreground="#555", wraplength=620, justify="left").pack(anchor="w", pady=4)

    def search_humans(self):
        if not self.need(): return
        self.h_results = self.eng.game.humans()
        self.h_list.delete(0, "end")
        for h in self.h_results:
            self.h_list.insert("end", "%s  [%s]  %s" % (h["name"], h["club_name"] or "?", h["nation"]))
        self.status.set(T("%d treinadores humanos") % len(self.h_results))

    def select_human(self, _=None):
        sel = self.h_list.curselection()
        if sel:
            self.cur_human = self.h_results[sel[0]]
        h = self.cur_human
        if not h:
            return
        g = self.eng.game
        self.h_title.config(text=h["name"])
        self.hv["club"].set(h["club_name"]); self.hv["nation"].set(h["nation"]); self.hv["dob"].set(h["dob"])
        c = g.human_contract(h["addr"]); h["contract"] = c
        if c:
            self.hv["wage"].set(int(round(c["wage"] * g.CURRENCY))); self.hv["start"].set(fm_date(c["start"])); self.hv["end"].set(fm_date(c["end"]))
        else:
            self.hv["wage"].set(""); self.hv["start"].set(""); self.hv["end"].set("")
        m = g.manager_details(h["team"]); h["details"] = m
        if m:
            self.hv["board"].set(struct.unpack("<H", self.eng.proc.read(m + 28, 2))[0]); self.hv["fans"].set(struct.unpack("<H", self.eng.proc.read(m + 52, 2))[0])
        else:
            self.hv["board"].set(""); self.hv["fans"].set("")
        for k, v in g.human_personality(h["addr"]).items():
            self.hp[k].set(v)
        self.h_fz_fans.set(("human:%08X:fans" % h["addr"]) in self.eng.freezer.items)
        it = self.eng.freezer.items.get("human:%08X:board" % h["addr"])
        self.h_mode.set("default" if not it else ("safe" if struct.unpack("<H", it["data"])[0] >= 5000 else "sack"))

    def save_human(self):
        if not self.need() or not self.cur_human: return
        h, g, p = self.cur_human, self.eng.game, self.eng.proc
        c = h.get("contract")
        if c:
            w = to_int(self.hv["wage"].get())
            if w is not None: p.write(c["addr"] + 16, struct.pack("<i", max(0, int(w / g.CURRENCY))))
            for key, off in (("start", 24), ("end", 32)):
                txt = self.hv[key].get().strip()
                if txt:
                    try: p.write(c["addr"] + off, struct.pack("<I", to_fm_date(datetime.datetime.strptime(txt, "%d/%m/%Y").date())))
                    except ValueError: pass
        m = h.get("details")
        if m:
            for key, off in (("board", 28), ("fans", 52)):
                v = to_int(self.hv[key].get())
                if v is not None: p.write(m + off, struct.pack("<H", max(0, min(10000, v))))
        pd = p.u32(h["addr"] + g.HUMAN["PersonData"])
        if pd:
            for k in PERSONALITY:
                v = to_int(self.hp[k].get())
                if v is not None: p.w_u8(pd + 24 + PERSONALITY.index(k), max(1, min(127, v)))
        self.status.set(T("Salvo no jogo: %s") % h["name"]); self.select_human()

    BOARD_MODES = {"safe": 9500, "sack": 0}

    def apply_board_mode(self):
        """Botões rápidos: 'safe' = 9500 congelado; 'sack' = 0 congelado; 'default' = descongela e deixa o valor como está."""
        if not self.need() or not self.cur_human: self.h_mode.set("default"); return
        h = self.cur_human; m = h.get("details"); key = "human:%08X:board" % h["addr"]
        mode = self.h_mode.get()
        if mode == "default" or not m:
            with self.eng.freezer.lock: self.eng.freezer.items.pop(key, None)
            self.status.set(T("%s: confiança voltou ao padrão do jogo (sem congelar)") % h["name"])
            return
        v = self.BOARD_MODES[mode]
        self.eng.proc.write(m + 28, struct.pack("<H", v))
        self.eng.freeze_board(h, m, v)
        self.hv["board"].set(v)
        self.status.set(T("%s: diretoria = %d (congelada)") % (h["name"], v))

    def toggle_fans_freeze(self):
        """Caixa ao lado da confiança da torcida: congela no valor digitado / descongela (separado da demissão)."""
        if not self.need() or not self.cur_human: self.h_fz_fans.set(False); return
        h = self.cur_human; m = h.get("details"); key = "human:%08X:fans" % h["addr"]
        if not self.h_fz_fans.get() or not m:
            with self.eng.freezer.lock: self.eng.freezer.items.pop(key, None)
            self.status.set(T("%s: torcida descongelada") % h["name"]); return
        v = to_int(self.hv["fans"].get())
        if v is None: self.h_fz_fans.set(False); return
        v = max(0, min(10000, v))
        self.eng.proc.write(m + 52, struct.pack("<H", v))
        self.eng.freeze_board(h, m, v, "fans")
        self.status.set(T("%s: torcida = %d (congelada)") % (h["name"], v))

    # ------------------------------------------------------------ Favoritos (aba própria)
    def build_favs(self):
        f = self.tab_favs
        left = ttk.Frame(f); left.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.fv_label = ttk.Label(left, text=T('Favoritos'), font=("Segoe UI", 12, "bold")); self.fv_label.pack(anchor="w")
        self.fv_list = tk.Listbox(left, width=80, height=34, selectmode="extended", exportselection=False); self.fv_list.pack(fill="both", expand=True)
        self.fv_list.bind("<Double-Button-1>", self.open_fav)
        bar = ttk.Frame(f); bar.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Button(bar, text=T('Abrir na aba Jogadores'), command=self.open_fav).pack(fill="x", pady=2)
        ttk.Button(bar, text=T('Editar todos em massa →'), command=lambda: (self.set_target("fav"), self.goto_mass(self.tab_mass))).pack(fill="x", pady=2)
        ttk.Button(bar, text=T('Remover selecionados'), command=self.remove_fav_sel).pack(fill="x", pady=2)
        ttk.Button(bar, text=T('Limpar favoritos'), command=self.clear_favs).pack(fill="x", pady=2)
        ttk.Label(bar, text=T("Para adicionar: aba Jogadores,\nselecione e clique\n'★ Adicionar selecionados aos favoritos'.\n\nA lista fica salva em favoritos.json."),
                  foreground="#555", justify="left").pack(pady=10)

    def refresh_favs(self):
        if not self.eng:
            return
        self.fv_label.config(text=T('Favoritos (%d)') % len(self.eng.favorites))
        self.fv_list.delete(0, "end")
        for q in self.eng.favorites:
            c = self.eng.cache.get(q["addr"], {})
            self.fv_list.insert("end", T('%s  [%s]  %s anos  CA %s / PA %s  %s') % (
                q["name"], self.eng.club_of(q), c.get("age", "?"), c.get("ca", "?"), c.get("pa", "?"), c.get("nat", "")))

    def open_fav(self, _=None):
        sel = self.fv_list.curselection()
        if sel and self.eng:
            self.p_results = list(self.eng.favorites); self.show_player_results()
            self.cur_player = self.p_results[sel[0]]; self.load_player(); self.nb.select(self.tab_players)

    def remove_fav_sel(self):
        if not self.need(): return
        for i in sorted(self.fv_list.curselection(), reverse=True):
            del self.eng.favorites[i]
        self.eng.save_favs(); self.refresh_mass()

    def clear_favs(self):
        if not self.need(): return
        if self.eng.favorites and messagebox.askyesno(T('Favoritos'), T('Remover todos os %d favoritos?') % len(self.eng.favorites)):
            self.eng.favorites.clear(); self.eng.save_favs(); self.refresh_mass()

    # ------------------------------------------------------------ Favoritos / em massa
    def build_mass(self):
        f = self.tab_mass
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        self.m_label = ttk.Label(left, text=T('Favoritos'), font=("Segoe UI", 11, "bold")); self.m_label.pack(anchor="w")
        row = ttk.Frame(left); row.pack(fill="x")
        ttk.Button(row, text=T('Usar favoritos'), command=lambda: self.set_target("fav")).pack(side="left")
        ttk.Button(row, text=T('Remover selecionados dos favoritos'), command=self.remove_favs).pack(side="left", padx=4)
        self.m_list = tk.Listbox(left, width=58, height=32, selectmode="extended", exportselection=False); self.m_list.pack(fill="y", expand=True)
        self.m_list.bind("<Double-Button-1>", self.open_from_mass)
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T('Edição em massa — campos vazios não são alterados. Vale para TODOS da lista à esquerda.'),
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        st = ttk.LabelFrame(right, text=T('Estado')); st.pack(fill="x", pady=4)
        self.mv = {}
        for i, (k, lab) in enumerate([("cond", T('Condição (0-10000)')), ("morale", T('Moral (1-20)')), ("ca", "CA"), ("pa", "PA")]):
            ttk.Label(st, text=lab).grid(row=0, column=i * 2, sticky="e", padx=4, pady=2)
            self.mv[k] = tk.StringVar(); ttk.Entry(st, textvariable=self.mv[k], width=7).grid(row=0, column=i * 2 + 1)
        at = ttk.LabelFrame(right, text=T('Atributos')); at.pack(fill="x", pady=4)
        self.m_raw = tk.BooleanVar()
        ttk.Checkbutton(at, text=T('bruto (-128..127). Desmarcado: o número é o valor do jogo (1-20) e é convertido proporcionalmente\npara os atributos de escala fina; acima de 20 vira bruto automaticamente (127 = sobre-humano)'), variable=self.m_raw).grid(row=0, column=0, columnspan=3, sticky="w", padx=4)
        ttk.Label(at, text=T('Todos =')).grid(row=1, column=0, sticky="e", padx=4)
        self.m_all = tk.StringVar(); ttk.Entry(at, textvariable=self.m_all, width=6).grid(row=1, column=1, sticky="w")
        self.m_grp = {}
        for i, gname in enumerate(GROUPS, start=2):
            ttk.Label(at, text="%s =" % T(gname)).grid(row=i, column=0, sticky="e", padx=4)
            self.m_grp[gname] = tk.StringVar(); ttk.Entry(at, textvariable=self.m_grp[gname], width=6).grid(row=i, column=1, sticky="w")
        ttk.Button(right, text=T('💾  Salvar no jogo (todos da lista)'), command=self.mass_save).pack(anchor="w", pady=6)
        ac = ttk.LabelFrame(right, text=T('Ações e congelamentos (aplicam a todos da lista)')); ac.pack(fill="x", pady=4)
        ttk.Button(ac, text=T('Curar lesões'), command=lambda: self.mass_action("heal")).grid(row=0, column=0, padx=4, pady=3)
        ttk.Button(ac, text=T('Remover suspensões'), command=lambda: self.mass_action("unban")).grid(row=0, column=1, padx=4)
        ttk.Button(ac, text=T('Restaurar backups'), command=lambda: self.mass_action("restore")).grid(row=0, column=2, padx=4)
        self.mfz = {}
        for i, (k, lab) in enumerate([("cond", T('Congelar condição (no valor acima)')), ("morale", T('Congelar moral (no valor acima)')),
                                      ("attrs", T('Congelar atributos (como estão agora)')), ("heal", T('Manter curados')), ("unban", T('Manter sem suspensão'))]):
            ttk.Button(ac, text=T('Ligar: ') + lab, command=lambda k=k: self.mass_freeze(k, True)).grid(row=1 + i, column=0, columnspan=2, sticky="w", padx=4, pady=1)
            ttk.Button(ac, text=T('Desligar'), command=lambda k=k: self.mass_freeze(k, False)).grid(row=1 + i, column=2, padx=4)
        self.refresh_mass()

    def mass_players(self):
        kind, obj = self.mass_target
        if kind == "club" and obj:
            return sorted(self.eng.squads.get(obj["club"], []), key=lambda q: q["name"])
        return list(self.eng.favorites)

    def set_target(self, kind):
        self.mass_target = (kind, None); self.refresh_mass()

    def refresh_mass(self):
        if not self.eng:
            return
        self.refresh_favs()
        kind, obj = self.mass_target
        self.m_label.config(text=(T('Elenco: %s') % obj["name"]) if kind == "club" and obj else T('Favoritos (%d)') % len(self.eng.favorites))
        self.m_list.delete(0, "end")
        for q in self.mass_players():
            c = self.eng.cache.get(q["addr"], {})
            self.m_list.insert("end", "%s  [%s]  CA %s / PA %s" % (q["name"], self.eng.club_of(q), c.get("ca", "?"), c.get("pa", "?")))

    def remove_favs(self):
        if self.mass_target[0] != "fav":
            return
        pls = self.mass_players()
        for i in sorted(self.m_list.curselection(), reverse=True):
            self.eng.favorites.remove(pls[i])
        self.eng.save_favs(); self.refresh_mass()

    def open_from_mass(self, _=None):
        sel = self.m_list.curselection()
        if sel:
            self.p_results = self.mass_players(); self.show_player_results()
            self.cur_player = self.p_results[sel[0]]; self.load_player(); self.nb.select(self.tab_players)

    def mass_save(self):
        if not self.need(): return
        pls = self.mass_players()
        if not pls:
            return
        if not messagebox.askyesno(T('Confirmar'), T('Salvar no jogo para %d jogadores?') % len(pls)):
            return
        skills = {}
        for gname, keys in GROUPS.items():
            v = self.m_grp[gname].get().strip() or ("" if gname.startswith("Posições") else self.m_all.get().strip())
            for k in keys:
                skills[k] = v
        raw = self.m_raw.get()
        for pl in pls:
            self.apply_to(pl, self.mv["cond"].get(), self.mv["morale"].get(), self.mv["ca"].get(), self.mv["pa"].get(), skills, raw)
        self.status.set(T('Salvo no jogo em %d jogadores') % len(pls)); self.refresh_mass()

    def mass_action(self, what):
        if not self.need(): return
        pls = self.mass_players(); n = 0
        for pl in pls:
            if what == "heal": self.eng.game.heal(pl); n += 1
            elif what == "unban": self.eng.game.unban(pl, force=True); n += 1
            elif what == "restore": self.eng.game.restore(pl); n += 1
            elif what == "unretire":
                if self.eng.game.retiring(pl) or self.eng.game.retire_entries(pl): self.eng.game.cancel_retirement(pl); n += 1
        names = {"heal": T("Curar lesões"), "unban": T("Remover suspensões"), "restore": T("Restaurar backups"), "unretire": T("Cancelar aposentadoria (RET)")}
        self.status.set(T("%s: %d jogadores") % (names.get(what, what), n))

    def mass_freeze(self, what, on):
        if not self.need(): return
        pls = self.mass_players()
        val = to_int(self.mv["cond"].get()) if what == "cond" else to_int(self.mv["morale"].get()) if what == "morale" else None
        for pl in pls:
            self.eng.set_freeze(pl, what, on, val)
        self.status.set(T("Congelamento '%s' %s em %d jogadores") % (what, T('ligado') if on else T('desligado'), len(pls)))

    # ------------------------------------------------------------ Clubes em massa
    def add_cmass(self):
        if not self.need(): return
        n = 0
        for i in self.c_list.curselection():
            c = self.c_results[i]
            if c["club"] not in [x["club"] for x in self.cmass]:
                self.cmass.append(c); n += 1
        self.refresh_cmass(); self.status.set(T('%d clubes adicionados (%d na lista)') % (n, len(self.cmass)))
        self.goto_mass(self.tab_cmass)

    def build_cmass(self):
        f = self.tab_cmass
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T('Clubes na lista'), font=("Segoe UI", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(left); row.pack(fill="x")
        ttk.Button(row, text=T('Remover selecionados'), command=self.remove_cmass).pack(side="left")
        ttk.Button(row, text=T('Limpar lista'), command=lambda: (self.cmass.clear(), self.refresh_cmass())).pack(side="left", padx=4)
        self.cm_list = tk.Listbox(left, width=58, height=32, selectmode="extended", exportselection=False); self.cm_list.pack(fill="y", expand=True)
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T('Campos vazios NÃO são alterados. Vale para todos os clubes da lista.'), font=("Segoe UI", 10, "bold")).pack(anchor="w")
        box = ttk.LabelFrame(right, text=T('Clube')); box.pack(fill="x", pady=4)
        self.cmv = {}
        for i, (k, lab) in enumerate([("rep", T('Reputação (0-10000)')), ("status", T('Status (1 prof / 2 semi / 3 amador)')),
                                      ("training", T('Condições de treino (0-20)')), ("academy", T('Academia (0-20)')), ("youth", T('Camadas jovens (0-20)')),
                                      ("avg", T('Público médio')), ("min", T('Público mínimo')), ("max", T('Público máximo'))]):
            ttk.Label(box, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.cmv[k] = tk.StringVar(); ttk.Entry(box, textvariable=self.cmv[k], width=12).grid(row=i, column=1, sticky="w")
        fin = ttk.LabelFrame(right, text=T('Finanças (como o jogo mostra; só clubes jogáveis recebem orçamentos)')); fin.pack(fill="x", pady=4)
        for i, (k, lab) in enumerate([("balance", T('Saldo')), ("transfer", T('Orçamento de transferências')), ("remaining", T('Restante')), ("wage", T('Orçamento salarial / semana'))]):
            ttk.Label(fin, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.cmv[k] = tk.StringVar(); ttk.Entry(fin, textvariable=self.cmv[k], width=16).grid(row=i, column=1, sticky="w")
        self.cm_nolimit = tk.BooleanVar()
        ttk.Checkbutton(right, text=T('sem limites (reputação até 65535, campos 0-20 até 127) — experimental'), variable=self.cm_nolimit).pack(anchor="w")
        ttk.Button(right, text=T('💾  Salvar no jogo (todos os clubes da lista)'), command=self.save_cmass).pack(anchor="w", pady=6)
        r2 = ttk.Frame(right); r2.pack(anchor="w")
        ttk.Button(r2, text=T('❄ Escolher o que congelar (todos da lista)…'), command=lambda: self.pick_obj_freeze("club", self.cmass, self.cmv, self.cm_nolimit)).pack(side="left")
        ttk.Button(r2, text=T('Descongelar todos da lista'), command=lambda: self.mass_unfreeze_objs("club")).pack(side="left", padx=4)

    def refresh_cmass(self):
        self.cm_list.delete(0, "end")
        for c in self.cmass:
            v = self.eng.club_values(c) if self.eng else {}
            self.cm_list.insert("end", T("%s  rep %s  inst %s  saldo %s") % (c["name"], v.get("rep", "?"), v.get("training", "?"), v.get("balance", "?")))

    def remove_cmass(self):
        for i in sorted(self.cm_list.curselection(), reverse=True):
            del self.cmass[i]
        self.refresh_cmass()

    def save_cmass(self):
        if not self.need(): return
        if not self.cmass:
            return
        vals = {k: v.get() for k, v in self.cmv.items()}
        if not any(to_int(x) is not None for x in vals.values()):
            messagebox.showinfo(T('Em massa'), T('Preencha pelo menos um campo.')); return
        if not messagebox.askyesno(T('Confirmar'), T('Aplicar os campos preenchidos em %d clubes?') % len(self.cmass)):
            return
        for c in self.cmass:
            self.eng.apply_club(c, vals, nolimit=self.cm_nolimit.get())
        self.status.set(T('Salvo no jogo em %d clubes') % len(self.cmass)); self.refresh_cmass()
        if self.cur_club: self.load_club()

    # ------------------------------------------------------------ Países em massa
    def add_nmass(self):
        if not self.need(): return
        n = 0
        for i in self.n_list.curselection():
            x = self.n_results[i]
            if x["addr"] not in [y["addr"] for y in self.nmass]:
                self.nmass.append(x); n += 1
        self.refresh_nmass(); self.status.set(T('%d países adicionados (%d na lista)') % (n, len(self.nmass)))
        self.goto_mass(self.tab_nmass)

    def build_nmass(self):
        f = self.tab_nmass
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T('Países na lista'), font=("Segoe UI", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(left); row.pack(fill="x")
        ttk.Button(row, text=T('Remover selecionados'), command=self.remove_nmass).pack(side="left")
        ttk.Button(row, text=T('Limpar lista'), command=lambda: (self.nmass.clear(), self.refresh_nmass())).pack(side="left", padx=4)
        self.nm_list = tk.Listbox(left, width=44, height=32, selectmode="extended", exportselection=False); self.nm_list.pack(fill="y", expand=True)
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T('Campos vazios NÃO são alterados. Vale para todos os países da lista.'), font=("Segoe UI", 10, "bold")).pack(anchor="w")
        box = ttk.LabelFrame(right, text=T('País')); box.pack(fill="x", pady=4)
        self.nmv = {}
        for i, (k, lab) in enumerate([("rep", T('Reputação (0-10000)')), ("importance", T('Importância de jogo (0-20)')),
                                      ("dev", T('Desenvolvimento (1/2/3)')), ("economy", T('Fator econômico (0-20)')), ("league", T('Nível do campeonato (0-20)'))]):
            ttk.Label(box, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=2)
            self.nmv[k] = tk.StringVar(); ttk.Entry(box, textvariable=self.nmv[k], width=10).grid(row=i, column=1, sticky="w")
        self.nm_nolimit = tk.BooleanVar()
        ttk.Checkbutton(right, text=T('sem limites (reputação até 65535, campos 0-20 até 127) — experimental'), variable=self.nm_nolimit).pack(anchor="w")
        ttk.Button(right, text=T('💾  Salvar no jogo (todos os países da lista)'), command=self.save_nmass).pack(anchor="w", pady=6)
        r2 = ttk.Frame(right); r2.pack(anchor="w")
        ttk.Button(r2, text=T('❄ Escolher o que congelar (todos da lista)…'), command=lambda: self.pick_obj_freeze("nation", self.nmass, self.nmv, self.nm_nolimit)).pack(side="left")
        ttk.Button(r2, text=T('Descongelar todos da lista'), command=lambda: self.mass_unfreeze_objs("nation")).pack(side="left", padx=4)

    def refresh_nmass(self):
        self.nm_list.delete(0, "end")
        for x in self.nmass:
            v = self.eng.nation_values(x["addr"]) if self.eng else {}
            self.nm_list.insert("end", T("%s  rep %s  imp %s  dev %s  eco %s  liga %s") % (x["name"], v.get("rep", "?"), v.get("importance", "?"), v.get("dev", "?"), v.get("economy", "?"), v.get("league", "?")))

    def remove_nmass(self):
        for i in sorted(self.nm_list.curselection(), reverse=True):
            del self.nmass[i]
        self.refresh_nmass()

    def save_nmass(self):
        if not self.need(): return
        vals = {k: v.get() for k, v in self.nmv.items()}
        if not self.nmass or not any(to_int(x) is not None for x in vals.values()):
            messagebox.showinfo(T('Em massa'), T('Preencha pelo menos um campo.')); return
        if not messagebox.askyesno(T('Confirmar'), T('Aplicar os campos preenchidos em %d países?') % len(self.nmass)):
            return
        for x in self.nmass:
            self.eng.apply_nation(x["addr"], vals, nolimit=self.nm_nolimit.get())
        self.status.set(T('Salvo em %d países') % len(self.nmass)); self.refresh_nmass()

    # ------------------------------------------------------------ Competições
    def build_comps(self):
        f = self.tab_comps
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        flt = ttk.LabelFrame(left, text=T('Busca e filtro')); flt.pack(fill="x")
        ttk.Label(flt, text=T('Nome')).grid(row=0, column=0, sticky="e", padx=3)
        self.k_search = ttk.Entry(flt, width=24); self.k_search.grid(row=0, column=1, columnspan=2, sticky="w")
        self.k_search.bind("<Return>", lambda e: self.search_comps())
        ttk.Label(flt, text=T('País')).grid(row=1, column=0, sticky="e", padx=3)
        self.k_nation = ttk.Entry(flt, width=24); self.k_nation.grid(row=1, column=1, columnspan=2, sticky="w")
        self.k_nation.bind("<Return>", lambda e: self.search_comps())
        self.kf = {"rep": (tk.StringVar(), tk.StringVar())}
        self.crit_row(flt, 2, T('Reputação'), self.kf["rep"][0], self.kf["rep"][1])
        ttk.Label(flt, text=T('Tipo')).grid(row=3, column=0, sticky="e", padx=3)
        self.k_kind = tk.StringVar(value=T("Todos"))
        ttk.Combobox(flt, textvariable=self.k_kind, values=[T(lab) for _, lab in Engine.COMP_KINDS], width=22, state="readonly").grid(row=3, column=1, columnspan=2, sticky="w")
        ttk.Label(flt, text=T('Nível (ligas)')).grid(row=4, column=0, sticky="e", padx=3)
        self.k_level = tk.StringVar(value=T("Todos"))
        ttk.Combobox(flt, textvariable=self.k_level, values=[T("Todos"), "1", "2", "3", "4", "5+"], width=6, state="readonly").grid(row=4, column=1, sticky="w")
        ttk.Button(flt, text=T('Buscar / filtrar'), command=self.search_comps).grid(row=5, column=0, columnspan=3, pady=4)
        self.k_list = tk.Listbox(left, width=60, height=30, selectmode="extended", exportselection=False); self.k_list.pack(fill="y", expand=True)
        self.k_list.bind("<<ListboxSelect>>", self.select_comp)
        self.k_results = []
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.k_title = ttk.Label(right, text=T('Selecione uma competição'), font=("Segoe UI", 12, "bold")); self.k_title.pack(anchor="w")
        box = ttk.LabelFrame(right, text=T('Campos')); box.pack(fill="x", pady=4)
        ttk.Label(box, text=T('Reputação (0-20)')).grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.kv = {"rep": tk.StringVar()}
        ttk.Entry(box, textvariable=self.kv["rep"], width=10).grid(row=0, column=1, sticky="w")
        self.k_nolimit = tk.BooleanVar()
        ttk.Checkbutton(right, text=T('sem limites (até 127) — experimental'), variable=self.k_nolimit).pack(anchor="w")
        bar = ttk.Frame(right); bar.pack(fill="x", pady=4)
        ttk.Button(bar, text=T('💾  Salvar no jogo (esta competição)'), command=self.save_comp).pack(side="left", padx=4)
        ttk.Button(bar, text=T('❄ Escolher o que congelar…'), command=lambda: self.pick_obj_freeze("comp", [self.cur_comp] if self.cur_comp else [], self.kv, self.k_nolimit)).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Descongelar'), command=lambda: self.cur_comp and (self.eng.unfreeze_prefix("comp:%08X:" % self.cur_comp["addr"]), self.status.set(T('Descongelado')))).pack(side="left", padx=4)
        ttk.Button(bar, text=T('➕ Adicionar selecionados à lista em massa'), command=self.add_kmass).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Descartar'), command=self.select_comp).pack(side="left", padx=4)
        ttk.Label(right, text=T('Reputação = COMP+96. Confira com o editor oficial (Série A 15 / Copa do Brasil 14 no seu save).'), foreground="#555").pack(anchor="w", pady=6)

    def search_comps(self):
        if not self.need(): return
        kind = next((k for k, lab in Engine.COMP_KINDS if T(lab) == self.k_kind.get()), "")
        level = "" if self.k_level.get() == T("Todos") else self.k_level.get()
        self.k_results = self.eng.filter_comps(self.k_search.get(), self.k_nation.get(), {k: self.crit(v[0], v[1]) for k, v in self.kf.items()}, kind, level)
        self.k_results.sort(key=lambda c: (-c["rep"], c["name"]))
        self.k_list.delete(0, "end")
        kinds = dict(Engine.COMP_KINDS)
        for c in self.k_results:
            tag = T(kinds.get(c.get("kind"), "")) + (" %d" % c["level"] if c.get("level") else "")
            self.k_list.insert("end", "%s  [%s]  rep %d  — %s" % (c["name"], c["nation"] or "?", c["rep"], tag))
        self.status.set(T('%d competições') % len(self.k_results))

    def select_comp(self, _=None):
        sel = self.k_list.curselection()
        if sel:
            self.cur_comp = self.k_results[sel[0]]
        c = self.cur_comp
        if not c:
            return
        self.k_title.config(text="%s (%s)" % (c["name"], c["nation"] or "?"))
        for k, v in self.eng.comp_values(c["addr"]).items():
            self.kv[k].set(v)

    def save_comp(self):
        if not self.need(): return
        c = self.cur_comp
        if c:
            self.eng.apply_comp(c["addr"], {k: v.get() for k, v in self.kv.items()}, nolimit=self.k_nolimit.get())
            self.status.set(T('Salvo no jogo: %s') % c["name"]); self.select_comp()

    def add_kmass(self):
        if not self.need(): return
        n = 0
        for i in self.k_list.curselection():
            x = self.k_results[i]
            if x["addr"] not in [y["addr"] for y in self.kmass]:
                self.kmass.append(x); n += 1
        self.refresh_kmass(); self.status.set(T('%d competições adicionadas (%d na lista)') % (n, len(self.kmass)))
        self.goto_mass(self.tab_kmass)

    def build_kmass(self):
        f = self.tab_kmass
        left = ttk.Frame(f); left.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Label(left, text=T('Competições na lista'), font=("Segoe UI", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(left); row.pack(fill="x")
        ttk.Button(row, text=T('Remover selecionados'), command=self.remove_kmass).pack(side="left")
        ttk.Button(row, text=T('Limpar lista'), command=lambda: (self.kmass.clear(), self.refresh_kmass())).pack(side="left", padx=4)
        self.km_list = tk.Listbox(left, width=60, height=32, selectmode="extended", exportselection=False); self.km_list.pack(fill="y", expand=True)
        right = ttk.Frame(f); right.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ttk.Label(right, text=T('Campos vazios NÃO são alterados. Vale para todas as competições da lista.'), font=("Segoe UI", 10, "bold")).pack(anchor="w")
        box = ttk.LabelFrame(right, text=T('Competição')); box.pack(fill="x", pady=4)
        ttk.Label(box, text=T('Reputação (0-20)')).grid(row=0, column=0, sticky="e", padx=4, pady=2)
        self.kmv = {"rep": tk.StringVar()}
        ttk.Entry(box, textvariable=self.kmv["rep"], width=10).grid(row=0, column=1, sticky="w")
        self.km_nolimit = tk.BooleanVar()
        ttk.Checkbutton(right, text=T('sem limites (reputação até 65535, campos 0-20 até 127) — experimental'), variable=self.km_nolimit).pack(anchor="w")
        ttk.Button(right, text=T('💾  Salvar no jogo (todas as competições da lista)'), command=self.save_kmass).pack(anchor="w", pady=6)
        r2 = ttk.Frame(right); r2.pack(anchor="w")
        ttk.Button(r2, text=T('❄ Escolher o que congelar (todas da lista)…'), command=lambda: self.pick_obj_freeze("comp", self.kmass, self.kmv, self.km_nolimit)).pack(side="left")
        ttk.Button(r2, text=T('Descongelar todas da lista'), command=lambda: self.mass_unfreeze_objs("comp")).pack(side="left", padx=4)

    def refresh_kmass(self):
        self.km_list.delete(0, "end")
        for x in self.kmass:
            v = self.eng.comp_values(x["addr"]) if self.eng else {}
            self.km_list.insert("end", "%s  [%s]  rep %s" % (x["name"], x.get("nation") or "?", v.get("rep", "?")))

    def remove_kmass(self):
        for i in sorted(self.km_list.curselection(), reverse=True):
            del self.kmass[i]
        self.refresh_kmass()

    def save_kmass(self):
        if not self.need(): return
        vals = {k: v.get() for k, v in self.kmv.items()}
        if not self.kmass or not any(to_int(x) is not None for x in vals.values()):
            messagebox.showinfo(T('Em massa'), T('Preencha pelo menos um campo.')); return
        if not messagebox.askyesno(T('Confirmar'), T('Aplicar os campos preenchidos em %d competições?') % len(self.kmass)):
            return
        for x in self.kmass:
            self.eng.apply_comp(x["addr"], vals, nolimit=self.km_nolimit.get())
        self.status.set(T('Salvo em %d competições') % len(self.kmass)); self.refresh_kmass()

    # ------------------------------------------------------------ Congelar clubes/países/competições
    def freeze_club_btn(self):
        if not self.need() or not self.cur_club: return
        n = self.eng.freeze_club(self.cur_club, {k: self.cv[k].get() for k in self.cv}, nolimit=self.c_nolimit.get())
        self.status.set(T('%d campos congelados em %s') % (n, self.cur_club["name"]) if n else T('Preencha os campos que quer congelar'))

    def freeze_nation_btn(self):
        if not self.need() or not self.cur_nation: return
        n = self.eng.freeze_nation(self.cur_nation["addr"], self.cur_nation["name"], {k: v.get() for k, v in self.nv.items()}, nolimit=self.n_nolimit.get())
        self.status.set(T('%d campos congelados em %s') % (n, self.cur_nation["name"]) if n else T('Preencha os campos que quer congelar'))

    def freeze_comp_btn(self):
        if not self.need() or not self.cur_comp: return
        n = self.eng.freeze_comp(self.cur_comp, {k: v.get() for k, v in self.kv.items()}, nolimit=self.k_nolimit.get())
        self.status.set(T('Reputação congelada: %s') % self.cur_comp["name"] if n else T('Preencha a reputação'))

    def pick_obj_freeze(self, kind, objs, entries, nolimit_var):
        """Janela para escolher campo a campo o que congelar (nos valores digitados) em clubes/países/competições."""
        if not self.need(): return
        if not objs:
            messagebox.showinfo(T('Congelar'), T('Selecione (ou adicione à lista) primeiro.')); return
        specs = {"club": [(k, v[3]) for k, v in self.eng.CLUB_SPECS.items()], "nation": [(k, v[2]) for k, v in self.eng.NATION_SPECS.items()],
                 "comp": [("rep", T('Reputação'))]}[kind]
        title = objs[0]["name"] if len(objs) == 1 else T("%d itens da lista") % len(objs)
        win = tk.Toplevel(self); win.title(T('Congelar — %s') % title); win.transient(self)
        ttk.Label(win, text=T('Marque os campos a congelar. Cada um é congelado NO VALOR que está no campo da aba (preencha antes).\nCampo marcado sem valor digitado é ignorado. Desmarcar = descongelar.'), justify="left").pack(anchor="w", padx=8, pady=6)
        box = ttk.Frame(win); box.pack(padx=8)
        vars_ = {}
        for i, (k, lab) in enumerate(specs):
            frozen = all(self.eng.is_frozen_field(kind, o, k) for o in objs)
            vars_[k] = tk.BooleanVar(value=frozen)
            val = entries[k].get().strip() if k in entries else ""
            ttk.Checkbutton(box, text=T("%s   (valor: %s)") % (lab, val or "—"), variable=vars_[k]).grid(row=i % 8, column=i // 8, sticky="w", padx=6, pady=1)
        def apply():
            n = 0
            for k, var in vars_.items():
                for o in objs:
                    if var.get():
                        if to_int(entries[k].get()) is not None:
                            n += self.eng.freeze_field(kind, o, k, entries[k].get(), nolimit_var.get())
                    elif self.eng.is_frozen_field(kind, o, k):
                        self.eng.unfreeze_prefix(self.eng.obj_key(kind, o) + k)
            self.status.set(T('%d congelamentos ativos criados/atualizados') % n); win.destroy()
        bar = ttk.Frame(win); bar.pack(pady=8)
        ttk.Button(bar, text=T('✔ Aplicar'), command=apply).pack(side="left", padx=4)
        ttk.Button(bar, text=T('Cancelar'), command=win.destroy).pack(side="left", padx=4)

    def mass_freeze_objs(self, kind):
        if not self.need(): return
        n = 0
        if kind == "club":
            vals = {k: v.get() for k, v in self.cmv.items()}
            for c in self.cmass: n += self.eng.freeze_club(c, vals, nolimit=self.cm_nolimit.get())
        elif kind == "nation":
            vals = {k: v.get() for k, v in self.nmv.items()}
            for x in self.nmass: n += self.eng.freeze_nation(x["addr"], x["name"], vals, nolimit=self.nm_nolimit.get())
        else:
            vals = {k: v.get() for k, v in self.kmv.items()}
            for c in self.kmass: n += self.eng.freeze_comp(c, vals, nolimit=self.km_nolimit.get())
        self.status.set(T("%d congelamentos criados") % n if n else T('Preencha os campos que quer congelar'))

    def mass_unfreeze_objs(self, kind):
        if not self.need(): return
        lst = {"club": [("club:%08X:" % c["club"]) for c in self.cmass], "nation": [("nation:%08X:" % x["addr"]) for x in self.nmass],
               "comp": [("comp:%08X:" % c["addr"]) for c in self.kmass]}[kind]
        for p in lst: self.eng.unfreeze_prefix(p)
        self.status.set(T('Descongelados %d') % len(lst))

    # ------------------------------------------------------------ Congelados
    FROZEN_CATS = ["Jogadores", "Clubes", "Países", "Competições", "Staff", "Treinadores"]

    # ------------------------------------------------------------ Aposentadorias (RET)
    RET_COLS = [("name", "Nome", 260), ("club", "Clube", 200), ("age", "Idade", 60), ("nat", "Nacionalidade", 140), ("ret", "RET", 50), ("date", "Data", 110)]

    def build_ret(self):
        f = self.tab_ret
        top = ttk.Frame(f); top.pack(fill="x", padx=6, pady=6)
        ttk.Button(top, text=T('🔍 Procurar jogadores com RET'), command=self.search_ret).pack(side="left", padx=(0, 16))
        ttk.Label(top, text=T('Clube')).pack(side="left", padx=(0, 3))
        self.r_club = tk.StringVar(); e = ttk.Entry(top, textvariable=self.r_club, width=18); e.pack(side="left"); e.bind("<Return>", lambda ev: self.search_ret())
        ttk.Label(top, text=T('Idade')).pack(side="left", padx=(16, 3))
        self.r_age_op, self.r_age = tk.StringVar(), tk.StringVar()
        ttk.Combobox(top, textvariable=self.r_age_op, values=list(OPS.keys()), width=3, state="readonly").pack(side="left")
        ttk.Entry(top, textvariable=self.r_age, width=5).pack(side="left", padx=2)
        self.r_only_future = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text=T('só aposentadorias futuras (esconde as já passadas)'), variable=self.r_only_future).pack(side="left", padx=16)
        self.r_info = ttk.Label(top, text=""); self.r_info.pack(side="left", padx=12)
        ttk.Label(f, text=T("Lista dos jogadores que anunciaram aposentadoria (RET) ou que estão nas listas internas de aposentadoria do jogo. Cancelar = tira da lista do jogo e apaga o RET. Marcar aposentadoria não é possível (corrompe o save). Clique no título da coluna para ordenar."), foreground="#555", wraplength=1100, justify="left").pack(anchor="w", padx=6)
        box = ttk.Frame(f); box.pack(fill="both", expand=True, padx=6, pady=6)
        self.r_tree = ttk.Treeview(box, columns=[c for c, _, _ in self.RET_COLS], show="headings", selectmode="extended", height=26)
        for c, lab, w in self.RET_COLS:
            self.r_tree.heading(c, text=T(lab), command=lambda c=c: self.sort_ret(c))
            self.r_tree.column(c, width=w, anchor="center" if c in ("age", "ret") else "w")
        sb = ttk.Scrollbar(box, orient="vertical", command=self.r_tree.yview); self.r_tree.configure(yscrollcommand=sb.set)
        self.r_tree.pack(side="left", fill="both", expand=True); sb.pack(side="left", fill="y")
        self.r_tree.bind("<Double-1>", lambda e: self.open_ret_player())
        self.r_results = []; self.r_sort = ("club", False)
        bar = ttk.Frame(f); bar.pack(fill="x", padx=6, pady=(0, 8))
        ttk.Button(bar, text=T('✖ Cancelar aposentadoria dos selecionados'), command=lambda: self.cancel_ret(False)).pack(side="left")
        ttk.Button(bar, text=T('✖ Cancelar aposentadoria de TODOS da lista'), command=lambda: self.cancel_ret(True)).pack(side="left", padx=8)
        ttk.Button(bar, text=T('Abrir na aba Jogadores'), command=self.open_ret_player).pack(side="left", padx=8)

    def search_ret(self):
        if not self.need(): return
        g = self.eng.game
        self.status.set(T('Procurando jogadores com RET...')); self.update_idletasks()
        cl = strip_accents(self.r_club.get()).lower().strip()
        op, val = self.crit(self.r_age_op, self.r_age)
        by_idx, by_addr, flagged = {}, {}, []
        for q in self.eng.players:
            b = self.eng.proc.read(q["addr"] + g.RETIRE_FLAG_OFF, 1)
            if len(b) != 1: continue
            by_idx[self.eng.proc.u32(q["addr"] + g.PERSON_INDEX_OFF)] = q; by_addr[q["addr"]] = q
            if b[0] & g.RETIRE_FLAG_BIT: flagged.append(q)
        dates = {}
        for off, ioff, data, n, cap, items in g.retire_lists():
            for it in items:
                if not it: continue
                q = by_idx.get(self.eng.proc.u32(it + ioff))
                if q is not None:
                    dates.setdefault(q["addr"], fm_date(self.eng.proc.u32(it + (0x14 if ioff == 0 else 12))))
        found = {q["addr"]: q for q in flagged}
        today = self.eng.game_date
        for a, d in dates.items():
            if a not in by_addr: continue
            if self.r_only_future.get():
                try:
                    if datetime.datetime.strptime(d, "%d/%m/%Y").date() < today: continue
                except Exception: continue
            found.setdefault(a, by_addr[a])
        rows = []
        for q in found.values():
            c = self.eng.cache.get(q["addr"], {})
            club = self.eng.club_of(q) or "-"
            if cl and cl not in strip_accents(club).lower(): continue
            age = c.get("age")
            if op and val is not None and (age is None or not OPS[op](age, val)): continue
            rows.append(dict(q=q, name=q["name"], club=club, age=age if age is not None else "?", nat=c.get("nat", ""), ret=T("sim") if q in flagged else T("não"), date=dates.get(q["addr"], T("(sem data)"))))
        self.r_results = rows
        self.fill_ret()
        self.r_info.config(text=T('%d jogadores') % len(rows)); self.status.set(T('%d jogadores com RET') % len(rows))

    def fill_ret(self):
        col, rev = self.r_sort
        def key(r):
            v = r[col]
            if col == "age": return (isinstance(v, str), v if isinstance(v, int) else 0)
            if col == "date":
                try: return (0, datetime.datetime.strptime(v, "%d/%m/%Y"))
                except Exception: return (1, datetime.datetime.max)
            return (0, strip_accents(str(v)).lower())
        self.r_results.sort(key=key, reverse=rev)
        self.r_tree.delete(*self.r_tree.get_children())
        for i, r in enumerate(self.r_results):
            self.r_tree.insert("", "end", iid=str(i), values=(r["name"], r["club"], r["age"], r["nat"], r["ret"], r["date"]))
        for c, lab, w in self.RET_COLS:
            self.r_tree.heading(c, text=T(lab) + (" ▼" if (c == col and rev) else " ▲" if c == col else ""))

    def sort_ret(self, col):
        cur, rev = self.r_sort
        self.r_sort = (col, not rev if col == cur else False)
        self.fill_ret()

    def ret_selected(self):
        return [self.r_results[int(i)]["q"] for i in self.r_tree.selection()]

    def cancel_ret(self, everyone):
        if not self.need() or not self.r_results: return
        pls = [r["q"] for r in self.r_results] if everyone else self.ret_selected()
        if not pls:
            messagebox.showinfo(T('Aposentadorias'), T('Selecione um ou mais jogadores na lista (Ctrl/Shift + clique).')); return
        if not messagebox.askyesno(T('Confirmar'), T('Cancelar a aposentadoria de %d jogadores? (Salve o save antes.)') % len(pls)): return
        n = 0
        for q in pls: n += self.eng.game.cancel_retirement(q)
        self.status.set(T('Aposentadoria cancelada em %d jogadores (%d registros removidos)') % (len(pls), n))
        self.search_ret()

    def open_ret_player(self):
        sel = self.ret_selected()
        if not sel: return
        q = sel[0]
        self.p_results = [q]; self.show_player_results(); self.p_list.selection_set(0); self.cur_player = q; self.load_player(); self.nb.select(self.tab_players)

    def build_frozen(self):
        f = self.tab_frozen
        top = ttk.Frame(f); top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text=T("Procurar")).pack(side="left")
        self.f_search = tk.StringVar(); e = ttk.Entry(top, textvariable=self.f_search, width=28); e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.search_frozen()); e.bind("<KeyRelease>", lambda ev: self.search_frozen())
        ttk.Button(top, text=T("Limpar"), command=lambda: (self.f_search.set(""), self.search_frozen())).pack(side="left")
        self.f_found = ttk.Label(top, text="", foreground="#1a5fb4"); self.f_found.pack(side="left", padx=12)
        ttk.Button(top, text=T('Descongelar todos'), command=self.unfreeze_all).pack(side="right", padx=4)
        ttk.Button(top, text=T('Descongelar selecionados'), command=self.unfreeze_sel).pack(side="right", padx=4)
        ttk.Label(f, text=T("Escolha a categoria, depois o jogador/clube na lista da esquerda; os congelamentos dele aparecem à direita. Os congelamentos são salvos e podem ser reaplicados na próxima vez."), foreground="#555", wraplength=1100, justify="left").pack(anchor="w", padx=6)
        self.nb_frozen = ttk.Notebook(f); self.nb_frozen.pack(fill="both", expand=True, padx=6, pady=6)
        self.f_tabs = {}
        for cat in self.FROZEN_CATS:
            tab = ttk.Frame(self.nb_frozen); self.nb_frozen.add(tab, text=T(cat))
            left = ttk.Frame(tab); left.pack(side="left", fill="y", padx=4, pady=4)
            ttk.Label(left, text=T("Quem")).pack(anchor="w")
            lb = tk.Listbox(left, width=40, height=26, exportselection=False); lb.pack(fill="y", expand=True)
            right = ttk.Frame(tab); right.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            ttk.Label(right, text=T("Congelamentos (selecione para descongelar)")).pack(anchor="w")
            items = tk.Listbox(right, width=80, height=26, selectmode="extended", exportselection=False); items.pack(fill="both", expand=True)
            t = dict(tab=tab, ents=lb, items=items, names=[], keys=[], groups={})
            lb.bind("<<ListboxSelect>>", lambda ev, t=t: self.show_frozen_entity(t))
            self.f_tabs[cat] = t
        self.f_keys_raw = []

    @staticmethod
    def frozen_entity(label):
        name = label.split(" — ")[0].strip()
        for pre in ("Clube ", "País ", "Competição ", "Club ", "Nation ", "Competition "):
            if name.startswith(pre):
                name = name[len(pre):]
        return name

    def show_frozen_entity(self, t):
        sel = t["ents"].curselection()
        t["items"].delete(0, "end"); t["keys"] = []
        if not sel:
            return
        name = t["names"][sel[0]]
        q = strip_accents(self.f_search.get()).lower().strip()
        for k, label in t["groups"].get(name, []):
            if q and q not in strip_accents(label).lower():
                continue
            t["items"].insert("end", label); t["keys"].append(k)

    def search_frozen(self):
        q = strip_accents(self.f_search.get()).lower().strip()
        found = []; first = None
        for cat in self.FROZEN_CATS:
            t = self.f_tabs[cat]
            cur = t["names"][t["ents"].curselection()[0]] if t["ents"].curselection() else None
            t["ents"].delete(0, "end"); t["names"] = []
            n = 0
            for name, lst in sorted(t["groups"].items(), key=lambda kv: strip_accents(kv[0]).lower()):
                hits = [x for x in lst if not q or q in strip_accents(x[1]).lower()]
                if not hits:
                    continue
                t["ents"].insert("end", "%s (%d)" % (name, len(hits))); t["names"].append(name); n += len(hits)
            if n and q:
                found.append("%s (%d)" % (T(cat), n)); first = first or cat
            if t["names"]:
                idx = t["names"].index(cur) if cur in t["names"] else 0
                t["ents"].selection_clear(0, "end"); t["ents"].selection_set(idx); t["ents"].see(idx)
            self.show_frozen_entity(t)
        if q:
            self.f_found.config(text=(T("Encontrado em: ") + ", ".join(found)) if found else T("Nada encontrado"))
            if first: self.nb_frozen.select(self.f_tabs[first]["tab"])
        else:
            self.f_found.config(text="")

    def save_freezes(self):
        if not self.eng:
            return
        try:
            json.dump(self.eng.freeze_export(), open(FREEZE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass

    def restore_freezes(self):
        try:
            entries = json.load(open(FREEZE_FILE, encoding="utf-8"))
        except Exception:
            return
        if not entries:
            return
        if not messagebox.askyesno(T("Congelados"), T("Há %d congelamentos salvos da última vez. Reaplicar agora?") % len(entries)):
            return
        self.status.set(T("Reaplicando congelamentos...")); self.update_idletasks()
        ok, miss = self.eng.freeze_restore(entries)
        msg = T("%d congelamentos reaplicados") % ok
        if miss:
            msg += T(" — não encontrados: ") + ", ".join(miss[:8])
        self.status.set(msg)

    @staticmethod
    def source_hash():
        """SHA-256 dos arquivos do programa: quem baixar pode comparar com o hash publicado pelo autor."""
        import hashlib
        h = hashlib.sha256(); here = os.path.dirname(os.path.abspath(__file__))
        for fn in ("gui.py", "mcfm.py", "lang.py", "vtables.json", "export_classes.json"):
            try: h.update(open(os.path.join(here, fn), "rb").read())
            except Exception: pass
        return h.hexdigest()

    def show_about(self):
        hx = self.source_hash()
        win = tk.Toplevel(self); win.title("MCFM05 Reborn"); win.transient(self)
        ttk.Label(win, text="MCFM05 Reborn %s — %s" % (VERSION, BUILD), font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        ttk.Label(win, text=T("Criado por %s. Versão original publicada pelo autor; qualquer outra cópia modificada não é a oficial.") % AUTHOR, wraplength=560, justify="left").pack(anchor="w", padx=10)
        ttk.Label(win, text=T("Impressão digital (SHA-256) dos arquivos desta cópia — compare com a publicada pelo autor:"), wraplength=560, justify="left").pack(anchor="w", padx=10, pady=(8, 2))
        e = ttk.Entry(win, width=70); e.insert(0, hx); e.config(state="readonly"); e.pack(padx=10)
        ttk.Button(win, text=T("Copiar"), command=lambda: (self.clipboard_clear(), self.clipboard_append(hx))).pack(pady=8)

    def tick_date(self):
        if self.eng:
            try:
                self.sync_date()
            except Exception:
                pass   # o jogo pode estar reorganizando a memória (virada de temporada); tenta de novo em 5 s
        self.after(5000, self.tick_date)

    FROZEN_GROUPS = [("club:", "Clubes"), ("nation:", "Países"), ("comp:", "Competições"), ("staff:", "Staff"), ("human:", "Treinadores")]

    def refresh_frozen(self):
        items = self.eng.freeze_list() if self.eng else []
        keys = [k for k, _ in items]
        if keys != self.f_keys_raw:
            self.f_keys_raw = keys
            self.save_freezes()
            for t in self.f_tabs.values(): t["groups"] = {}
            for k, label in items:
                cat = next((n for p, n in self.FROZEN_GROUPS if k.startswith(p)), "Jogadores")
                self.f_tabs[cat]["groups"].setdefault(self.frozen_entity(label), []).append((k, label))
            for cat in self.FROZEN_CATS:
                n = sum(len(v) for v in self.f_tabs[cat]["groups"].values())
                self.nb_frozen.tab(self.f_tabs[cat]["tab"], text="%s (%d)" % (T(cat), n) if n else T(cat))
            self.search_frozen()
        self.after(1500, self.refresh_frozen)

    def unfreeze_sel(self):
        if not self.need(): return
        cur = self.nb_frozen.select()
        t = next((t for t in self.f_tabs.values() if str(t["tab"]) == cur), None)
        if not t: return
        with self.eng.freezer.lock:
            for i in t["items"].curselection():
                self.eng.freezer.items.pop(t["keys"][i], None)
        if self.cur_player: self.load_player()

    def unfreeze_all(self):
        if not self.need(): return
        with self.eng.freezer.lock:
            self.eng.freezer.items.clear()
        if self.cur_player: self.load_player()


def main():
    try:
        App().mainloop()
    except Exception:
        # sem console (pythonw) um erro sumiria: grava em erro.log e avisa
        import traceback
        log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "erro.log")
        with open(log, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
        try:
            messagebox.showerror("MCFM05 Reborn", T('Erro inesperado. Detalhes em erro.log:\n\n') + traceback.format_exc()[-800:])
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
