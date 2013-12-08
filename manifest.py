#!/usr/bin/env python2

import unittest

class Manifest(object):
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


# Tests start here

from cStringIO import StringIO

class TestManifest(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main()
