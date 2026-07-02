from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import time
from pathlib import Path
from typing import Iterable

import httpx
from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import Settings, get_settings  # noqa: E402


OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
EMBED_BATCH_SIZE = 80

_SECTION_RE = re.compile(
    r"^(?:"
    r"[A-Z][A-Z\s,&\-/]{4,80}$"
    r"|(?:CHAPTER|SECTION)\s+\d+[:\s]"
    r"|(?:TABLE|FIGURE)\s+\d+"
    r")",
    re.MULTILINE,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def serialize_vector(values: list[float]) -> str:
    return json.dumps([round(float(value), 8) for value in values], separators=(",", ":"))


def detect_section_title(text: str) -> str | None:
    for line in text.split("\n")[:5]:
        line = line.strip()
        if not line or len(line) < 5 or len(line) > 120:
            continue
        if _SECTION_RE.match(line):
            return line
    return None


def iter_pdf_pages(path: Path) -> Iterable[tuple[int, str]]:
    reader = PdfReader(str(path))
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if text:
            yield index, text


def iter_chunks(
    pages: Iterable[tuple[int, str]],
    *,
    chunk_chars: int,
) -> Iterable[dict[str, object]]:
    buffer: list[str] = []
    page_start: int | None = None
    page_end: int | None = None
    chunk_index = 0
    current_section: str | None = None

    for page_number, page_text in pages:
        section = detect_section_title(page_text)
        if section:
            current_section = section

        paragraphs = [part.strip() for part in re.split(r"\n{2,}", page_text) if part.strip()]
        if not paragraphs:
            paragraphs = [page_text]

        for paragraph in paragraphs:
            next_size = sum(len(part) for part in buffer) + len(paragraph)
            if buffer and next_size > chunk_chars:
                text = "\n\n".join(buffer)
                yield {
                    "chunk_index": chunk_index,
                    "page_start": page_start,
                    "page_end": page_end,
                    "section_title": current_section,
                    "chunk_text": text,
                    "token_estimate": estimate_tokens(text),
                }
                chunk_index += 1
                buffer = []
                page_start = None
                page_end = None

            if page_start is None:
                page_start = page_number
            page_end = page_number
            buffer.append(paragraph)

    if buffer:
        text = "\n\n".join(buffer)
        yield {
            "chunk_index": chunk_index,
            "page_start": page_start,
            "page_end": page_end,
            "section_title": current_section,
            "chunk_text": text,
            "token_estimate": estimate_tokens(text),
        }


def require_settings(settings: Settings) -> None:
    missing = []
    if not settings.supabase_url:
        missing.append("SUPABASE_URL")
    if not settings.supabase_service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if not settings.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Missing required backend/.env values: {joined}")


def rpc(
    client: httpx.Client,
    settings: Settings,
    function_name: str,
    payload: dict[str, object],
) -> object:
    response = client.post(
        settings.supabase_url.rstrip("/") + f"/rest/v1/rpc/{function_name}",
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60.0,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase RPC {function_name} failed: {response.status_code} {response.text[:500]}")
    try:
        return response.json()
    except ValueError:
        return None


def embed_text(client: httpx.Client, settings: Settings, text: str) -> list[float]:
    return embed_batch(client, settings, [text])[0]


def embed_batch(
    client: httpx.Client,
    settings: Settings,
    texts: list[str],
) -> list[list[float]]:
    payload: dict[str, object] = {
        "model": settings.openai_embedding_model,
        "input": texts,
    }
    if settings.openai_embedding_dimensions > 0:
        payload["dimensions"] = settings.openai_embedding_dimensions

    response = client.post(
        OPENAI_EMBEDDINGS_URL,
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120.0,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI embedding failed: {response.status_code} {response.text[:500]}")

    body = response.json()
    data = body.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise RuntimeError(f"OpenAI returned {len(data) if data else 0} embeddings for {len(texts)} inputs.")
    data.sort(key=lambda d: d.get("index", 0))
    return [[float(v) for v in item["embedding"]] for item in data]


def ingest_pdf(
    client: httpx.Client,
    settings: Settings,
    path: Path,
    *,
    chunk_chars: int,
    limit_chunks: int | None,
    dry_run: bool,
    source_key: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
) -> int:
    source_key = source_key or slugify(path.stem)
    title = title or path.stem.replace("_", " ")
    chunks = list(iter_chunks(iter_pdf_pages(path), chunk_chars=chunk_chars))
    if limit_chunks is not None:
        chunks = chunks[:limit_chunks]

    print(f"  {path.name}: {len(chunks)} chunk(s), key={source_key}")
    if dry_run:
        return len(chunks)

    source_meta: dict[str, object] = {
        "file_name": path.name,
        "file_size_bytes": path.stat().st_size,
        "ingestion_tool": "tools/ingest_medical_knowledge.py",
    }
    if tags:
        source_meta["tags"] = tags

    rpc(client, settings, "upsert_medical_source", {
        "p_source_key": source_key,
        "p_title": title,
        "p_source_path": path.name,
        "p_metadata": source_meta,
    })

    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + EMBED_BATCH_SIZE]
        texts = [str(c["chunk_text"]) for c in batch]
        t0 = time.time()
        embeddings = embed_batch(client, settings, texts)
        dt = time.time() - t0
        print(f"    embedded {len(batch)} chunks in {dt:.1f}s (batch {batch_start // EMBED_BATCH_SIZE + 1})")

        for chunk, embedding in zip(batch, embeddings):
            rpc(client, settings, "upsert_medical_knowledge_chunk", {
                "p_source_key": source_key,
                "p_chunk_index": chunk["chunk_index"],
                "p_page_start": chunk["page_start"],
                "p_page_end": chunk["page_end"],
                "p_section_title": chunk.get("section_title"),
                "p_chunk_text": chunk["chunk_text"],
                "p_token_estimate": chunk["token_estimate"],
                "p_embedding": serialize_vector(embedding),
                "p_metadata": {"file_name": path.name},
            })
        print(f"    upserted chunks {batch_start}-{batch_start + len(batch) - 1}")

    return len(chunks)


def load_manifest(manifest_path: Path) -> list[dict[str, object]]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Manifest must be a JSON array.")
    for entry in data:
        for key in ("file", "source_key", "title", "tags"):
            if key not in entry:
                raise SystemExit(f"Manifest entry missing required key '{key}': {entry}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest private medical PDFs into Supabase via backend-only RPCs.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-dir", type=Path, help="Directory containing source PDFs.")
    source.add_argument("--source-file", type=Path, help="One PDF file to ingest.")
    source.add_argument("--manifest", type=Path, help="JSON manifest with source_key, title, tags per PDF.")
    parser.add_argument("--manifest-dir", type=Path, default=None, help="PDF directory (required with --manifest).")
    parser.add_argument("--include", default=None, help="Optional filename glob when using --source-dir, e.g. '*Endocrine*'.")
    parser.add_argument("--limit-files", type=int, default=None, help="Optional number of PDFs to process.")
    parser.add_argument("--limit-chunks", type=int, default=None, help="Optional chunks per PDF for smoke tests.")
    parser.add_argument("--chunk-chars", type=int, default=3500, help="Approximate maximum characters per chunk.")
    parser.add_argument("--dry-run", action="store_true", help="Extract and count chunks without uploading text.")
    parser.add_argument(
        "--confirm-send-to-openai",
        action="store_true",
        help="Required for non-dry-run ingestion because chunk text is sent to OpenAI for embeddings.",
    )
    args = parser.parse_args()

    if args.manifest:
        if not args.manifest.exists():
            raise SystemExit(f"Manifest not found: {args.manifest}")
        if not args.manifest_dir:
            raise SystemExit("--manifest-dir is required when using --manifest.")
        if not args.manifest_dir.exists():
            raise SystemExit(f"Manifest directory not found: {args.manifest_dir}")
    if args.source_file and not args.source_file.exists():
        raise SystemExit(f"Source file not found: {args.source_file}")
    if args.source_file and args.source_file.suffix.lower() != ".pdf":
        raise SystemExit("--source-file must point to a PDF.")
    if args.source_dir and not args.source_dir.exists():
        raise SystemExit(f"Source directory not found: {args.source_dir}")
    if args.chunk_chars < 1000:
        raise SystemExit("--chunk-chars must be at least 1000.")
    if not args.dry_run and not args.confirm_send_to_openai:
        raise SystemExit(
            "Refusing to upload private source text. Re-run with --confirm-send-to-openai "
            "after confirming that embedding these materials through OpenAI is acceptable."
        )

    settings = get_settings()
    if not args.dry_run:
        require_settings(settings)

    if args.manifest:
        manifest = load_manifest(args.manifest)
        if args.limit_files is not None:
            manifest = manifest[: args.limit_files]
        print(f"Manifest: {len(manifest)} sources from {args.manifest.name}")
        total_chunks = 0
        t_start = time.time()
        with httpx.Client() as client:
            for i, entry in enumerate(manifest, 1):
                pdf_path = args.manifest_dir / entry["file"]
                if not pdf_path.exists():
                    print(f"  [{i}/{len(manifest)}] SKIP (not found): {entry['file']}")
                    continue
                print(f"  [{i}/{len(manifest)}] {entry['title']}")
                total_chunks += ingest_pdf(
                    client, settings, pdf_path,
                    chunk_chars=args.chunk_chars,
                    limit_chunks=args.limit_chunks,
                    dry_run=args.dry_run,
                    source_key=entry["source_key"],
                    title=entry["title"],
                    tags=entry["tags"],
                )
        elapsed = time.time() - t_start
        print(f"\nDone. {len(manifest)} sources, {total_chunks} chunks, {elapsed:.0f}s elapsed.")
        return 0

    if args.source_file:
        pdfs = [args.source_file]
    else:
        pdfs = sorted(args.source_dir.glob("*.pdf"))
        if args.include:
            pdfs = [pdf for pdf in pdfs if fnmatch.fnmatch(pdf.name, args.include)]
    if args.limit_files is not None:
        pdfs = pdfs[: args.limit_files]
    if not pdfs:
        raise SystemExit("No PDFs found.")

    total_chunks = 0
    with httpx.Client() as client:
        for pdf in pdfs:
            total_chunks += ingest_pdf(
                client, settings, pdf,
                chunk_chars=args.chunk_chars,
                limit_chunks=args.limit_chunks,
                dry_run=args.dry_run,
            )

    print(f"Done. Processed {len(pdfs)} file(s), {total_chunks} chunk(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
