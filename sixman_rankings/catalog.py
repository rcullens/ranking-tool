"""UIL 1A six-man school directory, adapted from rcullens/sixmanmadness catalog.ts.

Only the public UIL 1A Division I and Division II field is published here.
District / region numbers follow the 2026–28 UIL alignment (Aquilla = I / R4 / Dist 14).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# name, mascot, city, division (I|II), uil_region (1-4), district (1-16)
UIL_ROWS: list[tuple[str, str, str, str, int, int]] = [
    # ——— UIL 1A Division I ———
    ("Boys Ranch", "Roughriders", "Boys Ranch", "I", 1, 1),
    ("Booker", "Kiowas", "Booker", "I", 1, 1),
    ("Claude", "Mustangs", "Claude", "I", 1, 1),
    ("White Deer", "Bucks", "White Deer", "I", 1, 1),
    ("Wildorado", "Mustangs", "Wildorado", "I", 1, 1),
    ("Springlake-Earth", "Wolverines", "Earth", "I", 1, 2),
    ("Nazareth", "Swifts", "Nazareth", "I", 1, 2),
    ("Whiteface", "Antelopes", "Whiteface", "I", 1, 2),
    ("Whitharral", "Panthers", "Whitharral", "I", 1, 2),
    ("Happy", "Cowboys", "Happy", "I", 1, 3),
    ("Kress", "Kangaroos", "Kress", "I", 1, 3),
    ("Petersburg", "Buffaloes", "Petersburg", "I", 1, 3),
    ("Silverton", "Owls", "Silverton", "I", 1, 3),
    ("Aspermont", "Hornets", "Aspermont", "I", 1, 4),
    ("Hermleigh", "Cardinals", "Hermleigh", "I", 1, 4),
    ("Jayton", "Jaybirds", "Jayton", "I", 1, 4),
    ("Roby", "Lions", "Roby", "I", 1, 4),
    ("Rotan", "Yellowhammers", "Rotan", "I", 1, 4),
    ("Spur", "Bulldogs", "Spur", "I", 1, 4),
    ("Sands", "Mustangs", "Ackerly", "I", 2, 5),
    ("Borden County", "Coyotes", "Gail", "I", 2, 5),
    ("Ira", "Bulldogs", "Ira", "I", 2, 5),
    ("Klondike", "Cougars", "Lamesa", "I", 2, 5),
    ("O'Donnell", "Eagles", "O'Donnell", "I", 2, 5),
    ("Westbrook", "Wildcats", "Westbrook", "I", 2, 5),
    ("Fort Hancock", "Mustangs", "Fort Hancock", "I", 2, 6),
    ("Garden City", "Bearkats", "Garden City", "I", 2, 6),
    ("Buena Vista", "Longhorns", "Imperial", "I", 2, 6),
    ("Grady", "Wildcats", "Lenorah", "I", 2, 6),
    ("Rankin", "Red Devils", "Rankin", "I", 2, 6),
    ("Baird", "Bears", "Baird", "I", 2, 7),
    ("Bronte", "Longhorns", "Bronte", "I", 2, 7),
    ("Paint Rock", "Indians", "Paint Rock", "I", 2, 7),
    ("Robert Lee", "Steers", "Robert Lee", "I", 2, 7),
    ("Highland", "Hornets", "Roscoe", "I", 2, 7),
    ("Santa Anna", "Mountaineers", "Santa Anna", "I", 2, 7),
    ("Eden", "Bulldogs", "Eden", "I", 2, 8),
    ("Menard", "Yellowjackets", "Menard", "I", 2, 8),
    ("Irion County", "Hornets", "Mertzon", "I", 2, 8),
    ("Sterling City", "Eagles", "Sterling City", "I", 2, 8),
    ("Veribest", "Falcons", "Veribest", "I", 2, 8),
    ("Water Valley", "Wildcats", "Water Valley", "I", 2, 8),
    ("Bryson", "Cowboys", "Bryson", "I", 3, 9),
    ("Newcastle", "Bobcats", "Newcastle", "I", 3, 9),
    ("Perrin-Whitt", "Pirates", "Perrin", "I", 3, 9),
    ("Northside", "Indians", "Vernon", "I", 3, 9),
    ("Gordon", "Longhorns", "Gordon", "I", 3, 10),
    ("Gorman", "Panthers", "Gorman", "I", 3, 10),
    ("Lingleville", "Cardinals", "Lingleville", "I", 3, 10),
    ("May", "Tigers", "May", "I", 3, 10),
    ("Ranger", "Bulldogs", "Ranger", "I", 3, 10),
    ("Avalon", "Eagles", "Avalon", "I", 3, 11),
    ("Bluff Dale", "Bobcats", "Bluff Dale", "I", 3, 11),
    ("Blum", "Bobcats", "Blum", "I", 3, 11),
    ("Covington", "Owls", "Covington", "I", 3, 11),
    ("Milford", "Bulldogs", "Milford", "I", 3, 11),
    ("Campbell", "Indians", "Campbell", "I", 3, 12),
    ("Fruitvale", "Bobcats", "Fruitvale", "I", 3, 12),
    ("Saint Jo", "Panthers", "Saint Jo", "I", 3, 12),
    ("Savoy", "Cardinals", "Savoy", "I", 3, 12),
    ("Burkeville", "Mustangs", "Burkeville", "I", 4, 13),
    ("Chester", "Yellowjackets", "Chester", "I", 4, 13),
    ("Union Hill", "Bulldogs", "Gilmer", "I", 4, 13),
    ("Leveretts Chapel", "Lions", "Laird Hill", "I", 4, 13),
    ("Abbott", "Panthers", "Abbott", "I", 4, 14),
    ("Aquilla", "Cougars", "Aquilla", "I", 4, 14),
    ("Coolidge", "Yellowjackets", "Coolidge", "I", 4, 14),
    ("Gholson", "Wildcats", "Gholson", "I", 4, 14),
    ("Penelope", "Wolverines", "Penelope", "I", 4, 14),
    ("Evant", "Elks", "Evant", "I", 4, 15),
    ("Jonesboro", "Eagles", "Jonesboro", "I", 4, 15),
    ("Lometa", "Hornets", "Lometa", "I", 4, 15),
    ("Oglesby", "Tigers", "Oglesby", "I", 4, 15),
    ("Nueces Canyon", "Panthers", "Barksdale", "I", 4, 16),
    ("Bruni", "Badgers", "Bruni", "I", 4, 16),
    ("Knippa", "Rockcrushers", "Knippa", "I", 4, 16),
    ("Leakey", "Eagles", "Leakey", "I", 4, 16),
    ("Medina", "Bobcats", "Medina", "I", 4, 16),
    ("Prairie Lea", "Indians", "Prairie Lea", "I", 4, 16),
    # ——— UIL 1A Division II ———
    ("Follett", "Panthers", "Follett", "II", 1, 1),
    ("Groom", "Tigers", "Groom", "II", 1, 1),
    ("Hedley", "Owls", "Hedley", "II", 1, 1),
    ("Lefors", "Pirates", "Lefors", "II", 1, 1),
    ("McLean", "Tigers", "McLean", "II", 1, 1),
    ("Miami", "Warriors", "Miami", "II", 1, 1),
    ("Chillicothe", "Eagles", "Chillicothe", "II", 1, 2),
    ("Crowell", "Wildcats", "Crowell", "II", 1, 2),
    ("Guthrie", "Jaguars", "Guthrie", "II", 1, 2),
    ("Motley County", "Matadors", "Matador", "II", 1, 2),
    ("Paducah", "Dragons", "Paducah", "II", 1, 2),
    ("Valley", "Patriots", "Turkey", "II", 1, 2),
    ("Amherst", "Bulldogs", "Amherst", "II", 1, 3),
    ("Anton", "Bulldogs", "Anton", "II", 1, 3),
    ("Cotton Center", "Elks", "Cotton Center", "II", 1, 3),
    ("Hart", "Longhorns", "Hart", "II", 1, 3),
    ("Lazbuddie", "Longhorns", "Lazbuddie", "II", 1, 3),
    ("Lorenzo", "Hornets", "Lorenzo", "II", 1, 3),
    ("Loop", "Longhorns", "Loop", "II", 1, 4),
    ("Meadow", "Broncos", "Meadow", "II", 1, 4),
    ("Southland", "Eagles", "Southland", "II", 1, 4),
    ("Dawson", "Dragons", "Welch", "II", 1, 4),
    ("Wellman-Union", "Wildcats", "Wellman", "II", 1, 4),
    ("Wilson", "Mustangs", "Wilson", "II", 1, 4),
    ("Dell City", "Cougars", "Dell City", "II", 2, 5),
    ("Fort Davis", "Indians", "Fort Davis", "II", 2, 5),
    ("Marfa", "Shorthorns", "Marfa", "II", 2, 5),
    ("Sierra Blanca", "Vaqueros", "Sierra Blanca", "II", 2, 5),
    ("Balmorhea", "Bears", "Balmorhea", "II", 2, 6),
    ("Grandfalls-Royalty", "Cowboys", "Grandfalls", "II", 2, 6),
    ("Rocksprings", "Angoras", "Rocksprings", "II", 2, 6),
    ("Sanderson", "Eagles", "Sanderson", "II", 2, 6),
    ("Blackwell", "Hornets", "Blackwell", "II", 2, 7),
    ("Loraine", "Bulldogs", "Loraine", "II", 2, 7),
    ("Olfen", "Mustangs", "Olfen", "II", 2, 7),
    ("Trent", "Gorillas", "Trent", "II", 2, 7),
    ("Panther Creek", "Panthers", "Valera", "II", 2, 7),
    ("Brookesmith", "Mustangs", "Brookesmith", "II", 2, 8),
    ("Cherokee", "Indians", "Cherokee", "II", 2, 8),
    ("Lohn", "Eagles", "Lohn", "II", 2, 8),
    ("Richland Springs", "Coyotes", "Richland Springs", "II", 2, 8),
    ("Rochelle", "Hornets", "Rochelle", "II", 2, 8),
    ("Benjamin", "Mustangs", "Benjamin", "II", 3, 9),
    ("Paint Creek", "Pirates", "Haskell", "II", 3, 9),
    ("Knox City", "Greyhounds", "Knox City", "II", 3, 9),
    ("Lueders-Avoca", "Raiders", "Lueders", "II", 3, 9),
    ("Rule", "Bobcats", "Rule", "II", 3, 9),
    ("Gold-Burg", "Bears", "Bowie", "II", 3, 10),
    ("Forestburg", "Longhorns", "Forestburg", "II", 3, 10),
    ("Harrold", "Hornets", "Harrold", "II", 3, 10),
    ("Throckmorton", "Greyhounds", "Throckmorton", "II", 3, 10),
    ("Woodson", "Cowboys", "Woodson", "II", 3, 10),
    ("Moran", "Bulldogs", "Moran", "II", 3, 11),
    ("Rising Star", "Wildcats", "Rising Star", "II", 3, 11),
    ("Sidney", "Eagles", "Sidney", "II", 3, 11),
    ("Strawn", "Greyhounds", "Strawn", "II", 3, 11),
    ("Blanket", "Tigers", "Blanket", "II", 3, 12),
    ("Gustine", "Tigers", "Gustine", "II", 3, 12),
    ("Mullin", "Bulldogs", "Mullin", "II", 3, 12),
    ("Priddy", "Pirates", "Priddy", "II", 3, 12),
    ("Zephyr", "Bulldogs", "Zephyr", "II", 3, 12),
    ("Cranfills Gap", "Lions", "Cranfills Gap", "II", 4, 13),
    ("Iredell", "Dragons", "Iredell", "II", 4, 13),
    ("Kopperl", "Eagles", "Kopperl", "II", 4, 13),
    ("Morgan", "Eagles", "Morgan", "II", 4, 13),
    ("Three Way", "Braves", "Stephenville", "II", 4, 13),
    ("Walnut Springs", "Hornets", "Walnut Springs", "II", 4, 13),
    ("Bynum", "Bulldogs", "Bynum", "II", 4, 14),
    ("Fannindel", "Falcons", "Ladonia", "II", 4, 14),
    ("Mount Calm", "Panthers", "Mount Calm", "II", 4, 14),
    ("Oakwood", "Panthers", "Oakwood", "II", 4, 14),
    ("Trinidad", "Trojans", "Trinidad", "II", 4, 14),
    ("Apple Springs", "Eagles", "Apple Springs", "II", 4, 15),
    ("Buckholts", "Badgers", "Buckholts", "II", 4, 15),
    ("Calvert", "Trojans", "Calvert", "II", 4, 15),
    ("High Island", "Cardinals", "High Island", "II", 4, 15),
    ("Benavides", "Eagles", "Benavides", "II", 4, 16),
    ("Pawnee", "Indians", "Pawnee", "II", 4, 16),
    ("Runge", "Yellowjackets", "Runge", "II", 4, 16),
    ("San Perlita", "Sand Crabs", "San Perlita", "II", 4, 16),
]

REGION_SLUG = {
    1: "panhandle",
    2: "west-texas",
    3: "north-central",
    4: "central-east-south",
}

# SixManFootball.com 2026 Week 1 computer ranks (catalog names, rank = index + 1).
SMF_WEEK1_DI = [
    "Gordon", "Whiteface", "Union Hill", "Borden County", "Jayton", "Menard",
    "Aquilla", "Sands", "Rankin", "Nazareth", "Water Valley", "Westbrook",
    "Klondike", "Chester", "Oglesby", "Newcastle", "Coolidge", "Roby",
    "Milford", "Robert Lee", "Abbott", "Medina", "Booker", "May", "Hermleigh",
    "Jonesboro", "Happy", "Bluff Dale", "Garden City", "Ira", "Sterling City",
    "Whitharral", "Aspermont", "Springlake-Earth", "Northside", "Bryson",
    "Perrin-Whitt", "Claude", "O'Donnell", "Grady", "Buena Vista", "Avalon",
    "Lometa", "Irion County", "Boys Ranch", "Eden", "Saint Jo", "Leakey",
    "Veribest", "White Deer", "Gorman", "Penelope", "Highland", "Bronte",
    "Petersburg", "Rotan", "Knippa", "Blum", "Baird", "Nueces Canyon",
    "Burkeville", "Kress", "Campbell", "Paint Rock", "Silverton", "Santa Anna",
    "Ranger", "Spur", "Evant", "Gholson", "Bruni", "Covington", "Wildorado",
    "Leveretts Chapel", "Prairie Lea", "Lingleville", "Fruitvale",
    "Fort Hancock", "Savoy",
]
SMF_WEEK1_DII = [
    "Strawn", "Motley County", "Richland Springs", "Oakwood", "Zephyr",
    "Three Way", "Valley", "Cherokee", "Paducah", "McLean", "Balmorhea",
    "Knox City", "Hart", "Blanket", "Runge", "Fannindel", "Gustine",
    "Mount Calm", "Grandfalls-Royalty", "Wellman-Union", "Sidney", "Rochelle",
    "Rising Star", "Guthrie", "Meadow", "Kopperl", "Harrold", "Blackwell",
    "Rocksprings", "Iredell", "Calvert", "Chillicothe", "Apple Springs",
    "Cranfills Gap", "Trinidad", "Bynum", "Amherst", "Benjamin", "Lefors",
    "Loraine", "Crowell", "Forestburg", "Miami", "Woodson", "Gold-Burg",
    "Throckmorton", "Lorenzo", "Marfa", "Paint Creek", "Sanderson",
    "Panther Creek", "Follett", "Loop", "Benavides", "Groom", "Brookesmith",
    "Morgan", "Anton", "Trent", "Rule", "Walnut Springs", "Dawson",
    "Lazbuddie", "Buckholts", "Lohn", "Mullin", "Lueders-Avoca", "Southland",
    "Dell City", "Sierra Blanca", "Olfen", "Pawnee", "Moran",
]


@dataclass(frozen=True)
class CatalogSchool:
    team_id: str
    name: str
    mascot: str
    city: str
    division: str
    uil_region: int
    district_n: int

    @property
    def classification(self) -> str:
        return f"1A D{self.division}"

    @property
    def district(self) -> str:
        return f"{self.district_n}-1A D{self.division}"

    @property
    def region(self) -> str:
        return REGION_SLUG[self.uil_region]


def slugify(name: str) -> str:
    return re.sub(
        r"^-+|-+$",
        "",
        re.sub(r"[^a-z0-9]+", "-", name.lower().replace("&", "and").replace("'", "").replace("'", "")),
    )


def football_season_year(now=None) -> int:
    """Texas HS football year (August start). Jan–June still belong to last fall."""

    from datetime import date

    stamp = now or date.today()
    return stamp.year - 1 if stamp.month < 7 else stamp.year


def maxpreps_season_path(year: int | None = None) -> str:
    """MaxPreps path segment, e.g. 2026 → ``26-27``."""

    y = year if year is not None else football_season_year()
    return f"{str(y)[-2:]}-{str(y + 1)[-2:]}"


def maxpreps_schedule_urls(school: CatalogSchool, *, season_path: str | None = None) -> list[str]:
    """Candidate MaxPreps schedule URLs (city/name/mascot slugs, then fallbacks)."""

    path = season_path or maxpreps_season_path()
    city = slugify(school.city)
    name = slugify(school.name)
    mascot = slugify(school.mascot)
    team = f"{name}-{mascot}" if mascot else name
    slugs = []
    for city_slug, team_slug in (
        (city, team),
        (name, team),
        (city, name),
        (name, name),
    ):
        url = f"https://www.maxpreps.com/tx/{city_slug}/{team_slug}/football/{path}/schedule/"
        if url not in slugs:
            slugs.append(url)
    return slugs


def uil_schools() -> list[CatalogSchool]:
    return [
        CatalogSchool(slugify(name), name, mascot, city, division, region, district)
        for name, mascot, city, division, region, district in UIL_ROWS
    ]


def prior_rating(name: str, division: str, *, mean: float = 1500.0, spread: float = 220.0) -> float:
    """Map SixManFootball Week 1 poll rank onto the engine's 1500-centered scale."""

    board = SMF_WEEK1_DI if division == "I" else SMF_WEEK1_DII
    try:
        rank = board.index(name) + 1
    except ValueError:
        return mean
    n = max(len(board), 2)
    # Rank 1 sits near mean+spread; last sits near mean-spread.
    t = (rank - 1) / (n - 1)
    return round(mean + spread * (1.0 - 2.0 * t), 1)
