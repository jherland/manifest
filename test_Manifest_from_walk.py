import unittest

from manifest import Manifest
from test_utils import t_path, unpacked_tar, Manifest_from_walking_unpacked_tar

class Test_Manifest_from_walk(unittest.TestCase):

    def must_equal(self, tar_path, expect):
        m = Manifest_from_walking_unpacked_tar(tar_path)
        self.assertEqual(m, expect)

    def test_missing_raises_ValueError(self):
        self.assertRaises(ValueError, Manifest.from_walk, t_path("missing"))

    def test_not_a_dir(self):
        self.assertRaises(ValueError, Manifest.from_walk, t_path("plain_file"))

    def test_empty_dir(self):
        self.must_equal("empty.tar", {})

    def test_empty_dir_trailing_slash(self):
        with unpacked_tar("empty.tar") as d:
            m = Manifest.from_walk(d + "/")
        self.assertEqual(m, {})

    def test_single_file(self):
        self.must_equal("single_file.tar", {"foo": {}})

    def test_two_files(self):
        self.must_equal("two_files.tar", {"foo": {}, "bar": {}})

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir.tar", {"file": {}, "subdir": {}})

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar",
                        {"file": {}, "subdir": {"foo": {}}})

    def test_file_and_subdir_trailing_slash(self):
        with unpacked_tar("file_and_subdir.tar") as d:
            m = Manifest.from_walk(d + "/")
        self.assertEqual(m, {"file": {}, "subdir": {"foo": {}}})

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar",{
            "foo": {},
            "bar": {},
            "baz": {
                "foo": {},
                "bar": {},
                "baz": {"foo": {}, "bar": {}, "baz": {}}
            }
        })

if __name__ == '__main__':
    unittest.main()
