import requests
import time
import os

API_KEY = 'YOUR_STEAM_API_KEY'  # Remplacez par votre clé API Steam

# Remplacez par votre SteamID64 et ceux de votre famille
STEAM_IDS = ['YOUR_STEAM_ID', 'STEAM_ID_2', 'STEAM_ID_3']

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

session = requests.Session()
session.headers.update(HEADERS)

# Cache unique : appid -> détails complets (name, dlc, etc.)
details_cache = {}


def safe_get_json(url, retries=3, pause=3):
    """Fait une requête et renvoie du JSON, ou None si ça échoue vraiment."""
    backoff = 15

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=10)
        except requests.RequestException as e:
            print(f"   Erreur réseau ({e}), tentative {attempt}/{retries}...")
            time.sleep(pause)
            continue

        if response.status_code == 429:
            print(f"   Trop de requêtes envoyées, pause de {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue

        if response.status_code == 404:
            print("   Erreur HTTP 404 (route introuvable), abandon pour cette requête.")
            return None

        if response.status_code != 200:
            print(f"   Erreur HTTP {response.status_code}, tentative {attempt}/{retries}...")
            time.sleep(pause)
            continue

        try:
            return response.json()
        except ValueError:
            print(f"   Réponse non-JSON reçue, tentative {attempt}/{retries}...")
            time.sleep(pause)

    return None


def get_app_names():
    """Télécharge l'annuaire Steam pour traduire les AppID en vrais noms."""
    print("Téléchargement de la base de données des noms Steam...")
    app_names = {}
    last_appid = 0
    have_more = True

    while have_more:
        url = (
            "https://api.steampowered.com/IStoreService/GetAppList/v1/"
            f"?key={API_KEY}&include_games=true&include_dlc=true"
            f"&max_results=50000&last_appid={last_appid}"
        )
        data = safe_get_json(url, retries=3, pause=5)
        if not data or 'response' not in data:
            print("Impossible de charger l'annuaire (Plan B activé pour les noms).")
            return app_names

        apps = data['response'].get('apps', [])
        for app in apps:
            app_names[app['appid']] = app['name']

        have_more = data['response'].get('have_more_results', False)
        last_appid = data['response'].get('last_appid', 0)

    return app_names


def get_owned_games(steam_id):
    """
    Récupère les jeux/DLC possédés par un compte.

    CORRECTIF 1 : ajout de include_played_free_games=1 pour récupérer aussi
    les DLC/jeux gratuits déjà lancés au moins une fois (sinon l'API Steam
    les exclut par défaut, même si tu les possèdes).

    CORRECTIF 2 : diagnostic plus clair. Un compte "public" au niveau du
    profil peut quand même avoir le réglage spécifique "Détails du jeu"
    (Game details) sur "Amis uniquement" -> l'API renvoie alors une liste
    vide silencieusement. C'est la cause la plus fréquente des DLC de
    bibliothèque familiale manquants.
    """
    url = (
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={API_KEY}&steamid={steam_id}&format=json"
        f"&include_played_free_games=1&include_appinfo=0&skip_unvetted_apps=false"
    )
    data = safe_get_json(url)

    if not data or 'response' not in data:
        print(f"ID {steam_id} : requête échouée (voir erreurs ci-dessus).")
        return []

    games = data['response'].get('games')
    if not games:
        print(
            f"ID {steam_id} : 0 jeu renvoyé. Le profil est probablement "
            f"privé OU le réglage 'Détails du jeu' (Game details) n'est pas "
            f"sur Public dans les paramètres de confidentialité Steam de ce compte."
        )
        return []

    print(f"ID {steam_id} : {len(games)} jeux/DLC trouvés.")
    return [game['appid'] for game in games]


def get_app_details(appid):
    """Récupère (et met en cache) les détails d'une appid : nom, DLC, etc."""
    if appid in details_cache:
        return details_cache[appid]

    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    data = safe_get_json(url)
    time.sleep(3)  # pause systématique ici : appdetails est très limité côté API

    details = None
    if data and str(appid) in data and data[str(appid)].get('success'):
        details = data[str(appid)]['data']

    details_cache[appid] = details
    return details


def get_name(appid, steam_app_names):
    """Nom d'une appid : d'abord l'annuaire (gratuit), sinon appdetails (coûteux)."""
    if appid in steam_app_names:
        return steam_app_names[appid]
    details = get_app_details(appid)
    return details['name'] if details else f"App Inconnue ({appid})"


def main():
    steam_app_names = get_app_names()

    all_owned_apps = set()
    print("\nRécupération des bibliothèques...")
    for steam_id in STEAM_IDS:
        all_owned_apps.update(get_owned_games(steam_id))

    total_jeux = len(all_owned_apps)
    print(f"\nTotal des jeux/apps uniques trouvés (union des {len(STEAM_IDS)} comptes) : {total_jeux}")

    if total_jeux == 0:
        print(
            "\nAucun jeu récupéré du tout. Vérifie que 'Détails du jeu' est "
            "sur Public pour au moins un des comptes avant de continuer."
        )
        return

    dossier_du_script = os.path.dirname(os.path.abspath(__file__))
    nom_fichier = os.path.join(dossier_du_script, "resultats_dlc_manquants.txt")

    with open(nom_fichier, "w", encoding="utf-8") as fichier:
        fichier.write("=== LISTE DES DLC MANQUANTS ===\n\n")
        print("Analyse des DLC en cours (Ne fermez pas la fenêtre)...")

        for i, appid in enumerate(all_owned_apps, 1):
            print(f"Scan en cours : {i} / {total_jeux}...", end='\r')

            details = get_app_details(appid)
            dlcs_available = details.get('dlc', []) if details else []
            if not dlcs_available:
                continue

            missing = [dlc for dlc in dlcs_available if dlc not in all_owned_apps]
            if missing:
                nom_jeu = get_name(appid, steam_app_names)
                fichier.write(f"{nom_jeu} (AppID: {appid})\n")

                for dlc_id in missing:
                    nom_dlc = get_name(dlc_id, steam_app_names)
                    fichier.write(f"   -> Manque : {nom_dlc} (https://store.steampowered.com/app/{dlc_id})\n")
                fichier.write("\n")

    print(f"\nTerminé ! Résultats sauvegardés dans : {nom_fichier}")


if __name__ == "__main__":
    main()