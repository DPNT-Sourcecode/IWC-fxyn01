from lib.solutions.HLO.hello_solution import HelloSolution


class TestHello():

    def test_hello(self):
        assert HelloSolution().hello("anything") == "Hello, anything!"

    def test_different_name(self):
        assert HelloSolution().hello("John") == "Hello, John!"