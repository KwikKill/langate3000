# nftables

Suite à la mise à jour de la tête de réseau de `iptables` vers `nftables` pour la XIX, netcontrol a été réécrit pour utiliser cet utilitaire.

De plus, les règles sont directement intégrées au module, là où avant elles étaient mises en place par un script séparé, [`portail.sh`](https://github.com/InsaLan/scripts-reseau/blob/ifupdown-iptables/portail.sh).

`nftables` est un utilitaire de gestion des règles réseau qui sert notamment à créer des pare-feu, du NAT, des redirections de ports...

Pour une page de doc complète et claire, voir [ici](https://wiki.nftables.org/wiki-nftables/index.php/Quick_reference-nftables_in_10_minutes).

Dans notre cas, on s'en sert pour autoriser la connexion des appareils uniquement si leur utilisateur est connecté à la langate.

À cet effet on utilisait auparavant [ipsets](https://ipset.netfilter.org/), qui nous permettait de garder une collection d'IP ayant accès au réseau et de pouvoir utiliser ça directement dans une règle `iptables`.

La fonctionnalité correspondante sur `nftables` est les [Maps](https://wiki.nftables.org/wiki-nftables/index.php/Maps). Elle nous permet d'associer une adresse MAC à une [mark](marks.md).

## Utiliser nftables à l'intérieur d'un Docker

Netcontrol 2000 n'utilisait pas Docker, c'était un service systemd. Pour la langate 3000, on utilise Docker.

Les containers Docker sont par définition isolés de la machine sur laquelle ils tournent. C'est donc compliqué de pouvoir gérer des `nftables` sur la tête de réseau depuis l'intérieur d'un container.

C'est à ça que sert cette ligne dans le `Dockerfile` de netcontrol :
```bash
&& pip install 'git+https://git.netfilter.org/nftables@v1.1.0#egg=nftables&subdirectory=py' \
```

Pour avoir un accès direct à la tête de réseau, il faut également ces lignes dans le docker compose :
```yaml
cap_add:
	- NET_ADMIN
network_mode: "host"
```

## Les règles nftables

> **_NOTE :_** Tous les bouts de code de cette partie proviennent de `netcontrol/nft.py` (mises en forme comme commandes `nft` pour plus de clarté).

Pour pouvoir faire ce qu'on doit faire, on n'a pas besoin d'énormément de règles; vu qu'on se sert d'une map, en réalité 3 suffisent. Mais déjà, voyons le setup des chaines et de la map qu'on utilise :

```bash
nft add table ip insalan
```
La table qu'on utilise.
```bash
nft add set insalan netcontrol-auth { type ether_addr; }
```
On a un set pour les adresses MAC authentifiées. C'est un workaround car dans la dernière version de nftables, on peut voir directement si une clé est présente dans la partie match d'une règle. Cependant, cette version n'est pas encore disponible dans le repo de Debian 12, qu'on utilise sur la tête.
```bash
nft add map insalan netcontrol-mac2mark { type ether_addr : mark; }
```
La map qui va associer une addresse mac à une mark. On rajoutera une entrée dedans par appareil authentifié.

Ensuite, voyons les trois règles qui définissent le comportement de netcontrol :

### Mark

```bash
nft add chain insalan netcontrol-filter { type filter hook prerouting priority 2; }

nft add rule insalan netcontrol-filter ip daddr != 172.16.1.0/24 ether saddr @netcontrol-auth meta mark set ether saddr map @netcontrol-mac2mark
```
Cette règle s'applique au paquets qui :
- `ip daddr != 172.16.1.0/24` : ne sont pas destiné à une IP locale;
- `ether saddr @netcontrol-auth` : ont leur addresse MAC dans le set.

Et elle :
- `meta mark set ether saddr map @netcontrol-mac2mark` : définit la mark du paquet comme celle qui correspond à sa MAC dans la map.

`meta mark set` signifie que la règle modifie la mark du paquet, dans ses méta-informations.

`ether saddr map @netcontrol-mac2mark` signifie que la mark est récupérée depuis l'entrée dans la map correspondant à `ether saddr`, ou la MAC de la source.

### Bypass

```bash
nft add chain insalan netcontrol-debypass { type filter hook prerouting priority 0; }

nft add rule insalan netcontrol-debypass meta mark > 1024 meta mark set meta mark & 0xFFFFFBFF
```

Cette règle s'applique aux paquets qui:
- `meta mark > 1024` : Ont le bypass activé.

Et elle :
- `meta mark set meta mark & ~1024` : Leur enlève le bypass, tout simplement (on suppose ne jamais avoir de mark supérieure à 2048, ça n'aurait pas de sens de toute façon).

> Alors oui mais ça sert à quoi le bypass du coup, si on l'enlève dans tous les cas ?

Eh bien non, on ne l'enlève pas dans tous les cas : seulement si le paquet est à destination d'une **IP non blacklistée**, où si **on n'a pas lancé le script bypass**. En effet, ce script rajoute une règle avec la priorité 1 : elle s'éxécute donc entre la règle qui assigne les marks et celle-ci. Cette règle qui est rajoutée prend les paquets à destination d'une **IP blacklistée avec le bypass**, et leur assigne la mark 1024 qui leur permet à la fois d'**ignorer la blacklist** et de **passer par Quantic**.

### Blocage des requêtes HTTP extérieures sur netcontrol

```bash
nft add rule insalan netcontrol-filter ip daddr { {docker0_ip},172.16.1.1 } tcp dport 6784 ip saddr != { {','.join(ips)} } drop
```

Cette règle s'applique aux paquets qui :
- `ip daddr { {docker0_ip},172.16.1.1 }` : ont pour destination l'IP de netcontrol;
- `tcp dport 6784` : ont pour destination le port de Netcontrol;
- `ip saddr != { {','.join(ips)} }` : ne viennent d'aucune des adresses IP de la tête.

Et elle :
- `drop` : les bloque tout simplement.

Cette règle empêche d'autres utilisateurs du réseau d'envoyer des requêtes à netcontrol, tout en nous laissant la possibilité d'en envoyer nous même via un terminal de la tête.

### Accès à la langate

```bash
nft add chain insalan netcontrol-nat { type nat hook prerouting priority 0; }

add rule insalan netcontrol-nat ip daddr != 172.16.1.0/24 ether saddr != @netcontrol-auth tcp dport 80 redirect to :80
```

Cette règle s'applique aux paquets qui :
- `ip daddr != 172.16.1.0/24` : ne sont pas destiné à une IP locale;
- `ether saddr != @netcontrol-auth` : n'ont **pas** leur addresse MAC dans le set;
- `tcp dport 80` : ont pour destination le port 80 (c'est celui qui correspond au protocole HTTP).

Et elle :
- `redirect to :80` : redirige le paquet vers le port 80 **de cette machine** (la tête de réseau).

Cela permet de rediriger toutes les connections web vers la langate, pour que les joueurs tombent facilement dessus.

### Blocage des paquets d'appareils non connectés

```bash
nft add chain insalan netcontrol-forward { type filter hook forward priority 0; }

nft add rule insalan netcontrol-forward ip daddr != { 172.16.1.1,{docker_subnet} } ip saddr {variables.ip_range()} ip saddr != { 172.16.1.1,{docker_subnet} } ether saddr != @netcontrol-auth reject
```

Cette règle s'applique aux paquets qui :
- `ip daddr != { 172.16.1.1,{docker_subnet} }` : ne sont pas destinés à la tête de réseau, netcontrol ou au backend;
- `ip saddr {variables.ip_range()}` : viennent de l'intérieur du réseau (ip_range est 172.16.0.0/12, soit toutes les addresses assignées par la tête);
- `ip saddr != { 172.16.1.1,{docker_subnet} }` : ne viennent pas de la tête, de netcontrol ou du backend;
- `ether saddr != @netcontrol-auth` : n'ont pas leur addresse MAC dans le set.

Et elle :
- `reject` : les rejette.

À noter que cette règle, contrairement aux deux autres, a lieu sur le hook `forward`, qui est après `postrouting` (cf. [ce schéma](https://www.linuxembedded.fr/sites/default/files/inline-images/nft_hooks.png)). Les paquets en destination du web auront donc déjà été redirigés vers la tête par la règle précédente et ne seront pas affectés.

## Connecter un appareil

Grace aux règles ci-dessus, pour connecter un appareil, il suffit de lui donner une mark comme ça :
```bash
nft add element insalan netcontrol-mac2mark { <mac> : <mark> }
```
Et pour le déconnecter, on supprime simplement cette entrée (`nft delete element`).

Pour changer sa mark, on le déconnecte et le reconnecte avec une mark différente.