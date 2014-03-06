from __future__ import print_function
import weakref
import os
import re
import hashlib

class AttributeHandler(object):
    name = None

    def parse(self, s):
        raise NotImplementedError

    def from_path(self, path):
        raise NotImplementedError

class SizeHandler(AttributeHandler):
    name = "size"
    parse = int

    def from_path(self, path):
        if os.path.isfile(path):
            return os.path.getsize(path)
        return None # we consider non-files to have no size

class SHA1Handler(AttributeHandler):
    name = "sha1"
    sha1RE = re.compile(r'^[0-9a-f]{40}$')

    def parse(self, s):
        sha1 = s.strip().lower()
        if not self.sha1RE.match(sha1):
            raise ValueError("Not a valid SHA1 sum: '%s'" % (s))
        return sha1

    def from_path(self, path):
        if os.path.isfile(path):
            with open(path, "rb") as f:
                return hashlib.sha1(f.read()).hexdigest()
        return None # we consider non-files to have no SHA1

class Manifest(dict):
    """Encapsulate a description of a file hierarchy.

    This is equivalent to a hierarchical dictionary, where each key is an entry
    (i.e. file or direcotry) in the file hierarchy, and the corresponding value
    is the Manifest object representing the children of that entry.

    In addition to merely wrapping a dict of Manifest objects, each Manifest
    also has a ._parent member that (weakly) references the Manifest object of
    the parent (or None for a toplevel Manifest object).

    Finally, each Manifest also has a ._attrs member which is a dictionary of
    attributes that apply to that Manifest. The dictionary is fundamentally
    open/free-form, but there are some attributes (e.g. 'size' and 'sha1') that
    carry special meaning.
    """

    KnownAttrs = {}
    for handler in [SizeHandler, SHA1Handler]:
        KnownAttrs[handler.name] = handler()

    @classmethod
    def parse_attr(cls, key_s, value_s):
        """Canonicalize the given attribute key and value strings."""
        key = key_s.strip().lower()
        val = value_s.strip()
        if key in cls.KnownAttrs:
            val = cls.KnownAttrs[key].parse(val)
        return (key, val)

    @classmethod
    def parse_token(cls, token):
        """Parse the given token into a (entry, attrs) tuple.

        A token consists of an entry (file/directory name) and an optional
        collection of attributes that apply to that entry. The general format
        of a token is thus:
            token_name WS* { attr_key: attr_val, attr_key: attr_val, ... }
        """
        # The final '{' separates the entry from the attributes
        try:
            entry, attr_s = token.rsplit('{', 1)
        except ValueError: # no attributes
            return (token, {})

        assert attr_s.endswith('}')
        attrs = {}
        for s in attr_s[:-1].split(','):
            if not s.strip():
                continue
            k, v = cls.parse_attr(*s.split(':', 1))
            attrs[k] = v

        return (entry.rstrip(), attrs)

    @classmethod
    def parse_lines(cls, f):
        """Return (indent, token, attrs) for each logical line in 'f'.

        The given 'f' may be anything that can be iterated to yield lines, e.g.
        a file object, a StringIO object, a list of lines, etc.
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
            token, attrs = cls.parse_token(token) # split attrs out of token
            yield(len(indents) - 1, token, attrs)

    @classmethod
    def parse(cls, f):
        """Parse the given file and return the resulting toplevel Manifest.

        The given file 'f' may be anything that can be iterated to yield lines.
        """
        prev = cur = top = cls()
        level = 0
        for indent, token, attrs in cls.parse_lines(f):
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

            prev = cur._add([token], attrs)
        return top

    @classmethod
    def from_walk(cls, path, attrkeys = None):
        """Generate a Manifest from the given directory structure.

        Recursively walk the directory structure rooted at 'path' and generate
        a Manifest tree that mirrors the structure. Return the top Manifest
        object, which corresponding to 'path'.

        The optional 'attrkeys' specifies a set of known attributes to be
        populated in the generated manifest. This set must be a subset of
        KnownAttrs.keys().
        """
        if attrkeys:
            for k in attrkeys:
                assert k in cls.KnownAttrs.keys()
        else:
            attrkeys = set()

        if not os.path.isdir(path):
            raise ValueError("'%s' is not a directory" % (path))

        top, top_path = cls(), path.rstrip(os.sep)
        for dirpath, dirnames, filenames in os.walk(path):
            assert dirpath.startswith(top_path)
            rel_path = dirpath[len(top_path):].lstrip(os.sep)
            components = rel_path.split(os.sep) if rel_path else []
            for name in filenames + dirnames:
                attrs = {}
                fullpath = os.path.join(dirpath, name)
                for k in attrkeys:
                    v = cls.KnownAttrs[k].from_path(fullpath)
                    if v is not None:
                        attrs[k] = v
                top._add(components + [name], attrs)
        return top

    @classmethod
    def from_tar(cls, tarpath, subdir = "./"):
        """Generate a Manifest from the given tar file.

        The given 'tarpath' filename is processed (using python's built-in
        tarfile module), and a new manifest is built (and returned) based on
        the contents of the tar archive.
        """
        # In python2.6, TarFile objects are not context managers, so we cannot
        # do "with tarfile.open(...) as tf:". Also, in python2.6 a TarFile's
        # .errorlevel defaults to 0, whereas later versions default to 1.
        import tarfile
        tf = tarfile.open(tarpath, errorlevel=1)
        top = cls()
        for ti in tf:
            if not ti.name.startswith(subdir):
                continue
            rel_path = ti.name[len(subdir):]
            top._add(rel_path.split('/'))
        tf.close()
        return top

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._parent = None
        self._attrs = {}

    def _add(self, path, attrs = None):
        """Add the given path (a list of components) to this manifest."""
        component = path.pop(0)
        if path: # not a leaf entry
            assert component in self # non-leafs must already exist in manifest
            return self[component]._add(path, attrs)
        assert component not in self
        new = self.setdefault(component, self.__class__())
        new.setparent(self)
        if attrs:
            new._attrs = attrs
        return new

    def getparent(self):
        return self._parent() if self._parent is not None else None

    def setparent(self, manifest):
        self._parent = weakref.ref(manifest) if manifest is not None else None

    def write(self, f, level = 0, indent = "\t"):
        """Write this Manifest in parse()able text format to the given file."""
        for name, m in sorted(self.items()):
            print(indent * level + name, file=f)
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

    def walk(self, path = None):
        """Analogue to os.walk(). Yield (path, entries) for each node in tree.

        The path is itself a list of path components navigating the manifest
        hierarchy. Join them with "/" as separator to get a relative path from
        the top-level manifest.
        The entries list contains the immediate sub-entries located at the
        corresponding path. The list may be modified by the caller to affect
        further walking.
        """
        if path is None:
            path = []
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

        paths = [next(gen) for gen in gens] # first line of contestants
        while any(p is not None for p in paths): # there are contestants left
            ticket = min(key(p) for p in paths if p is not None) # perform draw
            winners = [(p if key(p) == ticket else None) for p in paths]
            assert any(p is not None for p in winners) # at least one winner
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
            t = next(merged_entries)
            while True:
                if any(True for p in t if p is None): # One or more is None
                    yield t
                    t = next(merged_entries)
                else: # All manifests match on this entry. Drill down
                    t = merged_entries.send(True) # Recurse into this node/path
        except StopIteration:
            pass
