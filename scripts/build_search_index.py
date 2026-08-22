"""Generate objects/search-index.json: static full-text token index."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from srdlib import BASE, dump_json, iter_object_files, iter_text_fragments, load_json

TOKEN_RE = re.compile(r"[a-z0-9']+")
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "it", "you",
    "your", "that", "this", "as", "for", "with", "by", "at", "be", "are",
    "its", "can", "if", "when", "each", "one", "has", "have",
}


def build(root: Path) -> None:
    documents = []
    postings = {}
    for collection, path in iter_object_files(root):
        record = load_json(path)
        fragments = list(iter_text_fragments(record))
        doc_index = len(documents)
        documents.append(
            {
                "id": record["@id"].removeprefix(BASE),
                "type": record.get("@type", ""),
                "name": record.get("name", ""),
                "excerpt": next(
                    (f["text"][:160] for f in fragments if f["path"].endswith(("rulesText", "description"))),
                    "",
                ),
            }
        )
        excerpts = {}
        for fragment in fragments:
            text = fragment["text"]
            for match in TOKEN_RE.finditer(text.lower()):
                token = match.group(0)
                if len(token) < 3 or token in STOPWORDS or token in excerpts:
                    continue
                start = max(0, match.start() - 55)
                end = min(len(text), match.end() + 105)
                excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
                excerpts[token] = excerpt
        for token, excerpt in excerpts.items():
            postings.setdefault(token, []).append(
                {"document": doc_index, "excerpt": excerpt}
            )
    index = {
        "base": BASE,
        "documents": documents,
        "tokens": {token: postings[token] for token in sorted(postings)},
    }
    dump_json(root / "objects" / "search-index.json", index)
    print(f"search-index: {len(documents)} documents, {len(postings)} tokens")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    build(Path(args.root).resolve())


if __name__ == "__main__":
    main()
