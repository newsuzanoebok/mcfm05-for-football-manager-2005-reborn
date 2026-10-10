#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCFM05 Reborn - protótipo (Windows, Python 3.8+, sem dependências)

Reimplementa o scanner do MCFM05 original (MindCompression FM 2005 Memory Editor)
a partir dos offsets e assinaturas extraídos do mcfm.exe, e adiciona:
  - condição 100% em um jogador ou no elenco inteiro
  - congelar condição / atributos (thread que reescreve a cada 200 ms)
  - dump e diff da struct do jogador (para mapear lesão, suspensão, moral)

Uso: abra o FM2005, carregue o save, e rode:   python mcfm.py
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import struct
import sys
import time
import threading
import unicodedata


def T(s):
    """Tradução das mensagens que vão para a interface; o gui.py troca esta função pela do lang.py."""
    return s

# ----------------------------------------------------------------------------
# Constantes extraídas do mcfm.exe
# ----------------------------------------------------------------------------

PROCESS_NAME = "fm2005"
IMAGE_BASE = 0x400000
VERSION_DWORD_OFFSET = 0xF4  # mcfm lê int32 em base+0xF4 para detectar a versão

VERSIONS = {
    782425187:  ("5.0.0 Demo (Strawberry)", 0),
    788935750:  ("5.0.0 Retail", 2),
    1192244486: ("5.0.2 Retail", 4),
}

# Assinaturas: 6 grupos de (vtable0, vtable1), um por tipo de objeto.
# Ordem dos grupos: city, player, playercoach, coach, team, country
SIG_ORDER = ["city", "player", "playercoach", "coach", "team", "country"]
SIGNATURES = {
    0: bytes.fromhex("9c33c5008833c500946de400dc6fe4004c72e500a074e5004ce8e4008ce9e400b40ae400a40ae400fc20e400e820e400"),
    2: bytes.fromhex("5cb5ca004cb5ca00c451e5000c54e500243ce600783ee6006c1ae600941be6000c3ce500fc3be500a457e5009057e500"),
    4: bytes.fromhex("b492c800a092c8008cdbe900d4dde9002ce0ea0080e2ea000c56ea005057ea005479e9004479e900948fe900808fe900"),
    # variante alternativa da 5.0.2 (mcfm tenta esta se a primeira não achar jogadores)
    "4b": bytes.fromhex("b492c800a092c80094dbe900dcdde90024e0ea0078e2ea001456ea005457ea005c79e9004c79e9009c8fe900888fe900"),
}

PLAYER = dict(
    PersonDataPtr=360,         # ptr -> PERSON_DATA (32 bytes): +24..+31 = 8 traços de personalidade (1..20)
    Morale=40,                 # u16, 1..20 (confirmado: 20 = Excelente)
    StatusPtr=44,              # ptr -> objeto de status: +8 dados/+12 contagem = lesões (PLAYER_INJURY*),
                               #                          +20 dados/+24 contagem = suspensões (PLAYER_BAN*)
    Condition=8,               # int16, 0..10000
    CurrentAbility=20,         # int16
    PotentialAbility=22,       # int16
    SkillsPtr=152,             # +4 na versão 5.0.2 (CalculatedOffsets.Calculate)
    FirstName=228, LastName=232, Nickname=236,  # ptr triplo -> UTF-16
    DateOfBirth=244,           # FmDate
    CityOfBirth=248, Nationality=256,
    IntCaps=264, U21Caps=265, IntGoals=266, U21Goals=267,
    Id=204,
    ContractPtr=312,
)
PLAYER_STRUCT_SIZE = 412  # confirmado: em +412 começa o próximo jogador
# Jogador-treinador (ACTUAL_PLAYER_AND_NON_PLAYER, vtable 00E63C24, 476 bytes): mesma struct, mas a parte PERSON
# (nomes, nascimento, nacionalidade, time, contratos, personalidade, relações) fica 64 bytes adiante (+188 -> +252).
APANP_VT, APANP_DELTA = 0x00E63C24, 64
PERSON_START = 188


def pd(pl):
    """Deslocamento extra da parte PERSON deste jogador (0 normal, 64 jogador-treinador)."""
    return pl.get("pd", 0) if isinstance(pl, dict) else 0


def poff(pl, off):
    """Endereço absoluto de um campo do jogador, corrigindo a parte PERSON nos jogadores-treinadores."""
    return pl["addr"] + off + (pd(pl) if off >= PERSON_START else 0)

# Dentro do bloco apontado por SkillsPtr (todos sbyte, 1..20)
POSITIONS = dict(
    Goalkeeper=24, Sweeper=25, Defender=26, DefensiveMidfielder=27, Midfielder=28,
    AttackingMidfielder=29, Attacker=30, WingBack=31, FreeRole=32, Right=33, Centre=34, Left=35,
)
SKILLS = dict(
    Crossing=49, Dribbling=50, Finishing=51, Heading=52, LongShots=53, Marking=54,
    OffTheBall=55, Passing=56, PenaltyTaking=57, Tackling=58, Creativity=59, Handling=60,
    AerialAbility=61, CommandOfArea=62, Communication=63, Kicking=64, Throwing=65,
    Anticipation=66, Decisions=67, OneOnOnes=68, Positioning=69, Reflexes=70, FirstTouch=71,
    Technique=72, LeftFoot=73, RightFoot=74, Flair=75, Corners=76, Teamwork=77, Workrate=78,
    LongThrows=79, Eccentricity=80, RushingOut=81, TendencyToPunch=82, Acceleration=83,
    Freekicks=84, Strength=85, Stamina=86, Pace=87, Jumping=88, Influence=89, Dirtiness=90,
    Balance=91, Bravery=92, Consistency=93, Aggression=94, Agility=95, ImportantMatches=96,
    InjuryProneness=97, Versatility=98, NaturalFitness=99, Determination=100, Composure=101,
    Concentration=102,
)
# 13 bytes entre as posições e os atributos: provavelmente as "novas posições" do editor oficial (ordem a confirmar)
NEWPOS = dict(
    DefenderLeft=36, DefenderCentre=37, DefenderRight=38, DMCentre=39, MidLeft=40, MidCentre=41, MidRight=42,
    AMLeft=43, AMCentre=44, AMRight=45, Striker=46, WingBackLeft=47, WingBackRight=48,
)
ALL_SKILL_OFFSETS = {}
ALL_SKILL_OFFSETS.update(SKILLS); ALL_SKILL_OFFSETS.update(POSITIONS); ALL_SKILL_OFFSETS.update(NEWPOS)
SKILL_RANGE = (24, 103)  # bytes do bloco de skills que o "freeze attrs" preserva

# Atributos guardados em escala "fina" (sbyte -128..127); o jogo mostra floor((raw+99)/8),
# limitado a 1..20. 127 -> "28" = sobre-humano. Os demais são guardados direto em 1..20.
RAW_SKILLS = {
    "Crossing", "Dribbling", "Finishing", "Heading", "LongShots", "Marking", "OffTheBall",
    "Passing", "Tackling", "Creativity", "Handling", "AerialAbility", "CommandOfArea",
    "Communication", "Kicking", "Throwing", "Anticipation", "Decisions", "OneOnOnes",
    "Positioning", "Reflexes", "FirstTouch", "Technique", "Composure", "Concentration",
}


def raw_to_display(raw):
    return max(1, min(20, (raw + 99) // 8))


def display_to_raw(d):
    """Menor raw que mostra 'd'; pra 20 usa 61 (qualquer coisa de 61 a 127 mostra 20)."""
    return max(-128, min(127, d * 8 - 99))

# Personalidade (PERSON_DATA+24..+31). Ordem provável = editor oficial do FM2005 (alfabética em inglês).
PERSONALITY = ["Adaptability", "Ambition", "Loyalty", "Pressure", "Professionalism", "Sportsmanship", "Temperament", "Controversy"]  # confirmado (Casillas)

PREF_MOVES = [  # bits em player+160 (u64); nomes do editor oficial (fm_data_editor.exe + portuguese.ltf)
    (0, "Corre Com Bola Pela Esquerda (Runs With Ball Down Left)"),
    (1, "Corre Com Bola Pela Direita (Runs With Ball Down Right)"),
    (2, "Corre Com Bola Pelo Meio (Runs With Ball Through Centre)"),
    (3, "Entra Na Grande Área Adversária (Gets Into Opposition Area)"),
    (4, "Troca de Flancos (Moves Into Channels)"),
    (5, "Chega À Frente Sempre Que Possível (Gets Forward Whenever Possible)"),
    (6, "Joga Curto e Simples (Plays Short Simple Passes)"),
    (7, "Tenta Desmarcações Muitas Vezes (Tries Killer Balls Often)"),
    (8, "Remata de Longe (Shoots Long)"),
    (9, "Remata Com Força (Shoots With Power)"),
    (10, "Remata Em Jeito (Places Shots)"),
    (11, "Remata Com Efeito (Curls Ball)"),
    (12, "Gosta de Rodear G-Redes (Likes To Round Keeper)"),
    (13, "Gosta De Jogar No Limite do Fora-de-Jogo (Likes To Try To Beat Offside Trap)"),
    (14, "Usa Parte Externa Do Pé (trivela) (Uses Outside Of Foot)"),
    (15, "Marca Adversários Em Cima (Marks Opponent Tightly)"),
    (16, "Provoca Adversários (Winds Up Opponents)"),
    (17, "Discute Com Árbitros (Argues With Officials)"),
    (18, "Joga De Costas Para Baliza (Plays With Back To Goal)"),
    (19, "Vem Perto Buscar Jogo (Comes Deep To Get Ball)"),
    (20, "Faz Tabelinhas (Plays One Twos)"),
    (21, "Gosta de Fazer Balão Sobre G-R (Likes To Lob Keeper)"),
    (22, "Gere O Ritmo De Jogo (Dictates Tempo)"),
    (23, "Tenta Pontapés De Bicicleta (Attempts Overhead Kicks)"),
    (24, "Procura o passe em vez de tentar marcar (Looks For Pass Rather Than Attempting To Score)"),
    (25, "Não Faz Últimos Passes (Plays No Through Balls)"),
    (26, "Pára O Jogo (Stops Play)"),
    (27, "Desarma Adversários (Knocks Ball Past Opponent)"),
    (28, "Mete Bola No Pé Direito Antes De Ir Para A Finta (Moves Ball To Right Foot Before Dribble Attempt)"),
    (29, "Mete Bola No Pé Esquerdo Antes De Ir Para A Finta (Moves Ball To Left Foot Before Dribble Attempt)"),
    (30, "Adora Ter a Bola (Dwells On Ball)"),
    (31, "Chega Tarde À Área Adversária (Arrives Late In Opponents Area)"),
    (32, "Tenta Jogar Fora Da Confusão (Tries To Play Way Out Of Trouble)"),
    (33, "Fica Sempre Atrás (Stays Back At All Times)"),
    (34, "Evitar Utilizar Pé Mais Fraco (Avoids Using Weaker Foot)"),
    (35, "Tenta Truques (Tries Tricks)"),
    (36, "Tenta Marcar Livres de Muito Longe (Tries Long Range Freekicks)"),
    (37, "Cai Ao Mínimo Toque (Dives Into Tackles)"),
    (38, "Não Cai Ao Mínimo Toque (Does Not Dive Into Tackles)"),
    (39, "Vem Para Dentro (Cuts Inside)"),
    (40, "Vai à Linha (Hugs Line)"),
    (41, "Puxa Pelos Adeptos (Gets Crowd Going)"),
    (42, "Tenta Chutar De Primeira (Tries First Time Shots)"),
    (43, "Tenta Fazer Passes Longos (Tries Long Range Passes)"),
    (44, "Gosta De Ter Bola No Pé (Likes Ball Played Into Feet)"),
    (45, "Marca Livres Com Força (Hits Free Kick With Power)"),
    (46, "Usa e Abusa da Finta (Likes To Beat Man Repeatedly)"),
    (47, "Gosta De Passar Para Mudar De Flanco (Likes To Switch Ball To Other Flank)"),
]
PREF_MOVES += [(b, "bit %d (não usado)" % b) for b in range(48, 64)]
PREF_MOVES_OFF = 160

CONTRACT = dict(Wages=16, Started=24, Expires=32, AppearanceBonus=72, GoalBonus=76,
                AssistBonus=80, CleanSheetBonus=84)

# ----------------------------------------------------------------------------
# Acesso ao processo (ctypes puro)
# ----------------------------------------------------------------------------

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
PROCESS_VM_READ, PROCESS_VM_WRITE, PROCESS_VM_OPERATION, PROCESS_QUERY_INFORMATION = 0x10, 0x20, 0x08, 0x400
MEM_COMMIT, PAGE_GUARD, PAGE_NOACCESS = 0x1000, 0x100, 0x01


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD)]


k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, wt.LPCVOID, wt.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.argtypes = [wt.HANDLE, wt.LPVOID, wt.LPCVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.argtypes = [wt.HANDLE, wt.LPCVOID, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualAllocEx.argtypes = [wt.HANDLE, wt.LPVOID, ctypes.c_size_t, wt.DWORD, wt.DWORD]
k32.VirtualAllocEx.restype = wt.LPVOID
MEM_RESERVE, PAGE_READWRITE = 0x2000, 0x04


def find_pid(name):
    import subprocess
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if parts and name.lower() in parts[0].lower():
            return int(parts[1])
    return None


class Proc:
    def __init__(self, pid):
        self.h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION, False, pid)
        if not self.h:
            raise OSError("OpenProcess falhou (rode como administrador): erro %d" % ctypes.get_last_error())

    def read(self, addr, n):
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(self.h, addr, buf, n, ctypes.byref(got)):
            return b""
        return buf.raw[:got.value]

    def write(self, addr, data):
        n = ctypes.c_size_t()
        return bool(k32.WriteProcessMemory(self.h, addr, data, len(data), ctypes.byref(n)))

    def u8(self, a):  d = self.read(a, 1); return d[0] if d else None
    def i16(self, a): d = self.read(a, 2); return struct.unpack("<h", d)[0] if len(d) == 2 else None
    def u16(self, a): d = self.read(a, 2); return struct.unpack("<H", d)[0] if len(d) == 2 else None
    def u32(self, a): d = self.read(a, 4); return struct.unpack("<I", d)[0] if len(d) == 4 else None
    def i32(self, a): d = self.read(a, 4); return struct.unpack("<i", d)[0] if len(d) == 4 else None
    def w_i16(self, a, v): return self.write(a, struct.pack("<h", v))
    def w_u8(self, a, v):  return self.write(a, bytes([v & 0xFF]))

    def alloc(self, size):
        """Reserva memória nova dentro do jogo (fica alocada até o jogo fechar)."""
        return k32.VirtualAllocEx(self.h, None, max(size, 16), MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE) or 0

    def regions(self):
        """Regiões comprometidas e legíveis (melhor que a varredura cega do mcfm)."""
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while addr < 0x7FFF0000:
            if not k32.VirtualQueryEx(self.h, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            if mbi.State == MEM_COMMIT and not (mbi.Protect & PAGE_GUARD) and mbi.Protect != PAGE_NOACCESS:
                yield mbi.BaseAddress or 0, mbi.RegionSize
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize


# ----------------------------------------------------------------------------
# Modelo de dados
# ----------------------------------------------------------------------------

def fm_date(raw):
    """4 bytes little-endian: u16 dia-do-ano (0 = 1/jan) + u16 ano. Confirmado com 3 jogadores."""
    if raw is None:
        return "?"
    day = raw & 0xFFFF
    year = (raw >> 16) & 0xFFFF
    import datetime
    try:
        return (datetime.date(year, 1, 1) + datetime.timedelta(days=day)).strftime("%d/%m/%Y")
    except Exception:
        return "dia%d/%d" % (day, year)


def to_fm_date(d):
    return ((d.year & 0xFFFF) << 16) | ((d.timetuple().tm_yday - 1) & 0xFFFF)


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


COMP_VTABLES = {  # todas as classes derivadas de COMP (RTTI do fm2005.exe 5.0.0)
    0x00C895BC: 'COMP', 0x00E6A704: 'ACTUAL_COMP', 0x00E6D53C: 'UNDER_X_COMP', 0x00E71294: 'FRIENDLY_COMP',
    0x00E72254: 'EUR_CHAMPIONS_LEAGUE', 0x00E7247C: 'EUR_INTERTOTO_CUP', 0x00E726A4: 'EUR_SUPER_CUP', 0x00E728CC: 'EUR_UEFA_CUP',
    0x00E72AF4: 'EUR_ROYAL_LEAGUE', 0x00E74EEC: 'SVN_FIRST', 0x00E75114: 'SVN_SECOND', 0x00E7533C: 'SVN_CUP',
    0x00E756A4: 'ISL_PREM', 0x00E758CC: 'ISL_FIRST', 0x00E75AF4: 'ISL_CUP', 0x00E75D1C: 'ISL_UPPER_LEAGUE_CUP',
    0x00E75F44: 'ISL_LOWER_LEAGUE_CUP', 0x00E7617C: 'URU_FIRST', 0x00E763B4: 'URU_SECOND', 0x00E765EC: 'BLR_HIGHEST',
    0x00E76824: 'BLR_FIRST', 0x00E76A4C: 'BLR_CUP', 0x00E76C84: 'CHI_FIRST', 0x00E76EAC: 'CHI_FIRST_B',
    0x00E770D4: 'CHI_PRECOPASUD', 0x00E7736C: 'PER_FIRST', 0x00E775BC: 'ROM_CUP', 0x00E777E4: 'ROM_FIRST',
    0x00E77A0C: 'ROM_SUPER_CUP', 0x00E77C34: 'ROM_SECOND_GROUP', 0x00E77E5C: 'ROM_SECOND', 0x00E780A4: 'MAL_SUPER',
    0x00E782CC: 'MAL_FA_CUP', 0x00E784F4: 'MAL_CUP', 0x00E7871C: 'MAL_CHARITY', 0x00E78944: 'MAL_PREMIER_DIVISION',
    0x00E78B6C: 'MAL_PREMIER', 0x00E78DB4: 'BUL_A', 0x00E78FDC: 'BUL_B', 0x00E79204: 'BUL_CUP',
    0x00E7942C: 'BUL_SUPER_CUP', 0x00E79654: 'BUL_V_GROUPS_REGION', 0x00E7987C: 'BUL_V_GROUPS', 0x00E79AC4: 'HUN_FIRST',
    0x00E79CEC: 'HUN_FIRST_B', 0x00E79F14: 'HUN_CUP', 0x00E7A13C: 'HUN_SUPER_CUP', 0x00E7A374: 'UKR_HIGH',
    0x00E7A59C: 'UKR_FIRST', 0x00E7A7C4: 'UKR_CUP', 0x00E7A9EC: 'UKR_SUPER_CUP', 0x00E7AC14: 'UKR_SECOND_DIVISION',
    0x00E7AE3C: 'UKR_SECOND', 0x00E7B084: 'IDN_PREM', 0x00E7B2BC: 'IDN_FIRST_REGION', 0x00E7B4E4: 'IDN_FIRST',
    0x00E7B72C: 'SLV_FIRST', 0x00E7B954: 'SLV_CUP', 0x00E7BB7C: 'SLV_SUPER_CUP', 0x00E7BDA4: 'SLV_SECOND',
    0x00E7BFDC: 'COL_FIRST', 0x00E7C204: 'COL_SECOND', 0x00E7C43C: 'HON_FA_CUP', 0x00E7C664: 'HON_FIRST',
    0x00E7C88C: 'HON_LEAGUE_CUP', 0x00E7CAB4: 'HON_CHALLENGE_SHIELD', 0x00E7CCDC: 'HON_CHAMPIONS_CUP', 0x00E7CF14: 'SIN_CUP',
    0x00E7D13C: 'SIN_LEAGUE', 0x00E7D374: 'IND_FIRST', 0x00E7D59C: 'IND_DURAND_CUP', 0x00E7D7C4: 'IND_FED_CUP',
    0x00E7D9FC: 'WAL_PRM', 0x00E7DC8C: 'WAL_PRM_CUP', 0x00E7DEB4: 'WAL_LEAGUE_CUP', 0x00E7E0DC: 'WAL_CUP',
    0x00E7E314: 'ISR_CUP', 0x00E7E53C: 'ISR_PREM', 0x00E7E764: 'ISR_NATIONAL', 0x00E7E98C: 'ISR_PRM_TOTO_CUP',
    0x00E7EBB4: 'ISR_FIRST_TOTO_CUP', 0x00E7EDEC: 'MEX_FIRST', 0x00E7F01C: 'MEX_FIRST_A', 0x00E7F244: 'MEX_PREPRELIBER',
    0x00E7F47C: 'SWI_FIRST', 0x00E7F6A4: 'SWI_SECOND', 0x00E7F8CC: 'SWI_CUP', 0x00E7FAF4: 'SWI_FIRST_LEAGUE_GROUP',
    0x00E7FD1C: 'SWI_FIRST_LEAGUE', 0x00E7FF64: 'AUT_CUP', 0x00E8018C: 'AUT_FIRST', 0x00E803B4: 'AUT_PREM',
    0x00E805DC: 'AUT_SUPER_CUP', 0x00E80814: 'YUG_CUP', 0x00E80A3C: 'YUG_FIRST', 0x00E80C64: 'YUG_THIRD_DIVISION',
    0x00E80E8C: 'YUG_SECOND_DIVISION', 0x00E810B4: 'YUG_SECOND', 0x00E812EC: 'YUG_THIRD', 0x00E81534: 'CZE_CUP',
    0x00E8175C: 'CZE_FIRST', 0x00E81984: 'CZE_SECOND', 0x00E81BAC: 'CZE_THIRD_DIVISION', 0x00E81DD4: 'CZE_FOURTH_DIVISION',
    0x00E81FFC: 'CZE_FOURTH', 0x00E82234: 'CZE_THIRD', 0x00E8247C: 'RUS_CUP', 0x00E826A4: 'RUS_LEAGUE_CUP',
    0x00E828CC: 'RUS_FIRST', 0x00E82AF4: 'RUS_PREM', 0x00E82D1C: 'RUS_SUPER_CUP', 0x00E82F44: 'RUS_SECOND_REGION',
    0x00E8316C: 'RUS_SECOND', 0x00E833B4: 'POL_FIRST', 0x00E835DC: 'POL_FA_CUP', 0x00E83804: 'POL_SECOND',
    0x00E83A3C: 'IRE_FIRST', 0x00E83C64: 'IRE_PREM', 0x00E83E8C: 'IRE_SENIOR_CHAL_CUP', 0x00E840B4: 'IRE_PRESIDENT_CUP',
    0x00E842DC: 'IRE_LEINSTER_CUP', 0x00E84504: 'IRE_MUNSTER_CUP', 0x00E8472C: 'IRE_LEAGUE_CUP', 0x00E84954: 'IRE_CROSS_BORDER',
    0x00E84B7C: 'IRE_ALL_IRELAND', 0x00E84DE4: 'BRA_NAT_FIRST', 0x00E8500C: 'BRA_NAT_SECOND', 0x00E85234: 'BRA_NAT_THIRD',
    0x00E8545C: 'BRA_CUP', 0x00E85684: 'BRA_STATE_LEAGUE', 0x00E858AC: 'BRA_STATE_PARAIBA', 0x00E85AD4: 'BRA_STATE_PARANA',
    0x00E85CFC: 'BRA_STATE_PERNAM', 0x00E85F24: 'BRA_STATE_TOCAN', 0x00E8614C: 'BRA_STATE_SAO', 0x00E86374: 'BRA_STATE_GAUCHO',
    0x00E8659C: 'BRA_STATE_BAHIA', 0x00E867C4: 'BRA_STATE_SANTA', 0x00E869EC: 'BRA_STATE_PARA', 0x00E86C14: 'BRA_STATE',
    0x00E86E5C: 'CRO_A1', 0x00E87084: 'CRO_CUP', 0x00E872AC: 'CRO_SUPER_CUP', 0x00E874D4: 'CRO_THIRD_REGION',
    0x00E876FC: 'CRO_A2_REGION', 0x00E87924: 'CRO_A2', 0x00E87B5C: 'CRO_THIRD_NORTH', 0x00E87D94: 'CRO_THIRD_SOUTH',
    0x00E87FDC: 'TUR_PRM', 0x00E88214: 'TUR_CAT_A', 0x00E8843C: 'TUR_CUP', 0x00E88664: 'TUR_CAT_B_GROUP',
    0x00E8888C: 'TUR_CAT_B', 0x00E88AE4: 'AUS_NSL', 0x00E88D0C: 'AUS_CUP', 0x00E88F34: 'AUS_CHAMP',
    0x00E8916C: 'NIR_PREM', 0x00E89394: 'NIR_FIRST', 0x00E895BC: 'NIR_SECOND', 0x00E897E4: 'NIR_CUP',
    0x00E89A0C: 'NIR_LEAGUE_CUP', 0x00E89C34: 'NIR_INTER_LEAGUE_CUP', 0x00E89E5C: 'NIR_STEEL_CUP', 0x00E8A084: 'NIR_ANTRIM_SHIELD',
    0x00E8A2BC: 'GRE_CUP', 0x00E8A53C: 'GRE_PREM', 0x00E8A764: 'GRE_SEC', 0x00E8A98C: 'GRE_C_REGION',
    0x00E8ABB4: 'GRE_C', 0x00E8ADFC: 'FRE_CHARITY_CUP', 0x00E8B024: 'FRE_CUP', 0x00E8B24C: 'FRE_FIRST',
    0x00E8B474: 'FRE_LIGUE_CUP', 0x00E8B69C: 'FRE_NATIONAL', 0x00E8B8C4: 'FRE_SECOND', 0x00E8BAEC: 'FRE_CFA_REGION',
    0x00E8BD14: 'FRE_CFA', 0x00E8BF5C: 'DAN_FIRST', 0x00E8C184: 'DAN_PREM', 0x00E8C3AC: 'DAN_SECOND',
    0x00E8C5D4: 'DAN_CUP', 0x00E8C7FC: 'DAN_SUPER_CUP', 0x00E8CA24: 'DAN_THIRD_GROUP', 0x00E8CC4C: 'DAN_THIRD',
    0x00E8CE94: 'SWE_FIRST', 0x00E8D0BC: 'SWE_PREM', 0x00E8D2E4: 'SWE_THIRD_DIVISION', 0x00E8D50C: 'SWE_SECOND_DIVISION',
    0x00E8D734: 'SWE_SECOND', 0x00E8D96C: 'SWE_THIRD', 0x00E8DBA4: 'SWE_CUP', 0x00E8DDDC: 'HOL_FIRST',
    0x00E8E004: 'HOL_PREM', 0x00E8E22C: 'HOL_SUPER_CUP', 0x00E8E454: 'HOL_CUP', 0x00E8E68C: 'ESP_FIRST',
    0x00E8E8B4: 'ESP_SECOND', 0x00E8EADC: 'ESP_SUPER_CUP', 0x00E8ED04: 'ESP_SECOND_B_GROUP', 0x00E8EF2C: 'ESP_SECOND_B',
    0x00E8F194: 'ESP_CUP', 0x00E8F3CC: 'CHN_FIRST_A', 0x00E8F5F4: 'CHN_FIRST_B', 0x00E8F81C: 'CHN_CUP',
    0x00E8FA44: 'CHN_SUPER_CUP', 0x00E8FC6C: 'CHN_SUPER_LEAGUE_CUP', 0x00E8FE94: 'CHN_SECOND_REGION', 0x00E900BC: 'CHN_SECOND',
    0x00E90304: 'POR_CUP', 0x00E9052C: 'POR_PRM', 0x00E90754: 'POR_SECOND', 0x00E9097C: 'POR_SUPER_CUP',
    0x00E90BA4: 'POR_SECOND_B_DIVISION', 0x00E90DCC: 'POR_SECOND_B', 0x00E91014: 'ARG_PREMIER', 0x00E9123C: 'ARG_SECOND',
    0x00E91474: 'GER_CUP', 0x00E9169C: 'GER_FIRST', 0x00E918C4: 'GER_LEAGUE_CUP', 0x00E91AEC: 'GER_SECOND',
    0x00E91D14: 'GER_LOWER_DIVISIONS', 0x00E91F3C: 'GER_REGIONAL_DIVISION', 0x00E92164: 'GER_REGIONAL', 0x00E9239C: 'GER_LOWER',
    0x00E925E4: 'RSA_CHARITY_CUP', 0x00E9280C: 'RSA_CUP', 0x00E92A34: 'RSA_FIRST', 0x00E92C5C: 'RSA_PREM',
    0x00E92E84: 'RSA_SAFA_CUP', 0x00E930AC: 'RSA_TOP8_CUP', 0x00E932D4: 'RSA_VODA_CHALLENGE', 0x00E9350C: 'KOR_SUPER_CUP',
    0x00E93734: 'KOR_FA_CUP', 0x00E9395C: 'KOR_LEAGUE', 0x00E93B84: 'KOR_LEAGUE_2', 0x00E93DAC: 'KOR_ALL_STARS',
    0x00E93FD4: 'KOR_LEAGUE_CUP', 0x00E9420C: 'SCO_CHAL_CUP', 0x00E94434: 'SCO_CUP', 0x00E9465C: 'SCO_FIRST',
    0x00E94884: 'SCO_LEAGUE_CUP', 0x00E94AAC: 'SCO_PRM', 0x00E94CD4: 'SCO_SECOND', 0x00E94EFC: 'SCO_THIRD',
    0x00E95134: 'FIN_CUP', 0x00E9535C: 'FIN_FIRST', 0x00E95584: 'FIN_PREM', 0x00E957AC: 'FIN_SECOND_REGION',
    0x00E959D4: 'FIN_SECOND', 0x00E95C1C: 'BEL_CUP', 0x00E95E44: 'BEL_FIRST', 0x00E9606C: 'BEL_SECOND',
    0x00E96294: 'BEL_SUPER_CUP', 0x00E964BC: 'BEL_FOURTH_DIVISION', 0x00E966E4: 'BEL_THIRD_REGION', 0x00E9690C: 'BEL_FOURTH',
    0x00E96B44: 'BEL_THIRD', 0x00E96D8C: 'USA_COMBINE', 0x00E96FB4: 'USA_MLS', 0x00E971DC: 'USA_OPEN_CUP',
    0x00E97404: 'USA_ALL_STARS', 0x00E9773C: 'NOR_CUP', 0x00E97964: 'NOR_FIRST', 0x00E97B8C: 'NOR_PRM',
    0x00E97DB4: 'NOR_SECOND_DIVISION', 0x00E97FDC: 'NOR_SECOND', 0x00E98224: 'NAM_CHAMPIONS_CUP', 0x00E9845C: 'SAM_SUPER_CUP',
    0x00E98684: 'SAM_SUD_CUP', 0x00E988AC: 'SAM_LIBER_CUP', 0x00E98AE4: 'ITA_A', 0x00E98D0C: 'ITA_B',
    0x00E98F34: 'ITA_C2_DIVISION', 0x00E9915C: 'ITA_C_SUPER_CUP', 0x00E99384: 'ITA_SUPER_CUP', 0x00E995AC: 'ITA_D_DIVISION',
    0x00E997D4: 'ITA_C1_DIVISION', 0x00E999FC: 'ITA_C1', 0x00E99C34: 'ITA_C2', 0x00E99E6C: 'ITA_CUP',
    0x00E9A094: 'ITA_C_CUP', 0x00E9A2BC: 'ITA_D', 0x00E9A504: 'ENG_CHARITY', 0x00E9A72C: 'ENG_CONF',
    0x00E9A954: 'ENG_FA_CUP', 0x00E9AB7C: 'ENG_FIRST', 0x00E9ADA4: 'ENG_LEAGUE_CUP', 0x00E9AFCC: 'ENG_VANS_TROPHY',
    0x00E9B1F4: 'ENG_FA_TROPHY', 0x00E9B41C: 'ENG_PRM', 0x00E9B644: 'ENG_SECOND', 0x00E9B86C: 'ENG_THIRD',
    0x00E9BA94: 'ENG_REG_PRM_DIVISION', 0x00E9BCBC: 'ENG_CONF2_REGION', 0x00E9BEE4: 'ENG_CONF2', 0x00E9C11C: 'ENG_REG_PRM',
    0x00E9C364: 'ASI_CHAMPIONS_LEAGUE', 0x00E9C58C: 'ASI_ASEAN_CLUB_CHAMP', 0x00E9C7B4: 'ASI_EAST_CHAMP', 0x00E9C9DC: 'ASI_AFC_CUP',
    0x00E9CC14: 'AFR_CHAMPIONS_LEAGUE', 0x00E9CE3C: 'AFR_CUP_WINNERS_CUP', 0x00E9D064: 'AFR_SUPER_CUP', 0x00E9D314: 'OCE_CHAMPIONS_CUP',
    0x00E9D54C: 'WWCLUB_INTERCONTINENTAL_CUP', 0x00E9D774: 'WWCLUB_WORLD_CHAMP_CUP', 0x00E9D99C: 'WWCLUB_AFC_UEFA_CUP', 0x00E9DBC4: 'INTER_AFRICA_NATIONS_QUAL',
    0x00E9DDEC: 'INTER_AFRICA_NATIONS_CUP', 0x00E9E014: 'INTER_EURO_CHAMP', 0x00E9E23C: 'INTER_EURO_CHAMP_QUAL', 0x00E9E464: 'INTER_U21_EURO_CHAMP',
    0x00E9E68C: 'INTER_U19_EURO_CHAMP', 0x00E9E8B4: 'INTER_OCE_NATIONS_CUP', 0x00E9EADC: 'INTER_GOLD_CUP', 0x00E9ED04: 'INTER_ASIA_NATIONS_CUP',
    0x00E9EF2C: 'INTER_ASIA_NATIONS_QUAL', 0x00E9F1AC: 'INTER_FIFA_CONFED', 0x00E9F3D4: 'INTER_COPA_AMERICA', 0x00E9F5FC: 'INTER_OLYMPICS',
    0x00E9F824: 'INTER_OLYMPICS_OCEANIA_QUAL', 0x00E9FA4C: 'INTER_OLYMPICS_SOUTH_AMERICA_QUAL', 0x00E9FC74: 'INTER_U20_SOUTH_AMERICA_CHAMP', 0x00E9FE9C: 'INTER_AFC_OFC_CUP',
    0x00EA00C4: 'INTER_U21_EURO_CHAMP_QUAL', 0x00EA02EC: 'INTER_U19_EURO_CHAMP_QUAL', 0x00EA0514: 'WC_CONCACAF', 0x00EA073C: 'WC_EUROPE',
    0x00EA0964: 'WC_OCEANIA', 0x00EA0B8C: 'WC_SOUTH_AMERICA', 0x00EA0DB4: 'WC_WORLD_CUP', 0x00EA0FDC: 'WC_ASIA',
    0x00EA1204: 'WC_AFRICA', 0x00EA15AC: 'FRIENDLY_CUP', 0x00EA17DC: 'FRIENDLY_LEAGUE', 0x00EA1A1C: 'CHILD_COMP',
    0x00EA1C64: 'RESERVE_CUP', 0x00EA1E8C: 'RESERVE_CHILD_COMP', 0x00EA20B4: 'RESERVE_PARENT_COMP', 0x00EA22EC: 'FRIENDLY_ACTUAL_COMP',
}


class Game:
    def __init__(self, proc):
        self.p = proc
        self.version_name, self.version = self.detect_version()
        self.skills_off = PLAYER["SkillsPtr"] + (4 if self.version == 4 else 0)
        self.players = []  # list of dict(addr, name)

    def _blobs(self):
        return [(b, self.p.read(b, s)) for b, s in self.p.regions() if b < 0x7FFF0000]

    def autodetect(self):
        """O cabeçalho do exe pode mentir (no-CD, patch parcial): escolhe a assinatura
        que mais encontra jogadores na memória, e confere o offset do bloco de skills."""
        blobs = self._blobs()
        g = SIG_ORDER.index("player")
        best, best_n = None, 0
        for key, sig in SIGNATURES.items():
            want = sig[g * 8:(g + 1) * 8]
            n = sum(d.count(want) for _, d in blobs)
            if n > best_n:
                best, best_n = key, n
        if best is None:
            return blobs
        self.sig_key = best
        names = {0: "5.0.0 Demo", 2: "5.0.0 Retail", 4: "5.0.2 Retail", "4b": "5.0.2 (alt)"}
        if best != self.version:
            print("Aviso: cabeçalho diz '%s', mas a memória bate com %s (%d jogadores). Usando %s."
                  % (self.version_name, names[best], best_n, names[best]))
            self.version_name = names[best] + " (detectada pela memória)"
            self.version = 4 if best == "4b" else best
            self.skills_off = PLAYER["SkillsPtr"] + (4 if self.version == 4 else 0)
        # confere offset do ponteiro de skills (152 ou 156) no primeiro jogador achado
        want = SIGNATURES[best][g * 8:(g + 1) * 8]
        for base, d in blobs:
            i = d.find(want)
            while i >= 0:
                if i % 4 == 0:
                    a = base + i
                    for off in (152, 156):
                        sk = self.p.u32(a + off)
                        blk = self.p.read(sk, 104) if sk and sk > 0x10000 else b""
                        # valida pelo bloco de posições (sempre 1..20) e pelo pé direito/esquerdo
                        if len(blk) == 104 and all(1 <= b <= 20 for b in blk[24:49]) \
                                and all(1 <= b <= 20 for b in (blk[73], blk[74])):
                            self.skills_off = off
                            return blobs
                i = d.find(want, i + 4)
        return blobs

    def detect_version(self):
        v = self.p.u32(IMAGE_BASE + VERSION_DWORD_OFFSET)
        if v in VERSIONS:
            return VERSIONS[v]
        return ("desconhecida (dword=%s) - assumindo 5.0.2" % v, 4)

    # --- strings (ptr triplo, como no GetName(addr, 28, 8) do mcfm)
    def read_name(self, addr):
        p1 = self.p.u32(addr)
        if not p1: return ""
        p2 = self.p.u32(p1 + 28)
        if not p2: return ""
        p3 = self.p.u32(p2 + 8)
        if not p3: return ""
        raw = self.p.read(p3, 96)
        s = raw.decode("utf-16-le", errors="replace")
        return s.split("\x00", 1)[0]

    # --- scan
    def scan(self):
        blobs = self.autodetect()
        sig = SIGNATURES[getattr(self, "sig_key", self.version)]
        g = SIG_ORDER.index("player")
        want = sig[g * 8:(g + 1) * 8]
        found = []
        self.unnamed = 0
        for base, data in blobs:
            start = 0
            while True:
                i = data.find(want, start)
                if i < 0:
                    break
                if i % 4 == 0:  # objetos são alinhados em 4
                    found.append(base + i)
                start = i + 4
        players = []
        found = [(a, 0) for a in found] + [(a, APANP_DELTA) for a in self.scan_objs(APANP_VT)]   # + jogadores-treinadores
        for a, delta in found:
            fn, ln, nk = (self.read_name(a + delta + PLAYER["FirstName"]), self.read_name(a + delta + PLAYER["LastName"]),
                          self.read_name(a + delta + PLAYER["Nickname"]))
            name = (fn + " " + ln).strip()
            if nk:
                name = "%s (%s)" % (nk, name)
            if not name.strip():
                self.unnamed += 1
                name = "(sem nome) @%08X" % a
            q = dict(addr=a, name=name, key=strip_accents(name).lower())
            if delta: q["pd"] = delta
            players.append(q)
        self.players = players
        return players

    # --- leitura de um jogador
    # Onde fica o bloco de atributos: ("ptr", off) = ponteiro em player+off (layout do mcfm);
    # ("inline", off) = o bloco começa em player+off (sem ponteiro). 'findskills' descobre.
    skills_mode = None

    def skills_base(self, pl):
        mode, off = self.skills_mode or ("ptr", self.skills_off)
        if mode == "inline":
            return pl["addr"] + off
        return self.p.u32(pl["addr"] + off) or 0

    def findskills(self, pl, values):
        """Procura a sequência de atributos (na ordem Crossing, Dribbling, Finishing, Heading,
        LongShots...) dentro da struct do jogador e em tudo que ela aponta."""
        seq = bytes(v & 0xFF for v in values)
        a = pl["addr"]
        hits = []
        blob = self.p.read(a, 1024)
        i = blob.find(seq)
        while i >= 0:
            hits.append(("inline", i - SKILLS["Crossing"], a + i)); i = blob.find(seq, i + 1)
        for off in range(0, min(len(blob), 512) - 3, 4):
            ptr = struct.unpack_from("<I", blob, off)[0]
            if 0x10000 < ptr < 0x7FFF0000 and not (a <= ptr < a + 1024):
                tgt = self.p.read(ptr, 512)
                j = tgt.find(seq)
                while j >= 0:
                    hits.append(("ptr", off, ptr + j, j - SKILLS["Crossing"])); j = tgt.find(seq, j + 1)
        return hits

    def hunt(self, pl, values):
        """Busca global: onde na memória aparece a sequência, e como chegar lá a partir do jogador."""
        a = pl["addr"]
        seq = bytes(v & 0xFF for v in values)
        seq16 = b"".join(struct.pack("<h", v) for v in values)
        blobs = self._blobs()
        out = []
        for label, pat in (("u8", seq), ("i16", seq16)):
            hits = []
            for base, d in blobs:
                i = d.find(pat)
                while i >= 0 and len(hits) < 2000:
                    hits.append(base + i); i = d.find(pat, i + 1)
            out.append((label, hits))
        struct_bytes = self.p.read(a, 2048)
        ptrs = [(off, struct.unpack_from("<I", struct_bytes, off)[0]) for off in range(0, len(struct_bytes) - 3, 4)]
        ptrs = [(o, v) for o, v in ptrs if 0x10000 < v < 0x7FFF0000]
        lines = []
        for label, hits in out:
            lines.append("formato %s: %d ocorrências na memória" % (label, len(hits)))
            for h in hits[:200]:
                rel = h - a
                near = "dentro da struct (player%+d)" % rel if -64 <= rel < 2048 else ""
                paths = ["player+%d -> @%08X (%+d)" % (o, v, h - v) for o, v in ptrs if -512 <= h - v < 512]
                if not paths and not near:
                    # 2 níveis: ponteiro -> bloco -> ponteiro perto do hit
                    for o, v in ptrs:
                        blk = self.p.read(v, 256)
                        for o2 in range(0, len(blk) - 3, 4):
                            v2 = struct.unpack_from("<I", blk, o2)[0]
                            if 0x10000 < v2 < 0x7FFF0000 and -512 <= h - v2 < 512:
                                paths.append("player+%d -> +%d -> @%08X (%+d)" % (o, o2, h - v2, h - v2))
                if near or paths:
                    lines.append("  @%08X  %s %s" % (h, near, "; ".join(paths[:4])))
        return "\n".join(lines)

    def hunt2(self, pl, values, win=64):
        """Procura janelas de bytes (1..20) perto do jogador que contenham o conjunto de valores
        em qualquer ordem. Olha a struct (2 KB) e tudo que ela aponta (1 KB cada, 2 níveis)."""
        from collections import Counter
        want = Counter(values)
        a = pl["addr"]
        regions = [("player", a, self.p.read(a, 2048))]
        seen = {a}
        lvl1 = []
        for off in range(0, 2048 - 3, 4):
            v = struct.unpack_from("<I", regions[0][2], off)[0]
            if 0x10000 < v < 0x7FFF0000 and v not in seen:
                seen.add(v); d = self.p.read(v, 1024)
                if d: regions.append(("player+%d" % off, v, d)); lvl1.append((off, v, d))
        for off, v, d in lvl1:
            for off2 in range(0, min(len(d), 512) - 3, 4):
                v2 = struct.unpack_from("<I", d, off2)[0]
                if 0x10000 < v2 < 0x7FFF0000 and v2 not in seen:
                    seen.add(v2); d2 = self.p.read(v2, 1024)
                    if d2: regions.append(("player+%d->+%d" % (off, off2), v2, d2))
        best = []
        for label, base, d in regions:
            for i in range(0, max(0, len(d) - win)):
                w = d[i:i + win]
                inrange = sum(1 for b in w if 1 <= b <= 20)
                if inrange < win * 0.6:
                    continue
                have = Counter(b for b in w if 1 <= b <= 20)
                score = sum(min(have[k], c) for k, c in want.items())
                best.append((score, inrange, label, base + i, w))
        best.sort(key=lambda t: (-t[0], -t[1]))
        lines = ["valores pedidos: %d | regiões examinadas: %d" % (sum(want.values()), len(regions))]
        shown = set()
        for score, inrange, label, addr, w in best:
            if any(abs(addr - s) < win for s in shown):
                continue
            shown.add(addr)
            lines.append("  score %d/%d  bytes 1..20: %d/%d  %s @%08X" % (score, sum(want.values()), inrange, win, label, addr))
            lines.append("     " + " ".join("%d" % b for b in w))
            if len(shown) >= 6:
                break
        return "\n".join(lines)

    def hunt3(self, pl, values, anchor=b"\x83" * 6, before=48, after=80):
        """Usa a assinatura '131 x6' como âncora: acha todos os blocos de atributos na memória,
        pontua contra os valores do jogador e procura ponteiros da struct até o melhor bloco."""
        from collections import Counter
        want = Counter(values); total = sum(want.values())
        a = pl["addr"]
        blobs = self._blobs()
        cands = []
        for base, d in blobs:
            i = d.find(anchor)
            while i >= 0:
                w = d[max(0, i - before):i + after]
                have = Counter(b for b in w if 1 <= b <= 20)
                score = sum(min(have[k], c) for k, c in want.items())
                cands.append((score, base + i, w))
                i = d.find(anchor, i + len(anchor))
        cands.sort(key=lambda t: -t[0])
        lines = ["blocos com âncora: %d" % len(cands)]
        sb = self.p.read(a, 2048)
        ptrs = [(o, struct.unpack_from("<I", sb, o)[0]) for o in range(0, len(sb) - 3, 4)]
        ptrs = [(o, v) for o, v in ptrs if 0x10000 < v < 0x7FFF0000]
        for score, addr, w in cands[:5]:
            lines.append("  score %d/%d  âncora @%08X  (janela começa em @%08X)" % (score, total, addr, addr - before))
            lines.append("     " + " ".join("%d" % b for b in w))
            paths = ["player+%d -> @%08X (âncora em %+d)" % (o, v, addr - v) for o, v in ptrs if -8192 <= addr - v <= 8192]
            if not paths:
                for o, v in ptrs:
                    blk = self.p.read(v, 512)
                    for o2 in range(0, len(blk) - 3, 4):
                        v2 = struct.unpack_from("<I", blk, o2)[0]
                        if 0x10000 < v2 < 0x7FFF0000 and -8192 <= addr - v2 <= 8192:
                            paths.append("player+%d -> +%d -> @%08X (âncora em %+d)" % (o, o2, v2, addr - v2))
            lines.append("     caminho: " + ("; ".join(paths[:5]) if paths else "nenhum ponteiro direto"))
            lines.append("     dist. do player: %+d" % (addr - a))
        return "\n".join(lines)

    def pat(self, pl, tokens, head=62, size=128):
        """Busca global por padrão de bytes com curingas '?'. Mostra o bloco inteiro desde
        'head' bytes antes do match e quem aponta pra ele (ponteiros dentro da struct do jogador)."""
        import re
        rx = b"".join(b"." if t == "?" else re.escape(bytes([int(t) & 0xFF])) for t in tokens)
        rx = re.compile(rx, re.DOTALL)
        a = pl["addr"]
        blobs = self._blobs()
        hits = []
        for base, d in blobs:
            for m in rx.finditer(d):
                hits.append(base + m.start())
        lines = ["ocorrências: %d" % len(hits)]
        sb = self.p.read(a, 2048)
        for h in hits[:5]:
            start = h - head
            blk = self.p.read(start, size)
            lines.append("  match @%08X  bloco @%08X  (dist. do player %+d)" % (h, start, start - a))
            for i in range(0, len(blk), 32):
                lines.append("     %3d: %s" % (i, " ".join("%d" % b for b in blk[i:i + 32])))
            # quem aponta pra perto do bloco?
            refs = []
            for o in range(0, len(sb) - 3, 4):
                v = struct.unpack_from("<I", sb, o)[0]
                if -256 <= start - v <= 256:
                    refs.append("player+%d -> @%08X (bloco em %+d)" % (o, v, start - v))
            if not refs:
                for o in range(0, len(sb) - 3, 4):
                    v = struct.unpack_from("<I", sb, o)[0]
                    if 0x10000 < v < 0x7FFF0000:
                        blk2 = self.p.read(v, 512)
                        for o2 in range(0, len(blk2) - 3, 4):
                            v2 = struct.unpack_from("<I", blk2, o2)[0]
                            if -256 <= start - v2 <= 256:
                                refs.append("player+%d -> +%d -> @%08X (bloco em %+d)" % (o, o2, v2, start - v2))
            lines.append("     refs: " + ("; ".join(refs[:6]) if refs else "nenhuma na struct (2 níveis)"))
        return "\n".join(lines)

    SKILLBLOCK_HEAD = bytes.fromhex("8c58e300ffffffff")  # vtable 00E3588C + (-1)

    def block(self, pl):
        """Localiza o bloco de atributos do jogador cruzando ids e ponteiros."""
        a = pl["addr"]
        blobs = self._blobs()
        blocks = {}
        ids = {}
        for base, d in blobs:
            i = d.find(self.SKILLBLOCK_HEAD)
            while i >= 0:
                addr = base + i
                bid = struct.unpack_from("<I", d, i + 8)[0] if i + 12 <= len(d) else None
                blocks[addr] = bid
                ids.setdefault(bid, []).append(addr)
                i = d.find(self.SKILLBLOCK_HEAD, i + 8)
        lines = ["blocos: %d | ids distintos: %d" % (len(blocks), len(ids))]
        sb = self.p.read(a, 2048)
        found = []
        for o in range(0, len(sb) - 3, 4):
            v = struct.unpack_from("<I", sb, o)[0]
            for baddr in blocks:
                if -64 <= baddr - v <= 64:
                    found.append(("ponteiro", o, v, baddr))
            if v in ids and len(ids[v]) == 1 and v > 10:
                found.append(("id", o, v, ids[v][0]))
        if not found:
            # 2 níveis
            for o in range(0, len(sb) - 3, 4):
                v = struct.unpack_from("<I", sb, o)[0]
                if 0x10000 < v < 0x7FFF0000:
                    d2 = self.p.read(v, 1024)
                    for o2 in range(0, len(d2) - 3, 4):
                        v2 = struct.unpack_from("<I", d2, o2)[0]
                        if v2 in blocks:
                            found.append(("ponteiro2", "%d->+%d" % (o, o2), v2, v2))
        for kind, o, v, baddr in found[:8]:
            lines.append("  %s em player+%s = %s  ->  bloco @%08X" % (kind, o, "%d" % v if kind == "id" else "@%08X" % v, baddr))
            blk = self.p.read(baddr, 112)
            for i in range(0, len(blk), 28):
                lines.append("     %3d: %s" % (i, " ".join("%d" % b for b in blk[i:i + 28])))
        if not found:
            lines.append("  nada cruzou; id lido em player+204 = %s" % self.p.i32(a + 204))
        return "\n".join(lines)

    def finddate(self, pl, d_from, d_to, depth=2, size=16384):
        """Procura datas (u16 dia-do-ano + u16 ano) dentro da janela, na struct e nos objetos
        apontados (até 'depth' níveis). Devolve caminho + data decodificada."""
        import datetime
        lo, hi = to_fm_date(d_from), to_fm_date(d_to)
        def dates_in(buf):
            out = []
            for i in range(0, len(buf) - 3):
                v = struct.unpack_from("<I", buf, i)[0]
                y, day = v >> 16, v & 0xFFFF
                if 1990 <= y <= 2030 and day < 366:
                    if lo <= v <= hi:
                        out.append((i, fm_date(v)))
            return out
        seen = set()
        results = []
        def walk(addr, path, level):
            if addr in seen or level > depth:
                return
            seen.add(addr)
            buf = self.p.read(addr, size if level else PLAYER_STRUCT_SIZE)
            if not buf:
                return
            for i, ds in dates_in(buf):
                results.append("%s+%d  @%08X = %s" % (path, i, addr + i, ds))
            if level < depth:
                for o in range(0, min(len(buf), 1024) - 3, 4):
                    if level == 0 and (o in Watcher.NOT_POINTERS or o == 44):
                        continue
                    v = struct.unpack_from("<I", buf, o)[0]
                    if 0x01000000 < v < 0x7FFF0000 and v % 4 == 0:
                        walk(v, "%s+%d->" % (path, o), level + 1)
        walk(pl["addr"], "player", 0)
        return "\n".join(results) if results else "nenhuma data na janela"

    def follow(self, pl, chain):
        """Segue uma cadeia de ponteiros: player+c0 -> obj; obj+c1 -> obj2; ... devolve o endereço final."""
        addr = pl["addr"]
        for off in chain:
            addr = self.p.u32(addr + off)
            if not addr:
                return None
        return addr

    def peek(self, pl, chain, size=256, start=0):
        addr = self.follow(pl, chain)
        if not addr:
            return "ponteiro nulo no caminho"
        buf = self.p.read(addr + start, size)
        lines = ["objeto player->%s = @%08X (a partir de +%d)" % ("->".join("+%d" % c for c in chain), addr, start)]
        for k in range(0, len(buf), 16):
            i = start + k
            chunk = buf[k:k + 16]
            tags = []
            for j in range(0, 13, 4):
                v = struct.unpack_from("<I", chunk, j)[0] if j + 4 <= len(chunk) else 0
                y, day = v >> 16, v & 0xFFFF
                if 1990 <= y <= 2030 and day < 366:
                    tags.append("+%d=%s" % (i + j, fm_date(v)))
            lines.append("%4d  %-48s %s" % (i, chunk.hex(" "), "  ".join(tags)))
        return "\n".join(lines)

    def refs(self, pl, around=96, limit=40):
        """Quem aponta para este jogador? Varre a memória inteira atrás do endereço dele."""
        needle = struct.pack("<I", pl["addr"])
        hits = []
        for base, d in self._blobs():
            i = d.find(needle)
            while i >= 0 and len(hits) < 500:
                if i % 4 == 0:
                    hits.append(base + i)
                i = d.find(needle, i + 4)
        lines = ["referências ao jogador @%08X: %d" % (pl["addr"], len(hits))]
        for h in hits[:limit]:
            start = h - 32
            buf = self.p.read(start, around)
            tags = []
            for j in range(0, len(buf) - 3, 4):
                v = struct.unpack_from("<I", buf, j)[0]
                y, day = v >> 16, v & 0xFFFF
                if 1995 <= y <= 2020 and day < 366:
                    tags.append("+%d=%s" % (j - 32, fm_date(v)))
            lines.append("  ref @%08X (ponteiro em -32..): %s" % (h, "  ".join(tags)))
            for k in range(0, len(buf), 32):
                lines.append("     %4d: %s" % (k - 32, buf[k:k + 32].hex(" ")))
        return "\n".join(lines)

    def refsid(self, pl, around=128, limit=25, require_date=True):
        """Procura o id do jogador na memória; mostra só ocorrências com data por perto."""
        pid = self.p.i32(pl["addr"] + PLAYER["Id"])
        needle = struct.pack("<i", pid)
        hits = []
        for base, d in self._blobs():
            i = d.find(needle)
            while i >= 0:
                if i % 4 == 0 and base + i != pl["addr"] + PLAYER["Id"]:
                    ctx = d[max(0, i - 64):i + 64]
                    has_date = False
                    for j in range(0, len(ctx) - 3):
                        v = struct.unpack_from("<I", ctx, j)[0]
                        y, day = v >> 16, v & 0xFFFF
                        if 2004 <= y <= 2007 and day < 366:
                            has_date = True; break
                    if has_date or b"\xb4\xd3\xc4\x00" in ctx or not require_date:
                        hits.append(base + i)
                i = d.find(needle, i + 4)
        lines = ["id do jogador = %d; ocorrências com data por perto: %d" % (pid, len(hits))]
        for h in hits[:limit]:
            start = h - 64
            buf = self.p.read(start, around)
            tags = []
            for j in range(0, len(buf) - 3, 4):
                v = struct.unpack_from("<I", buf, j)[0]
                y, day = v >> 16, v & 0xFFFF
                if 2004 <= y <= 2007 and day < 366:
                    tags.append("%+d=%s" % (j - 64, fm_date(v)))
            lines.append("  id em @%08X: %s" % (h, "  ".join(tags)))
            for k in range(0, len(buf), 32):
                lines.append("     %+4d: %s" % (k - 64, buf[k:k + 32].hex(" ")))
        return "\n".join(lines)

    def dbsnap(self, pl, depth=2, size=256):
        """Foto do jogador por CAMINHO (não por endereço): serve para comparar dois saves diferentes."""
        snap = {}
        queue = [(pl["addr"], "player", 0)]
        seen = set()
        while queue and len(snap) < 400:
            addr, path, level = queue.pop(0)
            if addr in seen:
                continue
            seen.add(addr)
            buf = self.p.read(addr, PLAYER_STRUCT_SIZE if level == 0 else size)
            if not buf:
                continue
            snap[path] = buf.hex()
            if level < depth:
                for o in range(0, len(buf) - 3, 4):
                    v = struct.unpack_from("<I", buf, o)[0]
                    if 0x01000000 < v < 0x7FFF0000 and v % 4 == 0:
                        queue.append((v, "%s+%d" % (path, o), level + 1))
        return snap

    @staticmethod
    def dbdiff(a, b):
        """Compara duas fotos (dbsnap) caminho a caminho; ignora dwords que parecem ponteiros nos dois lados."""
        def ptrlike(buf, o):
            if o + 4 > len(buf): return False
            v = struct.unpack_from("<I", buf, o)[0]
            return (0x00400000 <= v < 0x7FFF0000)
        lines = []
        for path in a:
            if path not in b:
                continue
            x, y = bytes.fromhex(a[path]), bytes.fromhex(b[path])
            diffs = []
            for o in range(min(len(x), len(y))):
                if x[o] != y[o] and not (ptrlike(x, o - o % 4) and ptrlike(y, o - o % 4)):
                    diffs.append(o)
            if diffs:
                lines.append("== %s (%d bytes diferentes)" % (path, len(diffs)))
                for o in diffs:
                    lines.append("   +%-4d %3d (%02x) -> %3d (%02x)" % (o, x[o], x[o], y[o], y[o]))
        return "\n".join(lines) or "sem diferenças"

    def deepsnap(self, pl, depth=3, size=512, max_objs=3000):
        """Fotografa a struct e todos os objetos alcançáveis por ponteiros (até 'depth' níveis)."""
        snap = {}
        queue = [(pl["addr"], "player", 0)]
        while queue and len(snap) < max_objs:
            addr, path, level = queue.pop(0)
            if addr in snap:
                continue
            buf = self.p.read(addr, PLAYER_STRUCT_SIZE if level == 0 else size)
            if not buf:
                continue
            snap[addr] = (path, buf)
            if level < depth:
                for o in range(0, len(buf) - 3, 4):
                    if level == 0 and o in Watcher.NOT_POINTERS:
                        continue
                    v = struct.unpack_from("<I", buf, o)[0]
                    if 0x01000000 < v < 0x7FFF0000 and v % 4 == 0 and v not in snap:
                        queue.append((v, "%s+%d->" % (path, o), level + 1))
        return snap

    def deepdiff(self, old, new, days, skip_prefixes=("player+44->",)):
        lines = []
        hits = []
        def is_date(v):
            return 1990 <= ((v >> 16) & 0xFFFF) <= 2030 and (v & 0xFFFF) < 366
        for addr, (path, ob) in old.items():
            if any(path.startswith(p) for p in skip_prefixes):
                continue
            nb = new.get(addr)
            if nb is None:
                continue
            nb = nb[1]
            n = min(len(ob), len(nb))
            for o in range(0, n - 3):
                a4 = struct.unpack_from("<i", ob, o)[0]; b4 = struct.unpack_from("<i", nb, o)[0]
                if a4 == b4 or is_date(a4 & 0xFFFFFFFF) or is_date(b4 & 0xFFFFFFFF):
                    continue
                d = b4 - a4
                a2 = struct.unpack_from("<h", ob, o)[0]; b2 = struct.unpack_from("<h", nb, o)[0]
                a1, b1 = ob[o], nb[o]
                tag = ""
                if d == -days or d == days:
                    tag = "*** delta %+d (int32)" % d
                elif (b2 - a2) in (days, -days) and o % 2 == 0:
                    tag = "*** delta %+d (int16)" % (b2 - a2)
                elif (b1 - a1) in (days, -days):
                    tag = "** delta %+d (byte)" % (b1 - a1)
                if tag:
                    hits.append("  %s+%d @%08X: %d -> %d  %s" % (path, o, addr + o, a4, b4, tag))
        lines.append("objetos comparados: %d | campos que mudaram exatamente %d (sem datas, sem calendário): %d" % (len(old), days, len(hits)))
        lines.extend(hits[:150])
        return "\n".join(lines)

    def _ptr_refs(self, blobs, targets):
        """Endereços (alinhados) que contêm um ponteiro para qualquer um dos alvos (uma varredura só)."""
        import re
        targets = list(set(targets))
        if not targets:
            return {}
        rx = re.compile(b"|".join(re.escape(struct.pack("<I", t & 0xFFFFFFFF)) for t in targets))
        out = {}
        for base, d in blobs:
            for m in rx.finditer(d):
                if m.start() % 4 == 0:
                    t = struct.unpack("<I", m.group())[0]
                    out.setdefault(t, []).append(base + m.start())
        return out

    def injhunt(self, text, max_hops=4):
        """Acha um texto UTF-16, sobe a cadeia de quem aponta pra ele e mostra os donos."""
        blobs = self._blobs()
        enc = text.encode("utf-16-le")
        strs = []
        for base, d in blobs:
            i = d.find(enc)
            while i >= 0:
                strs.append(base + i); i = d.find(enc, i + 2)
        lines = ["texto '%s': %d ocorrências" % (text, len(strs))]
        if not strs:
            return "\n".join(lines)
        # volta até o início da string (terminador 00 00 anterior, alinhado a 2)
        starts = set()
        for a in strs[:40]:
            back = self.p.read(a - 256, 256)
            j = len(back)
            while j >= 2 and not (back[j - 2] == 0 and back[j - 1] == 0):
                j -= 2
            st = a - 256 + j
            starts.add(st)
            full = self.p.read(st, 120).decode("utf-16-le", errors="replace").split("\x00")[0]
            lines.append("   string @%08X: '%s'" % (st, full))
        # alvos: início da string e possíveis cabeçalhos antes dela
        level = sorted(set(x for st in starts for x in (st, st - 4, st - 8, st - 12, st - 16)))
        for hop in range(1, max_hops + 1):
            level = sorted(set(level))[:48]
            print("  (salto %d: procurando %d alvos...)" % (hop, len(level)))
            refs = self._ptr_refs(blobs, level)
            allrefs = sorted(set(a for lst in refs.values() for a in lst))
            lines.append("salto %d: %d campos apontam para o nível anterior" % (hop, len(allrefs)))
            for t, lst in sorted(refs.items()):
                lines.append("   alvo @%08X <- %s%s" % (t, ", ".join("@%08X" % a for a in lst[:8]), " ..." if len(lst) > 8 else ""))
            if not allrefs:
                break
            if len(allrefs) > 60:
                lines.append("   (muitas referências: provavelmente texto compartilhado pela interface; parando)")
                break
            # bases candidatas: para os primeiros saltos assumimos os offsets do mecanismo de nome (8, 28)
            if hop == 1:
                level = [a - 8 for a in allrefs]
            elif hop == 2:
                level = [a - 28 for a in allrefs]
            else:
                # objetos genéricos: mostramos contexto e tentamos bases em a-0..a-64
                for a in allrefs[:30]:
                    buf = self.p.read(a - 32, 96)
                    tags = []
                    for j in range(0, len(buf) - 3, 4):
                        v = struct.unpack_from("<I", buf, j)[0]
                        y, day = v >> 16, v & 0xFFFF
                        if 2004 <= y <= 2007 and day < 366: tags.append("%+d=%s" % (j - 32, fm_date(v)))
                    lines.append("   campo @%08X  %s" % (a, "  ".join(tags)))
                    for k in range(0, len(buf), 32):
                        lines.append("      %+4d: %s" % (k - 32, buf[k:k + 32].hex(" ")))
                level = sorted(set(a - o for a in allrefs for o in range(0, 68, 4)))
        return "\n".join(lines)

    try:  # vtables.json (gerado do RTTI do fm2005.exe): vtable -> nome da classe
        VTABLE_NAMES = {int(k, 16): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vtables.json"))).items()}
    except Exception:
        VTABLE_NAMES = {}
    VTABLES = {
        "PLAYER_INJURY": 0x00E1FD54, "PLAYER_BAN": 0x00E5AE84, "INJURY_MANAGER": 0x00E204C4,
        "PLAYER_BAN_LIST": 0x00CAE244, "PS_INJURY_LIST": 0x00CAE210, "INJURY": 0x00C82504,
        "SI_DATE": 0x00C80B70, "SI_SHORT_DATE": 0x00C4D3B4, "PLAYER_FORM": 0x00E54EDC,
        "MORALE_MANAGER": 0x00E258A8, "INJURY_HISTORY": 0x00CAD770, "CLUB": 0x00E54D04,
        "TEAM": 0x00E53C0C, "NATION": 0x00E557A4, "COMP": 0x00C895BC, "STADIUM": 0x00E5892C, "CLUB_FINANCE": 0x00E546EC,
    }
    # Offsets do MCFM05 (CLUB / finanças), validados pelos textos do exe
    CLUB = dict(Status=167, Training=168, AvgAtt=172, MinAtt=176, MaxAtt=180, KitPtr=64, FinancePtr=212, SponsorPtr=216)
    FIN = dict(Balance=4, SeasonTransferBudget=16, RemainingTransferBudget=20, WageBudget=116, WagesUsed=124)
    CURRENCY = 1.5  # o jogo guarda em moeda interna e mostra x1.5 (euros); ajuste se seu jogo mostrar outra moeda
    TRAINING_LABELS = {0: "Awful", 8: "Need major investment", 10: "Need some investment", 13: "Adequate", 16: "Top + youth academy"}

    def _name_at(self, p, hops):
        """Segue a cadeia de nome: hops = lista de offsets; último nível aponta para UTF-16."""
        for off in hops:
            if not p:
                return ""
            p = self.p.u32(p + off)
        if not p:
            return ""
        raw = self.p.read(p, 96)
        return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]

    def scan_objs(self, vtable):
        needle = struct.pack("<I", vtable)
        out = []
        for base, d in self._blobs():
            i = d.find(needle)
            while i >= 0:
                if i % 4 == 0:
                    out.append(base + i)
                i = d.find(needle, i + 4)
        return out

    def clubs(self, text):
        """Times (TEAM) cujo clube (team+44) tem nome contendo 'text'."""
        t = strip_accents(text).lower()
        res = []
        for team in self.scan_objs(self.VTABLES["TEAM"]):
            club = self.p.u32(team + 44)
            if not club:
                continue
            name = self._name_at(club, [32, 8])
            if name and t in strip_accents(name).lower():
                res.append(dict(team=team, club=club, name=name, kind=self.p.u8(team + 48)))
        # um clube pode ter vários TEAMs (principal, reservas, juniores): dedup por clube
        seen = {}
        for r in res:
            seen.setdefault(r["club"], r)
        return list(seen.values())

    def club_info(self, c):
        club = c["club"]
        fin = self.p.u32(club + self.CLUB["FinancePtr"])
        tr = self.p.u8(club + self.CLUB["Training"])
        label = max((k for k in self.TRAINING_LABELS if k <= tr), default=0)
        lines = ["%s  CLUB @%08X  TEAM @%08X  reputação(TEAM+92)=%d/10000" % (c["name"], club, c["team"], self.p.i32(c["team"] + 92))]
        lines.append("  status(+167)=%d (1=Profissional 2=Semi 3=Amador)  instalações(+168)=%d/20 (%s)" % (
            self.p.u8(club + 167), tr, self.TRAINING_LABELS[label]))
        lines.append("  público médio/mín/máx (+172/176/180) = %d / %d / %d" % (
            self.p.i32(club + 172), self.p.i32(club + 176), self.p.i32(club + 180)))
        if fin and self.p.u32(fin) == self.VTABLES["CLUB_FINANCE"]:
            k = self.CURRENCY
            lines.append("  finanças @%08X (valores como o jogo mostra, x%.1f): saldo=%s  orç.transf.=%s  restante=%s  orç.salarial/sem=%s  salários usados/sem=%s" % (
                fin, k, "{:,.0f}".format(self.p.i32(fin + 4) * k), "{:,.0f}".format(self.p.i32(fin + 16) * k),
                "{:,.0f}".format(self.p.i32(fin + 20) * k), "{:,.0f}".format(self.p.i32(fin + 116) * k), "{:,.0f}".format(self.p.i32(fin + 124) * k)))
        elif fin:
            lines.append("  finanças @%08X (clube não jogável, só saldo): saldo=%s" % (fin, "{:,.0f}".format(self.p.i32(fin + 4) * self.CURRENCY)))
        return "\n".join(lines)

    COMP_NAME_HOPS = [[32, 8], [28, 8], [36, 8], [24, 8], [40, 8], [44, 8], [48, 8], [52, 8], [56, 8], [60, 8]]

    def _utf16_ok(self, s):
        return len(s) >= 3 and all(32 <= ord(ch) < 0x2000 for ch in s)

    def comp_name(self, addr):
        """Tenta as cadeias de ponteiro conhecidas até achar um texto UTF-16 plausível."""
        for hops in self.COMP_NAME_HOPS:
            try:
                s = self._name_at(addr, hops)
            except Exception:
                continue
            if self._utf16_ok(s):
                return s, hops
        return "", None

    def scan_many(self, vtables):
        """Acha objetos cujo primeiro dword é qualquer um dos vtables (uma passada de regex)."""
        pat = re.compile(b"|".join(re.escape(struct.pack("<I", v)) for v in vtables))
        out = []
        for base, d in self._blobs():
            for m in pat.finditer(d):
                if m.start() % 4 == 0:
                    out.append((base + m.start(), struct.unpack("<I", m.group())[0]))
        return out

    def comps(self, text=""):
        t = strip_accents(text).lower()
        res = []
        for addr, vt in self.scan_many(COMP_VTABLES):
            name, hops = self.comp_name(addr)
            if name and (not t or t in strip_accents(name).lower()):
                res.append(dict(addr=addr, name=name, cls=COMP_VTABLES[vt], hops=hops))
        return res

    def nations(self, text):
        t = strip_accents(text).lower()
        res = []
        for n in self.scan_objs(self.VTABLES["NATION"]):
            name = self._name_at(n, [32, 8])
            if name and t in strip_accents(name).lower():
                res.append(dict(addr=n, name=name))
        return res

    def player_at(self, v):
        """Se v cai dentro da struct de algum jogador, devolve (jogador, offset)."""
        for q in self.players:
            if q["addr"] <= v < q["addr"] + PLAYER_STRUCT_SIZE:
                return q, v - q["addr"]
        return None, None

    def objs(self, vtable, size=96, limit=12, only_player=None):
        """Lista objetos cuja vtable (dword em +0) é 'vtable'; anota datas e ponteiros p/ jogadores."""
        needle = struct.pack("<I", vtable)
        hits = []
        for base, d in self._blobs():
            i = d.find(needle)
            while i >= 0:
                if i % 4 == 0:
                    hits.append(base + i)
                i = d.find(needle, i + 4)
        lines = ["objetos com vtable %08X: %d" % (vtable, len(hits))]
        shown = 0
        for h in hits:
            buf = self.p.read(h, size)
            tags = []
            owner = None
            for j in range(0, len(buf) - 3, 4):
                v = struct.unpack_from("<I", buf, j)[0]
                y, day = v >> 16, v & 0xFFFF
                if 1990 <= y <= 2030 and day < 366:
                    tags.append("+%d=%s" % (j, fm_date(v)))
                elif 0x01000000 < v < 0x7FFF0000:
                    q, off = self.player_at(v)
                    if q:
                        tags.append("+%d=%s(+%d)" % (j, q["name"], off)); owner = q
            if only_player and (owner is None or owner["addr"] != only_player["addr"]):
                continue
            lines.append("  @%08X  %s" % (h, "  ".join(tags)))
            for k in range(0, len(buf), 32):
                lines.append("     %3d: %s" % (k, buf[k:k + 32].hex(" ")))
            shown += 1
            if shown >= limit:
                lines.append("  ..."); break
        return "\n".join(lines)

    # --- lesões e suspensões (via player+44 -> status; descoberto com RTTI do fm2005.exe)
    INJURY = dict(TypePtr=8, Start=76, DaysMin=80, DaysMax=82, Status=84)
    BAN = dict(Games=12, Date=20)

    def status_lists(self, pl):
        p = self.p.u32(pl["addr"] + PLAYER["StatusPtr"])
        if not p:
            return None, [], []
        # ARRAY<T*, D>: a contagem é 1 byte (o 'D' do RTTI = char); depois vem lixo
        inj = []
        data, n = self.p.u32(p + 8), self.p.u8(p + 12)
        if data and n and 0 < n < 50:
            inj = [self.p.u32(data + 4 * i) for i in range(n)]
        bans = []
        data, n = self.p.u32(p + 20), self.p.u8(p + 24)
        if data and n and 0 < n < 50:
            bans = [self.p.u32(data + 4 * i) for i in range(n)]
        return p, [x for x in inj if x], [x for x in bans if x]

    def injuries(self, pl):
        p, inj, bans = self.status_lists(pl)
        lines = [T("%s: lesões: %d | suspensões: %d") % (pl["name"], len(inj), len(bans))]
        for a in inj:
            lines.append(T("  lesão: início=%s  dias=%d..%d  status=%d") % (
                fm_date(self.p.u32(a + self.INJURY["Start"])), self.p.i16(a + self.INJURY["DaysMin"]),
                self.p.i16(a + self.INJURY["DaysMax"]), self.p.i16(a + self.INJURY["Status"])))
        for a in bans:
            lines.append(T("  suspensão: tipo=%d  jogos=%d  data=%s  comp=%d") % (
                self.p.u8(a + 4), self.p.i32(a + self.BAN["Games"]), fm_date(self.p.u32(a + self.BAN["Date"])), self.p.i32(a + 24)))
        return "\n".join(lines)

    def heal(self, pl, force=False):
        p, inj, bans = self.status_lists(pl)
        if not inj:
            return T("sem lesão registrada")
        for a in inj:
            self.p.w_i16(a + self.INJURY["DaysMin"], 0)
            self.p.w_i16(a + self.INJURY["DaysMax"], 0)
        msg = T("duração zerada em %d lesão(ões); avance 1 dia no jogo") % len(inj)
        if force:
            self.p.w_u8(p + 12, 0)
            msg += T(" | contagem da lista zerada (forçado)")
        return msg

    def unban(self, pl, force=False):
        p, inj, bans = self.status_lists(pl)
        if not bans:
            return T("sem suspensão registrada")
        for a in bans:
            self.p.write(a + self.BAN["Games"], struct.pack("<i", 0))
        msg = T("jogos de suspensão zerados em %d registro(s)") % len(bans)
        if force:
            self.p.w_u8(p + 24, 0)
            msg += T(" | contagem da lista zerada (forçado)")
        return msg

    def info(self, pl):
        a = pl["addr"]
        cond = self.p.i16(a + PLAYER["Condition"])
        sk = self.skills_base(pl)
        skills = {}
        if sk:
            blk = self.p.read(sk, 104)
            if len(blk) >= 103:
                for k, v in SKILLS.items():
                    raw = struct.unpack("b", blk[v:v + 1])[0]
                    skills[k] = (raw_to_display(raw), raw) if k in RAW_SKILLS else (raw, None)
        return dict(
            addr=a, name=pl["name"], condition=cond, condition_pct=(cond or 0) / 100.0,
            morale=self.p.i16(a + PLAYER["Morale"]),
            ca=self.p.i16(a + PLAYER["CurrentAbility"]), pa=self.p.i16(a + PLAYER["PotentialAbility"]),
            dob=fm_date(self.p.u32(poff(pl, PLAYER["DateOfBirth"]))), skills_addr=sk, skills=skills,
        )

    def personality(self, pl):
        pd = self.p.u32(poff(pl, PLAYER["PersonDataPtr"]))
        if not pd:
            return {}
        b = self.p.read(pd + 24, 8)
        return {k: b[i] for i, k in enumerate(PERSONALITY)} if len(b) == 8 else {}

    # --- lista de "relações" do jogador (player+364 -> ARRAY<RELATIONSHIP>, itens de 12 bytes em linha)
    REL_PTR, REL_SIZE, REL_INT_RETIRED = 364, 12, 10
    REL_ARRAY_VTABLE = 0x00E4CCAC

    def relationships(self, pl):
        arr = self.p.u32(poff(pl, self.REL_PTR))
        if not arr:
            return arr, 0, 0, []
        data, cnt = self.p.u32(arr + 4), self.p.u8(arr + 8)
        items = [self.p.read(data + i * self.REL_SIZE, self.REL_SIZE) for i in range(cnt)] if data else []
        return arr, data, cnt, items

    # --- aposentadoria anunciada ("RET" / "a reformar-se"): bit 0 do byte player+212 (foto 10/12/2007: Henriksen, van der Sar,
    #     Ovchinnikov, Poborsky, Keane, Faber têm o bit; só jogadores de 31+ anos o têm no resto do banco)
    RETIRE_FLAG_OFF, RETIRE_FLAG_BIT = 212, 0x01

    def retiring(self, pl):
        b = self.p.u8(pl["addr"] + self.RETIRE_FLAG_OFF)
        return bool(b and b & self.RETIRE_FLAG_BIT)

    def set_retiring(self, pl, on):
        b = self.p.u8(pl["addr"] + self.RETIRE_FLAG_OFF)
        if b is None:
            return False
        b = (b | self.RETIRE_FLAG_BIT) if on else (b & ~self.RETIRE_FLAG_BIT & 0xFF)
        return self.p.write(pl["addr"] + self.RETIRE_FLAG_OFF, bytes([b]))

    # --- REGENERATION_MANAGER (vtable 00E30184; objeto global em 0x010141D0 no exe do usuário; funções 006B8BA0/006B63F0/006B68E0):
    #     +0x0C DEL_STEP_ARRAY<RETIREMENT*>  {vt, dados +0x10, cont. u32 +0x14, cap. +0x18}  = aposentadorias marcadas (executa quando a data chega)
    #     +0x1C DEL_STEP_ARRAY<RETIREMENT*>  (idem; segunda lista)
    #     +0x3C / +0x4C DEL_STEP_ARRAY<RETIREMENT_CONSIDERATION*> = "pensando" / "decidido" (item: +4 índice da pessoa, +12 data)
    #     RETIREMENT (24 bytes, sem vtable): +0 índice da pessoa (= player+208), +4 id do clube (TEAM+16), +0x10 SI_SHORT_DATE {vt, +0x14 data}
    REGEN_VT = 0x00E30184
    RET_ARR_VT, RETC_ARR_VT, RETC_ITEM_VT = 0x00E300E8, 0x00E30150, 0x00E2FC60
    RET_LISTS = ((0x0C, 0), (0x1C, 0), (0x3C, 4), (0x4C, 4))   # (offset do array, offset do índice dentro do item)
    PERSON_INDEX_OFF = 208

    def regen_manager(self):
        m = self.__dict__.get("_regen")
        if m and self.p.u32(m) == self.REGEN_VT and self.p.u32(m + 0x0C) == self.RET_ARR_VT:
            return m
        for a in self.scan_objs(self.REGEN_VT):
            if self.p.u32(a + 0x0C) == self.RET_ARR_VT and self.p.u32(a + 0x3C) == self.RETC_ARR_VT:
                self._regen = a
                return a
        return None

    def _arr(self, m, off):
        data, n, cap = self.p.u32(m + off + 4), self.p.u32(m + off + 8), self.p.u32(m + off + 12)
        items = list(struct.unpack("<%dI" % n, self.p.read(data, 4 * n))) if data and n and n < 20000 else []
        return data, n, cap, items

    def retire_lists(self):
        m = self.regen_manager()
        return [(off, ioff) + self._arr(m, off) for off, ioff in self.RET_LISTS] if m else []

    def retire_entries(self, pl):
        idx = self.p.u32(pl["addr"] + self.PERSON_INDEX_OFF)
        found = []
        for off, ioff, data, n, cap, items in self.retire_lists():
            for i, it in enumerate(items):
                if it and self.p.u32(it + ioff) == idx:
                    found.append((off, i, it, fm_date(self.p.u32(it + (0x14 if ioff == 0 else 12)))))
        return found

    def cancel_retirement(self, pl):
        """Tira o jogador das quatro listas e apaga o RET. Devolve quantos itens removeu."""
        m = self.regen_manager(); removed = 0
        if m:
            idx = self.p.u32(pl["addr"] + self.PERSON_INDEX_OFF)
            for off, ioff, data, n, cap, items in self.retire_lists():
                keep = [it for it in items if not (it and self.p.u32(it + ioff) == idx)]
                if len(keep) != len(items):
                    self.p.write(data, struct.pack("<%dI" % len(keep), *keep) if keep else b"")
                    self.p.write(m + off + 8, struct.pack("<I", len(keep)))
                    removed += len(items) - len(keep)
        self.set_retiring(pl, False)
        return removed

    # mark_retirement foi removido: criar o item fora do heap do jogo corrompe a memória quando o jogo o apaga (DEL_STEP_ARRAY).

    def int_retired(self, pl):
        """True se o jogador está 'afastado do futebol internacional' (item tipo 10 na lista)."""
        return any(it and it[0] == self.REL_INT_RETIRED for it in self.relationships(pl)[3])

    def set_int_retired(self, pl, on):
        arr, data, cnt, items = self.relationships(pl)
        has = [i for i, it in enumerate(items) if it and it[0] == self.REL_INT_RETIRED]
        if on and has or (not on and not has):
            return T("sem mudança")
        if not on:
            # remove o item: puxa os seguintes para trás e diminui o contador (sem alocar nada)
            i = has[0]
            rest = b"".join(items[i + 1:])
            if rest:
                self.p.write(data + i * self.REL_SIZE, rest)
            self.p.w_u8(arr + 8, cnt - 1)
            return T("removido 'afastado do futebol internacional'")
        # adiciona: precisa de um buffer maior -> aloca memória nova no jogo e copia os itens
        new_item = bytes([self.REL_INT_RETIRED, 100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        buf = self.p.alloc((cnt + 1) * self.REL_SIZE)
        if not buf:
            return T("falhou: não consegui alocar memória no jogo")
        self.p.write(buf, b"".join(items) + new_item)
        if not arr:
            arr = self.p.alloc(16)
            if not arr:
                return T("falhou: não consegui alocar memória no jogo")
            self.p.write(arr, struct.pack("<III", self.REL_ARRAY_VTABLE, buf, cnt + 1))
            self.p.write(poff(pl, self.REL_PTR), struct.pack("<I", arr))
        else:
            self.p.write(arr + 4, struct.pack("<I", buf))
            self.p.w_u8(arr + 8, cnt + 1)
        return T("marcado 'afastado do futebol internacional' (salve o jogo e recarregue o save para ficar 100% estável)")

    # --- contratos: player+308 = DEL_ARRAY<CONTRACT*> embutido {vtable +308, data +312, count u8 +316}; FULL_CONTRACT (vtable 00CB33A4):
    #     +4 -> PERSON (player+188), +8 -> CLUB, +16 salário/semana (moeda interna; o jogo mostra x1.5),
    #     +24 início (u16 dia, u16 ano), +32 fim. Confirmado com Vergassola (6250 -> 9.500, 30/06/2007).
    FULL_CONTRACT_VT = 0x00CB33A4
    CONTRACT_FIELDS = dict(Club=8, Wage=16, Start=24, End=32)

    def contracts(self, pl):
        # o array é EMBUTIDO no jogador: vtable em +308, dados em +312, contagem (u8) em +316
        # (conferido na foto do save: Vergassola +312 -> lista com 1 FULL_CONTRACT)
        data, cnt = self.p.u32(poff(pl, 312)), self.p.u8(poff(pl, 316))
        if not data:
            return []
        out = []
        for i in range(min(cnt or 0, 8)):
            c = self.p.u32(data + i * 4)
            if c and self.p.u32(c) == self.FULL_CONTRACT_VT:
                out.append(dict(addr=c, club=self.p.u32(c + 8), wage=self.p.i32(c + 16),
                                start=self.p.u32(c + 24), end=self.p.u32(c + 32)))
        return out

    # --- staff (ACTUAL_NON_PLAYER, vtable 00E61A6C, 284 bytes): +14 CA u16, +16 PA u16, +52 -> NON_PLAYING_DATA,
    #     +60 subobjeto PERSON (nomes +40/+44 -> +100/+104, nascimento +116, nação +128, PERSON_DATA +232), +156 -> TEAM,
    #     +180 array de contratos em linha {vtable, data +184, count +188}.
    #     NON_PLAYING_DATA +24..+57: 34 atributos; os de +50..+57 em escala fina: valor = round((bruto + 85) / 5).
    #     Ordem extraída do fm_data_editor.exe e confirmada com Ancelotti/Capello.
    STAFF_VT = 0x00E61A6C
    STAFF = dict(CA=14, PA=16, DataPtr=52, Person=60, DOB=116, Nation=128, Team=156, Contracts=180, PersonData=232)
    COACH_ATTRS = [  # (offset no NON_PLAYING_DATA, id do editor, nome PT do editor, nome EN, escala fina?)
        (24, "attk", "Atacante", "Attacking", False), (26, "tchq", "Treino Técnico", "Coaching Technique", False),
        (50, "cchg", "Treino Físico", "Coaching", True), (51, "chgk", "Treino Guarda-Redes", "Coaching Goalkeepers", True),
        (43, "dept", "Profundidade", "Depth", False), (29, "free", "Liberdade Jogadores", "Free Roles", False),
        (46, "hatr", "Intensidade de Treino", "Hardness Of Training", False), (31, "mark", "Marcação", "Marking", False),
        (32, "offs", "Fora de Jogo", "Offside", False), (56, "phys", "Fisioterapia", "Physiotherapy", True),
        (34, "prss", "Pressão", "Pressing", False), (47, "sqro", "Rotação do Plantel", "Squad Rotation", False),
        (57, "tcts", "Tácticas", "Tactics", True), (48, "temp", "Temporização", "Tempo", False),
        (41, "uply", "Uso de Organizador", "Use Of Playmaker", False), (42, "subs", "Uso de Substitutos", "Use Of Subs", False),
        (49, "widt", "Comprimento", "Width", False),
        (25, "buss", "Negócios", "Business", False), (38, "buyg", "Comprar Jogadores", "Buying Players", False),
        (37, "detr", "Determinação", "Determination", False), (27, "drct", "Jogo Directo", "Directness", False),
        (28, "dcpl", "Disciplina", "Discipline", False), (44, "flam", "Liberdade", "Flamboyancy", False),
        (45, "flex", "Flexibilidade", "Flexibility", False), (30, "intr", "Interferência", "Interference", False),
        (52, "judg", "Avaliação", "Judgement", True), (53, "potn", "Avaliação de Potencial", "Judging Potential", True),
        (54, "manh", "Gestão Pessoas", "Man Handling", True), (39, "mind", "Guerras de Palavras", "Mind Games", False),
        (55, "motv", "Motivação", "Motivation", True), (33, "patn", "Paciência", "Patience", False),
        (35, "rsrs", "Posses", "Resources", False), (40, "sitg", "Passividade", "Sitting Back", False),
        (36, "yung", "Aposta Jovens", "Youngsters", False),
    ]

    @staticmethod
    def coach_disp(raw, fine):
        return int(round((raw + 85) / 5.0)) if fine else raw

    @staticmethod
    def coach_raw(v, fine):
        return max(-128, min(127, 5 * v - 85)) if fine else max(0, min(127, v))

    def staff(self):
        out = []
        for a in self.scan_objs(self.STAFF_VT):
            person = a + self.STAFF["Person"]
            name = (self.read_name(person + 40) + " " + self.read_name(person + 44)).strip()
            if not name:
                continue
            team = self.p.u32(a + self.STAFF["Team"])
            club = self.p.u32(team + 44) if team and 0x01000000 < team < 0x7FFF0000 else 0
            nat = self.p.u32(a + self.STAFF["Nation"])
            out.append(dict(addr=a, name=name, team=team, club=club, club_name=self._name_at(club, [32, 8]) if club else "",
                            nation=self._name_at(nat, [32, 8]) if nat else "", dob=fm_date(self.p.u32(a + self.STAFF["DOB"])),
                            ca=self.p.i16(a + self.STAFF["CA"]), pa=self.p.i16(a + self.STAFF["PA"])))
        return out

    # ---- Transferência: TEAM+112 = STEP_ARRAY<PLAYER*> {vt 00E53A2C, +116 dados, +120 contagem, +124 capacidade};
    #      player+284 -> TEAM onde joga (emprestado: time que o recebe); FULL_CONTRACT+8 -> CLUB dono. A lista do TEAM é dos jogadores
    #      que o clube POSSUI (emprestado fica na lista do dono). (foto do save: Siena 29 jogadores / cap. 79; Barnetta/Freier emprestados)
    SQUAD_VT = 0x00E53A2C
    SQUAD = dict(Vt=112, Data=116, Count=120, Cap=124)
    PLAYER_TEAM = 284

    def squad(self, team):
        if self.p.u32(team + self.SQUAD["Vt"]) != self.SQUAD_VT:
            return None
        data, n = self.p.u32(team + self.SQUAD["Data"]), self.p.u16(team + self.SQUAD["Count"])   # 'F' no RTTI = contagem de 2 bytes
        if not data or n > 200:
            return None
        return dict(data=data, count=n, cap=self.p.u16(team + self.SQUAD["Cap"]),
                    items=list(struct.unpack("<%dI" % n, self.p.read(data, 4 * n))) if n else [])

    def squad_remove(self, team, addr):
        s = self.squad(team)
        if not s or addr not in s["items"]:
            return False
        items = [x for x in s["items"] if x != addr]
        self.p.write(s["data"], struct.pack("<%dI" % len(items), *items) if items else b"")
        self.p.write(team + self.SQUAD["Count"], struct.pack("<H", len(items)))
        return True

    def squad_add(self, team, addr):
        """Devolve (ok, realocou)."""
        s = self.squad(team)
        if not s:
            return False, False
        if addr in s["items"]:
            return True, False
        if s["cap"] > s["count"]:
            self.p.write(s["data"] + 4 * s["count"], struct.pack("<I", addr))
            self.p.write(team + self.SQUAD["Count"], struct.pack("<H", s["count"] + 1))
            return True, False
        newcap = s["count"] + 16
        buf = self.p.alloc(4 * newcap)
        if not buf:
            return False, False
        self.p.write(buf, struct.pack("<%dI" % (s["count"] + 1), *(s["items"] + [addr])))
        self.p.write(team + self.SQUAD["Data"], struct.pack("<I", buf))
        self.p.write(team + self.SQUAD["Count"], struct.pack("<H", s["count"] + 1))
        self.p.write(team + self.SQUAD["Cap"], struct.pack("<H", newcap))
        return True, True

    def transfer(self, pl, dest_team, dest_club, contract=None):
        """Move o jogador para outro clube: tira do elenco antigo, põe no novo, aponta player->TEAM e contrato->CLUB.
        Devolve (ok, realocou_lista). Se realocou, salve o jogo e recarregue o save."""
        a = pl["addr"]
        old = self.p.u32(poff(pl, self.PLAYER_TEAM))
        if old and 0x01000000 < old < 0x7FFF0000 and self.p.u32(old) == self.VTABLES["TEAM"]:
            self.squad_remove(old, a)
        ok, realloc = self.squad_add(dest_team, a)
        if not ok:
            return False, False
        self.p.write(poff(pl, self.PLAYER_TEAM), struct.pack("<I", dest_team))
        if contract:
            self.p.write(contract["addr"] + 8, struct.pack("<I", dest_club))
        return True, realloc

    def staff_attrs(self, st):
        d = self.p.u32(st["addr"] + self.STAFF["DataPtr"])
        if not d:
            return {}
        b = self.p.read(d + 24, 34)
        if len(b) < 34:
            return {}
        return {key: self.coach_disp(struct.unpack_from("<b", b, off - 24)[0], fine) for off, key, _, _, fine in self.COACH_ATTRS}

    def set_staff_attr(self, st, key, value):
        d = self.p.u32(st["addr"] + self.STAFF["DataPtr"])
        for off, k, _, _, fine in self.COACH_ATTRS:
            if k == key and d:
                return self.p.write(d + off, struct.pack("<b", self.coach_raw(int(value), fine)))
        return False

    def staff_contract(self, st):
        a = st["addr"]
        data, cnt = self.p.u32(a + self.STAFF["Contracts"] + 4), self.p.u8(a + self.STAFF["Contracts"] + 8)
        for i in range(min(cnt or 0, 8)):
            c = self.p.u32(data + i * 4)
            if c and self.p.u32(c) == self.FULL_CONTRACT_VT:
                return dict(addr=c, club=self.p.u32(c + 8), wage=self.p.i32(c + 16), start=self.p.u32(c + 24), end=self.p.u32(c + 32))
        return None

    def staff_personality(self, st):
        pd = self.p.u32(st["addr"] + self.STAFF["PersonData"])
        b = self.p.read(pd + 24, 8) if pd else b""
        return dict(zip(PERSONALITY, b)) if len(b) == 8 else {}

    # --- treinadores humanos (HUMAN_NON_PLAYER, 716 bytes): PERSON em +492 (nomes +40/+44, nascimento +116, nação +68 -> +560,
    #     PERSON_DATA +172 -> +664), TEAM em +588. CLUB_MANAGER_DETAILS (vtable 00E207A4): +20 TEAM, +24 e +48 CLUB_CONFIDENCE
    #     {vtable, u16 valor 0-10000, i16 tendência, ...} = diretoria e torcida (hipótese).
    HUMAN_VT, CMD_VT = 0x00E56F24, 0x00E207A4
    HUMAN = dict(Person=492, Team=588, Nation=560, DOB=548, PersonData=664)

    def humans(self):
        out = []
        for h in self.scan_objs(self.HUMAN_VT):
            team = self.p.u32(h + self.HUMAN["Team"])
            if not team or not (0x01000000 < team < 0x7FFF0000):
                continue
            person = h + self.HUMAN["Person"]
            name = (self.read_name(person + 40) + " " + self.read_name(person + 44)).strip()
            if not name:
                continue
            club = self.p.u32(team + 44)
            out.append(dict(addr=h, name=name, team=team, club=club, club_name=self._name_at(club, [32, 8]) if club else "",
                            nation=self._name_at(self.p.u32(h + self.HUMAN["Nation"]), [32, 8]) if self.p.u32(h + self.HUMAN["Nation"]) else "",
                            dob=fm_date(self.p.u32(h + self.HUMAN["DOB"]))))
        return out

    def human_contract(self, h):
        """Contrato do treinador humano: FULL_CONTRACT cujo +4 aponta para o PERSON (h+492)."""
        want = struct.pack("<I", h + self.HUMAN["Person"])
        for c in self.scan_objs(self.FULL_CONTRACT_VT):
            if self.p.read(c + 4, 4) == want:
                return dict(addr=c, club=self.p.u32(c + 8), wage=self.p.i32(c + 16), start=self.p.u32(c + 24), end=self.p.u32(c + 32))
        return None

    def manager_details(self, team):
        for m in self.scan_objs(self.CMD_VT):
            if self.p.u32(m + 20) == team:
                return m
        return None

    def human_personality(self, h):
        pd = self.p.u32(h + self.HUMAN["PersonData"])
        if not pd:
            return {}
        b = self.p.read(pd + 24, 8)
        return dict(zip(PERSONALITY, b)) if len(b) == 8 else {}

    def pref_moves(self, pl):
        d = self.p.read(pl["addr"] + PREF_MOVES_OFF, 8)
        return struct.unpack("<Q", d)[0] if len(d) == 8 else 0

    def set_pref_moves(self, pl, mask):
        return self.p.write(pl["addr"] + PREF_MOVES_OFF, struct.pack("<Q", mask & 0xFFFFFFFFFFFFFFFF))

    def set_personality(self, pl, key, value):
        pd = self.p.u32(poff(pl, PLAYER["PersonDataPtr"]))
        return bool(pd) and self.p.w_u8(pd + 24 + PERSONALITY.index(key), max(0, min(255, int(value))))

    def set_condition(self, pl, pct):
        return self.p.w_i16(pl["addr"] + PLAYER["Condition"], int(pct * 100))

    BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcfm_backup.json")

    def _backup_key(self, pl):
        # id do jogador (player+204) + nome: estável entre sessões e saves
        return "%s|%s" % (self.p.i32(pl["addr"] + PLAYER["Id"]), pl["name"])

    def backup(self, pl):
        """Guarda o bloco de atributos original (só na primeira vez)."""
        try:
            db = json.load(open(self.BACKUP_FILE, encoding="utf-8")) if os.path.exists(self.BACKUP_FILE) else {}
        except Exception:
            db = {}
        key = self._backup_key(pl)
        if key in db:
            return False
        sk = self.skills_base(pl)
        if not sk:
            return False
        lo, hi = SKILL_RANGE
        db[key] = dict(skills=list(self.p.read(sk + lo, hi - lo)),
                       condition=self.p.i16(pl["addr"] + PLAYER["Condition"]))
        json.dump(db, open(self.BACKUP_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return True

    def restore(self, pl):
        try:
            db = json.load(open(self.BACKUP_FILE, encoding="utf-8"))
        except Exception:
            return T("sem arquivo de backup")
        ent = db.get(self._backup_key(pl))
        if not ent:
            return T("sem backup para este jogador")
        sk = self.skills_base(pl)
        lo, hi = SKILL_RANGE
        ok = self.p.write(sk + lo, bytes(ent["skills"]))
        return T("atributos restaurados") if ok else T("falhou ao escrever")

    def set_skill(self, pl, skill, value, raw=False):
        """raw=False: value é o número que o jogo mostra (1..20); converte pra escala fina
        quando preciso. raw=True: escreve o byte bruto (-128..127; 127 = sobre-humano)."""
        sk = self.skills_base(pl)
        if not sk:
            return False
        v = int(value)
        if not raw and skill in RAW_SKILLS:
            v = display_to_raw(v)
        return self.p.w_u8(sk + ALL_SKILL_OFFSETS[skill], max(-128, min(127, v)))

    def dump(self, pl, size=PLAYER_STRUCT_SIZE):
        return self.p.read(pl["addr"], size)

    def find(self, text):
        t = strip_accents(text).lower()
        return [pl for pl in self.players if t in pl["key"]]


# ----------------------------------------------------------------------------
# Freezer: reescreve valores a cada 200 ms
# ----------------------------------------------------------------------------

class Freezer(threading.Thread):
    """Reescreve valores a cada 200 ms. Cada item tem um 'resolver' que devolve o endereço
    atual (o bloco de atributos pode mudar de lugar), e conta quantas vezes o jogo tentou
    alterar cada byte (pra sabermos o que ele está mexendo)."""
    def __init__(self, proc):
        super().__init__(daemon=True)
        self.p = proc
        self.items = {}  # key -> dict(resolve, data, label, fights{off:n}, writes)
        self.lock = threading.Lock()
        self.start()

    def add(self, key, label, resolve, data):
        with self.lock:
            self.items[key] = dict(resolve=resolve, data=bytes(data), label=label, fights={}, writes=0, moved=0, last=None)

    def remove_prefix(self, prefix):
        with self.lock:
            for k in [k for k in self.items if k.startswith(prefix)]:
                del self.items[k]

    def status(self):
        with self.lock:
            out = []
            for k, it in self.items.items():
                fights = sorted(it["fights"].items(), key=lambda t: -t[1])[:12]
                out.append("%s  reescritas=%d  bloco mudou de lugar=%d  bytes disputados=%s"
                           % (it["label"], it["writes"], it["moved"],
                              ", ".join("+%d(x%d)" % f for f in fights) if fights else "nenhum"))
            return "\n".join(out) if out else "nada congelado"

    def run(self):
        while True:
            with self.lock:
                items = list(self.items.values())
            for it in items:
                try:
                    addr = it["resolve"]()
                except Exception:
                    addr = None
                if not addr:
                    continue
                if it["last"] is not None and addr != it["last"]:
                    it["moved"] += 1
                it["last"] = addr
                cur = self.p.read(addr, len(it["data"]))
                if cur != it["data"]:
                    for i, (a, b) in enumerate(zip(cur, it["data"])):
                        if a != b:
                            it["fights"][i] = it["fights"].get(i, 0) + 1
                    self.p.write(addr, it["data"])
                    it["writes"] += 1
            time.sleep(0.2)


class Watcher(threading.Thread):
    """Vigia a struct de um jogador e imprime bytes que mudam, com hora.
    deep=True: vigia também o conteúdo de tudo que a struct aponta (objetos filhos)."""
    DEEP_SIZE = 192

    def __init__(self, proc, game, pl, size=PLAYER_STRUCT_SIZE, deep=False):
        super().__init__(daemon=True)
        self.p, self.game, self.pl, self.size, self.deep = proc, game, pl, size, deep
        self.stop = threading.Event()
        self.ignore = {PLAYER["Condition"], PLAYER["Condition"] + 1}
        self.start()

    NOT_POINTERS = {8, 12, 16, 20, 28, 36, 116, 120, 132, 136, 244, 264, 296, 304, 284}

    def targets(self, sb):
        out = {}
        for o in range(0, len(sb) - 3, 4):
            if o in self.NOT_POINTERS:
                continue
            v = struct.unpack_from("<I", sb, o)[0]
            if 0x01000000 < v < 0x7FFF0000 and v % 4 == 0 and v != self.pl["addr"]:
                out[o] = v
        return out

    def run(self):
        a = self.pl["addr"]
        prev = self.p.read(a, self.size)
        sk = self.game.skills_base(self.pl)
        prev_sk = self.p.read(sk, 104) if sk else b""
        prev_deep = {}
        if self.deep:
            for o, v in self.targets(prev).items():
                prev_deep[o] = (v, self.p.read(v, self.DEEP_SIZE))
        while not self.stop.is_set():
            time.sleep(1.0)
            cur = self.p.read(a, self.size)
            if cur and cur != prev:
                ch = [i for i in range(min(len(cur), len(prev))) if cur[i] != prev[i] and i not in self.ignore]
                if ch:
                    t = time.strftime("%H:%M:%S")
                    print("\n[watch %s] %s: " % (t, self.pl["name"]) +
                          "  ".join("+%d: %d->%d" % (i, prev[i], cur[i]) for i in ch[:30]) + "\nmcfm> ", end="")
                prev = cur
            if self.deep and cur:
                for o, v in self.targets(cur).items():
                    old = prev_deep.get(o)
                    d = self.p.read(v, self.DEEP_SIZE)
                    if old is None or old[0] != v:
                        if old is not None:
                            print("\n[deep %s] ponteiro player+%d mudou: @%08X -> @%08X\nmcfm> " % (time.strftime("%H:%M:%S"), o, old[0], v), end="")
                        prev_deep[o] = (v, d)
                        continue
                    if d != old[1]:
                        ch = [i for i in range(min(len(d), len(old[1]))) if d[i] != old[1][i]]
                        if ch:
                            print("\n[deep %s] %s player+%d->@%08X: " % (time.strftime("%H:%M:%S"), self.pl["name"], o, v) +
                                  "  ".join("+%d: %d->%d" % (i, old[1][i], d[i]) for i in ch[:30]) + "\nmcfm> ", end="")
                        prev_deep[o] = (v, d)
            if sk:
                cur_sk = self.p.read(sk, 104)
                if cur_sk and cur_sk != prev_sk:
                    ch = [i for i in range(104) if cur_sk[i] != prev_sk[i]]
                    print("\n[watch] bloco de atributos: " + "  ".join("+%d: %d->%d" % (i, prev_sk[i], cur_sk[i]) for i in ch) + "\nmcfm> ", end="")
                    prev_sk = cur_sk


def compare_groups(game, g1, g2, size=PLAYER_STRUCT_SIZE):
    """Offsets onde o grupo 1 difere sistematicamente do grupo 2."""
    d1 = [game.dump(pl, size) for pl in g1]
    d2 = [game.dump(pl, size) for pl in g2]
    lines = []
    for off in range(size):
        v1 = [d[off] for d in d1 if off < len(d)]
        v2 = [d[off] for d in d2 if off < len(d)]
        if not v1 or not v2:
            continue
        s1, s2 = set(v1), set(v2)
        if s1 & s2:
            continue  # algum valor aparece nos dois grupos: não separa
        kind = ""
        if all(v == 0 for v in v2) and all(v != 0 for v in v1):
            kind = "zero nos saudáveis, != 0 nos marcados"
        elif all(v == 0 for v in v1) and all(v != 0 for v in v2):
            kind = "!= 0 nos saudáveis, zero nos marcados"
        elif len(s1) == 1 and len(s2) == 1:
            kind = "constante em cada grupo"
        else:
            kind = "conjuntos disjuntos"
        lines.append("  +%-4d grupo1=%-24s grupo2=%-24s %s" % (off, v1, v2, kind))
    return "\n".join(lines) if lines else "  nenhum offset separa os grupos"


def regions_of(game, pl):
    """Regiões de memória do jogador para comparação: struct, bloco de skills, PERSON_DATA, status."""
    p = game.p
    a = pl["addr"]
    out = {"player": p.read(a, 768)}   # mais que os 412 conhecidos: a struct pode ser maior
    sk = game.skills_base(pl)
    if sk: out["skills"] = p.read(sk, 112)
    pd = p.u32(poff(pl, PLAYER["PersonDataPtr"]))
    if pd: out["person"] = p.read(pd, 32)
    st = p.u32(a + PLAYER["StatusPtr"])
    if st: out["status"] = p.read(st, 1024)
    # objetos apontados pela struct (nível 1) e pelos objetos de nível 1 (nível 2), 256 bytes cada
    buf = out["player"]
    lvl1 = []
    for off in range(0, len(buf) - 3, 4):
        v = struct.unpack_from("<I", buf, off)[0]
        if 0x01000000 < v < 0x7FFF0000 and v % 4 == 0:
            b = p.read(v, 512)
            out["p+%d" % off] = b
            lvl1.append((off, b))
    for off, b in lvl1:
        for o2 in range(0, len(b) - 3, 4):
            v = struct.unpack_from("<I", b, o2)[0]
            if 0x01000000 < v < 0x7FFF0000 and v % 4 == 0:
                out["p+%d>+%d" % (off, o2)] = p.read(v, 256)
    return out


def compare_bits(game, g1, g2):
    """Bits que são 1 em TODOS do grupo 1 e 0 em TODOS do grupo 2 (ou o contrário), em todas as regiões."""
    r1 = [regions_of(game, pl) for pl in g1]
    r2 = [regions_of(game, pl) for pl in g2]
    lines = []
    regs = ["player", "skills", "person", "status"] + sorted({k for r in r1 + r2 for k in r if k.startswith("p+")})
    for reg in regs:
        d1 = [r[reg] for r in r1 if reg in r]
        d2 = [r[reg] for r in r2 if reg in r]
        if len(d1) < len(r1) or len(d2) < len(r2):
            continue   # algum jogador não tem esse objeto: não dá pra comparar
        n = min(len(d) for d in d1 + d2)
        for off in range(n):
            # ignora dwords que parecem ponteiros
            o4 = off - off % 4
            if all(o4 + 4 <= len(d) and 0x00400000 <= struct.unpack_from("<I", d, o4)[0] < 0x7FFF0000 for d in d1 + d2):
                continue   # ponteiro: varia sempre
            for bit in range(8):
                b1 = [(d[off] >> bit) & 1 for d in d1]
                b2 = [(d[off] >> bit) & 1 for d in d2]
                if all(x == 1 for x in b1) and all(x == 0 for x in b2):
                    lines.append("  %-7s +%-4d bit %d  = 1 no grupo1, 0 no grupo2   (bytes g1=%s g2=%s)" % (reg, off, bit, [d[off] for d in d1], [d[off] for d in d2]))
                elif all(x == 0 for x in b1) and all(x == 1 for x in b2):
                    lines.append("  %-7s +%-4d bit %d  = 0 no grupo1, 1 no grupo2   (bytes g1=%s g2=%s)" % (reg, off, bit, [d[off] for d in d1], [d[off] for d in d2]))
    return "\n".join(lines) if lines else "  nenhum bit separa os grupos"


def compare_zero(game, g1, g2):
    """Dwords (e words) que são != 0 em TODOS de um grupo e 0 em TODOS do outro, em todas as regiões."""
    r1 = [regions_of(game, pl) for pl in g1]
    r2 = [regions_of(game, pl) for pl in g2]
    lines = []
    regs = ["player", "skills", "person", "status"] + sorted({k for r in r1 + r2 for k in r if k.startswith("p+")})
    def is_date(v):
        return 1950 <= ((v >> 16) & 0xFFFF) <= 2030 and (v & 0xFFFF) < 366
    for reg in regs:
        d1 = [r[reg] for r in r1 if reg in r]
        d2 = [r[reg] for r in r2 if reg in r]
        if len(d1) < len(r1) or len(d2) < len(r2):
            continue
        n = min(len(d) for d in d1 + d2)
        for off in range(0, n - 3, 2):
            v1 = [struct.unpack_from("<I", d, off)[0] for d in d1]
            v2 = [struct.unpack_from("<I", d, off)[0] for d in d2]
            if all(v for v in v1) and not any(v2):
                tag = "  <- parece DATA (%s)" % ", ".join(fm_date(v) for v in v1) if all(is_date(v) for v in v1) else ""
                lines.append("  %-7s +%-4d != 0 só no grupo1: %s%s" % (reg, off, v1, tag))
            elif all(v for v in v2) and not any(v1):
                tag = "  <- parece DATA (%s)" % ", ".join(fm_date(v) for v in v2) if all(is_date(v) for v in v2) else ""
                lines.append("  %-7s +%-4d != 0 só no grupo2: %s%s" % (reg, off, v2, tag))
    return "\n".join(lines) if lines else "  nada"


def compare_const(game, g1, g2):
    """Bytes/words/dwords com valor IGUAL dentro de cada grupo e DIFERENTE entre os grupos."""
    r1 = [regions_of(game, pl) for pl in g1]
    r2 = [regions_of(game, pl) for pl in g2]
    lines = []
    regs = ["player", "skills", "person", "status"] + sorted({k for r in r1 + r2 for k in r if k.startswith("p+")})
    for reg in regs:
        d1 = [r[reg] for r in r1 if reg in r]
        d2 = [r[reg] for r in r2 if reg in r]
        if len(d1) < len(r1) or len(d2) < len(r2):
            continue
        n = min(len(d) for d in d1 + d2)
        for off in range(n):
            v1 = {d[off] for d in d1}; v2 = {d[off] for d in d2}
            if len(v1) == 1 and len(v2) == 1 and v1 != v2:
                lines.append("  %-14s +%-4d byte: grupo1=%d  grupo2=%d" % (reg, off, v1.pop(), v2.pop()))
    return "\n".join(lines) if lines else "  nada"


# ----------------------------------------------------------------------------
# Anotação do dump (campos conhecidos)
# ----------------------------------------------------------------------------

def annotate(game, data, prev=None):
    known = {}
    for k, v in PLAYER.items():
        known[v] = k
    known[game.skills_off] = "SkillsPtr"
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hexs = []
        for i, b in enumerate(chunk):
            o = off + i
            s = "%02x" % b
            if prev is not None and o < len(prev) and prev[o] != b:
                s = "[" + s + "]"
            hexs.append(s)
        tags = [("%d=%s" % (o, known[o])) for o in range(off, off + 16) if o in known]
        lines.append("%4d  %-52s %s" % (off, " ".join(hexs), "  ".join(tags)))
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# CLI interativo
# ----------------------------------------------------------------------------

HELP = """
Comandos:
  find <nome>              procura jogadores pelo nome (vários: find casillas | elon)
  show <n>                 mostra condição, CA/PA, atributos do resultado n da última busca
  cond <n> [pct]           condição = pct (padrão 100)
  condall [pct]            condição de TODOS os jogadores encontrados (padrão 100)
  skill <n> <Nome> <1-20>  altera um atributo pelo valor que o jogo mostra (ex: skill 1 Pace 20)
  raw <n> <Nome> <v>       escreve o byte bruto, -128..127 (ex: raw 1 Finishing 127 = sobre-humano)
  max <n> [v]              todos = v; até 20 usa a escala do jogo, acima disso escreve bruto
                           (max 1 127 = time de super-heróis)
  findskills <n> a b c d.. localiza o bloco de atributos: informe os valores que o jogo
                           mostra, na ordem Cruzamento, Drible, Finalização, Cabeceio,
                           Chutes de longe, Marcação, Sem bola, Passe (mínimo 4)
  hunt2 <n> a b c d..      acha o bloco de atributos em QUALQUER ordem (passe todos os atributos)
  hunt <n> a b c d..       busca global da sequência na memória + caminho a partir do jogador
  banscan [dd/mm/aaaa]     lista objetos PLAYER_BAN (ou só os de uma data)
  clubs <nome> / club <n> [dump]   procura clubes; mostra status, instalações, público, finanças
  clubset <n> <campo> <v>  campos: reputation(0-10000) status training(0-20) avgatt minatt maxatt
                           balance transfer remaining wage (dinheiro: valor como o jogo mostra)
  nationset <n> <campo> <v> campos: reputation(0-10000, NATION+196, não verificável na tela)
  clubbyte/clubu16/clubint <n> <off> [v]      lê/escreve campo cru do clube (ex: clubbyte 1 164 20)
  nationbyte/nationu16/nationint <n> <off> [v] idem para país
  clubfin <n>              mostra o objeto de finanças do clube
  team <n> / cmpteam <n> <m> / teambyte|teamu16|teamint <n> <off> [v]   objeto TEAM do clube
  cmpclub <n> <m>          compara dois clubes (campos 0..10000 diferentes: reputação etc.)
  nations <nome> / nation <n>      procura países e mostra a struct
  comps <nome> / comp <n> / cmpcomp <n> <m>   competições: busca, struct, comparação byte a byte
  injuries <n>             mostra lesões e suspensões do jogador
  heal <n> [force]         cura: zera a duração da lesão (avance 1 dia); 'force' zera a lista na hora
  healall                  cura todos os jogadores lesionados do jogo
  unban <n>                remove a suspensão (tira da lista; efeito imediato)
  unbanall                 remove as suspensões de todos os jogadores
  morale <n> [1-20]        moral (padrão 20 = Excelente)
  moraleall [1-20]         moral de todos os jogadores
  freeze cond <n>          congela condição em 100%
  freeze attrs <n>         congela os atributos atuais (edite antes com skill/max)
  unfreeze <n>             remove congelamentos do jogador
  restore <n>              devolve os atributos originais (backup automático na 1ª edição)
  freezes                  mostra o que está congelado e quais bytes o jogo tentou mudar
  tag <grupo> <n>          põe o jogador n num grupo (ex: tag lesionado 1 / tag ok 2)
  cmp <grupo1> <grupo2>    bytes da struct que separam os dois grupos (acha lesão/suspensão)
  watch <n> / unwatch <n>  vigia a struct e imprime cada byte que mudar (acha moral etc.)
  deepwatch <n>            igual, mas vigia também os objetos que a struct aponta (lesão etc.)
  deepsnap <n> / deepdiff <n> <dias>  fotografa tudo alcançável; depois de avançar <dias>,
                           lista os campos que mudaram exatamente esse número (contadores de dias)
  chain <hex> [saltos]     sobe a cadeia "quem aponta pra quem" até chegar num jogador
  refsaddr <hex>           quem aponta para um endereço (diz se está dentro da struct de um jogador)
  objs <CLASSE> [n]        lista objetos da classe (ex: objs PLAYER_INJURY); com n, só os do jogador n
  classes                  classes conhecidas (vtables extraídas do fm2005.exe)
  injhunt <texto>          acha o texto (ex: nome de uma lesão) e sobe a cadeia de ponteiros até os donos
  cmpobj <n> <m> <o1>..    compara o objeto no caminho entre os jogadores n e m da última busca
  field <n> <off> [valor]  lê/escreve um int16 em player+off (ex: field 1 14 10000)
  who <hex>                diz qual jogador está nesse endereço
  peekaddr <hex> [@ini]    mostra 512 bytes a partir de um endereço (datas e ponteiro p/ jogador anotados)
  writeint <hex> <valor>   escreve um int32 num endereço (cuidado; salve o jogo antes)
  refsid <n> [all]         procura o id do jogador na memória (só onde há data por perto; 'all' = tudo)
  refs <n>                 lista tudo na memória que aponta para o jogador (registros de lesão etc.)
  finddate <n> <de> <até>  procura datas (dd/mm/aaaa) na struct e nos objetos apontados
  peek <n> <o1> <o2> .. [@ini]  mostra o objeto no caminho player+o1 -> +o2 -> ... (datas anotadas)
                           @ini = começar a mostrar a partir desse byte (ex: peek 1 48 264 @120)
  setdate <n> <o1>.. <campo> <dd/mm/aaaa>  escreve uma data no campo do objeto no caminho
  dump <n>                 hexdump anotado da struct do jogador (512 bytes)
  snap <n>                 guarda um snapshot da struct
  diff <n>                 compara com o snapshot e marca [bytes] que mudaram
  rescan                   varre a memória de novo (depois de carregar outro save)
  quit
"""


def main():
    if sys.platform != "win32":
        print("Este script precisa rodar no Windows com o FM2005 aberto.")
        return
    pid = find_pid(PROCESS_NAME)
    if not pid:
        print("Processo '%s' não encontrado. Abra o jogo e carregue um save." % PROCESS_NAME)
        return
    proc = Proc(pid)
    game = Game(proc)
    print("FM2005 pid=%d  versão: %s" % (pid, game.version_name))
    print("Varrendo memória...")
    t = time.time()
    players = game.scan()
    print("Jogadores encontrados: %d  (%.1fs)  | offset skills: +%d | sem nome: %d"
          % (len(players), time.time() - t, game.skills_off, game.unnamed))
    if not players:
        print("Nenhum jogador encontrado. O save está carregado? A versão do jogo bate?")
    freezer = Freezer(proc)
    last = []
    snaps = {}
    groups = {}
    watchers = {}
    lastc = []
    lastn = []
    lastk = []
    print(HELP)

    def pick(arg):
        try:
            return last[int(arg) - 1]
        except Exception:
            print("Use o número da última busca (find).")
            return None

    while True:
        try:
            line = input("mcfm> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        parts = line.split()
        cmd, args = parts[0].lower(), parts[1:]
        try:
            if cmd == "quit":
                break
            elif cmd == "help":
                print(HELP)
            elif cmd == "rescan":
                last = []
                print("Jogadores: %d" % len(game.scan()))
            elif cmd == "find":
                last = []
                for termo in " ".join(args).split("|"):
                    for q in game.find(termo.strip())[:40]:
                        if q["addr"] not in [x["addr"] for x in last]: last.append(q)
                for i, pl in enumerate(last, 1):
                    inf = game.info(pl)
                    print("%2d. %-35s cond=%5.1f%%  CA=%s PA=%s  @%08X" % (i, pl["name"], inf["condition_pct"], inf["ca"], inf["pa"], pl["addr"]))
            elif cmd == "show":
                pl = pick(args[0]);  inf = game.info(pl) if pl else None
                if inf:
                    print("%s  @%08X  nasc=%s  cond=%.1f%%  moral=%s/20  CA=%s  PA=%s  skills@%08X" % (inf["name"], inf["addr"], inf["dob"], inf["condition_pct"], inf["morale"], inf["ca"], inf["pa"], inf["skills_addr"] or 0))
                    print("   " + game.injuries(pl).split("\n", 1)[0])
                    items = sorted(inf["skills"].items())
                    def fmt(k, dv):
                        d, raw = dv
                        return "%-17s%3d%s" % (k, d, (" (%+4d)" % raw) if raw is not None else "       ")
                    for i in range(0, len(items), 3):
                        print("   " + "  ".join(fmt(k, dv) for k, dv in items[i:i + 3]))
                    print("   (entre parênteses: valor bruto dos atributos de escala fina; 127 = sobre-humano)")
            elif cmd == "cond":
                pl = pick(args[0]); pct = float(args[1]) if len(args) > 1 else 100.0
                if pl: print("ok" if game.set_condition(pl, pct) else "falhou")
            elif cmd == "condall":
                pct = float(args[0]) if args else 100.0
                n = sum(1 for pl in game.players if game.set_condition(pl, pct))
                print("condição %.0f%% aplicada em %d jogadores" % (pct, n))
            elif cmd == "skill":
                pl = pick(args[0])
                if pl:
                    if game.backup(pl): print("(backup dos atributos originais guardado)")
                    print("ok" if game.set_skill(pl, args[1], int(args[2])) else "falhou (nome do atributo?)")
            elif cmd == "raw":
                pl = pick(args[0])
                if pl:
                    if game.backup(pl): print("(backup dos atributos originais guardado)")
                    print("ok" if game.set_skill(pl, args[1], int(args[2]), raw=True) else "falhou (nome do atributo?)")
            elif cmd == "restore":
                pl = pick(args[0])
                if pl: print(game.restore(pl))
            elif cmd == "max":
                pl = pick(args[0]); val = int(args[1]) if len(args) > 1 else 20
                if pl:
                    if game.backup(pl): print("(backup dos atributos originais guardado)")
                    n = sum(1 for k in SKILLS if game.set_skill(pl, k, val, raw=(val > 20)))
                    print("%d atributos = %d%s" % (n, val, " (bruto, sobre-humano)" if val > 20 else ""))
            elif cmd == "hunt":
                pl = pick(args[0]); vals = [int(x) for x in args[1:]]
                if pl: print(game.hunt(pl, vals))
            elif cmd == "dbsnap":  # dbsnap <arquivo.json> <nome>   (foto do jogador para comparar entre saves)
                fn, hits = args[0], game.find(" ".join(args[1:]))
                if not hits:
                    print("jogador não encontrado")
                elif len(hits) > 1:
                    print("vários jogadores: " + " | ".join(h["name"] for h in hits[:10]) + "  (use o nome completo)")
                else:
                    pl = hits[0]
                    json.dump(game.dbsnap(pl), open(fn, "w"))
                    print("foto de %s salva em %s" % (pl["name"], fn))
            elif cmd == "dbdiff":  # dbdiff a.json b.json
                print(Game.dbdiff(json.load(open(args[0])), json.load(open(args[1]))))
            elif cmd == "deepsnap":
                pl = pick(args[0])
                if pl:
                    snaps[("deep", pl["addr"])] = game.deepsnap(pl)
                    print("fotografados %d objetos; avance N dias e rode 'deepdiff %s N'" % (len(snaps[("deep", pl["addr"])]), args[0]))
            elif cmd == "deepdiff":
                pl = pick(args[0]); days = int(args[1]) if len(args) > 1 else 1
                if pl:
                    old = snaps.get(("deep", pl["addr"]))
                    if old is None: print("faça 'deepsnap' primeiro")
                    else: print(game.deepdiff(old, game.deepsnap(pl), days))
            elif cmd == "refsid":
                pl = pick(args[0])
                if pl: print(game.refsid(pl, require_date=not (len(args) > 1 and args[1] == "all")))
            elif cmd == "refs":
                pl = pick(args[0])
                if pl: print(game.refs(pl))
            elif cmd == "peek":
                pl = pick(args[0])
                start = 0; chain = []
                for x in args[1:]:
                    if x.startswith("@"): start = int(x[1:])
                    else: chain.append(int(x))
                if pl: print(game.peek(pl, chain, start=start))
            elif cmd == "setdate":
                import datetime
                pl = pick(args[0])
                if pl:
                    *chain, field, ds = args[1:]
                    addr = game.follow(pl, [int(x) for x in chain])
                    d = datetime.datetime.strptime(ds, "%d/%m/%Y").date()
                    if addr:
                        tgt = addr + int(field)
                        print("antes: %s" % fm_date(proc.u32(tgt)))
                        ok = proc.write(tgt, struct.pack("<I", to_fm_date(d)))
                        print("depois: %s (%s)" % (fm_date(proc.u32(tgt)), "ok" if ok else "falhou"))
            elif cmd == "banscan":
                # banscan [dd/mm/aaaa] : lista objetos PLAYER_BAN (uma linha cada); com data, só os dessa data
                import datetime
                want = datetime.datetime.strptime(args[0], "%d/%m/%Y").date().strftime("%d/%m/%Y") if args else None
                needle = struct.pack("<I", game.VTABLES["PLAYER_BAN"])
                hits = []
                for base, d in game._blobs():
                    i = d.find(needle)
                    while i >= 0:
                        if i % 4 == 0: hits.append(base + i)
                        i = d.find(needle, i + 4)
                rows = []
                for h in hits:
                    b = proc.read(h, 40)
                    if len(b) < 40: continue
                    date = fm_date(struct.unpack_from("<I", b, 20)[0])
                    if want and date != want: continue
                    rows.append((date, "  @%08X  +4=%-6d +8=%-6d +10=%-4d +12(jogos?)=%-4d data(+20)=%s  +24=%-5d +28=%-8s | %s" % (
                        h, struct.unpack_from("<H", b, 4)[0], struct.unpack_from("<h", b, 8)[0], struct.unpack_from("<h", b, 10)[0],
                        struct.unpack_from("<i", b, 12)[0], date, struct.unpack_from("<i", b, 24)[0], "%08X" % struct.unpack_from("<I", b, 28)[0], b[:40].hex(" "))))
                rows.sort(key=lambda r: r[0][6:] + r[0][3:5] + r[0][:2], reverse=True)
                print("PLAYER_BAN: %d (mostrando %d)" % (len(hits), min(len(rows), 60)))
                for _, line in rows[:60]: print(line)
            elif cmd == "clubs":
                lastc = []
                for termo in " ".join(args).split("|"):
                    for c in game.clubs(termo.strip()):
                        if c["club"] not in [x["club"] for x in lastc]: lastc.append(c)
                for i, c in enumerate(lastc, 1):
                    print("%2d. %-40s CLUB @%08X  (team tipo %d)" % (i, c["name"], c["club"], c["kind"]))
                if not lastc: print("nenhum clube")
            elif cmd == "club":
                c = lastc[int(args[0]) - 1]
                print(game.club_info(c))
                if len(args) > 1 and args[1] == "dump":
                    buf = proc.read(c["club"], 512)
                    for k in range(0, len(buf), 16): print("  %4d  %s" % (k, buf[k:k + 16].hex(" ")))
            elif cmd == "clubset":
                # clubset <n> <campo> <valor>  campos: status training avgatt minatt maxatt balance transfer remaining wage
                c = lastc[int(args[0]) - 1]; campo = args[1].lower(); val = int(args[2])
                club = c["club"]; fin = proc.u32(club + game.CLUB["FinancePtr"])
                if campo in ("status", "training"):
                    ok = proc.w_u8(club + (167 if campo == "status" else 168), val)
                elif campo in ("reputation", "rep"):
                    ok = proc.write(c["team"] + 92, struct.pack("<i", max(0, min(10000, val))))
                elif campo in ("avgatt", "minatt", "maxatt"):
                    ok = proc.write(club + {"avgatt": 172, "minatt": 176, "maxatt": 180}[campo], struct.pack("<i", val))
                elif campo in ("balance", "transfer", "remaining", "wage") and fin:
                    # valor informado como o jogo mostra; convertido para a moeda interna
                    ok = proc.write(fin + {"balance": 4, "transfer": 16, "remaining": 20, "wage": 116}[campo], struct.pack("<i", int(val / game.CURRENCY)))
                else:
                    ok = False; print("campo desconhecido")
                print("ok" if ok else "falhou"); print(game.club_info(c))
            elif cmd in ("clubbyte", "clubu16", "clubint", "nationbyte", "nationu16", "nationint"):
                # <cmd> <n> <offset> [valor] : lê/escreve um campo cru no clube/país n da última busca
                base = lastc[int(args[0]) - 1]["club"] if cmd.startswith("club") else lastn[int(args[0]) - 1]["addr"]
                off = int(args[1]); a = base + off
                kind = cmd[-4:] if cmd.endswith(("byte", "u16")) else "int"
                rd = {"byte": proc.u8, "u16": lambda x: struct.unpack("<H", proc.read(x, 2))[0], "int": proc.i32}[kind]
                print("+%d: %s = %s" % (off, kind, rd(a)))
                if len(args) > 2:
                    v = int(args[2])
                    ok = {"byte": lambda: proc.w_u8(a, v), "u16": lambda: proc.write(a, struct.pack("<H", v)), "int": lambda: proc.write(a, struct.pack("<i", v))}[kind]()
                    print("ok" if ok else "falhou", "| agora =", rd(a))
            elif cmd == "team":
                c = lastc[int(args[0]) - 1]
                buf = proc.read(c["team"], 256)
                print("TEAM de %s @%08X" % (c["name"], c["team"]))
                for k in range(0, len(buf), 16): print("  %4d  %s" % (k, buf[k:k + 16].hex(" ")))
            elif cmd == "cmpteam":
                ca, cb = lastc[int(args[0]) - 1], lastc[int(args[1]) - 1]
                b1, b2 = proc.read(ca["team"], 256), proc.read(cb["team"], 256)
                print("TEAM %s @%08X  vs  %s @%08X" % (ca["name"], ca["team"], cb["name"], cb["team"]))
                for o in range(0, 252, 4):
                    if b1[o:o + 4] != b2[o:o + 4]:
                        print("  +%-4d %s  %-11d | %s  %-11d   u16: %d | %d" % (o, b1[o:o + 4].hex(" "), struct.unpack_from("<i", b1, o)[0],
                              b2[o:o + 4].hex(" "), struct.unpack_from("<i", b2, o)[0], struct.unpack_from("<H", b1, o)[0], struct.unpack_from("<H", b2, o)[0]))
            elif cmd in ("teambyte", "teamu16", "teamint"):
                base = lastc[int(args[0]) - 1]["team"]; off = int(args[1]); a = base + off
                kind = {"teambyte": "byte", "teamu16": "u16", "teamint": "int"}[cmd]
                rd = {"byte": proc.u8, "u16": lambda x: struct.unpack("<H", proc.read(x, 2))[0], "int": proc.i32}[kind]
                print("+%d: %s = %s" % (off, kind, rd(a)))
                if len(args) > 2:
                    v = int(args[2])
                    ok = {"byte": lambda: proc.w_u8(a, v), "u16": lambda: proc.write(a, struct.pack("<H", v)), "int": lambda: proc.write(a, struct.pack("<i", v))}[kind]()
                    print("ok" if ok else "falhou", "| agora =", rd(a))
            elif cmd == "clubfin":
                c = lastc[int(args[0]) - 1]; fin = proc.u32(c["club"] + game.CLUB["FinancePtr"])
                buf = proc.read(fin, 256)
                print("finanças de %s @%08X (int32 por posição):" % (c["name"], fin))
                for k in range(0, 256, 4):
                    v = struct.unpack_from("<i", buf, k)[0]
                    if v: print("  +%-4d %12d   %s" % (k, v, buf[k:k + 4].hex(" ")))
            elif cmd == "cmpclub":
                a, b = lastc[int(args[0]) - 1]["club"], lastc[int(args[1]) - 1]["club"]
                b1, b2 = proc.read(a, 1024), proc.read(b, 1024)
                print("%s @%08X  vs  %s @%08X (campos int16 diferentes, 0..10000)" % (lastc[int(args[0]) - 1]["name"], a, lastc[int(args[1]) - 1]["name"], b))
                for o in range(0, 1022, 2):
                    v1, v2 = struct.unpack_from("<H", b1, o)[0], struct.unpack_from("<H", b2, o)[0]
                    if v1 != v2 and 0 < v1 <= 10000 and 0 < v2 <= 10000:
                        print("  +%-4d %6d | %6d" % (o, v1, v2))
            elif cmd == "comps":
                lastk = game.comps(" ".join(args))
                for i, c in enumerate(lastk, 1): print("%2d. %-40s %-24s @%08X  nome via %s" % (i, c["name"], c["cls"], c["addr"], c["hops"]))
                if not lastk: print("nenhuma competição")
            elif cmd == "compset":  # compset N valor  -> reputação (COMP+96)
                c = lastk[int(args[0]) - 1]
                proc.write(c["addr"] + 96, struct.pack("<i", int(args[1])))
                print("%s: reputação(+96) = %d" % (c["name"], proc.i32(c["addr"] + 96)))
            elif cmd == "comp":
                c = lastk[int(args[0]) - 1]
                buf = proc.read(c["addr"], 512)
                print("%s @%08X  país=%s  reputação(+96)=%d  +92=%d  +100=%d" % (c["name"], c["addr"], game._name_at(proc.u32(c["addr"] + 72), [32, 8]), proc.i32(c["addr"] + 96), proc.i32(c["addr"] + 92), proc.i32(c["addr"] + 100)))
                for k in range(0, len(buf), 16): print("  %4d  %s" % (k, buf[k:k + 16].hex(" ")))
            elif cmd == "cmpcomp":
                a, b = lastk[int(args[0]) - 1], lastk[int(args[1]) - 1]
                b1, b2 = proc.read(a["addr"], 512), proc.read(b["addr"], 512)
                print("%s @%08X  vs  %s @%08X" % (a["name"], a["addr"], b["name"], b["addr"]))
                for o in range(0, 512):
                    if b1[o] != b2[o]: print("  +%-4d %3d | %3d" % (o, b1[o], b2[o]))
            elif cmd == "nations":
                lastn = game.nations(" ".join(args))
                for i, n in enumerate(lastn, 1): print("%2d. %-30s NATION @%08X" % (i, n["name"], n["addr"]))
                if not lastn: print("nenhum país")
            elif cmd == "nationset":
                n = lastn[int(args[0]) - 1]; campo = args[1].lower(); val = int(args[2])
                if campo in ("reputation", "rep"):
                    ok = proc.write(n["addr"] + 196, struct.pack("<H", max(0, min(10000, val))))
                    print("ok" if ok else "falhou", "| NATION+196 =", struct.unpack("<H", proc.read(n["addr"] + 196, 2))[0])
                else:
                    print("campo desconhecido (use nationbyte/nationu16 para campos crus)")
            elif cmd == "nation":
                n = lastn[int(args[0]) - 1]
                buf = proc.read(n["addr"], 768)
                print("%s @%08X" % (n["name"], n["addr"]))
                for k in range(0, len(buf), 16): print("  %4d  %s" % (k, buf[k:k + 16].hex(" ")))
            elif cmd == "injuries":
                pl = pick(args[0])
                if pl: print(game.injuries(pl))
            elif cmd == "heal":
                pl = pick(args[0])
                if pl: print(game.heal(pl, force=(len(args) > 1 and args[1] == "force")))
            elif cmd == "healall":
                n = 0
                for q in game.players:
                    if game.status_lists(q)[1]:
                        game.heal(q); n += 1
                print("duração zerada em %d jogadores lesionados; avance 1 dia" % n)
            elif cmd == "unban":
                pl = pick(args[0])
                if pl: print(game.unban(pl, force=not (len(args) > 1 and args[1] == "soft")))
            elif cmd == "unbanall":
                n = 0
                for q in game.players:
                    if game.status_lists(q)[2]:
                        game.unban(q, force=True); n += 1
                print("suspensões removidas de %d jogadores" % n)
            elif cmd == "morale":
                pl = pick(args[0]); val = int(args[1]) if len(args) > 1 else 20
                if pl: print("ok" if proc.w_i16(pl["addr"] + PLAYER["Morale"], max(0, min(127, val))) else "falhou")
            elif cmd == "moraleall":
                val = int(args[0]) if args else 20
                n = sum(1 for q in game.players if proc.w_i16(q["addr"] + PLAYER["Morale"], val))
                print("moral %d em %d jogadores" % (val, n))
            elif cmd == "chain":
                # chain <hex> [saltos] : sobe a cadeia de referências até cair na struct de um jogador
                target = int(args[0], 16); hops = int(args[1]) if len(args) > 1 else 5
                blobs = game._blobs()
                level = [target]
                for hop in range(1, hops + 1):
                    refs = game._ptr_refs(blobs, level[:40])
                    allrefs = sorted(set(a for lst in refs.values() for a in lst))
                    print("salto %d: %d referências" % (hop, len(allrefs)))
                    found_player = False
                    for a in allrefs[:12]:
                        q, off = game.player_at(a)
                        buf = proc.read(a - 16, 48)
                        tag = ("DENTRO DE %s (+%d)" % (q["name"], off)) if q else ""
                        # vtable conhecida 16/12/8/4 bytes antes?
                        print("   campo @%08X %s\n      %s" % (a, tag, buf.hex(" ")))
                        if q: found_player = True
                    if found_player or not allrefs or len(allrefs) > 40:
                        break
                    level = sorted(set(a - o for a in allrefs for o in (0, 4, 8, 12, 16, 20, 24)))
            elif cmd == "refsaddr":
                # refsaddr <hex> : quem aponta para este endereço (com contexto e jogador se for struct)
                target = int(args[0], 16)
                hits = []
                needle = struct.pack("<I", target)
                for base, d in game._blobs():
                    i = d.find(needle)
                    while i >= 0:
                        if i % 4 == 0: hits.append(base + i)
                        i = d.find(needle, i + 4)
                print("referências a @%08X: %d" % (target, len(hits)))
                for h in hits[:20]:
                    q, off = game.player_at(h)
                    where = "DENTRO DE %s (+%d)" % (q["name"], off) if q else ""
                    buf = proc.read(h - 16, 48)
                    print("  @%08X %s\n     %s" % (h, where, buf.hex(" ")))
            elif cmd == "objs":
                # objs <CLASSE|hex> [n]  : lista objetos da classe; com n, só os ligados ao jogador n
                key = args[0].upper()
                vt = game.VTABLES.get(key, None)
                if vt is None: vt = int(args[0], 16)
                pl = pick(args[1]) if len(args) > 1 else None
                print(game.objs(vt, only_player=pl, limit=(50 if pl else 12)))
            elif cmd == "classes":
                for k, v in game.VTABLES.items(): print("  %-16s %08X" % (k, v))
            elif cmd == "injhunt":
                print(game.injhunt(" ".join(args)))
            elif cmd == "cmpobj":
                # cmpobj <n> <m> <o1> <o2> ... : compara o objeto no caminho entre dois jogadores da última busca
                p1, p2 = pick(args[0]), pick(args[1]); chain = [int(x) for x in args[2:]]
                if p1 and p2:
                    a1, a2 = game.follow(p1, chain), game.follow(p2, chain)
                    if not a1 or not a2: print("ponteiro nulo (%s / %s)" % (a1, a2))
                    else:
                        b1, b2 = proc.read(a1, 1024), proc.read(a2, 1024)
                        print("%s @%08X  vs  %s @%08X" % (p1["name"], a1, p2["name"], a2))
                        n = min(len(b1), len(b2)); shown = 0
                        for o in range(0, n - 3, 4):
                            w1, w2 = b1[o:o + 4], b2[o:o + 4]
                            if w1 == w2: continue
                            v1, v2 = struct.unpack("<i", w1)[0], struct.unpack("<i", w2)[0]
                            kind = "ptr" if (0x01000000 < (v1 & 0xFFFFFFFF) < 0x7FFF0000 and 0x01000000 < (v2 & 0xFFFFFFFF) < 0x7FFF0000) else ""
                            print("  +%-4d %s  %-12d | %s  %-12d %s" % (o, w1.hex(" "), v1, w2.hex(" "), v2, kind))
                            shown += 1
                            if shown >= 120: print("  ..."); break
            elif cmd == "who":
                addr = int(args[0], 16)
                pls = [q for q in game.players if q["addr"] == addr]
                if not pls:
                    pls = [q for q in game.players if q["addr"] <= addr < q["addr"] + PLAYER_STRUCT_SIZE]
                    if pls: print("(endereço cai dentro da struct de %s, offset +%d)" % (pls[0]["name"], addr - pls[0]["addr"]))
                if pls:
                    last = pls; inf = game.info(pls[0])
                    print(" 1. %-35s cond=%5.1f%%  CA=%s PA=%s  @%08X  +40=%s" % (inf["name"], inf["condition_pct"], inf["ca"], inf["pa"], pls[0]["addr"], proc.i32(pls[0]["addr"] + 40)))
                else:
                    print("nenhum jogador nesse endereço")
            elif cmd == "peekaddr":
                addr = int(args[0], 16); start = 0
                for x in args[1:]:
                    if x.startswith("@"): start = int(x[1:])
                buf = proc.read(addr + start, 512)
                print("@%08X (a partir de +%d)" % (addr, start))
                for k in range(0, len(buf), 16):
                    i = start + k; chunk = buf[k:k + 16]; tags = []
                    for j in range(0, 13, 4):
                        v = struct.unpack_from("<I", chunk, j)[0] if j + 4 <= len(chunk) else 0
                        y, day = v >> 16, v & 0xFFFF
                        if 1990 <= y <= 2030 and day < 366: tags.append("+%d=%s" % (i + j, fm_date(v)))
                        if v == (last[0]["addr"] if last else -1): tags.append("+%d=PONTEIRO PARA O JOGADOR" % (i + j))
                    print("%4d  %-48s %s" % (i, chunk.hex(" "), "  ".join(tags)))
            elif cmd == "field":
                # field <n> <offset> [valor]  : lê (ou escreve) um int16 na struct do jogador
                pl = pick(args[0]); off = int(args[1])
                if pl:
                    a = pl["addr"] + off
                    print("player+%d: int16=%d  u8=%d" % (off, proc.i16(a), proc.u8(a)))
                    if len(args) > 2:
                        print("ok" if proc.w_i16(a, int(args[2])) else "falhou", "| agora int16=%d" % proc.i16(a))
            elif cmd == "byte":
                # byte <n> <offset> [valor]  : lê (ou escreve) UM byte na struct do jogador
                pl = pick(args[0]); off = int(args[1])
                if pl:
                    a = pl["addr"] + off
                    print("player+%d: u8=%d (0x%02x)  int32=%d" % (off, proc.u8(a), proc.u8(a), proc.i32(a)))
                    if len(args) > 2:
                        print("ok" if proc.w_u8(a, int(args[2])) else "falhou", "| agora u8=%d" % proc.u8(a))
            elif cmd == "pbyte":
                # pbyte <n> <offset do ponteiro> <offset dentro do objeto> [valor] : byte num objeto apontado pela struct
                pl = pick(args[0]); poff = int(args[1]); off = int(args[2])
                if pl:
                    obj = proc.u32(pl["addr"] + poff)
                    if not obj: print("ponteiro nulo")
                    else:
                        a = obj + off
                        print("player+%d -> @%08X +%d: u8=%d (0x%02x)" % (poff, obj, off, proc.u8(a), proc.u8(a)))
                        if len(args) > 3:
                            print("ok" if proc.w_u8(a, int(args[3])) else "falhou", "| agora u8=%d" % proc.u8(a))
            elif cmd == "int":
                # int <n> <offset> [valor] : lê (ou escreve) um int32 na struct do jogador
                pl = pick(args[0]); off = int(args[1])
                if pl:
                    a = pl["addr"] + off
                    print("player+%d: int32=%d (0x%08X)" % (off, proc.i32(a), proc.u32(a)))
                    if len(args) > 2:
                        print("ok" if proc.write(a, struct.pack("<i", int(args[2]))) else "falhou", "| agora int32=%d (0x%08X)" % (proc.i32(a), proc.u32(a)))
            elif cmd == "obyte":
                # obyte <n> <o1> <o2> ... : <off> [valor]  -> byte no objeto player+o1->+o2->...; ':' separa o caminho do byte
                pl = pick(args[0])
                if pl and ":" in args:
                    i = args.index(":")
                    chain = [int(x) for x in args[1:i]]; off = int(args[i + 1])
                    obj = game.follow(pl, chain)
                    if not obj: print("ponteiro nulo no caminho")
                    else:
                        a = obj + off
                        vt = proc.u32(obj)
                        print("objeto @%08X (vtable %08X = %s) +%d: u8=%d (0x%02x)" % (obj, vt, game.VTABLE_NAMES.get(vt, "?"), off, proc.u8(a), proc.u8(a)))
                        if len(args) > i + 2:
                            print("ok" if proc.w_u8(a, int(args[i + 2])) else "falhou", "| agora u8=%d" % proc.u8(a))
            elif cmd == "arrscan":
                # arrscan <vtable hex> [bytes por item]  : acha ARRAYs com esse vtable e mostra os itens (ponteiros p/ jogador e datas anotados)
                vt = int(args[0], 16); size = int(args[1]) if len(args) > 1 else 48
                found = game.scan_objs(vt)
                print("%d arrays com vtable %08X (%s)" % (len(found), vt, game.VTABLE_NAMES.get(vt, "?")))
                for arr in found[:20]:
                    data, cnt = proc.u32(arr + 4), proc.u32(arr + 8) & 0xFFFF
                    print("  array @%08X  data=%08X  count=%d" % (arr, data, cnt))
                    if not data or cnt > 5000: continue
                    for i in range(min(cnt, 12)):
                        item = proc.u32(data + i * 4)
                        if not item: continue
                        b = proc.read(item, size)
                        notes = []
                        for o in range(0, len(b) - 3, 4):
                            v = struct.unpack_from("<I", b, o)[0]
                            q, qo = game.player_at(v) if 0x01000000 < v < 0x7FFF0000 else (None, None)
                            if q: notes.append("+%d=%s%s" % (o, q["name"], "" if qo == 0 else "(+%d)" % qo))
                            elif 1950 <= (v >> 16) <= 2030 and (v & 0xFFFF) < 366: notes.append("+%d=data %s" % (o, fm_date(v)))
                            elif v in game.VTABLE_NAMES: notes.append("+%d=%s" % (o, game.VTABLE_NAMES[v]))
                        print("     [%d] @%08X %s" % (i, item, b[:32].hex(" ")))
                        if notes: print("         " + "  ".join(notes))
            elif cmd == "intretire":  # intretire <n> on|off : marca/desmarca 'afastado do futebol internacional'
                pl = pick(args[0])
                if pl: print(game.set_int_retired(pl, args[1].lower() in ("on", "1", "sim")))
            elif cmd == "moves":  # moves <n> [+bit|-bit ...] : mostra/altera movimentos preferidos (player+160)
                pl = pick(args[0])
                if pl:
                    m = game.pref_moves(pl)
                    for a in args[1:]:
                        if a[0] == "+": m |= 1 << int(a[1:])
                        elif a[0] == "-": m &= ~(1 << int(a[1:]))
                    if len(args) > 1: game.set_pref_moves(pl, m)
                    print("%s: máscara = 0x%016X" % (pl["name"], m))
                    for b, nm in PREF_MOVES:
                        if m >> b & 1: print("   [%2d] %s" % (b, nm))
            elif cmd == "export":  # export <arquivo.zip> : exporta os objetos do jogo (jogadores, staff, contratos, clubes, ligas...) para análise offline
                fn = args[0] if args else "export.zip"
                import zipfile, time as _t
                t0 = _t.time()
                cls = {int(k, 16): v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_classes.json"))).items()}
                print("procurando %d classes na memória..." % len(cls))
                found = game.scan_many(list(cls))
                print("%d objetos encontrados (%.1fs); lendo..." % (len(found), _t.time() - t0))
                recs = []
                seen = set()
                def add(addr, size):
                    if not addr or addr in seen or not (0x01000000 < addr < 0x7FFF0000): return None
                    b = proc.read(addr, size)
                    if b:
                        seen.add(addr); recs.append((0, addr, b))
                    return b
                def ptrs(b, lo=0, hi=None):
                    hi = len(b) if hi is None else min(hi, len(b))
                    for o in range(lo, hi - 3, 4):
                        v = struct.unpack_from("<I", b, o)[0]
                        if 0x01000000 < v < 0x7FFF0000 and v % 4 == 0: yield o, v
                for addr, vt in found:
                    name, size = cls[vt]
                    b = proc.read(addr, size)
                    if not b: continue
                    seen.add(addr); recs.append((vt, addr, b))
                    if name in ("TEAM", "NATIONAL_TEAM"):
                        # +212 ARRAY<TEAM_COMP_STATS_LINK>: data em +216, count em +220; itens de 24 bytes com ponteiros p/ stats
                        data, n = struct.unpack_from("<I", b, 216)[0], b[220]
                        lb = add(data, 24 * n) if n else None
                        if lb:
                            for o, v in ptrs(lb): add(v, 128)
                    elif name == "ACTUAL_NON_PLAYER" or name == "HUMAN_NON_PLAYER":
                        for off in (48, 52):
                            if off + 4 <= len(b): add(struct.unpack_from("<I", b, off)[0], 256)
                    elif name == "ACTUAL_PLAYER":
                        arr = struct.unpack_from("<I", b, 312)[0]
                        ab = add(arr, 16)
                        if ab:
                            data, n = struct.unpack_from("<I", ab, 4)[0], ab[8]
                            add(data, 4 * n)
                    elif name.endswith("STAGE") or name in ("CLUB_CONFIDENCE", "CONFIDENCE"):
                        for o, v in ptrs(b):
                            vb = add(v, 1024)
                            if vb and name.endswith("STAGE"):
                                for o2, w in ptrs(vb, 0, 64): add(w, 4096)
                meta = dict(version=game.version if hasattr(game, "version") else "?", game_date=proc.read(0x01017028, 12).hex(),
                            skills_off=game.skills_off, players=[(q["addr"], q["name"]) for q in game.players],
                            classes={hex(k): v[0] for k, v in cls.items()})
                with zipfile.ZipFile(fn, "w", zipfile.ZIP_DEFLATED) as z:
                    z.writestr("meta.json", json.dumps(meta))
                    out = bytearray()
                    for vt, addr, b in recs:
                        out += struct.pack("<IIH", vt, addr, len(b)) + b
                    z.writestr("objs.bin", bytes(out))
                print("exportado %d objetos para %s (%.1f MB, %.0fs)" % (len(recs), fn, os.path.getsize(fn) / 1e6, _t.time() - t0))
            elif cmd == "rels":
                # rels <n> : lista a ARRAY<RELATIONSHIP> em player+364 (tipo 10 = afastado do futebol internacional)
                pl = pick(args[0])
                if pl:
                    arr = proc.u32(poff(pl, 364))
                    if not arr: print("sem lista"); continue
                    data, cnt = proc.u32(arr + 4), proc.u8(arr + 8)
                    print("%s: array @%08X (vtable %08X %s) data=%08X count=%d" % (pl["name"], arr, proc.u32(arr), game.VTABLE_NAMES.get(proc.u32(arr), "?"), data, cnt))
                    print("  (itens de 12 bytes, em linha; cabeçalho do array: %s)" % proc.read(arr, 16).hex(" "))
                    for i in range(cnt):
                        item = data + i * 12
                        b = proc.read(item, 12)
                        notes = []
                        for o in range(0, 12, 4):
                            v = struct.unpack_from("<I", b, o)[0]
                            if 1950 <= (v >> 16) <= 2030 and (v & 0xFFFF) < 366: notes.append("+%d=data %s" % (o, fm_date(v)))
                            elif v in game.VTABLE_NAMES: notes.append("+%d=%s" % (o, game.VTABLE_NAMES[v]))
                            elif 0x01000000 < v < 0x7FFF0000:
                                nm = game._name_at(v, [32, 8]) if proc.u32(v) in game.VTABLE_NAMES else ""
                                if nm and all(32 <= ord(c) < 0x2000 for c in nm): notes.append("+%d->%s '%s'" % (o, game.VTABLE_NAMES.get(proc.u32(v)), nm[:30]))
                        print("  [%d] @%08X tipo=%d(0x%02x)  %s" % (i, item, b[0], b[0], b.hex(" ")))
                        if notes: print("       " + "  ".join(notes))
            elif cmd == "writeint":
                addr = int(args[0], 16); val = int(args[1])
                print("antes: %d" % proc.i32(addr))
                print("ok" if proc.write(addr, struct.pack("<i", val)) else "falhou", "| depois: %d" % proc.i32(addr))
            elif cmd == "finddate":
                import datetime
                pl = pick(args[0])
                if pl:
                    d1 = datetime.datetime.strptime(args[1], "%d/%m/%Y").date()
                    d2 = datetime.datetime.strptime(args[2], "%d/%m/%Y").date()
                    print(game.finddate(pl, d1, d2))
            elif cmd == "block":
                pl = pick(args[0])
                if pl: print(game.block(pl))
            elif cmd == "pat":
                pl = pick(args[0])
                if pl: print(game.pat(pl, args[1:]))
            elif cmd == "hunt3":
                pl = pick(args[0]); vals = [int(x) for x in args[1:]]
                if pl: print(game.hunt3(pl, vals))
            elif cmd == "hunt2":
                pl = pick(args[0]); vals = [int(x) for x in args[1:]]
                if pl: print(game.hunt2(pl, vals))
            elif cmd == "findskills":
                pl = pick(args[0]); vals = [int(x) for x in args[1:]]
                if pl and len(vals) < 4:
                    print("informe pelo menos 4 valores: Cruzamento Drible Finalização Cabeceio [Chutes de longe ...]")
                elif pl:
                    hits = game.findskills(pl, vals)
                    if not hits:
                        print("sequência não encontrada; confira os valores no jogo e tente com mais atributos")
                    for h in hits:
                        if h[0] == "inline":
                            print("  bloco EMBUTIDO em player+%d (match @%08X)" % (h[1], h[2]))
                        else:
                            print("  bloco via PONTEIRO em player+%d -> @%08X (offset dentro do bloco: %+d)" % (h[1], h[2], h[3]))
                    if len(hits) == 1:
                        h = hits[0]
                        game.skills_mode = ("inline", h[1]) if h[0] == "inline" else ("ptr", h[1])
                        if h[0] == "ptr" and h[3] != 0:
                            print("  atenção: deslocamento %+d dentro do bloco; me mande esta saída" % h[3])
                        print("  modo de skills definido; use 'show %s' para conferir" % args[0])
                    elif len(hits) > 1:
                        print("  mais de um lugar bate; use mais valores pra desambiguar")
            elif cmd == "freeze":
                pl = pick(args[1])
                key = "%08X" % pl["addr"] if pl else ""
                if pl and args[0] == "cond":
                    freezer.add(key + ":cond", "%s condição" % pl["name"],
                                (lambda a=pl["addr"]: a + PLAYER["Condition"]), struct.pack("<h", 10000))
                    print("condição congelada")
                elif pl and args[0] == "attrs":
                    sk = game.skills_base(pl)
                    lo, hi = SKILL_RANGE
                    freezer.add(key + ":attrs", "%s atributos" % pl["name"],
                                (lambda p=pl: game.skills_base(p) + lo), proc.read(sk + lo, hi - lo))
                    print("atributos congelados (bytes %d..%d do bloco)" % (lo, hi - 1))
            elif cmd == "unfreeze":
                pl = pick(args[0])
                if pl:
                    freezer.remove_prefix("%08X" % pl["addr"]); print("ok")
            elif cmd == "freezes":
                print(freezer.status())
            elif cmd == "tag":
                pl = pick(args[1])
                if pl:
                    groups.setdefault(args[0], [])
                    if pl["addr"] not in [q["addr"] for q in groups[args[0]]]:
                        groups[args[0]].append(pl)
                    print("grupo '%s': %s" % (args[0], ", ".join(q["name"] for q in groups[args[0]])))
            elif cmd == "untag":
                groups.pop(args[0], None); print("ok")
            elif cmd == "groups":
                for g, pls in groups.items(): print("  %s: %s" % (g, ", ".join(q["name"] for q in pls)))
            elif cmd == "cmpbits":  # cmpbits grupo1 grupo2 -> bits que separam (struct, skills, person, status)
                g1, g2 = groups.get(args[0]), groups.get(args[1])
                if not g1 or not g2: print("use 'tag <grupo> <n>' pra montar os dois grupos primeiro")
                else:
                    print("bits que separam '%s' (grupo1) de '%s' (grupo2):" % (args[0], args[1]))
                    print(compare_bits(game, g1, g2))
            elif cmd == "cmpzero":  # cmpzero grupo1 grupo2 -> campos zerados num grupo e preenchidos no outro
                g1, g2 = groups.get(args[0]), groups.get(args[1])
                if not g1 or not g2: print("use 'tag <grupo> <n>' pra montar os dois grupos primeiro")
                else: print(compare_zero(game, g1, g2))
            elif cmd == "cmpconst":  # cmpconst grupo1 grupo2 -> bytes constantes em cada grupo e diferentes entre eles (2 níveis de ponteiros)
                g1, g2 = groups.get(args[0]), groups.get(args[1])
                if not g1 or not g2: print("use 'tag <grupo> <n>' pra montar os dois grupos primeiro")
                else: print(compare_const(game, g1, g2))
            elif cmd == "hdr":  # hdr <n> -> primeiros 24 bytes do bloco de skills + PERSON_DATA
                pl = pick(args[0])
                if pl:
                    r = regions_of(game, pl)
                    print("%s  skills[0:24]=%s" % (pl["name"], r.get("skills", b"")[:24].hex(" ")))
                    print("   person=%s" % r.get("person", b"").hex(" "))
                    print("   player[96:152]=%s" % r["player"][96:152].hex(" "))
            elif cmd == "cmp":
                g1, g2 = groups.get(args[0]), groups.get(args[1])
                if not g1 or not g2: print("use 'tag <grupo> <n>' pra montar os dois grupos primeiro")
                else:
                    print("offsets que separam '%s' (grupo1) de '%s' (grupo2):" % (args[0], args[1]))
                    print(compare_groups(game, g1, g2))
            elif cmd in ("watch", "deepwatch"):
                pl = pick(args[0])
                if pl:
                    if pl["addr"] in watchers: watchers[pl["addr"]].stop.set()
                    watchers[pl["addr"]] = Watcher(proc, game, pl, deep=(cmd == "deepwatch"))
                    print("vigiando %s%s (avance o jogo; 'unwatch %s' para parar)" % (pl["name"], " + objetos apontados" if cmd == "deepwatch" else "", args[0]))
            elif cmd == "unwatch":
                pl = pick(args[0])
                if pl and pl["addr"] in watchers:
                    watchers.pop(pl["addr"]).stop.set(); print("ok")
            elif cmd == "dump":
                pl = pick(args[0])
                if pl: print(annotate(game, game.dump(pl)))
            elif cmd == "snap":
                pl = pick(args[0])
                if pl: snaps[pl["addr"]] = game.dump(pl); print("snapshot guardado")
            elif cmd == "diff":
                pl = pick(args[0])
                if pl:
                    prev = snaps.get(pl["addr"])
                    if prev is None: print("faça 'snap' primeiro")
                    else:
                        cur = game.dump(pl)
                        print(annotate(game, cur, prev))
                        changed = [i for i in range(min(len(cur), len(prev))) if cur[i] != prev[i]]
                        print("bytes alterados:", changed)
            else:
                print("comando desconhecido; 'help'")
        except Exception as e:
            print("erro:", e)


if __name__ == "__main__":
    main()
