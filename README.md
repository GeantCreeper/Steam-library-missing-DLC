# Steam-library-missing-DLC
Ce script Python permet de voir quels DLC ne sont pas possédés sur votre bibliothèque familiale Steam.

Fusion des bibliothèques : Récupère automatiquement les jeux possédés par plusieurs utilisateurs via leurs SteamID64. Pour votre propre compte, utilise une méthode qui récupère aussi les DLC sans temps de jeu souvent omis par l'API Steam classique.

Détection de DLC : Identifie les contenus additionnels manquants pour les jeux déjà présents dans la bibliothèque commune.

Exportation : Génère un fichier texte (resultats_dlc_manquants.txt) listant les jeux trouvés avec leur lien direct vers le magasin Steam.

Configuration : Ouvrez le fichier et modifiez les variables suivantes :
API_KEY : Remplacez par votre clé API Steam en allant sur https://steamcommunity.com/dev/apikey.
MY_STEAM_ID : Votre propre SteamID64.
STEAM_IDS : Remplacez par les SteamID64 des membres de votre famille.
MY_STEAM_LOGIN_SECURE : Le cookie de session de votre compte Steam (voir instructions dans le script). Il permet de récupérer la totalité de vos jeux/DLC possédés.
