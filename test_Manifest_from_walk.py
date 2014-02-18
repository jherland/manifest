import unittest
try:
    from cStringIO import StringIO # Most python2
except ImportError:
    try:
        from StringIO import StringIO # Some python2
    except ImportError:
        from io import StringIO # python3

from manifest import Manifest
from test_utils import t_path, unpacked_tar, Manifest_from_walking_unpacked_tar

class Test_Manifest_from_walk(unittest.TestCase):

    def must_equal(self, tar_path, expect):
        s = StringIO()
        Manifest_from_walking_unpacked_tar(tar_path).write(s)
        self.assertEqual(s.getvalue(), expect)

    def test_missing_raises_ValueError(self):
        self.assertRaises(ValueError, Manifest.from_walk, t_path("missing"))

    def test_not_a_dir(self):
        self.assertRaises(ValueError, Manifest.from_walk, t_path("plain_file"))

    def test_empty_dir(self):
        self.must_equal("empty.tar", "")

    def test_empty_dir_trailing_slash(self):
        s = StringIO()
        with unpacked_tar("empty.tar") as d:
            Manifest.from_walk(d + "/").write(s)
        self.assertEqual(s.getvalue(), "")

    def test_single_file(self):
        self.must_equal("single_file.tar", "foo\n")

    def test_two_files(self):
        self.must_equal("two_files.tar", "bar\nfoo\n")

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir.tar", "file\nsubdir\n")

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar", "file\nsubdir\n\tfoo\n")

    def test_file_and_subdir_trailing_slash(self):
        s = StringIO()
        with unpacked_tar("file_and_subdir.tar") as d:
            Manifest.from_walk(d + "/").write(s)
        self.assertEqual(s.getvalue(), "file\nsubdir\n\tfoo\n")

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar",
            "bar\nbaz\n\tbar\n\tbaz\n\t\tbar\n\t\tbaz\n\t\tfoo\n\tfoo\nfoo\n")

if __name__ == '__main__':
    unittest.main()
