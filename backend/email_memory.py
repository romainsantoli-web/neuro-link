"""
Neuro-Link Email Memory — persistent memory for the email AI agent.

Uses SentenceTransformers (all-MiniLM-L6-v2) for embeddings and FAISS for
semantic search, following the Memory-os-ai pattern by RoaminS.

Storage:
    backend/data/email_memory.jsonl      — all email records (JSONL)
    backend/data/email_embeddings.faiss  — FAISS index
    backend/data/email_meta.json         — metadata mapping index->record id

Every email sent, received, drafted, or campaign step is stored here.
Before each AI action, the full relevant context is loaded via semantic search.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import faiss
import numpy as np

DATA_DIR = Path(__file__).resolve().parent / "data"
MEMORY_FILE = DATA_DIR / "email_memory.jsonl"
FAISS_INDEX_FILE = DATA_DIR / "email_embeddings.faiss"
META_FILE = DATA_DIR / "email_meta.json"

# Lazy-loaded globals
_model = None
_index = None
_meta: list[dict[str, Any]] = []


def _get_model():
    """Lazy-load SentenceTransformer model (all-MiniLM-L6-v2)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        model_path = DATA_DIR / "models" / "all-MiniLM-L6-v2"
        if model_path.exists():
            _model = SentenceTransformer(str(model_path))
        else:
            _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embed(texts: list[str]) -> np.ndarray:
    """Embed a list of texts into vectors."""
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def _load_index():
    """Load FAISS index + metadata from disk."""
    global _index, _meta
    if FAISS_INDEX_FILE.exists() and META_FILE.exists():
        _index = faiss.read_index(str(FAISS_INDEX_FILE))
        _meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    else:
        _index = faiss.IndexFlatIP(384)  # 384-dim for MiniLM-L6-v2
        _meta = []


def _save_index():
    """Persist FAISS index + metadata to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if _index is not None:
        faiss.write_index(_index, str(FAISS_INDEX_FILE))
    META_FILE.write_text(json.dumps(_meta, ensure_ascii=False), encoding="utf-8")


def _record_to_text(record: dict[str, Any]) -> str:
    """Convert a memory record to a searchable text representation."""
    parts = []
    if record.get("type"):
        parts.append(f"[{record['type'].upper()}]")
    if record.get("subject"):
        parts.append(f"Subject: {record['subject']}")
    if record.get("to"):
        to = record["to"] if isinstance(record["to"], str) else ", ".join(record["to"])
        parts.append(f"To: {to}")
    if record.get("from_addr"):
        parts.append(f"From: {record['from_addr']}")
    if record.get("target_type"):
        parts.append(f"Target: {record['target_type']}")
    if record.get("target_name"):
        parts.append(f"Cible: {record['target_name']}")
    if record.get("campaign_id"):
        parts.append(f"Campaign: {record['campaign_id']}")
    if record.get("body"):
        body = record["body"][:500]
        parts.append(body)
    if record.get("summary"):
        parts.append(record["summary"])
    # Research records — index the full summary for semantic search
    if record.get("research_summary"):
        parts.append(record["research_summary"][:2000])
    return " | ".join(parts)


class EmailMemory:
    """Persistent email memory with semantic search (FAISS + SentenceTransformers)."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _load_index()

    def ingest(self, record: dict[str, Any]) -> str:
        """Store a new email record in memory + update FAISS index.

        Returns the record ID.
        """
        global _index, _meta

        if _index is None:
            _load_index()

        record_id = record.get("id") or f"em_{uuid.uuid4().hex[:12]}"
        record["id"] = record_id
        record["timestamp"] = record.get("timestamp") or datetime.now(timezone.utc).isoformat()

        # Append to JSONL
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Embed and add to FAISS
        text = _record_to_text(record)
        vec = _embed([text])
        _index.add(vec.astype(np.float32))
        _meta.append({"id": record_id, "idx": _index.ntotal - 1})
        _save_index()

        return record_id

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Semantic search over email memory. Returns most relevant records."""
        if _index is None or _index.ntotal == 0:
            return []

        vec = _embed([query])
        k = min(limit, _index.ntotal)
        scores, indices = _index.search(vec.astype(np.float32), k)

        # Map FAISS indices to record IDs
        result_ids = set()
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(_meta):
                result_ids.add(_meta[idx]["id"])

        # Load matching records from JSONL
        records = self._load_records_by_ids(result_ids)
        return records[:limit]

    def get_thread(self, thread_id: str) -> list[dict[str, Any]]:
        """Get all records in a conversation thread, ordered by timestamp."""
        all_records = self.get_all()
        thread = [r for r in all_records if r.get("thread_id") == thread_id]
        thread.sort(key=lambda r: r.get("timestamp", ""))
        return thread

    def get_by_contact(self, contact: str) -> list[dict[str, Any]]:
        """Get all records involving a specific contact (to or from)."""
        all_records = self.get_all()
        results = []
        contact_lower = contact.lower()
        for r in all_records:
            to = r.get("to", "")
            if isinstance(to, list):
                to = " ".join(to)
            from_addr = r.get("from_addr", "")
            if contact_lower in to.lower() or contact_lower in from_addr.lower():
                results.append(r)
        results.sort(key=lambda r: r.get("timestamp", ""))
        return results

    def get_by_campaign(self, campaign_id: str) -> list[dict[str, Any]]:
        """Get all records for a specific campaign."""
        all_records = self.get_all()
        return [r for r in all_records if r.get("campaign_id") == campaign_id]

    def get_by_target_name(self, target_name: str) -> list[dict[str, Any]]:
        """Get all records mentioning a specific target (by target_name field or subject/body)."""
        all_records = self.get_all()
        target_lower = target_name.lower()
        results = []
        for r in all_records:
            tn = (r.get("target_name") or "").lower()
            subj = (r.get("subject") or "").lower()
            if target_lower in tn or target_lower in subj:
                results.append(r)
        results.sort(key=lambda r: r.get("timestamp", ""))
        return results

    def get_research_for_target(self, target_name: str) -> list[dict[str, Any]]:
        """Get all research records for a specific target.

        Returns records of type='research' that match the target_name.
        Useful for recalling past web research before drafting prospection emails.
        """
        all_records = self.get_all()
        target_lower = target_name.lower()
        results = []
        for r in all_records:
            if r.get("type") != "research":
                continue
            tn = (r.get("target_name") or "").lower()
            subj = (r.get("subject") or "").lower()
            if target_lower in tn or target_lower in subj:
                results.append(r)
        results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return results

    def get_all_extracted_emails(self, target_name: str = "") -> list[str]:
        """Get all extracted email addresses from research records.

        If target_name is provided, only return emails from research on that target.
        """
        records = self.get_research_for_target(target_name) if target_name else [
            r for r in self.get_all() if r.get("type") == "research"
        ]
        emails: list[str] = []
        seen: set[str] = set()
        for r in records:
            for em in r.get("extracted_emails", []):
                if em.lower() not in seen:
                    seen.add(em.lower())
                    emails.append(em)
        return emails

    def get_all(self) -> list[dict[str, Any]]:
        """Load all records from JSONL."""
        if not MEMORY_FILE.exists():
            return []
        records = []
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records

    def get_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get the N most recent records."""
        all_records = self.get_all()
        all_records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return all_records[:limit]

    def load_full_context(self, query: str = "", limit: int = 15) -> str:
        """Build a comprehensive context string for the AI agent.

        Combines:
        - Semantic search results (if query provided)
        - Last N recent records
        - Summary statistics
        """
        parts = []

        # Stats
        all_records = self.get_all()
        sent = sum(1 for r in all_records if r.get("type") == "sent")
        received = sum(1 for r in all_records if r.get("type") == "received")
        drafts = sum(1 for r in all_records if r.get("type") == "draft")
        research = sum(1 for r in all_records if r.get("type") == "research")
        campaigns = len(set(r.get("campaign_id", "") for r in all_records if r.get("campaign_id")))

        parts.append(f"=== EMAIL MEMORY: {len(all_records)} records "
                     f"({sent} sent, {received} received, {drafts} drafts, "
                     f"{research} research, {campaigns} campaigns) ===")

        # Semantic search results
        if query:
            search_results = self.search(query, limit=limit)
            if search_results:
                parts.append("\n--- RELEVANT RECORDS (semantic search) ---")
                for r in search_results:
                    parts.append(self._format_record(r))

        # Recent records
        recent = self.get_recent(limit=10)
        if recent:
            parts.append("\n--- RECENT ACTIVITY ---")
            for r in recent:
                parts.append(self._format_record(r))

        return "\n".join(parts)

    def rebuild_index(self):
        """Rebuild the entire FAISS index from JSONL records."""
        global _index, _meta
        all_records = self.get_all()

        _index = faiss.IndexFlatIP(384)
        _meta = []

        if all_records:
            texts = [_record_to_text(r) for r in all_records]
            vecs = _embed(texts)
            _index.add(vecs.astype(np.float32))
            _meta = [{"id": r["id"], "idx": i} for i, r in enumerate(all_records)]

        _save_index()
        return len(all_records)

    def _load_records_by_ids(self, ids: set[str]) -> list[dict[str, Any]]:
        """Load specific records by their IDs from JSONL."""
        if not MEMORY_FILE.exists():
            return []
        records = []
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        if r.get("id") in ids:
                            records.append(r)
                    except json.JSONDecodeError:
                        pass
        return records

    @staticmethod
    def _format_record(r: dict[str, Any]) -> str:
        """Format a single record for context display."""
        ts = r.get("timestamp", "?")[:16]
        rtype = r.get("type", "?").upper()
        to = r.get("to", "")
        if isinstance(to, list):
            to = ", ".join(to)
        from_addr = r.get("from_addr", "")
        subject = r.get("subject", "")
        body = r.get("body", "")[:200]
        target = r.get("target_type", "")
        target_name = r.get("target_name", "")
        campaign = r.get("campaign_id", "")

        line = f"[{ts}] {rtype}"
        if from_addr:
            line += f" from={from_addr}"
        if to:
            line += f" to={to}"
        if subject:
            line += f" subj=\"{subject}\""
        if target:
            line += f" target={target}"
        if target_name:
            line += f" cible={target_name}"
        if campaign:
            line += f" campaign={campaign}"
        # Research records — show summary excerpt
        if rtype == "RESEARCH":
            summary = r.get("research_summary", "")[:400]
            n_results = r.get("search_results_count", 0)
            n_pages = r.get("scraped_pages_count", 0)
            line += f" [{n_results} résultats, {n_pages} pages]"
            if summary:
                line += f"\n  {summary}"
        elif body:
            line += f"\n  {body}"
        return line
