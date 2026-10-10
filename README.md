# MCFM05 Reborn — v1.0 FINAL

Real-time memory editor for **Football Manager 2005** (v5.0.2), inspired by the classic MCFM05.
Created by **g0ldenboy & Claude AI**.

[Português: LEIA-ME.txt](LEIA-ME.txt) · [English: README.txt](README.txt) · [Español: LEEME.txt](LEEME.txt)

## Features
- **Players**: condition, morale, CA/PA, all attributes (incl. hidden ones, personality, positions, new positions), preferred moves, date of birth, nationality, contract (club, wage, dates), heal injuries, remove suspensions, "retired from international football", transfer to another club, cancel announced retirement (RET).
- **Clubs**: reputation, status, training/academy/youth facilities, attendance, finances; **nations**: reputation, importance, development, economy, league level (continent filter); **competitions**: reputation (type/level filter); **staff**: 34 coaching attributes, CA/PA, contract, personality; **human managers**: contract, board/fans confidence, quick "will / will not be sacked" buttons.
- **Mass edit** for players, clubs, nations, competitions and staff; **favourites**; **freezes** (keep a value fixed while the game runs, saved between sessions); **retirements** tab.
- Interface in English (default), Portuguese and Spanish. Auto-refreshing game date.

## Requirements
- Windows, FM 2005 **v5.0.2** (no-CD/"win10fix" build — other versions may not work).
- **Python 3.8+** from https://www.python.org/downloads/ with "Add python.exe to PATH" ticked (Tkinter is included).
- Administrator rights (asked automatically).

## How to use
1. Download the latest release zip and unzip it anywhere.
2. Open FM 2005 and load your save. **Save your game first.**
3. Double-click `MCFM05 Reborn.bat` → "Load from game" → edit → "Save to game".

## Is this the official copy?
Click the **created by…** button (bottom-right). It shows the version and the **SHA-256 fingerprint** of the program files.
Compare it with the fingerprint published in the Releases page. If it does not match, the copy was modified and is not the official one.

## Safety notes
- Never use 255 in 0-20 fields ("no limits" goes up to 127 for a reason).
- After ticking "retired from international football" or a transfer that warned "list reallocated": save the game and reload the save.
- Setting a retirement is not supported (it corrupts the save); cancelling is.
- Use at your own risk; keep a backup of your save.

## Technical notes
`OFFSETS.md` documents every memory offset found (player, club, nation, competition, staff, manager, retirement lists…).
