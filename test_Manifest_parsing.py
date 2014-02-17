import unittest
try:
    from cStringIO import StringIO # Most python2
except ImportError:
    try:
        from StringIO import StringIO # Some python2
    except ImportError:
        from io import StringIO # python3

from manifest import Manifest

class Test_Manifest_parse_lines(unittest.TestCase):

    def must_equal(self, input_string, expect):
        stream = Manifest.parse_lines(StringIO(input_string))
        self.assertEqual(list(stream), expect)

    def must_raise(self, input_string, exception):
        stream = Manifest.parse_lines(StringIO(input_string))
        self.assertRaises(exception, list, stream)

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

class Test_Manifest_parse(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main()
