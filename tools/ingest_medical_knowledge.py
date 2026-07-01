from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

import httpx
from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import Settings, get_settings  # noqa: E402


OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "source"


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def serialize_vector(values: list[float]) -> str:
    return json.dumps([round(float(value), 8) for value in values], separators=(",", ":"))


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

    for page_number, page_text in pages:
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
    payload: dict[str, object] = {
        "model": settings.openai_embedding_model,
        "input": text,
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
        timeout=60.0,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI embedding failed: {response.status_code} {response.text[:500]}")

    body = response.json()
    data = body.get("data")
    embedding = data[0].get("embedding") if isinstance(data, list) and data else None
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("OpenAI embedding response did not include an embedding vector.")
    return [float(value) for value in embedding]


def ingest_pdf(
    client: httpx.Client,
    settings: Settings,
    path: Path,
    *,
    chunk_chars: int,
    limit_chunks: int | None,
    dry_run: bool,
) -> int:
    source_key = slugify(path.stem)
    chunks = list(iter_chunks(iter_pdf_pages(path), chunk_chars=chunk_chars))
    if limit_chunks is not None:
        chunks = chunks[:limit_chunks]

    print(f"{path.name}: {len(chunks)} chunk(s)")
    if dry_run:
        return len(chunks)

    rpc(
        client,
        settings,
        "upsert_medical_source",
        {
            "p_source_key": source_key,
            "p_title": path.stem.replace("_", " "),
            "p_source_path": path.name,
            "p_metadata": {
                "file_name": path.name,
                "file_size_bytes": path.stat().st_size,
                "ingestion_tool": "tools/ingest_medical_knowledge.py",
            },
        },
    )

    for chunk in chunks:
        embedding = embed_text(client, settings, str(chunk["chunk_text"]))
        rpc(
            client,
            settings,
            "upsert_medical_knowledge_chunk",
            {
                "p_source_key": source_key,
                "p_chunk_index": chunk["chunk_index"],
                "p_page_start": chunk["page_start"],
                "p_page_end": chunk["page_end"],
                "p_section_title": None,
                "p_chunk_text": chunk["chunk_text"],
                "p_token_estimate": chunk["token_estimate"],
                "p_embedding": serialize_vector(embedding),
                "p_metadata": {"file_name": path.name},
            },
        )
        print(f"  upserted chunk {chunk['chunk_index']} pages {chunk['page_start']}-{chunk['page_end']}")

    return len(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest private medical PDFs into Supabase via backend-only RPCs.")
    parser.add_argument("--source-dir", required=True, type=Path, help="Directory containing source PDFs.")
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

    if not args.source_dir.exists():
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

    pdfs = sorted(args.source_dir.glob("*.pdf"))
    if args.limit_files is not None:
        pdfs = pdfs[: args.limit_files]
    if not pdfs:
        raise SystemExit("No PDFs found.")

    total_chunks = 0
    with httpx.Client() as client:
        for pdf in pdfs:
            total_chunks += ingest_pdf(
                client,
                settings,
                pdf,
                chunk_chars=args.chunk_chars,
                limit_chunks=args.limit_chunks,
                dry_run=args.dry_run,
            )

    print(f"Done. Processed {len(pdfs)} file(s), {total_chunks} chunk(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
