#!/usr/bin/env python2

import sys
import os
import unittest
from cStringIO import StringIO

from manifest import Manifest

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

class TestManifest_from_walk(unittest.TestCase):

    testdir = os.path.join(os.path.dirname(sys.argv[0]), "t")

    def tpath(self, path):
        return os.path.join(self.testdir, path)

    def must_equal(self, path, expect):
        m = Manifest.walk(self.tpath(path))
        s = StringIO()
        m.write(s)
        self.assertEqual(s.getvalue(), expect)

    def test_missing_raises_ValueError(self):
        self.assertRaises(ValueError, Manifest.walk, self.tpath("missing"))

    def test_not_a_dir(self):
        self.assertRaises(ValueError, Manifest.walk, self.tpath("plain_file"))

    def test_empty_dir(self):
        emptydir = self.tpath("empty")
        if not os.path.exists(emptydir):
            os.makedirs(emptydir)
        self.must_equal("empty", "")


if __name__ == '__main__':
    unittest.main()
