"""Donor outreach review interface.

A local web app for fundraising staff: upload a donor file, set the campaign,
and see every data problem, warning, confidence score, and letter before
anything goes near an outbox.

This app contains no business logic. It shells out to the same three scripts
the skill uses (validate, calculate, generate), so what you see here is
exactly what the pipeline does. See docs/adr/0012-operator-interface.md.

Run with:
    streamlit run app/review_app.py
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skill" / "charity-donor-outreach"
SCRIPTS = SKILL_DIR / "scripts"
FIXTURE = SKILL_DIR / "assets" / "sample_donors.csv"
TEMPLATE = SKILL_DIR / "assets" / "template.html"

CAMPAIGN_LABELS = {
    "emergency_appeal": "Emergency appeal",
    "annual_fund": "Annual fund",
    "capital_campaign": "Capital campaign",
    "event_fundraiser": "Event fundraiser",
}

st.set_page_config(page_title="Donor Outreach Review", page_icon="📬", layout="wide")


def run_pipeline(donor_bytes: bytes, donor_suffix: str, config: dict) -> dict:
    """Run validate -> calculate -> generate in a temp dir, return all outputs."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        donor_path = tmp_path / f"donors{donor_suffix}"
        donor_path.write_bytes(donor_bytes)
        config_path = tmp_path / "campaign.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        workdir = tmp_path / "work"
        outdir = tmp_path / "output"

        steps = [
            ("validate_input.py", ["--input", str(donor_path)]),
            ("calculate_ask.py", []),
            ("generate_letters.py", ["--outdir", str(outdir), "--template", str(TEMPLATE)]),
        ]
        logs = []
        for script, extra in steps:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / script), "--config", str(config_path),
                 "--workdir", str(workdir), *extra],
                capture_output=True, text=True,
            )
            logs.append(f"$ {script}\n{result.stdout}")
            if result.returncode != 0:
                return {"ok": False, "error": result.stderr or result.stdout, "step": script}

        letters = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((outdir / "letters").glob("*.html"))
        }
        return {
            "ok": True,
            "logs": "\n".join(logs),
            "report": json.loads((workdir / "validation_report.json").read_text(encoding="utf-8")),
            "validated": pd.read_csv(workdir / "validated.csv", dtype=str).fillna(""),
            "exceptions": pd.read_csv(workdir / "exceptions.csv", dtype=str).fillna(""),
            "computed": pd.read_csv(workdir / "computed.csv", dtype=str).fillna(""),
            "manifest": pd.read_csv(outdir / "manifest.csv", dtype=str).fillna(""),
            "letters": letters,
        }


def letters_zip(letters: dict[str, str], manifest: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("manifest.csv", manifest.to_csv(index=False))
        for name, content in letters.items():
            bundle.writestr(f"letters/{name}", content)
    return buffer.getvalue()


st.title("Donor Outreach Review")
st.caption(
    "Upload a donor file, set the campaign, and review everything before a "
    "single letter goes out. Every number is computed by the same audited "
    "policy scripts the automation uses. Nothing is ever sent from here."
)

with st.sidebar:
    st.header("Campaign settings")
    campaign_type = st.selectbox(
        "Campaign type", list(CAMPAIGN_LABELS), format_func=CAMPAIGN_LABELS.get,
    )
    as_of_date = st.date_input(
        "As-of date", value=pd.Timestamp("2024-06-30"),
        help="The reference date for lapsed status and loyalty rules. Use the "
             "date your donor extract was taken, not today's date.",
    )
    charity_name = st.text_input("Charity name", "ASPCA")
    donation_url = st.text_input("Donation URL", "https://www.aspca.org/donate")
    signer_name = st.text_input("Signer name", "Jordan Ellis")
    signer_title = st.text_input("Signer title", "Director of Development")

    st.subheader("Gift matching")
    match_confirmed = st.checkbox(
        "A gift match is confirmed in writing",
        help="Letters may only mention matching when this is checked. "
             "Unconfirmed match claims are a compliance risk, so the pipeline "
             "blocks them entirely.",
    )
    match_sponsor = match_terms = ""
    if match_confirmed:
        match_sponsor = st.text_input("Match sponsor")
        match_terms = st.text_input("Match terms", placeholder="doubled up to $100,000 through August 31")

    event_name = ""
    event_registered_count = None
    if campaign_type == "event_fundraiser":
        st.subheader("Event details")
        event_name = st.text_input("Event name")
        count = st.number_input("Registered so far (0 = do not mention)", min_value=0, value=0)
        event_registered_count = int(count) or None

    reengagement_gift = st.text_input(
        "Re-engagement gift (optional)",
        help="Mentioned only to lapsed donors, and only if set.",
    )

config = {
    "campaign_type": campaign_type,
    "as_of_date": str(as_of_date),
    "charity_name": charity_name,
    "donation_url": donation_url,
    "signer_name": signer_name,
    "signer_title": signer_title,
    "match_confirmed": bool(match_confirmed),
    "match_sponsor": match_sponsor,
    "match_terms": match_terms,
    "event_name": event_name,
    "event_registered_count": event_registered_count,
    "reengagement_gift": reengagement_gift,
}

upload_col, sample_col = st.columns([3, 1])
with upload_col:
    uploaded = st.file_uploader("Donor file (CSV or Excel)", type=["csv", "xlsx", "xls"])
with sample_col:
    st.write("")
    use_sample = st.button("Try the sample file", use_container_width=True)

if use_sample:
    st.session_state["result"] = run_pipeline(FIXTURE.read_bytes(), ".csv", config)
    st.session_state["source"] = FIXTURE.name
elif uploaded is not None and st.button("Run checks", type="primary"):
    suffix = Path(uploaded.name).suffix.lower() or ".csv"
    st.session_state["result"] = run_pipeline(uploaded.getvalue(), suffix, config)
    st.session_state["source"] = uploaded.name

result = st.session_state.get("result")
if result is None:
    st.info(
        "Start by uploading your donor export, or try the sample file. "
        "The checks will list every problem found, in plain language, before "
        "any letters are created."
    )
    st.stop()

if not result["ok"]:
    st.error(f"The {result['step']} step could not run:\n\n{result['error']}")
    st.stop()

report = result["report"]
manifest = result["manifest"]
exceptions = result["exceptions"]
letters = result["letters"]

st.subheader(f"Results for {st.session_state.get('source', 'donor file')}")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Rows in file", report["rows_in"])
m2.metric("Passed all checks", report["rows_validated"])
m3.metric("Need data fixes", report["rows_excepted"])
m4.metric("Letters drafted", int((manifest["letter_file"] != "").sum()))
m5.metric("Need human review", int((manifest["review_level"] != "none").sum()))

tab_problems, tab_review, tab_asks, tab_letters, tab_log = st.tabs([
    "Data problems", "Review queue", "Ask calculations", "Letter previews", "Run log",
])

with tab_problems:
    if len(exceptions):
        st.error(
            f"{len(exceptions)} donor record(s) were held back. No letters were "
            "created for them. Each row explains exactly what to fix in the "
            "source system, then re-run the checks."
        )
        st.dataframe(exceptions, use_container_width=True, hide_index=True)
    else:
        st.success("No records were held back. Every row passed validation.")
    warned = manifest[manifest["warnings"] != ""]
    if len(warned):
        st.warning(
            f"{len(warned)} record(s) passed but carry warnings. Their letters "
            "exist and are marked for review."
        )
        st.dataframe(
            warned[["donor_name", "tier", "status", "confidence", "warnings"]],
            use_container_width=True, hide_index=True,
        )

with tab_review:
    st.markdown(
        "Review levels come from policy: every Platinum letter is reviewed by "
        "a person, any warning means review is recommended, and low confidence "
        "or special routing makes it mandatory."
    )
    order = {"mandatory": 0, "recommended": 1, "none": 2}
    queue = manifest.sort_values(by="review_level", key=lambda s: s.map(order))
    st.dataframe(
        queue[["donor_name", "tier", "status", "ask_amount", "confidence",
               "review_level", "review_reasons", "warnings"]],
        use_container_width=True, hide_index=True,
    )

with tab_asks:
    st.markdown(
        "Every ask amount is calculated by the policy script, never estimated. "
        "The trace column shows each step of the calculation."
    )
    st.dataframe(
        result["computed"][["donor_name", "tier", "status", "largest_gift",
                            "lifetime_total", "ask_amount", "ask_trace"]],
        use_container_width=True, hide_index=True,
    )

with tab_letters:
    if letters:
        eligible = manifest[manifest["letter_file"] != ""]
        chosen = st.selectbox("Donor", eligible["donor_name"].tolist())
        row = eligible[eligible["donor_name"] == chosen].iloc[0]
        st.caption(
            f"Tier {row['tier']}, ask ${row['ask_amount']}, confidence "
            f"{row['confidence']}, review: {row['review_level']}"
        )
        file_name = Path(row["letter_file"]).name
        st.components.v1.html(letters[file_name], height=520, scrolling=True)
    else:
        st.info("No letters were generated on this run.")

with tab_log:
    st.code(result["logs"])

st.divider()
d1, d2, d3 = st.columns(3)
d1.download_button(
    "Download review manifest (CSV)", manifest.to_csv(index=False),
    file_name="manifest.csv", use_container_width=True,
)
d2.download_button(
    "Download data problems (CSV)", exceptions.to_csv(index=False),
    file_name="exceptions.csv", use_container_width=True,
)
d3.download_button(
    "Download letters + manifest (ZIP)", letters_zip(letters, manifest),
    file_name="letters_for_review.zip", use_container_width=True,
)
st.caption(
    "Letters are drafts for human review. This tool never sends email and "
    "never changes your source data."
)
