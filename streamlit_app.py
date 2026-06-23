"""review-queue - live demo (Streamlit Community Cloud).

Reads the committed promotion-records under queue/, decided/, and examples/
and renders the human-gate queue: AI proposes a candidate, a reviewer
approves / rejects / edits it with a diff and provenance, approved items
ship to a target. No network, no secrets - runs entirely off the committed
records.

Deploy: Streamlit Community Cloud -> New app -> repo AthenaTheOwl/review-queue,
branch main, main file streamlit_app.py.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from review_queue import records as records_mod
from review_queue import show as show_mod

REPO = Path(__file__).resolve().parent
ROOTS = [REPO / "queue", REPO / "decided", REPO / "examples"]

_STATUS_RANK = show_mod._STATUS_RANK


def load_records():
    return records_mod.iter_records(ROOTS)


st.set_page_config(page_title="review-queue - human-gate queue", layout="wide")
st.title("review-queue")
st.caption(
    "human-gated promotion queue for AI-generated candidates - a candidate lands "
    "as a typed record, a reviewer approves / rejects / edits it with a diff and "
    "provenance, approved items ship to a target. nothing ships without a recorded verdict."
)

recs = load_records()
if not recs:
    st.warning("no promotion-records found under queue/, decided/, or examples/")
    st.stop()

ranked = show_mod.rank(recs)
counts = show_mod.status_counts(ranked)
pending = counts.get("pending", 0)
decided = sum(counts.get(s, 0) for s in ("approved", "published", "rejected", "superseded"))

c1, c2, c3 = st.columns(3)
c1.metric("records", len(ranked))
c2.metric("pending a verdict", pending)
c3.metric("decided", decided)

# headline: what most needs attention.
if pending:
    oldest = min(
        (r for r in ranked if r.fm.get("status") == "pending"),
        key=lambda r: r.fm.get("created_at", ""),
    )
    st.info(
        f"**needs attention:** {pending} record(s) pending a human verdict - oldest is "
        f"`{oldest.fm.get('id')}` ({oldest.fm.get('record_type')}, queued "
        f"{oldest.fm.get('created_at')})."
    )
else:
    st.info("**queue is clear** - 0 records pending a human verdict.")

# interactive control: filter by status.
all_statuses = sorted(counts, key=lambda s: _STATUS_RANK.get(s, 9))
chosen = st.multiselect(
    "filter by status",
    options=all_statuses,
    default=all_statuses,
    help="rows are ranked with pending first, then most recent.",
)
shown = [r for r in ranked if r.fm.get("status") in chosen]


def _decision(r) -> str:
    v = r.fm.get("verdicts") or []
    return v[-1].get("decision", "-") if v else "-"


def _reviewer(r) -> str:
    v = r.fm.get("verdicts") or []
    return v[-1].get("reviewer", "-") if v else "-"


st.subheader("queue")
st.dataframe(
    [
        {
            "id": r.fm.get("id"),
            "status": r.fm.get("status"),
            "type": r.fm.get("record_type"),
            "decision": _decision(r),
            "reviewer": _reviewer(r),
            "created": r.fm.get("created_at"),
            "target": r.fm.get("target"),
        }
        for r in shown
    ],
    use_container_width=True,
    hide_index=True,
)

if not shown:
    st.stop()

# record inspector: pick a record, see its diff / provenance / verdict.
st.subheader("record inspector")
by_id = {r.fm.get("id"): r for r in shown}
picked_id = st.selectbox("pick a record", options=list(by_id.keys()))
r = by_id[picked_id]

i1, i2, i3 = st.columns(3)
i1.metric("status", r.fm.get("status", "?"))
i2.metric("type", r.fm.get("record_type", "?"))
i3.metric("verdict", _decision(r))

st.markdown(f"**target:** `{r.fm.get('target')}`")
st.markdown(f"**provenance:** `{r.fm.get('provenance_ref')}`")
st.markdown(f"**candidate:** `{r.fm.get('candidate_ref')}`")

st.markdown("**candidate diff**")
st.code(r.fm.get("diff", "(no diff)"), language="diff")

verdicts = r.fm.get("verdicts") or []
if verdicts:
    st.markdown("**verdicts**")
    for v in verdicts:
        line = (
            f"- **{v.get('decision')}** by {v.get('reviewer')} "
            f"at {v.get('decided_at')}"
        )
        if v.get("note"):
            line += f"  \n  note: {v['note']}"
        st.markdown(line)
        if v.get("edit_diff"):
            st.code(v["edit_diff"], language="diff")
else:
    st.markdown("_no verdict yet - this record is pending a human decision._")

st.caption(
    "v0.1 ships committed example records. the schema + state machine live in "
    "`review_queue/`; this page reads the committed records under queue/, decided/, "
    "examples/. repo: github.com/AthenaTheOwl/review-queue"
)
