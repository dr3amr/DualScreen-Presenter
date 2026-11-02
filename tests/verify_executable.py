"""Verify the built executable's subsystem, icon, modules, and runtime assets."""

from pathlib import Path
import os
import subprocess
import tempfile
import sys

import pefile
from PyInstaller.archive.readers import CArchiveReader


project_dir = Path(__file__).resolve().parents[1]
exe_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else project_dir / "dist/DualScreenPresenter.exe"
pe = pefile.PE(str(exe_path))
assert pe.OPTIONAL_HEADER.Subsystem == 2, "Expected Windows GUI subsystem (no console)"
resource_types = {entry.id for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries}
assert {3, 14}.issubset(resource_types), "Missing Windows icon resources"
pe.close()

archive = CArchiveReader(str(exe_path))
entries = {name.replace("\\", "/"): name for name in archive.toc}
assert archive.extract(entries["app_icon.ico"]) == (project_dir / "app_icon.ico").read_bytes()
assert archive.extract(entries["assets/checkbox-check.svg"]) == (project_dir / "assets/checkbox-check.svg").read_bytes()
assert archive.extract(entries["assets/dropdown-arrow.svg"]) == (project_dir / "assets/dropdown-arrow.svg").read_bytes()
for asset in (project_dir / "sample_media").iterdir():
    if asset.is_file():
        name = "sample_media/" + asset.name
        assert archive.extract(entries[name]) == asset.read_bytes(), f"Asset mismatch: {name}"

for suffix in (
    "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Multimedia.dll",
    "platforms/qwindows.dll", "multimedia/ffmpegmediaplugin.dll",
):
    assert any(name.endswith(suffix) for name in entries), f"Missing Qt dependency: {suffix}"
assert any("avcodec" in name and name.endswith(".dll") for name in entries)

pyz = archive.open_embedded_archive("PYZ.pyz")
for module in ("preview_widget", "presenter_app", "projector_window", "media_manager", "styles"):
    assert module in pyz.toc, f"Missing application module: {module}"

print(f"Verified {exe_path.name}: Windows GUI subsystem, embedded icon, application modules,")
print("bundled sample media, Qt runtime, Windows platform plugin, and FFmpeg backend.")
print(f"Size: {exe_path.stat().st_size / (1024 * 1024):.1f} MiB")

# Archive contents alone cannot detect an incompatible DLL pulled from PATH.
# Launch the actual executable and require a marker written after the GUI starts.
with tempfile.TemporaryDirectory() as directory:
    marker = Path(directory) / "startup.txt"
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    with (Path(directory) / "startup.log").open("w+b") as log:
        process = subprocess.Popen(
            [str(exe_path), "--smoke-test", str(marker)],
            env=env, stdout=log, stderr=log,
        )
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            # The one-file bootloader owns a child process; clean up only this tree.
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
            )
            process.wait(timeout=5)
            raise AssertionError("Packaged application did not finish startup smoke test")
        log.seek(0)
        output = log.read().decode(errors="replace")
        assert process.returncode == 0, f"Packaged startup failed: {output}"
        assert marker.is_file(), f"GUI initialization marker missing: {output}"
        assert marker.read_text().strip() == "GUI initialized successfully"
print("Verified actual executable startup, GUI initialization, event loop, and clean exit.")
