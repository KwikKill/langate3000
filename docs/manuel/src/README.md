# Introduction

## I love you 3000

Ce manuel a pour but de documenter le fonctionnement de la [langate 3000](https://github.com/InsaLan/langate3000) (réécrite en 2024 pour la XIX). La langate étant bâtie sur beaucoup des mêmes technologies que le site web, une documentation plus extensive sur ces technologies est disponible dans le [manuel de prise en main du backend](https://docs.insalan.fr/backend/).

Le manuel de la langate est présenté, comme celui du site, sous une license [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Langate ?

La langate est le portail captif de l'InsaLan, utilisé en Mini et à la LAN. Elle fournit les fonctionnalités suivantes :
- Gestion d'utilisateurs ([*non implémenté*] statut de paiement, [*non implémenté*] gestion des privilèges)
- [*non implémenté*] Synchronisation des comptes utilisateurs avec le site web
- Gestion d'appareils (+whitelist)
- Panneau de gestion custom (et très bien conçu !)
- Annonces

## Historique

Au commencement, il n'y avait rien. Puis il y eut l'InsaLan. La première date d'utilisation d'un portail captif n'est pas connue, peut-être que les archives sont incomplètes, cependant on en trouve plusieurs mentions sur l'ancien wiki.

La [langate 2000](https://github.com/InsaLan/langate2000) fut mise en service en 2019 pour l'InsaLan XIV. Elle était codée avec des technologies similaires à la langate actuelle (surtout le back, qui était déjà en Django), mais sans documentation.

Il a donc été décidé de créer cette version de la langate. Elle nous permettra d'avoir une documentation et une compréhension complète de son fonctionnement, et elle sera ainsi plus facile à maintenir et améliorer. Elle nous a aussi permis d'utiliser des technologies plus récentes et simples d'utilisation.

## Technologies

Cette langate, comme le site web [insalan.fr](https://docs.insalan.fr/backend/), utilise [Nginx](nginx.com) et [DRF](django-rest-framework.org) (outil permettant de développer des API web en **Python**) pour le [backend](01-backend/README.md) et [Vue](https://fr.vuejs.org) pour le [frontend](02-frontend/README.md).

Le module [netcontrol](00-netcontrol/README.md) a également été entièrement refait, incorporant directement les [nftables](00-netcontrol/nftables.md) nécéssaires à son fonctionnement.

On déploie la langate avec [Docker Compose](https://docs.docker.com/compose/).

## L'équipe

La langate 3000 est le fruit d'une coopération historique entre les équipes SysRez-Dev et SysRez-Infra, et plus spécifiquement :

- Gabriel "**KwikKill**" Blaisot [il], responsable SysRez-Dev de l'InsaLan XIX
- Paul "**TheBloodMan**" Gasnier [il], responsable SysRez-Infra de l'InsaLan XVIII
- Youenn "**SkytAsul**" Le Jeune [il], responsable SysRez-Infra de l'InsaLan XVIII
- Amance "**Ecnama**" Graindorge [il], responsable SysRez-Infra de l'InsaLan XIX
- Hector "**pixup1**" Vernet [il], responsable SysRez-Infra de l'InsaLan XIX

Elle repose bien évidemment sur le travail des légendes à l'origine de la langate 2000 :

- **Mahal** / ShiroUsagi-san
- **Red** / red4game
- **Flo** / darkgallium
- **Lin HD** / cloudyhug
- **Kuro** / antonincms
- **Trinity** / trinity-1686a
- **Lux** / Lymkwi
- **ElPainAuChocolat** / NathanPERIER