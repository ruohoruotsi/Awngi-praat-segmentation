import os

import pytest


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


AUDIO_1203 = os.path.join(repo_root(), "audio", "1203_spm37_intervocalic.WAV")
GRID_1203_STUDENT = os.path.join(repo_root(), "audio", "1203_spm37_intervocalic.TextGrid")


@pytest.fixture(scope="session")
def seg_output(tmp_path_factory):
    """Run the real pipeline once on 1203 into a temp out dir."""
    if not os.path.exists(AUDIO_1203):
        pytest.skip("sample audio not present")
    from pipeline.__main__ import main

    out_root = tmp_path_factory.mktemp("out")
    main(["segment", AUDIO_1203, "--out", str(out_root)])
    return os.path.join(str(out_root), "1203_spm37_intervocalic")


@pytest.fixture(scope="session")
def student_grid():
    if not os.path.exists(GRID_1203_STUDENT):
        pytest.skip("student TextGrid not present")
    from pipeline.textgrid import read_grid

    return read_grid(GRID_1203_STUDENT)
