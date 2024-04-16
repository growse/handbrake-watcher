from pathlib import Path

import PyInstaller.__main__

HERE = Path(__file__).parent.absolute()


def build_converter():
    PyInstaller.__main__.run(
        [
            str(HERE / "converter.py"),
            "--onefile",
        ]
    )


def build_normalizer():
    PyInstaller.__main__.run(
        [
            str(HERE / "normalizer.py"),
            "--onefile",
        ]
    )
