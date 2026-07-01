"""Scans local VST3 install paths for plugins the user can pick from upstream.

VST3 bundles (Linux/macOS layout) may ship a Contents/moduleinfo.json (VST3 SDK
>= 3.7.4) with real vendor/class/category metadata. When present we parse it;
otherwise we fall back to deriving a name from the bundle filename so the
plugin still shows up in the catalog (flagged as unverified).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PluginClass:
    name: str
    category: str
    cid: str | None = None  # 32-char hex VST3 class ID, needed to write a .vstpreset for this class


@dataclass
class PluginInfo:
    id: str
    bundle_path: str
    name: str
    vendor: str
    classes: list[PluginClass] = field(default_factory=list)
    metadata_source: str = "moduleinfo.json"


def _read_moduleinfo(bundle: Path) -> dict | None:
    for candidate in (
        bundle / "Contents" / "moduleinfo.json",
        bundle / "Contents" / "Resources" / "moduleinfo.json",
    ):
        if candidate.is_file():
            try:
                return json.loads(candidate.read_text())
            except (json.JSONDecodeError, OSError):
                return None
    return None


def _plugin_from_moduleinfo(bundle: Path, info: dict) -> PluginInfo:
    factory = info.get("Factory Info", {})
    classes = [
        PluginClass(name=c.get("Name", "Unknown"), category=c.get("Category", "Unknown"), cid=c.get("CID"))
        for c in info.get("Classes", [])
    ]
    return PluginInfo(
        id=bundle.stem,
        bundle_path=str(bundle),
        name=classes[0].name if classes else bundle.stem,
        vendor=factory.get("Vendor", "Unknown"),
        classes=classes,
        metadata_source="moduleinfo.json",
    )


def _plugin_from_filename(bundle: Path) -> PluginInfo:
    return PluginInfo(
        id=bundle.stem,
        bundle_path=str(bundle),
        name=bundle.stem,
        vendor="Unknown",
        classes=[],
        metadata_source="filename-fallback",
    )


def audio_module_cid(info: PluginInfo) -> str | None:
    """The class ID a .vstpreset needs for this plugin's main audio
    processor -- moduleinfo.json labels it Category == "Audio Module Class"."""
    for c in info.classes:
        if c.category == "Audio Module Class" and c.cid:
            return c.cid
    return info.classes[0].cid if info.classes else None


def scan_paths(paths: list[str]) -> list[PluginInfo]:
    found: list[PluginInfo] = []
    for raw_path in paths:
        root = Path(raw_path)
        if not root.is_dir():
            continue
        for entry in sorted(root.rglob("*.vst3")):
            if entry.is_dir():
                info = _read_moduleinfo(entry)
                found.append(_plugin_from_moduleinfo(entry, info) if info else _plugin_from_filename(entry))
            elif entry.is_file():
                found.append(_plugin_from_filename(entry))
    return found
