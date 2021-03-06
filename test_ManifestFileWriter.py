import unittest
try:
    from cStringIO import StringIO # Most python2
except ImportError:
    try:
        from StringIO import StringIO # Some python2
    except ImportError:
        from io import StringIO # python3

from manifest import Manifest
from manifest_file import ManifestFileParser, ManifestFileWriter

class Test_ManifestFileWriter(unittest.TestCase):

    def must_equal(self, lines, expect, *args, **kwargs):
        m = ManifestFileParser().build(lines)
        s = StringIO()
        ManifestFileWriter().write(m, s, *args, **kwargs)
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

    def test_entries_w_parsed_attrs(self):
        self.must_equal(
            ["foo {}", "\tbar {size:123}", "\t\tbaz { xyzzy : zyxxy , a : b }"],
            "foo\n\tbar {size: 123}\n\t\tbaz {a: b, xyzzy: zyxxy}\n")

    def test_entries_w_direct_attrs(self):
        m = Manifest()
        m.add(["foo"], {"uid": 1234, "gid": 321})
        m.add(["foo", "bar"], {"size": 123, "mode": 0o040755})
        m.add(["foo", "bar", "baz"], {"xyzzy": "z", "a": "b", "mode": 0o100644})
        s = StringIO()
        ManifestFileWriter().write(m, s, indent = "    ")
        self.assertEqual(s.getvalue(), """\
foo {gid: 321, uid: 1234}
    bar {mode: 0o040755, size: 123}
        baz {a: b, mode: 0o100644, xyzzy: z}
""")

if __name__ == '__main__':
    unittest.main()
