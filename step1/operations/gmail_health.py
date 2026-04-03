"""
Gmail Health Activity — Human-like browsing to build Google trust score.

Launches random activities on a logged-in Google profile:
  • Google Search — random queries (country-specific), click results, browse
  • Google Maps — search locations (country-specific), click places
  • YouTube — scroll feed, click video, watch briefly
  • Gmail — open inbox, scroll, read emails
  • Google Drive — visit drive, browse
  • Google Account — visit security settings, click around
  • Google News — browse headlines, click articles
  • Google Shopping — search products, browse

Activities are randomized each run with human-like delays.
Duration and country are configurable.
"""

import asyncio
import random
import time

from shared.logger import _log
from shared.robust import robust_goto

# ─────────────────────────────────────────────────────────────────────────────
# Country-specific content pools
# ─────────────────────────────────────────────────────────────────────────────

COUNTRY_SEARCH_QUERIES = {
    'US': [
        "best restaurants near me", "weather forecast today", "latest news",
        "how to cook pasta carbonara", "funny cat videos", "top movies 2025",
        "best budget smartphones", "morning workout routine", "healthy breakfast ideas",
        "best coffee shops near me", "how to fix a leaky faucet", "national parks to visit",
        "best free online courses", "how to save money fast", "best hiking trails",
        "easy dinner recipes", "best laptops under 500", "how to write a resume",
        "best podcasts 2025", "home office setup ideas", "best running shoes",
        "simple smoothie recipes", "best museums in the world", "travel packing tips",
        "how to tie a tie", "meal prep ideas for the week", "indoor plant care tips",
        "best board games 2025", "best documentaries on netflix",
        "super bowl highlights", "nba scores today", "best pizza near me",
        "amazon deals today", "gas prices near me", "dmv appointment",
    ],
    'FR': [
        "meilleurs restaurants paris", "météo aujourd'hui", "actualités france",
        "recette crêpes bretonnes", "comment faire un gâteau au chocolat",
        "films français 2025", "meilleur smartphone pas cher", "exercices de yoga",
        "idées petit déjeuner sain", "cafés à paris", "comment réparer un robinet",
        "parcs nationaux france", "cours en ligne gratuits", "économiser de l'argent",
        "randonnées en france", "recettes faciles rapides", "meilleur ordinateur portable",
        "comment écrire un cv", "podcasts français populaires", "aménagement bureau maison",
        "chaussures de course", "recettes de smoothies", "musées à visiter en france",
        "conseils voyage", "préparation repas semaine", "plantes d'intérieur",
        "ligue 1 résultats", "tour de france 2025", "boulangerie près de moi",
        "soldes en ligne", "prix essence", "bon plan vacances",
        "recette ratatouille", "horaires sncf", "programme télé ce soir",
        "meilleur fromage français", "vin rouge recommandation", "brocante près de moi",
        "comment faire du pain maison", "jardin potager conseils",
    ],
    'BD': [
        "আজকের খবর", "রান্নার রেসিপি", "ঢাকার রেস্টুরেন্ট",
        "best restaurants dhaka", "weather dhaka today", "bangladesh cricket score",
        "biryani recipe bangla", "hilsa fish recipe", "latest bangla movie",
        "chittagong hill tracts travel", "cox bazar hotel booking",
        "sundarban tour package", "bangladesh news today", "bkash offer today",
        "grameenphone internet offer", "robi recharge offer",
        "dhaka university admission", "online earning bangladesh",
        "ielts preparation tips", "best coaching center dhaka",
        "bangladesh vs india cricket", "bpl 2025 schedule",
        "cheap flights from dhaka", "best mobile under 15000 bdt",
    ],
    'IN': [
        "best restaurants near me", "aaj ka mausam", "latest news india",
        "biryani recipe", "butter chicken recipe", "bollywood movies 2025",
        "best budget phones india", "morning yoga routine", "healthy breakfast indian",
        "best cafes mumbai", "ipl 2025 schedule", "upsc preparation tips",
        "neet exam preparation", "flipkart sale today", "amazon great indian sale",
        "railway pnr status", "petrol price today", "gold rate today",
        "best places to visit india", "goa travel package", "delhi street food",
        "jio recharge plans", "airtel offers today", "aadhaar card update",
        "pan card apply online", "sbi bank balance check", "mutual fund sip",
        "cricket live score", "best dosa near me", "south indian recipes",
    ],
    'DE': [
        "beste Restaurants in meiner Nähe", "Wetter heute", "aktuelle Nachrichten",
        "Rezept Schnitzel", "Schwarzwälder Kirschtorte Rezept", "beste Filme 2025",
        "günstiges Smartphone", "Yoga Übungen Anfänger", "gesundes Frühstück",
        "Cafés in Berlin", "Bundesliga Ergebnisse", "wandern in den Alpen",
        "kostenlose Online-Kurse", "Geld sparen Tipps", "beste Wanderwege Deutschland",
        "einfache Abendessen Rezepte", "bester Laptop unter 500 Euro",
        "Bewerbung schreiben Tipps", "Podcasts auf Deutsch", "Homeoffice einrichten",
        "Laufschuhe Test", "Smoothie Rezepte", "Museen in Deutschland",
        "Reise Packliste", "Meal Prep Ideen", "Zimmerpflanzen Pflege",
        "Deutsche Bahn Fahrplan", "Oktoberfest München", "Weihnachtsmarkt besuchen",
    ],
    'TR': [
        "yakınımdaki restoranlar", "hava durumu bugün", "son dakika haberleri",
        "lahmacun tarifi", "baklava nasıl yapılır", "en iyi filmler 2025",
        "uygun fiyatlı telefon", "yoga hareketleri", "sağlıklı kahvaltı",
        "istanbul kafeleri", "süper lig puan durumu", "kapadokya gezi rehberi",
        "ücretsiz online kurslar", "para biriktirme yolları", "türkiye'de yürüyüş parkurları",
        "kolay yemek tarifleri", "en iyi laptop", "cv nasıl yazılır",
        "türkçe podcastler", "ev ofis düzenleme", "koşu ayakkabısı",
        "smoothie tarifleri", "türkiye müzeleri", "seyahat çantası hazırlama",
        "haftalık yemek hazırlığı", "iç mekan bitkileri bakımı",
        "istanbul'da gezilecek yerler", "antalya otelleri", "türk kahvesi yapımı",
    ],
    'BR': [
        "melhores restaurantes perto de mim", "previsão do tempo hoje", "últimas notícias",
        "receita de feijoada", "bolo de cenoura receita", "melhores filmes 2025",
        "celular bom e barato", "exercícios de yoga", "café da manhã saudável",
        "cafeterias em são paulo", "brasileirão resultados", "trilhas no brasil",
        "cursos online gratuitos", "como economizar dinheiro", "melhores praias brasil",
        "receitas fáceis para jantar", "melhor notebook custo benefício",
        "como fazer currículo", "podcasts em português", "home office organização",
        "tênis para corrida", "receitas de smoothie", "museus no brasil",
        "dicas de viagem", "meal prep receitas", "plantas para apartamento",
        "preço da gasolina hoje", "carnaval 2025", "receita de pão de queijo",
    ],
    'PK': [
        "best restaurants near me", "weather today", "pakistan news today",
        "biryani recipe pakistani", "nihari recipe", "latest pakistani drama",
        "best budget phones pakistan", "cricket live score pakistan",
        "psl 2025 schedule", "cheap flights pakistan", "islamabad restaurants",
        "lahore food street", "karachi beach", "northern areas pakistan travel",
        "hunza valley tour package", "jazz internet packages", "telenor call packages",
        "online earning in pakistan", "freelancing tips urdu",
        "best universities pakistan", "css exam preparation",
        "gold rate today pakistan", "dollar rate today", "petrol price pakistan",
    ],
    'ID': [
        "restoran terdekat", "cuaca hari ini", "berita terkini indonesia",
        "resep nasi goreng", "resep rendang", "film terbaru 2025",
        "hp murah terbaik", "olahraga di rumah", "sarapan sehat",
        "kafe di jakarta", "liga 1 klasemen", "tempat wisata indonesia",
        "kursus online gratis", "cara menabung", "pantai terindah indonesia",
        "resep masakan mudah", "laptop murah terbaik", "cara membuat cv",
        "podcast indonesia", "dekorasi ruang kerja", "sepatu lari terbaik",
        "resep smoothie", "museum di indonesia", "tips traveling",
        "harga bbm hari ini", "promo tokopedia", "resep martabak",
    ],
    'PH': [
        "best restaurants near me", "weather today philippines", "latest news philippines",
        "adobo recipe", "sinigang recipe", "latest pinoy movies 2025",
        "best budget phones philippines", "home workout routine",
        "healthy breakfast ideas", "cafes in manila", "pba scores today",
        "best beaches philippines", "free online courses", "how to save money",
        "boracay travel guide", "easy dinner recipes pinoy", "best laptop for students",
        "how to write a resume", "popular podcasts philippines",
        "work from home setup", "running shoes philippines", "smoothie recipes",
        "museums in manila", "travel tips domestic", "meal prep ideas",
        "indoor plants care", "gcash promo today", "shopee sale schedule",
    ],
    'GB': [
        "best restaurants near me", "weather forecast today", "latest news uk",
        "fish and chips near me", "sunday roast recipe", "best films 2025",
        "best budget phones uk", "morning workout routine", "healthy breakfast ideas",
        "best coffee shops london", "premier league results", "hiking trails uk",
        "free online courses uk", "how to save money uk", "national trust places",
        "easy dinner recipes", "best laptops under 500", "how to write a cv uk",
        "best podcasts 2025", "home office ideas", "best running shoes uk",
        "smoothie recipes", "museums london", "packing list holiday",
        "train times uk", "bbc iplayer", "best pubs near me",
    ],
}

COUNTRY_MAP_LOCATIONS = {
    'US': [
        "Times Square New York", "Golden Gate Bridge", "Statue of Liberty",
        "Central Park NYC", "Grand Canyon Arizona", "Hollywood Sign LA",
        "Empire State Building", "Yellowstone National Park", "Miami Beach",
        "Las Vegas Strip", "Disney World Orlando", "Space Needle Seattle",
    ],
    'FR': [
        "Tour Eiffel Paris", "Louvre Museum Paris", "Notre-Dame de Paris",
        "Mont Saint-Michel", "Château de Versailles", "Arc de Triomphe Paris",
        "Côte d'Azur Nice", "Sacré-Cœur Montmartre", "Pont du Gard",
        "Carcassonne", "Strasbourg Cathedral", "Lyon Vieux Lyon",
        "Marseille Vieux-Port", "Bordeaux centre-ville", "Toulouse Capitole",
    ],
    'BD': [
        "Cox's Bazar Beach", "Sundarbans Bangladesh", "Lalbagh Fort Dhaka",
        "Ahsan Manzil Dhaka", "Srimangal Tea Gardens", "Saint Martin Island",
        "Ratargul Swamp Forest", "Paharpur Bihar", "Rangamati Lake",
        "Kuakata Beach", "Sonargaon", "Mahasthangarh",
    ],
    'IN': [
        "Taj Mahal Agra", "India Gate New Delhi", "Gateway of India Mumbai",
        "Hawa Mahal Jaipur", "Qutub Minar Delhi", "Red Fort Delhi",
        "Mysore Palace", "Golden Temple Amritsar", "Goa Beaches",
        "Kerala Backwaters", "Varanasi Ghats", "Hampi Ruins",
    ],
    'DE': [
        "Brandenburg Gate Berlin", "Neuschwanstein Castle", "Cologne Cathedral",
        "Berlin Wall Memorial", "Munich Marienplatz", "Heidelberg Castle",
        "Hamburg Speicherstadt", "Dresden Frauenkirche", "Black Forest",
        "Rhine Valley", "Zugspitze", "Rothenburg ob der Tauber",
    ],
    'TR': [
        "Hagia Sophia Istanbul", "Blue Mosque Istanbul", "Cappadocia",
        "Ephesus Ruins", "Topkapi Palace", "Grand Bazaar Istanbul",
        "Pamukkale Travertines", "Antalya Old Town", "Galata Tower",
        "Mount Nemrut", "Troy Ancient City", "Bodrum Castle",
    ],
    'BR': [
        "Christ the Redeemer Rio", "Sugarloaf Mountain", "Copacabana Beach",
        "Iguazu Falls Brazil", "Amazon Rainforest Manaus", "São Paulo Paulista",
        "Pelourinho Salvador", "Chapada Diamantina", "Fernando de Noronha",
        "Ouro Preto", "Lençóis Maranhenses", "Foz do Iguaçu",
    ],
    'PK': [
        "Badshahi Mosque Lahore", "Faisal Mosque Islamabad", "Minar-e-Pakistan",
        "Hunza Valley", "Skardu Pakistan", "Mohenjo-daro", "Lahore Fort",
        "Fairy Meadows", "Nanga Parbat Base Camp", "Swat Valley",
        "Taxila Museum", "Karachi Clifton Beach",
    ],
    'ID': [
        "Bali Tanah Lot Temple", "Borobudur Temple Java", "Komodo Island",
        "Raja Ampat Papua", "Ubud Monkey Forest", "Bromo Mountain",
        "Jakarta Monas", "Yogyakarta Kraton", "Lake Toba Sumatra",
        "Prambanan Temple", "Gili Islands", "Tana Toraja",
    ],
    'PH': [
        "Chocolate Hills Bohol", "Mayon Volcano", "Intramuros Manila",
        "El Nido Palawan", "Boracay Beach", "Banaue Rice Terraces",
        "Coron Palawan", "Cebu Basilica", "Vigan Heritage City",
        "Siargao Island", "Puerto Princesa Underground River", "Taal Volcano",
    ],
    'GB': [
        "Big Ben London", "Buckingham Palace", "Tower of London",
        "Stonehenge", "Edinburgh Castle", "Bath Roman Baths",
        "Windsor Castle", "Lake District", "Oxford University",
        "Cambridge Colleges", "Stratford-upon-Avon", "Giant's Causeway",
    ],
}

COUNTRY_YOUTUBE_SEARCHES = {
    'US': [
        "relaxing music", "cooking tutorial", "travel vlog", "tech review 2025",
        "how to draw", "funny animals compilation", "science experiment",
        "workout at home", "guitar lesson beginner", "nature documentary",
    ],
    'FR': [
        "musique relaxante", "recette cuisine française", "vlog voyage france",
        "test tech 2025", "tuto dessin", "animaux drôles compilation",
        "expérience scientifique", "sport à la maison", "cours de guitare",
        "documentaire nature france",
    ],
    'BD': [
        "bangla song", "bangladeshi cooking recipe", "dhaka city vlog",
        "mobile review bangla", "drawing tutorial bangla", "funny bangla video",
        "cricket highlights bangladesh", "home workout bangla",
        "bangla natok new", "travel vlog bangladesh",
    ],
    'IN': [
        "bollywood songs", "indian cooking recipe", "travel vlog india",
        "tech review hindi", "drawing tutorial", "funny indian videos",
        "cricket highlights india", "yoga at home hindi",
        "guitar lesson hindi", "indian wildlife documentary",
    ],
    'DE': [
        "entspannende Musik", "Kochen lernen deutsch", "Reise Vlog Deutschland",
        "Tech Review deutsch", "Zeichnen lernen", "lustige Tier Videos",
        "Wissenschaft Experiment", "Sport zu Hause", "Gitarre lernen",
        "Natur Dokumentation",
    ],
    'TR': [
        "rahatlatıcı müzik", "yemek tarifi türk mutfağı", "gezi vlog türkiye",
        "teknoloji inceleme 2025", "resim çizme dersi", "komik hayvan videoları",
        "bilim deneyi", "evde spor", "gitar dersi", "doğa belgeseli",
    ],
    'BR': [
        "música relaxante", "receita culinária brasileira", "vlog viagem brasil",
        "review tecnologia 2025", "tutorial desenho", "animais engraçados",
        "experiência científica", "treino em casa", "aula de violão",
        "documentário natureza brasil",
    ],
    'PK': [
        "pakistani songs", "pakistani cooking recipe", "travel vlog pakistan",
        "mobile review urdu", "drawing tutorial urdu", "funny pakistani videos",
        "cricket highlights pakistan", "home workout urdu",
        "naat sharif", "northern areas pakistan travel",
    ],
    'ID': [
        "musik santai", "resep masakan indonesia", "travel vlog indonesia",
        "review teknologi 2025", "tutorial menggambar", "video lucu binatang",
        "eksperimen sains", "olahraga di rumah", "belajar gitar",
        "dokumenter alam indonesia",
    ],
    'PH': [
        "opm music", "filipino cooking recipe", "travel vlog philippines",
        "tech review 2025 filipino", "drawing tutorial", "funny pinoy videos",
        "basketball highlights pba", "home workout", "guitar tutorial tagalog",
        "nature documentary philippines",
    ],
    'GB': [
        "relaxing music", "british cooking recipe", "travel vlog uk",
        "tech review 2025", "drawing tutorial", "funny animal videos",
        "science experiment", "home workout", "guitar lesson beginner",
        "nature documentary bbc",
    ],
}

COUNTRY_SHOPPING_QUERIES = {
    'US': [
        "wireless earbuds", "running shoes", "laptop stand", "water bottle",
        "desk lamp", "backpack", "phone case", "headphones", "webcam",
    ],
    'FR': [
        "écouteurs sans fil", "chaussures de course", "support ordinateur",
        "bouteille d'eau", "lampe de bureau", "sac à dos", "coque téléphone",
        "casque audio", "webcam",
    ],
    'BD': [
        "wireless earbuds", "running shoes", "mobile cover", "power bank",
        "desk lamp", "backpack", "laptop bag", "headphones", "smartwatch",
    ],
    'IN': [
        "wireless earbuds india", "running shoes", "laptop stand",
        "water bottle", "desk lamp", "backpack", "phone case",
        "headphones", "smartwatch under 5000",
    ],
    'DE': [
        "kabellose Kopfhörer", "Laufschuhe", "Laptopständer",
        "Trinkflasche", "Schreibtischlampe", "Rucksack", "Handyhülle",
        "Kopfhörer", "Webcam",
    ],
    'TR': [
        "kablosuz kulaklık", "koşu ayakkabısı", "laptop standı",
        "su şişesi", "masa lambası", "sırt çantası", "telefon kılıfı",
        "kulaklık", "webcam",
    ],
    'BR': [
        "fone bluetooth", "tênis corrida", "suporte notebook",
        "garrafa de água", "luminária mesa", "mochila", "capinha celular",
        "headphone", "webcam",
    ],
    'PK': [
        "wireless earbuds pakistan", "running shoes", "laptop bag",
        "power bank", "desk lamp", "backpack", "mobile cover",
        "headphones", "smartwatch",
    ],
    'ID': [
        "earbuds wireless", "sepatu lari", "stand laptop",
        "botol minum", "lampu meja", "tas ransel", "case hp",
        "headphone", "webcam",
    ],
    'PH': [
        "wireless earbuds", "running shoes", "laptop stand",
        "water bottle", "desk lamp", "backpack", "phone case",
        "headphones", "webcam",
    ],
    'GB': [
        "wireless earbuds uk", "running shoes", "laptop stand",
        "water bottle", "desk lamp", "backpack", "phone case",
        "headphones", "webcam",
    ],
}

# Default fallback
DEFAULT_COUNTRY = 'US'


def _get_queries(country):
    return COUNTRY_SEARCH_QUERIES.get(country, COUNTRY_SEARCH_QUERIES[DEFAULT_COUNTRY])

def _get_locations(country):
    return COUNTRY_MAP_LOCATIONS.get(country, COUNTRY_MAP_LOCATIONS[DEFAULT_COUNTRY])

def _get_yt_searches(country):
    return COUNTRY_YOUTUBE_SEARCHES.get(country, COUNTRY_YOUTUBE_SEARCHES[DEFAULT_COUNTRY])

def _get_shopping(country):
    return COUNTRY_SHOPPING_QUERIES.get(country, COUNTRY_SHOPPING_QUERIES[DEFAULT_COUNTRY])


# ─────────────────────────────────────────────────────────────────────────────
# Helper — human-like delays & scrolling
# ─────────────────────────────────────────────────────────────────────────────

async def _human_delay(min_s=1.5, max_s=5.0):
    """Random human-like pause."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def _human_scroll(page, scrolls=None):
    """Random scrolling down the page (1-5 scrolls)."""
    if scrolls is None:
        scrolls = random.randint(1, 5)
    for _ in range(scrolls):
        delta = random.randint(200, 600)
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.5, 2.0))


async def _human_scroll_up(page, scrolls=None):
    """Random scrolling up."""
    if scrolls is None:
        scrolls = random.randint(1, 3)
    for _ in range(scrolls):
        delta = random.randint(-600, -200)
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.5, 1.5))


async def _safe_click(page, selector, timeout=5000):
    """Click element if visible, return True/False."""
    try:
        loc = page.locator(selector).first
        if await loc.count() > 0:
            await loc.wait_for(state='visible', timeout=timeout)
            await loc.click()
            return True
    except Exception:
        pass
    return False


async def _dismiss_google_consent(page):
    """Dismiss Google consent / cookie popup if present (optional, best-effort)."""
    try:
        # Selectors for 'Accept all' across languages (FR, EN, DE, etc.)
        selectors = [
            '#L2AGLb',                          # primary ID
            'button.tHlp8d',                    # class-based
            'button[aria-label*="Accept"]',     # EN aria
            'button[aria-label*="Accepter"]',   # FR aria
            'form[action*="consent"] button[value="1"]',  # consent form
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                try:
                    await loc.click(timeout=3000)
                    await page.wait_for_load_state('domcontentloaded', timeout=5000)
                    return
                except Exception:
                    continue
    except Exception:
        pass


async def _safe_goto(page, url, worker_id, label=""):
    """Navigate with error handling."""
    try:
        await robust_goto(page, url, worker_id)
        await _human_delay(1.5, 3.0)
        await _dismiss_google_consent(page)
        await _human_delay(0.5, 1.5)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Google Search
# ─────────────────────────────────────────────────────────────────────────────

async def _google_search(page, worker_id, country='US', query=None):
    """Perform a Google search, click 1-2 results, browse briefly."""
    if query is None:
        queries = _get_queries(country)
        query = random.choice(queries)
    _log(worker_id, f"[HEALTH] Google Search: '{query}'")

    if not await _safe_goto(page, "https://www.google.com", worker_id):
        return

    # Dismiss consent popup if it appeared after page load
    await _dismiss_google_consent(page)

    # Type search query
    try:
        search_input = page.locator('textarea[name="q"], input[name="q"]').first
        if await search_input.count() > 0:
            await search_input.click()
            await _human_delay(0.5, 1.5)
            await search_input.fill(query)
            await _human_delay(0.5, 1.0)
            await page.keyboard.press('Enter')
            await _human_delay(2.0, 4.0)
        else:
            return
    except Exception:
        return

    # Scroll through results
    await _human_scroll(page, random.randint(1, 3))
    await _human_delay(1.0, 3.0)

    # Click 1-2 search results
    clicks = random.randint(1, 2)
    for _ in range(clicks):
        try:
            results = page.locator('div#search a h3')
            count = await results.count()
            if count > 0:
                idx = random.randint(0, min(count - 1, 7))
                await results.nth(idx).click()
                await _human_delay(3.0, 8.0)

                # Browse the page
                await _human_scroll(page, random.randint(1, 4))
                await _human_delay(2.0, 5.0)

                if random.random() > 0.5:
                    await _human_scroll_up(page, 1)
                    await _human_delay(1.0, 2.0)

                await page.go_back()
                await _human_delay(2.0, 4.0)
        except Exception:
            break

    _log(worker_id, f"[HEALTH] Google Search complete: '{query}'")


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Google Maps
# ─────────────────────────────────────────────────────────────────────────────

async def _browse_maps(page, worker_id, country='US'):
    """Browse Google Maps — search a location, explore."""
    locations = _get_locations(country)
    location = random.choice(locations)
    _log(worker_id, f"[HEALTH] Google Maps: '{location}'")

    if not await _safe_goto(page, "https://www.google.com/maps", worker_id):
        return

    await _human_delay(2.0, 4.0)

    try:
        search_box = page.locator('#searchboxinput').first
        if await search_box.count() > 0:
            await search_box.click()
            await _human_delay(0.5, 1.0)
            await search_box.fill(location)
            await _human_delay(0.5, 1.0)
            await page.keyboard.press('Enter')
            await _human_delay(3.0, 6.0)
        else:
            return
    except Exception:
        return

    await _human_scroll(page, random.randint(1, 3))
    await _human_delay(2.0, 5.0)

    # Try clicking on a nearby place
    try:
        place_links = page.locator('a[href*="/maps/place/"]')
        cnt = await place_links.count()
        if cnt > 0:
            idx = random.randint(0, min(cnt - 1, 4))
            await place_links.nth(idx).click()
            await _human_delay(3.0, 6.0)
            await _human_scroll(page, random.randint(1, 2))
    except Exception:
        pass

    # Zoom in/out randomly
    try:
        for _ in range(random.randint(1, 3)):
            key = random.choice(['+', '-'])
            await page.keyboard.press(key)
            await _human_delay(1.0, 2.0)
    except Exception:
        pass

    await _human_delay(2.0, 4.0)
    _log(worker_id, f"[HEALTH] Google Maps complete: '{location}'")


# ─────────────────────────────────────────────────────────────────────────────
# Activity: YouTube
# ─────────────────────────────────────────────────────────────────────────────

async def _browse_youtube(page, worker_id, country='US'):
    """Browse YouTube — search, click a video, watch briefly."""
    yt_searches = _get_yt_searches(country)
    query = random.choice(yt_searches)
    _log(worker_id, f"[HEALTH] YouTube: '{query}'")

    if not await _safe_goto(page, "https://www.youtube.com", worker_id):
        return

    await _human_delay(2.0, 4.0)

    # Scroll the home feed first
    await _human_scroll(page, random.randint(1, 3))
    await _human_delay(1.0, 3.0)

    # Search
    try:
        search_input = page.locator('input#search, input[name="search_query"]').first
        if await search_input.count() > 0:
            await search_input.click()
            await _human_delay(0.5, 1.0)
            await search_input.fill(query)
            await _human_delay(0.5, 1.0)
            await page.keyboard.press('Enter')
            await _human_delay(3.0, 6.0)
        else:
            return
    except Exception:
        return

    await _human_scroll(page, random.randint(1, 3))
    await _human_delay(1.0, 2.0)

    # Click a video
    try:
        video_links = page.locator('a#video-title, ytd-video-renderer a#thumbnail')
        cnt = await video_links.count()
        if cnt > 0:
            idx = random.randint(0, min(cnt - 1, 5))
            await video_links.nth(idx).click()
            await _human_delay(3.0, 5.0)

            # "Watch" for 10-30 seconds
            watch_time = random.uniform(10, 30)
            _log(worker_id, f"[HEALTH] YouTube: watching video for {watch_time:.0f}s")
            await asyncio.sleep(watch_time)

            # Scroll down to comments area
            await _human_scroll(page, random.randint(1, 3))
            await _human_delay(2.0, 4.0)

            if random.random() > 0.5:
                await _human_scroll_up(page, 2)
                await _human_delay(1.0, 2.0)
    except Exception:
        pass

    _log(worker_id, f"[HEALTH] YouTube complete: '{query}'")


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Gmail
# ─────────────────────────────────────────────────────────────────────────────

async def _check_gmail(page, worker_id, country='US'):
    """Open Gmail inbox, scroll, maybe read an email."""
    _log(worker_id, "[HEALTH] Gmail: checking inbox")

    if not await _safe_goto(page, "https://mail.google.com/mail/u/0/#inbox", worker_id):
        return

    await _human_delay(3.0, 6.0)

    await _human_scroll(page, random.randint(1, 4))
    await _human_delay(2.0, 4.0)

    # Try clicking an email row
    try:
        email_rows = page.locator('tr.zA, div[role="row"]')
        cnt = await email_rows.count()
        if cnt > 0:
            idx = random.randint(0, min(cnt - 1, 9))
            await email_rows.nth(idx).click()
            await _human_delay(3.0, 6.0)

            await _human_scroll(page, random.randint(1, 3))
            await _human_delay(3.0, 6.0)

            await page.go_back()
            await _human_delay(2.0, 3.0)
    except Exception:
        pass

    # Maybe check another tab
    if random.random() > 0.6:
        try:
            tabs = page.locator('div[role="tab"]')
            cnt = await tabs.count()
            if cnt > 1:
                idx = random.randint(1, min(cnt - 1, 3))
                await tabs.nth(idx).click()
                await _human_delay(2.0, 4.0)
                await _human_scroll(page, random.randint(1, 2))
                await _human_delay(2.0, 3.0)
        except Exception:
            pass

    _log(worker_id, "[HEALTH] Gmail complete")


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Google Drive
# ─────────────────────────────────────────────────────────────────────────────

async def _visit_drive(page, worker_id, country='US'):
    """Visit Google Drive, browse files."""
    _log(worker_id, "[HEALTH] Google Drive: browsing")

    if not await _safe_goto(page, "https://drive.google.com/drive/my-drive", worker_id):
        return

    await _human_delay(3.0, 5.0)

    await _human_scroll(page, random.randint(1, 3))
    await _human_delay(2.0, 4.0)

    try:
        items = page.locator('div[data-target="doc"]')
        cnt = await items.count()
        if cnt > 0:
            idx = random.randint(0, min(cnt - 1, 5))
            await items.nth(idx).click()
            await _human_delay(2.0, 4.0)
    except Exception:
        pass

    if random.random() > 0.5:
        try:
            await _safe_goto(page, "https://drive.google.com/drive/shared-with-me", worker_id)
            await _human_scroll(page, random.randint(1, 2))
            await _human_delay(2.0, 4.0)
        except Exception:
            pass

    _log(worker_id, "[HEALTH] Google Drive complete")


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Google Account
# ─────────────────────────────────────────────────────────────────────────────

async def _visit_account(page, worker_id, country='US'):
    """Visit Google Account settings, click around."""
    _log(worker_id, "[HEALTH] Google Account: visiting settings")

    pages_to_visit = [
        "https://myaccount.google.com/",
        "https://myaccount.google.com/security",
        "https://myaccount.google.com/personal-info",
        "https://myaccount.google.com/data-and-privacy",
    ]

    visit_count = random.randint(1, 2)
    chosen = random.sample(pages_to_visit, min(visit_count, len(pages_to_visit)))

    for url in chosen:
        if not await _safe_goto(page, url, worker_id):
            continue

        await _human_delay(2.0, 4.0)
        await _human_scroll(page, random.randint(1, 3))
        await _human_delay(2.0, 5.0)

        if random.random() > 0.5:
            await _human_scroll_up(page, 1)
            await _human_delay(1.0, 2.0)

    _log(worker_id, "[HEALTH] Google Account complete")


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Google News
# ─────────────────────────────────────────────────────────────────────────────

async def _browse_news(page, worker_id, country='US'):
    """Browse Google News — read headlines, click articles."""
    _log(worker_id, "[HEALTH] Google News: browsing")

    if not await _safe_goto(page, "https://news.google.com/", worker_id):
        return

    await _human_delay(2.0, 4.0)

    await _human_scroll(page, random.randint(2, 5))
    await _human_delay(2.0, 4.0)

    clicks = random.randint(1, 2)
    for _ in range(clicks):
        try:
            articles = page.locator('article a[href]')
            cnt = await articles.count()
            if cnt > 0:
                idx = random.randint(0, min(cnt - 1, 8))
                await articles.nth(idx).click()
                await _human_delay(4.0, 8.0)

                await _human_scroll(page, random.randint(2, 5))
                await _human_delay(3.0, 6.0)

                await page.go_back()
                await _human_delay(2.0, 3.0)
        except Exception:
            break

    _log(worker_id, "[HEALTH] Google News complete")


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Google Shopping
# ─────────────────────────────────────────────────────────────────────────────

async def _browse_shopping(page, worker_id, country='US'):
    """Browse Google Shopping — search products, browse."""
    shopping = _get_shopping(country)
    query = random.choice(shopping)
    _log(worker_id, f"[HEALTH] Google Shopping: '{query}'")

    url = f"https://www.google.com/search?q={query.replace(' ', '+')}&tbm=shop"
    if not await _safe_goto(page, url, worker_id):
        return

    await _human_delay(2.0, 4.0)

    await _human_scroll(page, random.randint(1, 4))
    await _human_delay(2.0, 4.0)

    try:
        products = page.locator('div.sh-dgr__gr-auto a')
        cnt = await products.count()
        if cnt > 0:
            idx = random.randint(0, min(cnt - 1, 5))
            await products.nth(idx).click()
            await _human_delay(3.0, 6.0)
            await _human_scroll(page, random.randint(1, 3))
            await _human_delay(2.0, 4.0)
            await page.go_back()
            await _human_delay(1.0, 2.0)
    except Exception:
        pass

    _log(worker_id, f"[HEALTH] Google Shopping complete: '{query}'")


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

ALL_ACTIVITIES = [
    _google_search,
    _browse_maps,
    _browse_youtube,
    _check_gmail,
    _visit_drive,
    _visit_account,
    _browse_news,
    _browse_shopping,
]


# ─────────────────────────────────────────────────────────────────────────────
# Simple new activity functions for additional Google services
# ─────────────────────────────────────────────────────────────────────────────

async def _visit_photos(page, worker_id, country='US', variant=''):
    try:
        await page.goto('https://photos.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(200, 500))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_translate(page, worker_id, country='US', variant=''):
    try:
        await page.goto('https://translate.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_calendar(page, worker_id, country='US', variant=''):
    try:
        await page.goto('https://calendar.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_keep(page, worker_id, country='US', variant=''):
    try:
        await page.goto('https://keep.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_play(page, worker_id, country='US', variant=''):
    try:
        await page.goto('https://play.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(200, 500))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_meet(page, worker_id, country='US', variant=''):
    try:
        await page.goto('https://meet.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Activity ID → (function, query/variant) mapping
# ─────────────────────────────────────────────────────────────────────────────

SEARCH_QUERIES_BY_ID = {
    'search_restaurants': "best restaurants near me",
    'search_news': "latest news today",
    'search_weather': "weather forecast today",
    'search_movies': "best movies and shows 2025",
    'search_sports': "sports scores today",
    'search_tech': "technology news 2025",
    'search_travel': "best travel destinations 2025",
    'search_recipes': "easy dinner recipes",
    'search_products': "best product reviews 2025",
    'search_local': "local businesses near me",
}

# Activity-specific queries (used when a specific topic is requested)
# Falls back to random country pool when entry is missing.
ACTIVITY_QUERIES = {
    'search_crypto':      ['bitcoin price today', 'ethereum price usd', 'crypto market cap', 'best crypto to buy 2025', 'bitcoin news today', 'solana price prediction', 'dogecoin news', 'crypto portfolio tracker', 'defi explained', 'nft market 2025'],
    'search_fashion':     ['fashion trends 2025', 'spring outfit ideas', 'best fashion brands online', 'street style inspiration', 'capsule wardrobe essentials', 'affordable fashion haul', 'sustainable fashion brands', 'how to style a blazer', 'summer dress trends', 'men fashion 2025'],
    'search_beauty':      ['skincare routine morning', 'best moisturizer for dry skin', 'makeup tutorial beginners', 'hair care tips for growth', 'best beauty products 2025', 'natural skincare routine', 'anti aging serums', 'eyeshadow blending tips', 'curly hair routine', 'best drugstore makeup'],
    'search_jobs':        ['remote jobs work from home 2025', 'how to write cover letter', 'best jobs near me', 'highest paying jobs no degree', 'linkedin profile tips', 'resume writing tips 2025', 'freelance jobs for beginners', 'data entry jobs remote', 'how to ace job interview', 'side hustle ideas 2025'],
    'search_finance':     ['how to invest money for beginners', 'stock market today', 'best high yield savings account', 'credit score improvement tips', 'personal finance tips 2025', 'how to budget monthly', 'index fund vs etf', 'best dividend stocks', 'how to get out of debt fast', 'passive income ideas'],
    'search_fitness':     ['best home workout routine', 'no equipment workout', 'how to lose belly fat', 'protein rich foods list', 'beginner yoga morning routine', 'gym workout plan for beginners', 'running tips for beginners', 'best pre workout foods', 'how to build muscle fast', 'intermittent fasting benefits'],
    'search_health':      ['symptoms of vitamin d deficiency', 'how to improve sleep quality', 'stress relief techniques', 'best health supplements 2025', 'immune system boost foods', 'mental health tips daily', 'anxiety management techniques', 'healthy gut foods', 'hydration benefits', 'best vitamins for energy'],
    'search_realestate':  ['houses for rent near me', 'how to buy first home tips', 'apartment rental guide', 'real estate market trends 2025', 'best mortgage rates today', 'how to negotiate house price', 'home buying checklist', 'condo vs house pros cons', 'investment property tips', 'rental property income'],
    'search_gaming':      ['best games 2025', 'pc gaming setup budget guide', 'best ps5 games', 'gaming news today', 'minecraft survival tips', 'best free pc games', 'gaming monitor review', 'how to reduce lag gaming', 'best gaming headset', 'elden ring tips'],
    'search_diy':         ['diy home improvement ideas', 'how to paint walls perfectly', 'furniture restoration tips beginner', 'diy garden raised bed', 'budget home decor ideas', 'how to fix squeaky floors', 'bathroom renovation tips', 'kitchen cabinet painting', 'outdoor patio ideas', 'diy bookshelf plans'],
    'search_cars':        ['best cars 2025 review', 'used car buying checklist', 'car maintenance schedule', 'electric car comparison 2025', 'best car insurance cheap', 'how to detail a car at home', 'car tires when to replace', 'best suv 2025', 'hybrid car benefits', 'car loan tips'],
    'search_pets':        ['dog training tips at home', 'best dry cat food', 'pet care basics guide', 'veterinarian near me', 'dog breed comparison', 'puppy potty training', 'cat behavior tips', 'best pet insurance', 'fish tank beginner setup', 'rabbit care tips'],
    'search_education':   ['online courses free certificate', 'how to learn python programming', 'best books to read 2025', 'study tips for exams', 'learn spanish online free', 'best learning apps 2025', 'how to speed read', 'time management for students', 'best youtube channels learning', 'coursera vs udemy'],
    'search_travel':      ['best travel destinations 2025', 'cheap flights tips', 'travel packing list', 'best travel insurance', 'solo travel tips', 'budget travel europe', 'best hotels booking tips', 'travel hacks flight deals', 'visa requirements guide', 'best travel credit cards'],
    'search_food':        ['best restaurants near me', 'easy dinner recipes tonight', 'healthy meal prep ideas', 'air fryer recipes easy', 'vegan recipes beginners', 'what to cook with chicken', 'quick breakfast ideas', 'baking tips for beginners', 'best pizza dough recipe', 'slow cooker recipes easy'],
    'search_shopping':    ['best deals amazon today', 'online shopping tips save money', 'product comparison 2025', 'coupon codes today', 'cashback shopping apps', 'best buy vs amazon', 'back to school shopping list', 'holiday gift ideas', 'best subscription boxes', 'black friday deals'],
    'search_tech_news':   ['technology news today', 'new iphone 2025 release', 'best laptop 2025', 'artificial intelligence news', 'cybersecurity tips home', 'best smart home devices', 'android vs iphone 2025', 'best budget tablet', 'cloud storage comparison', 'best vpn service 2025'],
    'search_sports_news': ['sports news today', 'premier league results', 'nba highlights today', 'formula 1 race results', 'tennis atp rankings', 'football transfer news', 'boxing news today', 'cricket world cup', 'golf pga tour results', 'olympic sports news'],
    'search_news_world':  ['world news today', 'breaking news headlines', 'economy news 2025', 'climate change news', 'political news today', 'business news today', 'science news 2025', 'space exploration news', 'health news today', 'environment news'],
}

# French-specific queries for ALL search activity categories
# Used when country='FR' — ensures realistic French user browsing behavior
ACTIVITY_QUERIES_FR = {
    # Core searches
    'search_restaurants': ['meilleurs restaurants paris', 'restaurant gastronomique pas cher', 'restaurant livraison domicile', 'meilleur burger paris', 'restaurant végétarien lyon', 'pizza livraison rapide', 'restaurant romantique bordeaux', 'avis tripadvisor restaurant', 'menu du jour restaurant', 'restaurant ouvert dimanche'],
    'search_news':        ['actualités france aujourd\'hui', 'dernières nouvelles france', 'actu politique france', 'journal télévisé replay', 'infos locales', 'le monde actualités', 'lefigaro actualités', 'bfmtv dernières nouvelles', 'actualités économie france', 'actu régionale'],
    'search_weather':     ['météo aujourd\'hui paris', 'météo demain lyon', 'prévisions météo semaine', 'météo ile de france', 'météo côte d\'azur', 'températures france', 'météo montagne', 'météo bordeaux', 'météo marseille', 'météo week-end'],
    'search_movies':      ['films français 2025', 'meilleurs films netflix france', 'cinéma programme cette semaine', 'films à voir 2025', 'allocine avis films', 'séries netflix populaires', 'films d\'action 2025', 'comédie française récente', 'oscars 2025 films', 'disney plus nouveautés'],
    'search_sports':      ['résultats ligue 1 aujourd\'hui', 'classement ligue 1 2025', 'psg match prochain', 'équipe de france football', 'tour de france 2025', 'roland garros résultats', 'champions league programme', 'rugby top 14', 'transfert foot france', 'tennis atp résultats'],
    'search_tech':        ['meilleur smartphone 2025', 'test iphone 16 pro', 'samsung galaxy comparatif', 'meilleur ordinateur portable', 'tablette ipad ou samsung', 'vrai test airpods', 'smart tv guide d\'achat', 'comparatif antivirus 2025', 'clé usb vitesse rapide', 'écouteurs sans fil test'],
    'search_travel':      ['voyage pas cher europe', 'destination vacances été 2025', 'vol paris rome pas cher', 'location voiture vacances', 'camping france bord mer', 'hôtels pas chers paris', 'visa espagne français', 'que faire à amsterdam', 'week-end romantique france', 'train pas cher sncf'],
    'search_recipes':     ['recette crêpes bretonnes', 'recette tarte tatin facile', 'poulet rôti recette', 'gratin dauphinois maison', 'quiche lorraine originale', 'soupe à l\'oignon gratinée', 'boeuf bourguignon recette', 'crème brûlée maison', 'ratatouille provençale', 'recette pain maison levure'],
    'search_products':    ['avis produits amazon france', 'comparatif aspirateur robot', 'meilleur robot cuisine', 'cafetière capsule test', 'tondeuse barbe avis', 'machine à café comparatif', 'aspirateur dyson test', 'friteuse sans huile comparatif', 'climatiseur mobile test', 'purificateur air comparatif'],
    'search_local':       ['pharmacie de garde près de moi', 'médecin généraliste disponible', 'supermarché ouvert maintenant', 'coiffeur pas cher près de moi', 'garage auto réparation', 'boulangerie artisanale', 'pressing à proximité', 'opticien paris', 'dentiste urgence', 'serrurier urgence'],
    # Extended categories
    'search_crypto':      ['prix bitcoin aujourd\'hui', 'cours ethereum en direct', 'crypto actualités france', 'meilleure crypto à acheter', 'portefeuille crypto application', 'cryptomonnaie débutant', 'ripple xrp cours', 'avalanche crypto prix', 'defi finance décentralisée', 'nft marché 2025'],
    'search_fashion':     ['tendances mode femme 2025', 'marques mode française luxe', 'tenues printemps été', 'mode homme casual chic', 'soldes été france', 'vêtements bio éthique', 'style vestimentaire parisien', 'sacs à main tendance', 'chaussures mode 2025', 'comment s\'habiller élégamment'],
    'search_beauty':      ['routine beauté matin naturelle', 'meilleur soin hydratant visage', 'tutoriel maquillage naturel', 'soin cheveux bouclés', 'produits beauté bio france', 'anti-âge crème efficace', 'fond de teint teint parfait', 'soin peau sensible', 'routine cheveux abîmés', 'cosmétiques français bio'],
    'search_jobs':        ['offres emploi télétravail france', 'comment rédiger cv 2025', 'emploi cadre paris', 'métiers bien rémunérés', 'freelance indépendant france', 'pole emploi offres', 'reconversion professionnelle', 'lettre motivation exemple', 'entretien embauche conseils', 'salaire moyen france 2025'],
    'search_finance':     ['comment investir son argent', 'bourse cac40 aujourd\'hui', 'taux livret a 2025', 'crédit immobilier taux', 'retraite épargne conseils', 'assurance vie avantages', 'impôts déclaration revenus', 'bourse débutant france', 'meilleure banque en ligne', 'actions dividendes france'],
    'search_fitness':     ['exercices maison sans matériel', 'perdre du ventre rapidement', 'aliments riches en protéines', 'yoga débutant matin', 'programme musculation gratuit', 'cardio brûle graisses', 'stretching quotidien', 'courir débutant programme', 'nutrition sportive conseils', 'hiit entraînement maison'],
    'search_health':      ['symptômes carence vitamine d', 'améliorer sommeil naturellement', 'gestion stress quotidien', 'booster immunité naturellement', 'compléments alimentaires avis', 'santé mentale conseils', 'méditation bienfaits', 'alimentation équilibrée semaine', 'remèdes naturels rhume', 'douleurs dos soulager'],
    'search_realestate':  ['prix immobilier paris 2025', 'louer appartement pas cher', 'acheter maison france', 'crédit immobilier simulation', 'location saisonnière airbnb', 'investissement locatif rentable', 'dpe maison explication', 'terrain constructible prix', 'promoteur immobilier avis', 'notaire frais achat immobilier'],
    'search_gaming':      ['meilleurs jeux pc 2025', 'ps5 jeux exclusifs', 'jeux switch nouveautés', 'gaming setup budget france', 'jeux gratuits 2025', 'gta 6 sortie france', 'minecraft serveur français', 'league of legends guide', 'steam soldes jeux', 'jeux de rôle rpg pc'],
    'search_diy':         ['bricolage maison débutant', 'comment peindre mur salon', 'renovation appartement budget', 'jardinage potager débutant', 'décoration intérieure tendance', 'parquet poser soi-même', 'plomberie fuite réparer', 'menuiserie bois débutant', 'isolation maison économie', 'cuisine relooker pas cher'],
    'search_cars':        ['meilleure voiture électrique 2025', 'voiture d\'occasion achat conseils', 'contrôle technique obligation', 'assurance auto pas chère', 'entretien voiture soi-même', 'pneus quand changer', 'bonus écologique voiture', 'comparatif suv 2025', 'leasing voiture avantages', 'voiture hybride rechargeable'],
    'search_pets':        ['alimentation chien naturelle', 'meilleure nourriture chat', 'vétérinaire urgence paris', 'dresser son chien maison', 'race chien appartement', 'vaccination chien calendrier', 'comportement chat comprendre', 'assurance animaux comparatif', 'aquarium débutant poissons', 'lapin nain soins'],
    'search_education':   ['cours en ligne gratuit france', 'apprendre anglais rapidement', 'formation professionnelle gratuite', 'bac révisions conseils', 'université france inscription', 'mooc certificat reconnu', 'formation certifiante en ligne', 'apprendre programmation python', 'parcoursup orientation', 'bourse étudiant conditions'],
    'search_shopping':    ['code promo amazon france', 'soldes été bonnes affaires', 'cashback application france', 'fnac promo du jour', 'vinted occasion mode', 'comparateur prix en ligne', 'black friday france date', 'leboncoin achat vente', 'cdiscount promotions', 'veepee ventes privées'],
    'search_tech_news':   ['actualités technologie france', 'intelligence artificielle actualités', 'nouvelles applications 2025', 'cybersécurité conseils', 'apple nouveautés 2025', 'google android mise à jour', 'nouvelles voitures électriques tech', 'maison connectée domotique', 'réseaux sociaux actualités', 'startup française tech'],
    'search_sports_news': ['ligue 1 résultats', 'psg champions league', 'rugby xv de france', 'tour de france étapes', 'tennis roland garros', 'formule 1 grand prix', 'équipe france résultats', 'handball france championnat', 'jeux olympiques france', 'cyclisme france actualités'],
    'search_news_world':  ['actualités monde aujourd\'hui', 'europe politique actualités', 'économie mondiale 2025', 'climat environnement france', 'conflit international news', 'relations diplomatiques france', 'sciences découvertes', 'espace exploration nouvelles', 'santé actualités mondiales', 'technologie monde'],
    'search_shopping_electronics': ['bon plan high tech france', 'promotion téléphone', 'pc portable soldes', 'tablette prix réduit', 'écran pc offre', 'casque audio promo', 'montre connectée soldes', 'appareil photo offre', 'enceinte bluetooth promo', 'disque dur externe pas cher'],
}

# Map: country code → activity query dict
# Add more countries here to expand localization
_ACTIVITY_QUERIES_BY_COUNTRY = {
    'FR': ACTIVITY_QUERIES_FR,
    # Add 'DE', 'ES', 'IT' etc. here when needed
}

ACTIVITY_MAP = {
    # Google Search
    'search_restaurants':   (_google_search, 'restaurants'),
    'search_news':          (_google_search, 'news'),
    'search_weather':       (_google_search, 'weather'),
    'search_movies':        (_google_search, 'movies'),
    'search_sports':        (_google_search, 'sports'),
    'search_tech':          (_google_search, 'tech'),
    'search_travel':        (_google_search, 'travel'),
    'search_recipes':       (_google_search, 'recipes'),
    'search_products':      (_google_search, 'products'),
    'search_local':         (_google_search, 'local'),
    # Gmail
    'gmail_inbox':          (_check_gmail, 'inbox'),
    'gmail_read_email':     (_check_gmail, 'read'),
    'gmail_check_spam':     (_check_gmail, 'spam'),
    'gmail_check_sent':     (_check_gmail, 'sent'),
    'gmail_scroll_inbox':   (_check_gmail, 'scroll'),
    'gmail_search_email':   (_check_gmail, 'search'),
    # YouTube
    'youtube_browse_feed':  (_browse_youtube, 'feed'),
    'youtube_trending':     (_browse_youtube, 'trending'),
    'youtube_search_music': (_browse_youtube, 'music'),
    'youtube_shorts':       (_browse_youtube, 'shorts'),
    'youtube_subscriptions':(_browse_youtube, 'subscriptions'),
    'youtube_watch_video':  (_browse_youtube, 'watch'),
    # Google Maps
    'maps_search_restaurants': (_browse_maps, 'restaurants'),
    'maps_directions':      (_browse_maps, 'directions'),
    'maps_browse_places':   (_browse_maps, 'places'),
    'maps_view_photos':     (_browse_maps, 'photos'),
    'maps_read_reviews':    (_browse_maps, 'reviews'),
    'maps_street_view':     (_browse_maps, 'street'),
    # Google Drive
    'drive_browse':         (_visit_drive, 'browse'),
    'drive_recent':         (_visit_drive, 'recent'),
    'drive_shared':         (_visit_drive, 'shared'),
    'drive_new_doc':        (_visit_drive, 'new_doc'),
    # Google Account
    'account_security':     (_visit_account, 'security'),
    'account_activity':     (_visit_account, 'activity'),
    'account_profile':      (_visit_account, 'profile'),
    'account_privacy':      (_visit_account, 'privacy'),
    # Google News
    'news_headlines':       (_browse_news, 'headlines'),
    'news_tech':            (_browse_news, 'tech'),
    'news_sports':          (_browse_news, 'sports'),
    'news_entertainment':   (_browse_news, 'entertainment'),
    'news_business':        (_browse_news, 'business'),
    # Google Shopping
    'shopping_electronics': (_browse_shopping, 'electronics'),
    'shopping_clothing':    (_browse_shopping, 'clothing'),
    'shopping_compare':     (_browse_shopping, 'compare'),
    'shopping_deals':       (_browse_shopping, 'deals'),
    # Google Photos
    'photos_browse':        (_visit_photos, 'browse'),
    'photos_albums':        (_visit_photos, 'albums'),
    # Other Services
    'translate_phrases':    (_visit_translate, ''),
    'calendar_view':        (_visit_calendar, ''),
    'keep_browse':          (_visit_keep, ''),
    'play_browse_apps':     (_visit_play, ''),
    'meet_check':           (_visit_meet, ''),
    # Specific topic searches
    'search_crypto':      (_google_search, 'crypto'),
    'search_fashion':     (_google_search, 'fashion'),
    'search_beauty':      (_google_search, 'beauty'),
    'search_jobs':        (_google_search, 'jobs'),
    'search_finance':     (_google_search, 'finance'),
    'search_fitness':     (_google_search, 'fitness'),
    'search_health':      (_google_search, 'health'),
    'search_realestate':  (_google_search, 'realestate'),
    'search_gaming':      (_google_search, 'gaming'),
    'search_diy':         (_google_search, 'diy'),
    'search_cars':        (_google_search, 'cars'),
    'search_pets':        (_google_search, 'pets'),
    'search_education':   (_google_search, 'education'),
    'search_food':        (_google_search, 'food'),
    'search_shopping':    (_google_search, 'shopping'),
    'search_tech_news':   (_google_search, 'tech_news'),
    'search_sports_news': (_google_search, 'sports_news'),
    'search_news_world':  (_google_search, 'news_world'),
}


async def gmail_health_activity(page, worker_id, duration_minutes=10, country='US',
                                activities=None):
    """
    Run random human-like activities.

    Args:
        page: Playwright page object (logged-in Google profile)
        worker_id: Worker number for logging
        duration_minutes: Legacy param — only used if activities is None (fallback)
        country: Country code for localized queries
        activities: List of activity IDs to run (round-robin, shuffled).
                    If None, falls back to timed duration_minutes mode.

    Returns:
        dict with success, activities_done, activity_log
    """
    if activities:
        # New mode: run each activity once in random order
        _log(worker_id, f"[HEALTH] Starting health activity — {len(activities)} activities, country={country}")
        shuffled = list(activities)
        random.shuffle(shuffled)
        activities_done = 0
        activity_log = []

        for act_id in shuffled:
            entry = ACTIVITY_MAP.get(act_id)
            if not entry:
                _log(worker_id, f"[HEALTH] Unknown activity: {act_id}, skipping")
                continue
            fn, variant = entry
            try:
                _log(worker_id, f"[HEALTH] Activity {activities_done + 1}: {act_id}")
                # Use activity-specific query pool if available (country-aware)
                # Priority: country-specific queries > general English queries > country general pool
                specific_q = None
                if fn == _google_search:
                    q_pool = None
                    country_queries = _ACTIVITY_QUERIES_BY_COUNTRY.get(country)
                    if country_queries and act_id in country_queries:
                        q_pool = country_queries[act_id]
                    elif act_id in ACTIVITY_QUERIES:
                        q_pool = ACTIVITY_QUERIES[act_id]
                    if q_pool:
                        specific_q = random.choice(q_pool)
                if specific_q is not None:
                    await fn(page, worker_id, country=country, query=specific_q)
                else:
                    await fn(page, worker_id, country=country)
                activities_done += 1
                activity_log.append(act_id)
            except Exception as e:
                _log(worker_id, f"[HEALTH] Activity {act_id} error: {e}")

            # Human-like pause between activities
            pause = random.uniform(5.0, 20.0)
            await asyncio.sleep(pause)

        _log(worker_id, f"[HEALTH] Complete — {activities_done}/{len(activities)} activities done")
        return {
            'success': True,
            'activities_done': activities_done,
            'activity_log': activity_log,
        }
    else:
        # Legacy duration-based mode
        _log(worker_id, f"[HEALTH] Starting health activity — {duration_minutes} min, country={country}")
        end_time = time.time() + (duration_minutes * 60)
        activities_done = 0
        activity_log = []

        while time.time() < end_time:
            activity_fn = random.choice(ALL_ACTIVITIES)
            activity_name = activity_fn.__name__.lstrip('_')

            try:
                _log(worker_id, f"[HEALTH] Activity {activities_done + 1}: {activity_name}")
                await activity_fn(page, worker_id, country=country)
                activities_done += 1
                activity_log.append(activity_name)
            except Exception as e:
                _log(worker_id, f"[HEALTH] Activity {activity_name} error: {e}")

            if time.time() < end_time:
                pause = random.uniform(5.0, 20.0)
                remaining = end_time - time.time()
                actual_pause = min(pause, max(remaining, 0))
                if actual_pause > 0:
                    await asyncio.sleep(actual_pause)

        _log(worker_id, f"[HEALTH] Complete — {activities_done} activities done in ~{duration_minutes} min")
        return {
            'success': True,
            'activities_done': activities_done,
            'activity_log': activity_log,
            'duration_minutes': duration_minutes,
        }
