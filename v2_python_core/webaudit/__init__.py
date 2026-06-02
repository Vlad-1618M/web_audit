"""Web Audit v2 package root.

What: Public package marker; exposes ``__version__`` for imports and reports.
Where: Imported as ``webaudit`` after ``pip install -e .``; not used directly by CLI.
How: ``from webaudit import __version__`` — orchestrator and CLI import from submodules.
"""

from webaudit.__version__ import __version__

__all__ = ["__version__"]
