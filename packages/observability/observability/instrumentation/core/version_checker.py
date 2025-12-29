from __future__ import annotations

import logging
import re


logger = logging.getLogger(__name__)

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:[.-]?([a-zA-Z0-9]+))?")


class VersionChecker:
    def parse(self, version_str: str | None) -> tuple[int, int, int, str | None] | None:
        if not version_str:
            return None
        m = _VERSION_RE.match(version_str)
        if not m:
            return None
        major, minor, patch = m.group(1), m.group(2), m.group(3)
        suffix = m.group(4)
        try:
            return (int(major), int(minor), int(patch), suffix)
        except Exception:
            return None

    def is_compatible(self, installed: str | None, required_min: str | None) -> bool:
        if required_min is None or installed is None:
            return True
        pi = self.parse(installed)
        pr = self.parse(required_min)
        if pi is None or pr is None:
            return True
        return pi[:3] >= pr[:3]

