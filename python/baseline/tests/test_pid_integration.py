from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_pid.py"
SPEC_PATH = ROOT / "biochar_pid_spec.yml"

spec = importlib.util.spec_from_file_location("generate_pid", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_generate_two_sheet_outputs(tmp_path):
    out_dxf = tmp_path / "pid.dxf"
    out_svg = tmp_path / "pid.svg"

    mod.generate(str(SPEC_PATH), str(out_dxf), str(out_svg), sheet_set="two", profile="presentation")

    assert out_dxf.exists()
    assert out_svg.exists()
    assert (tmp_path / "pid_controls.dxf").exists()
    assert (tmp_path / "pid_controls.svg").exists()
