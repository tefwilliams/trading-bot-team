"""Loads curated reference material for grounding the Researcher.

Drop quant-strategy guides, papers, or notes into the `references/` directory as
`.md`, `.txt`, or `.pdf`. `load_references()` returns their text as a single block to
inject into the Researcher's prompt, so proposals are grounded in proven approaches
rather than the model's parametric memory alone.

For a handful of documents this simply concatenates everything (it fits comfortably in
the model's context). If the corpus grows large, switch to chunking + embedding retrieval
rather than stuffing it all in.
"""

import logging
import os

logger = logging.getLogger(__name__)

REFERENCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "references")

# Total budget across all reference files, to keep the prompt from blowing up.
MAX_REFERENCE_CHARS = 100_000

# Files that are instructions for humans, not reference material to feed the model.
_SKIP_FILES = {"readme.md", "readme.txt"}


def _extract_pdf_text(path: str) -> str:
    """Extract text from a PDF. Requires `pypdf` (only imported when a PDF is present)."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_references() -> str:
    """Return all reference material under references/ as one text block ('' if none)."""
    if not os.path.isdir(REFERENCES_DIR):
        return ""

    parts: list[str] = []
    for name in sorted(os.listdir(REFERENCES_DIR)):
        path = os.path.join(REFERENCES_DIR, name)
        if not os.path.isfile(path) or name.lower() in _SKIP_FILES:
            continue

        ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
        try:
            if ext in ("md", "txt"):
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif ext == "pdf":
                text = _extract_pdf_text(path)
            else:
                continue  # unsupported type — skip quietly
        except Exception as e:
            # A bad/unreadable file (or missing pypdf) shouldn't break research.
            logger.warning(f"Could not read reference '{name}': {e}")
            continue

        if text.strip():
            parts.append(f"--- Reference: {name} ---\n{text.strip()}")

    blob = "\n\n".join(parts)
    if len(blob) > MAX_REFERENCE_CHARS:
        logger.warning(
            f"Reference material is {len(blob)} chars; truncating to {MAX_REFERENCE_CHARS}. "
            "Consider retrieval instead of loading everything."
        )
        blob = blob[:MAX_REFERENCE_CHARS]
    return blob
