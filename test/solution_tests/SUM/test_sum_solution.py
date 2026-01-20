from lib.solutions.SUM.sum_solution import SumSolution


class TestSum():
    def test_sum(self):
        assert SumSolution().compute(1, 2) == 3

    def test_larger_number(self):
        assert SumSolution().compute(100008, 200009) == 300017