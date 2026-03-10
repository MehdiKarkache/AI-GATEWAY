import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from src.aggregator import validate_syntax, run_analysis
from src.db import init_db, save_review, get_recent_reviews, delete_review, delete_all_reviews
from src.models import Severity

init_db()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Code Review Assistant",
    layout="wide",
)

st.title("Code Review Assistant")
st.caption("Analyse automatique : bugs  securite  lisibilite")

# ── Constantes ────────────────────────────────────────────────────────────────
SEVERITY_LABEL = {
    Severity.CRITICAL: "CRITIQUE",
    Severity.MAJOR:    "MAJEUR",
    Severity.MINOR:    "MINEUR",
}

CATEGORY_LABEL = {
    "bug":        "bug",
    "securite":   "security",
    "lisibilite": "style",
}

SEVERITY_COLOR = {
    Severity.CRITICAL: "#c0392b",
    Severity.MAJOR:    "#e67e22",
    Severity.MINOR:    "#f1c40f",
}

SEVERITY_TEXT_COLOR = {
    Severity.CRITICAL: "#fff",
    Severity.MAJOR:    "#fff",
    Severity.MINOR:    "#1a1a1a",
}

CATEGORY_COLOR = {
    "bug":        "#e74c3c",
    "securite":   "#3498db",
    "lisibilite": "#2ecc71",
}

LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java",
    "C", "C++", "C#", "Go", "Rust", "PHP", "Ruby", "Kotlin", "Swift",
]

LANG_SYNTAX = {
    "Python": "python", "JavaScript": "javascript", "TypeScript": "typescript",
    "Java": "java", "C": "c", "C++": "cpp", "C#": "csharp",
    "Go": "go", "Rust": "rust", "PHP": "php", "Ruby": "ruby",
    "Kotlin": "kotlin", "Swift": "swift",
}

EXT_TO_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".java": "Java",
    ".c": "C", ".cpp": "C++", ".cs": "C#", ".go": "Go", ".rs": "Rust",
    ".php": "PHP", ".rb": "Ruby", ".kt": "Kotlin", ".swift": "Swift",
}


# ── Carte issue style IDE ─────────────────────────────────────────────────────
def _issue_card(issue, idx: int, syntax: str):
    sev_color  = SEVERITY_COLOR[issue.severity]
    sev_txt    = SEVERITY_TEXT_COLOR[issue.severity]
    sev_label  = SEVERITY_LABEL[issue.severity]
    cat_color  = CATEGORY_COLOR.get(issue.category.value, "#aaa")
    cat_label  = CATEGORY_LABEL.get(issue.category.value, issue.category.value)
    line_info  = f"L{issue.line_number}" if issue.line_number else "global"

    header_html = f"""
    <div style="
        background:#1e1e2e;
        border-left:3px solid {sev_color};
        padding:10px 14px;
        border-radius:0 6px 6px 0;
        margin-bottom:4px;
        font-family:monospace;
    ">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span style="color:#6272a4;font-size:12px">#{idx:02d}</span>
            <span style="background:{sev_color};color:{sev_txt};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;letter-spacing:.5px">{sev_label}</span>
            <span style="background:#2c3e50;color:{cat_color};padding:2px 8px;border-radius:4px;font-size:11px;font-family:monospace">{cat_label}</span>
            <span style="color:#cdd6f4;font-weight:600;font-size:13px">{issue.title}</span>
            <span style="margin-left:auto;color:#6272a4;font-size:11px;font-family:monospace">{line_info}</span>
        </div>
    </div>
    """
    with st.expander(f"#{idx:02d}  {issue.title}  [{sev_label}]  {line_info}", expanded=False):
        st.markdown(header_html, unsafe_allow_html=True)
        col_exp, col_fix = st.columns([1, 1])
        with col_exp:
            st.markdown("**Diagnostic**")
            st.info(issue.explanation)
        with col_fix:
            st.markdown("**Correction suggeree**")
            st.code(issue.suggestion, language=syntax)


# ── Affichage des resultats ───────────────────────────────────────────────────
def display_results(issues: list, filename: str, language: str):
    syntax = LANG_SYNTAX.get(language, language.lower())

    if not issues:
        st.success("Aucun probleme detecte.")
        save_review(filename, issues)
        return

    critical = [i for i in issues if i.severity == Severity.CRITICAL]
    major    = [i for i in issues if i.severity == Severity.MAJOR]
    minor    = [i for i in issues if i.severity == Severity.MINOR]
    score    = max(0, 100 - len(critical) * 25 - len(major) * 10 - len(minor) * 3)
    score_color = "#c0392b" if score < 50 else "#e67e22" if score < 75 else "#2ecc71"

    # Barre de statut
    status_html = f"""
    <div style="
        background:#181825;border-radius:8px;padding:12px 18px;
        display:flex;align-items:center;gap:24px;flex-wrap:wrap;
        border:1px solid #313244;margin-bottom:16px;font-family:monospace;
    ">
        <span style="color:#cdd6f4;font-size:13px"><b>{filename}</b></span>
        <span style="color:#6272a4;font-size:12px">|</span>
        <span style="color:#cdd6f4;font-size:13px">{language}</span>
        <span style="color:#6272a4;font-size:12px">|</span>
        <span style="color:#e74c3c;font-size:13px">{len(critical)} critique</span>
        <span style="color:#e67e22;font-size:13px">{len(major)} majeur</span>
        <span style="color:#f9e2af;font-size:13px;color:#b8a200">{len(minor)} mineur</span>
        <span style="margin-left:auto;font-size:13px">Score : <b style="color:{score_color}">{score}/100</b></span>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)

    # Filtres
    st.divider()
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_sev = st.multiselect(
            "Severite",
            ["Critique", "Majeur", "Mineur"],
            default=["Critique", "Majeur", "Mineur"],
            key=f"filter_sev_{filename}",
        )
    with col_f2:
        filter_cat = st.multiselect(
            "Categorie",
            ["Bug", "Securite", "Lisibilite"],
            default=["Bug", "Securite", "Lisibilite"],
            key=f"filter_cat_{filename}",
        )

    sev_map = {"Critique": Severity.CRITICAL, "Majeur": Severity.MAJOR, "Mineur": Severity.MINOR}
    cat_map = {"Bug": "bug", "Securite": "securite", "Lisibilite": "lisibilite"}
    sel_sevs = {sev_map[s] for s in filter_sev}
    sel_cats = {cat_map[c] for c in filter_cat}
    filtered = [i for i in issues if i.severity in sel_sevs and i.category.value in sel_cats]

    st.markdown(f"<p style='color:#6272a4;font-size:12px;font-family:monospace'>{len(filtered)} issue(s)</p>", unsafe_allow_html=True)
    for idx, issue in enumerate(filtered, 1):
        _issue_card(issue, idx, syntax)

    save_review(filename, issues)
    st.caption(f"Rapport sauvegarde — {filename}")


# ── Gestion des erreurs API ───────────────────────────────────────────────────
def _handle_error(msg: str):
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        st.error("Quota depasse. Attends 1 minute et reessaie.")
    elif "402" in msg or "credits" in msg.lower():
        st.error("Credits OpenRouter insuffisants.")
        st.info("Recharge sur openrouter.ai/settings/credits")
    else:
        st.error(f"Erreur : {msg}")


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_upload, tab_editor = st.tabs(["Upload fichier", "Ecrire du code"])

# ── Tab 1 : Upload ────────────────────────────────────────────────────────────
with tab_upload:
    uploaded_file = st.file_uploader(
        "Depose un fichier source",
        help="Formats supportes : .py .js .ts .java .c .cpp .cs .go .rs .php .rb .kt .swift — Limite : 500 lignes",
    )

    if uploaded_file:
        ext = "." + uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
        language = EXT_TO_LANG.get(ext, "Python")
        code = uploaded_file.read().decode("utf-8")

        if len(code.splitlines()) > 500:
            st.error(f"Le fichier fait {len(code.splitlines())} lignes. Limite : 500 lignes.")
            st.stop()

        st.caption(f"Langage detecte : {language}")
        with st.expander("Code source", expanded=False):
            st.code(code, language=LANG_SYNTAX.get(language, "text"), line_numbers=True)

        valid, error_msg = validate_syntax(code, language)
        if not valid:
            st.error(f"Erreur de syntaxe : {error_msg}")
            st.stop()

        if st.button("Lancer l'analyse", type="primary", key="btn_upload"):
            with st.spinner("Analyse en cours..."):
                try:
                    issues = asyncio.run(run_analysis(code, language))
                except Exception as e:
                    _handle_error(str(e))
                    st.stop()
            display_results(issues, uploaded_file.name, language)

# ── Tab 2 : Editeur ───────────────────────────────────────────────────────────
with tab_editor:
    col_lang, _ = st.columns([1, 3])
    with col_lang:
        language = st.selectbox("Langage", LANGUAGES, index=0)

    code_input = st.text_area(
        "Colle ou ecris ton code ici",
        height=320,
        placeholder="def hello():\n    print('Hello, world!')",
        key="editor_code",
    )

    if code_input.strip():
        if len(code_input.splitlines()) > 500:
            st.error("Le code depasse 500 lignes.")
        else:
            valid, error_msg = validate_syntax(code_input, language)
            if not valid:
                st.error(f"Erreur de syntaxe : {error_msg}")
            elif st.button("Lancer l'analyse", type="primary", key="btn_editor"):
                with st.spinner("Analyse en cours..."):
                    try:
                        issues = asyncio.run(run_analysis(code_input, language))
                    except Exception as e:
                        _handle_error(str(e))
                        st.stop()
                display_results(issues, f"editeur_{language.lower()}", language)

# ── Historique ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Historique")

    if st.button("Supprimer tout l'historique", key="del_all"):
        delete_all_reviews()
        st.rerun()

    records = get_recent_reviews(limit=20)
    if not records:
        st.info("Aucune analyse enregistree.")
    else:
        for r in records:
            col_info, col_del = st.columns([4, 1])
            with col_info:
                st.markdown(
                    f"**{r.filename}**  \n"
                    f"{r.critical_count} critique  {r.major_count} majeur  {r.minor_count} mineur  \n"
                    f"_{r.created_at[:16]}_"
                )
            with col_del:
                if st.button("X", key=f"del_{r.id}", help="Supprimer"):
                    delete_review(r.id)
                    st.rerun()
            st.divider()

