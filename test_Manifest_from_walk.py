import unittest
import os
from cStringIO import StringIO

from manifest import Manifest
from test_utils import t_path, Manifest_from_tar

class Test_Manifest_from_walk(unittest.TestCase):

    def must_equal(self, path, expect):
        m = Manifest.from_walk(t_path(path))
        s = StringIO()
        m.write(s)
        self.assertEqual(s.getvalue(), expect)

    def test_missing_raises_ValueError(self):
        self.assertRaises(ValueError, Manifest.from_walk, t_path("missing"))

    def test_not_a_dir(self):
        self.assertRaises(ValueError, Manifest.from_walk, t_path("plain_file"))

    def test_empty_dir(self):
        emptydir = t_path("empty")
        if not os.path.exists(emptydir):
            os.makedirs(emptydir)
        self.must_equal("empty", "")

    def test_empty_dir_trailing_slash(self):
        emptydir = t_path("empty")
        if not os.path.exists(emptydir):
            os.makedirs(emptydir)
        self.must_equal("empty/", "")

    def test_single_file(self):
        self.must_equal("single_file", "foo\n")

    def test_two_files(self):
        self.must_equal("two_files", "bar\nfoo\n")

    def test_file_and_empty_subdir(self):
        emptydir = t_path("file_and_empty_subdir/subdir")
        if not os.path.exists(emptydir):
            os.makedirs(emptydir)
        self.must_equal("file_and_empty_subdir", "file\nsubdir\n")

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir", "file\nsubdir\n\tfoo\n")

    def test_file_and_subdir_trailing_slash(self):
        self.must_equal("file_and_subdir/", "file\nsubdir\n\tfoo\n")

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels",
            "bar\nbaz\n\tbar\n\tbaz\n\t\tbar\n\t\tbaz\n\t\tfoo\n\tfoo\nfoo\n")

    def must_equal_tar(self, tar_path, expect):
        m = Manifest_from_tar(tar_path)
        s = StringIO()
        m.write(s)
        self.assertEqual(s.getvalue(), expect)

    def test_empty_tar(self):
        self.must_equal_tar("empty.tar", "")

    def test_single_file_tar(self):
        self.must_equal_tar("single_file.tar", "foo\n")

    def test_two_files_tar(self):
        self.must_equal_tar("two_files.tar", "bar\nfoo\n")

    def test_file_and_empty_subdir_tar(self):
        self.must_equal_tar("file_and_empty_subdir.tar", "file\nsubdir\n")

    def test_file_and_subdir_tar(self):
        self.must_equal_tar("file_and_subdir.tar", "file\nsubdir\n\tfoo\n")

    def test_files_at_many_levels_tar(self):
        self.must_equal_tar("files_at_many_levels.tar",
            "bar\nbaz\n\tbar\n\tbaz\n\t\tbar\n\t\tbaz\n\t\tfoo\n\tfoo\nfoo\n")

if __name__ == '__main__':
    unittest.main()
