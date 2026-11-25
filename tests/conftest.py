import os

import pytest


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


GRID_1203_STUDENT = os.path.join(repo_root(), "audio", "1203_spm37_intervocalic.TextGrid")


@pytest.fixture(scope="session")
def student_grid():
    if not os.path.exists(GRID_1203_STUDENT):
        pytest.skip("student TextGrid not present")
    from src.textgrid import read_grid

    return read_grid(GRID_1203_STUDENT)
