# Calcul de l'artificialisation - 2024
## Installation
1) Copier le fichier `env.cfg.example` en `env.cfg`
2) Remplacer les valeurs de la section `POSTGRES` par les identifiants de connection de la base de donnée postgres locale
3) Lancer la commande `python calcul.py`

Le résultat du calcul sera disponible dans la table `surface_artificialisee` de la base de donnée.

## Dépendances
- Postgis installé en local et les commandes `psql` et `ogr2ogr` accessibles globalement
- 7z installé en local et la commande `7z` accessible globalement

## Fonctionnement de `calcul.py`
- Télécharge un millésime d'occupation du sol OCS GE depuis la géoplateforme
- Extrait le fichier 7Z téléchargé
- Importe le shapefile dans la base de donnée locale
- Execute une commande SQL qui :
    - Assigne une valeur artificiel / non artificiel à chaque objet OCS GE
    - Regroupe les objets artificiels et non artficiels se touchant
    - Inverse la valeur artificiel / non artificiel des objets < 2500m2 enclavés
    - Selectionne les objets batis (CS 1.1.1.1) < 2500m2 enclavé d'objets non-artificiels
    - Effectue une union entre les clusters articiciels (> 2500m2) et les objets batis enclavés (< 2500m2)
    - Crée une table contenant à partir de l'union ci-dessous (cette table ne contient qu'un objet)