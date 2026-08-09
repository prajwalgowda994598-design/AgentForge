"""
sitecustomize.py – loaded automatically by Python before any other import.

The repo layout has backend/ at the repo root, but all source files use
'from agentforge.backend.X import Y'.  This file installs a meta path finder
that transparently redirects every 'agentforge.backend.*' import to the real
'backend.*' package that lives at the repo root.

Python loads sitecustomize.py from every directory on PYTHONPATH before
any user code runs, so setting PYTHONPATH=/opt/render/project/src is enough.
"""
import importlib
import importlib.abc
import importlib.machinery
import sys


class _AgentForgeRedirector(importlib.abc.MetaPathFinder):
    """Redirect agentforge.backend.* → backend.*"""

    PREFIX = "agentforge.backend"
    REAL   = "backend"

    def find_spec(self, fullname, path, target=None):
        if fullname == "agentforge":
            return self._make_namespace_spec()

        if fullname == "agentforge.backend" or fullname.startswith("agentforge.backend."):
            real_name = self.REAL + fullname[len(self.PREFIX):]
            try:
                real_spec = importlib.util.find_spec(real_name)
            except (ModuleNotFoundError, ValueError):
                return None
            if real_spec is None:
                return None
            return real_spec

        return None

    @staticmethod
    def _make_namespace_spec():
        if "agentforge" in sys.modules:
            return None  # already loaded
        spec = importlib.machinery.ModuleSpec(
            "agentforge",
            loader=None,
            is_package=True,
        )
        spec.submodule_search_locations = []
        return spec


# Only install once
if not any(isinstance(f, _AgentForgeRedirector) for f in sys.meta_path):
    sys.meta_path.insert(0, _AgentForgeRedirector())
