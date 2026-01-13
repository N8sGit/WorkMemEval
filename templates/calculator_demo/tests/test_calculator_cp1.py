import pytest
from calculator import add


def test_add_basic():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_add_floats():
    assert pytest.approx(add(2.5, 0.5)) == 3.0
