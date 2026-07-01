# Steam-library-missing-DLC
Ce script Python permet de voir quels dlc ne sont pas possédés sur votre bibliothèque familiale Steam.

Fusion des bibliothèques : Récupère automatiquement les jeux possédés par plusieurs utilisateurs via leurs SteamID64.

Détection de DLC : Identifie les contenus additionnels manquants pour les jeux déjà présents dans la bibliothèque commune.

Exportation : Génère un fichier texte (resultats_dlc_manquants.txt) listant les jeux trouvés avec leur lien direct vers le magasin Steam.

Configuration : Ouvrez le fichier et modifiez les variables suivantes :

API_KEY : Remplacez par votre clé API Steam.

STEAM_IDS : Remplacez par les SteamID64 des membres de votre famille. Le premier ID doit être le vôtre.
