#!/usr/bin/env python2

import sys
import os
import unittest
from cStringIO import StringIO
import tempfile
import shutil
import subprocess
import glob

from manifest import Manifest

# Absolute path to t/ subdir
TEST_DIR = os.path.normpath(os.path.join(
    os.getcwd(), os.path.dirname(sys.argv[0]), "t"))

def t_path(path):
    """Return absolute path to 'path' inside t/."""
    return os.path.join(TEST_DIR, path)

class TestManifest_parse_lines(unittest.TestCase):

    # Helpers

    def must_equal(self, input_string, expect):
        stream = Manifest.parse_lines(StringIO(input_string))
        self.assertEqual(list(stream), expect)

    def must_raise(self, input_string, exception):
        stream = Manifest.parse_lines(StringIO(input_string))
        self.assertRaises(exception, list, stream)

    # Test methods

    def test_empty(self):
        self.must_equal("", [])

    def test_comment_line(self):
        self.must_equal("    # This is a comment", [])

    def test_single_word(self):
        self.must_equal("foo", [(0, "foo")])

    def test_line_with_comment(self):
        self.must_equal("foo # comment", [(0, "foo")])

    def test_two_entries(self):
        self.must_equal("foo\nbar", [(0, "foo"), (0, "bar")])

    def test_simple_indent(self):
        self.must_equal("foo\n\tbar", [(0, "foo"), (1, "bar")])

    def test_increasing_indent(self):
        self.must_equal("foo\n\tbar\n\t baz",
                        [(0, "foo"), (1, "bar"), (2, "baz")])

    def test_decreasing_indent(self):
        self.must_equal("foo\n\tbar\n\t baz\n\txyzzy",
                        [(0, "foo"), (1, "bar"), (2, "baz"), (1, "xyzzy")])

    def test_multidecreasing_indent(self):
        self.must_equal("foo\n\tbar\n\t baz\nxyzzy",
                        [(0, "foo"), (1, "bar"), (2, "baz"), (0, "xyzzy")])

    def test_broken_indent(self):
        self.must_raise("foo\n\tbar\n\t baz\n  xyzzy", ValueError)

    def test_empty_lines(self):
        self.must_equal("\n   \n  foo   \n #comment line\n\t\t\n",
                        [(1, "foo")])

    def test_empty_lines_and_comments_between_indents(self):
        self.must_equal("foo\n\tbar\n#comment line\n\n\t\t\t\n\nbaz\n\t\n#foo",
                        [(0, "foo"), (1, "bar"), (0, "baz")])

    def test_token_with_spaces(self):
        self.must_equal("This is a token with spaces",
                        [(0, "This is a token with spaces")])

    def test_token_with_spaces(self):
        self.must_equal("This is a token with spaces",
                        [(0, "This is a token with spaces")])

    def test_list_of_strings(self):
        stream = Manifest.parse_lines(["foo", "bar", "\tbaz", "\t    xyzzy"])
        self.assertEqual(list(stream),
                         [(0, "foo"), (0, "bar"), (1, "baz"), (2, "xyzzy")])

class TestManifest_parse(unittest.TestCase):

    def test_empty(self):
        m = Manifest.parse(StringIO(""))
        self.assertEqual(len(m), 0)

    def test_single_word(self):
        m = Manifest.parse(StringIO("foo"))
        self.assertEqual(len(m), 1)
        self.assertEqual(m.keys(), ["foo"])
        self.assertEqual(len(m["foo"]), 0)

    def test_two_words(self):
        m = Manifest.parse(StringIO("foo\nbar"))
        self.assertEqual(len(m), 2)
        self.assertEqual(sorted(m.keys()), ["bar", "foo"])
        self.assertEqual(len(m["foo"]), 0)
        self.assertEqual(len(m["bar"]), 0)

    def test_entry_with_child(self):
        m = Manifest.parse(StringIO("foo\n\tbar"))
        self.assertEqual(len(m), 1)
        self.assertEqual(m.keys(), ["foo"])
        self.assertEqual(len(m["foo"]), 1)
        self.assertEqual(m["foo"].keys(), ["bar"])
        self.assertEqual(len(m["foo"]["bar"]), 0)

    def test_entry_with_children(self):
        m = Manifest.parse(StringIO("foo\n\tbar\n\tbaz"))
        self.assertEqual(len(m), 1)
        self.assertEqual(m.keys(), ["foo"])
        self.assertEqual(len(m["foo"]), 2)
        self.assertEqual(sorted(m["foo"].keys()), ["bar", "baz"])
        self.assertEqual(len(m["foo"]["bar"]), 0)
        self.assertEqual(len(m["foo"]["baz"]), 0)

    def test_entry_with_child_and_sibling(self):
        m = Manifest.parse(StringIO("foo\n\tbar\nfooz"))
        self.assertEqual(len(m), 2)
        self.assertEqual(sorted(m.keys()), ["foo", "fooz"])
        self.assertEqual(len(m["foo"]), 1)
        self.assertEqual(sorted(m["foo"].keys()), ["bar"])
        self.assertEqual(len(m["foo"]["bar"]), 0)
        self.assertEqual(len(m["fooz"]), 0)

    def test_entry_with_grandchild(self):
        m = Manifest.parse(StringIO("foo\n\tbar\n\t\tbaz"))
        self.assertEqual(len(m), 1)
        self.assertEqual(m.keys(), ["foo"])
        self.assertEqual(len(m["foo"]), 1)
        self.assertEqual(m["foo"].keys(), ["bar"])
        self.assertEqual(len(m["foo"]["bar"]), 1)
        self.assertEqual(m["foo"]["bar"].keys(), ["baz"])
        self.assertEqual(len(m["foo"]["bar"]["baz"]), 0)

    def test_entry_with_grandchild_and_sibling(self):
        m = Manifest.parse(StringIO("foo\n\tbar\n\t\tbaz\nxyzzy"))
        self.assertEqual(len(m), 2)
        self.assertEqual(sorted(m.keys()), ["foo", "xyzzy"])
        self.assertEqual(len(m["foo"]), 1)
        self.assertEqual(m["foo"].keys(), ["bar"])
        self.assertEqual(len(m["foo"]["bar"]), 1)
        self.assertEqual(m["foo"]["bar"].keys(), ["baz"])
        self.assertEqual(len(m["foo"]["bar"]["baz"]), 0)
        self.assertEqual(len(m["xyzzy"]), 0)

    def test_parent_refs(self):
        m = Manifest.parse(StringIO("foo\n\tbar"))
        self.assertEqual(len(m), 1)
        self.assertEqual(m.keys(), ["foo"])
        self.assertEqual(len(m["foo"]), 1)
        self.assertEqual(m["foo"].keys(), ["bar"])
        self.assertEqual(len(m["foo"]["bar"]), 0)
        self.assertEqual(m.getparent(), None)
        self.assertEqual(m["foo"].getparent(), m)
        self.assertEqual(m["foo"]["bar"].getparent(), m["foo"])

class TestManifest_write(unittest.TestCase):

    def must_equal(self, lines, expect, *args, **kwargs):
        m = Manifest.parse(lines)
        s = StringIO()
        m.write(s, *args, **kwargs)
        self.assertEqual(s.getvalue(), expect)

    def test_empty(self):
        self.must_equal("", "")

    def test_single_entry(self):
        self.must_equal(["foo"], "foo\n")

    def test_multiple_entries_are_sorted(self):
        self.must_equal(["foo", "bar", "baz"], "bar\nbaz\nfoo\n")

    def test_entry_with_child(self):
        self.must_equal(["foo", "\tbar"], "foo\n\tbar\n")

    def test_entry_with_grandchild(self):
        self.must_equal(["foo", "\tbar", "\t\tbaz"], "foo\n\tbar\n\t\tbaz\n")

    def test_supply_indent(self):
        self.must_equal(["foo", "\tbar", "\t\tbaz"], "foo\n--bar\n----baz\n",
                        indent = "--")

    def test_supply_level(self):
        self.must_equal(["foo", "\tbar", "\t\tbaz"],
                        "XXXfoo\nXXXXbar\nXXXXXbaz\n", indent = "X", level = 3)

class TestManifest_resolve(unittest.TestCase):

    def test_empty(self):
        m = Manifest()
        self.assertTrue(m.resolve("") is m)

    def test_single_entry(self):
        m = Manifest.parse(["foo"])
        self.assertTrue(m.resolve("") is m)
        self.assertTrue(m.resolve("foo") is m["foo"])

    def test_missing_is_None(self):
        m = Manifest.parse(["foo"])
        self.assertTrue(m.resolve("bar") is None)

    def test_grandchild(self):
        m = Manifest.parse(["foo", "\tbar"])
        self.assertTrue(m.resolve("") is m)
        self.assertTrue(m.resolve("foo") is m["foo"])
        self.assertTrue(m.resolve("foo/bar") is m["foo"]["bar"])

    def test_dot_path(self):
        m = Manifest.parse(["foo", "\tbar"])
        self.assertTrue(m.resolve("./foo") is m["foo"])
        self.assertTrue(m.resolve("foo/./") is m["foo"])
        self.assertTrue(m.resolve("foo/./bar") is m["foo"]["bar"])
        self.assertTrue(m.resolve("./foo/./bar/.") is m["foo"]["bar"])
        self.assertTrue(m.resolve("./foo/./bar/./") is m["foo"]["bar"])

    def test_dotdot_path(self):
        m = Manifest.parse(["foo", "\tbar"])
        self.assertTrue(m.resolve("foo/..") is m)
        self.assertTrue(m.resolve("foo/../foo") is m["foo"])
        self.assertTrue(m.resolve("foo/../foo/bar") is m["foo"]["bar"])
        self.assertTrue(m.resolve("./foo/./bar/..") is m["foo"])
        self.assertTrue(m.resolve("./foo/bar/../") is m["foo"])
        self.assertTrue(m.resolve("./foo/bar/../..") is m)

    def test_excessive_dotdot_fails(self):
        m = Manifest.parse(["foo", "\tbar"])
        self.assertTrue(m.resolve("..") is None)
        self.assertTrue(m.resolve("../") is None)
        self.assertTrue(m.resolve("foo/../..") is None)
        self.assertTrue(m.resolve("foo/bar/../../..") is None)
        self.assertTrue(m.resolve("foo/bar/../bar/../../..") is None)

class TestManifest_from_walk(unittest.TestCase):

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
        try:
            tempdir = tempfile.mkdtemp()
            subprocess.check_call(["tar", "-xf", t_path(tar_path)],
                                  cwd = tempdir)
            m = Manifest.from_walk(tempdir)
            s = StringIO()
            m.write(s)
            self.assertEqual(s.getvalue(), expect)
        finally:
            shutil.rmtree(tempdir)

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

class TestManifest_walk_visits_all_paths(unittest.TestCase):

    def check_visited_paths(self, path, expect):
        m = Manifest.from_walk(t_path(path))
        self.assertEquals(map(lambda t: "/".join(t[0]), m.walk()), expect)

    def test_empty(self):
        self.check_visited_paths("empty", [""])

    def test_single_file(self):
        self.check_visited_paths("single_file", ["", "foo"])

    def test_two_files(self):
        self.check_visited_paths("two_files", ["", "bar", "foo"])

    def test_file_and_empty_subdir(self):
        self.check_visited_paths("file_and_empty_subdir",
                                 ["", "file", "subdir"])

    def test_file_and_subdir(self):
        self.check_visited_paths("file_and_subdir",
                                 ["", "file", "subdir", "subdir/foo"])

    def test_file_and_subdir_trailing_slash(self):
        self.check_visited_paths("file_and_subdir/",
                                 ["", "file", "subdir", "subdir/foo"])

    def test_files_at_many_levels(self):
        self.check_visited_paths("files_at_many_levels", [
            "",
            "bar",
            "baz",
            "baz/bar",
            "baz/baz",
            "baz/baz/bar",
            "baz/baz/baz",
            "baz/baz/foo",
            "baz/foo",
            "foo",
        ])

    def test_nonrecursive(self):
        m = Manifest.parse("""\
            foo
                child1
                child2
            bar
            baz
                child3
            """.split("\n"))
        result = []
        for path, names in m.walk():
            result.append("/".join(path))
            del names[:]
        self.assertEquals(result, [""])
        result = []
        for path, names in m.walk():
            result.append("/".join(path))
            if path:
                del names[:]
        self.assertEquals(result, ["", "bar", "baz", "foo"])

class TestManifest_iterpaths(unittest.TestCase):

    def must_equal(self, path, expect):
        m = Manifest.from_walk(t_path(path))
        self.assertEquals(list(m.iterpaths()), expect)

    def test_empty(self):
        self.must_equal("empty", [])

    def test_single_file(self):
        self.must_equal("single_file", ["foo"])

    def test_two_files(self):
        self.must_equal("two_files", ["bar", "foo"])

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir", ["file", "subdir"])

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir", ["file", "subdir", "subdir/foo"])

    def test_file_and_subdir_trailing_slash(self):
        self.must_equal("file_and_subdir/", ["file", "subdir", "subdir/foo"])

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels", [
            "bar",
            "baz",
            "baz/bar",
            "baz/baz",
            "baz/baz/bar",
            "baz/baz/baz",
            "baz/baz/foo",
            "baz/foo",
            "foo",
        ])

    def test_nonrecursive(self):
        m = Manifest.parse("""\
            foo
                child1
                child2
            bar
            baz
                child3
            """.split("\n"))
        self.assertEquals(list(m.iterpaths(recursive = False)),
                          ["bar", "baz", "foo"])

class TestManifest_merge(unittest.TestCase):

    def test_nothing(self):
        self.assertEqual(list(Manifest.merge()), [])

    def test_one_empty(self):
        m = Manifest()
        self.assertEqual(list(Manifest.merge(m)), [])

    def test_two_empties(self):
        m1, m2 = Manifest(), Manifest.from_walk(t_path("empty"))
        self.assertEqual(list(Manifest.merge(m1, m2)), [])

    def test_one_single_file(self):
        m = Manifest.from_walk(t_path("single_file"))
        self.assertEqual(list(Manifest.merge(m)), [("foo",)])

    def test_two_single_file(self):
        ms = Manifest.from_walk(t_path("single_file")), Manifest.parse(["foo"])
        self.assertEqual(list(Manifest.merge(*ms)), [("foo", "foo")])

    def test_three_different_singles(self):
        m1, m2, m3 = map(Manifest.parse, (["foo"], ["bar"], ["baz"]))
        self.assertEqual(list(Manifest.merge(m1, m2, m3)), [
            (None, "bar", None), (None, None, "baz"), ("foo", None, None)])

    def test_three_mixed_singles(self):
        m1, m2, m3 = map(Manifest.parse, (["foo"], ["bar"], ["foo"]))
        self.assertEqual(list(Manifest.merge(m1, m2, m3)), [
            (None, "bar", None), ("foo", None, "foo")])

    def test_three_with_overlap(self):
        ms = map(Manifest.parse,
                 (["foo", "same"], ["bar", "same"], ["baz", "same"]))
        self.assertEqual(list(Manifest.merge(*ms)), [
            (None, "bar", None), (None, None, "baz"), ("foo", None, None),
            ("same", "same", "same")])

    def test_empty_subdir_vs_nonepty_subdir(self):
        ms = map(Manifest.from_walk,
                 (t_path("file_and_empty_subdir"), t_path("file_and_subdir")))
        self.assertEqual(list(Manifest.merge(*ms)), [
            ("file", "file"), ("subdir", "subdir"), (None, "subdir/foo")])

class TestManifest_diff(unittest.TestCase):

    def from_tar(self, tar_path):
        try:
            tempdir = tempfile.mkdtemp()
            subprocess.check_call(["tar", "-xf", t_path(tar_path)],
                                  cwd = tempdir)
            return Manifest.from_walk(tempdir)
        finally:
            shutil.rmtree(tempdir)

    def test_diff_empties(self):
        m1 = Manifest()
        m2 = Manifest.from_walk(t_path("empty"))
        m3 = self.from_tar(t_path("empty.tar"))
        self.assertEquals(list(Manifest.diff(m1, m2)), [])
        self.assertEquals(list(Manifest.diff(m1, m3)), [])
        self.assertEquals(list(Manifest.diff(m2, m1)), [])
        self.assertEquals(list(Manifest.diff(m2, m3)), [])
        self.assertEquals(list(Manifest.diff(m3, m1)), [])
        self.assertEquals(list(Manifest.diff(m3, m2)), [])
        self.assertEquals(m1, m2)
        self.assertEquals(m2, m3)
        self.assertEquals(m3, m1)

    def test_diff_tar_and_dirs(self):
        tars = glob.glob(t_path("*.tar"))
        for t in tars:
            d = os.path.splitext(t)[0]
            if not os.path.isdir(d): # Need corresponding dir
                continue
            m1 = Manifest.from_walk(d)
            m2 = self.from_tar(t)
            self.assertEqual(list(Manifest.diff(m1, m2)), [])
            self.assertEqual(list(Manifest.diff(m2, m1)), [])
            self.assertEqual(m1, m2)
            self.assertEqual(m2, m1)

    def test_diff_unlike(self):
        tars = glob.glob(t_path("*.tar"))
        shifted = tars[:]
        shifted.append(shifted.pop(0))
        for t1, t2 in zip(tars, shifted):
            m1 = self.from_tar(t1)
            m2 = self.from_tar(t2)
            self.assertTrue(list(Manifest.diff(m1, m2)))
            self.assertTrue(list(Manifest.diff(m2, m1)))
            self.assertNotEqual(m1, m2)
            self.assertNotEqual(m2, m1)

            self.assertEqual(len(list(Manifest.diff(m1, m2))),
                             len(list(Manifest.diff(m2, m1))))

    def test_diff_empty_vs_single_file(self):
        m1 = self.from_tar("empty.tar")
        m2 = self.from_tar("single_file.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [(None, "foo")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [("foo", None)])

    def test_diff_single_file_vs_two_files(self):
        m1 = self.from_tar("single_file.tar")
        m2 = self.from_tar("two_files.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [(None, "bar")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [("bar", None)])

    def test_diff_two_files_vs_file_and_empty_subdir(self):
        m1 = self.from_tar("two_files.tar")
        m2 = self.from_tar("file_and_empty_subdir.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [
            ("bar", None), (None, "file"), ("foo", None), (None, "subdir")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [
            (None, "bar"), ("file", None), (None, "foo"), ("subdir", None)])

    def test_diff_file_and_empty_subdir_vs_file_and_subdir(self):
        m1 = self.from_tar("file_and_empty_subdir.tar")
        m2 = self.from_tar("file_and_subdir.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [(None, "subdir/foo")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [("subdir/foo", None)])

    def test_diff_two_files_vs_files_at_many_levels(self):
        m1 = self.from_tar("two_files.tar")
        m2 = self.from_tar("files_at_many_levels.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [
            (None, "baz"), (None, "baz/bar"), (None, "baz/baz"),
            (None, "baz/baz/bar"), (None, "baz/baz/baz"), (None, "baz/baz/foo"),
            (None, "baz/foo")])

    def test_min_diff_two_files_vs_files_at_many_levels(self):
        m1 = self.from_tar("two_files.tar")
        m2 = self.from_tar("files_at_many_levels.tar")
        self.assertEqual(list(Manifest.mindiff(m1, m2)), [(None, "baz")])

    def test_min_diff_with_diff_at_muliples_levels(self):
        m1 = Manifest.parse("""\
            1foo
            2bar
                1xyzzy
                    1blah
                2zyxxy
                3diff
            3baz
            """.split("\n"))
        m2 = Manifest.parse("""\
            1foo
            2bar
                1xyzzy
                    1blah
                    2diff
                2zyxxy
            3baz
            4diff
            """.split("\n"))
        #self.assertEqual(list(Manifest.mindiff(m1, m2)), [
            #(None, "2bar/1xyzzy/2diff"),
            #("2bar/3diff", None),
            #(None, "4diff"),
        #])

if __name__ == '__main__':
    unittest.main()
