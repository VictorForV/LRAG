@echo off
chcp 65001 >nul 2>&1

echo Sozdanie virtualnogo okruzheniya dlya Windows...
uv venv
echo Ustanovka zavisimostey...
call .venv\Scripts\activate.bat
uv pip install -e .
echo Gotovo! Zapustite run_web.bat
pause
