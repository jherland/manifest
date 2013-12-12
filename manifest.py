#!/usr/bin/env python2

import weakref
import itertools

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
    def from_walk(cls, path):
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

    #def __missing__(self, key):
        #return None

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

    def walk(self, path = []):
        """Analogue to os.walk(). Yield (path, entries) for each node in tree.

        The entries list may be changed by the caller to affect further walking.
        """
        names = sorted(self.keys())
        yield path, names # Caller may modify names
        for name in names:
            for x in self[name].walk(path + [name]):
                yield x

    def paths(self, recursive = True, never_stop = False):
        """Generate relative paths from this manifests and all its children.

        The 'recursive' argument determines whether to recurse into child
        nodes by default. The caller may always override the default by
        send()ing True into a yield to force recursion into that node, or
        send()ing False into a yield to force recursion to be skipped for that
        node.

        If 'never_stop' is true, keep yielding None forever instead of raising
        StopIteration. The caller is responsible for aborting the iteration at
        an appropriate time.
        """
        for path, names in self.walk():
            if not path: # skip top-level/empty path
                continue
            recurse = (yield "/".join(path))
            if recurse is None:
                recurse = recursive
            if not recurse:
                del names[:]
        if never_stop:
            while True:
                yield None

    @classmethod
    def merge(cls, *args, **kwargs):
        """Merge walks across multiple manifests.

        The given args are one or more Manifests (ma, mb, mc, ...). For each
        given manifest mx, we call .paths() to generate a sequence of relative
        paths. Merge these paths across manifests (using the given 'key' as a
        sort key), and generate a sorted sequence of tuples (pa, pb, pc, ...),
        where each px is either a path from the corresponding Manifest mx, or
        None if the corresponding mx did not provide a matching path (according
        to the 'key'). For a given tuple in the result sequence, all present
        items (i.e. those that are not None) will be equivalent (according to
        'key'), and there will be at least one present item. The total length
        of the resulting sequence is equal to the length of the superset of the
        given Manifests (again, using 'key' to discern between nodes). All
        elements from all manifests will occur exactly once in the generated
        sequence, and in sorted order.

        If you need to change the default recursive behavior of the manifests'
        .paths() invocation, you can pass the 'recursive' keyword argument.
        You may also send() True/False to a yield to force recursion on/off for
        that set of nodes.
        """
        key = kwargs.get("key", lambda px: px) # use path itself as default key
        recursive = kwargs.get("recursive", True)

        # prevent StopIteration: make all generators repeat None ad infinitum.
        # detect end of overall iteration when _all_ generators return None.
        gens = [m.paths(never_stop = True) for m in args]

        present = lambda p: p is not None # predicate for present entries

        paths = [gen.next() for gen in gens] # first line of contestants
        while filter(present, paths): # there are still contestants left
            ticket = min(key(px) for px in paths if present(px)) # perform draw
            winners = [(p if key(p) == ticket else None) for p in paths]
            assert filter(present, winners) # at least one winner
            recurse = (yield tuple(winners))
            if recurse is None:
                recurse = recursive
            next_round = []
            for w, p, g in zip(winners, paths, gens):
                # if p is a winner, get next round's player from g, else reuse p
                next_round.append(p if w is None else g.send(recurse))
            paths = next_round # prepare for next round

    @classmethod
    def diff(cls, *args, **kwargs):
        """Generate sequence of differences between two or more manifests.

        For the given manifests (ma, mb, mc, ...), generate a sequence of tuples
        (pa, pb, pc, ...) whenever a path px is encountered that is not present
        in all manifests. This is equivalent to filtering merge() for tuples
        where all px are present.

        Use the 'recursive' keyword argument to control whether you get a
        minimal (recursive = False, the default) or maximal (recursive = True)
        diff. A minimal diff does not recurse into an entry which has
        differences, whereas a maximal diff enumerates the entirety of the
        differences between the given manifests. For example, if one manifest
        contains an entry "foo" with a sub-entry "bar", neither of which occurs
        in the other manifest(s), then a minimal diff will stop list only "foo",
        whereas a maximal diff will list both "foo" and "foo/bar".

        As with .merge(), the 'key' keyword argument determines how entries are
        compared, and this very much controls what ends up in the resulting
        diff. The default key simply evaluates to the relative entry path,
        which is probably what you want in most cases.
        """
        kwargs.setdefault('recursive', False) # Default to minimal diff
        try:
            merged_entries = cls.merge(*args, **kwargs)
            t = merged_entries.next()
            while True:
                if filter(lambda p: p is None, t): # One or more is None
                    yield t
                    t = merged_entries.next()
                else: # All manifests match on this entry. Drill down
                    t = merged_entries.send(True) # Recurse into this node/path
        except StopIteration:
            pass
