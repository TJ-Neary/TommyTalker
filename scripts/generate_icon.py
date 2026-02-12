#!/usr/bin/env python3
"""
Generate TommyTalker app icon (.icns) from programmatic rendering.

Creates the TT icon at all required sizes and bundles into .icns format
using macOS iconutil. Output: resources/TommyTalker.icns

Usage:
    python scripts/generate_icon.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def generate_icon_png(size: int, output_path: str) -> None:
    """Generate a TT icon PNG at the specified size."""
    # Import PyQt6 here so the script fails fast with a clear message
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
    from PyQt6.QtCore import Qt, QRect

    # QApplication required for QPainter
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    # White filled rounded square
    corner_radius = max(size // 5, 4)
    margin = max(size // 32, 1)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255))
    painter.drawRoundedRect(margin, margin, size - 2 * margin, size - 2 * margin,
                            corner_radius, corner_radius)

    # TT letters in dark color
    font_size = max(size // 2, 8)
    font = QFont("Helvetica Neue", font_size, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(30, 30, 30))
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "TT")

    painter.end()
    pixmap.save(output_path, "PNG")


def main():
    project_root = Path(__file__).parent.parent
    resources_dir = project_root / "resources"
    resources_dir.mkdir(exist_ok=True)

    # macOS iconset requires these specific sizes
    icon_sizes = [16, 32, 64, 128, 256, 512, 1024]

    with tempfile.TemporaryDirectory() as tmpdir:
        iconset_dir = Path(tmpdir) / "TommyTalker.iconset"
        iconset_dir.mkdir()

        for size in icon_sizes:
            # Standard resolution
            filename = f"icon_{size}x{size}.png"
            generate_icon_png(size, str(iconset_dir / filename))

            # @2x (Retina) for sizes up to 512
            if size <= 512:
                retina_size = size * 2
                filename_2x = f"icon_{size}x{size}@2x.png"
                generate_icon_png(retina_size, str(iconset_dir / filename_2x))

        # Convert iconset to .icns using macOS iconutil
        icns_path = resources_dir / "TommyTalker.icns"
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"iconutil failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        print(f"Icon generated: {icns_path}")


if __name__ == "__main__":
    main()
