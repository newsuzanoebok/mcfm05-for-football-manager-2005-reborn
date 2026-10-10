MCFM05 Reborn v1.0 FINAL — real-time editor for Football Manager 2005
==========================================================

WHAT IT IS
  Edits the game WHILE it is running (memory), without touching the save files.
  Nothing is changed until you click "Save to game". Save your game before editing.

REQUIREMENTS
  - Windows (tested on Windows 10/11, 64-bit).
  - Football Manager 2005 version 5.0.2 (shows "5.0.2" on the start screen), no-CD/"win10fix" build.
    It was mapped on that version; on another version (5.0.0, 5.0.5) many things may not work.
  - Python 3 (3.8 or newer), 32 or 64-bit, with Tkinter (included by default in the python.org installer).
    Install from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  - Administrator rights (the program asks for them when it opens).

HOW TO USE
  1. Unzip the folder anywhere (e.g. D:\Apps\MCFM05Reborn).
  2. Open FM 2005 and load your save.
  3. Double-click "MCFM05 Reborn.bat" (accept the administrator prompt).
  4. Click "Load from game". Edit, then "Save to game".
  Language: top-right corner (English by default; Portuguese and Spanish). Restart the program after changing it.

FILES THE PROGRAM CREATES IN ITS OWN FOLDER
  config.json (language), janela.json (window size), favoritos.json, congelados.json, attribute backup, erro.log.

COMMON PROBLEMS
  - "fm2005.exe is not running": open the game and load a save before "Load from game".
  - Nothing happens when opening the .bat: Python not installed or not added to PATH. Test in cmd: python --version
  - The window does not open and there is an erro.log in the folder: send erro.log to the maintainer.
  - 255 in 0-20 fields corrupts the game: with "no limits" go only up to 127.
  - After ticking "retired from international football" or a transfer that warned "list reallocated":
    save the game and reload the save before playing on.

OFFICIAL VERSION
  Created by g0ldenboy & Claude AI. The "created by..." button shows the version and the SHA-256 fingerprint of the files;
  compare it with the one published by the author. Any modified copy is not the official one.

DISCLAIMER
  Use at your own risk. Keep a copy of your save before editing.
