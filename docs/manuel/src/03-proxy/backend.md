# Proxy Backend

En beta comme en production, Caddy sert à la même chose : il transfère les requêtes destinées au backend vers... le backend.

## Caddyfile
C'est la section `api.{$CADDY_HOST}:{$CADDY_PORT}`.

Déjà, on définit un [matcher](https://caddyserver.com/docs/caddyfile/matchers#path) qui va concerner les chemins menant à des fichiers à fournir directement : ceux dans les dossiers "static" ou "media".
On y associe une clause `file_server` associée de son `root` pour dire d'où fournir les fichiers.
> On ne pouvait pas mettre le matcher directement dans la clause `file_server` car il y avait plusieurs chemins possibles.

Ensuite, si les URLs n'ont pas matché précédemment, on redirige les requêtes vers le backend avec le port associé via un `reverse_proxy`.
