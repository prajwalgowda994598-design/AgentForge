"""
Test: does running the workflow directly on one asyncio.run() event loop (no thread wrapper)
avoid the 'cannot schedule new futures' crash?
Run from Project01 root.
"""
import sys, os, asyncio
# Make 'agentforge' importable as a package (Project01 is parent of agentforge/)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agentforge'))

async def main():
    from agentforge.backend.database.session import create_tables
    await create_tables()
    print("DB OK")

    from agentforge.backend.vectorstore.faiss_store import get_vector_store
    vs = await get_vector_store()
    print("VS OK, vectors:", vs._index.ntotal if vs._index else 0)

    from agentforge.backend.graph.workflow import run_research_workflow

    async def cb(session_id, agent_name, status):
        print(f"  [{agent_name}] {status}")

    print("\n=== Running workflow on main event loop (no thread) ===")
    try:
        result = await run_research_workflow(
            query="What is quantum computing?",
            session_id="direct-test-001",
            top_k=3,
            status_callback=cb,
        )
        print("\nSUCCESS")
        print("critic_score:", result.get("critic_score"))
        ans = result.get("final_answer", "")
        print("answer[:300]:", ans[:300])
    except Exception as e:
        import traceback
        print("FAIL:", type(e).__name__)
        traceback.print_exc()

asyncio.run(main())
