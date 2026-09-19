"""Texas six-man school directory, ported from rcullens/sixmanmadness catalog.ts.

Full field: UIL 1A DI/DII, TAPPS DI/DII/DIII/Freelance, TAIAO, TCAF, TCAL,
and independents. District / region numbers follow the 2026–28 alignments
(Aquilla = UIL I / R4 / Dist 14). Cross-association games count.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# name, mascot, city, association, division (I|II|III|Freelance), region, district
CATALOG_ROWS: list[tuple[str, str, str, str, str, int, int]] = [
    # ——— UIL 1A Division I ———
    ("Boys Ranch", "Roughriders", "Boys Ranch", "UIL", "I", 1, 1),
    ("Booker", "Kiowas", "Booker", "UIL", "I", 1, 1),
    ("Claude", "Mustangs", "Claude", "UIL", "I", 1, 1),
    ("White Deer", "Bucks", "White Deer", "UIL", "I", 1, 1),
    ("Wildorado", "Mustangs", "Wildorado", "UIL", "I", 1, 1),
    ("Springlake-Earth", "Wolverines", "Earth", "UIL", "I", 1, 2),
    ("Nazareth", "Swifts", "Nazareth", "UIL", "I", 1, 2),
    ("Whiteface", "Antelopes", "Whiteface", "UIL", "I", 1, 2),
    ("Whitharral", "Panthers", "Whitharral", "UIL", "I", 1, 2),
    ("Happy", "Cowboys", "Happy", "UIL", "I", 1, 3),
    ("Kress", "Kangaroos", "Kress", "UIL", "I", 1, 3),
    ("Petersburg", "Buffaloes", "Petersburg", "UIL", "I", 1, 3),
    ("Silverton", "Owls", "Silverton", "UIL", "I", 1, 3),
    ("Aspermont", "Hornets", "Aspermont", "UIL", "I", 1, 4),
    ("Hermleigh", "Cardinals", "Hermleigh", "UIL", "I", 1, 4),
    ("Jayton", "Jaybirds", "Jayton", "UIL", "I", 1, 4),
    ("Roby", "Lions", "Roby", "UIL", "I", 1, 4),
    ("Rotan", "Yellowhammers", "Rotan", "UIL", "I", 1, 4),
    ("Spur", "Bulldogs", "Spur", "UIL", "I", 1, 4),
    ("Sands", "Mustangs", "Ackerly", "UIL", "I", 2, 5),
    ("Borden County", "Coyotes", "Gail", "UIL", "I", 2, 5),
    ("Ira", "Bulldogs", "Ira", "UIL", "I", 2, 5),
    ("Klondike", "Cougars", "Lamesa", "UIL", "I", 2, 5),
    ("O'Donnell", "Eagles", "O'Donnell", "UIL", "I", 2, 5),
    ("Westbrook", "Wildcats", "Westbrook", "UIL", "I", 2, 5),
    ("Fort Hancock", "Mustangs", "Fort Hancock", "UIL", "I", 2, 6),
    ("Garden City", "Bearkats", "Garden City", "UIL", "I", 2, 6),
    ("Buena Vista", "Longhorns", "Imperial", "UIL", "I", 2, 6),
    ("Grady", "Wildcats", "Lenorah", "UIL", "I", 2, 6),
    ("Rankin", "Red Devils", "Rankin", "UIL", "I", 2, 6),
    ("Baird", "Bears", "Baird", "UIL", "I", 2, 7),
    ("Bronte", "Longhorns", "Bronte", "UIL", "I", 2, 7),
    ("Paint Rock", "Indians", "Paint Rock", "UIL", "I", 2, 7),
    ("Robert Lee", "Steers", "Robert Lee", "UIL", "I", 2, 7),
    ("Highland", "Hornets", "Roscoe", "UIL", "I", 2, 7),
    ("Santa Anna", "Mountaineers", "Santa Anna", "UIL", "I", 2, 7),
    ("Eden", "Bulldogs", "Eden", "UIL", "I", 2, 8),
    ("Menard", "Yellowjackets", "Menard", "UIL", "I", 2, 8),
    ("Irion County", "Hornets", "Mertzon", "UIL", "I", 2, 8),
    ("Sterling City", "Eagles", "Sterling City", "UIL", "I", 2, 8),
    ("Veribest", "Falcons", "Veribest", "UIL", "I", 2, 8),
    ("Water Valley", "Wildcats", "Water Valley", "UIL", "I", 2, 8),
    ("Bryson", "Cowboys", "Bryson", "UIL", "I", 3, 9),
    ("Newcastle", "Bobcats", "Newcastle", "UIL", "I", 3, 9),
    ("Perrin-Whitt", "Pirates", "Perrin", "UIL", "I", 3, 9),
    ("Northside", "Indians", "Vernon", "UIL", "I", 3, 9),
    ("Gordon", "Longhorns", "Gordon", "UIL", "I", 3, 10),
    ("Gorman", "Panthers", "Gorman", "UIL", "I", 3, 10),
    ("Lingleville", "Cardinals", "Lingleville", "UIL", "I", 3, 10),
    ("May", "Tigers", "May", "UIL", "I", 3, 10),
    ("Ranger", "Bulldogs", "Ranger", "UIL", "I", 3, 10),
    ("Avalon", "Eagles", "Avalon", "UIL", "I", 3, 11),
    ("Bluff Dale", "Bobcats", "Bluff Dale", "UIL", "I", 3, 11),
    ("Blum", "Bobcats", "Blum", "UIL", "I", 3, 11),
    ("Covington", "Owls", "Covington", "UIL", "I", 3, 11),
    ("Milford", "Bulldogs", "Milford", "UIL", "I", 3, 11),
    ("Campbell", "Indians", "Campbell", "UIL", "I", 3, 12),
    ("Fruitvale", "Bobcats", "Fruitvale", "UIL", "I", 3, 12),
    ("Saint Jo", "Panthers", "Saint Jo", "UIL", "I", 3, 12),
    ("Savoy", "Cardinals", "Savoy", "UIL", "I", 3, 12),
    ("Burkeville", "Mustangs", "Burkeville", "UIL", "I", 4, 13),
    ("Chester", "Yellowjackets", "Chester", "UIL", "I", 4, 13),
    ("Union Hill", "Bulldogs", "Gilmer", "UIL", "I", 4, 13),
    ("Leveretts Chapel", "Lions", "Laird Hill", "UIL", "I", 4, 13),
    ("Abbott", "Panthers", "Abbott", "UIL", "I", 4, 14),
    ("Aquilla", "Cougars", "Aquilla", "UIL", "I", 4, 14),
    ("Coolidge", "Yellowjackets", "Coolidge", "UIL", "I", 4, 14),
    ("Gholson", "Wildcats", "Gholson", "UIL", "I", 4, 14),
    ("Penelope", "Wolverines", "Penelope", "UIL", "I", 4, 14),
    ("Evant", "Elks", "Evant", "UIL", "I", 4, 15),
    ("Jonesboro", "Eagles", "Jonesboro", "UIL", "I", 4, 15),
    ("Lometa", "Hornets", "Lometa", "UIL", "I", 4, 15),
    ("Oglesby", "Tigers", "Oglesby", "UIL", "I", 4, 15),
    ("Nueces Canyon", "Panthers", "Barksdale", "UIL", "I", 4, 16),
    ("Bruni", "Badgers", "Bruni", "UIL", "I", 4, 16),
    ("Knippa", "Rockcrushers", "Knippa", "UIL", "I", 4, 16),
    ("Leakey", "Eagles", "Leakey", "UIL", "I", 4, 16),
    ("Medina", "Bobcats", "Medina", "UIL", "I", 4, 16),
    ("Prairie Lea", "Indians", "Prairie Lea", "UIL", "I", 4, 16),
    # ——— UIL 1A Division II ———
    ("Follett", "Panthers", "Follett", "UIL", "II", 1, 1),
    ("Groom", "Tigers", "Groom", "UIL", "II", 1, 1),
    ("Hedley", "Owls", "Hedley", "UIL", "II", 1, 1),
    ("Lefors", "Pirates", "Lefors", "UIL", "II", 1, 1),
    ("McLean", "Tigers", "McLean", "UIL", "II", 1, 1),
    ("Miami", "Warriors", "Miami", "UIL", "II", 1, 1),
    ("Chillicothe", "Eagles", "Chillicothe", "UIL", "II", 1, 2),
    ("Crowell", "Wildcats", "Crowell", "UIL", "II", 1, 2),
    ("Guthrie", "Jaguars", "Guthrie", "UIL", "II", 1, 2),
    ("Motley County", "Matadors", "Matador", "UIL", "II", 1, 2),
    ("Paducah", "Dragons", "Paducah", "UIL", "II", 1, 2),
    ("Valley", "Patriots", "Turkey", "UIL", "II", 1, 2),
    ("Amherst", "Bulldogs", "Amherst", "UIL", "II", 1, 3),
    ("Anton", "Bulldogs", "Anton", "UIL", "II", 1, 3),
    ("Cotton Center", "Elks", "Cotton Center", "UIL", "II", 1, 3),
    ("Hart", "Longhorns", "Hart", "UIL", "II", 1, 3),
    ("Lazbuddie", "Longhorns", "Lazbuddie", "UIL", "II", 1, 3),
    ("Lorenzo", "Hornets", "Lorenzo", "UIL", "II", 1, 3),
    ("Loop", "Longhorns", "Loop", "UIL", "II", 1, 4),
    ("Meadow", "Broncos", "Meadow", "UIL", "II", 1, 4),
    ("Southland", "Eagles", "Southland", "UIL", "II", 1, 4),
    ("Dawson", "Dragons", "Welch", "UIL", "II", 1, 4),
    ("Wellman-Union", "Wildcats", "Wellman", "UIL", "II", 1, 4),
    ("Wilson", "Mustangs", "Wilson", "UIL", "II", 1, 4),
    ("Dell City", "Cougars", "Dell City", "UIL", "II", 2, 5),
    ("Fort Davis", "Indians", "Fort Davis", "UIL", "II", 2, 5),
    ("Marfa", "Shorthorns", "Marfa", "UIL", "II", 2, 5),
    ("Sierra Blanca", "Vaqueros", "Sierra Blanca", "UIL", "II", 2, 5),
    ("Balmorhea", "Bears", "Balmorhea", "UIL", "II", 2, 6),
    ("Grandfalls-Royalty", "Cowboys", "Grandfalls", "UIL", "II", 2, 6),
    ("Rocksprings", "Angoras", "Rocksprings", "UIL", "II", 2, 6),
    ("Sanderson", "Eagles", "Sanderson", "UIL", "II", 2, 6),
    ("Blackwell", "Hornets", "Blackwell", "UIL", "II", 2, 7),
    ("Loraine", "Bulldogs", "Loraine", "UIL", "II", 2, 7),
    ("Olfen", "Mustangs", "Olfen", "UIL", "II", 2, 7),
    ("Trent", "Gorillas", "Trent", "UIL", "II", 2, 7),
    ("Panther Creek", "Panthers", "Valera", "UIL", "II", 2, 7),
    ("Brookesmith", "Mustangs", "Brookesmith", "UIL", "II", 2, 8),
    ("Cherokee", "Indians", "Cherokee", "UIL", "II", 2, 8),
    ("Lohn", "Eagles", "Lohn", "UIL", "II", 2, 8),
    ("Richland Springs", "Coyotes", "Richland Springs", "UIL", "II", 2, 8),
    ("Rochelle", "Hornets", "Rochelle", "UIL", "II", 2, 8),
    ("Benjamin", "Mustangs", "Benjamin", "UIL", "II", 3, 9),
    ("Paint Creek", "Pirates", "Haskell", "UIL", "II", 3, 9),
    ("Knox City", "Greyhounds", "Knox City", "UIL", "II", 3, 9),
    ("Lueders-Avoca", "Raiders", "Lueders", "UIL", "II", 3, 9),
    ("Rule", "Bobcats", "Rule", "UIL", "II", 3, 9),
    ("Gold-Burg", "Bears", "Bowie", "UIL", "II", 3, 10),
    ("Forestburg", "Longhorns", "Forestburg", "UIL", "II", 3, 10),
    ("Harrold", "Hornets", "Harrold", "UIL", "II", 3, 10),
    ("Throckmorton", "Greyhounds", "Throckmorton", "UIL", "II", 3, 10),
    ("Woodson", "Cowboys", "Woodson", "UIL", "II", 3, 10),
    ("Moran", "Bulldogs", "Moran", "UIL", "II", 3, 11),
    ("Rising Star", "Wildcats", "Rising Star", "UIL", "II", 3, 11),
    ("Sidney", "Eagles", "Sidney", "UIL", "II", 3, 11),
    ("Strawn", "Greyhounds", "Strawn", "UIL", "II", 3, 11),
    ("Blanket", "Tigers", "Blanket", "UIL", "II", 3, 12),
    ("Gustine", "Tigers", "Gustine", "UIL", "II", 3, 12),
    ("Mullin", "Bulldogs", "Mullin", "UIL", "II", 3, 12),
    ("Priddy", "Pirates", "Priddy", "UIL", "II", 3, 12),
    ("Zephyr", "Bulldogs", "Zephyr", "UIL", "II", 3, 12),
    ("Cranfills Gap", "Lions", "Cranfills Gap", "UIL", "II", 4, 13),
    ("Iredell", "Dragons", "Iredell", "UIL", "II", 4, 13),
    ("Kopperl", "Eagles", "Kopperl", "UIL", "II", 4, 13),
    ("Morgan", "Eagles", "Morgan", "UIL", "II", 4, 13),
    ("Three Way", "Braves", "Stephenville", "UIL", "II", 4, 13),
    ("Walnut Springs", "Hornets", "Walnut Springs", "UIL", "II", 4, 13),
    ("Bynum", "Bulldogs", "Bynum", "UIL", "II", 4, 14),
    ("Fannindel", "Falcons", "Ladonia", "UIL", "II", 4, 14),
    ("Mount Calm", "Panthers", "Mount Calm", "UIL", "II", 4, 14),
    ("Oakwood", "Panthers", "Oakwood", "UIL", "II", 4, 14),
    ("Trinidad", "Trojans", "Trinidad", "UIL", "II", 4, 14),
    ("Apple Springs", "Eagles", "Apple Springs", "UIL", "II", 4, 15),
    ("Buckholts", "Badgers", "Buckholts", "UIL", "II", 4, 15),
    ("Calvert", "Trojans", "Calvert", "UIL", "II", 4, 15),
    ("High Island", "Cardinals", "High Island", "UIL", "II", 4, 15),
    ("Benavides", "Eagles", "Benavides", "UIL", "II", 4, 16),
    ("Pawnee", "Indians", "Pawnee", "UIL", "II", 4, 16),
    ("Runge", "Yellowjackets", "Runge", "UIL", "II", 4, 16),
    ("San Perlita", "Sand Crabs", "San Perlita", "UIL", "II", 4, 16),
    # ——— TAPPS Six-Man Division I ———
    ("Abilene Christian", "Panthers", "Abilene", "TAPPS", "I", 1, 1),
    ("Covenant Classical", "Cavaliers", "Fort Worth", "TAPPS", "I", 1, 1),
    ("Lakehill Prep", "Warriors", "Dallas", "TAPPS", "I", 1, 1),
    ("Temple Christian", "Eagles", "Fort Worth", "TAPPS", "I", 1, 1),
    ("Trinity Midland", "Chargers", "Midland", "TAPPS", "I", 1, 1),
    ("Coram Deo", "Lions", "Plano", "TAPPS", "I", 2, 2),
    ("Rockwall Heritage", "Eagles", "Rockwall", "TAPPS", "I", 2, 2),
    ("Lucas Christian", "Warriors", "Lucas", "TAPPS", "I", 2, 2),
    ("Vanguard College Prep", "Vikings", "Waco", "TAPPS", "I", 2, 2),
    ("Lutheran San Antonio", "Mustangs", "San Antonio", "TAPPS", "I", 3, 3),
    ("St. Augustine", "Knights", "Laredo", "TAPPS", "I", 3, 3),
    ("Castle Hills", "Eagles", "San Antonio", "TAPPS", "I", 3, 3),
    ("Faith Academy", "Flames", "Marble Falls", "TAPPS", "I", 3, 3),
    ("Round Rock Christian", "Crusaders", "Round Rock", "TAPPS", "I", 3, 3),
    ("Texas School for the Deaf", "Rangers", "Austin", "TAPPS", "I", 3, 3),
    ("Veritas Academy", "Lions", "Austin", "TAPPS", "I", 3, 3),
    ("First Baptist Christian", "Warriors", "Pasadena", "TAPPS", "I", 4, 4),
    ("Logos Prep", "Lions", "Sugar Land", "TAPPS", "I", 4, 4),
    ("Emery/Weiner", "Jaguars", "Houston", "TAPPS", "I", 4, 4),
    ("Westbury Christian", "Wildcats", "Houston", "TAPPS", "I", 4, 4),
    ("Immanuel Christian", "Warriors", "El Paso", "TAPPS", "Freelance", 0, 0),
    ("Covenant Christian", "Cougars", "Conroe", "TAPPS", "Freelance", 0, 0),
    ("Cornerstone", "Warriors", "McKinney", "TAPPS", "Freelance", 0, 0),
    # ——— TAPPS Six-Man Division II ———
    ("Denton Calvary", "Lions", "Denton", "TAPPS", "II", 1, 1),
    ("Fellowship Academy", "Mustangs", "Kennedale", "TAPPS", "II", 1, 1),
    ("Harvest Christian Keller", "Saints", "Keller", "TAPPS", "II", 1, 1),
    ("Holy Cross Midland", "Crusaders", "Midland", "TAPPS", "II", 1, 1),
    ("Nazarene Christian", "Lions", "Crowley", "TAPPS", "II", 1, 1),
    ("Weatherford Christian", "Lions", "Weatherford", "TAPPS", "II", 1, 1),
    ("Garland Christian", "Swordsmen", "Garland", "TAPPS", "II", 2, 2),
    ("Lone Star North", "Tornadoes", "Gainesville", "TAPPS", "II", 2, 2),
    ("Ovilla Christian", "Eagles", "Red Oak", "TAPPS", "II", 2, 2),
    ("Prestonwood North", "Lions", "Prosper", "TAPPS", "II", 2, 2),
    ("The Highlands", "Blazers", "Irving", "TAPPS", "II", 2, 2),
    ("Wylie Prep", "Patriots", "Wylie", "TAPPS", "II", 2, 2),
    ("Bracken Christian", "Warriors", "Bulverde", "TAPPS", "II", 3, 3),
    ("Concordia", "Cardinals", "Pflugerville", "TAPPS", "II", 3, 3),
    ("Lone Star Southeast", "Mustangs", "Giddings", "TAPPS", "II", 3, 3),
    ("San Marcos Academy", "Bears", "San Marcos", "TAPPS", "II", 3, 3),
    ("St. Joseph Bryan", "Eagles", "Bryan", "TAPPS", "II", 3, 3),
    ("Valor Prep", "Knights", "Waco", "TAPPS", "II", 3, 3),
    ("Alpha Omega", "Lions", "Huntsville", "TAPPS", "II", 4, 4),
    ("Baytown Christian", "Bulldogs", "Baytown", "TAPPS", "II", 4, 4),
    ("Brazosport Christian", "Eagles", "Lake Jackson", "TAPPS", "II", 4, 4),
    ("Legacy Christian Beaumont", "Warriors", "Beaumont", "TAPPS", "II", 4, 4),
    # ——— TAPPS Six-Man Division III ———
    ("Christ the King", "Golden Lions", "Lubbock", "TAPPS", "III", 1, 1),
    ("Kingdom Prep", "Warriors", "Lubbock", "TAPPS", "III", 1, 1),
    ("San Jacinto Christian", "Patriots", "Amarillo", "TAPPS", "III", 1, 1),
    ("Wichita Christian", "Stars", "Wichita Falls", "TAPPS", "III", 1, 1),
    ("Azle Christian", "Crusaders", "Azle", "TAPPS", "III", 1, 2),
    ("Fairhill", "Falcons", "Dallas", "TAPPS", "III", 1, 2),
    ("Texoma Christian", "Eagles", "Sherman", "TAPPS", "III", 1, 2),
    ("Victory Christian", "Patriots", "Decatur", "TAPPS", "III", 1, 2),
    ("Christian Heritage Longview", "Sentinels", "Longview", "TAPPS", "III", 2, 3),
    ("Greenville Christian", "Eagles", "Greenville", "TAPPS", "III", 2, 3),
    ("Poetry Community", "Patriots", "Terrell", "TAPPS", "III", 2, 3),
    ("Providence Academy", "Lions", "Rockwall", "TAPPS", "III", 2, 3),
    ("Trinity School of Texas", "Titans", "Longview", "TAPPS", "III", 2, 3),
    ("Annapolis Christian", "Warriors", "Corpus Christi", "TAPPS", "III", 2, 4),
    ("Fredericksburg Heritage", "Eagles", "Fredericksburg", "TAPPS", "III", 2, 4),
    ("Hill Country Christian", "Rams", "San Marcos", "TAPPS", "III", 2, 4),
    ("Living Rock Academy", "Lions", "Bulverde", "TAPPS", "III", 2, 4),
    ("Our Lady of the Hills", "Hawks", "Kerrville", "TAPPS", "III", 2, 4),
    ("Austin Classical", "Mustangs", "Austin", "TAPPS", "III", 3, 5),
    ("Allen Academy", "Rams", "Bryan", "TAPPS", "III", 3, 5),
    ("Holy Trinity Temple", "Crusaders", "Temple", "TAPPS", "III", 3, 5),
    ("Summit Christian", "Eagles", "Cedar Park", "TAPPS", "III", 3, 5),
    ("Covenant Prep", "Knights", "Kingwood", "TAPPS", "III", 3, 6),
    ("Divine Savior", "Rays", "Missouri City", "TAPPS", "III", 3, 6),
    ("Faith Bellville", "Knights", "Bellville", "TAPPS", "III", 3, 6),
    ("Founders Christian", "Falcons", "Spring", "TAPPS", "III", 3, 6),
    ("Grace Christian Houston", "Eagles", "Houston", "TAPPS", "III", 3, 6),
    ("Second Baptist UM", "Eagles", "Houston", "TAPPS", "III", 3, 6),
    ("Second Baptist Cypress", "Eagles", "Cypress", "TAPPS", "III", 3, 6),
    ("Second Baptist North", "Eagles", "Houston", "TAPPS", "III", 3, 6),
    # ——— TAIAO homeschool ———
    ("Texas Wind", "Skyhawks", "Dallas", "TAIAO", "I", 1, 1),
    ("THESA", "Riders", "Fort Worth", "TAIAO", "I", 1, 1),
    ("Lubbock Titans", "Titans", "Lubbock", "TAIAO", "I", 1, 1),
    ("Texas Leadership Midland", "Eagles", "Midland", "TAIAO", "I", 1, 1),
    ("El Paso Leadership", "Leaders", "El Paso", "TAIAO", "I", 1, 1),
    ("Tyler HEAT", "HEAT", "Tyler", "TAIAO", "I", 1, 1),
    ("ETHS", "Chargers", "Tyler", "TAIAO", "I", 1, 1),
    ("Austin Royals", "Royals", "Austin", "TAIAO", "I", 2, 2),
    ("Founders Classical Leander", "Archers", "Leander", "TAIAO", "I", 2, 2),
    ("WILCO", "Falcons", "Georgetown", "TAIAO", "I", 2, 2),
    ("BVCHEA", "Mustangs", "College Station", "TAIAO", "I", 2, 2),
    ("Fort Bend Homeschool", "Chargers", "Sugar Land", "TAIAO", "I", 2, 2),
    ("SA Homeschool", "Patriots", "San Antonio", "TAIAO", "I", 2, 2),
    ("CenTex Homeschool", "Chargers", "Temple", "TAIAO", "I", 2, 2),
    ("Valor North Austin", "Lions", "Austin", "TAIAO", "I", 2, 2),
    ("Jubilee Brownsville", "Titans", "Brownsville", "TAIAO", "I", 2, 2),
    ("Georgetown Grace", "Griffins", "Georgetown", "TAIAO", "II", 1, 1),
    ("JCSA", "Lions", "Cleburne", "TAIAO", "II", 1, 1),
    ("King's Academy", "Knights", "Tyler", "TAIAO", "II", 1, 1),
    ("PCHEA", "Warriors", "Amarillo", "TAIAO", "II", 1, 1),
    ("Greenville Homeschool", "Archers", "Greenville", "TAIAO", "II", 1, 1),
    ("Plainview Classical", "Eagles", "Plainview", "TAIAO", "II", 1, 1),
    ("Founders Classical Conroe", "Voyagers", "Conroe", "TAIAO", "II", 1, 1),
    ("Newman International", "Warriors", "Cedar Hill", "TAIAO", "II", 1, 1),
    ("Victoria Gators", "Gators", "Victoria", "TAIAO", "II", 2, 2),
    ("New Braunfels Spartans", "Spartans", "New Braunfels", "TAIAO", "II", 2, 2),
    ("Valor South Austin", "Falcons", "Austin", "TAIAO", "II", 2, 2),
    ("Coastal Christian", "Badgers", "Corpus Christi", "TAIAO", "II", 2, 2),
    ("Brazos Valley Lions", "Lions", "Bryan", "TAIAO", "II", 2, 2),
    ("NYOS", "Jaguars", "Austin", "TAIAO", "II", 2, 2),
    ("Compass Rose", "Polar Bears", "San Antonio", "TAIAO", "II", 2, 2),
    ("Big Springs Charter", "Hawks", "Leakey", "TAIAO", "II", 2, 2),
    ("New Braunfels Thunder", "Thunder", "New Braunfels", "TAIAO", "III", 1, 1),
    ("Grace Classical Granbury", "Gryphons", "Granbury", "TAIAO", "III", 1, 1),
    ("Stephenville Faith", "Knights", "Stephenville", "TAIAO", "III", 1, 1),
    ("West Texas Tornadoes", "Tornadoes", "Midland", "TAIAO", "III", 1, 1),
    ("Grayson Christian", "Falcons", "Sherman", "TAIAO", "III", 1, 1),
    ("Community Christian Mineral Wells", "Warriors", "Mineral Wells", "TAIAO", "III", 1, 1),
    ("Wise County Homeschool", "Warriors", "Decatur", "TAIAO", "III", 1, 1),
    ("Ignite Community", "Guardians", "Mesquite", "TAIAO", "III", 1, 1),
    ("Jubilee Lake View", "Rams", "San Antonio", "TAIAO", "III", 2, 2),
    ("Town East Christian", "Eagles", "San Antonio", "TAIAO", "III", 2, 2),
    ("Jubilee San Antonio", "Lions", "San Antonio", "TAIAO", "III", 2, 2),
    ("Hill Country Knights", "Knights", "Boerne", "TAIAO", "III", 2, 2),
    ("Arlington Heights Christian", "Lions", "Corpus Christi", "TAIAO", "III", 2, 2),
    ("St. Mary's Taylor", "Rams", "Taylor", "TAIAO", "III", 2, 2),
    ("Valor Kyle", "Kingfishers", "Kyle", "TAIAO", "III", 2, 2),
    ("Valor Leander", "Griffins", "Leander", "TAIAO", "III", 2, 2),
    ("Victoria Cobras", "Cobras", "Victoria", "TAIAO", "III", 2, 2),
    ("Texas Empowerment", "Panthers", "Austin", "TAIAO", "III", 2, 2),
    ("CHANT Homeschool", "Knights", "Houston", "TAIAO", "Freelance", 0, 0),
    ("Northside Lions", "Lions", "San Antonio", "TAIAO", "Freelance", 0, 0),
    ("Tribe Warriors", "Warriors", "Austin", "TAIAO", "Freelance", 0, 0),
    ("UME Prep", "Lions", "Dallas", "TAIAO", "Freelance", 0, 0),
    ("Gloria Deo", "Lions", "Spring Branch", "TAIAO", "Freelance", 0, 0),
    ("Calvary Baptist Academy", "Eagles", "Fort Worth", "TAIAO", "Freelance", 0, 0),
    ("Waco Christian", "Lions", "Waco", "TAIAO", "Freelance", 0, 0),
    # ——— TCAF / TCAL / independents ———
    ("Faustina", "Falcons", "Irving", "TCAF", "I", 1, 1),
    ("Harvest Christian Lantana", "Saints", "Lantana", "TCAF", "I", 1, 1),
    ("Methodist Children's Home", "Bulldogs", "Waco", "TCAF", "I", 1, 1),
    ("Grace Christian Perrin", "Colts", "Perrin", "TCAF", "I", 1, 1),
    ("Westlake Academy", "Blacksmiths", "Westlake", "TCAF", "I", 1, 1),
    ("St. Paul Prep", "Lions", "Arlington", "TCAF", "I", 1, 1),
    ("Dallas Academy", "Bulldogs", "Dallas", "TCAF", "I", 1, 1),
    ("DaVinci", "Lions", "San Antonio", "TCAL", "I", 1, 1),
    ("Westhoff", "Warriors", "Westhoff", "IND", "Freelance", 0, 0),
    ("North Star", "Naturals", "Dallas", "IND", "Freelance", 0, 0),
    ("Pinnacle Christian", "Falcons", "Dallas", "IND", "Freelance", 0, 0),
]

REGION_SLUG = {
    1: "panhandle",
    2: "west-texas",
    3: "north-central",
    4: "central-east-south",
}

ASSOC_REGION = {
    "TAPPS": "tapps",
    "TAIAO": "taiao",
    "TCAF": "tcaf",
    "TCAL": "tcal",
    "IND": "independent",
}

# Extra feed labels that do not slug-match the catalog name.
NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "first-baptist-christian": (
        "First Baptist",
        "First Baptist Academy",
        "Pasadena First Baptist",
        "FBA",
        "First Baptist Christian Academy",
    ),
    "emery-weiner": ("Emery Weiner", "The Emery/Weiner School", "Emery-Weiner"),
    "texas-school-for-the-deaf": ("TSD", "Texas School for the Deaf Rangers"),
    "methodist-childrens-home": ("Methodist Childrens Home", "MCH Waco"),
    "st-augustine": ("Saint Augustine", "St Augustine"),
    "st-joseph-bryan": ("Saint Joseph Bryan", "St Joseph", "St. Joseph"),
    "st-marys-taylor": ("Saint Marys Taylor", "St Marys Taylor"),
    "st-paul-prep": ("Saint Paul Prep", "St Paul Prep"),
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
    association: str
    division: str
    uil_region: int
    district_n: int

    @property
    def classification(self) -> str:
        if self.association == "UIL":
            return f"1A D{self.division}"
        if self.division == "Freelance":
            return f"{self.association} Freelance" if self.association != "IND" else "IND"
        if self.association in {"TCAF", "TCAL"}:
            return self.association
        return f"{self.association} D{self.division}"

    @property
    def district(self) -> str:
        if self.association == "UIL":
            return f"{self.district_n}-1A D{self.division}"
        if not self.district_n:
            return "Independent" if self.association == "IND" else f"{self.association} Freelance"
        return f"{self.district_n}-{self.association} D{self.division}"

    @property
    def region(self) -> str:
        if self.association == "UIL":
            return REGION_SLUG[self.uil_region]
        return ASSOC_REGION.get(self.association, self.association.lower())


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


def catalog_schools() -> list[CatalogSchool]:
    return [
        CatalogSchool(slugify(name), name, mascot, city, assoc, division, region, district)
        for name, mascot, city, assoc, division, region, district in CATALOG_ROWS
    ]


def uil_schools() -> list[CatalogSchool]:
    """Full Texas six-man catalog (name kept for existing ingest callers)."""

    return catalog_schools()


def prior_rating(name: str, division: str, *, mean: float = 1500.0, spread: float = 220.0) -> float:
    """Map SixManFootball Week 1 poll rank onto the engine's 1500-centered scale."""

    board = SMF_WEEK1_DI if division == "I" else SMF_WEEK1_DII
    try:
        rank = board.index(name) + 1
    except ValueError:
        return mean
    n = max(len(board), 2)
    t = (rank - 1) / (n - 1)
    return round(mean + spread * (1.0 - 2.0 * t), 1)
