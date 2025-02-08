# Proxy Frontend

## Production
En production, le frontend est construit au démarrage du Docker puis c'est fini. Caddy doit simplement fournir les fichiers construits par le frontend, qui se trouvent dans `volumes/prod/frontend`. On les monte donc dans le docker-compose.

### Caddyfile
Dans le Caddyfile, on s'intéresse à la section `{$CADDY_HOST}:{$CADDY_PORT}` : le host est normalement `gate.insalan.fr` et le port `80`, donc cette section concerne les requêtes dirigées vers `http://gate.insalan.fr/xxx`, i.e. le frontend.

Déjà, on paramètre la racine des fichiers : il s'agit de là où on a monté les fichiers du frontend dans le docker-compose.

La clause `try_files {path} {path}/ /index.html` indique à Caddy que si il n'y a pas de fichier au chemin `{path}` spécifié dans l'URL, il peut renvoyer le fichier `{path}/index.html` à la place (s'il existe).

La clause `file_server {    hide .*    }` est celle qui fait vraiment le travail : elle indique à Caddy de fonctionner en mode "serveur de fichier", qui va tout simplement envoyer en réponse le fichier demandé dans l'URL (modulo les modifications dûes au `try_files`). On fait attention tout de même à ne pas renvoyer les _dotfiles_ (les fichiers commençant par un `.`) car ce sont en général des fichiers internes.

## Beta
En beta, le frontend n'est pas construit à l'avance : il est fourni par un serveur Vite qui attend sur le port 5173. Il faut donc simplement rediriger les requêtes destinées au frontend vers le container approprié : `reverse_proxy http://frontend:{$FRONTEND_PORT}`.
