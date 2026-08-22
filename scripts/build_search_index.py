"""Generate objects/search-index.json: static full-text token index."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from srdlib import BASE, dump_json, iter_object_files, load_json

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
        text = " ".join(
            str(record.get(key, ""))
            for key in ("name", "rulesText", "description")
        )
        doc_index = len(documents)
        documents.append(
            {
                "id": record["@id"].removeprefix(BASE),
                "type": record.get("@type", ""),
                "name": record.get("name", ""),
                "excerpt": (record.get("rulesText") or "")[:160],
            }
        )
        seen = set()
        for token in TOKEN_RE.findall(text.lower()):
            if len(token) < 3 or token in STOPWORDS or token in seen:
                continue
            seen.add(token)
            postings.setdefault(token, []).append(doc_index)
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
