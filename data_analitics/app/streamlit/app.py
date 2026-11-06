"""
Точка входа для обратной совместимости. Запускает Home.py.
"""
import runpy
from pathlib import Path

home_path = Path(__file__).resolve().parent / "Home.py"
runpy.run_path(str(home_path), run_name="__main__")
