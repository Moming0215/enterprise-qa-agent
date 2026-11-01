import os
import subprocess
import sys
from pathlib import Path


def test_cli_prints_utf8_even_with_legacy_console_encoding(tmp_path):
    root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "input.json"
    input_path.write_text('{"question":"每周可以在家办公几天？"}', encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "cp936"}
    result = subprocess.run([sys.executable, "-m", "src.cli", "--input", str(input_path), "--mode", "mock"],
                            cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert "远程办公" in result.stdout.decode("utf-8")
