# FM2005 — mapa de memória (extraído do MCFM05 / mcfm.exe, dez/2004)

Processo: `fm2005.exe`, base `0x400000`, 32-bit. Todos os offsets em bytes decimais.

## Detecção de versão
`int32` em `0x400000 + 0xF4`:

| valor | versão | id interno |
|---|---|---|
| 782425187 (0x2EA2DC63) | 5.0.0 Demo "Strawberry" | 0 |
| 788935750 (0x2F063446) | 5.0.0 Retail | 2 |
| 1192244486 (0x47103506) | 5.0.2 Retail | 4 |

## Como os objetos são encontrados
Todo objeto do jogo é uma classe C++ cujos 8 primeiros bytes são **duas vtables**
(ponteiros para dentro do .exe). O MCFM05 varre a memória inteira do processo e
reconhece cada tipo pelo par de vtables. Assinaturas (little-endian, 2 dwords por tipo,
ordem: city, player, playercoach, coach, team, country):

| versão | city | player | playercoach | coach | team | country |
|---|---|---|---|---|---|---|
| 5.0.0 demo | 00C5339C 00C53388 | 00E46D94 00E46FDC | 00E5724C 00E574A0 | 00E4E84C 00E4E98C | 00E40AB4 00E40AA4 | 00E420FC 00E420E8 |
| 5.0.0 retail | 00CAB55C 00CAB54C | 00E551C4 00E5540C | 00E63C24 00E63E78 | 00E61A6C 00E61B94 | 00E53C0C 00E53BFC | 00E557A4 00E55790 |
| 5.0.2 retail | 00C892B4 00C892A0 | 00E9DB8C 00E9DDD4 | 00EAE02C 00EAE280 | 00EA560C 00EA5750 | 00E97954 00E97944 | 00E98F94 00E98F80 |
| 5.0.2 (alt) | 00C892B4 00C892A0 | 00E9DB94 00E9DDDC | 00EAE024 00EAE278 | 00EA5614 00EA5754 | 00E9795C 00E9794C | 00E98F9C 00E98F88 |

Depois de achar um jogador, o MCFM05 pula 256 bytes (player), 304 (playercoach), 32 (city).

## Player (e PlayerCoach)
| offset | tipo | campo | obs |
|---|---|---|---|
| 0 | ptr | vtable 0 | |
| 4 | ptr | vtable 1 | |
| 8 | int16 | **Condição** | 0..10000 (÷100 = %) |
| 20 | int16 | CA | |
| 22 | int16 | PA | |
| 152 | ptr | → bloco de atributos | **156 na 5.0.2** (único offset que muda: tudo entre 141 e 159 ganha +4) |
| 204 | int32 | Id | PlayerCoach: 268 |
| 228 | ptr³ | Nome | PlayerCoach: 292 |
| 232 | ptr³ | Sobrenome | PlayerCoach: 296 |
| 236 | ptr³ | Apelido | PlayerCoach: 300 |
| 244 | date | Nascimento | PlayerCoach: 308 |
| 248 | ptr | Cidade natal | PlayerCoach: 312 |
| 256 | ptr | Nacionalidade | PlayerCoach: 320 |
| 264 / 265 | u8 | Jogos seleção / sub-21 | PlayerCoach: 328 / 329 |
| 266 / 267 | u8 | Gols seleção / sub-21 | PlayerCoach: 330 / 331 |
| 312 | ptr² | Contrato | PlayerCoach: 376 (ver abaixo) |

**Não mapeado (a descobrir): lesão, suspensão, moral.** Candidatos: bytes 10–19, 23,
103–151, 156–227, 240–243, 252–255, 260–263, 268–311.

### Strings (ptr³)
`p1 = *(addr)`; `p2 = *(p1+28)`; `p3 = *(p2+8)`; em `p3` há UTF-16LE terminado em 0 (≤48 chars).

### Datas (4 bytes)
`[ano_lo][ano_hi]` byte-swapped + `[dia_lo][dia_hi]` byte-swapped, dia = dia-do-ano − 1.
Ou seja: ano = swap16(bytes 0-1), dia0 = swap16(bytes 2-3).

### Contrato (ptr²)
`c = *(player+312)`; só válido se `*(uint8*)(player+316) == 1`; depois `c = *c`.
| offset | tipo | campo |
|---|---|---|
| 16 | int32 | Salário |
| 24 | date | Início |
| 32 | date | Fim |
| 72 / 76 / 80 / 84 | int32 | Bônus por jogo / gol / assistência / clean sheet |

## Bloco de atributos (apontado por player+152/156) — todos `sbyte` 1..20
**Posições** 24 GK · 25 SW · 26 D · 27 DM · 28 M · 29 AM · 30 ST · 31 WB · 32 FreeRole · 33 R · 34 C · 35 L ·
36–48 posições "novas" (DL, DC, DR, DMC, ML, MC, MR, AML, AMC, AMR, STC, WBL, WBR)

**Atributos** 49 Crossing · 50 Dribbling · 51 Finishing · 52 Heading · 53 LongShots · 54 Marking ·
55 OffTheBall · 56 Passing · 57 PenaltyTaking · 58 Tackling · 59 Creativity · 60 Handling ·
61 AerialAbility · 62 CommandOfArea · 63 Communication · 64 Kicking · 65 Throwing ·
66 Anticipation · 67 Decisions · 68 OneOnOnes · 69 Positioning · 70 Reflexes · 71 FirstTouch ·
72 Technique · 73 LeftFoot · 74 RightFoot · 75 Flair · 76 Corners · 77 Teamwork · 78 Workrate ·
79 LongThrows · 80 Eccentricity · 81 RushingOut · 82 TendencyToPunch · 83 Acceleration ·
84 Freekicks · 85 Strength · 86 Stamina · 87 Pace · 88 Jumping · 89 Influence · 90 Dirtiness ·
91 Balance · 92 Bravery · 93 Consistency · 94 Aggression · 95 Agility · 96 ImportantMatches ·
97 InjuryProneness · 98 Versatility · 99 NaturalFitness · 100 Determination · 101 Composure ·
102 Concentration

## Coach
Id 76 · CCA 14 (int16) · PCA 16 (int16) · skills ptr 152 · contrato 184 · nome 100/104/108 ·
nascimento 116 · cidade 120 · nacionalidade 128 · caps/gols 136–139

## Team / Club / Finanças
Team: Id 16 · Type 48 · ClubPtr 44
Club: Status 167 (u8) · TrainingGround 168 (u8) · Público médio/mín/máx 172/176/180 (int32) ·
KitPtr 64 · FinancePtr 212 · SponsorPtr 216
Finanças (via FinancePtr): Saldo 4 · Orçamento transf. temporada 16 · Restante 20 ·
Receita de vendas disponível 24 · Orçamento salarial 116

---
# Descobertas da sessão de 08/10/2026 (com RTTI do fm2005.exe)

## Correções ao mapa do MCFM05
- **Struct do jogador = classe `ACTUAL_PLAYER`, 412 bytes** (em +412 começa o próximo). Sub-objetos (vtables) em +188, +192, +196, +200, +220.
- **Datas**: 8 bytes = vtable `SI_SHORT_DATE` (00C4D3B4) + `u16 dia-do-ano (0 = 1/jan)` + `u16 ano`, little-endian. Ex.: `b4 d3 c4 00 d7 00 d5 07` = 04/08/2005.
- **Ponteiro de skills (+152) → `PLAYING_DATA`** (108 bytes: 3 vtables, vtable, -1, id, 25 posições, 54 atributos, 5 bytes).
- **Atributos têm duas escalas**: os "finos" (Crossing, Dribbling, Finishing, Heading, LongShots, Marking, OffTheBall, Passing, Tackling, Creativity, os 6 de goleiro, Anticipation, Decisions, OneOnOnes, Positioning, Reflexes, FirstTouch, Technique, Composure, Concentration) são sbyte com exibição `floor((raw+99)/8)` limitada a 1..20 (127 → "28", sobre-humano). Os demais são 1..20 diretos. Em qualquer um, 127 bruto = efeito extremo.
- **Arrays `ARRAY<T*, D>`**: `{vtable, ponteiro p/ dados, contagem}` — o `D` do RTTI = contagem em **1 byte** (`F` = 2 bytes, `J` = 4). Ex.: contratos em +308 (`DEL_ARRAY<CONTRACT*,D>`: dados +312, contagem +316 — por isso o MCFM testava `byte == 1`).
- Padding: bytes "lixo" repetidos por struct (ex.: `00 f4 55 00`) — não são campos.

## Campos novos na struct do jogador
| offset | tipo | campo | obs |
|---|---|---|---|
| +10 | u16 | ~"ritmo/sharpness"? 0..10000 | cai enquanto lesionado |
| +12 | int16 | negativo, cai ~10/dia fora, sobe ao treinar/jogar | não é lesão |
| +14 / +16 | int16 | 0..10000 (par quase igual) | provável jadedness/forma |
| +28 | int32 | valor de mercado | |
| **+40** | **u16** | **Moral, 1..20** (20 = Excelente) | **confirmado em jogo** |
| **+44** | **ptr** | **objeto de status** (ver abaixo) | |
| +48 | ptr | `PLAYER_FORM` (lista de `PLAYER_TEAM_FORM`) | não é lesão |
| +60 | ptr | registros de desempenho (48 bytes cada) | |
| +64 / +364 | ptr | `CLUB` do jogador | |
| +76 | u32 | número da semana (sobe 1 a cada ~7 dias) | |
| +80, +96 | obj | `TRAINING_CATEGORIES` embutidos (16 bytes cada) | |
| +112 | obj | `POSITION_MASK` embutido | |
| +168 | obj | `DEL_ARRAY<PLAYER_BOOKING_COUNT*,D>` (dados +172, cont. +176) | |
| +204 | int32 | Id | |
| +208 | int32 | id do clube? | igual em `+60`-registros |
| +292, +304 | date | entrada no clube etc. | |
| +308 | obj | `DEL_ARRAY<CONTRACT*,D>` (dados +312, cont. +316) | |
| +340 | obj | `STEP_ARRAY<CLUB*,F>` (dados +344) | |
| +392 | obj | `NICK_NAME_ARRAY` | |

## Objeto de status (player+44)
```
+0   ptr
+4   vtable DEL_ARRAY<PLAYER_INJURY*,D>   +8  dados   +12 contagem (byte)
+16  vtable DEL_ARRAY<PLAYER_BAN*,D>      +20 dados   +24 contagem (byte)
```
### PLAYER_INJURY (vtable 00E1FD54), 88 bytes
| offset | tipo | campo |
|---|---|---|
| +8 | ptr | tipo de lesão (`INJURY`, registro do DB) |
| +12 | obj | `SHORT_FIXTURE` embutido (jogo em que aconteceu) |
| +72 | date | **início** (8 bytes, vtable + data) |
| +80 | u16 | **duração mínima (dias)** |
| +82 | u16 | **duração máxima (dias)** — o jogo mostra `(max − decorridos)` em semanas |
| +84 | u16 | status (2 = ativa) |
**Curar**: zerar +80 e +82 → o jogo encerra a lesão no dia seguinte (testado). Alternativa: contagem da lista = 0.

### PLAYER_BAN (vtable 00E5AE84)
| offset | tipo | campo |
|---|---|---|
| +4 | u8 | tipo (0x0B, 0x0C, 0x0D…) |
| +12 | int32 | jogos (1, 2…) — zerar **não** basta |
| +16 | date | data (pode ser nula) |
| +24 | int32 | competição (189 = liga principal, 5 = outra) |
**Remover suspensão**: contagem da lista (status+24) = 0 → efeito imediato (testado).

## Classes úteis (vtables, build do usuário)
ACTUAL_PLAYER 00E551C4 · PLAYING_DATA 00E3588C(+12) · PLAYER_INJURY 00E1FD54 · PLAYER_BAN 00E5AE84 ·
INJURY_MANAGER 00E204C4 · PLAYER_BAN_LIST 00CAE244 · PS_INJURY_LIST 00CAE210 · SI_DATE 00C80B70 ·
SI_SHORT_DATE 00C4D3B4 · PLAYER_FORM 00E54EDC · PLAYER_TEAM_FORM 00CAE1DC · CLUB 00E54D04 ·
FIXTURE 00E1FAB4 · PLAYER_STATS 00E66948 · MORALE_MANAGER 00E258A8. O mapa completo (7153 vtables)
pode ser regenerado do exe pelo RTTI (`.?AV…@@` → COL → vtable).

---
# Clubes, times, países e finanças (09/10/2026)

## Como achar
- `TEAM` (vtable 00E53C0C): `+16` id, `+44` → `CLUB`, `+48` tipo (0 = principal), **`+92` int32 = reputação 0–10000 (confirmado: 10000 → "Mundial")**, `+204` outro valor 0–10000 (Real Madrid 10000; não é o rótulo).
- `CLUB` (vtable 00E54D04, ~340 bytes): nome em `*(*(club+32)+8)` (UTF-16); `+16` id; `+160` → `NATION`; **`+164` academia (youth academy) e `+165` recrutamento/jovens (youth) 1–20** (confirmado com o editor oficial: Santos 17/18/19 = treino/academia/jovens); **`+167` status (1 prof/2 semi/3 amador); `+168` instalações de treino 0–20** (0–7 Awful, 8–9 Need major investment, 10–12 Need some investment, 13–15 Adequate, 16–20 Top facilities plus youth academy); `+172/176/180` público médio/mín/máx (int32); `+212` → finanças.
- Não existem no FM 2005 os campos separados *Junior Coaching*, *Youth Recruitment* e *Youth Facilities*: só a escala única de instalações acima.
- Finanças: clubes jogáveis têm `CLUB_FINANCE` (vtable 00E546EC): `+4` saldo, `+16` orçamento de transferências da temporada, `+20` restante, `+116` orçamento salarial/semana, `+124` salários usados/semana. Clubes não jogáveis têm `CLUB_FINANCE_BASE` (só `+4` saldo). **O jogo mostra os valores ×1,5** (moeda interna → euros).
- `NATION` (vtable 00E557A4): nome em `*(*(nation+32)+8)`; `+16` id; `+108..+123` 16 bytes 1–20 (provável tática padrão); `+175`/`+177` bytes 1–20 (Espanha 20/18, Brasil 14/15 — candidatos a fator econômico / poder financeiro); **`+196` u16 (Espanha 8000, Brasil 9550 — provável reputação)**; `+204..+220` contagens do DB; `+300` float (1.0 / 0.25); `+380..+620` 12 registros de 20 bytes `{ptr, int, int, valor 0–10000}`. A tela do jogo não mostra reputação de país, então estes não foram verificados.

## Data do jogo
- `SI_DATE` global em **`0x01017028`**: `{vtable 00C80B70, u16 dia-do-ano (0 = 1/jan), u16 ano, u8 flag}` = data atual (confirmado: 03/09/2005). Em `0x01017034` outra `SI_DATE` = data de início do save. (Função que a lê: fm2005.exe @00658CC0.)
- `SI_DATE` = 12 bytes `{vtable, +4 dia u16, +6 ano u16, +8 byte}`; `SI_SHORT_DATE` = 8 bytes `{vtable 00C4D3B4, +4 dia u16, +6 ano u16}`.
- Reputação do clube: **`TEAM+92` é u16** (2 bytes); `+94` é outro campo.

## Personalidade
- `player+360` → `PERSON_DATA` (32 bytes: 4 vtables `00E2FD14/00E2FD00/00E2FCD4/00E2FCC4`, -1, id sequencial, **8 bytes 1–20 em +24..+31**). Ordem **confirmada** contra o editor oficial (Casillas): +24 Adaptability, +25 Ambition, +26 Loyalty, +27 Pressure, +28 Professionalism, +29 Sportsmanship, +30 Temperament, +31 Controversy.

## Campos de país (confirmados com o editor oficial, 09/10/2026)
- `NATION+172` u8 estado de desenvolvimento (1 desenvolvido, 2 em desenvolvimento, 3 subdesenvolvido); `+174` u8 importância do jogo 0–20; `+175` u8 nível da liga 0–20; `+177` u8 fator econômico 0–20; `+196` u16 reputação 0–10000. Alemanha 1/1(dev)/19/17 e Argélia 3/2/13/9 conferem.

## Competições (em andamento)
- `COMP` vtable 00C895BC; nome em `*(*(comp+32)+8)`. Reputação 0–20 do editor oficial ainda não localizada — usar `comps <texto>`, `comp N`, `cmpcomp N M` no CLI.
- **Atualização:** `COMP` é a classe-mãe; cada competição tem o vtable da sua classe derivada (340 classes: `ACTUAL_COMP`, `BRA_CUP`, `ENG_FA_CUP`…). No save do usuário os registros são `COMP` puro, 104 bytes cada, contíguos. Layout: `+16` id, `+32` ARRAY (nome via `*(*(comp+36)+8)`), `+72` → `NATION`, `+80/+84/+88` cores RGBA, `+92` int, **`+96` int32 = reputação 0–20 (Série A 15, Rio 13, SP 14, Copa do Brasil 14)**, `+100` int.

## Posições (bloco de skills)
- `+24..+35` posições clássicas 1–20 (GK, líbero, defesa, MD, médio, MO, atacante, ala, ação livre, direita, centro, esquerda).
- `+36..+48` 13 bytes — hipótese: "novas posições" do editor (DL, DC, DR, DMC, ML, MC, MR, AML, AMC, AMR, ST, WBL, WBR). **A confirmar.**
- Nascimento `player+244` (u16 dia-do-ano + u16 ano); nacionalidade `player+256` → NATION. Condição `player+8` i16 0–10000.

## Afastado do futebol internacional (resolvido via desmontagem do fm2005.exe)
- Não é um campo do jogador: é um item na lista `player+364` → `ARRAY<RELATIONSHIP,D>` = `{vtable 00E4CCAC, data, count u8}`, itens **em linha de 12 bytes**: `{tipo u8, valor u8 (100), u16, ptr (clube/país/pessoa), kind u8 (1 clube / 2 país / 3 pessoa), 3 bytes lixo}`.
- Tipos vistos: 1 ?, 3 = clube por onde passou, 9 = país (?), **10 = afastado do futebol internacional**, 69 ?, 80/81 = avisos ("Withdrawn From Squad"), 97/98 = clube/país favorito ou rival.
- O código em `004CCEF0` (servidor) percorre a lista e manda o tipo 10/80/81 ao cliente (`+0x5b4` da struct de cliente); `00772980` escolhe o texto.
- Remover: desloca os itens e decrementa count. Adicionar: novo buffer via VirtualAllocEx (salvar e recarregar o save depois).

## Movimentos preferidos
- `player+160` u64, um bit por movimento (função virtual ACTUAL_PLAYER +0x23C lê `[this+0xA0]`/`[+0xA4]`). Os 48 bits foram extraídos do `fm_data_editor.exe` (função em `004BA520` registra cada caixa com sua máscara de 64 bits) e os nomes em português do `portuguese.ltf` (KEY/STR-0). Bits 48–63 não usados.

## Contratos (confirmado com foto do save, Vergassola / Krshiev)
- contratos do jogador: array embutido em `player+308` (dados `+312`, contagem u8 `+316`) — **não** é ponteiro para um objeto ARRAY (bug corrigido na v39); staff: array em linha em `ACTUAL_NON_PLAYER+180`. `FULL_CONTRACT` (vtable 00CB33A4, 108 bytes): `+4` → PERSON (player+188 / staff+60), `+8` → CLUB, `+16` salário/semana interno (jogo mostra ×1,5 arredondado), `+24` início, `+32` fim (u16 dia, u16 ano), `+88` STEP_ARRAY<CONTRACT_CLAUSE>.
- `ACTUAL_NON_PLAYER` (284 bytes): `+52` → `NON_PLAYING_DATA` (atributos em `+24..`), `+60` = subobjeto PERSON (nascimento +116, PERSON_DATA via +232), `+156` → TEAM, `+180` array de contratos.
- `TEAM+212` ARRAY<TEAM_COMP_STATS_LINK> (`+216` dados, itens 8 bytes: comp, stats). Stats: `+9` posição (0 = 1º), `+11` jogos, `+20..` forma recente, mais novo primeiro (3 V, 2 E, 0 D). V/E/D/gols/pontos **não** são guardados: calculados dos RESULT (conferido: tabela recalculada dos 348 jogos da Série A 06/07 bate com as posições guardadas).
- RESULT (vtable 00E1F1E4, 136 bytes): placar em +124 (casa) / +130 (fora). Edição de tabela foi descartada (decisão do usuário).
- Atributos de treino (NON_PLAYING_DATA +24..+57), ordem tirada do editor (`fm_data_editor.exe` 004AAA95 → setters) e confirmada com Ancelotti/Capello: 24 attk, 25 buss, 26 tchq, 27 drct, 28 dcpl, 29 free, 30 intr, 31 mark, 32 offs, 33 patn, 34 prss, 35 rsrs, 36 yung, 37 detr, 38 buyg, 39 mind, 40 sitg, 41 uply, 42 subs, 43 dept, 44 flam, 45 flex, 46 hatr, 47 sqro, 48 temp, 49 widt; **escala fina** `round((bruto+85)/5)`: 50 cchg, 51 chgk, 52 judg, 53 potn, 54 manh, 55 motv, 56 phys, 57 tcts. Staff +14/+16 = CA/PA (u16).
- Treinador humano (HUMAN_NON_PLAYER 00E56F24, 716 bytes): PERSON +492, nação +560, nascimento +548, TEAM +588, PERSON_DATA +664. CLUB_MANAGER_DETAILS (00E207A4): +20 TEAM, +24/+48 CLUB_CONFIDENCE {vt, u16 valor, i16 tendência,…} (diretoria/torcida — hipótese).
- **Elenco / transferência** (foto do save, Siena 29 jogadores): `TEAM+112` STEP_ARRAY<PLAYER*,F,4> {vt 00E53A2C, `+116` dados, `+120` contagem (u32), `+124` capacidade (u32; o buffer guarda ponteiros velhos além da contagem)}. `player+284` → TEAM atual. `TEAM+248/+272` → outros TEAMs (adversários), não reservas. `player+208` = índice do jogador (não é clube). Transferir = tirar da lista antiga, pôr na nova (dentro da capacidade, senão realocar), `player+284` = TEAM novo, FULL_CONTRACT+8 = CLUB novo. A lista do TEAM é dos jogadores que o clube POSSUI: emprestados (Barnetta, Freier) ficam na lista do clube dono e têm `+284` = time que os recebe + um LOAN_CONTRACT (vt 00E345E4) na lista de contratos. A tela 'Emprestado ao X' (função 0077C95B) compara o clube do time de `+284` com o clube do contrato: se o contrato não for atualizado, o jogo mostra o jogador como emprestado.
- **Confiança (confirmado no exe)**: CLUB_MANAGER_DETAILS (00E207A4, 96 bytes): `+20` TEAM, `+24` CLUB_CONFIDENCE diretoria {vt, `+28` u16 valor, `+30` i16 tendência}, `+48` torcida (`+52` valor). Construtor põe 5000; ao assumir um clube vira 7250 (0042D865); atualização pós-jogo/posição em 0042C4xx (faixa 4275..6500, deltas −50/−75, +/−). Decisão de demissão (0042D145): só avalia se `+14` (byte) = 0, `+28` ≤ 4275 **e** dias no cargo ≥ 180 (vfunc +0x230 do contrato); em 0042D451 há limiar extra de 3000. Os textos da tela de confiança (MTAC_*) vêm de outros critérios (reputação, finanças, folha, expectativa), não deste número.
- **Aposentadoria anunciada (RET)**: bit 0 do byte `player+212` (bits 1/3/6 = outras flags, não mexer). Foto 10/12/2007: todos os 6 jogadores com RET informados têm o bit; no resto do banco só jogadores de 31+ anos (pico nascidos 1973). `player+144` SI_SHORT_DATE = data planejada ('Plans to retire on'); nula = fim da temporada. A tela do perfil (0077A240) mostra 'Retiring at the end of the season' quando a data é nula.
- **Aposentadoria (de verdade, v48)**: REGENERATION_MANAGER global em 0x010141D0: `+0x0C` e `+0x1C` DEL_STEP_ARRAY<RETIREMENT*> {dados +4, cont. u32 +8, cap. +12} — RETIREMENT (24 B, sem vtable): `+0` índice da pessoa (player+208), `+4` id do clube (TEAM+16), `+0x10` SI_SHORT_DATE, `+0x14` data; 006B8BA0 executa (006B68E0) quando a data chega. Versão anterior da nota: só o bit de `player+212` não basta (Henriksen aposentou mesmo assim). O jogo guarda as decisões no `REGENERATION_MANAGER` (vt 00E30184, 1 objeto): `+0x3C` STEP_ARRAY<RETIREMENT_CONSIDERATION*> (dados +0x40, cont. u16 +0x44) = pensando; `+0x4C` STEP_ARRAY<RETIREMENT*> (dados +0x50, cont. u16 +0x54, cap. +0x58) = decidido (função 006B63F0 move da 1ª para a 2ª quando chega a data e cria a notícia). Item (vt 00E2FC60, 24 B): `+4` índice da pessoa na tabela global [0x1016F70] = `player+208` (Ovchinnikov 123 confere), `+8` SI_SHORT_DATE, `+12` data. Cancelar = tirar dos dois arrays + limpar o bit; marcar = criar item e pôr em +0x4C.
- **Jogador-treinador** (ACTUAL_PLAYER_AND_NON_PLAYER, vt 00E63C24, 476 B; 53 no save): a varredura por assinatura não os achava (Otto Konrad, Onofrio Barone, Musarra). Mesma struct do ACTUAL_PLAYER até +187; a parte PERSON começa em +252 em vez de +188 (nascimento +308, nacionalidade +320, TEAM +348, contratos +372/+376, PERSON_DATA +424, relações +428). No código: `pl['pd']=64` e `poff(pl, off)`.

