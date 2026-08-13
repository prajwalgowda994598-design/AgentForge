"""
Gets exact free model IDs from OpenRouter API and tests them live.
Run: python find_working_models.py
"""
import urllib.request, urllib.error, json, time

# Set your key here or in a .env file as OPENROUTER_API_KEY=sk-or-v1-...
import os
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
API_KEY = ""
if os.path.exists(_env):
    for _line in open(_env).read().splitlines():
        if _line.strip().startswith("OPENROUTER_API_KEY="):
            API_KEY = _line.strip().split("=", 1)[1].strip().strip('"').strip("'")
if not API_KEY:
    API_KEY = input("Paste your OPENROUTER_API_KEY (sk-or-v1-...): ").strip()

print("Fetching model list...")
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {API_KEY}", "HTTP-Referer": "http://localhost:3000"}
)
with urllib.request.urlopen(req, timeout=20) as r:
    models = json.loads(r.read())["data"]

print(f"Total models: {len(models)}\n")

free = []
for m in models:
    p = m.get("pricing", {})
    if str(p.get("prompt", "1")) == "0" and str(p.get("completion", "1")) == "0":
        free.append({"id": m["id"], "name": m.get("name",""), "ctx": m.get("context_length",0)})

free.sort(key=lambda x: x["id"])
print(f"FREE models ({len(free)}):\n")
for m in free:
    print(f"  {m['id']}")

print("\n" + "="*65)
print("Testing each...\n")

working = []
SKIP = ["embed", "rerank", "vl-1b", "transcri", "speech", "whisper"]
for m in free:
    mid = m["id"]
    if any(s in mid.lower() for s in SKIP):
        print(f"  SKIP  {mid}"); continue
    try:
        body = json.dumps({
            "model": mid,
            "messages": [{"role":"user","content":"say ok"}],
            "max_tokens": 8,
        }).encode()
        r2 = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "AgentForge",
            },
            method="POST",
        )
        with urllib.request.urlopen(r2, timeout=15) as resp:
            rb = json.loads(resp.read())
            reply = rb["choices"][0]["message"]["content"].strip()[:25]
            print(f"  OK    {mid}  →  {reply!r}")
            working.append(mid)
    except urllib.error.HTTPError as e:
        try: msg = json.loads(e.read()).get("error",{}).get("message","")[:70]
        except: msg = str(e)
        print(f"  {e.code}   {mid}  →  {msg}")
    except Exception as e:
        print(f"  ERR   {mid}  →  {str(e)[:70]}")
    time.sleep(0.4)

print("\n" + "="*65)
print(f"WORKING ({len(working)}):")
for m in working:
    print(f"  {m}")
if working:
    print(f"\nRender dashboard values:")
    print(f"  OPENROUTER_MODEL           = {working[0]}")
    print(f"  OPENROUTER_FALLBACK_MODELS = {','.join(working[1:4])}")
input("\nPress Enter...")
