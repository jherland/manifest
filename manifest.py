#!/usr/bin/env python2

import weakref

class Manifest(dict):
    """Encapsulate a description of a file hierarchy.

    This is equivalent to a hierachical dictionary, where each key is an entry
    (i.e. file or direcotry) in the file hierachy, and the corresponding value
    is the Manifest object representing the children of that entry.

    In addition to merely wrapping a dict of Manifest objects, each Manifest
    also has a parent attribute that references the Manifest object of the
    parent (or None for a toplevel Manifest object).
    """

    @staticmethod
    def parse_lines(f):
        """Return (indent, token) for each logical line in the given file."""
        indents = [0] # Stack of indent levels. Initial 0 is always present
        for linenum, line in enumerate(f):
            # Strip trailing newline, strip comment to EOL, and s/tab/spaces/
            line = line.rstrip("\n").split('#', 1)[0].replace("\t", " " * 8)
            token = line.lstrip(" ") # Token starts after indent
            if not token: # blank line
                continue

            indent = len(line) - len(token) # Indent is #spaces stripped above
            if indent > indents[-1]: # Increasing indent
                indents.append(indent)
            elif indent < indents[-1]: # Decreasing indent
                while indent < indents[-1]:
                    indents.pop()
                if indent != indents[-1]:
                    raise ValueError("Broken indent at line %d in %s: level "
                        "%d != %d" % (linenum, getattr(f, "name", "<unknown>"),
                                      indent, indents[-1]))

            token = token.rstrip() # strip trailing WS
            yield(len(indents) - 1, token)

    @classmethod
    def parse(cls, f):
        """Parse the given file and return the resulting toplevel Manifest."""
        prev = cur = top = cls()
        level = 0
        for indent, token in cls.parse_lines(f):
            if indent > level:
                # drill into the previous entry
                cur = prev
                level += 1
                assert indent == level
            elif indent < level:
                while indent < level:
                    cur = cur.getparent()
                    assert cur is not None
                    level -= 1
                assert indent == level

            assert token not in cur
            prev = cur.setdefault(token, cls())
            prev.setparent(cur)
        return top

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._parent = None

    def getparent(self):
        return self._parent() if self._parent is not None else None

    def setparent(self, manifest):
        self._parent = weakref.ref(manifest) if manifest is not None else None

# Tests start here

import unittest
from cStringIO import StringIO

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

class TestManifest_parse(unittest.TestCase):

    def test_empty(self):
        m = Manifest.parse(StringIO(""))
        self.assertEqual(len(m), 0)

    def test_single_word(self):
        m = Manifest.parse(StringIO("foo"))
        self.assertEqual(len(m), 1)
        self.assertEqual(m.keys(), ["foo"])
        self.assertEqual(len(m["foo"]), 0)

    def test_two_word(self):
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
