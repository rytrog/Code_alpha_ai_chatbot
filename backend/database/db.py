import sys
import uuid
import asyncio
from datetime import datetime, timezone
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings
from utils.logger import logger

from chromadb import EmbeddingFunction

class DummyEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input):
        # Return a zero embedding of dimension 384 (standard default embedding size)
        return [[0.0] * 384 for _ in input]

# Lazy ChromaDB client & collection cache
_db_client = None
_collections = {}

def _get_db_client():
    global _db_client
    if _db_client is None:
        logger.info("Initializing ChromaDB PersistentClient for relational DB mock...")
        _db_client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _db_client

def _get_collection(name):
    global _collections
    if name not in _collections:
        client = _get_db_client()
        _collections[name] = client.get_or_create_collection(
            name=name,
            embedding_function=DummyEmbeddingFunction(),
        )
    return _collections[name]

def get_next_document_id():
    col = _get_collection("documents")
    res = col.get()
    max_id = 0
    if res and res["metadatas"]:
        for meta in res["metadatas"]:
            if meta:
                meta_id = meta.get("id", 0)
                if meta_id > max_id:
                    max_id = meta_id
    return max_id + 1

class Row(dict):
    """Custom row class that supports dict key access and tuple index access."""
    def __init__(self, data):
        super().__init__(data)
        self._data = list(data.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._data[key]
        return super().__getitem__(key)

class MockCursor:
    def __init__(self, query, params=None):
        self.query = query
        self.params = params or ()
        self.results = []
        self.idx = 0
        self.rowcount = 0
        self._execute()

    def _execute(self):
        sql = self.query.strip().replace('\n', ' ')
        logger.debug(f"Mock SQL Execute: '{sql}' | Params: {self.params}")
        
        # 1. FAQ Queries
        if "SELECT COUNT(*) FROM faq" in sql:
            count = _get_collection("faq").count()
            self.results = [Row({"count": count})]
            self.rowcount = 1
            
        elif "SELECT answer, source FROM faq WHERE normalized_key" in sql:
            key = self.params[0]
            col = _get_collection("faq")
            res = col.get(ids=[key])
            if res and res["metadatas"] and res["metadatas"][0]:
                meta = res["metadatas"][0]
                self.results = [Row({
                    "answer": meta.get("answer"),
                    "source": meta.get("source") or "FAQ Database"
                })]
            else:
                self.results = []
            self.rowcount = len(self.results)
            
        elif "SELECT normalized_key, answer, source FROM faq" in sql:
            col = _get_collection("faq")
            res = col.get()
            self.results = []
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta:
                        self.results.append(Row({
                            "normalized_key": meta.get("normalized_key"),
                            "answer": meta.get("answer"),
                            "source": meta.get("source")
                        }))
            self.rowcount = len(self.results)
            
        elif "INSERT INTO faq" in sql:
            if len(self.params) == 4:
                q, norm_key, a, cat = self.params
                src = "seed"
            elif len(self.params) == 5:
                q, norm_key, a, cat, src = self.params
            else:
                q, norm_key, a, src = self.params
                cat = "general"
                
            col = _get_collection("faq")
            col.upsert(
                ids=[norm_key],
                documents=[q],
                metadatas=[{
                    "question": q,
                    "normalized_key": norm_key,
                    "answer": a,
                    "category": cat,
                    "source": src
                }]
            )
            self.rowcount = 1
            
        elif "UPDATE faq SET answer = %s WHERE normalized_key" in sql:
            answer = self.params[0]
            key = self.params[1] if len(self.params) > 1 else 'hod cse'
            col = _get_collection("faq")
            res = col.get(ids=[key])
            if res and res["metadatas"] and res["metadatas"][0]:
                meta = res["metadatas"][0]
                meta["answer"] = answer
                col.update(ids=[key], metadatas=[meta])
            self.rowcount = 1

        elif "DELETE FROM faq WHERE source" in sql:
            src = self.params[0]
            col = _get_collection("faq")
            col.delete(where={"source": src})
            self.rowcount = 1

        # 2. Answer Cache Queries
        elif "SELECT COUNT(*) FROM answer_cache" in sql:
            count = _get_collection("answer_cache").count()
            self.results = [Row({"count": count})]
            self.rowcount = 1

        elif "SELECT answer, source FROM answer_cache WHERE normalized_key" in sql:
            key = self.params[0]
            col = _get_collection("answer_cache")
            res = col.get(ids=[key])
            if res and res["metadatas"] and res["metadatas"][0]:
                meta = res["metadatas"][0]
                self.results = [Row({
                    "answer": meta.get("answer"),
                    "source": meta.get("source") or ""
                })]
            else:
                self.results = []
            self.rowcount = len(self.results)

        elif "DELETE FROM answer_cache WHERE normalized_key" in sql:
            key = self.params[0]
            col = _get_collection("answer_cache")
            col.delete(ids=[key])
            self.rowcount = 1

        elif "INSERT INTO answer_cache" in sql:
            norm_key, answer, source = self.params[:3]
            col = _get_collection("answer_cache")
            col.upsert(
                ids=[norm_key],
                documents=[answer],
                metadatas=[{
                    "normalized_key": norm_key,
                    "answer": answer,
                    "source": source,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }]
            )
            self.rowcount = 1

        elif "DELETE FROM answer_cache WHERE source" in sql:
            filename = self.params[0].replace("%", "")
            col = _get_collection("answer_cache")
            res = col.get()
            if res and res["metadatas"]:
                ids_to_delete = []
                for meta in res["metadatas"]:
                    if meta:
                        src = meta.get("source") or ""
                        if filename.lower() in src.lower():
                            ids_to_delete.append(meta["normalized_key"])
                if ids_to_delete:
                    col.delete(ids=ids_to_delete)
            self.rowcount = 1

        elif "DELETE FROM answer_cache" in sql or "TRUNCATE TABLE answer_cache" in sql:
            col = _get_collection("answer_cache")
            res = col.get()
            if res and res["ids"]:
                col.delete(ids=res["ids"])
            self.rowcount = 1

        # 3. Documents Registry Queries
        elif "SELECT COUNT(*) FROM documents" in sql:
            count = _get_collection("documents").count()
            self.results = [Row({"count": count})]
            self.rowcount = 1

        elif "INSERT INTO documents" in sql:
            filename = self.params[0]
            source_type = self.params[1]
            chunk_count = self.params[2]
            status = "completed"
            error_message = None
            if len(self.params) > 3:
                status = self.params[3]
            if len(self.params) > 4:
                error_message = self.params[4]
                
            next_id = get_next_document_id()
            col = _get_collection("documents")
            col.upsert(
                ids=[filename],
                documents=[filename],
                metadatas=[{
                    "id": next_id,
                    "filename": filename,
                    "source_type": source_type,
                    "chunk_count": chunk_count,
                    "status": status,
                    "error_message": error_message,
                    "uploaded_at": datetime.now(timezone.utc).isoformat()
                }]
            )
            self.rowcount = 1

        elif "SELECT * FROM documents WHERE id" in sql:
            doc_id = int(self.params[0])
            col = _get_collection("documents")
            res = col.get()
            self.results = []
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta and meta.get("id") == doc_id:
                        self.results.append(Row({
                            "id": meta.get("id"),
                            "filename": meta.get("filename"),
                            "source_type": meta.get("source_type"),
                            "chunk_count": meta.get("chunk_count"),
                            "status": meta.get("status", "completed"),
                            "error_message": meta.get("error_message"),
                            "uploaded_at": datetime.fromisoformat(meta.get("uploaded_at")) if meta.get("uploaded_at") else None
                        }))
                        break
            self.rowcount = len(self.results)

        elif "status = 'pending'" in sql or "status = \'pending\'" in sql:
            col = _get_collection("documents")
            res = col.get(where={"status": "pending"})
            self.results = []
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta:
                        self.results.append(Row({
                            "id": meta.get("id"),
                            "filename": meta.get("filename"),
                            "source_type": meta.get("source_type")
                        }))
                self.results.sort(key=lambda x: x["id"])
            self.rowcount = len(self.results)

        elif "SELECT * FROM documents" in sql:
            col = _get_collection("documents")
            res = col.get()
            self.results = []
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta:
                        uploaded_at_str = meta.get("uploaded_at")
                        uploaded_at = datetime.fromisoformat(uploaded_at_str) if uploaded_at_str else None
                        self.results.append(Row({
                            "id": meta.get("id"),
                            "filename": meta.get("filename"),
                            "source_type": meta.get("source_type"),
                            "chunk_count": meta.get("chunk_count"),
                            "status": meta.get("status", "completed"),
                            "error_message": meta.get("error_message"),
                            "uploaded_at": uploaded_at
                        }))
            self.results.sort(key=lambda x: x["uploaded_at"] or datetime.min, reverse=True)
            self.rowcount = len(self.results)

        elif "DELETE FROM documents WHERE id" in sql:
            doc_id = int(self.params[0])
            col = _get_collection("documents")
            res = col.get()
            filename_to_delete = None
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta and meta.get("id") == doc_id:
                        filename_to_delete = meta.get("filename")
                        break
            if filename_to_delete:
                col.delete(ids=[filename_to_delete])
            self.rowcount = 1

        elif "UPDATE documents SET" in sql:
            col = _get_collection("documents")
            res = col.get()
            doc_id = int(self.params[-1])
            meta_to_update = None
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta and meta.get("id") == doc_id:
                        meta_to_update = meta
                        break
            if meta_to_update:
                if "status = 'processing'" in sql or "status = \'processing\'" in sql:
                    meta_to_update["status"] = "processing"
                elif "status = 'completed'" in sql or "status = \'completed\'" in sql:
                    meta_to_update["chunk_count"] = self.params[0]
                    meta_to_update["status"] = "completed"
                    meta_to_update["error_message"] = None
                elif "status = 'failed'" in sql or "status = \'failed\'" in sql:
                    meta_to_update["status"] = "failed"
                    meta_to_update["error_message"] = str(self.params[0])
                col.update(ids=[meta_to_update["filename"]], metadatas=[meta_to_update])
            self.rowcount = 1

        # 4. Chat History Queries (Memory)
        elif "INSERT INTO chat_history" in sql:
            session_id, role, content = self.params
            col = _get_collection("chat_history")
            msg_id = f"{session_id}_{datetime.now(timezone.utc).timestamp()}_{uuid.uuid4().hex[:4]}"
            col.add(
                ids=[msg_id],
                documents=[content],
                metadatas=[{
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }]
            )
            self.rowcount = 1

        elif "SELECT role, content FROM chat_history" in sql:
            session_id = self.params[0]
            limit = self.params[1] if len(self.params) > 1 else 100
            col = _get_collection("chat_history")
            res = col.get(where={"session_id": session_id})
            self.results = []
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta:
                        created_at_str = meta.get("created_at")
                        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.min
                        self.results.append({
                            "role": meta.get("role"),
                            "content": meta.get("content"),
                            "created_at": created_at
                        })
                self.results.sort(key=lambda x: x["created_at"])
                self.results = [Row({"role": r["role"], "content": r["content"]}) for r in self.results[-limit:]]
            self.rowcount = len(self.results)

        elif "DELETE FROM chat_history WHERE session_id" in sql and "NOT IN" in sql:
            session_id = self.params[0]
            limit = self.params[2]
            col = _get_collection("chat_history")
            res = col.get(where={"session_id": session_id})
            if res and res["metadatas"]:
                items = []
                for i in range(len(res["ids"])):
                    meta = res["metadatas"][i]
                    if meta:
                        created_at_str = meta.get("created_at")
                        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.min
                        items.append({
                            "id": res["ids"][i],
                            "created_at": created_at
                        })
                items.sort(key=lambda x: x["created_at"], reverse=True)
                if len(items) > limit:
                    ids_to_delete = [item["id"] for item in items[limit:]]
                    col.delete(ids=ids_to_delete)
            self.rowcount = 1

        elif "DELETE FROM chat_history WHERE created_at" in sql:
            col = _get_collection("chat_history")
            res = col.get()
            if res and res["metadatas"]:
                ids_to_delete = []
                now = datetime.now(timezone.utc)
                for i in range(len(res["ids"])):
                    meta = res["metadatas"][i]
                    if meta:
                        created_at_str = meta.get("created_at")
                        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.min
                        if (now - created_at).total_seconds() > 3600:
                            ids_to_delete.append(res["ids"][i])
                if ids_to_delete:
                    col.delete(ids=ids_to_delete)
            self.rowcount = 1

        # 5. Chat Logs Queries (Analytics)
        elif "INSERT INTO chat_logs" in sql:
            question, answer, source, response_type, response_time_ms = self.params
            col = _get_collection("chat_logs")
            log_id = f"log_{uuid.uuid4().hex}"
            col.add(
                ids=[log_id],
                documents=[question],
                metadatas=[{
                    "id": log_id,
                    "question": question,
                    "answer": answer,
                    "source": source,
                    "response_type": response_type,
                    "response_time_ms": response_time_ms,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }]
            )
            self.rowcount = 1

        elif "SELECT COUNT(*) FROM chat_logs" in sql:
            col = _get_collection("chat_logs")
            res = col.get()
            count = 0
            if res and res["metadatas"]:
                if "created_at >=" in sql:
                    filter_time = self.params[0]
                    if isinstance(filter_time, str):
                         filter_time = datetime.fromisoformat(filter_time.replace("Z", "+00:00"))
                    for meta in res["metadatas"]:
                        if meta:
                            created_at_str = meta.get("created_at")
                            created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.min
                            if created_at.tzinfo is None:
                                created_at = created_at.replace(tzinfo=timezone.utc)
                            if filter_time.tzinfo is None:
                                filter_time = filter_time.replace(tzinfo=timezone.utc)
                            if created_at >= filter_time:
                                count += 1
                elif "WHERE" in sql and ("question ILIKE" in sql or "answer ILIKE" in sql):
                    search = self.params[0].replace("%", "").lower()
                    for meta in res["metadatas"]:
                        if meta:
                            q = meta.get("question", "").lower()
                            a = meta.get("answer", "").lower()
                            if search in q or search in a:
                                count += 1
                else:
                    count = len(res["metadatas"])
            self.results = [Row({"count": count})]
            self.rowcount = 1

        elif "GROUP BY response_type" in sql:
            col = _get_collection("chat_logs")
            res = col.get()
            counts = {}
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta:
                        rtype = meta.get("response_type", "unknown")
                        counts[rtype] = counts.get(rtype, 0) + 1
            self.results = [Row({"response_type": k, "cnt": v}) for k, v in counts.items()]
            self.rowcount = len(self.results)

        elif "AVG(response_time_ms)" in sql:
            col = _get_collection("chat_logs")
            res = col.get()
            total_time = 0.0
            count = 0
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta:
                        total_time += meta.get("response_time_ms", 0.0)
                        count += 1
            avg_rt = total_time / count if count > 0 else 0.0
            self.results = [Row({"avg_rt": avg_rt})]
            self.rowcount = 1

        elif "SELECT * FROM chat_logs" in sql:
            col = _get_collection("chat_logs")
            res = col.get()
            raw_logs = []
            if res and res["metadatas"]:
                for meta in res["metadatas"]:
                    if meta:
                        created_at_str = meta.get("created_at")
                        created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.min
                        raw_logs.append({
                            "id": meta.get("id"),
                            "question": meta.get("question"),
                            "answer": meta.get("answer"),
                            "source": meta.get("source"),
                            "response_type": meta.get("response_type"),
                            "response_time_ms": meta.get("response_time_ms"),
                            "created_at": created_at
                        })
            
            filtered_logs = []
            search = ""
            if "WHERE" in sql and ("question ILIKE" in sql or "answer ILIKE" in sql):
                search = self.params[0].replace("%", "").lower()
                
            for log in raw_logs:
                if search:
                    if search in log["question"].lower() or search in log["answer"].lower():
                        filtered_logs.append(log)
                else:
                    filtered_logs.append(log)
                    
            filtered_logs.sort(key=lambda x: x["created_at"], reverse=True)
            
            limit = self.params[-2] if len(self.params) >= 2 else len(filtered_logs)
            offset = self.params[-1] if len(self.params) >= 1 else 0
            
            self.results = [Row(log) for log in filtered_logs[offset:offset+limit]]
            self.rowcount = len(self.results)

        elif "SELECT 1" in sql:
            self.results = [Row({"?column?": 1})]
            self.rowcount = 1
            
        elif "SELECT 1 FROM pg_database" in sql:
            self.results = [Row({"?column?": 1})]
            self.rowcount = 1

        else:
            logger.warning(f"Mock SQL query fell through: '{sql}'")
            self.results = []
            self.rowcount = 0

    async def fetchone(self):
        if self.idx < len(self.results):
            row = self.results[self.idx]
            self.idx += 1
            return row
        return None

    async def fetchall(self):
        rows = self.results[self.idx:]
        self.idx = len(self.results)
        return rows

class MockConnection:
    def __init__(self):
        self.row_factory = None

    class DummyTransaction:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def transaction(self):
        return self.DummyTransaction()

    async def execute(self, query, params=None):
        cursor = MockCursor(query, params)
        return cursor

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def cursor(self):
        return MockCursorSync(self)

class MockCursorSync:
    def __init__(self, conn):
        self.conn = conn
        self.results = []
        self.idx = 0
        self.rowcount = 0

    def execute(self, query, params=None):
        c = MockCursor(query, params)
        self.results = c.results
        self.rowcount = c.rowcount
        self.idx = 0

    def fetchone(self):
        if self.idx < len(self.results):
            row = self.results[self.idx]
            self.idx += 1
            return row
        return None

    def fetchall(self):
        rows = self.results[self.idx:]
        self.idx = len(self.results)
        return rows

    def close(self):
        pass

class MockPool:
    def connection(self):
        return MockConnection()
    async def open(self):
        pass
    async def close(self):
        pass

# ── Instantiate singletons for other scripts ──
_conninfo = ""
db_pool = MockPool()

async def init_pool():
    pass

async def close_pool():
    pass

async def init_db():
    _get_collection("faq")
    _get_collection("answer_cache")
    _get_collection("documents")
    _get_collection("chat_logs")
    _get_collection("chat_history")
    logger.info("ChromaDB collections initialized for relational storage.")

async def get_conn():
    yield MockConnection()

# ── Dynamic module injection for sys.modules ──
class MockPsycopgRows:
    @staticmethod
    def dict_row(*args, **kwargs):
        pass

class MockPsycopg:
    class AsyncConnection:
        @staticmethod
        async def connect(*args, **kwargs):
            return MockConnection()
            
    @staticmethod
    def connect(*args, **kwargs):
        return MockConnection()

sys.modules['psycopg'] = MockPsycopg()
sys.modules['psycopg.rows'] = MockPsycopgRows()
sys.modules['psycopg_pool'] = MockPsycopg()
