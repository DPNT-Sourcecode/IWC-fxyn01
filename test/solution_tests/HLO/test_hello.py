from lib.solutions.HLO.hello_solution import HelloSolution


class TestHello():

    def test_hello(self):
        assert HelloSolution().hello("anything") == "hello world"
