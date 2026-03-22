import streamlit as st
import asyncio
import os
import difflib
import io
import json
import zipfile
from dotenv import load_dotenv
load_dotenv(override=True)

from src.aggregator import validate_syntax, run_analysis
from src.db import init_db, save_review, get_recent_reviews, delete_review, delete_all_reviews
from src.models import Severity

init_db()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Code Review Assistant",
    page_icon="",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* ── White text for dark-background elements ── */
.stSelectbox label, .stMultiSelect label, .stFileUploader label,
.stTextArea label, .stTextInput label, .stRadio label, .stNumberInput label {
    color: #ffffff !important;
}
[data-baseweb="select"] * {
    color: #ffffff !important;
}
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* ── Tabs ── */
.stTabs [role="tablist"] {
    border-bottom: 1px solid #2d2d3f;
    gap: 0;
    padding: 0 8px;
}
.stTabs [role="tab"] {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: #6272a4;
    font-size: 13px;
    font-weight: 500;
    padding: 10px 20px;
    transition: all .15s;
}
.stTabs [aria-selected="true"] {
    color: #cdd6f4 !important;
    border-bottom: 2px solid #6c63ff !important;
    background: transparent !important;
}
.stTabs [role="tab"]:hover {
    color: #a6adc8;
}

/* ── Primary button ── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #6c63ff 0%, #574fd6 100%);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-weight: 600;
    font-size: 13px;
    padding: 10px 24px;
    transition: all .2s;
    box-shadow: 0 2px 8px rgba(108, 99, 255, .25);
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #574fd6 0%, #4a3fc7 100%);
    box-shadow: 0 4px 16px rgba(108, 99, 255, .35);
    transform: translateY(-1px);
}

/* ── Secondary buttons ── */
.stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 6px;
    color: #cdd6f4;
    font-size: 12px;
    padding: 6px 12px;
    transition: all .15s;
}
.stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover {
    background: #2a2a3e;
    border-color: #454158;
}

/* ── IDE Text area ── */
textarea {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    color: #c9d1d9 !important;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    padding: 16px !important;
    tab-size: 4;
    letter-spacing: 0.02em;
}
textarea:focus {
    border-color: #6c63ff !important;
    box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.15) !important;
}
/* Label above text area */
.stTextArea label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    color: #6272a4 !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0d1117;
    border: 2px dashed #21262d;
    border-radius: 10px;
    padding: 16px;
    transition: border-color .2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: #6c63ff;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px !important;
    color: #c9d1d9 !important;
    padding: 10px 16px !important;
}
.streamlit-expanderContent {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #21262d;
}

/* ── Multiselect ── */
.stMultiSelect span[data-baseweb="tag"] {
    background: #21262d !important;
    color: #c9d1d9 !important;
    border-radius: 6px;
    font-size: 11px;
}

/* ── Selectbox ── */
[data-baseweb="select"] > div {
    background: #161b22 !important;
    border-color: #21262d !important;
    border-radius: 8px !important;
}

/* ── Divider ── */
hr { border-color: #21262d !important; margin: 8px 0; }

/* ── Alert ── */
.stAlert { border-radius: 8px !important; font-size: 13px !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px !important;
}

/* ── Code blocks ── */
pre {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
}
code {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

/* ── Caption ── */
.stCaption { color: #484f58 !important; font-size: 11px !important; }

/* ── Hide menu + footer ── */
#MainMenu, footer { visibility: hidden; }

/* ── Custom scrollbar ── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #21262d; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #30363d; }

/* ── Number input ── */
.stNumberInput input {
    background: #161b22 !important;
    border-color: #21262d !important;
    color: #c9d1d9 !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    display:flex; align-items:center; justify-content:space-between;
    padding:12px 0 20px 0; border-bottom:1px solid #21262d; margin-bottom:28px;
">
    <div>
        <h1 style="margin:0;color:#c9d1d9;font-size:1.6rem;font-weight:700;letter-spacing:-0.02em">
            Code Review Assistant
        </h1>
        <p style="margin:6px 0 0 0;color:#484f58;font-size:13px">
            Automated code analysis &nbsp;·&nbsp; bugs &nbsp;·&nbsp; security &nbsp;·&nbsp; readability &nbsp;·&nbsp; auto-fix
        </p>
    </div>
    <div style="display:flex;gap:10px;align-items:center">
        <span style="
            background:#161b22; border:1px solid #21262d; border-radius:20px;
            padding:6px 14px; font-family:'JetBrains Mono',monospace; font-size:11px;
            color:#6272a4;
        ">MCP v3 &nbsp;·&nbsp; 11 tools</span>
        <span style="
            background:#161b22; border:1px solid #21262d; border-radius:20px;
            padding:6px 14px; font-family:'JetBrains Mono',monospace; font-size:11px;
            color:#484f58;
        ">gemma-3-4b &nbsp;·&nbsp; OpenRouter</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
SEVERITY_LABEL = {
    Severity.CRITICAL: "CRITICAL",
    Severity.MAJOR:    "MAJOR",
    Severity.MINOR:    "MINOR",
}

CATEGORY_LABEL = {
    "bug":        "bug",
    "securite":   "security",
    "lisibilite": "style",
}

SEVERITY_COLOR = {
    Severity.CRITICAL: "#f85149",
    Severity.MAJOR:    "#d29922",
    Severity.MINOR:    "#58a6ff",
}

SEVERITY_BG = {
    Severity.CRITICAL: "#3d1117",
    Severity.MAJOR:    "#3d2b10",
    Severity.MINOR:    "#0d2240",
}

CATEGORY_COLOR = {
    "bug":        "#f85149",
    "securite":   "#a371f7",
    "lisibilite": "#3fb950",
}

CATEGORY_BG = {
    "bug":        "#3d1117",
    "securite":   "#271844",
    "lisibilite": "#0d2818",
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


# ── Visual Diff helper ────────────────────────────────────────────────────────
def _render_diff(original: str, fixed: str):
    """Render a side-by-side diff between original and fixed code."""
    orig_lines = original.splitlines()
    fixed_lines = fixed.splitlines()
    diff = list(difflib.unified_diff(orig_lines, fixed_lines, lineterm="", n=3))

    if not diff:
        st.info("No differences found — code is identical.")
        return

    html_lines = []
    for line in diff[2:]:  # skip --- +++ headers
        if line.startswith("@@"):
            html_lines.append(
                f"<div style='background:#161b22;color:#8b949e;padding:4px 12px;"
                f"font-size:11px;font-family:monospace;border-top:1px solid #21262d;"
                f"border-bottom:1px solid #21262d;margin:4px 0'>{line}</div>"
            )
        elif line.startswith("-"):
            escaped = line[1:].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_lines.append(
                f"<div style='background:#3d1117;color:#f85149;padding:2px 12px;"
                f"font-size:12px;font-family:\"JetBrains Mono\",monospace;white-space:pre'>"
                f"- {escaped}</div>"
            )
        elif line.startswith("+"):
            escaped = line[1:].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_lines.append(
                f"<div style='background:#0d2818;color:#3fb950;padding:2px 12px;"
                f"font-size:12px;font-family:\"JetBrains Mono\",monospace;white-space:pre'>"
                f"+ {escaped}</div>"
            )
        else:
            escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_lines.append(
                f"<div style='color:#8b949e;padding:2px 12px;"
                f"font-size:12px;font-family:\"JetBrains Mono\",monospace;white-space:pre'>"
                f"  {escaped}</div>"
            )

    st.markdown(
        "<p style='color:#484f58;font-size:10px;font-family:monospace;"
        "text-transform:uppercase;letter-spacing:1px;margin-top:16px;margin-bottom:4px'>DIFF VIEW</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:10px;"
        f"overflow:hidden;max-height:500px;overflow-y:auto'>{''.join(html_lines)}</div>",
        unsafe_allow_html=True,
    )


# ── PDF Export helper ─────────────────────────────────────────────────────────
def _generate_pdf(issues, filename, score):
    """Generate a PDF report and return the bytes."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Code Review Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"File: {filename}    Score: {score}/100", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Summary counts
    from src.models import Severity as Sev
    crit = sum(1 for i in issues if i.severity == Sev.CRITICAL)
    maj = sum(1 for i in issues if i.severity == Sev.MAJOR)
    minor = sum(1 for i in issues if i.severity == Sev.MINOR)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, f"Issues: {len(issues)} total  |  {crit} critical  |  {maj} major  |  {minor} minor",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Issues
    for idx, issue in enumerate(issues, 1):
        sev = SEVERITY_LABEL.get(issue.severity, "?")
        cat = CATEGORY_LABEL.get(issue.category.value, "?")
        line = f"L{issue.line_number}" if issue.line_number else "global"

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, f"#{idx}  [{sev}] [{cat}]  {line} - {issue.title}", new_x="LMARGIN", new_y="NEXT", fill=True)

        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, f"Explanation: {issue.explanation}")
        pdf.set_font("Courier", "", 8)
        pdf.multi_cell(0, 4, f"Suggestion: {issue.suggestion}")
        pdf.ln(2)

    return pdf.output()


# ── Issue card ────────────────────────────────────────────────────────────────
def _issue_card(issue, idx: int, syntax: str):
    sev_color = SEVERITY_COLOR[issue.severity]
    sev_bg    = SEVERITY_BG[issue.severity]
    sev_label = SEVERITY_LABEL[issue.severity]
    cat_color = CATEGORY_COLOR.get(issue.category.value, "#8b949e")
    cat_bg    = CATEGORY_BG.get(issue.category.value, "#161b22")
    cat_label = CATEGORY_LABEL.get(issue.category.value, issue.category.value)
    line_info = f":{issue.line_number}" if issue.line_number else ""

    header_html = f"""
    <div style="
        background:#161b22;
        border-left: 3px solid {sev_color};
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 2px;
        font-family: 'JetBrains Mono', monospace;
    ">
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <span style="color:#484f58; font-size:11px; min-width:28px">#{idx:02d}</span>
            <span style="
                background:{sev_bg}; color:{sev_color};
                padding:2px 10px; border-radius:20px;
                font-size:10px; font-weight:600; letter-spacing:.5px;
                border: 1px solid {sev_color}33;
            ">{sev_label}</span>
            <span style="
                background:{cat_bg}; color:{cat_color};
                padding:2px 10px; border-radius:20px;
                font-size:10px; font-family:monospace;
                border: 1px solid {cat_color}33;
            ">{cat_label}</span>
            <span style="color:#c9d1d9; font-weight:600; font-size:13px; flex:1">{issue.title}</span>
            <span style="
                color:#484f58; font-size:11px; font-family:monospace;
                background:#0d1117; padding:2px 8px; border-radius:4px;
            ">{syntax}{line_info}</span>
        </div>
    </div>
    """

    with st.expander(f"  #{idx:02d}  {issue.title}  [{sev_label}]{line_info}", expanded=False):
        st.markdown(header_html, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        col_exp, col_fix = st.columns([1, 1], gap="medium")
        with col_exp:
            st.markdown(
                "<span style='color:#484f58;font-size:10px;font-family:monospace;"
                "text-transform:uppercase;letter-spacing:1px'>DIAGNOSTIC</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;"
                f"padding:12px 14px;font-size:13px;color:#c9d1d9;line-height:1.6'>{issue.explanation}</div>",
                unsafe_allow_html=True,
            )
        with col_fix:
            st.markdown(
                "<span style='color:#484f58;font-size:10px;font-family:monospace;"
                "text-transform:uppercase;letter-spacing:1px'>SUGGESTED FIX</span>",
                unsafe_allow_html=True,
            )
            st.code(issue.suggestion, language=syntax)


# ── Display results ───────────────────────────────────────────────────────────
def display_results(issues: list, filename: str, language: str):
    syntax = LANG_SYNTAX.get(language, language.lower())

    if not issues:
        st.markdown("""
        <div style="background:#0d2818;border:1px solid #238636;border-radius:10px;
                    padding:16px 20px;color:#3fb950;font-size:13px;display:flex;align-items:center;gap:10px">
            <span style="font-size:18px">&#10003;</span>
            <span>No issues found — code looks clean!</span>
        </div>
        """, unsafe_allow_html=True)
        save_review(filename, issues)
        return

    critical = [i for i in issues if i.severity == Severity.CRITICAL]
    major    = [i for i in issues if i.severity == Severity.MAJOR]
    minor    = [i for i in issues if i.severity == Severity.MINOR]
    score    = max(0, 100 - len(critical) * 25 - len(major) * 10 - len(minor) * 3)
    score_color = "#f85149" if score < 50 else "#d29922" if score < 75 else "#3fb950"

    # Status bar
    st.markdown(f"""
    <div style="
        background:#161b22; border-radius:10px; padding:16px 24px;
        display:flex; align-items:center; gap:24px; flex-wrap:wrap;
        border:1px solid #21262d; margin-bottom:20px;
    ">
        <span style="color:#c9d1d9;font-size:14px;font-weight:600">{filename}</span>
        <span style="color:#21262d;font-size:16px">|</span>
        <span style="
            background:#161b22;border:1px solid #21262d;border-radius:20px;
            padding:2px 12px;color:#8b949e;font-size:11px;font-family:monospace;
        ">{language}</span>
        <div style="display:flex;gap:16px;align-items:center">
            <span style="color:#f85149;font-size:12px;font-family:monospace">
                <span style="font-size:14px;font-weight:700">{len(critical)}</span> critical
            </span>
            <span style="color:#d29922;font-size:12px;font-family:monospace">
                <span style="font-size:14px;font-weight:700">{len(major)}</span> major
            </span>
            <span style="color:#58a6ff;font-size:12px;font-family:monospace">
                <span style="font-size:14px;font-weight:700">{len(minor)}</span> minor
            </span>
        </div>
        <span style="margin-left:auto;display:flex;align-items:baseline;gap:4px">
            <span style="color:#484f58;font-size:11px;font-family:monospace">score</span>
            <span style="color:{score_color};font-size:22px;font-weight:700;font-family:'JetBrains Mono',monospace">{score}</span>
            <span style="color:#30363d;font-size:13px">/100</span>
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Filters
    col_f1, col_f2 = st.columns(2, gap="medium")
    with col_f1:
        filter_sev = st.multiselect(
            "Severity",
            ["Critical", "Major", "Minor"],
            default=["Critical", "Major", "Minor"],
            key=f"filter_sev_{filename}",
        )
    with col_f2:
        filter_cat = st.multiselect(
            "Category",
            ["Bug", "Security", "Readability"],
            default=["Bug", "Security", "Readability"],
            key=f"filter_cat_{filename}",
        )

    sev_map = {"Critical": Severity.CRITICAL, "Major": Severity.MAJOR, "Minor": Severity.MINOR}
    cat_map = {"Bug": "bug", "Security": "securite", "Readability": "lisibilite"}
    sel_sevs = {sev_map[s] for s in filter_sev}
    sel_cats = {cat_map[c] for c in filter_cat}
    filtered = [i for i in issues if i.severity in sel_sevs and i.category.value in sel_cats]

    st.markdown(
        f"<p style='color:#484f58;font-size:11px;font-family:monospace;margin:12px 0 6px'>"
        f"{len(filtered)} issue(s)</p>",
        unsafe_allow_html=True,
    )
    for idx, issue in enumerate(filtered, 1):
        _issue_card(issue, idx, syntax)

    # PDF export button
    try:
        pdf_bytes = _generate_pdf(issues, filename, score)
        st.download_button(
            label="Export PDF Report",
            data=pdf_bytes,
            file_name=f"review_{filename.replace('.', '_')}.pdf",
            mime="application/pdf",
            key=f"pdf_{filename}",
        )
    except Exception:
        pass  # fpdf2 not installed — silently skip

    save_review(filename, issues)


# ── Error handler ─────────────────────────────────────────────────────────────
def _handle_error(msg: str):
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "rate" in msg.lower():
        st.warning("⏳ Rate limit hit — retrying automatically (up to 3 attempts with backoff)…")
        st.info("Free models have strict limits. If this persists, wait ~30 seconds and retry.")
    elif "402" in msg or "credits" in msg.lower():
        st.error("Insufficient OpenRouter credits. Top up at openrouter.ai/settings/credits")
    else:
        st.error(f"Error: {msg}")


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_editor, tab_upload, tab_multi, tab_dashboard, tab_mcp = st.tabs([
    "Code Editor", "Upload File", "Multi-File", "Dashboard", "MCP Console",
])

# ── Tab 1 : Code Editor (PRIMARY — IDE-style) ─────────────────────────────────
with tab_editor:
    # Top bar
    col_lang, col_action, _ = st.columns([1, 1, 2])
    with col_lang:
        language = st.selectbox("Language", LANGUAGES, index=0, key="editor_lang")
    with col_action:
        action_mode = st.selectbox("Action", ["Review", "Fix Code", "Explain Code", "Generate Tests"], key="editor_action")

    # Editor header
    st.markdown(f"""
    <div style="
        background:#161b22;border:1px solid #21262d;border-bottom:none;
        border-radius:10px 10px 0 0;padding:8px 16px;
        display:flex;align-items:center;gap:12px;margin-top:8px;
    ">
        <div style="display:flex;gap:6px">
            <span style="width:12px;height:12px;border-radius:50%;background:#f85149;display:inline-block"></span>
            <span style="width:12px;height:12px;border-radius:50%;background:#d29922;display:inline-block"></span>
            <span style="width:12px;height:12px;border-radius:50%;background:#3fb950;display:inline-block"></span>
        </div>
        <span style="color:#484f58;font-size:11px;font-family:'JetBrains Mono',monospace">
            editor.{LANG_SYNTAX.get(language, 'txt')} — {language}
        </span>
        <span style="margin-left:auto;color:#30363d;font-size:10px;font-family:monospace">
            UTF-8 &nbsp;·&nbsp; LF &nbsp;·&nbsp; Spaces: 4
        </span>
    </div>
    """, unsafe_allow_html=True)

    code_input = st.text_area(
        f"{language} source code",
        height=450,
        placeholder="// Paste or type your code here...\n// The editor supports all 13 languages.\n// Use the Action dropdown to Review, Fix, or get Suggestions.",
        key="editor_code",
        label_visibility="collapsed",
    )

    # Bottom bar
    line_count = len(code_input.splitlines()) if code_input.strip() else 0
    char_count = len(code_input) if code_input.strip() else 0
    st.markdown(f"""
    <div style="
        background:#161b22;border:1px solid #21262d;border-top:none;
        border-radius:0 0 10px 10px;padding:6px 16px;margin-bottom:16px;
        display:flex;align-items:center;gap:16px;
    ">
        <span style="color:#484f58;font-size:10px;font-family:monospace">
            Ln {line_count} &nbsp;·&nbsp; {char_count} chars
        </span>
        <span style="color:#30363d;font-size:10px;font-family:monospace">
            {language} &nbsp;·&nbsp; {action_mode}
        </span>
        <span style="margin-left:auto;color:#30363d;font-size:10px;font-family:monospace">
            max 500 lines
        </span>
    </div>
    """, unsafe_allow_html=True)

    if code_input.strip():
        if len(code_input.splitlines()) > 500:
            st.error("Code exceeds 500 lines limit.")
        else:
            valid, error_msg = validate_syntax(code_input, language)
            if not valid:
                st.error(f"Syntax error: {error_msg}")
            else:
                btn_label = {"Review": "Run Analysis", "Fix Code": "Auto-Fix", "Explain Code": "Explain", "Generate Tests": "Generate"}
                if st.button(btn_label[action_mode], type="primary", key="btn_editor"):

                    if action_mode == "Review":
                        status = st.status("Analyzing code…", expanded=True)
                        try:
                            def _progress(msg):
                                status.update(label=msg)
                            issues = asyncio.run(run_analysis(code_input, language, progress_callback=_progress))
                            status.update(label="Analysis complete", state="complete", expanded=False)
                        except Exception as e:
                            status.update(label="Analysis failed", state="error", expanded=False)
                            _handle_error(str(e))
                            st.stop()
                        display_results(issues, f"editor.{LANG_SYNTAX.get(language, 'txt')}", language)

                    elif action_mode == "Fix Code":
                        with st.spinner("Auto-fixing code..."):
                            try:
                                from src.mcp_server import fix_code as _fix_code
                                raw = asyncio.run(_fix_code(code_input, language))
                                import json
                                result = json.loads(raw)
                            except Exception as e:
                                _handle_error(str(e))
                                st.stop()

                        if "error" in result:
                            st.error(result["error"])
                        else:
                            # Score comparison
                            orig = result.get("original_score", 0)
                            fixed = result.get("fixed_score", 0)
                            delta = fixed - orig
                            delta_color = "#3fb950" if delta > 0 else "#f85149" if delta < 0 else "#8b949e"

                            st.markdown(f"""
                            <div style="background:#161b22;border:1px solid #21262d;border-radius:10px;
                                        padding:16px 24px;margin-bottom:16px;display:flex;align-items:center;gap:24px">
                                <div>
                                    <span style="color:#484f58;font-size:10px;font-family:monospace;text-transform:uppercase">
                                        Original Score
                                    </span><br/>
                                    <span style="color:#d29922;font-size:20px;font-weight:700;font-family:'JetBrains Mono'">{orig}</span>
                                </div>
                                <span style="color:#30363d;font-size:20px">&rarr;</span>
                                <div>
                                    <span style="color:#484f58;font-size:10px;font-family:monospace;text-transform:uppercase">
                                        Fixed Score
                                    </span><br/>
                                    <span style="color:#3fb950;font-size:20px;font-weight:700;font-family:'JetBrains Mono'">{fixed}</span>
                                </div>
                                <span style="color:{delta_color};font-size:14px;font-weight:600;font-family:monospace">
                                    {delta:+d} pts
                                </span>
                                <span style="margin-left:auto;color:#484f58;font-size:11px;font-family:monospace">
                                    {result.get('total_changes', 0)} changes applied
                                </span>
                            </div>
                            """, unsafe_allow_html=True)

                            # Changes list
                            for ch in result.get("changes", []):
                                sev = ch.get("severity", "mineur").upper()
                                sev_c = {"CRITIQUE": "#f85149", "MAJEUR": "#d29922", "MINEUR": "#58a6ff"}.get(sev, "#8b949e")
                                st.markdown(
                                    f"<div style='background:#0d1117;border-left:3px solid {sev_c};"
                                    f"padding:8px 14px;border-radius:0 6px 6px 0;margin-bottom:4px;"
                                    f"font-size:12px;font-family:monospace'>"
                                    f"<span style='color:{sev_c};font-weight:600'>L{ch.get('line','?')}</span> "
                                    f"<span style='color:#c9d1d9'>{ch.get('description','')}</span>"
                                    f"</div>",
                                    unsafe_allow_html=True,
                                )

                            # Fixed code
                            st.markdown("""
                            <p style='color:#484f58;font-size:10px;font-family:monospace;
                                       text-transform:uppercase;letter-spacing:1px;margin-top:16px'>
                                Fixed Code
                            </p>
                            """, unsafe_allow_html=True)
                            st.code(result.get("fixed_code", code_input), language=LANG_SYNTAX.get(language, "text"), line_numbers=True)

                            # Visual diff
                            _render_diff(code_input, result.get("fixed_code", code_input))

                    elif action_mode == "Explain Code":
                        with st.spinner("Explaining code..."):
                            try:
                                from src.mcp_server import explain_code as _explain
                                raw = asyncio.run(_explain(code_input, language, "medium"))
                                import json
                                result = json.loads(raw)
                            except Exception as e:
                                _handle_error(str(e))
                                st.stop()

                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.markdown(
                                f"<div style='background:#161b22;border:1px solid #21262d;border-radius:10px;"
                                f"padding:16px 24px;margin-bottom:16px'>"
                                f"<p style='color:#484f58;font-size:10px;font-family:monospace;"
                                f"text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>SUMMARY</p>"
                                f"<p style='color:#c9d1d9;font-size:14px;line-height:1.6'>{result.get('summary', '')}</p>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                            steps = result.get("step_by_step", [])
                            if steps:
                                st.markdown(
                                    "<p style='color:#484f58;font-size:10px;font-family:monospace;"
                                    "text-transform:uppercase;letter-spacing:1px;margin:12px 0 8px'>STEP BY STEP</p>",
                                    unsafe_allow_html=True,
                                )
                                for idx, step in enumerate(steps, 1):
                                    st.markdown(
                                        f"<div style='background:#0d1117;border-left:3px solid #58a6ff;"
                                        f"padding:8px 14px;border-radius:0 6px 6px 0;margin-bottom:4px;"
                                        f"font-size:13px;font-family:monospace'>"
                                        f"<span style='color:#58a6ff;font-weight:600'>{idx}.</span> "
                                        f"<span style='color:#c9d1d9'>{step}</span></div>",
                                        unsafe_allow_html=True,
                                    )

                            col_cx, col_kc = st.columns(2)
                            with col_cx:
                                complexity = result.get("complexity", "")
                                if complexity:
                                    st.markdown(
                                        f"<div style='background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 16px;margin-top:12px'>"
                                        f"<span style='color:#484f58;font-size:10px;font-family:monospace'>COMPLEXITY</span><br/>"
                                        f"<span style='color:#d29922;font-size:13px;font-family:monospace'>{complexity}</span></div>",
                                        unsafe_allow_html=True,
                                    )
                            with col_kc:
                                concepts = result.get("key_concepts", [])
                                if concepts:
                                    tags = " ".join(
                                        f"<span style='background:#0d2240;color:#58a6ff;padding:3px 10px;"
                                        f"border-radius:20px;font-size:11px;border:1px solid #58a6ff33;margin:2px'>{c}</span>"
                                        for c in concepts
                                    )
                                    st.markdown(
                                        f"<div style='margin-top:12px'>"
                                        f"<span style='color:#484f58;font-size:10px;font-family:monospace'>KEY CONCEPTS</span><br/>"
                                        f"<div style='display:flex;flex-wrap:wrap;gap:4px;margin-top:6px'>{tags}</div></div>",
                                        unsafe_allow_html=True,
                                    )

                    elif action_mode == "Generate Tests":
                        with st.spinner("Generating tests..."):
                            try:
                                from src.mcp_server import generate_tests as _gen_tests
                                raw = asyncio.run(_gen_tests(code_input, language, "auto"))
                                import json
                                result = json.loads(raw)
                            except Exception as e:
                                _handle_error(str(e))
                                st.stop()

                        if "error" in result:
                            st.error(result["error"])
                        else:
                            st.markdown(
                                f"<div style='background:#161b22;border:1px solid #21262d;border-radius:10px;"
                                f"padding:12px 24px;margin-bottom:16px;display:flex;align-items:center;gap:20px'>"
                                f"<span style='color:#3fb950;font-size:18px;font-weight:700;font-family:monospace'>"
                                f"{result.get('test_count', 0)}</span>"
                                f"<span style='color:#8b949e;font-size:13px'>tests generated</span>"
                                f"<span style='color:#30363d'>|</span>"
                                f"<span style='color:#58a6ff;font-size:12px;font-family:monospace'>"
                                f"{result.get('framework', 'auto')}</span>"
                                f"<span style='margin-left:auto;color:#484f58;font-size:11px'>"
                                f"{result.get('coverage_summary', '')[:100]}</span></div>",
                                unsafe_allow_html=True,
                            )
                            st.code(result.get("test_code", "# No tests generated"), language=LANG_SYNTAX.get(language, "text"), line_numbers=True)


# ── Tab 2 : Upload ────────────────────────────────────────────────────────────
with tab_upload:
    uploaded_file = st.file_uploader(
        "Drop a source file",
        help="Supported: .py .js .ts .java .c .cpp .cs .go .rs .php .rb .kt .swift — Max 500 lines",
    )

    if uploaded_file:
        ext = "." + uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
        language_up = EXT_TO_LANG.get(ext, "Python")
        code_up = uploaded_file.read().decode("utf-8")

        if len(code_up.splitlines()) > 500:
            st.error(f"File has {len(code_up.splitlines())} lines. Max: 500.")
            st.stop()

        st.markdown(
            f"<p style='color:#8b949e;font-size:12px;font-family:monospace;margin:8px 0'>"
            f"Detected: <b style='color:#c9d1d9'>{language_up}</b> &nbsp;·&nbsp; "
            f"{len(code_up.splitlines())} lines</p>",
            unsafe_allow_html=True,
        )
        with st.expander("View source", expanded=False):
            st.code(code_up, language=LANG_SYNTAX.get(language_up, "text"), line_numbers=True)

        valid_up, error_up = validate_syntax(code_up, language_up)
        if not valid_up:
            st.error(f"Syntax error: {error_up}")
            st.stop()

        col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 3])
        with col_btn1:
            do_review = st.button("Review", type="primary", key="btn_up_review")
        with col_btn2:
            do_fix = st.button("Auto-Fix", key="btn_up_fix")
        with col_btn3:
            do_gentest = st.button("Gen Tests", key="btn_up_gentest")

        if do_review:
            status = st.status("Analyzing…", expanded=True)
            try:
                def _progress_up(msg):
                    status.update(label=msg)
                issues = asyncio.run(run_analysis(code_up, language_up, progress_callback=_progress_up))
                status.update(label="Analysis complete", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Analysis failed", state="error", expanded=False)
                _handle_error(str(e))
                st.stop()
            display_results(issues, uploaded_file.name, language_up)

        if do_fix:
            with st.spinner("Auto-fixing..."):
                try:
                    from src.mcp_server import fix_code as _fix_code
                    import json
                    raw = asyncio.run(_fix_code(code_up, language_up))
                    result = json.loads(raw)
                except Exception as e:
                    _handle_error(str(e))
                    st.stop()
            if "error" not in result:
                st.markdown(
                    f"<p style='color:#3fb950;font-size:13px'>"
                    f"Score: {result.get('original_score',0)} &rarr; {result.get('fixed_score',0)} "
                    f"({result.get('total_changes',0)} changes)</p>",
                    unsafe_allow_html=True,
                )
                st.code(result.get("fixed_code", ""), language=LANG_SYNTAX.get(language_up, "text"), line_numbers=True)
                _render_diff(code_up, result.get("fixed_code", ""))
            else:
                st.error(result["error"])

        if do_gentest:
            with st.spinner("Generating tests..."):
                try:
                    from src.mcp_server import generate_tests as _gen_tests
                    import json
                    raw = asyncio.run(_gen_tests(code_up, language_up, "auto"))
                    result = json.loads(raw)
                except Exception as e:
                    _handle_error(str(e))
                    st.stop()
            if "error" not in result:
                st.markdown(
                    f"<p style='color:#3fb950;font-size:13px'>"
                    f"{result.get('test_count', 0)} tests generated with {result.get('framework', 'auto')}</p>",
                    unsafe_allow_html=True,
                )
                st.code(result.get("test_code", ""), language=LANG_SYNTAX.get(language_up, "text"), line_numbers=True)
            else:
                st.error(result["error"])


# ── Tab 3 : Multi-File Analysis ───────────────────────────────────────────────
with tab_multi:
    st.markdown("""
    <div style="background:#161b22;border:1px solid #21262d;border-radius:10px;
                padding:16px 24px;margin-bottom:20px">
        <div style="display:flex;align-items:center;gap:12px">
            <span style="color:#a371f7;font-size:20px;font-family:monospace">&#128230;</span>
            <span style="color:#c9d1d9;font-weight:600;font-size:15px">Multi-File Analysis</span>
            <span style="color:#484f58;font-size:12px">
                — Upload a .zip archive to analyze all source files at once
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    zip_file = st.file_uploader(
        "Upload a .zip archive",
        type=["zip"],
        help="Upload a zip containing source files (.py, .js, .ts, .java, etc.)",
        key="zip_upload",
    )

    if zip_file:
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_file.read()))
        except zipfile.BadZipFile:
            st.error("Invalid zip file.")
            st.stop()

        source_files = []
        for name in zf.namelist():
            if name.endswith("/") or name.startswith("__") or "/.git/" in name:
                continue
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in EXT_TO_LANG:
                try:
                    content = zf.read(name).decode("utf-8", errors="replace")
                except Exception:
                    continue
                if len(content.splitlines()) <= 500 and content.strip():
                    source_files.append((name, EXT_TO_LANG[ext], content))

        if not source_files:
            st.warning("No supported source files found in the archive.")
        else:
            st.markdown(
                f"<p style='color:#8b949e;font-size:12px;font-family:monospace;margin:8px 0'>"
                f"Found <b style='color:#c9d1d9'>{len(source_files)}</b> source file(s)</p>",
                unsafe_allow_html=True,
            )
            for name, lang, _ in source_files:
                st.markdown(
                    f"<span style='background:#0d1117;border:1px solid #21262d;border-radius:6px;"
                    f"padding:2px 10px;font-size:11px;font-family:monospace;color:#58a6ff;"
                    f"margin-right:4px;display:inline-block;margin-bottom:4px'>"
                    f"{name} <span style='color:#484f58'>({lang})</span></span>",
                    unsafe_allow_html=True,
                )

            if st.button("Analyze All Files", type="primary", key="btn_multi_analyze"):
                all_results = {}
                progress = st.progress(0, text="Starting analysis...")

                for file_idx, (name, lang, code) in enumerate(source_files):
                    progress.progress(
                        (file_idx) / len(source_files),
                        text=f"Analyzing {name}...",
                    )
                    valid, err = validate_syntax(code, lang)
                    if not valid:
                        all_results[name] = {"language": lang, "issues": [], "error": err}
                        continue
                    try:
                        issues = asyncio.run(run_analysis(code, lang))
                        all_results[name] = {"language": lang, "issues": issues, "error": None}
                    except Exception as e:
                        all_results[name] = {"language": lang, "issues": [], "error": str(e)}

                progress.progress(1.0, text="Analysis complete!")

                # Summary
                total_files = len(all_results)
                total_issues = sum(len(r["issues"]) for r in all_results.values())
                errors = sum(1 for r in all_results.values() if r["error"])
                avg_score = 0
                scores = []
                for r in all_results.values():
                    if r["issues"] is not None:
                        c = sum(1 for i in r["issues"] if i.severity == Severity.CRITICAL)
                        m = sum(1 for i in r["issues"] if i.severity == Severity.MAJOR)
                        n = sum(1 for i in r["issues"] if i.severity == Severity.MINOR)
                        scores.append(max(0, 100 - c * 25 - m * 10 - n * 3))
                if scores:
                    avg_score = sum(scores) // len(scores)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Files Analyzed", total_files)
                with c2:
                    st.metric("Total Issues", total_issues)
                with c3:
                    st.metric("Avg Score", f"{avg_score}/100")
                with c4:
                    st.metric("Errors", errors)

                # Per-file results
                for name, data in all_results.items():
                    if data["error"]:
                        st.warning(f"**{name}**: {data['error']}")
                    elif data["issues"]:
                        display_results(data["issues"], name, data["language"])
                    else:
                        st.success(f"**{name}** — No issues found!")


# ── Tab 4 : Dashboard ─────────────────────────────────────────────────────────
with tab_dashboard:
    st.markdown("""
    <div style="background:#161b22;border:1px solid #21262d;border-radius:10px;
                padding:16px 24px;margin-bottom:20px">
        <div style="display:flex;align-items:center;gap:12px">
            <span style="color:#d29922;font-size:20px;font-family:monospace">&#128202;</span>
            <span style="color:#c9d1d9;font-weight:600;font-size:15px">Analytics Dashboard</span>
            <span style="color:#484f58;font-size:12px">
                — Visual overview of your review history
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    records = get_recent_reviews(limit=100)

    if not records:
        st.info("No review history yet. Run some analyses to see charts here.")
    else:
        import plotly.graph_objects as go

        # Compute data from records
        dash_scores = []
        dash_dates = []
        dash_critical = 0
        dash_major = 0
        dash_minor = 0
        lang_counts = {}

        for r in reversed(records):  # oldest first for timeline
            c = r.critical_count
            m = r.major_count
            n = r.minor_count
            s = max(0, 100 - c * 25 - m * 10 - n * 3)
            dash_scores.append(s)
            dash_dates.append(r.created_at[:16])
            dash_critical += c
            dash_major += m
            dash_minor += n
            ext = "." + r.filename.rsplit(".", 1)[-1].lower() if "." in r.filename else ""
            lang = EXT_TO_LANG.get(ext, "Other")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        avg = sum(dash_scores) // len(dash_scores) if dash_scores else 0
        best = max(dash_scores) if dash_scores else 0
        worst = min(dash_scores) if dash_scores else 0

        # KPI row
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Total Reviews", len(records))
        with k2:
            st.metric("Avg Score", f"{avg}/100")
        with k3:
            st.metric("Best Score", f"{best}/100")
        with k4:
            st.metric("Total Issues", dash_critical + dash_major + dash_minor)

        chart_col1, chart_col2 = st.columns(2)

        # Score over time line chart
        with chart_col1:
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=list(range(1, len(dash_scores) + 1)),
                y=dash_scores,
                mode="lines+markers",
                line=dict(color="#6c63ff", width=2),
                marker=dict(size=6, color="#6c63ff"),
                hovertext=dash_dates,
                hoverinfo="text+y",
            ))
            fig_line.update_layout(
                title=dict(text="Score Over Time", font=dict(color="#c9d1d9", size=14)),
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                font=dict(color="#8b949e", size=11),
                xaxis=dict(title="Review #", gridcolor="#21262d", zeroline=False),
                yaxis=dict(title="Score", gridcolor="#21262d", zeroline=False, range=[0, 105]),
                margin=dict(l=40, r=20, t=40, b=40),
                height=320,
            )
            st.plotly_chart(fig_line, use_container_width=True)

        # Issues by severity pie chart
        with chart_col2:
            fig_pie = go.Figure(data=[go.Pie(
                labels=["Critical", "Major", "Minor"],
                values=[dash_critical, dash_major, dash_minor],
                marker=dict(colors=["#f85149", "#d29922", "#58a6ff"]),
                hole=0.45,
                textinfo="label+value",
                textfont=dict(size=12),
            )])
            fig_pie.update_layout(
                title=dict(text="Issues by Severity", font=dict(color="#c9d1d9", size=14)),
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                font=dict(color="#8b949e", size=11),
                margin=dict(l=20, r=20, t=40, b=20),
                height=320,
                showlegend=True,
                legend=dict(font=dict(color="#c9d1d9")),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        chart_col3, chart_col4 = st.columns(2)

        # Languages analyzed bar chart
        with chart_col3:
            lang_names = list(lang_counts.keys())
            lang_vals = list(lang_counts.values())
            fig_bar = go.Figure(data=[go.Bar(
                x=lang_names,
                y=lang_vals,
                marker_color="#6c63ff",
                text=lang_vals,
                textposition="outside",
                textfont=dict(color="#c9d1d9"),
            )])
            fig_bar.update_layout(
                title=dict(text="Languages Analyzed", font=dict(color="#c9d1d9", size=14)),
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                font=dict(color="#8b949e", size=11),
                xaxis=dict(gridcolor="#21262d"),
                yaxis=dict(gridcolor="#21262d", zeroline=False),
                margin=dict(l=40, r=20, t=40, b=40),
                height=320,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Score distribution histogram
        with chart_col4:
            fig_hist = go.Figure(data=[go.Histogram(
                x=dash_scores,
                nbinsx=10,
                marker_color="#3fb950",
                marker_line=dict(color="#238636", width=1),
            )])
            fig_hist.update_layout(
                title=dict(text="Score Distribution", font=dict(color="#c9d1d9", size=14)),
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                font=dict(color="#8b949e", size=11),
                xaxis=dict(title="Score", gridcolor="#21262d", range=[0, 105]),
                yaxis=dict(title="Count", gridcolor="#21262d", zeroline=False),
                margin=dict(l=40, r=20, t=40, b=40),
                height=320,
            )
            st.plotly_chart(fig_hist, use_container_width=True)


# ── Tab 5 : MCP Console ───────────────────────────────────────────────────────
with tab_mcp:
    st.markdown("""
    <div style="background:#161b22;border:1px solid #21262d;border-radius:10px;
                padding:16px 24px;margin-bottom:20px">
        <div style="display:flex;align-items:center;gap:12px">
            <span style="color:#3fb950;font-size:20px;font-family:monospace">$</span>
            <span style="color:#c9d1d9;font-weight:600;font-size:15px">MCP Console</span>
            <span style="color:#484f58;font-size:12px">
                — Direct interaction with the MCP server via stdio transport
            </span>
            <span style="margin-left:auto;background:#0d2818;color:#3fb950;padding:3px 12px;
                         border-radius:20px;font-size:10px;font-family:monospace;border:1px solid #23863633">
                11 tools · 3 resources · 2 prompts
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    mcp_action = st.selectbox(
        "Action",
        [
            "Server Introspection",
            "── Code Intelligence ──",
            "Review Code via MCP",
            "Fix Code via MCP",
            "Explain Code via MCP",
            "Generate Tests via MCP",
            "── GitHub Integration ──",
            "GitHub: Get Repository",
            "GitHub: Get File",
            "GitHub: Create Issue",
            "GitHub: List Issues",
            "GitHub: Search Repos",
            "── Utility ──",
            "Global Statistics",
            "Supported Languages",
        ],
        key="mcp_action",
    )

    if mcp_action == "Server Introspection":
        if st.button("Connect & Introspect", type="primary", key="btn_mcp_intro"):
            with st.spinner("Connecting to MCP server..."):
                try:
                    from src.mcp_client import MCPClient

                    async def _introspect():
                        async with MCPClient() as c:
                            return await c.list_tools(), await c.list_resources(), await c.list_prompts()

                    tools, resources, prompts = asyncio.run(_introspect())
                except Exception as e:
                    st.error(f"MCP Error: {e}")
                    tools, resources, prompts = None, None, None

            if tools is not None:
                col_t, col_r, col_p = st.columns(3)
                with col_t:
                    st.markdown(
                        f"<p style='color:#3fb950;font-size:11px;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>"
                        f"Tools ({len(tools)})</p>",
                        unsafe_allow_html=True,
                    )
                    for t in tools:
                        st.markdown(
                            f"<div style='background:#0d1117;border:1px solid #21262d;"
                            f"border-radius:8px;padding:10px 14px;margin-bottom:6px'>"
                            f"<span style='color:#58a6ff;font-size:12px;font-weight:600;"
                            f"font-family:monospace'>{t['name']}</span><br/>"
                            f"<span style='color:#484f58;font-size:11px;line-height:1.4'>"
                            f"{(t['description'] or '')[:120]}</span></div>",
                            unsafe_allow_html=True,
                        )
                with col_r:
                    st.markdown(
                        f"<p style='color:#d29922;font-size:11px;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>"
                        f"Resources ({len(resources)})</p>",
                        unsafe_allow_html=True,
                    )
                    for r in resources:
                        st.markdown(
                            f"<div style='background:#0d1117;border:1px solid #21262d;"
                            f"border-radius:8px;padding:10px 14px;margin-bottom:6px'>"
                            f"<span style='color:#d29922;font-size:12px;font-weight:600;"
                            f"font-family:monospace'>{r['uri']}</span><br/>"
                            f"<span style='color:#484f58;font-size:11px;line-height:1.4'>"
                            f"{(r.get('description') or '')[:120]}</span></div>",
                            unsafe_allow_html=True,
                        )
                with col_p:
                    st.markdown(
                        f"<p style='color:#a371f7;font-size:11px;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>"
                        f"Prompts ({len(prompts)})</p>",
                        unsafe_allow_html=True,
                    )
                    for p in prompts:
                        st.markdown(
                            f"<div style='background:#0d1117;border:1px solid #21262d;"
                            f"border-radius:8px;padding:10px 14px;margin-bottom:6px'>"
                            f"<span style='color:#a371f7;font-size:12px;font-weight:600;"
                            f"font-family:monospace'>{p['name']}</span><br/>"
                            f"<span style='color:#484f58;font-size:11px;line-height:1.4'>"
                            f"{(p.get('description') or '')[:120]}</span></div>",
                            unsafe_allow_html=True,
                        )

    elif mcp_action in ("Review Code via MCP", "Fix Code via MCP", "Explain Code via MCP", "Generate Tests via MCP"):
        col_l, col_f = st.columns([1, 3])
        with col_l:
            mcp_language = st.selectbox("Language", LANGUAGES, index=0, key="mcp_lang")
        if mcp_action == "Explain Code via MCP":
            with col_f:
                mcp_detail = st.selectbox("Detail", ["brief", "medium", "detailed"], index=1, key="mcp_detail")
        if mcp_action == "Generate Tests via MCP":
            with col_f:
                mcp_framework = st.selectbox("Framework", ["auto", "pytest", "unittest", "jest", "mocha", "junit"], key="mcp_framework")

        mcp_code = st.text_area(
            "Source code",
            height=300,
            placeholder="// Code to send to the MCP server...",
            key="mcp_code",
        )

        tool_map = {
            "Review Code via MCP": "review_code",
            "Fix Code via MCP": "fix_code",
            "Explain Code via MCP": "explain_code",
            "Generate Tests via MCP": "generate_tests",
        }
        tool_name = tool_map[mcp_action]

        if mcp_code.strip() and st.button(f"Call {tool_name}", type="primary", key="btn_mcp_tool"):
            with st.spinner(f"MCP → {tool_name}..."):
                try:
                    from src.mcp_client import MCPClient

                    async def _call():
                        async with MCPClient() as c:
                            args = {"code": mcp_code, "language": mcp_language}
                            if tool_name == "review_code":
                                args["filename"] = "mcp_console"
                            if tool_name == "explain_code":
                                args["detail_level"] = mcp_detail
                            if tool_name == "generate_tests":
                                args["framework"] = mcp_framework
                            return await c.call_tool(tool_name, args)

                    import json
                    raw = asyncio.run(_call())
                    try:
                        result = json.loads(raw)
                    except Exception:
                        result = raw
                except Exception as e:
                    st.error(f"MCP Error: {e}")
                    result = None

            if result:
                if isinstance(result, dict) and "fixed_code" in result:
                    st.markdown(
                        f"<p style='color:#3fb950;font-size:13px;font-family:monospace'>"
                        f"Score: {result.get('original_score',0)} &rarr; {result.get('fixed_score',0)}</p>",
                        unsafe_allow_html=True,
                    )
                    st.code(result["fixed_code"], language=LANG_SYNTAX.get(mcp_language, "text"), line_numbers=True)
                elif isinstance(result, dict) and "test_code" in result:
                    st.code(result["test_code"], language=LANG_SYNTAX.get(mcp_language, "text"), line_numbers=True)
                st.markdown("<p style='color:#484f58;font-size:10px;margin-top:12px;font-family:monospace'>RAW RESPONSE</p>", unsafe_allow_html=True)
                if isinstance(result, (dict, list)):
                    st.json(result)
                else:
                    st.code(str(result))

    elif mcp_action == "Global Statistics":
        if st.button("Load Stats", type="primary", key="btn_mcp_stats"):
            with st.spinner("Reading review://stats..."):
                try:
                    from src.mcp_client import MCPClient

                    async def _stats():
                        async with MCPClient() as c:
                            return await c.get_stats()

                    stats = asyncio.run(_stats())
                except Exception as e:
                    st.error(f"MCP Error: {e}")
                    stats = None

            if stats and stats.get("total_reviews", 0) > 0:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Reviews", stats["total_reviews"])
                with c2:
                    st.metric("Avg Score", f"{stats['average_score']}/100")
                with c3:
                    st.metric("Best", f"{stats['best_score']}/100")
                with c4:
                    st.metric("Total Issues", stats["total_issues"])
                col_crit, col_maj, col_min = st.columns(3)
                with col_crit:
                    st.metric("Critical", stats["total_critical"], delta_color="inverse")
                with col_maj:
                    st.metric("Major", stats["total_major"], delta_color="inverse")
                with col_min:
                    st.metric("Minor", stats["total_minor"], delta_color="inverse")
            elif stats:
                st.info("No reviews recorded yet.")

    elif mcp_action == "Supported Languages":
        if st.button("Load Languages", type="primary", key="btn_mcp_langs"):
            with st.spinner("Reading review://supported-languages..."):
                try:
                    from src.mcp_client import MCPClient

                    async def _langs():
                        async with MCPClient() as c:
                            return await c.get_languages()

                    langs = asyncio.run(_langs())
                except Exception as e:
                    st.error(f"MCP Error: {e}")
                    langs = None

            if langs:
                cols = st.columns(4)
                for idx, item in enumerate(langs):
                    with cols[idx % 4]:
                        st.markdown(
                            f"<div style='background:#0d1117;border:1px solid #21262d;"
                            f"border-radius:8px;padding:8px 14px;margin-bottom:6px;"
                            f"font-family:monospace;font-size:12px'>"
                            f"<span style='color:#58a6ff'>{item['language']}</span> "
                            f"<span style='color:#30363d'>{item['extension']}</span></div>",
                            unsafe_allow_html=True,
                        )

    elif mcp_action == "GitHub: Get Repository":
        col_o, col_r = st.columns(2)
        with col_o:
            gh_owner = st.text_input("Owner", placeholder="facebook", key="gh_owner")
        with col_r:
            gh_repo = st.text_input("Repository", placeholder="react", key="gh_repo")

        if gh_owner and gh_repo and st.button("Get Repo Info", type="primary", key="btn_gh_repo"):
            with st.spinner(f"GitHub → {gh_owner}/{gh_repo}..."):
                try:
                    from src.mcp_client import MCPClient
                    import json

                    async def _gh_repo():
                        async with MCPClient() as c:
                            return await c.call_tool("github_get_repo", {"owner": gh_owner, "repo": gh_repo})

                    raw = asyncio.run(_gh_repo())
                    result = json.loads(raw)
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result and "error" not in result:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Stars", f"{result.get('stars', 0):,}")
                with c2:
                    st.metric("Forks", f"{result.get('forks', 0):,}")
                with c3:
                    st.metric("Issues", f"{result.get('open_issues', 0):,}")
                with c4:
                    st.metric("Language", result.get("language", "—"))
                st.markdown(
                    f"<div style='background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px 24px;margin-top:12px'>"
                    f"<p style='color:#58a6ff;font-size:15px;font-weight:600'>{result.get('full_name','')}</p>"
                    f"<p style='color:#8b949e;font-size:13px'>{result.get('description','')}</p>"
                    f"<p style='color:#484f58;font-size:11px;font-family:monospace;margin-top:8px'>"
                    f"License: {result.get('license','—')} · Branch: {result.get('default_branch','')} · "
                    f"Topics: {', '.join(result.get('topics',[])[:5])}</p></div>",
                    unsafe_allow_html=True,
                )
            elif result:
                st.error(result.get("error", "Unknown error"))

    elif mcp_action == "GitHub: Get File":
        col_o, col_r, col_p = st.columns(3)
        with col_o:
            gh_owner2 = st.text_input("Owner", placeholder="microsoft", key="gh_owner2")
        with col_r:
            gh_repo2 = st.text_input("Repository", placeholder="vscode", key="gh_repo2")
        with col_p:
            gh_path = st.text_input("File Path", placeholder="src/main.ts", key="gh_path")

        if gh_owner2 and gh_repo2 and gh_path and st.button("Fetch File", type="primary", key="btn_gh_file"):
            with st.spinner(f"GitHub → {gh_path}..."):
                try:
                    from src.mcp_client import MCPClient
                    import json

                    async def _gh_file():
                        async with MCPClient() as c:
                            return await c.call_tool("github_get_file", {
                                "owner": gh_owner2, "repo": gh_repo2, "path": gh_path,
                            })

                    raw = asyncio.run(_gh_file())
                    result = json.loads(raw)
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result and "error" not in result:
                st.markdown(
                    f"<p style='color:#8b949e;font-size:12px;font-family:monospace'>"
                    f"{result.get('filename','')} · {result.get('size',0)} bytes · sha: {(result.get('sha',''))[:7]}</p>",
                    unsafe_allow_html=True,
                )
                ext = gh_path.rsplit(".", 1)[-1] if "." in gh_path else "text"
                st.code(result.get("content", ""), language=ext, line_numbers=True)
            elif result:
                st.error(result.get("error", "Unknown error"))

    elif mcp_action == "GitHub: Create Issue":
        col_o, col_r = st.columns(2)
        with col_o:
            gh_owner3 = st.text_input("Owner", key="gh_owner3")
        with col_r:
            gh_repo3 = st.text_input("Repository", key="gh_repo3")
        gh_title = st.text_input("Issue Title", placeholder="Bug: description of the problem", key="gh_title")
        gh_body = st.text_area("Issue Body (Markdown)", height=200,
                               placeholder="## Description\n\nDetailed description...\n\n## Steps to reproduce\n\n1. ...",
                               key="gh_body")
        gh_labels = st.text_input("Labels (comma-separated)", placeholder="bug, security", key="gh_labels")

        if gh_owner3 and gh_repo3 and gh_title and st.button("Create Issue", type="primary", key="btn_gh_issue"):
            labels = [l.strip() for l in gh_labels.split(",") if l.strip()] if gh_labels else []
            with st.spinner("Creating GitHub issue..."):
                try:
                    from src.mcp_client import MCPClient
                    import json

                    async def _gh_issue():
                        async with MCPClient() as c:
                            return await c.call_tool("github_create_issue", {
                                "owner": gh_owner3, "repo": gh_repo3,
                                "title": gh_title, "body": gh_body, "labels": labels,
                            })

                    raw = asyncio.run(_gh_issue())
                    result = json.loads(raw)
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result and "error" not in result:
                st.success(f"Issue #{result.get('number')} created!")
                st.markdown(
                    f"<a href='{result.get('html_url','')}' target='_blank' "
                    f"style='color:#58a6ff;font-size:13px'>View on GitHub →</a>",
                    unsafe_allow_html=True,
                )
            elif result:
                st.error(result.get("error", "Unknown error"))

    elif mcp_action == "GitHub: List Issues":
        col_o, col_r, col_s = st.columns(3)
        with col_o:
            gh_owner4 = st.text_input("Owner", key="gh_owner4")
        with col_r:
            gh_repo4 = st.text_input("Repository", key="gh_repo4")
        with col_s:
            gh_state = st.selectbox("State", ["open", "closed", "all"], key="gh_state")

        if gh_owner4 and gh_repo4 and st.button("List Issues", type="primary", key="btn_gh_issues"):
            with st.spinner("Fetching issues..."):
                try:
                    from src.mcp_client import MCPClient
                    import json

                    async def _gh_issues():
                        async with MCPClient() as c:
                            return await c.call_tool("github_list_issues", {
                                "owner": gh_owner4, "repo": gh_repo4,
                                "state": gh_state, "limit": 10,
                            })

                    raw = asyncio.run(_gh_issues())
                    result = json.loads(raw)
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result and "error" not in result:
                st.markdown(
                    f"<p style='color:#8b949e;font-size:12px'>{result.get('count',0)} issue(s)</p>",
                    unsafe_allow_html=True,
                )
                for issue in result.get("issues", []):
                    state_color = "#3fb950" if issue.get("state") == "open" else "#8b949e"
                    labels_html = " ".join(
                        f"<span style='background:#21262d;color:#c9d1d9;padding:1px 8px;"
                        f"border-radius:20px;font-size:10px'>{l}</span>"
                        for l in issue.get("labels", [])
                    )
                    st.markdown(
                        f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:8px;"
                        f"padding:10px 16px;margin-bottom:6px;display:flex;align-items:center;gap:10px'>"
                        f"<span style='color:{state_color};font-weight:700;font-family:monospace;min-width:40px'>"
                        f"#{issue.get('number','')}</span>"
                        f"<span style='color:#c9d1d9;font-size:13px;flex:1'>{issue.get('title','')}</span>"
                        f"<span style='display:flex;gap:4px'>{labels_html}</span>"
                        f"<span style='color:#484f58;font-size:11px;font-family:monospace'>"
                        f"{issue.get('author','')}</span></div>",
                        unsafe_allow_html=True,
                    )
            elif result:
                st.error(result.get("error", "Unknown error"))

    elif mcp_action == "GitHub: Search Repos":
        gh_query = st.text_input("Search query", placeholder="fastapi language:python stars:>1000", key="gh_query")

        if gh_query and st.button("Search", type="primary", key="btn_gh_search"):
            with st.spinner("Searching GitHub..."):
                try:
                    from src.mcp_client import MCPClient
                    import json

                    async def _gh_search():
                        async with MCPClient() as c:
                            return await c.call_tool("github_search_repos", {"query": gh_query, "limit": 5})

                    raw = asyncio.run(_gh_search())
                    result = json.loads(raw)
                except Exception as e:
                    st.error(f"Error: {e}")
                    result = None

            if result and "error" not in result:
                st.markdown(
                    f"<p style='color:#8b949e;font-size:12px'>{result.get('total_count',0):,} total results</p>",
                    unsafe_allow_html=True,
                )
                for r in result.get("repos", []):
                    topics_html = " ".join(
                        f"<span style='background:#0d2240;color:#58a6ff;padding:1px 8px;"
                        f"border-radius:20px;font-size:10px;border:1px solid #58a6ff33'>{t}</span>"
                        for t in r.get("topics", [])
                    )
                    st.markdown(
                        f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:10px;"
                        f"padding:14px 20px;margin-bottom:8px'>"
                        f"<div style='display:flex;align-items:center;gap:12px'>"
                        f"<span style='color:#58a6ff;font-size:14px;font-weight:600'>{r.get('full_name','')}</span>"
                        f"<span style='color:#d29922;font-size:12px;font-family:monospace'>★ {r.get('stars',0):,}</span>"
                        f"<span style='color:#484f58;font-size:11px'>{r.get('language','')}</span></div>"
                        f"<p style='color:#8b949e;font-size:12px;margin:6px 0'>{r.get('description','')}</p>"
                        f"<div style='display:flex;gap:4px;flex-wrap:wrap'>{topics_html}</div></div>",
                        unsafe_allow_html=True,
                    )


# ── Sidebar: History ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 16px 0">
        <p style="font-size:11px;font-weight:700;text-transform:uppercase;
                  letter-spacing:1.5px;color:#484f58;margin:0">History</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Clear All", key="del_all"):
        delete_all_reviews()
        st.rerun()

    records = get_recent_reviews(limit=20)
    if not records:
        st.markdown(
            "<p style='color:#30363d;font-size:12px'>No reviews yet.</p>",
            unsafe_allow_html=True,
        )
    else:
        for r in records:
            score = max(0, 100 - r.critical_count * 25 - r.major_count * 10 - r.minor_count * 3)
            score_color = "#f85149" if score < 50 else "#d29922" if score < 75 else "#3fb950"
            col_info, col_del = st.columns([5, 1])
            with col_info:
                st.markdown(f"""
                <div style="margin-bottom:2px">
                    <div style="display:flex;align-items:center;gap:8px">
                        <span style="color:#c9d1d9;font-size:12px;font-weight:600">{r.filename}</span>
                        <span style="color:{score_color};font-size:10px;font-weight:700;font-family:monospace;
                                     background:{score_color}15;padding:1px 6px;border-radius:4px">{score}</span>
                    </div>
                    <p style="color:#484f58;font-size:10px;font-family:monospace;margin:2px 0">
                        <span style="color:#f85149">{r.critical_count}c</span>
                        <span style="color:#d29922">{r.major_count}m</span>
                        <span style="color:#58a6ff">{r.minor_count}s</span>
                        &nbsp;·&nbsp; {r.created_at[:16]}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            with col_del:
                if st.button("×", key=f"del_{r.id}", help="Delete"):
                    delete_review(r.id)
                    st.rerun()
            st.markdown("<hr style='border-color:#161b22;margin:6px 0'>", unsafe_allow_html=True)
