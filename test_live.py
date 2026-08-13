"""
AgentForge end-to-end live test.
Uses only Python stdlib — no pip installs needed.
Run:  python test_live.py
"""
import urllib.request, urllib.error, json, time, sys

BACKEND = "https://agentforge-backend-0jm1.onrender.com"

def req(method, path, data=None):
    url = BACKEND + path
    body = json.dumps(data).encode() if data else None
    hdrs = {"Content-Type": "application/json", "User-Agent": "AgentForge-Test/1.0"}
    r = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:    return e.code, json.loads(e.read())
        except: return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}

SEP = "=" * 60
print(SEP)
print("AgentForge Live Test  —  backend:", BACKEND)
print(SEP)

# 1. Health
print("\n[1] /health")
s, b = req("GET", "/health")
print(f"  {s}  {b}")

# 2. Readiness
print("\n[2] /health/ready")
s, b = req("GET", "/health/ready")
print(f"  {s}  {b}")
if s != 200:
    print("  Backend not ready — wait for Render deploy to finish, then re-run.")
    input("Press Enter to exit..."); sys.exit(1)

# 3. Submit
print("\n[3] POST /api/v1/research  query='What is Python?'")
s, b = req("POST", "/api/v1/research", {"query": "What is Python?", "top_k": 2})
print(f"  {s}  {b}")
if "session_id" not in b:
    print("  Cannot start session."); input("Press Enter..."); sys.exit(1)

sid = b["session_id"]
print(f"  session_id = {sid}")

# 4. Poll
print("\n[4] Polling every 10 s (up to 5 min)...")
for i in range(30):
    time.sleep(10)
    elapsed = (i+1)*10
    s, d = req("GET", f"/api/v1/research/{sid}")
    st = d.get("status","?")
    print(f"  [{elapsed:3d}s]  status={st}  critic={d.get('critic_score','')}", flush=True)

    if st == "completed":
        fa = d.get("final_answer","")
        print(f"\n{SEP}")
        print("  SUCCESS")
        print(f"  critic_score = {d.get('critic_score')}")
        print(f"  iterations   = {d.get('iterations')}")
        print(f"\n  Answer (first 600 chars):")
        print("  " + fa[:600].replace("\n", "\n  "))
        print(SEP)
        break

    if st == "failed":
        meta = d.get("metadata_") or {}
        err  = meta.get("error","no detail")
        print(f"\n{SEP}")
        print("  FAILED")
        print(f"  error: {err[:600]}")
        s2, runs = req("GET", f"/api/v1/research/{sid}/runs")
        if isinstance(runs, list):
            print("\n  Agent runs:")
            for r2 in runs:
                em = (r2.get("error_message") or "")[:200]
                print(f"    {r2.get('agent_name'):15s}  {r2.get('status'):12s}  {em}")
        print(SEP)
        break
else:
    print(f"\n  TIMEOUT — still running after 5 min. Check Render logs.")

input("\nPress Enter to exit...")
