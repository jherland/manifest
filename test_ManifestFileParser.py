import unittest
try:
    from cStringIO import StringIO # Most python2
except ImportError:
    try:
        from StringIO import StringIO # Some python2
    except ImportError:
        from io import StringIO # python3

from manifest import Manifest
from manifest_file import ManifestFileParser

class Test_ManifestFileParser_parse_lines(unittest.TestCase):

    def setUp(self):
        self.mfp = ManifestFileParser()

    def must_equal(self, input_string, expect):
        stream = self.mfp.parse_lines(StringIO(input_string))
        self.assertEqual(list(stream), expect)

    def must_raise(self, input_string, exception):
        stream = self.mfp.parse_lines(StringIO(input_string))
        self.assertRaises(exception, list, stream)

    def test_empty(self):
        self.must_equal("", [])

    def test_comment_line(self):
        self.must_equal("    # This is a comment", [])

    def test_single_word(self):
        self.must_equal("foo", [(0, "foo", {})])

    def test_line_with_comment(self):
        self.must_equal("foo # comment", [(0, "foo", {})])

    def test_two_entries(self):
        self.must_equal("foo\nbar", [(0, "foo", {}), (0, "bar", {})])

    def test_simple_indent(self):
        self.must_equal("foo\n\tbar", [(0, "foo", {}), (1, "bar", {})])

    def test_increasing_indent(self):
        self.must_equal("foo\n\tbar\n\t baz",
                        [(0, "foo", {}), (1, "bar", {}), (2, "baz", {})])

    def test_decreasing_indent(self):
        self.must_equal("foo\n\tbar\n\t baz\n\txyzzy",
                        [(0, "foo", {}), (1, "bar", {}), (2, "baz", {}),
                         (1, "xyzzy", {})])

    def test_multidecreasing_indent(self):
        self.must_equal("foo\n\tbar\n\t baz\nxyzzy",
                        [(0, "foo", {}), (1, "bar", {}), (2, "baz", {}),
                         (0, "xyzzy", {})])

    def test_broken_indent(self):
        self.must_raise("foo\n\tbar\n\t baz\n  xyzzy", ValueError)

    def test_empty_lines(self):
        self.must_equal("\n   \n  foo   \n #comment line\n\t\t\n",
                        [(1, "foo", {})])

    def test_empty_lines_and_comments_between_indents(self):
        self.must_equal("foo\n\tbar\n#comment line\n\n\t\t\t\n\nbaz\n\t\n#foo",
                        [(0, "foo", {}), (1, "bar", {}), (0, "baz", {})])

    def test_token_with_spaces(self):
        self.must_equal("This is a token with spaces",
                        [(0, "This is a token with spaces", {})])

    def test_token_with_spaces(self):
        self.must_equal("This is a token with spaces",
                        [(0, "This is a token with spaces", {})])

    def test_list_of_strings(self):
        stream = self.mfp.parse_lines(["foo", "bar", "\tbaz", "\t    xyzzy"])
        self.assertEqual(list(stream), [(0, "foo", {}), (0, "bar", {}),
                                        (1, "baz", {}), (2, "xyzzy", {})])

    def test_empty_attrs(self):
        self.must_equal("foo {}", [(0, "foo", {})])

    def test_size_attr(self):
        self.must_equal("foo {size: 1}", [(0, "foo", {"size": 1})])

    def test_two_attrs(self):
        sha1 = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        self.must_equal("foo {size: 1, sha1: %s}" % (sha1),
                        [(0, "foo", {"size": 1, "sha1": sha1})])

    def test_sha1_attr_lowered(self):
        sha1 = "deadbeefDEADBEEFdeadbeefdeadbeefdeadbeef"
        self.must_equal("foo {size: 1, sha1: %s}" % (sha1),
                        [(0, "foo", {"size": 1, "sha1": sha1.lower()})])

    def test_unknown_attr(self):
        self.must_equal("foo { bar : baz }", [(0, "foo", {"bar": "baz"})])

class Test_ManifestFileParser_build(unittest.TestCase):

    def setUp(self):
        self.mfp = ManifestFileParser()

    def test_empty(self):
        m = self.mfp.build(StringIO(""))
        self.assertEqual(m, {})

    def test_single_word(self):
        m = self.mfp.build(StringIO("foo"))
        self.assertEqual(m, {"foo": {}})

    def test_two_words(self):
        m = self.mfp.build(StringIO("foo\nbar"))
        self.assertEqual(m, {"foo": {}, "bar": {}})

    def test_entry_with_child(self):
        m = self.mfp.build(StringIO("foo\n\tbar"))
        self.assertEqual(m, {"foo": {"bar": {}}})

    def test_entry_with_children(self):
        m = self.mfp.build(StringIO("foo\n\tbar\n\tbaz"))
        self.assertEqual(m, {"foo": {"bar": {}, "baz": {}}})

    def test_entry_with_child_and_sibling(self):
        m = self.mfp.build(StringIO("foo\n\tbar\nfooz"))
        self.assertEqual(m, {"foo": {"bar": {}}, "fooz": {}})

    def test_entry_with_grandchild(self):
        m = self.mfp.build(StringIO("foo\n\tbar\n\t\tbaz"))
        self.assertEqual(m, {"foo": {"bar": {"baz": {}}}})

    def test_entry_with_grandchild_and_sibling(self):
        m = self.mfp.build(StringIO("foo\n\tbar\n\t\tbaz\nxyzzy"))
        self.assertEqual(m, {"foo": {"bar": {"baz": {}}}, "xyzzy": {}})

    def test_parent_refs(self):
        m = self.mfp.build(StringIO("foo\n\tbar"))
        self.assertEqual(m, {"foo": {"bar": {}}})
        self.assertEqual(m.getparent(), None)
        self.assertEqual(m["foo"].getparent(), m)
        self.assertEqual(m["foo"]["bar"].getparent(), m["foo"])

    def test_empty_attrs(self):
        m = self.mfp.build(["foo {}"])
        self.assertEqual(m, {"foo": {}})
        self.assertEqual(m["foo"].getattrs(), {})

    def test_unknown_attr(self):
        m = self.mfp.build(["foo {bar: baz}"])
        self.assertEqual(m, {"foo": {}})
        self.assertEqual(m["foo"].getattrs(), { "bar": "baz"})

    def test_size_attr(self):
        m = self.mfp.build(["foo {size: 1}"])
        self.assertEqual(m, {"foo": {}})
        self.assertEqual(m["foo"].getattrs(), {"size": 1})

    def test_invalid_size_attr_raises(self):
        self.assertRaises(ValueError, self.mfp.build, ["foo {size: bar}"])
        self.assertRaises(ValueError, self.mfp.build, ["foo {size: -1}"])

    def test_two_attrs(self):
        sha1 = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        m = self.mfp.build(["foo {size: 1, sha1: %s}" % (sha1)])
        self.assertEqual(m, {"foo": {}})
        self.assertEqual(m["foo"].getattrs(), {"size": 1, "sha1": sha1})

    def test_sha1_attr_lowered(self):
        sha1 = "deadbeefDEADBEEFdeadbeefdeadbeefdeadbeef"
        m = self.mfp.build(["foo {size: 1, sha1: %s}" % (sha1)])
        self.assertEqual(m, {"foo": {}})
        self.assertEqual(m["foo"].getattrs(), {"size": 1, "sha1": sha1.lower()})

    def test_invalid_sha1_attr_raises(self):
        self.assertRaises(ValueError, self.mfp.build, ["foo {sha1: not_hex}"])
        self.assertRaises(ValueError, self.mfp.build, ["foo {sha1: 123}"]) # <40

    def test_mode_Xid_attr(self):
        m = self.mfp.build(["foo { mode: 0o100644, uid: 1000, gid: 100 }"])
        self.assertEqual(m, {"foo": {}})
        self.assertEqual(m["foo"].getattrs(),
                         {"mode": 0o100644, "uid": 1000, "gid": 100})

    def test_invalid_mode_Xid_attr_raises(self):
        self.assertRaises(ValueError, self.mfp.build, ["foo {mode: not_int}"])
        self.assertRaises(ValueError, self.mfp.build, ["foo {uid: -13}"])
        self.assertRaises(ValueError, self.mfp.build, ["foo {gid: 0x123foo}"])

if __name__ == '__main__':
    unittest.main()
