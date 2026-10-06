@echo off
cd /d "%~dp0"
rem 使用 anaconda base 环境（PyPDF2/python-docx 等包都装在这里）
call conda activate base 2>nul
python -c "import fastapi, uvicorn, PyPDF2, docx" >nul 2>&1
if errorlevel 1 (
  echo [Installing missing dependencies...]
  python -m pip install fastapi uvicorn pydantic python-multipart PyPDF2 python-docx python-pptx
)
echo [Starting backend] http://localhost:8000  (docs: http://localhost:8000/docs)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
