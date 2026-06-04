"""
Top 100 popular online competitive/multiplayer games.
Cover art URLs use Steam's CDN (publicly hosted, free to hotlink) for games on Steam.
Non-Steam games (mobile/console exclusives) use image_url=None — frontend shows a placeholder.
"""

# Steam header URL pattern: https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg
def _steam(app_id: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"


TOP_GAMES = [
    # === FPS / SHOOTERS ===
    {"name": "Counter-Strike 2", "platform": "PC", "category": "FPS", "image_url": _steam(730)},
    {"name": "Call of Duty: Modern Warfare III", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": _steam(2519060)},
    {"name": "Call of Duty: Warzone", "platform": "PC, PS5, Xbox Series", "category": "Battle Royale", "image_url": _steam(1962663)},
    {"name": "Apex Legends", "platform": "PC, PS5, Xbox Series, Switch", "category": "Battle Royale", "image_url": _steam(1172470)},
    {"name": "Valorant", "platform": "PC", "category": "FPS", "image_url": None},
    {"name": "Overwatch 2", "platform": "PC, PS5, Xbox Series, Switch", "category": "FPS", "image_url": _steam(2357570)},
    {"name": "Tom Clancy's Rainbow Six Siege", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": _steam(359550)},
    {"name": "PUBG: BATTLEGROUNDS", "platform": "PC, PS5, Xbox Series", "category": "Battle Royale", "image_url": _steam(578080)},
    {"name": "Battlefield 2042", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": _steam(1517290)},
    {"name": "Destiny 2", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": _steam(1085660)},
    {"name": "Halo Infinite", "platform": "PC, Xbox Series", "category": "FPS", "image_url": _steam(1240440)},
    {"name": "The Finals", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": _steam(2073850)},
    {"name": "Escape from Tarkov", "platform": "PC", "category": "FPS", "image_url": None},
    {"name": "Team Fortress 2", "platform": "PC", "category": "FPS", "image_url": _steam(440)},
    {"name": "XDefiant", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": None},
    {"name": "Hunt: Showdown 1896", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": _steam(594650)},
    {"name": "DELTA FORCE", "platform": "PC", "category": "FPS", "image_url": _steam(2507950)},
    {"name": "Marvel Rivals", "platform": "PC, PS5, Xbox Series", "category": "FPS", "image_url": _steam(2767030)},
    {"name": "Fortnite", "platform": "PC, PS5, Xbox Series, Switch, Mobile", "category": "Battle Royale", "image_url": None},

    # === MOBA ===
    {"name": "Dota 2", "platform": "PC", "category": "MOBA", "image_url": _steam(570)},
    {"name": "League of Legends", "platform": "PC", "category": "MOBA", "image_url": None},
    {"name": "SMITE 2", "platform": "PC, PS5, Xbox Series", "category": "MOBA", "image_url": _steam(2437110)},
    {"name": "Pokemon UNITE", "platform": "Switch, Mobile", "category": "MOBA", "image_url": None},

    # === AUTOCHESS / TACTICS ===
    {"name": "Teamfight Tactics", "platform": "PC, Mobile", "category": "Autobattler", "image_url": None},
    {"name": "Marvel Snap", "platform": "PC, Mobile", "category": "Card", "image_url": _steam(1997040)},

    # === SPORTS ===
    {"name": "EA SPORTS FC 25", "platform": "PC, PS5, Xbox Series, Switch", "category": "Sports", "image_url": _steam(2669320)},
    {"name": "NBA 2K25", "platform": "PC, PS5, Xbox Series, Switch", "category": "Sports", "image_url": _steam(3017860)},
    {"name": "EA SPORTS Madden NFL 25", "platform": "PC, PS5, Xbox Series", "category": "Sports", "image_url": _steam(2840770)},
    {"name": "EA SPORTS NHL 25", "platform": "PS5, Xbox Series", "category": "Sports", "image_url": None},
    {"name": "MLB The Show 24", "platform": "PS5, Xbox Series, Switch", "category": "Sports", "image_url": None},
    {"name": "EA SPORTS PGA TOUR", "platform": "PC, PS5, Xbox Series", "category": "Sports", "image_url": _steam(2104450)},
    {"name": "Top Spin 2K25", "platform": "PC, PS5, Xbox Series", "category": "Sports", "image_url": _steam(2932510)},
    {"name": "Rocket League", "platform": "PC, PS5, Xbox Series, Switch", "category": "Sports", "image_url": _steam(252950)},

    # === RACING ===
    {"name": "F1 24", "platform": "PC, PS5, Xbox Series", "category": "Racing", "image_url": _steam(2488620)},
    {"name": "Forza Motorsport", "platform": "PC, Xbox Series", "category": "Racing", "image_url": _steam(2440510)},
    {"name": "Forza Horizon 5", "platform": "PC, Xbox Series", "category": "Racing", "image_url": _steam(1551360)},
    {"name": "Gran Turismo 7", "platform": "PS5", "category": "Racing", "image_url": None},
    {"name": "Mario Kart 8 Deluxe", "platform": "Switch", "category": "Racing", "image_url": None},
    {"name": "iRacing", "platform": "PC", "category": "Racing", "image_url": _steam(266410)},
    {"name": "Assetto Corsa Competizione", "platform": "PC, PS5, Xbox Series", "category": "Racing", "image_url": _steam(805550)},
    {"name": "WRC", "platform": "PC, PS5, Xbox Series", "category": "Racing", "image_url": _steam(2396990)},

    # === FIGHTING ===
    {"name": "Street Fighter 6", "platform": "PC, PS5, Xbox Series", "category": "Fighting", "image_url": _steam(1364780)},
    {"name": "Tekken 8", "platform": "PC, PS5, Xbox Series", "category": "Fighting", "image_url": _steam(1778820)},
    {"name": "Mortal Kombat 1", "platform": "PC, PS5, Xbox Series, Switch", "category": "Fighting", "image_url": _steam(1971870)},
    {"name": "Guilty Gear -Strive-", "platform": "PC, PS5, Xbox Series", "category": "Fighting", "image_url": _steam(1384160)},
    {"name": "Super Smash Bros. Ultimate", "platform": "Switch", "category": "Fighting", "image_url": None},
    {"name": "Dragon Ball FighterZ", "platform": "PC, PS5, Xbox Series, Switch", "category": "Fighting", "image_url": _steam(678950)},
    {"name": "The King of Fighters XV", "platform": "PC, PS5, Xbox Series", "category": "Fighting", "image_url": _steam(1498570)},
    {"name": "MultiVersus", "platform": "PC, PS5, Xbox Series", "category": "Fighting", "image_url": _steam(1818750)},

    # === MMORPG ===
    {"name": "World of Warcraft", "platform": "PC", "category": "MMORPG", "image_url": None},
    {"name": "Final Fantasy XIV Online", "platform": "PC, PS5, Xbox Series", "category": "MMORPG", "image_url": _steam(39210)},
    {"name": "The Elder Scrolls Online", "platform": "PC, PS5, Xbox Series", "category": "MMORPG", "image_url": _steam(306130)},
    {"name": "Lost Ark", "platform": "PC", "category": "MMORPG", "image_url": _steam(1599340)},
    {"name": "Black Desert", "platform": "PC, PS5, Xbox Series", "category": "MMORPG", "image_url": _steam(582660)},
    {"name": "Throne and Liberty", "platform": "PC, PS5, Xbox Series", "category": "MMORPG", "image_url": _steam(2429660)},
    {"name": "Path of Exile 2", "platform": "PC, PS5, Xbox Series", "category": "ARPG", "image_url": _steam(2694490)},
    {"name": "Diablo IV", "platform": "PC, PS5, Xbox Series", "category": "ARPG", "image_url": _steam(2344520)},
    {"name": "Last Epoch", "platform": "PC", "category": "ARPG", "image_url": _steam(899770)},

    # === SURVIVAL / SANDBOX ===
    {"name": "Rust", "platform": "PC, PS5, Xbox Series", "category": "Survival", "image_url": _steam(252490)},
    {"name": "ARK: Survival Ascended", "platform": "PC, PS5, Xbox Series", "category": "Survival", "image_url": _steam(2399830)},
    {"name": "DayZ", "platform": "PC, PS5, Xbox Series", "category": "Survival", "image_url": _steam(221100)},
    {"name": "Minecraft", "platform": "PC, PS5, Xbox Series, Switch, Mobile", "category": "Sandbox", "image_url": None},
    {"name": "Roblox", "platform": "PC, PS5, Xbox Series, Mobile", "category": "Sandbox", "image_url": None},
    {"name": "Palworld", "platform": "PC, PS5, Xbox Series", "category": "Survival", "image_url": _steam(1623730)},
    {"name": "Valheim", "platform": "PC, PS5, Xbox Series", "category": "Survival", "image_url": _steam(892970)},
    {"name": "Terraria", "platform": "PC, PS5, Xbox Series, Switch, Mobile", "category": "Sandbox", "image_url": _steam(105600)},
    {"name": "7 Days to Die", "platform": "PC, PS5, Xbox Series", "category": "Survival", "image_url": _steam(251570)},
    {"name": "Enshrouded", "platform": "PC", "category": "Survival", "image_url": _steam(1203620)},
    {"name": "Nightingale", "platform": "PC", "category": "Survival", "image_url": _steam(1928980)},

    # === CO-OP / EXTRACTION ===
    {"name": "Helldivers 2", "platform": "PC, PS5", "category": "Co-op", "image_url": _steam(553850)},
    {"name": "Lethal Company", "platform": "PC", "category": "Co-op", "image_url": _steam(1966720)},
    {"name": "Deep Rock Galactic", "platform": "PC, PS5, Xbox Series", "category": "Co-op", "image_url": _steam(548430)},
    {"name": "Warframe", "platform": "PC, PS5, Xbox Series, Switch", "category": "Co-op", "image_url": _steam(230410)},
    {"name": "Risk of Rain 2", "platform": "PC, PS5, Xbox Series, Switch", "category": "Co-op", "image_url": _steam(632360)},
    {"name": "Phasmophobia", "platform": "PC, PS5, Xbox Series", "category": "Co-op", "image_url": _steam(739630)},
    {"name": "Dead by Daylight", "platform": "PC, PS5, Xbox Series, Switch, Mobile", "category": "Co-op", "image_url": _steam(381210)},
    {"name": "Sea of Thieves", "platform": "PC, PS5, Xbox Series", "category": "Co-op", "image_url": _steam(1172620)},
    {"name": "GTFO", "platform": "PC", "category": "Co-op", "image_url": _steam(493520)},

    # === STRATEGY / RTS ===
    {"name": "Age of Empires IV", "platform": "PC, Xbox Series", "category": "Strategy", "image_url": _steam(1466860)},
    {"name": "StarCraft II", "platform": "PC", "category": "Strategy", "image_url": None},
    {"name": "Sid Meier's Civilization VI", "platform": "PC, PS5, Xbox Series, Switch, Mobile", "category": "Strategy", "image_url": _steam(289070)},
    {"name": "Total War: WARHAMMER III", "platform": "PC", "category": "Strategy", "image_url": _steam(1142710)},
    {"name": "Stormgate", "platform": "PC", "category": "Strategy", "image_url": _steam(2012510)},
    {"name": "Company of Heroes 3", "platform": "PC, PS5, Xbox Series", "category": "Strategy", "image_url": _steam(1677280)},

    # === CARD / DIGITAL TCG ===
    {"name": "Hearthstone", "platform": "PC, Mobile", "category": "Card", "image_url": None},
    {"name": "MTG Arena", "platform": "PC, Mobile", "category": "Card", "image_url": _steam(2141910)},
    {"name": "Pokemon TCG Live", "platform": "PC, Mobile", "category": "Card", "image_url": None},
    {"name": "Yu-Gi-Oh! Master Duel", "platform": "PC, PS5, Xbox Series, Switch, Mobile", "category": "Card", "image_url": _steam(1449850)},

    # === PARTY / CASUAL ===
    {"name": "Among Us", "platform": "PC, PS5, Xbox Series, Switch, Mobile", "category": "Party", "image_url": _steam(945360)},
    {"name": "Fall Guys", "platform": "PC, PS5, Xbox Series, Switch", "category": "Party", "image_url": _steam(1097150)},
    {"name": "Stumble Guys", "platform": "PC, Mobile", "category": "Party", "image_url": _steam(1677740)},
    {"name": "Gang Beasts", "platform": "PC, PS5, Xbox Series, Switch", "category": "Party", "image_url": _steam(285900)},
    {"name": "Golf With Your Friends", "platform": "PC, PS5, Xbox Series, Switch", "category": "Party", "image_url": _steam(431240)},
    {"name": "Pummel Party", "platform": "PC", "category": "Party", "image_url": _steam(880940)},

    # === MILITARY SIM / TACTICAL ===
    {"name": "Arma 3", "platform": "PC", "category": "Tactical", "image_url": _steam(107410)},
    {"name": "Arma Reforger", "platform": "PC, PS5, Xbox Series", "category": "Tactical", "image_url": _steam(1874880)},
    {"name": "Squad", "platform": "PC", "category": "Tactical", "image_url": _steam(393380)},
    {"name": "World of Tanks", "platform": "PC, PS5, Xbox Series", "category": "Vehicles", "image_url": None},
    {"name": "War Thunder", "platform": "PC, PS5, Xbox Series", "category": "Vehicles", "image_url": _steam(236390)},
    {"name": "World of Warships", "platform": "PC", "category": "Vehicles", "image_url": None},
]
