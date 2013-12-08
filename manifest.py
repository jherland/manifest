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
        """Return (indent, token) for each logical line in the given file.

        The given file 'f' may be anything that can be iterated to yield lines.
        """
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
        """Parse the given file and return the resulting toplevel Manifest.

        The given file 'f' may be anything that can be iterated to yield lines.
        """
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
