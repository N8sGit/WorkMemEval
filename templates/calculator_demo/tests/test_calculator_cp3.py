from calculator import Calculator


def test_calculator_class():
    calc = Calculator()
    assert calc.add(10, 5) == 15
    assert calc.multiply(3, 4) == 12
