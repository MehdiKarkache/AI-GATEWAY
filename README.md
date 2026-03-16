# Assistant de Code Review Multi-Criteres

Analyse automatique de code sur 3 axes : **bugs**, **securite**, **lisibilite**.
Disponible en **interface Streamlit**, **serveur MCP** (Model Context Protocol),
**client Python** et **CLI**.

---

## Installation

```bash
# 1. Cloner / ouvrir le dossier
cd code-review-assistant

# 2. Creer un environnement virtuel
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Installer les dependances
pip install -r requirements.txt

# 4. Configurer la cle API
copy .env.example .env
# Ouvrir .env et ajouter ta cle OpenRouter
```

---

## Utilisation

### Interface Streamlit

```bash
streamlit run app.py
```

L'interface s'ouvre sur `http://localhost:8501` avec 3 onglets :

1. **Upload** — Depose un fichier source pour analyse
2. **Editeur** — Ecris ou colle du code directement
3. **MCP Console** — Interaction directe avec le serveur MCP (introspection, review, stats, export, comparaison)

L'historique est visible dans la barre laterale.

### Serveur MCP (Model Context Protocol)

Le serveur MCP expose 7 tools, 3 resources et 2 prompts.

#### Demarrage

```bash
# Mode stdio (defaut — pour VS Code, Claude Desktop, etc.)
python -m src.mcp_server

# Mode SSE (HTTP pour clients distants)
python -m src.mcp_server --sse --port 8080
```

#### Configuration VS Code (Copilot)

Le fichier `.vscode/mcp.json` est inclus. VS Code detecte automatiquement le serveur.

#### Configuration Claude Desktop

Ajoute dans `claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "code-review-assistant": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/chemin/vers/code-review-assistant",
      "env": {
        "OPENROUTER_API_KEY": "ta-cle-ici"
      }
    }
  }
}
```

#### Tools MCP (7)

| Tool | Description |
|---|---|
| `review_code` | Analyse multi-criteres (bugs, securite, style). Retourne score + issues JSON |
| `check_syntax` | Validation de syntaxe (profonde pour Python, acceptation pour les autres) |
| `get_review_history` | Derniers rapports d'analyse enregistres |
| `get_review_details` | Detail complet d'un rapport par ID |
| `delete_review` | Suppression d'un rapport par ID |
| `compare_reviews` | Compare deux rapports cote a cote (delta scores, evolution) |
| `export_report` | Exporte un rapport en Markdown ou JSON |

#### Resources MCP (3)

| Resource | Description |
|---|---|
| `review://history` | Liste compacte des 20 derniers rapports avec scores |
| `review://supported-languages` | 13 langages supportes (JSON) |
| `review://stats` | Statistiques globales (score moyen, meilleur, pire, totaux) |

#### Prompts MCP (2)

| Prompt | Description |
|---|---|
| `code_review` | Template de revue de code multi-criteres |
| `security_audit` | Audit de securite approfondi OWASP |

### Client Python

```python
from src.mcp_client import MCPClient

async with MCPClient() as client:
    # Introspection
    tools = await client.list_tools()
    resources = await client.list_resources()
    prompts = await client.list_prompts()

    # Review
    result = await client.review_code("def f(): pass", "Python")
    print(result["score"])

    # Historique, details, comparaison, export
    history = await client.get_history(limit=5)
    details = await client.get_details(review_id=1)
    comparison = await client.compare(id_a=1, id_b=2)
    markdown = await client.export(review_id=1, fmt="markdown")

    # Resources
    stats = await client.get_stats()
    langs = await client.get_languages()

    # Prompts
    prompt = await client.get_prompt("security_audit", {"code": "...", "language": "Python"})
```

Transport SSE :
```python
async with MCPClient(transport="sse", sse_url="http://127.0.0.1:8080/sse") as client:
    ...
```

### CLI

```bash
# Introspection
python -m src.mcp_cli tools
python -m src.mcp_cli resources
python -m src.mcp_cli prompts

# Analyse
python -m src.mcp_cli review mon_fichier.py
python -m src.mcp_cli review script.js --lang JavaScript
python -m src.mcp_cli syntax mon_fichier.py

# Historique / details
python -m src.mcp_cli history --limit 10
python -m src.mcp_cli details 3
python -m src.mcp_cli stats
python -m src.mcp_cli langs

# Comparaison / export
python -m src.mcp_cli compare 1 2
python -m src.mcp_cli export 3 --format markdown
python -m src.mcp_cli export 3 --format json

# Suppression
python -m src.mcp_cli delete 5
```

---

## Structure

```
code-review-assistant/
├── app.py                       # Interface Streamlit (3 tabs: upload, editeur, MCP)
├── mcp.json                     # Config MCP (Claude Desktop)
├── requirements.txt
├── .env                         # OPENROUTER_API_KEY
├── .vscode/
│   └── mcp.json                 # Config MCP pour VS Code
├── src/
│   ├── __init__.py              # load_dotenv(override=True)
│   ├── mcp_server.py            # Serveur MCP v2 (7 tools, 3 resources, 2 prompts)
│   ├── mcp_client.py            # Client MCP async (stdio + SSE)
│   ├── mcp_cli.py               # CLI interactive
│   ├── aggregator.py            # Fusion + tri par severite
│   ├── models.py                # Schemas Pydantic
│   ├── db.py                    # Persistance SQLite
│   └── analyzers/
│       ├── __init__.py          # extract_json()
│       ├── bugs.py              # Analyse bugs
│       ├── security.py          # Analyse securite
│       └── style.py             # Analyse lisibilite
└── tests/
    ├── test_analyzers.py        # 5 tests aggregateur
    ├── test_mcp_server.py       # 27 tests serveur MCP v2
    ├── test_integration_mcp.py  # 9 tests integration client ↔ serveur
    └── fixtures/
```

---

## Tests

```bash
# Tous les tests (41)
pytest tests/ -v

# Unitaires seulement
pytest tests/test_analyzers.py tests/test_mcp_server.py -v

# Integration MCP (client ↔ serveur via stdio)
pytest tests/test_integration_mcp.py -v
```

41 tests : 5 aggregateur + 27 MCP server + 9 integration.

---

## Variables d'environnement

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Cle API OpenRouter (obligatoire) |

---

## Langages supportes

Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, PHP, Ruby, Kotlin, Swift
