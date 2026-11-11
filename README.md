# Suivi LEGO Disney

Une page web qui se met à jour seule. Chaque jour : meilleurs prix, remises, retraits proches, alertes. Chaque mardi : dates de sortie et de retrait, prix chez Fnac, Cultura et grandes surfaces (quand Brickfact les relève), annonces neuf et occasion sur eBay.fr, ventes estimées.

## Mise en ligne (environ 15 minutes, gratuit)

1. Créez un compte sur github.com (activez la double authentification), puis un dépôt public (par exemple `lego-disney`).
2. Envoyez-y tous les fichiers de ce dossier, en gardant l’arborescence `.github/workflows/`.
3. Clé Brickset (facultative, pour les dates précises de sortie et de retrait) : ajoutez-la dans les mêmes « secrets » sous le nom `BRICKSET_KEY`. Si Brickset affiche une erreur sur le « userHash » au premier lancement, ajoutez aussi `BRICKSET_USER` et `BRICKSET_PASS` (votre identifiant et votre mot de passe Brickset).
   Pour les données eBay (facultatif mais recommandé) : créez un compte développeur sur developer.ebay.com et récupérez l’*App ID* et le *Cert ID* de l’environnement Production. Dans le dépôt : Settings → Secrets and variables → Actions → ajoutez `EBAY_ID` et `EBAY_SECRET`. Sans eux, les colonnes eBay restent vides.
4. Settings → Pages → source : branche `main`, dossier racine. La page sera sur `https://VOTRE-PSEUDO.github.io/lego-disney/`.
5. Onglet Actions → « maj-quotidienne » → Run workflow, pour générer les premières données.
6. Pour recevoir les alertes par e-mail : en haut du dépôt, Watch → All activity.

## Alertes

- Un set bientôt retiré qui passe sous −30 % de son prix conseillé déclenche une alerte (seuil `ALERT_PCT` dans `update.py`). Elle prend la forme d’une « issue » GitHub, qui vous est envoyée par e-mail.
- Promos générales sur les jouets (King Jouet, Carrefour…) : aucune source automatique fiable n’existe. Ajoutez-les à la main dans `promos_jouets.json` quand une opération démarre :

```json
[{"enseigne": "Carrefour", "libelle": "10 € offerts dès 30 € d’achat de jouets",
  "remise": 10, "seuil": 30, "du": "2026-11-15", "au": "2026-11-23"}]
```

La page affiche alors les sets dont le prix atteint le seuil, avec le prix net après remise (prix de l’enseigne si Brickfact le connaît, sinon prix conseillé LEGO). Une alerte part le premier jour de l’opération.

## Limites à connaître

- Les prix et boutiques viennent de Brickfact (et les dates précises de Brickset, quand la clé est renseignée) (comparateur français), lus automatiquement. Vérifiez ses conditions d’utilisation avant de l’utiliser durablement : le script fait peu de requêtes (environ 6 par jour, une centaine le mardi, une pause entre chaque). Si Brickfact change sa mise en page, la lecture est à ajuster.
- Le code n’a pas pu être testé avec les vrais sites depuis la conversation. Au premier lancement, consultez le journal de l’onglet Actions : les erreurs y sont affichées set par set.
- Les ventes sont estimées : eBay ne publie pas les ventes réalisées. Le script compare chaque semaine les annonces visibles et compte celles qui ont disparu (ventes, mais aussi annonces retirées). Les chiffres deviennent parlants après quelques semaines.
- Seules les 200 premières annonces eBay par set sont lues, par recherche sur le numéro de set.
- Cultura et les supermarchés n’apparaissent que si Brickfact les relève pour le set. L’Avenue de la Brique et Vinted ne sont pas inclus.
