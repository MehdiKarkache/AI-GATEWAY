# Journal de développement — Code Review Assistant

**Projet :** Assistant de revue de code avec IA et intégration MCP  
**Étudiant :** El Mehdi Karkache  
**Dépôt :** https://github.com/MehdiKarkache/AI-GATEWAY

---

## Session 1 — Début du projet, choix de l'API

### Ce que je voulais faire
Mon idée c'etait de faire un outil ou tu colles du code et l'IA te dit ce qui va pas dedans — les bugs, les failles de secu, les trucs pas lisibles. J'ai commencé par la parce que c'est le coeur du projet, si cette partie marche pas le reste sert a rien.

### Comment j'ai travaillé avec l'IA
J’ai utilisé ChatGPT et Copilot tout au long du projet pour m’aider à avancer plus vite et à mieux structurer mon code. Au début, je faisais des demandes assez générales, donc j’obtenais quelque chose qui fonctionnait, mais le code était souvent regroupé dans un seul fichier et restait difficile à maintenir. En reformulant mes demandes de manière plus précise, j’ai réussi à obtenir un résultat beaucoup plus propre, avec une meilleure séparation des différentes parties du projet. Ça m’a vraiment fait comprendre que la qualité du résultat dépend beaucoup de la façon dont on pose la demande : plus le prompt est clair et structuré, plus le code généré l’est aussi.

Pour le choix de l'API j'ai galéré. D'abord OpenAI direct — trop cher. Apres Gemini — le quota marchait bizarrement, des fois ca passait des fois non, j'ai pas compris pourquoi. Au final j'ai trouvé OpenRouter qui donne acces a des modeles gratuits. J'ai pris `google/gemma-3-4b-it:free`. C'est pas ouf mais c'est gratuit. Le probleme c'est que le quota se finit vite et je dois creeer un compte a chaque fois.

### Ce qui a bloqué
Le modele renvoyait le JSON dans des balises markdown genre ` ```json ... ``` `. Du coup `json.loads()` plantait systematiquement. J'ai demandé a Copilot : *« Comment parser un JSON qui est entouré de balises markdown ? »*. Il m'a proposé une regex et j'ai fait une fonction `extract_json()` dans `src/analyzers/__init__.py` pour extraire le premier objet JSON du texte. C'est bricolé mais ca marche. J'aurais pu utiliser `response_format` coté API mais c'est pas supporté par tous les modeles gratuits sur OpenRouter.

### Ce que j'en retiens
On peut pas faire confiance a un LLM pour respecter un format de sortie juste avec le prompt. Le modele dit qu'il va retourner du JSON brut et il fait ce qu'il veut. Faut toujours prevoir un parsing defensif coté code.

---

## Session 2 — Architecture à 3 analyseurs et interface Streamlit

### Ce que je voulais faire
Séparer l'analyse en 3 axes : bugs, securité, lisibilité. L'idée c'est que chaque analyseur ait son propre prompt systeme pour que le modele se concentre sur un seul aspect a la fois. Ca devrait donner de meilleurs resultats qu'un seul gros prompt.

### Comment j'ai travaillé avec l'IA
J'ai demandé a Copilot de generer les trois fichiers `bugs.py`, `security.py`, `style.py` avec des prompts differents pour chacun. Pour les lancer en parallele j'ai utilisé `asyncio.gather()` — Copilot me l'avait suggéré et sur le papier c'est la bonne approche pour de l'async.

Pour l'interface, j'ai fait un theme sombre style GitHub. Je donnais les couleurs hex a Copilot genre : *« Utilise #0d1117 pour le fond, #161b22 pour les surfaces, #6c63ff pour l'accent, et fais moi tout le CSS »*. Il generait le CSS complet et j'avais presque rien a corriger. J'ai ajouté un editeur de code, une sidebar pour l'historique, des onglets. La partie visuelle c'est la ou j'avais pas pris beaucoup du temps.

### Ce qui a bloqué ou changé
Rien a bloqué a ce stade. Tout marchait. Mais ce que je savais pas c'est que envoyer 3 requetes en parallele au meme modele gratuit, ca allait me poser un enorme probleme plus tard avec le rate limit...

### Ce que j'en retiens
J'etais content du resultat visuel et de l'architecture. Mais j'ai fait l'erreur de pas verifier les contraintes du modele avant de designer l'archi. Le `asyncio.gather()` c'etait la bombe a retardement.

---

## Session 3 — Le MCP (j'ai du tout recommencer)

### Ce que je voulais faire
Integrer le protocole MCP (Model Context Protocol) pour exposer les fonctionnalités du projet comme des outils que d'autres IA ou agents peuvent appeler. C'etait la partie la plus floue pour moi — j'avais jamais touché au MCP avant.

### Comment j'ai travaillé avec l'IA
J'ai fait beaucoup de prompts exploratoires pour comprendre : *« Comment créer un serveur MCP avec FastMCP en Python ? »*, *« C'est quoi la différence entre un tool, une resource et un prompt en MCP ? »*, *« Montre moi un exemple complet avec FastMCP »*. Copilot etait utile pour le code mais pas toujours fiable pour les concepts. A un moment il m'a generé un serveur MCP avec `version=` et `description=` dans le constructeur FastMCP. Ca plantait au demarrage et j'ai mis un moment a comprendre que FastMCP prend juste `name` et `instructions` comme parametres — c'est le genre d'erreur ou tu fais confiance a l'IA et tu perds 30 minutes pour rien.

### Ce qui a bloqué ou changé
J'ai reussi a faire tourner un serveur MCP v1 avec des outils... mais quand j'ai pris du recul je me suis rendu compte que mes outils avaient aucun sens. Genre j'avais "supprimer une review", "comparer des analyses", "exporter un rapport". Personne va connecter un agent IA a mon projet pour supprimer une ligne dans SQLite.

J'ai demandé a Copilot : *« Quels sont les MCP les plus connus et utiles ? Qu'est-ce que les vrais devs utilisent ? »*. La reponse m'a orienté vers GitHub (tres demandé) et l'intelligence sur le code (explain, fix, generate tests). Du coup j'ai tout supprimé et reconstruit autour de 11 outils qui ont du sens. Ca m'a couté une session entiere le pivot.

### Ce que j'en retiens
La premiere version d'une architecture c'est rarement la bonne. Ici j'avais fait l'erreur classique de construire ce qui est possible plutôt que ce qui est utile. Le pivot m'a couté du temps mais le resultat est bien plus coherent.

### Remarques
Je suis pas sur d'avoir encore bien compris toutes les subtilités du MCP honnêtement. La distinction entre resource et prompt me parait encore un peu floue dans certains cas. Mais au moins mes outils font quelque chose de concret maintenant.

---

## Session 4 — GitHub et les outils avancés

### Ce que je voulais faire
Implementer les 5 outils GitHub (`get_repo`, `get_file`, `create_issue`, `list_issues`, `search_repos`) et les outils d'intelligence code (`explain_code`, `generate_tests`).

### Comment j'ai travaillé avec l'IA
Pour GitHub j'ai utilisé `httpx` pour les appels API REST. J'ai demandé a Copilot : *« Fais moi un helper pour appeler l'API GitHub v3 avec httpx, Bearer token, et gestion d'erreurs »*. Il a generé `_github_request()` correctement du premier coup avec le bon header `X-GitHub-Api-Version: 2022-11-28`. J'ai juste adapté la gestion des erreurs HTTP.

Pour les prompts de `explain_code` et `generate_tests` ca a ete plus long. Copilot me proposait des prompts trop vagues genre *« Explain this code »*. Le modele renvoyait du texte libre melangé avec du code. J'ai du ecrire les prompts moi-meme en etant tres explicite : *« Return ONLY a JSON object with these exact fields: test_code (string with escaped newlines), test_count (integer), framework (string), coverage_summary (string). No markdown, no explanation, ONLY the JSON. »*. Ca derange mais c'est la seule façon d'avoir un retour structuré avec un modele gratuit.

### Ce qui a bloqué
Le fichier `app.py` commencait a devenir enorme — plus de 800 lignes. Copilot commencait a ecraser des sections existantes quand je lui demandais d'ajouter du code, ou il creait des variables avec le meme nom que d'autres. J'ai appris a etre beaucoup plus ciblé dans mes demandes plutôt que de lui demander de modifier des grands blocs.

### Ce que j'en retiens
Plus un fichier est long, plus c'est risqué de laisser l'IA le modifier en entier. Faut lui donner un contexte precis et petit. Et pour les prompts LLM, la precision c'est tout — un prompt vague donne un retour vague.

---

## Session 5 — Tout a planté (rate limit)

### Ce que je voulais faire
Juste tester l'app avec un vrai fichier de code. Rien de compliqué en theorie.

### Comment j'ai travaillé avec l'IA
Quand j'ai eu l'erreur de rate limit j'ai d'abord demandé a Copilot : *« Comment gérer une erreur 429 rate limit avec retry et backoff ? »*. Il m'a fait une logique de retry avec `asyncio.sleep()` — 3 tentatives, delais de 2-3 secondes, timeout de 30 secondes. Sur le papier c'etait correct mais en pratique c'etait horrible : 3 tentatives × 3 analyseurs × 5-15 secondes d'attente = l'app qui boucle pendant 90 secondes dans le vide.

C'est la que j'ai du reflechir par moi-meme au lieu de suivre ce que l'IA proposait. J'ai testé l'API directement et j'ai vu :

```
ERROR: RateLimitError 429 — Rate limit exceeded: free-models-per-day.
X-RateLimit-Remaining: 0
```

Le vrai probleme c'etait pas le retry. C'etait que j'avais **50 requetes par jour** et que j'en consommais **3 par analyse** (bugs + secu + style). Donc ~16 analyses max par jour. Avec mes tests de dev j'avais tout finis.

### Ce qui a bloqué ou changé
J'ai completement reecrit `src/aggregator.py`. Au lieu d'appeler 3 analyseurs separés, j'envoie maintenant **1 seul prompt** qui analyse les 3 axes en meme temps. 1 analyse = 1 requete = 50 analyses par jour.

### Ce que j'en retiens
Les contraintes d'infrastructure (quotas, rate limits, coûts) doivent etre des premieres considerations de design, pas une chose qu'on decouvre apres. Je savais que c'etait un modele gratuit limité, j'aurais du concevoir pour ça des le depart au lieu de faire une belle architecture a 3 fichiers qui marche pas en pratique.

### Remarques
C'est probablement la session ou j'ai le plus appris. Pas techniquement — le fix etait simple — mais sur la methode. L'IA m'a proposé un retry qui etait techniquement correct mais qui reglait pas le vrai probleme. C'est moi qui ai du identifier la vraie cause et trouver la bonne solution. Je pense que c'est exactement le genre de situation ou faut pas juste executer ce que l'IA dit.

---

## Session 6 — Le push Git (et les clés exposées)

### Ce que je voulais faire
Push le projet sur GitHub. Ca aurait du prendre 2 minutes.

### Comment j'ai travaillé avec l'IA
J'avais 2 commits et ca voulait pas push, y'avait un conflit. J'ai demandé a Copilot comment resoudre et il m'a proposé un soft reset pour fusionner les commits. Ca marchait.

### Ce qui a bloqué ou changé
Le vrai probleme c'est quand GitHub Push Protection a bloqué mon push :

```
Push cannot contain secrets
GitHub Personal Access Token found in .env.example:2
```

J'avais oublié mes VRAIES cles API dans le `.env.example`. La cle OpenRouter et le token GitHub en clair. C'est clairement ma plus grosse erreur du projet. Meme si je les supprime apres, les cles sont dans l'historique git donc elles sont compromises, faut les regenerer.

Pour fixer j'ai fait un soft reset, viré les `__pycache__` et `reviews.db` du tracking, mis des placeholders dans `.env.example`, refait un commit propre. Ca a marché.

### Ce que j'en retiens
Le `.env.example` c'est un fichier de documentation, pas une copie du `.env`. Et le `.gitignore` doit etre configuré **avant** le premier commit, pas apres. C'est le genre de leçon que tu oublies pas.

### Remarques
J'ai failli faire un `git push --force` a un moment pour resoudre le conflit. Heureusement j'ai pas fait ça parce que ça aurait pu etre pire. Ca m'a appris a pas foncer tete baissée avec git quand on comprend pas le probleme.

---

## Session 7 — Ajout des features avancées

### Ce que je voulais faire
Le projet marchait bien mais je trouvais qu'il manquait des trucs pour le rendre plus complet et plus impressionnant. J'ai listé 6 idées et j'en ai gardé 4 : un diff visuel pour le mode auto-fix, un dashboard avec des graphiques, l'export PDF des rapports, et l'analyse multi-fichier via upload de .zip.

### Comment j'ai travaillé avec l'IA
Pour le **diff visuel** j'ai demandé : *« Ajoute un diff unifié entre le code original et le code fixé en utilisant difflib, stylé pour un theme dark avec rouge pour les suppressions et vert pour les ajouts »*. Ca a bien marché du premier coup. `difflib` est dans la lib standard de Python donc pas de dependance en plus. Le rendu ressemble a ce qu'on voit sur GitHub. Ca parait tellement logique je sais pas pourquoi j'ai pas fait ça des le debut.

Pour le **dashboard** j'ai hesité entre Altair et Plotly. J'ai demandé a Copilot : *« Fais moi un dashboard analytique avec plotly : score au fil du temps, repartition par severité en donut, langages analysés en bar chart, et distribution des scores en histogramme. Theme dark #0d1117 »*. ce qui est bien c'est que j'ai pas eu a toucher a la base de données — toutes les infos etaient deja dans la table `ReviewRecord`.

Pour le **PDF** j'ai d'abord essayé `reportlab` mais c'etait vraiment trop verbeux. J'ai demandé : *« Remplace reportlab par fpdf2 pour generer un PDF simple avec le score, les issues et les suggestions »*. En genre 30 lignes j'avais un rapport propre.

Le **multi-fichier** c'est juste du `zipfile`. L'app extrait les fichiers sources du .zip, les filtre, et les analyse un par un avec une progress bar. J'ai pas parallélisé parce que avec 50 requetes/jour ca aurait atteindre la quota.

### Ce qui a bloqué ou changé
Deux trucs betes. D'abord le CSS : quand j'ai ajouté les nouveaux onglets, les labels "Language", "Action" etc etaient invisibles — gris foncé sur fond noir. J'ai du ajouter des overrides CSS avec des selecteurs `[data-testid]`. C'est pas propre mais Streamlit donne pas d'autre moyen.

Ensuite quand je suis passé de 3 a 5 onglets, le destructuring `tab_editor, tab_upload, tab_mcp = st.tabs(...)` s'est cassé parce que y'avait plus 3 mais 5 variables. Le genre de bug qui te bloque 10 minutes alors que la correction prend 2 secondes.

### Ce que j'en retiens
Ces 4 features sont pas tres complexes individuellement mais elles changent vraiment la perception du projet. Le diff aurait du etre la des le debut. Le dashboard montre que les données stockées servent a quelque chose. Et le multi-fichier fait passer l'outil d'un truc pour un fichier a quelque chose qui geree un petit projet.

### Remarques
`app.py` fait maintenant plus de 1500 lignes. C'est clairement trop. Si je continuais le projet, la premiere chose serait de decouper en composants separés. J'aurais du le faire bien plus tôt mais a ce stade c'est trop de refactoring pour le temps qu'il reste.

---

## Bilan

Techniquement y'a pas mal de trucs que je connaissais pas avant :
- Le MCP avec FastMCP — la distinction entre tools, resources et prompts c'est pas evident au debut
- L'API REST GitHub avec httpx et le Bearer token
- Que `asyncio.gather()` c'est pas toujours la bonne idée quand on a des rate limits
- Le parsing defensif du JSON quand on recoit des reponses de LLM
- Des commandes git que j'utilisais jamais (amend, soft reset, push protection)
- Plotly pour les charts, fpdf2 pour les PDFs, difflib pour les diffs

Pour le travail avec l'IA (Copilot / ChatGPT) : c'est utile pour generer du code vite mais faut pas se reposer a 100% dessus. Des fois il genere des fautes (les parametres FastMCP) et si tu verifies pas tu perds du temps. Le plus important c'est d'etre precis dans ses prompts — un prompt vague ça donne du code vague et des retours inutiles.

Si c'etait a refaire :
- Le `.gitignore` et les fichiers d'exemple : a configurer **avant** le premier commit. 
- Un seul appel API combiné des le debut au lieu de 3 separés
- Decouper `app.py` en modules bien plus tôt
- Le diff visuel des le mode Fix, c'est tellement evident

Un truc qui me derange encore : le modele `gemma-3-4b-it` c'est pas super fiable. Des fois le JSON sort parfaitement, des fois il retourne n'importe quoi. Pour un vrai projet faudrait passer a GPT-4o mini ou quelque chose comme ça, mais ça implique de payer. Pour le TP c'est suffisant pour montrer que l'architecture marche, mais c'est clairement pas production-ready.
