"""
Full end-to-end HTTP test: submit research, wait for pipeline to complete via polling.
Run from Project01 root.
"""
import sys, os, asyncio, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agentforge'))

async def main():
    from agentforge.backend.database.session import create_tables
    await create_tables()

    from agentforge.backend.vectorstore.faiss_store import get_vector_store
    vs = await get_vector_store()
    print(f"VS ready ({vs._index.ntotal} vectors)")

    from agentforge.backend.services.redis_service import get_redis_client
    await (await get_redis_client()).ping()

    from httpx import AsyncClient, ASGITransport
    from agentforge.backend.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Submit
        resp = await client.post(
            "/api/v1/research",
            json={"query": "What is quantum computing?", "top_k": 3},
            timeout=15.0,
        )
        print(f"POST status: {resp.status_code}")
        if resp.status_code != 202:
            print("FAIL:", resp.text)
            return

        data = resp.json()
        session_id = data["session_id"]
        print(f"session_id: {session_id}")

        # 2. Poll until done (max 180s)
        print("Waiting for pipeline to complete", end="", flush=True)
        deadline = time.time() + 180
        while time.time() < deadline:
            await asyncio.sleep(3)
            poll = await client.get(f"/api/v1/research/{session_id}", timeout=10.0)
            if poll.status_code == 200:
                s = poll.json()
                status = s.get("status")
                print(f"\r  status: {status}           ", end="", flush=True)
                if status in ("completed", "failed"):
                    print()
                    print("FINAL STATUS:", status)
                    if status == "completed":
                        print("critic_score :", s.get("critic_score"))
                        ans = s.get("final_answer") or ""
                        print("answer[:300] :", ans[:300])
                    else:
                        print("ERROR:", s)
                    return
            else:
                print(f"\npoll error {poll.status_code}: {poll.text[:200]}")

        print("\nTIMEOUT — pipeline did not complete within 180s")

asyncio.run(main())
