"""
AgentForge – Neo4j Knowledge Graph Service
============================================
LOCAL_DEV=true  → All operations are no-ops (Neo4j not required locally)
LOCAL_DEV=false → Connects to a real Neo4j instance

The stub implements the same interface so all callers work unchanged.
"""

import os
from typing import Any, Dict, List, Optional

_LOCAL_DEV = os.getenv("LOCAL_DEV", "true").lower() in ("true", "1", "yes")


# ── Stub (local dev) ───────────────────────────────────────────────────────────

class _StubDriver:
    """No-op Neo4j driver for local development."""
    async def verify_connectivity(self) -> None:
        pass
    async def close(self) -> None:
        pass


class KnowledgeGraphService:
    """
    Knowledge graph service.
    In local dev mode all methods return empty results immediately.
    """

    def __init__(self, driver=None):
        self._driver = driver
        self._local = _LOCAL_DEV

    async def create_constraints(self) -> None:
        if self._local:
            return

    async def upsert_node(self, node_id: str, node_type: str, label: str,
                          properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._local:
            return {"id": node_id, "label": label}
        props = properties or {}
        props.update({"id": node_id, "label": label})
        if not node_type.isidentifier():
            from agentforge.backend.core.exceptions import GraphDatabaseError
            raise GraphDatabaseError(f"Invalid node_type: {node_type!r}")
        query = f"""
        MERGE (n:{node_type} {{id: $id}})
        ON CREATE SET n += $props, n.created_at = datetime()
        ON MATCH  SET n += $props, n.updated_at = datetime()
        RETURN n
        """
        async with self._driver.session() as session:
            result = await session.run(query, id=node_id, props=props)
            record = await result.single()
            return dict(record["n"]) if record else {}

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        if self._local:
            return None
        async with self._driver.session() as session:
            result = await session.run("MATCH (n {id: $id}) RETURN n", id=node_id)
            record = await result.single()
            return dict(record["n"]) if record else None

    async def create_relationship(self, source_id: str, target_id: str,
                                  relationship: str,
                                  properties: Optional[Dict[str, Any]] = None) -> None:
        if self._local:
            return

    async def get_related_concepts(self, node_id: str, max_depth: int = 2,
                                   limit: int = 20) -> List[Dict[str, Any]]:
        if self._local:
            return []
        query = """
        MATCH path = (start {id: $node_id})-[*1..$depth]-(related)
        RETURN DISTINCT related, length(path) AS distance
        ORDER BY distance LIMIT $limit
        """
        async with self._driver.session() as session:
            result = await session.run(query, node_id=node_id, depth=max_depth, limit=limit)
            records = await result.data()
            return [{"node": dict(r["related"]), "distance": r["distance"]} for r in records]

    async def search_nodes(self, label_contains: str, limit: int = 10) -> List[Dict[str, Any]]:
        if self._local:
            return []
        query = "MATCH (n) WHERE toLower(n.label) CONTAINS toLower($term) RETURN n LIMIT $limit"
        async with self._driver.session() as session:
            result = await session.run(query, term=label_contains, limit=limit)
            records = await result.data()
            return [dict(r["n"]) for r in records]

    async def store_research_finding(self, session_id: str, finding: str,
                                     sources: List[str],
                                     entity_labels: Optional[List[str]] = None) -> str:
        if self._local:
            import uuid
            return str(uuid.uuid4())
        import uuid
        finding_id = str(uuid.uuid4())
        await self.upsert_node(node_id=finding_id, node_type="Finding",
                               label=finding[:200],
                               properties={"session_id": session_id, "full_text": finding})
        for source in sources:
            source_id = f"source:{source[:100]}"
            await self.upsert_node(node_id=source_id, node_type="Source", label=source[:200])
            await self.create_relationship(finding_id, source_id, "DERIVED_FROM")
        for entity in (entity_labels or []):
            entity_id = f"entity:{entity.lower().replace(' ', '_')}"
            await self.upsert_node(node_id=entity_id, node_type="Concept", label=entity)
            await self.create_relationship(finding_id, entity_id, "MENTIONS")
        return finding_id

    async def get_graph_stats(self) -> Dict[str, int]:
        if self._local:
            return {"nodes": 0, "edges": 0, "note": "Neo4j disabled in local dev mode"}
        async with self._driver.session() as session:
            nodes_result = await session.run("MATCH (n) RETURN count(n) AS count")
            edges_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS count")
            nodes_record = await nodes_result.single()
            edges_record = await edges_result.single()
            return {
                "nodes": nodes_record["count"] if nodes_record else 0,
                "edges": edges_record["count"] if edges_record else 0,
            }


# ── Public helpers ─────────────────────────────────────────────────────────────

async def get_neo4j_driver():
    """Return the Neo4j driver (stub in local dev, real driver in production)."""
    if _LOCAL_DEV:
        return _StubDriver()
    from agentforge.backend.core.config import settings
    from neo4j import AsyncGraphDatabase
    from neo4j.exceptions import ServiceUnavailable
    from agentforge.backend.core.exceptions import GraphDatabaseError
    try:
        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=20,
        )
        await driver.verify_connectivity()
        return driver
    except ServiceUnavailable as exc:
        raise GraphDatabaseError(f"Cannot connect to Neo4j: {exc}") from exc


async def close_neo4j() -> None:
    pass  # Stub handles its own lifecycle; real driver closed in main.py
