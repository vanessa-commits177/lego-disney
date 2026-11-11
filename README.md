# Suivi LEGO Disney

Une page web qui se met à jour seule. Chaque mardi : liste des sets Disney depuis 2023, dates de sortie et de retrait, prix conseillé (Brickset), annonces neuf et occasion sur eBay.fr, ventes estimées. Chaque jour : promos générales sur les jouets et alertes.

## Mise en ligne (gratuit)

1. Dépôt GitHub public avec : `update.py`, `index.html`, `README.md`, `promos_jouets.json` et `.github/workflows/maj-quotidienne.yml`.
2. Settings → Secrets and variables → Actions : `BRICKSET_KEY` (clé Brickset). Si Brickset signale un problème de « userHash » au premier lancement, ajoutez aussi `BRICKSET_USER` et `BRICKSET_PASS`. Pour eBay, une fois vos clés validées : `EBAY_ID` (App ID) et `EBAY_SECRET` (Cert ID), environnement Production.
3. Settings → Pages → Deploy from a branch → `main` → `/ (root)`.
4. Onglet Actions → « maj-quotidienne » → Run workflow, pour la première mise à jour.
5. Pour recevoir les alertes par e-mail : en haut du dépôt, Watch → All activity.

## Promos générales sur les jouets

Aucune source automatique autorisée n’existe. Notez les opérations à la main dans `promos_jouets.json` :

```json
[{"enseigne": "Carrefour", "libelle": "10 € offerts dès 30 € d’achat de jouets",
  "remise": 10, "seuil": 30, "du": "2026-11-15", "au": "2026-11-23"}]
```

La page affiche alors les sets dont le prix conseillé atteint le seuil, avec le prix net après remise (en supposant que le prix en rayon est le prix conseillé). Une alerte part le premier jour de l’opération.

## Limites à connaître

- Sources : Brickset (API officielle) et eBay (API officielle). Il n’y a pas de relevé automatique des prix chez les revendeurs (Fnac, Cultura, supermarchés).
- Le prix LEGO est le prix conseillé en euros de LEGO.com (zone euro), pas toujours identique au prix français.
- Le code n’a pas pu être testé avec les vrais services depuis la conversation : au premier lancement, consultez le journal de l’onglet Actions.
- Les ventes sont estimées : eBay ne publie pas les ventes réalisées. Le script compare chaque semaine les annonces visibles et compte celles qui ont disparu (ventes, mais aussi annonces retirées). Les chiffres deviennent parlants après quelques semaines.
- Seules les 200 premières annonces eBay par set sont lues, par recherche sur le numéro de set.
