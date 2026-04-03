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
    'ES': [
        "mejores restaurantes cerca de mí", "el tiempo hoy", "últimas noticias españa",
        "receta paella valenciana", "cómo hacer tortilla española", "mejores películas 2025",
        "móviles baratos y buenos", "rutina de ejercicios en casa", "desayuno saludable ideas",
        "cafeterías en madrid", "resultados la liga", "rutas de senderismo españa",
        "cursos online gratis", "cómo ahorrar dinero rápido", "mejores playas españa",
        "recetas fáciles para cenar", "mejores portátiles calidad precio", "cómo hacer un currículum",
        "podcasts en español populares", "ideas despacho en casa", "zapatillas running baratas",
        "recetas de batidos", "museos en españa", "consejos para viajar",
        "horarios renfe", "precio gasolina hoy", "ofertas amazon españa",
        "tapas recetas caseras", "plan de pensiones", "lotería nacional resultados",
    ],
    'IT': [
        "migliori ristoranti vicino a me", "meteo oggi", "ultime notizie italia",
        "ricetta pasta carbonara", "come fare la pizza in casa", "migliori film 2025",
        "smartphone economici migliori", "esercizi a casa", "colazione sana idee",
        "caffè a roma", "risultati serie a", "sentieri trekking italia",
        "corsi online gratuiti", "come risparmiare soldi", "migliori spiagge italia",
        "ricette facili per cena", "migliori computer portatili", "come scrivere un curriculum",
        "podcast italiani popolari", "arredamento ufficio casa", "scarpe da corsa migliori",
        "ricette frullati", "musei in italia", "consigli di viaggio",
        "orari treni trenitalia", "prezzo benzina oggi", "offerte amazon italia",
        "ricetta tiramisù originale", "ricetta risotto ai funghi", "programmi tv stasera",
    ],
    'PT': [
        "melhores restaurantes perto de mim", "previsão do tempo hoje", "últimas notícias portugal",
        "receita bacalhau à brás", "como fazer pastéis de nata", "melhores filmes 2025",
        "telemóveis baratos e bons", "exercícios em casa", "pequeno almoço saudável",
        "cafés em lisboa", "resultados primeira liga", "trilhos pedestres portugal",
        "cursos online gratuitos", "como poupar dinheiro", "melhores praias portugal",
        "receitas fáceis para jantar", "melhores computadores portáteis", "como fazer currículo",
        "podcasts em português", "ideias escritório em casa", "sapatilhas corrida baratas",
        "receitas de batidos", "museus em portugal", "dicas de viagem",
        "horários comboios cp", "preço gasolina hoje", "promoções continente",
        "receita francesinha porto", "receita caldo verde", "programa tv hoje",
    ],
    'PL': [
        "najlepsze restauracje w pobliżu", "pogoda dzisiaj", "najnowsze wiadomości polska",
        "przepis na pierogi", "jak zrobić bigos", "najlepsze filmy 2025",
        "tanie telefony dobre", "ćwiczenia w domu", "zdrowe śniadanie pomysły",
        "kawiarnie w warszawie", "wyniki ekstraklasa", "szlaki turystyczne polska",
        "kursy online za darmo", "jak oszczędzać pieniądze", "najlepsze plaże polska",
        "łatwe przepisy na kolację", "najlepsze laptopy do 3000 zł", "jak napisać cv",
        "podcasty po polsku", "pomysły na biuro w domu", "buty do biegania ranking",
        "przepisy na koktajle", "muzea w polsce", "porady podróżnicze",
        "rozkład jazdy pkp", "cena benzyny dzisiaj", "promocje allegro",
        "przepis na żurek", "przepis na sernik", "program tv dzisiaj",
    ],
    'NL': [
        "beste restaurants bij mij in de buurt", "weer vandaag", "laatste nieuws nederland",
        "recept stamppot", "hoe maak je pannenkoeken", "beste films 2025",
        "goedkope telefoons", "oefeningen thuis", "gezond ontbijt ideeën",
        "cafés in amsterdam", "eredivisie uitslagen", "wandelroutes nederland",
        "gratis online cursussen", "hoe geld besparen", "beste stranden nederland",
        "makkelijke recepten avondeten", "beste laptops onder 500 euro", "hoe schrijf je een cv",
        "populaire podcasts nederlands", "thuiswerken inrichten", "hardloopschoenen test",
        "smoothie recepten", "musea in nederland", "reistips",
        "ns treinreizen", "benzineprijs vandaag", "aanbiedingen bol.com",
        "recept bitterballen", "recept appeltaart", "tv gids vanavond",
    ],
    'RU': [
        "лучшие рестораны рядом", "погода сегодня", "последние новости россия",
        "рецепт борща", "как приготовить пельмени", "лучшие фильмы 2025",
        "недорогие смартфоны", "упражнения дома", "здоровый завтрак идеи",
        "кафе в москве", "результаты рпл", "маршруты для походов россия",
        "бесплатные онлайн курсы", "как экономить деньги", "лучшие пляжи россии",
        "простые рецепты на ужин", "лучшие ноутбуки до 50000 рублей", "как составить резюме",
        "подкасты на русском", "идеи для домашнего офиса", "кроссовки для бега рейтинг",
        "рецепты смузи", "музеи в россии", "советы путешественникам",
        "расписание поездов ржд", "цена бензина сегодня", "скидки на озон",
        "рецепт оливье", "рецепт блинов", "программа тв сегодня",
    ],
    'JP': [
        "近くのおすすめレストラン", "今日の天気", "最新ニュース 日本",
        "カレーライス レシピ", "ラーメン 作り方", "おすすめ映画 2025",
        "安いスマートフォン おすすめ", "自宅でできる運動", "健康的な朝食 アイデア",
        "東京 カフェ おすすめ", "Jリーグ 結果", "日本 ハイキングコース",
        "無料オンライン講座", "お金を貯める方法", "日本 おすすめビーチ",
        "簡単 夕食レシピ", "おすすめノートパソコン", "履歴書の書き方",
        "人気ポッドキャスト 日本語", "ホームオフィス インテリア", "ランニングシューズ おすすめ",
        "スムージー レシピ", "日本の美術館", "旅行 アドバイス",
        "新幹線 時刻表", "ガソリン 価格 今日", "アマゾン セール",
        "お好み焼き レシピ", "味噌汁 作り方", "今日のテレビ番組",
    ],
    'KR': [
        "근처 맛집 추천", "오늘 날씨", "최신 뉴스 한국",
        "김치찌개 레시피", "불고기 만드는 법", "추천 영화 2025",
        "가성비 스마트폰 추천", "집에서 할 수 있는 운동", "건강한 아침식사 아이디어",
        "서울 카페 추천", "K리그 결과", "한국 등산 코스 추천",
        "무료 온라인 강좌", "돈 모으는 방법", "한국 해수욕장 추천",
        "간단한 저녁 레시피", "추천 노트북 가성비", "이력서 작성법",
        "인기 팟캐스트 한국어", "홈오피스 인테리어", "러닝화 추천",
        "스무디 레시피", "한국 박물관 추천", "여행 팁",
        "KTX 시간표", "오늘 기름값", "쿠팡 세일",
        "떡볶이 레시피", "된장찌개 만드는 법", "오늘 TV 편성표",
    ],
    'MX': [
        "mejores restaurantes cerca de mí", "clima hoy", "últimas noticias méxico",
        "receta tacos al pastor", "cómo hacer mole poblano", "mejores películas 2025",
        "celulares baratos y buenos", "rutina de ejercicio en casa", "desayuno saludable ideas",
        "cafeterías en cdmx", "resultados liga mx", "rutas de senderismo méxico",
        "cursos en línea gratis", "cómo ahorrar dinero", "mejores playas méxico",
        "recetas fáciles para cenar", "mejores laptops calidad precio", "cómo hacer un currículum",
        "podcasts en español méxico", "ideas oficina en casa", "tenis para correr baratos",
        "recetas de licuados", "museos en méxico", "tips para viajar",
        "precio gasolina hoy", "ofertas mercado libre", "receta enchiladas verdes",
        "receta pozole rojo", "receta chilaquiles", "programación tv hoy",
    ],
    'AR': [
        "mejores restaurantes cerca de mí", "clima hoy", "últimas noticias argentina",
        "receta empanadas argentinas", "cómo hacer asado", "mejores películas 2025",
        "celulares baratos y buenos", "rutina de ejercicios en casa", "desayuno saludable ideas",
        "cafeterías en buenos aires", "resultados liga profesional", "rutas de senderismo argentina",
        "cursos online gratis", "cómo ahorrar plata", "mejores playas argentina",
        "recetas fáciles para cenar", "mejores notebooks calidad precio", "cómo hacer un cv",
        "podcasts en español argentina", "ideas oficina en casa", "zapatillas running baratas",
        "recetas de licuados", "museos en argentina", "tips para viajar",
        "precio nafta hoy", "ofertas mercado libre", "receta milanesas napolitana",
        "receta locro argentino", "receta alfajores", "programación tv hoy",
    ],
    'SA': [
        "أفضل المطاعم القريبة", "حالة الطقس اليوم", "آخر الأخبار السعودية",
        "طريقة عمل الكبسة", "طريقة عمل المندي", "أفضل الأفلام 2025",
        "أفضل الجوالات الرخيصة", "تمارين رياضية في المنزل", "أفكار فطور صحي",
        "مقاهي في الرياض", "نتائج الدوري السعودي", "أماكن سياحية في السعودية",
        "دورات مجانية عبر الإنترنت", "كيف توفر المال", "أفضل الشواطئ في السعودية",
        "وصفات عشاء سهلة", "أفضل اللابتوبات", "كيف تكتب سيرة ذاتية",
        "بودكاست عربي", "أفكار مكتب منزلي", "أحذية جري مريحة",
        "وصفات سموذي", "متاحف السعودية", "نصائح سفر",
        "سعر البنزين اليوم", "عروض نون", "طريقة عمل الجريش",
        "طريقة عمل المطبق", "وصفات حلويات سهلة", "برامج التلفزيون اليوم",
    ],
    'AE': [
        "أفضل المطاعم القريبة", "حالة الطقس اليوم", "آخر الأخبار الإمارات",
        "طريقة عمل المچبوس", "طريقة عمل اللقيمات", "أفضل الأفلام 2025",
        "أفضل الجوالات الرخيصة", "تمارين رياضية في المنزل", "أفكار فطور صحي",
        "مقاهي في دبي", "نتائج الدوري الإماراتي", "أماكن سياحية في الإمارات",
        "دورات مجانية عبر الإنترنت", "كيف توفر المال", "أفضل الشواطئ في دبي",
        "وصفات عشاء سهلة", "أفضل اللابتوبات", "كيف تكتب سيرة ذاتية",
        "بودكاست عربي شهير", "أفكار مكتب منزلي", "أحذية جري مريحة",
        "وصفات سموذي", "متاحف الإمارات", "نصائح سفر",
        "سعر البنزين اليوم دبي", "عروض نون الإمارات", "طريقة عمل الهريس",
        "طريقة عمل البلاليط", "وصفات حلويات إماراتية", "برامج التلفزيون اليوم",
    ],
    'EG': [
        "أفضل المطاعم القريبة", "حالة الطقس اليوم", "آخر الأخبار مصر",
        "طريقة عمل الكشري", "طريقة عمل الملوخية", "أفضل الأفلام 2025",
        "أفضل الموبايلات الرخيصة", "تمارين رياضية في البيت", "أفكار فطار صحي",
        "كافيهات في القاهرة", "نتائج الدوري المصري", "أماكن سياحية في مصر",
        "كورسات مجانية أونلاين", "إزاي توفر فلوس", "أحسن شواطئ في مصر",
        "وصفات عشاء سهلة", "أحسن لابتوب", "إزاي تكتب سي في",
        "بودكاست عربي مصري", "أفكار مكتب في البيت", "جزم جري مريحة",
        "وصفات سموذي", "متاحف مصر", "نصائح سفر",
        "سعر البنزين النهاردة", "عروض جوميا", "طريقة عمل الفتة المصرية",
        "طريقة عمل أم علي", "وصفات حلويات سهلة", "برامج التلفزيون النهاردة",
    ],
    'NG': [
        "best restaurants near me", "weather forecast today", "latest news nigeria",
        "jollof rice recipe", "how to make egusi soup", "best nollywood movies 2025",
        "best budget phones nigeria", "home workout routine", "healthy breakfast ideas",
        "best cafes in lagos", "premier league results", "tourist attractions nigeria",
        "free online courses", "how to save money naira", "best beaches nigeria",
        "easy dinner recipes nigerian", "best laptops under 300k naira", "how to write a cv",
        "popular podcasts nigeria", "home office ideas", "best running shoes",
        "smoothie recipes", "museums in lagos", "travel tips nigeria",
        "fuel price today", "jumia deals today", "suya recipe",
        "pounded yam recipe", "chin chin recipe", "tv schedule today",
    ],
    'ZA': [
        "best restaurants near me", "weather forecast today", "latest news south africa",
        "braai recipes", "bobotie recipe", "best movies 2025",
        "best budget phones south africa", "home workout routine", "healthy breakfast ideas",
        "best coffee shops cape town", "psl results today", "hiking trails south africa",
        "free online courses", "how to save money rands", "best beaches south africa",
        "easy dinner recipes", "best laptops under 10000 rand", "how to write a cv south africa",
        "popular podcasts south africa", "home office ideas", "best running shoes",
        "smoothie recipes", "museums in south africa", "travel tips south africa",
        "petrol price today", "takealot deals", "biltong recipe",
        "melktert recipe", "koeksister recipe", "tv schedule today",
    ],
    'AU': [
        "best restaurants near me", "weather forecast today", "latest news australia",
        "meat pie recipe", "lamington recipe", "best movies 2025",
        "best budget phones australia", "morning workout routine", "healthy breakfast ideas",
        "best coffee shops melbourne", "afl results today", "hiking trails australia",
        "free online courses australia", "how to save money fast", "best beaches australia",
        "easy dinner recipes", "best laptops under 1000 aud", "how to write a resume australia",
        "best podcasts 2025", "home office setup ideas", "best running shoes australia",
        "smoothie recipes", "museums in sydney", "travel tips australia",
        "woolworths specials", "petrol prices today", "bunnings hardware",
        "tim tam recipe", "pavlova recipe", "tv guide tonight",
    ],
    'CA': [
        "best restaurants near me", "weather forecast today", "latest news canada",
        "poutine recipe", "butter tart recipe", "best movies 2025",
        "best budget phones canada", "morning workout routine", "healthy breakfast ideas",
        "best coffee shops toronto", "nhl scores today", "hiking trails canada",
        "free online courses canada", "how to save money canada", "best beaches canada",
        "easy dinner recipes", "best laptops under 1000 cad", "how to write a resume canada",
        "best podcasts 2025", "home office setup ideas", "best running shoes canada",
        "smoothie recipes", "museums in ottawa", "travel tips canada",
        "gas prices today", "canadian tire deals", "shoppers drug mart flyer",
        "nanaimo bar recipe", "tourtiere recipe", "cbc schedule tonight",
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
    'ES': [
        "Sagrada Familia Barcelona", "Alhambra Granada", "Plaza Mayor Madrid",
        "Mezquita Córdoba", "Parque Güell Barcelona", "Museo del Prado Madrid",
        "Catedral Sevilla", "Acueducto Segovia", "Santiago de Compostela",
        "San Sebastián Playa", "Tenerife Teide", "Mallorca Palma",
    ],
    'IT': [
        "Colosseo Roma", "Piazza San Marco Venezia", "Duomo di Milano",
        "Torre di Pisa", "Ponte Vecchio Firenze", "Fontana di Trevi Roma",
        "Costiera Amalfitana", "Pompei Scavi", "Vaticano Roma",
        "Cinque Terre Liguria", "Lago di Como", "Piazza del Campo Siena",
    ],
    'PT': [
        "Torre de Belém Lisboa", "Ponte Dom Luís Porto", "Palácio da Pena Sintra",
        "Praça do Comércio Lisboa", "Mosteiro dos Jerónimos", "Cabo da Roca",
        "Universidade de Coimbra", "Algarve Faro", "Braga Bom Jesus",
        "Ribeira Porto", "Évora Templo Romano", "Madeira Funchal",
    ],
    'PL': [
        "Rynek Główny Kraków", "Zamek Królewski Warszawa", "Wawel Kraków",
        "Stare Miasto Gdańsk", "Auschwitz Oświęcim", "Kopalnia Soli Wieliczka",
        "Łazienki Królewskie Warszawa", "Malbork Zamek", "Tatry Zakopane",
        "Wrocław Rynek", "Poznań Stary Rynek", "Toruń Stare Miasto",
    ],
    'NL': [
        "Rijksmuseum Amsterdam", "Anne Frank Huis Amsterdam", "Vondelpark Amsterdam",
        "Keukenhof Lisse", "Kinderdijk Windmills", "Van Gogh Museum Amsterdam",
        "Dam Square Amsterdam", "Mauritshuis Den Haag", "Markthal Rotterdam",
        "Utrecht Domtoren", "Maastricht Vrijthof", "Giethoorn Village",
    ],
    'RU': [
        "Красная площадь Москва", "Эрмитаж Санкт-Петербург", "Кремль Москва",
        "Петергоф", "Храм Василия Блаженного", "Дворцовая площадь",
        "Байкал озеро", "Невский проспект", "Третьяковская галерея",
        "Казанский Кремль", "Мамаев курган Волгоград", "Сочи набережная",
    ],
    'JP': [
        "東京タワー", "浅草寺 東京", "京都 金閣寺",
        "富士山", "大阪城", "厳島神社 広島",
        "東京スカイツリー", "奈良 東大寺", "渋谷スクランブル交差点",
        "清水寺 京都", "沖縄 美ら海水族館", "札幌 時計台",
    ],
    'KR': [
        "경복궁 서울", "남산타워 서울", "해운대 해수욕장 부산",
        "제주도 한라산", "광화문 광장", "불국사 경주",
        "명동 서울", "인사동 서울", "한옥마을 전주",
        "동대문 디자인 플라자", "성산일출봉 제주", "북촌 한옥마을",
    ],
    'MX': [
        "Chichén Itzá Yucatán", "Teotihuacán México", "Zócalo Ciudad de México",
        "Cancún Playa", "Frida Kahlo Museum CDMX", "Tulum Ruins",
        "Guadalajara Centro", "Oaxaca Centro", "San Miguel de Allende",
        "Palacio de Bellas Artes CDMX", "Puerto Vallarta", "Playa del Carmen",
    ],
    'AR': [
        "Obelisco Buenos Aires", "Caminito La Boca", "Plaza de Mayo Buenos Aires",
        "Glaciar Perito Moreno", "Cataratas del Iguazú", "Teatro Colón Buenos Aires",
        "Bariloche Centro Cívico", "Mendoza Viñedos", "Ushuaia Fin del Mundo",
        "Quebrada de Humahuaca", "Recoleta Cementerio", "Puerto Madero Buenos Aires",
    ],
    'SA': [
        "الحرم المكي مكة", "المسجد النبوي المدينة", "برج المملكة الرياض",
        "واجهة الرياض", "العلا مدائن صالح", "جدة البلد التاريخية",
        "الدرعية التاريخية", "حافة العالم الرياض", "كورنيش جدة",
        "جزيرة فرسان", "أبها السودة", "ينبع الشاطئ",
    ],
    'AE': [
        "برج خليفة دبي", "متحف اللوفر أبوظبي", "نخلة جميرا دبي",
        "دبي مول", "مسجد الشيخ زايد أبوظبي", "برج العرب دبي",
        "القرية العالمية دبي", "عين دبي", "جزيرة ياس أبوظبي",
        "خور دبي", "سوق الذهب دبي", "مارينا دبي",
    ],
    'EG': [
        "أهرامات الجيزة", "معبد الكرنك الأقصر", "المتحف المصري القاهرة",
        "وادي الملوك الأقصر", "الإسكندرية قلعة قايتباي", "أبو سمبل أسوان",
        "خان الخليلي القاهرة", "شرم الشيخ", "الغردقة البحر الأحمر",
        "مسجد محمد علي القاهرة", "واحة سيوة", "دهب سيناء",
    ],
    'NG': [
        "Lekki Conservation Centre Lagos", "Nike Art Gallery Lagos", "Olumo Rock Abeokuta",
        "National Museum Lagos", "Yankari Game Reserve", "Zuma Rock Abuja",
        "Aso Rock Abuja", "Osun-Osogbo Sacred Grove", "Obudu Mountain Resort",
        "Tarkwa Bay Beach Lagos", "Millennium Park Abuja", "Tinapa Resort Calabar",
    ],
    'ZA': [
        "Table Mountain Cape Town", "Kruger National Park", "V&A Waterfront Cape Town",
        "Robben Island", "Johannesburg Apartheid Museum", "Blyde River Canyon",
        "Garden Route", "Durban Beachfront", "Stellenbosch Wine Route",
        "Drakensberg Mountains", "Pilanesberg National Park", "Addo Elephant Park",
    ],
    'AU': [
        "Sydney Opera House", "Great Barrier Reef Queensland", "Uluru Ayers Rock",
        "Sydney Harbour Bridge", "Melbourne Federation Square", "Blue Mountains NSW",
        "Bondi Beach Sydney", "Twelve Apostles Victoria", "Kakadu National Park",
        "Daintree Rainforest", "Perth Kings Park", "Hobart MONA",
    ],
    'CA': [
        "Niagara Falls Ontario", "CN Tower Toronto", "Banff National Park",
        "Old Montreal Quebec", "Stanley Park Vancouver", "Parliament Hill Ottawa",
        "Whistler BC", "Peggy's Cove Nova Scotia", "Lake Louise Alberta",
        "Signal Hill Newfoundland", "Quebec City Old Town", "Butchart Gardens Victoria",
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
    'ES': [
        "música relajante", "receta cocina española", "vlog viaje españa",
        "análisis tecnología 2025", "tutorial dibujo", "videos graciosos animales",
        "experimento ciencia", "ejercicios en casa", "clase guitarra principiante",
        "documental naturaleza españa", "resumen la liga", "maquillaje tutorial español",
    ],
    'IT': [
        "musica rilassante", "ricetta cucina italiana", "vlog viaggio italia",
        "recensione tecnologia 2025", "tutorial disegno", "video divertenti animali",
        "esperimento scientifico", "allenamento a casa", "lezione chitarra principiante",
        "documentario natura italia", "serie a highlights", "tutorial trucco italiano",
    ],
    'PT': [
        "música relaxante", "receita culinária portuguesa", "vlog viagem portugal",
        "review tecnologia 2025", "tutorial desenho", "vídeos engraçados animais",
        "experiência científica", "treino em casa", "aula guitarra iniciante",
        "documentário natureza portugal", "liga portugal resumo", "maquilhagem tutorial",
    ],
    'PL': [
        "muzyka relaksacyjna", "przepis kuchnia polska", "vlog podróże polska",
        "recenzja technologia 2025", "tutorial rysowanie", "śmieszne filmy ze zwierzętami",
        "eksperyment naukowy", "ćwiczenia w domu", "lekcja gitary dla początkujących",
        "dokument przyrodniczy polska", "ekstraklasa skróty", "makijaż tutorial polski",
    ],
    'NL': [
        "ontspannende muziek", "recept Nederlandse keuken", "vlog reizen nederland",
        "tech review 2025 nederlands", "teken tutorial", "grappige dierenvideo's",
        "wetenschappelijk experiment", "thuis sporten", "gitaarles beginners",
        "natuurdocumentaire nederland", "eredivisie samenvatting", "make-up tutorial nederlands",
    ],
    'RU': [
        "расслабляющая музыка", "рецепт русская кухня", "влог путешествие россия",
        "обзор технологий 2025", "урок рисования", "смешные видео с животными",
        "научный эксперимент", "тренировка дома", "урок гитары для начинающих",
        "документальный фильм природа", "рпл обзор матча", "макияж урок русский",
    ],
    'JP': [
        "リラックス音楽", "和食 レシピ 作り方", "旅行Vlog 日本",
        "テック レビュー 2025", "イラスト 描き方", "面白い動物動画",
        "科学実験", "自宅トレーニング", "ギター 初心者レッスン",
        "自然ドキュメンタリー 日本", "Jリーグ ハイライト", "メイク チュートリアル",
    ],
    'KR': [
        "편안한 음악", "한국 요리 레시피", "여행 브이로그 한국",
        "테크 리뷰 2025", "그림 그리기 튜토리얼", "재미있는 동물 영상",
        "과학 실험", "홈트레이닝", "기타 초보 레슨",
        "자연 다큐멘터리 한국", "K리그 하이라이트", "메이크업 튜토리얼 한국",
    ],
    'MX': [
        "música relajante", "receta comida mexicana", "vlog viaje méxico",
        "review tecnología 2025", "tutorial dibujo", "videos graciosos de animales",
        "experimento de ciencia", "ejercicio en casa", "clase de guitarra principiante",
        "documental naturaleza méxico", "liga mx resumen", "maquillaje tutorial mexicano",
    ],
    'AR': [
        "música relajante", "receta comida argentina", "vlog viaje argentina",
        "review tecnología 2025", "tutorial de dibujo", "videos graciosos de animales",
        "experimento de ciencia", "ejercicio en casa", "clase de guitarra principiante",
        "documental naturaleza argentina", "liga profesional resumen", "maquillaje tutorial",
    ],
    'SA': [
        "موسيقى هادئة", "وصفة طبخ سعودي", "فلوق سفر السعودية",
        "مراجعة تقنية 2025", "تعليم الرسم", "فيديوهات حيوانات مضحكة",
        "تجربة علمية", "تمارين في البيت", "تعليم العود للمبتدئين",
        "وثائقي طبيعة", "دوري روشن ملخص", "مكياج تعليمي عربي",
    ],
    'AE': [
        "موسيقى هادئة", "وصفة طبخ إماراتي", "فلوق سفر الإمارات",
        "مراجعة تقنية 2025", "تعليم الرسم", "فيديوهات حيوانات مضحكة",
        "تجربة علمية", "تمارين في البيت", "تعليم الجيتار للمبتدئين",
        "وثائقي طبيعة", "الدوري الإماراتي ملخص", "مكياج تعليمي",
    ],
    'EG': [
        "موسيقى هادئة", "وصفة أكل مصري", "فلوق سفر مصر",
        "مراجعة موبايلات 2025", "تعليم رسم", "فيديوهات حيوانات مضحكة",
        "تجربة علمية", "تمارين في البيت", "تعلم جيتار للمبتدئين",
        "وثائقي طبيعة مصر", "الدوري المصري ملخص", "ميكب توتوريال",
    ],
    'NG': [
        "afrobeats music", "nigerian cooking recipe", "travel vlog nigeria",
        "tech review 2025 nigeria", "drawing tutorial", "funny nigerian videos",
        "science experiment", "home workout", "guitar lesson beginner",
        "wildlife documentary africa", "premier league highlights", "makeup tutorial nigerian",
    ],
    'ZA': [
        "relaxing music", "south african cooking recipe", "travel vlog south africa",
        "tech review 2025", "drawing tutorial", "funny animal videos south africa",
        "science experiment", "home workout routine", "guitar lesson beginner",
        "nature documentary south africa", "psl highlights", "makeup tutorial south african",
    ],
    'AU': [
        "relaxing music", "australian cooking recipe", "travel vlog australia",
        "tech review 2025", "drawing tutorial", "funny animal videos australia",
        "science experiment", "home workout", "guitar lesson beginner",
        "nature documentary australia", "afl highlights", "makeup tutorial australian",
    ],
    'CA': [
        "relaxing music", "canadian cooking recipe", "travel vlog canada",
        "tech review 2025", "drawing tutorial", "funny animal videos",
        "science experiment", "home workout", "guitar lesson beginner",
        "nature documentary canada", "nhl highlights", "makeup tutorial canadian",
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
    'ES': [
        "auriculares inalámbricos", "zapatillas running", "soporte portátil",
        "botella de agua", "lámpara escritorio", "mochila", "funda móvil",
        "cascos bluetooth", "webcam", "ratón inalámbrico", "teclado mecánico",
    ],
    'IT': [
        "auricolari wireless", "scarpe da corsa", "supporto laptop",
        "borraccia", "lampada scrivania", "zaino", "cover telefono",
        "cuffie bluetooth", "webcam", "mouse wireless", "tastiera meccanica",
    ],
    'PT': [
        "auriculares sem fios", "sapatilhas corrida", "suporte portátil",
        "garrafa de água", "candeeiro secretária", "mochila", "capa telemóvel",
        "auscultadores bluetooth", "webcam", "rato sem fios", "teclado mecânico",
    ],
    'PL': [
        "słuchawki bezprzewodowe", "buty do biegania", "podstawka pod laptopa",
        "butelka na wodę", "lampka biurkowa", "plecak", "etui na telefon",
        "słuchawki bluetooth", "kamerka internetowa", "myszka bezprzewodowa", "klawiatura mechaniczna",
    ],
    'NL': [
        "draadloze oordopjes", "hardloopschoenen", "laptop standaard",
        "waterfles", "bureaulamp", "rugzak", "telefoonhoesje",
        "koptelefoon bluetooth", "webcam", "draadloze muis", "mechanisch toetsenbord",
    ],
    'RU': [
        "беспроводные наушники", "кроссовки для бега", "подставка для ноутбука",
        "бутылка для воды", "настольная лампа", "рюкзак", "чехол для телефона",
        "наушники bluetooth", "веб камера", "беспроводная мышь", "механическая клавиатура",
    ],
    'JP': [
        "ワイヤレスイヤホン", "ランニングシューズ", "ノートパソコンスタンド",
        "水筒", "デスクライト", "リュックサック", "スマホケース",
        "ヘッドフォン", "ウェブカメラ", "ワイヤレスマウス", "メカニカルキーボード",
    ],
    'KR': [
        "무선 이어폰", "러닝화", "노트북 거치대",
        "물병", "책상 조명", "백팩", "핸드폰 케이스",
        "블루투스 헤드폰", "웹캠", "무선 마우스", "기계식 키보드",
    ],
    'MX': [
        "audífonos inalámbricos", "tenis para correr", "soporte para laptop",
        "botella de agua", "lámpara de escritorio", "mochila", "funda celular",
        "audífonos bluetooth", "webcam", "mouse inalámbrico", "teclado mecánico",
    ],
    'AR': [
        "auriculares inalámbricos", "zapatillas running", "soporte notebook",
        "botella de agua", "lámpara escritorio", "mochila", "funda celular",
        "auriculares bluetooth", "webcam", "mouse inalámbrico", "teclado mecánico",
    ],
    'SA': [
        "سماعات بلوتوث", "حذاء جري", "حامل لابتوب",
        "قارورة ماء", "مصباح مكتب", "حقيبة ظهر", "كفر جوال",
        "سماعات رأس", "كاميرا ويب", "ماوس لاسلكي", "كيبورد ميكانيكي",
    ],
    'AE': [
        "سماعات بلوتوث", "حذاء رياضي", "حامل لابتوب",
        "قارورة ماء", "مصباح مكتبي", "شنطة ظهر", "كفر موبايل",
        "سماعات رأس", "كاميرا ويب", "ماوس لاسلكي", "كيبورد ميكانيكي",
    ],
    'EG': [
        "سماعات بلوتوث", "جزمة جري", "حامل لاب توب",
        "زجاجة مية", "لمبة مكتب", "شنطة ضهر", "جراب موبايل",
        "سماعات هيدفون", "كاميرا ويب", "ماوس وايرلس", "كيبورد ميكانيكال",
    ],
    'NG': [
        "wireless earbuds", "running shoes nigeria", "laptop stand",
        "water bottle", "desk lamp", "backpack", "phone case",
        "headphones", "webcam", "power bank", "smartwatch",
    ],
    'ZA': [
        "wireless earbuds south africa", "running shoes", "laptop stand",
        "water bottle", "desk lamp", "backpack", "phone case",
        "headphones", "webcam", "power bank", "smartwatch",
    ],
    'AU': [
        "wireless earbuds australia", "running shoes", "laptop stand",
        "water bottle", "desk lamp", "backpack", "phone case",
        "headphones", "webcam", "mechanical keyboard", "smartwatch",
    ],
    'CA': [
        "wireless earbuds canada", "running shoes", "laptop stand",
        "water bottle", "desk lamp", "backpack", "phone case",
        "headphones", "webcam", "mechanical keyboard", "smartwatch",
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


async def _visit_contacts(page, worker_id, country='US', variant=''):
    """Visit Google Contacts."""
    try:
        await page.goto('https://contacts.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(200, 500))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_blogger(page, worker_id, country='US', variant=''):
    """Visit Blogger."""
    try:
        await page.goto('https://www.blogger.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(100, 400))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_sites(page, worker_id, country='US', variant=''):
    """Visit Google Sites."""
    try:
        await page.goto('https://sites.google.com', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


async def _visit_forms(page, worker_id, country='US', variant=''):
    """Visit Google Forms."""
    try:
        await page.goto('https://docs.google.com/forms', timeout=15000)
        await asyncio.sleep(random.uniform(2, 4))
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(1, 3))
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Activity: Custom GMB (Google My Business) browsing
# ─────────────────────────────────────────────────────────────────────────────

async def _custom_gmb_activity(page, worker_id, gmb_name='', gmb_address='', country='US'):
    """
    Simulate organic local search behaviour around a specific business.

    Steps:
      1. Google-search the business name, click results, browse.
      2. Search "[business name] [address]" on Google Maps.
      3. Search generic categories ("restaurants near [address]", etc.) on Maps.
      4. Browse nearby places on Maps.
      5. Run 5-8 varied search queries around the business location.
    """
    if not gmb_name:
        _log(worker_id, "[HEALTH] custom_gmb: no gmb_name provided, skipping")
        return

    address_part = gmb_address if gmb_address else ''
    _log(worker_id, f"[HEALTH] Custom GMB activity: '{gmb_name}' / '{address_part}'")

    # --- Step 1: Google-search the business name ---
    await _google_search(page, worker_id, country=country, query=gmb_name)
    await _human_delay(3.0, 6.0)

    # --- Step 2: Search business on Google Maps ---
    maps_query = f"{gmb_name} {address_part}".strip()
    _log(worker_id, f"[HEALTH] GMB Maps search: '{maps_query}'")
    if await _safe_goto(page, "https://www.google.com/maps", worker_id):
        try:
            search_box = page.locator('#searchboxinput').first
            if await search_box.count() > 0:
                await search_box.click()
                await _human_delay(0.5, 1.0)
                await search_box.fill(maps_query)
                await _human_delay(0.5, 1.0)
                await page.keyboard.press('Enter')
                await _human_delay(4.0, 8.0)
                await _human_scroll(page, random.randint(1, 3))
                await _human_delay(2.0, 4.0)
        except Exception:
            pass

    # --- Step 3: Search generic categories near the address ---
    if address_part:
        nearby_categories = ["restaurants", "shops", "cafes", "hotels", "pharmacies",
                             "gas stations", "banks", "gyms", "supermarkets", "parking"]
        chosen_cats = random.sample(nearby_categories, min(random.randint(2, 4), len(nearby_categories)))
        for cat in chosen_cats:
            cat_query = f"{cat} near {address_part}"
            _log(worker_id, f"[HEALTH] GMB nearby search: '{cat_query}'")
            if await _safe_goto(page, "https://www.google.com/maps", worker_id):
                try:
                    search_box = page.locator('#searchboxinput').first
                    if await search_box.count() > 0:
                        await search_box.click()
                        await _human_delay(0.5, 1.0)
                        await search_box.fill(cat_query)
                        await _human_delay(0.5, 1.0)
                        await page.keyboard.press('Enter')
                        await _human_delay(3.0, 6.0)
                        await _human_scroll(page, random.randint(1, 3))
                        await _human_delay(2.0, 4.0)

                        # Click a nearby place
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
                except Exception:
                    pass
            await _human_delay(2.0, 5.0)

    # --- Step 4: Varied search queries around the business ---
    query_templates = [
        f"{gmb_name} reviews",
        f"{gmb_name} opening hours",
        f"{gmb_name} contact",
        f"directions to {gmb_name}",
        f"{gmb_name} photos",
        f"best {gmb_name.split()[0] if gmb_name.split() else 'business'} near {address_part}",
        f"{gmb_name} menu" if random.random() > 0.5 else f"{gmb_name} services",
        f"things to do near {address_part}" if address_part else f"{gmb_name} location",
    ]
    num_queries = random.randint(5, 8)
    selected_queries = random.sample(query_templates, min(num_queries, len(query_templates)))
    for q in selected_queries:
        await _google_search(page, worker_id, country=country, query=q)
        await _human_delay(3.0, 8.0)

    _log(worker_id, f"[HEALTH] Custom GMB activity complete: '{gmb_name}'")


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
    'search_music':          ['best music 2025', 'new album releases', 'top songs this week', 'music playlist chill', 'best jazz albums', 'indie music 2025', 'classical music for studying', 'best rap albums 2025', 'how to read sheet music', 'music festivals 2025'],
    'search_gardening':      ['beginner gardening tips', 'how to grow tomatoes', 'indoor herb garden', 'composting for beginners', 'flower garden ideas', 'raised bed garden plans', 'best plants for shade', 'organic gardening tips', 'vegetable garden layout', 'when to plant seeds'],
    'search_photography':    ['photography tips beginners', 'best camera 2025', 'portrait photography tips', 'landscape photography settings', 'photo editing software free', 'smartphone photography tricks', 'night photography tips', 'composition rules photography', 'macro photography guide', 'best lenses for portraits'],
    'search_astronomy':      ['planets visible tonight', 'meteor shower schedule 2025', 'best telescope for beginners', 'astronomy news today', 'star map tonight', 'how to see milky way', 'solar eclipse 2025', 'james webb telescope images', 'constellation guide', 'astrophotography for beginners'],
    'search_history':        ['interesting history facts', 'ancient civilizations timeline', 'world war 2 summary', 'history documentaries best', 'famous historical figures', 'medieval history facts', 'history of the internet', 'ancient egypt facts', 'roman empire history', 'cold war summary'],
    'search_science':        ['science news today', 'interesting science experiments', 'latest scientific discoveries 2025', 'science for kids', 'quantum physics explained simply', 'climate science facts', 'biology fun facts', 'chemistry experiments home', 'space science news', 'science podcasts best'],
    'search_books':          ['best books 2025', 'book recommendations fiction', 'best self help books', 'new book releases', 'audiobook recommendations', 'best mystery novels', 'classic literature must read', 'best non fiction books', 'book club picks 2025', 'best fantasy series'],
    'search_art':            ['art exhibitions near me', 'famous paintings to know', 'digital art for beginners', 'art history timeline', 'how to draw portraits', 'watercolor painting tips', 'modern art explained', 'art museums virtual tour', 'best art supplies', 'street art cities'],
    'search_cooking':        ['cooking tips for beginners', 'easy recipes for dinner', 'how to meal prep', 'baking tips and tricks', 'best cooking youtube channels', 'kitchen gadgets worth buying', 'how to cook steak perfectly', 'cooking with cast iron', 'seasonal recipes spring', 'one pot meals easy'],
    'search_parenting':      ['parenting tips toddlers', 'baby sleep schedule', 'kids activities at home', 'healthy snacks for kids', 'screen time guidelines children', 'positive parenting techniques', 'baby milestones by month', 'kids education apps', 'family meal ideas', 'potty training tips'],
    'search_psychology':     ['psychology facts interesting', 'how to improve mental health', 'cognitive behavioral therapy basics', 'psychology of habits', 'emotional intelligence tips', 'mindfulness meditation guide', 'psychology of persuasion', 'how to manage anxiety', 'self improvement psychology', 'body language reading tips'],
    'search_philosophy':     ['philosophy for beginners', 'famous philosophical quotes', 'stoicism explained simply', 'existentialism summary', 'best philosophy books', 'philosophical questions to ponder', 'ethics philosophy basics', 'socrates teachings summary', 'eastern philosophy introduction', 'philosophy podcasts best'],
    'search_architecture':   ['famous architecture around the world', 'modern architecture trends 2025', 'sustainable architecture design', 'interior design ideas', 'house design plans', 'architecture styles guide', 'tiny house designs', 'building materials guide', 'gothic architecture history', 'famous architects and buildings'],
    'search_interior_design':['interior design ideas living room', 'minimalist home decor', 'small apartment design ideas', 'color schemes for rooms', 'furniture arrangement tips', 'home decoration trends 2025', 'kitchen design ideas modern', 'bathroom remodel ideas', 'bedroom design inspiration', 'home office design ideas'],
    'search_marketing':      ['digital marketing tips 2025', 'social media marketing strategy', 'seo tips for beginners', 'email marketing best practices', 'content marketing guide', 'google ads tutorial', 'brand building strategies', 'influencer marketing tips', 'marketing analytics tools', 'copywriting tips'],
    'search_startups':       ['how to start a startup', 'startup ideas 2025', 'venture capital explained', 'business plan template', 'startup funding stages', 'lean startup methodology', 'startup success stories', 'how to pitch investors', 'best startup books', 'startup accelerator programs'],
    'search_programming':    ['programming for beginners', 'best programming language 2025', 'python tutorial beginner', 'web development roadmap', 'javascript projects for beginners', 'coding bootcamp reviews', 'github projects trending', 'data structures algorithms', 'api development tutorial', 'best code editor 2025'],
    'search_ai':             ['artificial intelligence news 2025', 'chatgpt alternatives', 'machine learning for beginners', 'ai tools for productivity', 'ai art generators', 'deep learning explained', 'ai in healthcare', 'best ai apps 2025', 'ai ethics debate', 'how to learn ai'],
    'search_space':          ['space news today', 'nasa missions 2025', 'spacex launch schedule', 'mars exploration latest', 'international space station', 'black hole discoveries', 'exoplanets discovered', 'space tourism 2025', 'artemis moon mission', 'universe facts interesting'],
    'search_environment':    ['climate change solutions', 'renewable energy facts', 'recycling tips at home', 'sustainable living tips', 'electric vehicles comparison', 'carbon footprint calculator', 'plastic pollution solutions', 'green energy sources', 'environmental news today', 'how to reduce waste'],
    'search_politics':       ['political news today', 'election results 2025', 'government policies explained', 'how democracy works', 'political parties comparison', 'local government news', 'international relations news', 'political debates 2025', 'voting information', 'public policy changes'],
    'search_comedy':         ['best comedy movies 2025', 'funny videos compilation', 'stand up comedy specials', 'best comedy shows netflix', 'funny memes today', 'comedy podcasts best', 'sitcoms to binge watch', 'funny jokes clean', 'comedy clubs near me', 'best comedians 2025'],
    'search_podcasts':       ['best podcasts 2025', 'true crime podcasts', 'comedy podcasts popular', 'business podcasts top', 'science podcasts for curious minds', 'history podcasts best', 'how to start a podcast', 'podcast app best', 'new podcast releases', 'interview podcasts top'],
    'search_documentaries':  ['best documentaries 2025', 'nature documentaries netflix', 'true crime documentaries', 'history documentaries best', 'science documentaries must watch', 'space documentaries', 'food documentaries', 'social documentaries', 'music documentaries best', 'ocean documentaries'],
    'search_anime':          ['best anime 2025', 'anime recommendations action', 'new anime releases', 'anime streaming sites', 'top anime series all time', 'anime movies best rated', 'slice of life anime', 'anime news today', 'manga to anime adaptations', 'anime conventions 2025'],
    'search_manga':          ['best manga 2025', 'manga recommendations', 'new manga releases', 'manga online read', 'top manga series', 'shonen manga best', 'manga art style tutorial', 'manga vs anime differences', 'seinen manga top rated', 'manga apps best'],
    'search_board_games':    ['best board games 2025', 'board games for 2 players', 'strategy board games', 'family board games fun', 'board game cafe near me', 'new board game releases', 'cooperative board games', 'party board games', 'board game reviews', 'how to play catan'],
    'search_camping':        ['camping essentials checklist', 'best camping spots near me', 'camping gear reviews', 'camping recipes easy', 'tent camping tips beginners', 'camping with kids tips', 'best sleeping bag 2025', 'camping cooking equipment', 'national parks camping', 'winter camping tips'],
    'search_fishing':        ['fishing tips for beginners', 'best fishing spots near me', 'fishing gear essentials', 'fly fishing guide', 'bass fishing tips', 'fishing license how to get', 'best fishing rods 2025', 'fishing knots tutorial', 'saltwater fishing tips', 'ice fishing beginners'],
    'search_cycling':        ['cycling for beginners', 'best bikes 2025', 'cycling routes near me', 'road bike vs mountain bike', 'cycling gear essentials', 'bike maintenance tips', 'cycling training plan', 'best cycling apps', 'electric bike reviews', 'cycling safety tips'],
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
    # --- New Google Search activities ---
    'search_music':          (_google_search, 'music'),
    'search_gardening':      (_google_search, 'gardening'),
    'search_photography':    (_google_search, 'photography'),
    'search_astronomy':      (_google_search, 'astronomy'),
    'search_history':        (_google_search, 'history'),
    'search_science':        (_google_search, 'science'),
    'search_books':          (_google_search, 'books'),
    'search_art':            (_google_search, 'art'),
    'search_cooking':        (_google_search, 'cooking'),
    'search_parenting':      (_google_search, 'parenting'),
    'search_psychology':     (_google_search, 'psychology'),
    'search_philosophy':     (_google_search, 'philosophy'),
    'search_architecture':   (_google_search, 'architecture'),
    'search_interior_design':(_google_search, 'interior_design'),
    'search_marketing':      (_google_search, 'marketing'),
    'search_startups':       (_google_search, 'startups'),
    'search_programming':    (_google_search, 'programming'),
    'search_ai':             (_google_search, 'ai'),
    'search_space':          (_google_search, 'space'),
    'search_environment':    (_google_search, 'environment'),
    'search_politics':       (_google_search, 'politics'),
    'search_comedy':         (_google_search, 'comedy'),
    'search_podcasts':       (_google_search, 'podcasts'),
    'search_documentaries':  (_google_search, 'documentaries'),
    'search_anime':          (_google_search, 'anime'),
    'search_manga':          (_google_search, 'manga'),
    'search_board_games':    (_google_search, 'board_games'),
    'search_camping':        (_google_search, 'camping'),
    'search_fishing':        (_google_search, 'fishing'),
    'search_cycling':        (_google_search, 'cycling'),
    # --- New Gmail activities ---
    'gmail_compose_draft':   (_check_gmail, 'compose_draft'),
    'gmail_star_email':      (_check_gmail, 'star'),
    'gmail_labels':          (_check_gmail, 'labels'),
    'gmail_contacts':        (_check_gmail, 'contacts'),
    # --- New YouTube activities ---
    'youtube_gaming':        (_browse_youtube, 'gaming'),
    'youtube_cooking':       (_browse_youtube, 'cooking'),
    'youtube_news':          (_browse_youtube, 'news'),
    'youtube_education':     (_browse_youtube, 'education'),
    'youtube_tech_review':   (_browse_youtube, 'tech_review'),
    'youtube_vlogs':         (_browse_youtube, 'vlogs'),
    'youtube_sports':        (_browse_youtube, 'sports'),
    'youtube_music_playlist':(_browse_youtube, 'music_playlist'),
    'youtube_diy':           (_browse_youtube, 'diy'),
    'youtube_travel':        (_browse_youtube, 'travel'),
    'youtube_fitness':       (_browse_youtube, 'fitness'),
    'youtube_comedy':        (_browse_youtube, 'comedy'),
    'youtube_documentary':   (_browse_youtube, 'documentary'),
    'youtube_asmr':          (_browse_youtube, 'asmr'),
    # --- New Maps activities ---
    'maps_gas_stations':     (_browse_maps, 'gas_stations'),
    'maps_hotels':           (_browse_maps, 'hotels'),
    'maps_hospitals':        (_browse_maps, 'hospitals'),
    'maps_parks':            (_browse_maps, 'parks'),
    'maps_shopping_malls':   (_browse_maps, 'shopping_malls'),
    'maps_coffee_shops':     (_browse_maps, 'coffee_shops'),
    'maps_gyms':             (_browse_maps, 'gyms'),
    'maps_atms':             (_browse_maps, 'atms'),
    'maps_pharmacies':       (_browse_maps, 'pharmacies'),
    'maps_schools':          (_browse_maps, 'schools'),
    'maps_banks':            (_browse_maps, 'banks'),
    'maps_supermarkets':     (_browse_maps, 'supermarkets'),
    'maps_car_wash':         (_browse_maps, 'car_wash'),
    'maps_libraries':        (_browse_maps, 'libraries'),
    'maps_museums':          (_browse_maps, 'museums'),
    'maps_theaters':         (_browse_maps, 'theaters'),
    # --- New News activities ---
    'news_health':           (_browse_news, 'health'),
    'news_science':          (_browse_news, 'science'),
    'news_world':            (_browse_news, 'world'),
    'news_politics':         (_browse_news, 'politics'),
    'news_environment':      (_browse_news, 'environment'),
    'news_education':        (_browse_news, 'education'),
    # --- New Shopping activities ---
    'shopping_home':         (_browse_shopping, 'home'),
    'shopping_beauty':       (_browse_shopping, 'beauty'),
    'shopping_sports':       (_browse_shopping, 'sports'),
    'shopping_toys':         (_browse_shopping, 'toys'),
    'shopping_books':        (_browse_shopping, 'books'),
    'shopping_garden':       (_browse_shopping, 'garden'),
    'shopping_automotive':   (_browse_shopping, 'automotive'),
    'shopping_jewelry':      (_browse_shopping, 'jewelry'),
    # --- New Drive activities ---
    'drive_search':          (_visit_drive, 'search'),
    'drive_trash':           (_visit_drive, 'trash'),
    'drive_starred':         (_visit_drive, 'starred'),
    # --- New Account activities ---
    'account_storage':       (_visit_account, 'storage'),
    'account_payments':      (_visit_account, 'payments'),
    'account_data_export':   (_visit_account, 'data_export'),
    # --- New Photos activities ---
    'photos_favorites':      (_visit_photos, 'favorites'),
    'photos_archive':        (_visit_photos, 'archive'),
    'photos_trash':          (_visit_photos, 'trash'),
    # --- New Other Services ---
    'contacts_browse':       (_visit_contacts, 'browse'),
    'contacts_search':       (_visit_contacts, 'search'),
    'blogger_browse':        (_visit_blogger, 'browse'),
    'sites_browse':          (_visit_sites, 'browse'),
    'forms_browse':          (_visit_forms, 'browse'),
    # --- Custom GMB ---
    'custom_gmb':            (_custom_gmb_activity, 'gmb'),
}


async def gmail_health_activity(page, worker_id, duration_minutes=10, country='US',
                                activities=None, rounds=1,
                                gmb_name='', gmb_address=''):
    """
    Run random human-like activities.

    Args:
        page: Playwright page object (logged-in Google profile)
        worker_id: Worker number for logging
        duration_minutes: Legacy param — only used if activities is None (fallback)
        country: Country code for localized queries
        activities: List of activity IDs to run (round-robin, shuffled).
                    If None, falls back to timed duration_minutes mode.
        rounds: Number of times to repeat the full activity list (default 1).
        gmb_name: Business name for custom_gmb activity.
        gmb_address: Business address for custom_gmb activity.

    Returns:
        dict with success, activities_done, activity_log
    """
    if activities:
        # New mode: run each activity once per round in random order
        _log(worker_id, f"[HEALTH] Starting health activity — {len(activities)} activities x {rounds} round(s), country={country}")
        activities_done = 0
        activity_log = []

        for round_num in range(rounds):
            _log(worker_id, f"[HEALTH] === Round {round_num + 1}/{rounds} ===")
            shuffled = list(activities)
            random.shuffle(shuffled)

            for act_id in shuffled:
                entry = ACTIVITY_MAP.get(act_id)
                if not entry:
                    _log(worker_id, f"[HEALTH] Unknown activity: {act_id}, skipping")
                    continue
                fn, variant = entry
                try:
                    _log(worker_id, f"[HEALTH] Round {round_num + 1} — Activity {activities_done + 1}: {act_id}")
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

                    # Custom GMB gets special kwargs
                    if fn == _custom_gmb_activity:
                        await fn(page, worker_id, gmb_name=gmb_name,
                                 gmb_address=gmb_address, country=country)
                    elif specific_q is not None:
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

            if round_num < rounds - 1:
                inter_round_pause = random.uniform(10.0, 30.0)
                _log(worker_id, f"[HEALTH] Pausing {inter_round_pause:.0f}s between rounds")
                await asyncio.sleep(inter_round_pause)

        total_expected = len(activities) * rounds
        _log(worker_id, f"[HEALTH] Complete — {activities_done}/{total_expected} activities done across {rounds} round(s)")
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
