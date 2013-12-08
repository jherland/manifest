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
            if indent > level: # drill into the previous entry
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

    @classmethod
    def walk(cls, path):
        """Generate a Manifest from the given directory structure.

        Recursively walk the directory structure rooted at 'path' and generate
        a Manifest tree that mirrors the structure. Return the top Manifest
        object, which corresponding to 'path'.
        """
        import os
        if not os.path.isdir(path):
            raise ValueError("'%s' is not a directory" % (path))

        top, top_path = cls(), path.rstrip(os.sep)
        for dirpath, dirnames, filenames in os.walk(path):
            assert dirpath.startswith(top_path)
            rel_path = dirpath[len(top_path):].lstrip(os.sep)
            m = top.resolve(rel_path)
            assert m is not None

            for name in filenames + dirnames:
                assert name not in m
                new = m.setdefault(name, cls())
                new.setparent(m)
        return top

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._parent = None

    def getparent(self):
        return self._parent() if self._parent is not None else None

    def setparent(self, manifest):
        self._parent = weakref.ref(manifest) if manifest is not None else None

    def write(self, f, level = 0, indent = "\t"):
        """Write this Manifest in parse()able text format to the given file."""
        for name, m in sorted(self.iteritems()):
            print >>f, indent * level + name
            m.write(f, level + 1, indent)

    def resolve(self, path):
        """Resolve a relative pathspec against this Manifest."""
        try:
            name, rest = path.split("/", 1)
        except ValueError:
            name, rest = path, ""

        special = {
            "": self,
            ".": self,
            "..": self.getparent(),
        }
        m = special.get(name, self.get(name))
        return m.resolve(rest) if (m is not None and rest) else m

    def iterpaths(self):
        """Generate relative paths from this manifests and all its children."""
        for p, m in sorted(self.iteritems()):
            yield p
            for c in m.iterpaths():
                yield p + "/" + c

    @classmethod
    def merge(cls, *args):
        """Generate sequence of matching path tuples from multiple manifests.

        The given arguments are one or more Manifests (ma, mb, mc, ...). For
        each given manifest mx call .iterpaths() to generate a sequence of
        relative paths. Merge these paths across manifests, into a sorted
        sequence of tuples (pa, pb, pc, ...), where each px is either a path
        from the corresponding Manifest mx, or None if the corresponding mx
        does not contain that path. For a given tuple in the result sequence,
        all present items (i.e. those that are not None) will be identical, and
        there will be at least one present item. The total length of the
        resulting sequence is equal to the length of the superset of the given
        Manifests. All elements from all manifests will occur exactly once in
        the generated sequence.
        """
        def next_or_none(gen):
            try:
                return next(gen)
            except StopIteration:
                return None

        exists = lambda p: p is not None

        gens = [m.iterpaths() for m in args]
        paths = [next_or_none(gen) for gen in gens]
        while filter(exists, paths):
            least = min(filter(exists, paths))
            ret, next_paths = [], []
            for p, gen in zip(paths, gens):
                if p == least:
                    ret.append(p)
                    next_paths.append(next_or_none(gen))
                else:
                    ret.append(None)
                    next_paths.append(p)
            assert filter(exists, ret)
            yield tuple(ret)
            paths = next_paths

    @classmethod
    def diff(cls, *args):
        """Generate sequence of differences between two or more manifests.

        For the given manifests (ma, mb, mc, ...), generate a sequence of tuples
        (pa, pb, pc, ...) whenever a path px is encountered that is not present
        in all manifests. This is equivalent to filtering merge() for tuples
        where all px are present.
        """
        for t in cls.merge(*args):
            if filter(lambda p: p is None, t): # One or more is None
                yield t

    @classmethod
    def mindiff(cls, *args):
        """Generate the minimal sequence of differences between manifests.

        This is the same as above, except when differences are found, we don't
        drill into those diffs to generate everything beneath as additional
        diffs.
        """
        def next_or_none(gen):
            try:
                return next(gen)
            except StopIteration:
                return None

        exists = lambda p: p is not None
        entry_key = lambda e: e[0] if e is not None else None

        print "\nmindiff:", ", ".join([repr(a) for a in args])
        gens = [iter(sorted(m.iteritems())) for m in args]
        entries = [next_or_none(gen) for gen in gens]
        while filter(exists, entries):
            print "  entries:", ", ".join([repr(e) for e in entries])
            least = min([entry_key(e) for e in entries if e])
            print "  least:", least
            ret, next_entries = [], []
            for entry, gen in zip(entries, gens):
                if entry_key(entry) == least:
                    ret.append(entry)
                    next_entries.append(next_or_none(gen))
                else:
                    ret.append(None)
                    next_entries.append(entry)
            found = len(filter(exists, ret))
            assert found > 0
            if found > 1: # Drill down
                print "  -> drill into %s" % (repr(ret)) # TODO
            else:
                yield tuple(map(entry_key, ret))
            entries = next_entries
