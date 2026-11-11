# Suivi LEGO Disney

Une page web qui se met à jour seule chaque jour : sets Disney, dates de sortie et de retrait, prix LEGO, annonces neuf et occasion sur eBay.fr, ventes estimées.

## Mise en ligne (environ 15 minutes, gratuit)

1. Créez un compte sur github.com, puis un dépôt public (par exemple `lego-disney`).
2. Envoyez-y les 4 fichiers de ce dossier, en gardant l’arborescence `.github/workflows/`.
3. Demandez deux accès gratuits :
   - une clé API Brickset (brickset.com/tools/webservices/requestkey) ;
   - un compte développeur eBay (developer.ebay.com) : récupérez le *App ID* (client) et le *Cert ID* (secret) de l’environnement Production.
4. Dans le dépôt : Settings → Secrets and variables → Actions → ajoutez `BRICKSET_KEY`, `EBAY_ID` et `EBAY_SECRET`.
5. Settings → Pages → source : branche `main`, dossier racine. Votre page sera sur `https://VOTRE-PSEUDO.github.io/lego-disney/`.
6. Onglet Actions → « maj-quotidienne » → Run workflow, pour générer les premières données. Ensuite, tout se fait seul chaque matin.

## Limites à connaître

- Le code n’a pas pu être testé avec les vrais services depuis ma conversation : au premier lancement, regardez le journal de l’onglet Actions. Les erreurs sont affichées set par set et le reste continue.
- Les ventes sont estimées : eBay ne fournit pas publiquement les ventes réalisées. Le script compare chaque jour les annonces visibles et compte celles qui ont disparu. Les chiffres ne deviennent parlants qu’après une à deux semaines d’historique.
- Seules les 200 premières annonces par set sont lues, et la recherche se fait par numéro de set : de rares annonces hors sujet peuvent s’y glisser.
- Le prix LEGO vient de la zone euro de LEGO.com via Brickset. Les offres de Cultura, Fnac, supermarchés et les alertes sur les remises ne sont pas encore intégrées, et L’Avenue de la Brique n’a pas d’accès automatique officiel.
