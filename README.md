# LabelGuard AI Demo Prototype

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run `pip install -r requirements.txt`.
4. Run `streamlit run app.py`.

## Features
- Upload label PDF, image, or text file.
- Extract text from text-based PDFs; image OCR is optional and depends on local OCR dependencies.
- Run a configurable checklist and basic UDI/LOT/REF pattern checks.
- Compare approved and revised label text.
- Generate downloadable CSV and JSON review reports.
- Show illustrative change-impact prompts and a session-level reviewer decision.

## Demo safety note
This is a proof-of-concept, not a certified regulatory compliance system. Its checklist is illustrative and is not a complete or current interpretation of India, EU MDR, or US FDA requirements. OCR can be imperfect. Use fictional or authorized sample data. All findings and release decisions require qualified human review.
