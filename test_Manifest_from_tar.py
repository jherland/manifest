import unittest

from manifest import Manifest
from test_utils import t_path, TEST_TARS, Manifest_from_walking_unpacked_tar

class Test_Manifest_from_tar(unittest.TestCase):

    def must_equal(self, tar_path, expect):
        self.assertEqual(Manifest.from_tar(t_path(tar_path)), expect)

    def test_missing_raises_ValueError(self):
        self.assertRaises(Exception, Manifest.from_tar, t_path("missing.tar"))

    def test_not_a_tar(self):
        self.assertRaises(Exception, Manifest.from_tar, t_path("not_tar"))

    def test_empty_dir(self):
        self.must_equal("empty.tar", {})

    def test_single_file(self):
        self.must_equal("single_file.tar", {"foo": {}})

    def test_two_files(self):
        self.must_equal("two_files.tar", {"foo": {}, "bar": {}})

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir.tar", {"file": {}, "subdir": {}})

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar",
                        {"file": {}, "subdir": {"foo": {}}})

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar", {
            "foo": {},
            "bar": {},
            "baz": {
                "foo": {},
                "bar": {},
                "baz": {"foo": {}, "bar": {}, "baz": {}}
            }
        })

    def test_from_tar_against_walking_unpacked_tars(self):
        for tar in TEST_TARS:
            m_walk = Manifest_from_walking_unpacked_tar(tar)
            m_tar = Manifest.from_tar(tar)
            self.assertEqual(m_tar, m_walk)

if __name__ == '__main__':
    unittest.main()
