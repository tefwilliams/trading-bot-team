# References

Curated material the **Researcher** reads to ground its strategy proposals in proven
approaches (rather than relying only on the model's memory).

## What to put here

Drop in `.md`, `.txt`, or `.pdf` files — e.g.:

- A quant-strategies guide or cheat-sheet (momentum, mean-reversion, breakout, pairs, etc.).
- Papers or write-ups of strategies you want the team to consider.
- Your own notes on what has/hasn't worked.

`references.py::load_references()` concatenates everything here (except this README) and
feeds it into the Researcher's prompt. PDFs are text-extracted via `pypdf`.

## Notes

- **PDFs are git-ignored by default** (they're often large or copyrighted). Markdown/text
  notes are committed so the team's knowledge base is versioned. Override per-file with
  `git add -f` if you want to commit a specific PDF.
- Keep the total reasonably small — everything is loaded into context (cap:
  `MAX_REFERENCE_CHARS` in `references.py`). For a large corpus, switch to retrieval.
- Higher signal beats volume: a few good references produce better proposals than a pile
  of low-quality web content.
