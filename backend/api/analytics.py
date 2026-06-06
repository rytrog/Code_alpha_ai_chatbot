"""
Analytics API — GET /api/analytics, GET /api/logs, GET /api/documents
"""
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timezone
from database.db import get_conn
from psycopg.rows import dict_row

router = APIRouter()


@router.get("/analytics")
async def get_analytics(conn=Depends(get_conn)):
    """Dashboard statistics."""
    # Total questions
    r = await conn.execute("SELECT COUNT(*) FROM chat_logs")
    total_questions = (await r.fetchone())["count"]

    # Today's questions
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    r = await conn.execute("SELECT COUNT(*) FROM chat_logs WHERE created_at >= %s", (today_start,))
    today_questions = (await r.fetchone())["count"]

    # Counts by response type
    r = await conn.execute("SELECT response_type, COUNT(*) as cnt FROM chat_logs GROUP BY response_type")
    counts = {row["response_type"]: row["cnt"] for row in await r.fetchall()}

    # Average response time
    r = await conn.execute("SELECT AVG(response_time_ms) as avg_rt FROM chat_logs")
    avg_response_time = round((await r.fetchone())["avg_rt"] or 0, 2)

    # Documents uploaded
    r = await conn.execute("SELECT COUNT(*) FROM documents")
    documents_uploaded = (await r.fetchone())["count"]

    # Cache entries
    r = await conn.execute("SELECT COUNT(*) FROM answer_cache")
    cache_entries = (await r.fetchone())["count"]

    return {
        "total_questions": total_questions,
        "today_questions": today_questions,
        "cache_hits": counts.get("cached", 0),
        "ai_calls": counts.get("rag", 0),
        "faq_hits": counts.get("faq", 0),
        "greeting_hits": counts.get("greeting", 0),
        "out_of_scope": counts.get("out_of_scope", 0),
        "documents_uploaded": documents_uploaded,
        "cache_entries": cache_entries,
        "avg_response_time_ms": avg_response_time,
    }


@router.get("/logs")
async def get_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    search: str = Query(default=""),
    date: str = Query(default=""),
    conn=Depends(get_conn),
):
    """Paginated chat logs."""
    conditions = []
    params = []

    if search:
        conditions.append("(question ILIKE %s OR answer ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d")
            conditions.append("created_at >= %s AND created_at < %s + INTERVAL '1 day'")
            params.extend([filter_date, filter_date])
        except ValueError:
            pass

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    r = await conn.execute(f"SELECT COUNT(*) FROM chat_logs{where_clause}", params)
    total = (await r.fetchone())["count"]

    # Fetch page
    offset = (page - 1) * per_page
    r = await conn.execute(
        f"SELECT * FROM chat_logs{where_clause} ORDER BY created_at DESC LIMIT %s OFFSET %s",
        params + [per_page, offset],
    )
    logs = await r.fetchall()

    return {
        "logs": [
            {
                "id": log["id"],
                "question": log["question"],
                "answer": log["answer"],
                "source": log["source"] or "",
                "response_type": log["response_type"],
                "response_time_ms": log["response_time_ms"],
                "created_at": log["created_at"].isoformat() if log["created_at"] else "",
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page else 1,
    }


@router.get("/documents")
async def get_documents(conn=Depends(get_conn)):
    """List all uploaded documents."""
    r = await conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
    docs = await r.fetchall()

    return {
        "documents": [
            {
                "id": doc["id"],
                "filename": doc["filename"],
                "source_type": doc["source_type"] or "document",
                "chunk_count": doc["chunk_count"],
                "uploaded_at": doc["uploaded_at"].isoformat() if doc["uploaded_at"] else "",
            }
            for doc in docs
        ]
    }
