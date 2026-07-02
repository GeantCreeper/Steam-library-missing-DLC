# ============================================================
# COMMENT RÉCUPÉRER MY_STEAM_LOGIN_SECURE (une seule fois, valable
# plusieurs semaines/mois selon votre config Steam) :
#
# 1. Ouvrez https://store.steampowered.com dans votre navigateur et
#    connectez-vous avec VOTRE compte (celui de MY_STEAM_ID).
# 2. Appuyez sur F12 pour ouvrir les outils développeur.
# 3. Allez dans l'onglet "Application" (Chrome/Edge) ou "Stockage" (Firefox).
# 4. Dans "Cookies" -> "https://store.steampowered.com", cherchez la ligne
#    "steamLoginSecure".
# 5. Copiez toute la valeur (une longue chaîne) et collez-la dans
#    MY_STEAM_LOGIN_SECURE en haut du script.
#
# Ce cookie ne donne accès qu'à ce que votre navigateur voit déjà sur le
# site Steam (votre bibliothèque) — il ne permet pas d'acheter, de modifier
# des paramètres, ni d'accéder aux autres comptes.
# ============================================================

import requests
import time
import os

API_KEY = 'MY_API_KEY'  # Remplacez par votre clé API Steam

# Votre propre SteamID64 (celui du cookie ci-dessous). Doit faire partie de STEAM_IDS.
MY_STEAM_ID = 'USER_STEAM_ID64'  # Remplacez par votre SteamID64

# Remplacez par votre SteamID64 et ceux de votre famille
STEAM_IDS = [MY_STEAM_ID, 'FAMILY_MEMBER_STEAM_ID64_1', 'FAMILY_MEMBER_STEAM_ID64_2']

# Cookie de session Steam pour VOTRE compte (voir instructions en bas du fichier
# pour savoir comment le récupérer). Laissez vide pour désactiver cette méthode
# (dans ce cas, votre compte utilisera aussi la méthode standard GetOwnedGames,
# qui peut manquer des DLC à 0 minute de jeu).
MY_STEAM_LOGIN_SECURE = 'MY_STEAM_LOGIN_SECURE'  # Remplacez par votre cookie de session

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
}

session = requests.Session()
session.headers.update(HEADERS)

# Cache unique : appid -> détails complets (name, dlc, etc.)
details_cache = {}


def safe_get_json(url, retries=3, pause=3, cookies=None):
    """Fait une requête et renvoie du JSON, ou None si ça échoue vraiment."""
    backoff = 15

    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=10, cookies=cookies)
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


def get_owned_games_api(steam_id):
    """
    Récupère les jeux/DLC possédés via l'API publique GetOwnedGames.

    Cette route omet souvent les DLC sans temps de jeu
    enregistré, même quand ils sont bien possédés. C'est pour ça qu'on
    utilise une méthode alternative pour votre propre compte (voir
    get_owned_apps_dynamicstore ci-dessous).
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

    print(f"ID {steam_id} : {len(games)} jeux/DLC trouvés (API publique).")
    return [game['appid'] for game in games]


def get_owned_apps_dynamicstore(login_secure_cookie):
    """
    Récupère TOUS les appids possédés (jeux + DLC, même à 0 minute de jeu)
    via l'endpoint interne que Steam utilise sur le site lui-même.
    Nécessite d'être connecté (cookie steamLoginSecure), mais aucune clé API.
    """
    if not login_secure_cookie:
        return None

    url = "https://store.steampowered.com/dynamicstore/userdata/"
    data = safe_get_json(url, cookies={'steamLoginSecure': login_secure_cookie})

    if not data or 'rgOwnedApps' not in data:
        print(
            "Échec de récupération via dynamicstore/userdata : le cookie "
            "MY_STEAM_LOGIN_SECURE est probablement invalide ou expiré."
        )
        return None

    owned = data['rgOwnedApps']
    print(f"Compte perso ({MY_STEAM_ID}) : {len(owned)} jeux/DLC trouvés (méthode dynamicstore, plus fiable).")
    return owned


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
        if steam_id == MY_STEAM_ID and MY_STEAM_LOGIN_SECURE:
            owned = get_owned_apps_dynamicstore(MY_STEAM_LOGIN_SECURE)
            if owned is not None:
                all_owned_apps.update(int(a) for a in owned)
                continue
            print("Repli sur l'API publique pour ce compte.")

        owned = get_owned_games_api(steam_id)
        all_owned_apps.update(int(a) for a in owned)

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
            dlcs_available = [int(dlc) for dlc in (details.get('dlc', []) if details else [])]
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
