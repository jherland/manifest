import unittest
try:
    from cStringIO import StringIO # Most python2
except ImportError:
    try:
        from StringIO import StringIO # Some python2
    except ImportError:
        from io import StringIO # python3

from manifest import Manifest

class Test_Manifest_write(unittest.TestCase):

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

class Test_Manifest_resolve(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main()
