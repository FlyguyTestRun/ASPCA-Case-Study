"""Donor outreach review interface.

A guided workflow for fundraising staff, four steps, one path:

    1. Upload      bring in the donor file, set the campaign
    2. Findings    every error and warning explained; approve fixes, resubmit
    3. Review      search any donor, read their letter, sign off record by record
    4. Finalize    sign-off is recorded to the decision history, then export

This app contains no business logic. It shells out to the same scripts the
skill uses, so what you see here is exactly what the pipeline does. Nothing
is ever sent from here, and nothing is finalized until a named person signs
off. Persistent changes (corrections, style adoptions, sign-offs) each write
an entry to docs/decision-log/, the running system's own ADR history.

Run with:
    streamlit run app/review_app.py
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skill" / "charity-donor-outreach"
SCRIPTS = SKILL_DIR / "scripts"
FIXTURE = SKILL_DIR / "assets" / "sample_donors.csv"
TEMPLATE = SKILL_DIR / "assets" / "template.html"
STYLE_PROFILE = REPO_ROOT / "feedback" / "style_profile.json"
DECISION_LOG = REPO_ROOT / "docs" / "decision-log"
ARCHIVE_ROOT = REPO_ROOT / "output" / "archive"
AUDIO_FILE = Path(__file__).resolve().parent / "assets" / "tutorial_walkthrough.wav"
TRANSCRIPT_FILE = Path(__file__).resolve().parent / "assets" / "tutorial_transcript.md"

sys.path.insert(0, str(SCRIPTS))
import donor_rules as rules  # noqa: E402

CAMPAIGN_LABELS = {
    "emergency_appeal": "Emergency appeal",
    "annual_fund": "Annual fund",
    "capital_campaign": "Capital campaign",
    "event_fundraiser": "Event fundraiser",
}
STEP_NAMES = ["Upload", "Findings", "Review", "Finalize"]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# Mirrors the pipeline table in SKILL.md. Used to label which script is
# running live, and to teach the mapping between what this interface does
# and the actual code behind it, for anyone studying this as a reference
# implementation rather than just using it.
PIPELINE_STAGES = [
    {
        "script": "scripts/validate_input.py",
        "title": "1. Schema and business-rule validation",
        "purpose": (
            "Checks the file's structure against references/donor.schema.json, "
            "then recomputes tier, lapsed status, and totals from the gift "
            "history and checks them against what the file states. Nothing "
            "moves forward until this passes."
        ),
        "determinism": "Deterministic",
    },
    {
        "script": "scripts/calculate_ask.py",
        "title": "2. Deterministic ask calculation",
        "purpose": (
            "Computes every donor's ask amount with a fixed formula and one "
            "rounding step at the end, plus a confidence score. No arithmetic "
            "ever happens inside a language model in this system."
        ),
        "determinism": "Deterministic",
    },
    {
        "script": "scripts/generate_letters.py",
        "title": "3. Letter assembly, schema check, and render",
        "purpose": (
            "Builds a structured letter object per donor from approved "
            "language, validates it against references/letter_schema.json, "
            "and only then renders it to HTML. A model is never in this path "
            "unless a user explicitly asks for personalization (see "
            "prompts/personalization_prompt.md), and even then only within "
            "hard guardrails."
        ),
        "determinism": "Deterministic",
    },
]

st.set_page_config(page_title="Donor Outreach Review", page_icon="📬", layout="wide")


def tip(text: str) -> None:
    """Tutorial callout, shown only when tutorial mode is on."""
    if st.session_state.get("tutorial", True):
        st.info(text, icon="🎓")


def operator_name() -> str:
    return (st.session_state.get("operator") or "").strip()


_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+.!|>~-])")


def md_escape(text) -> str:
    """Escape markdown-significant characters in donor-supplied free text
    before it is interpolated into st.markdown/st.error/st.warning.

    Unlike tier, status, or review_level (schema-constrained enums checked
    in validate_input.py before a row ever reaches this app), donor_name is
    arbitrary text straight from the uploaded file. Streamlit's default
    unsafe_allow_html=False already blocks raw HTML, but markdown link
    syntax is still parsed, so an unescaped name could render as a link or
    otherwise distort the layout.
    """
    return _MD_SPECIAL.sub(r"\\\1", str(text))


def run_pipeline(donor_bytes: bytes, donor_suffix: str, config: dict,
                  status=None) -> dict:
    """Run validate -> calculate -> generate in a temp dir, return all outputs.

    If a Streamlit status container is given, it is updated with the exact
    script being executed as each stage runs, so a viewer watching the
    interface can see the real command line behind each step.
    """
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
        for stage_index, (script, extra) in enumerate(steps):
            if status is not None:
                stage_info = PIPELINE_STAGES[stage_index]
                status.update(label=f"Running {stage_info['script']}")
                status.write(f"**{stage_info['title']}**  \n{stage_info['purpose']}")
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / script), "--config", str(config_path),
                 "--workdir", str(workdir), *extra],
                capture_output=True, text=True,
            )
            logs.append(f"$ {script}\n{result.stdout}{result.stderr}")
            if result.returncode != 0:
                if status is not None:
                    status.update(label=f"{script} failed", state="error")
                return {"ok": False, "error": result.stderr or result.stdout, "step": script}
        if status is not None:
            status.update(label="All three stages complete", state="complete")

        letters = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((outdir / "letters").glob("*.html"))
        }
        return {
            "ok": True,
            "logs": "\n".join(logs),
            "metrics": json.loads((workdir / "run_metrics.json").read_text(encoding="utf-8")),
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
    """Apply approved corrections to the uploaded file, return corrected CSV bytes.

    Every field is passed through csv_safe before writing: the corrections
    only touch the field being fixed (usually tier), so every other column,
    including donor_name, is carried through from whatever the uploaded
    file said, unexamined. This file is also handed straight back to Excel
    via a download button, exactly the fundraising-staff-facing CSV export
    csv_safe already protects everywhere else in the pipeline (ADR 0018).
    """
    if donor_suffix in (".xlsx", ".xls"):
        frame = pd.read_excel(io.BytesIO(donor_bytes), dtype=str).fillna("")
    else:
        frame = pd.read_csv(io.BytesIO(donor_bytes), dtype=str).fillna("")
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    for _, fix in approved.iterrows():
        row_index = int(fix["row_number"]) - 2  # data rows start at file row 2
        if 0 <= row_index < len(frame) and fix["field"] in frame.columns:
            frame.loc[row_index, fix["field"]] = fix["suggested_value"]
    frame = frame.map(rules.csv_safe)
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
        return json.loads((workdir / "style_suggestions.json").read_text(encoding="utf-8"))


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
    rules.record_decision(
        DECISION_LOG,
        title=f"Adopted letter style preference: {field}",
        problem=("Reviewers repeatedly made the same edit to drafted letters, "
                 "which meant the house style did not match the team's voice."),
        decision=(f"{field} set to {value!r}, observed identically in "
                  f"{evidence} edited letters and passed through the style "
                  "guardrails."),
        effect=("Future letters use this preference automatically. It can only "
                "affect personality-level content and is re-checked against "
                "the guardrails on every generation run."),
        approved_by=approved_by,
        source="review app, letter style panel",
    )


def export_manifest(manifest: pd.DataFrame) -> pd.DataFrame:
    reviewed = st.session_state.get("reviewed", {})
    out = manifest.copy()
    out["reviewed"] = out["donor_id"].map(lambda d: "yes" if reviewed.get(d) else "no")
    out["reviewed_by"] = out["donor_id"].map(
        lambda d: operator_name() if reviewed.get(d) else ""
    )
    return out


def letters_zip(letters: dict[str, str], manifest: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("manifest.csv", export_manifest(manifest).to_csv(index=False))
        for name, content in letters.items():
            bundle.writestr(f"letters/{name}", content)
    return buffer.getvalue()


def start_run(data: bytes, suffix: str, label: str, config: dict) -> None:
    st.session_state["donor_bytes"] = data
    st.session_state["donor_suffix"] = suffix
    st.session_state["source"] = label
    with st.status("Starting the pipeline...", expanded=True) as status:
        st.session_state["result"] = run_pipeline(data, suffix, config, status=status)
    st.session_state["reviewed"] = {}
    st.session_state["signoff_recorded"] = False
    st.session_state["run_id"] = st.session_state.get("run_id", 0) + 1
    st.session_state["stage"] = 2


def archive_current_run(result: dict, label: str, note: str, approved_by: str) -> Path:
    """Snapshot the in-memory run result to a labeled, timestamped folder.

    generate_letters.py clears output/letters/ at the start of every run
    (ADR 0022), and this app runs the pipeline in a temp directory that is
    gone the moment run_pipeline returns, so archiving happens here, from
    the letters and manifest already held in memory, not from a live
    output directory. See ADR 0027.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = rules.slugify(label)[:60] or "run"
    archive_dir = ARCHIVE_ROOT / f"{timestamp}-{slug}"
    letters_dir = archive_dir / "letters"
    letters_dir.mkdir(parents=True, exist_ok=False)

    result["manifest"].to_csv(archive_dir / "manifest.csv", index=False)
    for name, content in result["letters"].items():
        (letters_dir / name).write_text(content, encoding="utf-8")

    letter_count = int((result["manifest"]["letter_file"] != "").sum())
    info = {
        "label": label,
        "note": note,
        "archived_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rules_version": rules.RULES_VERSION,
        "donor_count": len(result["manifest"]),
        "letter_count": letter_count,
        "approved_by": approved_by,
    }
    (archive_dir / "archive_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    rules.record_decision(
        DECISION_LOG,
        title=f"Archived run: {label}",
        problem=("A completed, signed-off run needed to be preserved before "
                 "the next run clears and overwrites output/letters/."),
        decision=(f"Snapshot saved with {letter_count} letters and "
                  f"{info['donor_count']} donor records."),
        effect=("This snapshot is permanent and unaffected by any future "
                "run; it stays until removed by hand."),
        approved_by=approved_by,
        source="review app, finalize step",
    )
    return archive_dir


def go(stage: int) -> None:
    st.session_state["stage"] = stage


# ---------------------------------------------------------------- sidebar --

st.title("Donor Outreach Review")

with st.sidebar:
    st.text_input(
        "Your name", key="operator",
        help="Recorded with every approval you make: corrections, style "
             "adoptions, and the final sign-off all carry your name in the "
             "decision history.",
    )
    st.toggle(
        "Tutorial mode", key="tutorial",
        value=st.session_state.get("tutorial", True),
        help="Plain-language guidance beside each step.",
    )
    if st.toggle("Audio walkthrough", value=False):
        if AUDIO_FILE.exists():
            st.audio(AUDIO_FILE.read_bytes(), format="audio/wav")
            if TRANSCRIPT_FILE.exists():
                with st.expander("Transcript"):
                    st.markdown(TRANSCRIPT_FILE.read_text(encoding="utf-8"))
        else:
            st.warning("Audio file not found; see app/assets/README.md.")

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
        help="Letters may only mention matching when this is checked; "
             "unconfirmed match claims are blocked entirely.",
    )
    match_sponsor = match_terms = ""
    if match_confirmed:
        match_sponsor = st.text_input("Match sponsor")
        match_terms = st.text_input("Match terms",
                                    placeholder="doubled up to $100,000 through August 31")

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

# ----------------------------------------------------------------- header --

stage = st.session_state.get("stage", 1)
cols = st.columns(4)
for index, name in enumerate(STEP_NAMES, start=1):
    marker = "●" if index == stage else ("✔" if index < stage else "○")
    cols[index - 1].markdown(f"**{marker} Step {index}: {name}**")
st.progress((stage - 1) / 3)

result = st.session_state.get("result")

# ---------------------------------------------------------- stage 1: upload --

if stage == 1:
    tip(
        "Start here. Set the campaign in the sidebar (especially the as-of "
        "date), then upload your donor export or try the built-in sample. "
        "The checks read the gift history itself and verify everything else "
        "against it, so mislabeled tiers, unbalanced totals, and impossible "
        "dates are caught here, not in a donor's mailbox."
    )

    with st.expander("Two ways to start: your own file, or the built-in sample"):
        st.markdown(
            "**Upload your own donor file.** CSV or Excel, up to 5 MB. Every "
            "column this system needs is listed in "
            "`skill/charity-donor-outreach/references/input_schema.md`; "
            "donor name and giving history are the only required columns, "
            "everything else is optional and gets checked if present.\n\n"
            "**Or try the built-in sample.** The button below loads "
            "`skill/charity-donor-outreach/assets/sample_donors.csv`, the "
            "same fifty donors from the original case study's own skill "
            "file, transcribed field for field, planted errors included. "
            "It exists specifically so this pipeline always has something "
            "real to run against without needing live donor data, and it "
            "doubles as the permanent regression fixture: [ADR "
            "0019](https://github.com/FlyguyTestRun/ASPCA-Case-Study/blob/main/docs/adr/0019-data-provenance-and-fixture-fidelity.md) "
            "covers where it came from."
        )

    with st.expander("How this pipeline actually works, script by script"):
        st.markdown(
            "Every button in this app calls one of three Python scripts, in "
            "the same order, every time. Nothing here is a black box; each "
            "one is short enough to read end to end."
        )
        for stage_info in PIPELINE_STAGES:
            st.markdown(
                f"**`{stage_info['script']}`**: {stage_info['title']}  \n"
                f"{stage_info['purpose']}"
            )
        st.caption(
            "Full source: skill/charity-donor-outreach/scripts/. The "
            "orchestration instructions an AI assistant follows to run "
            "these in order are in SKILL.md; the business rules behind the "
            "numbers are in references/policy.md."
        )

    upload_col, sample_col = st.columns([3, 1])
    with upload_col:
        uploaded = st.file_uploader("Donor file (CSV or Excel)", type=["csv", "xlsx", "xls"])
    with sample_col:
        st.write("")
        if st.button("Try the sample file", width="stretch"):
            start_run(FIXTURE.read_bytes(), ".csv", FIXTURE.name, config)
            st.rerun()
    if uploaded is not None:
        if len(uploaded.getvalue()) > MAX_UPLOAD_BYTES:
            st.error(
                "That file is larger than 5 MB. Donor exports this size should "
                "go through the batch pipeline directly; ask a technical "
                "colleague to run the validate script on it."
            )
        elif st.button("Run checks", type="primary"):
            start_run(uploaded.getvalue(),
                      Path(uploaded.name).suffix.lower() or ".csv",
                      uploaded.name, config)
            st.rerun()
    st.stop()

if result is None or not result.get("ok"):
    if result is not None:
        st.error(f"The {result['step']} step could not run:\n\n{result['error']}")
    if st.button("Back to upload"):
        go(1)
        st.rerun()
    st.stop()

report = result["report"]
manifest = result["manifest"]
exceptions = result["exceptions"]
corrections = result["corrections"]
letters = result["letters"]
run_id = st.session_state.get("run_id", 0)

st.caption(f"File: {st.session_state.get('source', 'donor file')}")

# -------------------------------------------------------- stage 2: findings --

if stage == 2:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows in file", report["rows_in"])
    m2.metric("Passed all checks", report["rows_validated"])
    m3.metric("Held for data fixes", report["rows_excepted"])
    m4.metric("Passed with warnings", report["rows_with_warnings"])

    tip(
        "Proof the data before any letter is finalized. Held records are "
        "listed with the exact problem and a suggested fix; nothing is "
        "corrected without your approval, and applying fixes re-runs every "
        "check. Warnings do not hold a record, but they lower its confidence "
        "and add it to the review queue in the next step."
    )

    if len(exceptions) == 0:
        st.success("No records were held back. Every row passed validation.")
    else:
        st.error(
            f"{len(exceptions)} record(s) held back, no letters created for "
            "them. Approve the fixes you agree with, then apply and re-check."
        )
        editable = corrections.copy()
        editable.insert(0, "approve", True)
        edited = st.data_editor(
            editable, width="stretch", hide_index=True,
            disabled=[c for c in editable.columns if c != "approve"],
            column_config={"approve": st.column_config.CheckboxColumn("Approve")},
            key=f"fixes_{run_id}",
        )
        approved = edited[edited["approve"] == True]  # noqa: E712
        if not operator_name():
            st.warning("Enter your name in the sidebar to apply fixes; every "
                       "approval is recorded with a name.")
        apply_col, download_col = st.columns(2)
        with apply_col:
            if st.button(
                f"Apply {len(approved)} approved fix(es) and re-run checks",
                type="primary",
                disabled=len(approved) == 0 or not operator_name(),
            ):
                corrected = apply_corrections_to_bytes(
                    st.session_state["donor_bytes"],
                    st.session_state["donor_suffix"], approved,
                )
                changes = [
                    f"row {fix['row_number']} ({fix['donor_name']}): "
                    f"{fix['field']} {fix['current_value']!r} -> "
                    f"{fix['suggested_value']!r} ({fix['reason']})"
                    for _, fix in approved.iterrows()
                ]
                rules.record_decision(
                    DECISION_LOG,
                    title=(f"Applied {len(approved)} data correction(s) to "
                           f"{st.session_state['source']}"),
                    problem=("Validation held these records because stated "
                             "values contradicted the gift history, which is "
                             "the source of truth."),
                    decision="Corrections approved and applied:\n\n"
                             + "\n".join(f"- {line}" for line in changes),
                    effect=("The corrected file supersedes the original for "
                            "this run. The same corrections must be made in "
                            "the source system so the discrepancy does not "
                            "recur."),
                    approved_by=operator_name(),
                    source="review app, findings step",
                )
                start_run(corrected, ".csv",
                          st.session_state["source"].replace(" (corrected)", "")
                          + " (corrected)", config)
                st.rerun()
        with download_col:
            if len(approved):
                st.download_button(
                    "Download corrected file for your source system",
                    apply_corrections_to_bytes(
                        st.session_state["donor_bytes"],
                        st.session_state["donor_suffix"], approved),
                    file_name="donors_corrected.csv", width="stretch",
                )

    warned = manifest[manifest["warnings"] != ""]
    if len(warned):
        st.warning(f"{len(warned)} record(s) passed with warnings; their "
                   "letters exist and are queued for review in the next step.")
        st.dataframe(
            warned[["donor_name", "tier", "status", "confidence", "warnings"]],
            width="stretch", hide_index=True,
        )

    nav_back, nav_next = st.columns([1, 3])
    if nav_back.button("Back"):
        go(1)
        st.rerun()
    next_label = "Continue to letter review"
    if len(exceptions):
        next_label += f" ({len(exceptions)} held record(s) stay excluded)"
    if nav_next.button(next_label, type="primary"):
        go(3)
        st.rerun()
    st.stop()

# ---------------------------------------------------------- stage 3: review --

required_ids = manifest.loc[manifest["review_level"] == "mandatory", "donor_id"].tolist()
reviewed = st.session_state.setdefault("reviewed", {})

if stage == 3:
    tip(
        "Check every record by name before anything is finalized. Search or "
        "scroll the full table, open any donor to read their letter and the "
        "step-by-step ask calculation, and mark it reviewed. Records marked "
        "mandatory must all be signed off before the final step unlocks."
    )

    done_required = sum(1 for donor_id in required_ids if reviewed.get(donor_id))
    st.markdown(
        f"**Required reviews: {done_required} of {len(required_ids)} complete.** "
        "Platinum letters, low-confidence records, and special routings are "
        "always reviewed by a person."
    )

    search = st.text_input("Search donors by name", placeholder="start typing a name...")
    table = manifest.copy()
    table["reviewed"] = table["donor_id"].map(lambda d: "✔" if reviewed.get(d) else "")
    if search.strip():
        table = table[table["donor_name"].str.contains(search.strip(), case=False)]

    st.dataframe(
        table[["reviewed", "donor_name", "tier", "status", "ask_amount",
               "confidence", "review_level", "warnings", "review_reasons",
               "letter_file"]],
        width="stretch", hide_index=True, height=280,
    )

    options = table["donor_name"].tolist()
    if options:
        chosen = st.selectbox("Open a donor record", options)
        row = manifest[manifest["donor_name"] == chosen].iloc[0]
        computed_row = result["computed"]
        computed_row = computed_row[computed_row["donor_name"] == chosen].iloc[0]

        left, right = st.columns([3, 2])
        with left:
            if row["letter_file"]:
                file_name = Path(row["letter_file"]).name
                preview_dir = Path(tempfile.gettempdir()) / "donor_review_previews"
                preview_dir.mkdir(parents=True, exist_ok=True)
                preview_path = preview_dir / file_name
                preview_path.write_text(letters[file_name], encoding="utf-8")
                st.iframe(preview_path, height=430)
            else:
                st.info(
                    "No letter for this record, by policy: "
                    + (row["review_reasons"] or "see review reasons")
                )
        with right:
            st.markdown(
                f"**{md_escape(row['donor_name'])}**  \n"
                f"Tier {row['tier']}, {row['status']}  \n"
                f"Ask: {'$' + row['ask_amount'] if row['ask_amount'] else 'none'}  \n"
                f"Confidence {row['confidence']} ({row['confidence_band']}), "
                f"review: {row['review_level']}"
            )
            if row["warnings"]:
                st.warning(row["warnings"])
            if row["review_reasons"]:
                st.error(row["review_reasons"])
            with st.expander("How this ask was calculated"):
                for step in computed_row["ask_trace"].split(" -> "):
                    st.markdown(f"- {step}")
            checked = st.checkbox(
                "Reviewed and approved" + (f" by {operator_name()}" if operator_name() else ""),
                value=bool(reviewed.get(row["donor_id"])),
                key=f"rev_{run_id}_{row['donor_id']}",
                disabled=not operator_name(),
                help="Enter your name in the sidebar first." if not operator_name() else None,
            )
            reviewed[row["donor_id"]] = checked

    with st.expander("Teach the system your letter style"):
        st.markdown(
            "Edit drafted letters the way you like them (keep the file names), "
            "upload the edited copies, and a change seen 3 or more times is "
            "suggested for adoption. Style can affect the closing and a P.S. "
            "line only, never amounts or claims."
        )
        if STYLE_PROFILE.exists():
            profile = json.loads(STYLE_PROFILE.read_text(encoding="utf-8"))
            active = ", ".join(f"{k} = \"{v}\"" for k, v in profile.items()
                               if k in ("closing_phrase", "ps_line") and v)
            if active:
                st.success(f"Active style: {active} (approved by "
                           f"{profile.get('approved_by', 'unknown')})")
        edited_files = st.file_uploader(
            "Your edited letters (HTML)", type=["html"], accept_multiple_files=True,
        )
        if edited_files and st.button("Analyze my edits"):
            st.session_state["style_report"] = learn_style_from_uploads(letters, edited_files)
        style_report = st.session_state.get("style_report")
        if style_report:
            if "error" in style_report:
                st.error(style_report["error"])
            else:
                for note in style_report.get("manual_edits_detected", []):
                    st.warning(note)
                for i, s in enumerate(style_report.get("suggestions", [])):
                    line = (f"**{s['field']}** = \"{s['value']}\" "
                            f"(seen {s['evidence_edits']}x): {s['status']}")
                    st.markdown(line)
                    if s["status"] == "eligible for adoption":
                        if st.button(f"Adopt (recorded as {operator_name() or '...'})",
                                     key=f"adopt_{i}", disabled=not operator_name()):
                            adopt_style(s["field"], s["value"],
                                        s["evidence_edits"], operator_name())
                            st.session_state.pop("style_report", None)
                            st.rerun()

    nav_back, nav_next = st.columns([1, 3])
    if nav_back.button("Back to findings"):
        go(2)
        st.rerun()
    if nav_next.button("Continue to finalize", type="primary"):
        go(4)
        st.rerun()
    st.stop()

# -------------------------------------------------------- stage 4: finalize --

if stage == 4:
    tip(
        "The gate. Every mandatory-review record must be signed off before "
        "export unlocks. The sign-off itself is written to the decision "
        "history (docs/decision-log/) with your name, so how this batch was "
        "cleared is always answerable. Even after export, nothing is sent: "
        "delivery happens through your existing channels."
    )

    pending = [donor_id for donor_id in required_ids if not reviewed.get(donor_id)]
    letters_count = int((manifest["letter_file"] != "").sum())
    st.markdown(
        f"**Batch summary:** {report['rows_in']} rows in, "
        f"{report['rows_validated']} validated, {report['rows_excepted']} held, "
        f"{letters_count} letters drafted, {len(required_ids)} required reviews."
    )

    if pending:
        names = manifest[manifest["donor_id"].isin(pending)]["donor_name"].tolist()
        st.error(
            f"{len(pending)} required review(s) outstanding: "
            f"{', '.join(md_escape(n) for n in names)}. "
            "Go back and sign each one off."
        )
        if st.button("Back to review"):
            go(3)
            st.rerun()
        st.stop()

    st.success("All required reviews are signed off.")

    if not st.session_state.get("signoff_recorded"):
        if not operator_name():
            st.warning("Enter your name in the sidebar; the sign-off is recorded with a name.")
        if st.button("Record sign-off in the decision history", type="primary",
                     disabled=not operator_name()):
            reviewed_names = manifest[
                manifest["donor_id"].map(lambda d: bool(reviewed.get(d)))
            ]["donor_name"].tolist()
            entry = rules.record_decision(
                DECISION_LOG,
                title=(f"Review sign-off: {st.session_state['source']}, "
                       f"{CAMPAIGN_LABELS.get(config['campaign_type'], config['campaign_type'])}"),
                problem=(f"{len(required_ids)} record(s) required individual "
                         "human review before this batch could be finalized."),
                decision=("Each required record was opened and signed off: "
                          + ", ".join(reviewed_names) + "."),
                effect=(f"The batch ({letters_count} letters) is cleared for "
                        "delivery through existing, human-controlled channels. "
                        "Held records remain excluded until their data is fixed."),
                approved_by=operator_name(),
                source="review app, finalize step",
            )
            st.session_state["signoff_recorded"] = True
            st.session_state["signoff_entry"] = str(entry)
            st.rerun()
    else:
        st.success(f"Sign-off recorded: {st.session_state.get('signoff_entry', '')}")
        d1, d2, d3 = st.columns(3)
        d1.download_button(
            "Review manifest (CSV)", export_manifest(manifest).to_csv(index=False),
            file_name="manifest.csv", width="stretch",
        )
        d2.download_button(
            "Held records (CSV)", exceptions.to_csv(index=False),
            file_name="exceptions.csv", width="stretch",
        )
        d3.download_button(
            "Letters + manifest (ZIP)", letters_zip(letters, manifest),
            file_name="letters_for_review.zip", width="stretch",
        )

        st.divider()
        tip(
            "generate_letters.py clears output/letters/ at the start of "
            "every run, on purpose, so the manifest and the folder can "
            "never disagree (ADR 0022). That means this run's output is "
            "otherwise gone the moment the next one starts. Archiving here "
            "keeps a permanent, labeled copy before that happens."
        )
        st.subheader("Keep a record of this run")
        archive_label = st.text_input(
            "Label for this archive",
            value=f"{st.session_state.get('source', 'run')} - "
                  f"{CAMPAIGN_LABELS.get(config['campaign_type'], config['campaign_type'])}",
        )
        archive_note = st.text_input("Note (optional)", placeholder="anything worth remembering about this batch")
        if st.button("Archive this run", disabled=not operator_name() or not archive_label.strip()):
            archive_dir = archive_current_run(
                result, archive_label.strip(), archive_note.strip(), operator_name()
            )
            st.success(f"Archived to {archive_dir.relative_to(REPO_ROOT)}")
        if not operator_name():
            st.caption("Enter your name in the sidebar to archive a run.")

        past_runs = rules.list_archived_runs(ARCHIVE_ROOT)
        if past_runs:
            with st.expander(f"Past archived runs ({len(past_runs)})"):
                for past in past_runs:
                    st.markdown(
                        f"**{past['label']}**: {past['letter_count']} letters, "
                        f"{past['donor_count']} donors, rules {past['rules_version']}, "
                        f"archived {past['archived_at_utc']} by {past.get('approved_by', 'unknown')}"
                    )
                    if past.get("note"):
                        st.caption(past["note"])

    if st.button("Back to review", key="back_from_finalize"):
        go(3)
        st.rerun()

# ------------------------------------------------------------------ footer --

with st.expander("Run log and metrics"):
    metrics = result.get("metrics", {})
    stage_rows = [
        {"stage": name, **values}
        for name, values in metrics.items()
        if isinstance(values, dict)
    ]
    if stage_rows:
        st.dataframe(pd.DataFrame(stage_rows).fillna(""), width="stretch", hide_index=True)
        if isinstance(metrics.get("token_cost"), str):
            st.caption(f"Token cost: {metrics['token_cost']}.")
    st.code(result["logs"])

st.caption(
    "Letters are drafts for human review. This tool never sends email and "
    "never changes your source data."
)
