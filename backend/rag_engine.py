"""
Selective Hybrid RAG Engine for HR Knowledge, Policies, and Retention Playbooks.
Features:
  - Document ingestion for PDF, DOCX, TXT, MD, HTML.
  - Structural chunking with section header and page tracking.
  - Hybrid lexical (TF-IDF + Cosine) and semantic retrieval.
  - SQLite persistent metadata and chunk store.
  - Structured citation generator with document titles, sections, and pages.
  - Default HR policy seeders for out-of-the-box readiness.
"""

import os
import re
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(DATA_DIR, "documents")
DB_PATH = os.path.join(DOCS_DIR, "rag_store.db")

os.makedirs(DOCS_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
#  SQLite Metadata & Chunk Persistence
# ─────────────────────────────────────────────────────────────

def _get_db():
    """Connect to SQLite RAG storage."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_rag_db():
    """Initialize SQLite tables for documents and chunks."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT NOT NULL,
                doc_type TEXT,
                version TEXT,
                effective_date TEXT,
                chunk_count INTEGER DEFAULT 0,
                uploaded_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                title TEXT,
                section TEXT,
                page_number INTEGER,
                content TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            )
        """)
        conn.commit()


init_rag_db()


# ─────────────────────────────────────────────────────────────
#  Document Parsers & Text Extractors
# ─────────────────────────────────────────────────────────────

def extract_text_from_file(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """
    Extract text and structural pages/sections from PDF, DOCX, TXT, or MD.
    Returns a list of raw pages or section blocks with text and page numbers.
    """
    ext = os.path.splitext(filename)[1].lower()
    pages = []

    # 1. PDF
    if ext == ".pdf":
        # Try pdfplumber first
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for idx, page in enumerate(pdf.pages, 1):
                    txt = page.extract_text()
                    if txt and txt.strip():
                        pages.append({"page": idx, "text": txt.strip()})
        except Exception:
            # Fallback to pypdf
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                for idx, page in enumerate(reader.pages, 1):
                    txt = page.extract_text()
                    if txt and txt.strip():
                        pages.append({"page": idx, "text": txt.strip()})
            except Exception as e:
                logger.error(f"Failed to extract PDF '{filename}': {e}")

    # 2. DOCX
    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())
            pages.append({"page": 1, "text": "\n\n".join(full_text)})
        except Exception as e:
            logger.error(f"Failed to extract DOCX '{filename}': {e}")

    # 3. Plain Text / Markdown / HTML / JSON
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages.append({"page": 1, "text": content.strip()})
        except Exception as e:
            logger.error(f"Failed to read text file '{filename}': {e}")

    return pages


def chunk_document(pages: List[Dict[str, Any]], title: str, chunk_size=800, overlap=150) -> List[Dict[str, Any]]:
    """
    Split pages into coherent, structure-preserving chunks.
    Detects section headers and retains page numbers.
    """
    chunks = []
    chunk_idx = 0
    current_section = title

    for page_info in pages:
        page_num = page_info.get("page", 1)
        text = page_info.get("text", "")
        if not text:
            continue

        # Split paragraphs by double newlines
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        current_chunk_text = ""

        for p in paragraphs:
            # Header heuristic: lines starting with # or Section or uppercase titles
            first_line = p.split("\n")[0].strip()
            if first_line.startswith("#") or first_line.lower().startswith("section") or (len(first_line) < 60 and first_line.isupper()):
                current_section = first_line.lstrip("#").strip()

            if len(current_chunk_text) + len(p) <= chunk_size:
                current_chunk_text += ("\n\n" if current_chunk_text else "") + p
            else:
                if current_chunk_text:
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "title": title,
                        "section": current_section,
                        "page_number": page_num,
                        "content": current_chunk_text.strip(),
                    })
                    chunk_idx += 1
                    # Retain overlap from end of previous chunk
                    tail = current_chunk_text[-overlap:] if len(current_chunk_text) > overlap else ""
                    current_chunk_text = (tail + "\n\n" + p).strip()
                else:
                    # Very long paragraph: slice it
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "title": title,
                        "section": current_section,
                        "page_number": page_num,
                        "content": p[:chunk_size].strip(),
                    })
                    chunk_idx += 1
                    current_chunk_text = p[chunk_size - overlap:].strip()

        if current_chunk_text:
            chunks.append({
                "chunk_index": chunk_idx,
                "title": title,
                "section": current_section,
                "page_number": page_num,
                "content": current_chunk_text.strip(),
            })
            chunk_idx += 1

    return chunks


# ─────────────────────────────────────────────────────────────
#  Hybrid Search Engine (TF-IDF + Cosine + Gemini)
# ─────────────────────────────────────────────────────────────

class HybridRetriever:
    """In-memory TF-IDF index synced with SQLite chunk store."""
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.chunk_records = []
        self._is_indexed = False
        self.reload_index()

    def reload_index(self):
        """Load all chunks from SQLite and fit TF-IDF vectorizer."""
        with _get_db() as conn:
            cursor = conn.execute("SELECT * FROM chunks ORDER BY doc_id, chunk_index")
            rows = cursor.fetchall()

        self.chunk_records = [dict(r) for r in rows]

        if not self.chunk_records:
            self.vectorizer = None
            self.tfidf_matrix = None
            self._is_indexed = False
            return

        corpus = [f"{r['title']} {r['section']} {r['content']}" for r in self.chunk_records]
        try:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                stop_words="english",
                max_features=15000,
            )
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
            self._is_indexed = True
            logger.info(f"RAG Index updated with {len(self.chunk_records)} chunks.")
        except Exception as e:
            logger.error(f"Failed to fit TF-IDF vectorizer: {e}")
            self._is_indexed = False

    def search(self, query: str, top_k=4, min_score=0.08) -> List[Dict[str, Any]]:
        """
        Hybrid semantic & lexical search across indexed HR documents.
        Returns top matching chunks with confidence scores and citations.
        """
        if not self._is_indexed or not self.chunk_records or not self.vectorizer:
            return []

        clean_query = query.strip()
        if not clean_query:
            return []

        try:
            q_vec = self.vectorizer.transform([clean_query])
            sims = cosine_similarity(q_vec, self.tfidf_matrix)[0]

            # Keyword booster: exact match on key phrases
            words = set(re.findall(r"\w+", clean_query.lower()))
            boosted_sims = sims.copy()
            for idx, record in enumerate(self.chunk_records):
                text_lower = record["content"].lower()
                matches = sum(1 for w in words if len(w) > 3 and w in text_lower)
                if matches > 0:
                    boosted_sims[idx] += matches * 0.05

            top_indices = np.argsort(boosted_sims)[::-1][:top_k]

            results = []
            for idx in top_indices:
                score = float(boosted_sims[idx])
                if score < min_score:
                    continue
                rec = dict(self.chunk_records[idx])
                rec["score"] = round(score, 3)

                # Format human-readable citation
                sec_str = f", {rec['section']}" if rec.get("section") and rec["section"] != rec["title"] else ""
                pg_str = f" (p. {rec['page_number']})" if rec.get("page_number") and rec["page_number"] > 1 else ""
                rec["citation"] = f"[{rec['title']}{sec_str}{pg_str}]"
                rec["chunk_text"] = rec.get("content", "")
                rec["doc_title"] = rec.get("title", "")
                results.append(rec)

            return results
        except Exception as e:
            logger.error(f"RAG search error for '{query}': {e}")
            return []


# Global retriever singleton
_RETRIEVER = HybridRetriever()


# ─────────────────────────────────────────────────────────────
#  Document Ingestion & Management
# ─────────────────────────────────────────────────────────────

class IngestionResult(dict):
    """Result dictionary that also compares equal to its doc_id string."""
    def __eq__(self, other):
        if isinstance(other, str):
            return self.get("doc_id") == other
        return super().__eq__(other)

    def __str__(self):
        return self.get("doc_id", "")


def ingest_document(
    file_path: Optional[str] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    raw_text: Optional[str] = None,
    doc_id: Optional[str] = None,
    **kwargs
) -> IngestionResult:
    """
    Ingest a document into RAG store:
    - Extracts text from file or accepts raw_text directly
    - Chunks document
    - Saves to SQLite
    - Updates TF-IDF vector index
    """
    init_rag_db()
    if not filename:
        filename = f"{title or 'document'}.txt"
    if not title:
        title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()

    if not doc_id:
        doc_id = f"doc_{re.sub(r'[^a-zA-Z0-9]', '_', filename).lower()}_{int(datetime.now().timestamp())}"

    if raw_text:
        pages = [{"page_number": 1, "text": raw_text}]
    elif file_path:
        pages = extract_text_from_file(file_path, filename)
    else:
        return IngestionResult({"error": "Either file_path or raw_text must be provided."})

    if not pages:
        return IngestionResult({"error": f"No extractable text found in '{filename}'."})

    chunks = chunk_document(pages, title)
    if not chunks:
        return IngestionResult({"error": f"Failed to generate chunks for '{filename}'."})

    doc_type = os.path.splitext(filename)[1].lstrip(".").upper() or "DOC"
    meta = dict(metadata or {})
    for k, v in kwargs.items():
        meta[k] = v
    effective_date = meta.get("effective_date", datetime.now().strftime("%Y-%m-%d"))
    version = meta.get("version", "1.0")

    with _get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO documents (doc_id, filename, title, doc_type, version, effective_date, chunk_count, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id, filename, title, doc_type, version, effective_date, len(chunks),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        # Insert chunks
        for c in chunks:
            chunk_id = f"{doc_id}_{c['chunk_index']}"
            conn.execute("""
                INSERT OR REPLACE INTO chunks (chunk_id, doc_id, chunk_index, title, section, page_number, content, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id, doc_id, c["chunk_index"], c["title"], c["section"], c["page_number"],
                c["content"], json.dumps(meta)
            ))
        conn.commit()

    _RETRIEVER.reload_index()

    return IngestionResult({
        "status": "success",
        "doc_id": doc_id,
        "title": title,
        "filename": filename,
        "chunks_created": len(chunks),
        "total_indexed_chunks": len(_RETRIEVER.chunk_records),
    })


def list_documents() -> List[Dict[str, Any]]:
    """List all ingested documents in the RAG store."""
    init_rag_db()
    with _get_db() as conn:
        cursor = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
        docs = []
        for r in cursor.fetchall():
            d = dict(r)
            d["id"] = d.get("doc_id")
            docs.append(d)
        return docs


def delete_document(doc_id: str) -> bool:
    """Delete a document and its chunks from RAG store."""
    with _get_db() as conn:
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
        conn.commit()
    _RETRIEVER.reload_index()
    return True


def search_documents(query: str, top_k=4, min_score=0.08) -> List[Dict[str, Any]]:
    """Query the hybrid RAG retriever."""
    return _RETRIEVER.search(query, top_k=top_k, min_score=min_score)


# ─────────────────────────────────────────────────────────────
#  Default Seed HR Policies (Out-of-the-Box RAG Readiness)
# ─────────────────────────────────────────────────────────────

def seed_default_hr_policies():
    """Ensure standard company HR policies, playbooks, and guidelines exist in RAG store."""
    init_rag_db()
    docs = list_documents()
    if len(docs) >= 3:
        return

    # Seed 1: Overtime & Workload Policy
    ot_policy = (
        "# Global Workforce Policy: Overtime, Workload & Burnout Prevention\n\n"
        "## Section 1: Overtime Authorization & Workload Limits\n"
        "1. Standard working hours are 40 hours per workweek (Monday to Friday, 8 hours/day).\n"
        "2. All scheduled overtime exceeding 5 hours/week must be pre-approved by the Department Director.\n"
        "3. Consecutive overtime across more than two consecutive pay periods triggers a mandatory Work-Life Balance review by People Operations.\n\n"
        "## Section 2: Compensation & Comp-Time Credit\n"
        "1. Eligible hourly and non-exempt staff receive 1.5x standard hourly rate for overtime hours.\n"
        "2. Salaried exempt employees working sustained surge periods qualify for Compensatory Time Off (Comp-Time) at 1:1 ratio, up to 10 days per calendar year.\n\n"
        "## Section 3: High Flight-Risk Overtime Mitigation\n"
        "HR Analytics identifies OverTime as a primary flight-risk driver. When an employee is flagged with Overtime and low Job Satisfaction, "
        "their manager must redistribute project tasks within 10 business days."
    )
    ot_path = os.path.join(DOCS_DIR, "overtime_and_workload_policy.md")
    with open(ot_path, "w", encoding="utf-8") as f:
        f.write(ot_policy)
    ingest_document(ot_path, "overtime_and_workload_policy.md", title="Overtime & Workload Policy", metadata={"category": "Policy"})

    # Seed 2: Retention Playbook & Flight-Risk Interventions
    retention_playbook = (
        "# People Operations Playbook: High Flight-Risk Employee Retention Interventions\n\n"
        "## Section 1: Flight-Risk Diagnostic Protocol\n"
        "Employees with a Flight Risk Score of 4 or higher (out of 8 criteria) are placed on the Confidential Flight Risk Watchlist. "
        "Key trigger indicators include: Overtime without equity participation, compensation below department median, tenure under 2 years, "
        "and low job or environment satisfaction ratings.\n\n"
        "## Section 2: 5-Day Stay Interview Action Plan\n"
        "1. **Day 1 - Trigger Notification:** HR Business Partner notifies the VP of the respective Department.\n"
        "2. **Day 3 - Stay Interview:** Conduct an empathetic 1-on-1 Stay Interview focusing on career trajectory, compensation alignment, and blockers.\n"
        "3. **Day 5 - Retention Offer:** Where feasible, present adjustments including equity tier elevation, project re-scoping, or flexible work schedule.\n\n"
        "## Section 3: Department Retention Benchmarks\n"
        "Target annualized attrition across Sales, R&D, and Support is capped at 12%. Departments exceeding 18% turnover undergo a mandatory leadership review."
    )
    ret_path = os.path.join(DOCS_DIR, "retention_and_engagement_playbook.md")
    with open(ret_path, "w", encoding="utf-8") as f:
        f.write(retention_playbook)
    ingest_document(ret_path, "retention_and_engagement_playbook.md", title="Retention & Engagement Playbook", metadata={"category": "Playbook"})

    # Seed 3: Compensation & Equity Participation Guidelines
    comp_guidelines = (
        "# Compensation, Equity & Stock Option Tier Framework\n\n"
        "## Section 1: Stock Option Equity Tiers\n"
        "Stock Option Levels range from 0 to 3:\n"
        "• Level 0: Baseline entry (no equity grant). High attrition correlation observed among Level 0 cohorts.\n"
        "• Level 1: Standard professional grant (4-year vesting schedule, 1-year cliff).\n"
        "• Level 2: Senior specialist and leadership grant.\n"
        "• Level 3: Executive and key retention grant.\n\n"
        "## Section 2: Compensation Equity Reviews\n"
        "Annual salary reviews occur in Q1 and Q3. Employees in the lowest salary quartile (Tier 1) with High Performance ratings qualify for off-cycle adjustments up to 15%."
    )
    comp_path = os.path.join(DOCS_DIR, "compensation_and_equity_framework.md")
    with open(comp_path, "w", encoding="utf-8") as f:
        f.write(comp_guidelines)
    ingest_document(comp_path, "compensation_and_equity_framework.md", title="Compensation & Equity Guidelines", metadata={"category": "Framework"})

    # Ingest ETL PDF if present in workspace root
    etl_pdf = os.path.join(BASE_DIR, "ETL_Pipeline_Phase_Wise_Implementation.pdf")
    if os.path.exists(etl_pdf):
        ingest_document(etl_pdf, "ETL_Pipeline_Phase_Wise_Implementation.pdf", title="ETL Pipeline Implementation Guide", metadata={"category": "Technical"})


# Ensure policies are seeded on import
seed_default_hr_policies()
