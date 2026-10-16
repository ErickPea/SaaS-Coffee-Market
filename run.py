"""
Arranca Coffee Market Intelligence con recarga automática en desarrollo.

Uso:
    python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=8000,
    workers=4,
    #reload=True,#
    #reload_dirs=["app"],           # solo mira app/, no data/ ni tests/
    reload_excludes=[
        "*.db",
        "*.db-journal",
        "*.db-wal",
        "*.db-shm",
        "__pycache__",
        "*.pyc",
        ".pytest_cache",
         "uvicorn.log",
    ],
)
