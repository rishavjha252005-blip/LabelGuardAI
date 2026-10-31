import streamlit as st
import pandas as pd
import re, json, difflib, hashlib
from datetime import datetime
from io import BytesIO

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    from PIL import Image
except Exception:
    Image = None
try:
    import pytesseract
except Exception:
    pytesseract = None

st.set_page_config(page_title="LabelGuard AI | Demo", page_icon="🛡️", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; max-width: 1400px;}
.hero {padding: 1.25rem 1.5rem; border-radius: 18px; background: linear-gradient(110deg,#e7f3ff,#f7f9ff); border:1px solid #d8e8fb;}
.hero h1 {color:#12346b; margin:0;}
.hero p {color:#304766; margin:.35rem 0 0 0;}
.small-note {font-size: .86rem; color:#5b6573;}
.metric-card {padding:12px; border:1px solid #dbe7f5; border-radius:12px; background:#fbfdff;}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🛡️ LabelGuard AI</h1><p>Intelligent medical-device label validation, revision comparison & change-impact review</p></div>', unsafe_allow_html=True)
st.caption("DEMO PROTOTYPE • Uses configurable example checks, not an approved regulatory rules engine.")

with st.sidebar:
    st.header("Review configuration")
    market = st.multiselect("Target markets", ["India", "European Union", "United States"], default=["India", "European Union"])
    product_type = st.selectbox("Example device category", ["Surgical device", "General medical device", "Diagnostic device"])
    required_terms = st.text_area("Required text/checklist terms (one per line)", "UDI\nLOT\nREF\nSTERILE\nDo not re-sterilize\nManufacturer", height=145)
    st.markdown("---")
    st.markdown("**Prototype limits**")
    st.caption("Rules are illustrative and must be reviewed against current, product-specific requirements by qualified regulatory/quality staff.")

def extract_text(uploaded):
    if uploaded is None:
        return "", "No file"
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith(".pdf"):
        if fitz:
            doc = fitz.open(stream=raw, filetype="pdf")
            text = "\\n".join(page.get_text("text") for page in doc)
            if text.strip():
                return text, "PDF text extraction"
            return "", "Scanned PDF: OCR not available in this runtime"
        return "", "PDF extraction unavailable (install PyMuPDF)"
    if name.endswith((".txt", ".md", ".csv")):
        return raw.decode("utf-8", errors="ignore"), "Text extraction"
    if name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")):
        if Image and pytesseract:
            try:
                image = Image.open(BytesIO(raw))
                return pytesseract.image_to_string(image), "OCR extraction"
            except Exception as e:
                return "", f"OCR failed: {e}"
        return "", "Image uploaded; OCR requires Pillow, pytesseract and Tesseract OCR installed"
    return raw.decode("utf-8", errors="ignore"), "Best-effort text extraction"

def validate(text, terms, markets):
    t = text.lower()
    rows = []
    def add(issue, severity, evidence, status="Open", category="Content"):
        rows.append({"Issue":issue,"Severity":severity,"Category":category,"Evidence":evidence or "No matching text found","Status":status})
    if not text.strip():
        add("Unable to extract readable label text", "High", "Use a text-based PDF/TXT or enable OCR for image/scanned inputs", category="Extraction")
        return rows
    for term in terms:
        term = term.strip()
        if term and term.lower() not in t:
            sev = "High" if term.lower() in ["sterile", "do not re-sterilize", "udi"] else "Medium"
            add(f"Required checklist term not detected: {term}", sev, f"Expected term: {term}", category="Checklist")
    if not re.search(r'\b(udi|\(01\)|01\d{10,})\b', t):
        add("UDI / device identifier pattern not detected", "High", "No recognizable UDI text pattern found", category="Identifier")
    if not re.search(r'\b(lot|batch)\b', t):
        add("Lot/batch traceability field not detected", "Medium", "No LOT or BATCH field found", category="Traceability")
    if not re.search(r'\b(ref|catalogue|catalog)\b', t):
        add("Reference/catalogue field not detected", "Medium", "No REF/catalogue field found", category="Traceability")
    if markets:
        add("Market-specific review required", "Medium", "Configured markets: " + ", ".join(markets) + ". Verify applicable symbol, language and UDI requirements.", category="Regulatory review")
    if not rows:
        add("No configured checklist issues detected", "Low", "This is not proof of compliance; manual review remains required", status="Review", category="Summary")
    return rows

def compare_text(old, new):
    old_lines = [x.strip() for x in old.splitlines() if x.strip()]
    new_lines = [x.strip() for x in new.splitlines() if x.strip()]
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines)
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            changes.append({"Change type":tag.title(),
                            "Approved label text":" | ".join(old_lines[i1:i2]) or "—",
                            "Revised label text":" | ".join(new_lines[j1:j2]) or "—",
                            "Review priority":"High" if any(k in (" ".join(old_lines[i1:i2]+new_lines[j1:j2])).lower() for k in ["steril", "warning", "contraind", "do not", "expiry", "patient"]) else "Medium"})
    return changes

def readme_text():
    return """# LabelGuard AI Demo Prototype

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run: `pip install -r requirements.txt`
4. Run: `streamlit run app.py`

## Features
- Upload label PDF, image, or text file
- Extract text where supported
- Run configurable checklist checks and basic UDI/LOT/REF pattern checks
- Compare approved and revised label text
- Generate a downloadable CSV and JSON review report
- Display illustrative change-impact prompts

## Demo safety note
This is a proof-of-concept, not a certified regulatory compliance system. The checklist is configurable and illustrative, not a complete or current interpretation of India, EU MDR, or US FDA requirements. OCR can be imperfect. Use fictional or authorized sample data. All findings and release decisions require qualified human review.
"""

with st.expander("How this demo works", expanded=False):
    st.write("Upload an approved label and/or a revised label. LabelGuard AI extracts readable text, checks it against your configured checklist, compares revisions, and prepares a review log. The sample rules are intentionally transparent and editable.")

tab1, tab2, tab3 = st.tabs(["① Validate a label", "② Compare revisions", "③ Review report & impact"])

with tab1:
    st.subheader("Smart label validation")
    file_new = st.file_uploader("Upload label to review (PDF, PNG, JPG, TXT)", type=["pdf","png","jpg","jpeg","tif","tiff","bmp","txt","md","csv"], key="new")
    if file_new:
        new_text, extraction_method = extract_text(file_new)
        st.info(f"Input: {file_new.name} • Method: {extraction_method}")
        if new_text:
            with st.expander("Extracted text preview"):
                st.text(new_text[:8000])
        terms = required_terms.splitlines()
        findings = validate(new_text, terms, market)
        st.session_state["findings"] = findings
        st.session_state["new_text"] = new_text
        st.session_state["new_name"] = file_new.name
        df = pd.DataFrame(findings)
        c1,c2,c3 = st.columns(3)
        c1.metric("Findings", len(df))
        c2.metric("High severity", int((df["Severity"]=="High").sum()) if not df.empty else 0)
        c3.metric("Markets selected", len(market))
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download validation CSV", df.to_csv(index=False).encode("utf-8"), "labelguard_validation.csv", "text/csv")
    else:
        st.info("Upload a label file to start a validation review.")

with tab2:
    st.subheader("Approved vs revised artwork")
    left,right = st.columns(2)
    with left:
        old_file = st.file_uploader("Approved label", type=["pdf","png","jpg","jpeg","txt","md","csv"], key="old")
    with right:
        revised_file = st.file_uploader("Revised label", type=["pdf","png","jpg","jpeg","txt","md","csv"], key="rev")
    if old_file and revised_file:
        old_text, old_method = extract_text(old_file)
        rev_text, rev_method = extract_text(revised_file)
        if old_text.strip() and rev_text.strip():
            changes = compare_text(old_text, rev_text)
            st.session_state["changes"] = changes
            st.write(f"Approved: **{old_file.name}** ({old_method})  ·  Revised: **{revised_file.name}** ({rev_method})")
            if changes:
                st.dataframe(pd.DataFrame(changes), use_container_width=True, hide_index=True)
            else:
                st.success("No text differences detected. Visual differences may still exist.")
            old_low, rev_low = old_text.lower(), rev_text.lower()
            impact = []
            for term in ["steril", "warning", "udi", "expiry", "manufacturer", "language"]:
                if (term in old_low) != (term in rev_low) or (term in old_low and term in rev_low and old_low.count(term)!=rev_low.count(term)):
                    impact.append(term)
            st.markdown("**Illustrative change-impact prompts**")
            if impact:
                st.warning("Review other labels/markets potentially affected by: " + ", ".join(impact))
            else:
                st.info("No keyword-based impact prompts generated. Review product and market dependencies manually.")
        else:
            st.error("Could not extract readable text from both files. Try text-based PDFs or TXT files.")
    else:
        st.info("Upload both versions to see text-level changes and impact prompts.")

with tab3:
    st.subheader("Review report and traceability")
    findings = st.session_state.get("findings", [])
    changes = st.session_state.get("changes", [])
    if findings:
        st.markdown("**Current validation findings**")
        st.dataframe(pd.DataFrame(findings), use_container_width=True, hide_index=True)
    if changes:
        st.markdown("**Revision differences**")
        st.dataframe(pd.DataFrame(changes), use_container_width=True, hide_index=True)
    if findings or changes:
        review = {
            "product_category": product_type,
            "target_markets": market,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "prototype": "LabelGuard AI",
            "label_file": st.session_state.get("new_name"),
            "validation_findings": findings,
            "revision_changes": changes,
            "disclaimer": "Decision-support prototype only. Findings require qualified human review; not regulatory certification."
        }
        st.download_button("Download complete review report (JSON)", json.dumps(review, indent=2), "labelguard_review_report.json", "application/json")
        st.caption("Report includes findings and detected text changes for traceability. Add reviewer name, decision, and approval timestamp in a production implementation.")
    else:
        st.info("Run validation or compare two revisions to populate this report.")
    st.markdown("---")
    st.markdown("**Human review checklist**")
    reviewer = st.text_input("Reviewer / owner")
    decision = st.selectbox("Review status", ["Pending review", "Accepted for further review", "Changes required", "Escalated to regulatory/quality"])
    notes = st.text_area("Reviewer notes")
    if st.button("Record review decision"):
        st.session_state["review_decision"] = {"reviewer": reviewer, "decision": decision, "notes": notes, "timestamp": datetime.now().isoformat(timespec="seconds")}
        st.success("Review decision recorded for this session.")
    if "review_decision" in st.session_state:
        st.json(st.session_state["review_decision"])

st.markdown("---")
st.markdown('<p class="small-note">Prototype disclaimer: LabelGuard AI is a demonstration of document extraction, configurable checklist validation and text-level change review. It does not certify compliance, guarantee detection, or replace qualified regulatory/quality approval. Visual artwork comparison and market-specific rules are simplified or future extensions.</p>', unsafe_allow_html=True)
