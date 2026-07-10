"""Donor outreach review interface.

A local web app for fundraising staff: upload a donor file, set the campaign,
and see every data problem, warning, confidence score, and letter before
anything goes near an outbox. Approve suggested data fixes and resubmit in
one click. Teach the system your letter style, within guardrails, by sharing
your edited letters.

This app contains no business logic. It shells out to the same scripts the
skill uses, so what you see here is exactly what the pipeline does. See
docs/adr/0012-operator-interface.md, 0014, and 0015.

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
STYLE_PROFILE = REPO_ROOT / "feedback" / "style_profile.json"
AUDIO_FILE = Path(__file__).resolve().parent / "assets" / "tutorial_walkthrough.wav"
TRANSCRIPT_FILE = Path(__file__).resolve().parent / "assets" / "tutorial_transcript.md"

CAMPAIGN_LABELS = {
    "emergency_appeal": "Emergency appeal",
    "annual_fund": "Annual fund",
    "capital_campaign": "Capital campaign",
    "event_fundraiser": "Event fundraiser",
}

st.set_page_config(page_title="Donor Outreach Review", page_icon="📬", layout="wide")


def tip(text: str) -> None:
    """Tutorial callout, shown only when tutorial mode is on."""
    if st.session_state.get("tutorial", True):
        st.info(text, icon="🎓")


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
            ("generate_letters.py", ["--outdir", str(outdir), "--template", str(TEMPLATE),
                                     "--style", str(STYLE_PROFILE)]),
        ]
        logs = []
        for script, extra in steps:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / script), "--config", str(config_path),
                 "--workdir", str(workdir), *extra],
                capture_output=True, text=True,
            )
            logs.append(f"$ {script}\n{result.stdout}{result.stderr}")
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
            "corrections": pd.read_csv(workdir / "corrections.csv", dtype=str).fillna(""),
            "computed": pd.read_csv(workdir / "computed.csv", dtype=str).fillna(""),
            "manifest": pd.read_csv(outdir / "manifest.csv", dtype=str).fillna(""),
            "letters": letters,
        }


def apply_corrections_to_bytes(donor_bytes: bytes, donor_suffix: str,
                               approved: pd.DataFrame) -> bytes:
    """Apply approved corrections to the uploaded file, return corrected CSV bytes."""
    if donor_suffix in (".xlsx", ".xls"):
        frame = pd.read_excel(io.BytesIO(donor_bytes), dtype=str).fillna("")
    else:
        frame = pd.read_csv(io.BytesIO(donor_bytes), dtype=str).fillna("")
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    for _, fix in approved.iterrows():
        row_index = int(fix["row_number"]) - 2  # data rows start at file row 2
        if 0 <= row_index < len(frame) and fix["field"] in frame.columns:
            frame.loc[row_index, fix["field"]] = fix["suggested_value"]
    return frame.to_csv(index=False).encode("utf-8")


def learn_style_from_uploads(original_letters: dict[str, str], edited_files) -> dict:
    """Run the style learner on uploaded edited letters; returns its report."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        originals = tmp_path / "originals"
        edited = tmp_path / "edited"
        workdir = tmp_path / "work"
        originals.mkdir()
        edited.mkdir()
        for name, content in original_letters.items():
            (originals / name).write_text(content, encoding="utf-8")
        for upload in edited_files:
            (edited / Path(upload.name).name).write_bytes(upload.getvalue())
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "learn_style.py"), "--originals", str(originals),
             "--edited", str(edited), "--workdir", str(workdir)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return {"error": result.stderr or result.stdout}
        report = json.loads((workdir / "style_suggestions.json").read_text(encoding="utf-8"))
        report["_log"] = result.stdout
        return report


def adopt_style(field: str, value: str, evidence: int, approved_by: str) -> None:
    profile = {}
    if STYLE_PROFILE.exists():
        profile = json.loads(STYLE_PROFILE.read_text(encoding="utf-8"))
    profile[field] = value
    profile["approved_by"] = approved_by
    profile["approved_on"] = pd.Timestamp.today().strftime("%Y-%m-%d")
    profile["evidence_edits"] = evidence
    STYLE_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    STYLE_PROFILE.write_text(json.dumps(profile, indent=2), encoding="utf-8")


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
    st.header("Help")
    st.toggle(
        "Tutorial mode", key="tutorial", value=st.session_state.get("tutorial", True),
        help="Shows plain-language guidance beside each step. Turn it off once "
             "you know your way around.",
    )
    audio_on = st.toggle(
        "Audio walkthrough", value=False,
        help="A narrated tour of this screen, including why the original "
             "spreadsheet-in-a-prompt approach fails at scale.",
    )
    if audio_on:
        if AUDIO_FILE.exists():
            st.audio(AUDIO_FILE.read_bytes(), format="audio/wav")
            if TRANSCRIPT_FILE.exists():
                with st.expander("Transcript"):
                    st.markdown(TRANSCRIPT_FILE.read_text(encoding="utf-8"))
        else:
            st.warning("Audio file not found. See app/assets/ for how it is generated.")

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

tip(
    "Step 1: upload your donor export (or press Try the sample file). The "
    "checks read the gift history itself and verify everything else against "
    "it, so mislabeled tiers and unbalanced totals are caught here, not in "
    "a donor's mailbox."
)

upload_col, sample_col = st.columns([3, 1])
with upload_col:
    uploaded = st.file_uploader("Donor file (CSV or Excel)", type=["csv", "xlsx", "xls"])
with sample_col:
    st.write("")
    use_sample = st.button("Try the sample file", use_container_width=True)


def start_run(data: bytes, suffix: str, label: str) -> None:
    st.session_state["donor_bytes"] = data
    st.session_state["donor_suffix"] = suffix
    st.session_state["source"] = label
    st.session_state["result"] = run_pipeline(data, suffix, config)


if use_sample:
    start_run(FIXTURE.read_bytes(), ".csv", FIXTURE.name)
elif uploaded is not None and st.button("Run checks", type="primary"):
    start_run(uploaded.getvalue(), Path(uploaded.name).suffix.lower() or ".csv", uploaded.name)

result = st.session_state.get("result")
if result is None:
    st.stop()

if not result["ok"]:
    st.error(f"The {result['step']} step could not run:\n\n{result['error']}")
    st.stop()

report = result["report"]
manifest = result["manifest"]
exceptions = result["exceptions"]
corrections = result["corrections"]
letters = result["letters"]

st.subheader(f"Results for {st.session_state.get('source', 'donor file')}")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Rows in file", report["rows_in"])
m2.metric("Passed all checks", report["rows_validated"])
m3.metric("Need data fixes", report["rows_excepted"])
m4.metric("Letters drafted", int((manifest["letter_file"] != "").sum()))
m5.metric("Need human review", int((manifest["review_level"] != "none").sum()))

tab_problems, tab_fixes, tab_review, tab_asks, tab_letters, tab_style, tab_log = st.tabs([
    "Data problems", "Fix and resubmit", "Review queue", "Ask calculations",
    "Letter previews", "Letter style", "Run log",
])

with tab_problems:
    tip(
        "Every held-back record is listed with the exact problem and a "
        "suggested correction. Nothing is fixed silently: you decide, on the "
        "next tab, what gets applied."
    )
    if len(exceptions):
        st.error(
            f"{len(exceptions)} donor record(s) were held back. No letters were "
            "created for them."
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

with tab_fixes:
    tip(
        "This is the human gate. Each suggested fix shows the current value, "
        "the value computed from the donor's own gift history, and the reason. "
        "Untick anything you disagree with, then apply and re-run. Remember to "
        "make the same fix in your source system so it stays fixed."
    )
    if len(corrections) == 0:
        st.success("No suggested corrections for this file.")
    else:
        editable = corrections.copy()
        editable.insert(0, "approve", True)
        edited = st.data_editor(
            editable, use_container_width=True, hide_index=True,
            disabled=[c for c in editable.columns if c != "approve"],
            column_config={"approve": st.column_config.CheckboxColumn("Approve")},
        )
        approved = edited[edited["approve"] == True]  # noqa: E712
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                f"Apply {len(approved)} approved fix(es) and re-run checks",
                type="primary", disabled=len(approved) == 0,
            ):
                corrected = apply_corrections_to_bytes(
                    st.session_state["donor_bytes"],
                    st.session_state["donor_suffix"], approved,
                )
                start_run(corrected, ".csv",
                          st.session_state["source"] + " (corrected)")
                st.rerun()
        with col_b:
            if len(approved):
                corrected_preview = apply_corrections_to_bytes(
                    st.session_state["donor_bytes"],
                    st.session_state["donor_suffix"], approved,
                )
                st.download_button(
                    "Download corrected file for your source system",
                    corrected_preview, file_name="donors_corrected.csv",
                    use_container_width=True,
                )

with tab_review:
    tip(
        "Review levels are policy, not preference: every Platinum letter gets "
        "individual review, any warning means review is recommended, and low "
        "confidence or special routing makes it mandatory. Lapsed major donors "
        "never get a form letter; they appear here routed to personal outreach."
    )
    order = {"mandatory": 0, "recommended": 1, "none": 2}
    queue = manifest.sort_values(by="review_level", key=lambda s: s.map(order))
    st.dataframe(
        queue[["donor_name", "tier", "status", "ask_amount", "confidence",
               "review_level", "review_reasons", "warnings"]],
        use_container_width=True, hide_index=True,
    )

with tab_asks:
    tip(
        "Every ask amount is calculated by the policy script, never estimated. "
        "The trace column shows each step, so any number can be explained to a "
        "donor, an auditor, or a new team member."
    )
    st.dataframe(
        result["computed"][["donor_name", "tier", "status", "largest_gift",
                            "lifetime_total", "ask_amount", "ask_trace"]],
        use_container_width=True, hide_index=True,
    )

with tab_letters:
    tip(
        "Preview any drafted letter. Letters use approved campaign language "
        "plus your adopted style preferences; facts and amounts come only "
        "from verified data."
    )
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

with tab_style:
    tip(
        "Teach the system your voice, safely. Save your edited copies of "
        "drafted letters (same file names) and upload them here. A change is "
        "suggested only after it appears in 3 or more of your edits, only for "
        "personality-level items (the closing phrase, a P.S. line), and it "
        "takes effect only when a named person adopts it. Facts, amounts, and "
        "claims can never be changed this way."
    )
    if STYLE_PROFILE.exists():
        profile = json.loads(STYLE_PROFILE.read_text(encoding="utf-8"))
        st.success(
            "Active style profile: "
            + ", ".join(f"{k} = \"{v}\"" for k, v in profile.items()
                        if k in ("closing_phrase", "ps_line"))
            + f" (approved by {profile.get('approved_by', 'unknown')} "
              f"on {profile.get('approved_on', '?')})"
        )
    edited_files = st.file_uploader(
        "Your edited letters (HTML, same file names as the drafts)",
        type=["html"], accept_multiple_files=True,
    )
    if edited_files and st.button("Analyze my edits"):
        st.session_state["style_report"] = learn_style_from_uploads(letters, edited_files)
    style_report = st.session_state.get("style_report")
    if style_report:
        if "error" in style_report:
            st.error(style_report["error"])
        else:
            st.write(f"Letter pairs compared: {style_report['letter_pairs_compared']}")
            for note in style_report.get("manual_edits_detected", []):
                st.warning(note)
            for i, s in enumerate(style_report.get("suggestions", [])):
                line = (f"**{s['field']}** = \"{s['value']}\" "
                        f"(seen {s['evidence_edits']}x): {s['status']}")
                if s["status"] == "eligible for adoption":
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(line)
                    approver = c2.text_input("Approved by", key=f"appr_{i}",
                                             placeholder="Your name")
                    if c2.button("Adopt", key=f"adopt_{i}", disabled=not approver.strip()):
                        adopt_style(s["field"], s["value"], s["evidence_edits"],
                                    approver.strip())
                        st.session_state.pop("style_report", None)
                        st.rerun()
                else:
                    st.markdown(line)

with tab_log:
    tip(
        "The raw output of each pipeline step, exactly as it would appear if "
        "run from the command line. Useful when asking a technical colleague "
        "for help."
    )
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
