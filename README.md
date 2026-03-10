# Assistant de Code Review Multi-Critères

Analyse automatique de code Python sur 3 axes : **bugs**, **sécurité**, **lisibilité**.

---

## Installation

```bash
# 1. Cloner / ouvrir le dossier
cd code-review-assistant

# 2. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer la clé API
copy .env.example .env
# Ouvrir .env et remplacer sk-...ta_cle_ici par ta vraie clé OpenAI
```

---

## Utilisation

```bash
streamlit run app.py
```

L'interface s'ouvre dans le navigateur sur `http://localhost:8501`.

1. Dépose un fichier `.py` (max 500 lignes)
2. Clique sur **Lancer l'analyse**
3. Consulte le rapport trié par sévérité
4. L'historique des analyses est visible dans la barre latérale

---

## Structure

```
code-review-assistant/
├── app.py                  # Interface Streamlit
├── requirements.txt
├── .env.example            # Modèle de config (copier en .env)
├── src/
│   ├── analyzers/
│   │   ├── bugs.py         # Prompt spécialisé bugs
│   │   ├── security.py     # Prompt spécialisé sécurité
│   │   └── style.py        # Prompt spécialisé lisibilité
│   ├── aggregator.py       # Fusion + tri par sévérité
│   ├── models.py           # Schémas Pydantic
│   └── db.py               # Persistance SQLite
└── tests/
    ├── test_analyzers.py
    └── fixtures/           # Fichiers de test
```

---

## Lancer les tests

```bash
pytest tests/ -v
```

---

## Variables d'environnement

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Clé API OpenAI (obligatoire) |
