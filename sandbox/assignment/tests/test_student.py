from test_helper.jactestcase import JACTestCase
import student_file

class Tests(JACTestCase):
    def test_quality(self):
        self.assertCodeQuality(student_file, "student_file.py")

    def test_returns(self):
        self.assertFunctionReturns(student_file.get_parity, "student_file.py")