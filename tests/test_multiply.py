import unittest
from audiogen import util

class TestVectorOperations(unittest.TestCase):
  def test_multiply(self):
    self.assertEqual(
                    list(util.multiply(iter([2, 2, 2]), iter([1, 2, 3]))),
                    [2, 4, 6]
                    )
  def test_sum(self):
    self.assertEqual(
                    list(util.sum(iter([2, 2, 2]), iter([1, 2, 3]))),
                    [3, 4, 5]
                    )

if __name__ == '__main__':
  unittest.main()
