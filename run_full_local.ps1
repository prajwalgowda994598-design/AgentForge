Set-Location "C:\Users\M M PRAJWAL\Desktop\Project01\agentforge"
$env:PYTHONPATH = "C:\Users\M M PRAJWAL\Desktop\Project01"
$env:OPENROUTER_API_KEY = (Get-Content .env | Select-String '^OPENROUTER_API_KEY=' | ForEach-Object { $_.Line.Split('=',2)[1].Trim() })
$env:OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
$env:LLM_PROVIDER = 'openrouter'
$env:LOCAL_DEV = 'true'

Start-Process -FilePath "C:\Users\M M PRAJWAL\Desktop\Project01\agentforge\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","agentforge.backend.main:app","--host","0.0.0.0","--port","8000","--reload","--log-level","info" -WorkingDirectory "C:\Users\M M PRAJWAL\Desktop\Project01\agentforge"
Start-Process -FilePath "C:\Users\M M PRAJWAL\Desktop\Project01\agentforge\frontend\node_modules\.bin\vite.cmd" -WorkingDirectory "C:\Users\M M PRAJWAL\Desktop\Project01\agentforge\frontend" -ArgumentList "--host","0.0.0.0","--port","5173"
