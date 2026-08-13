@echo off
cd /d "%~dp0"
git add "find_working_models.py"
git add "list_free_models.py"
git add "test_live.py"
git add "push_fixes.bat"
git add "run_model_test.bat"
git commit -m "chore: add model diagnostics and live test scripts"
git push
pause
