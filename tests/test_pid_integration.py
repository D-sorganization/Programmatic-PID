from __future__ import annotations

from pathlib import Path

import programmatic_pid.generator as mod

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "examples" / "biochar" / "biochar_pid_spec.yml"


def test_generate_two_sheet_outputs(tmp_path):
    out_dxf = tmp_path / "pid.dxf"
    out_svg = tmp_path / "pid.svg"

    mod.generate(str(SPEC_PATH), str(out_dxf), str(out_svg), sheet_set="two", profile="presentation")

    assert out_dxf.exists()
    assert out_svg.exists()
    assert (tmp_path / "pid_controls.dxf").exists()
    assert (tmp_path / "pid_controls.svg").exists()
