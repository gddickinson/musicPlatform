"""Test setup: headless Qt (offscreen), silent pygame audio, and PyQt5 for pyqtgraph and pytest-qt (when installed),
so another Qt binding in the environment (e.g. PySide6) is never mixed in."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYQTGRAPH_QT_LIB", "PyQt5")
os.environ.setdefault("PYTEST_QT_API", "pyqt5")
