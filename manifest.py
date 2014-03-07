import weakref

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

    @classmethod
    def parse(cls, f):
        """Parse the given file and return the resulting toplevel Manifest.

        The given file 'f' may be anything that can be iterated to yield lines.
        """
        from manifest_file import ManifestFileParser
        return ManifestFileParser(cls).build(f)

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
        from manifest_dir import ManifestDirWalker
        return ManifestDirWalker(cls).build(path, attrkeys)

    @classmethod
    def from_tar(cls, tarpath, subdir = "./", attrkeys = None):
        """Generate a Manifest from the given tar file.

        The given 'tarpath' filename is processed (using python's built-in
        tarfile module), and a new manifest is built (and returned) based on
        the contents of the tar archive.
        """
        from manifest_tar import ManifestTarWalker
        return ManifestTarWalker(cls).build(tarpath, subdir, attrkeys)

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._parent = None
        self._attrs = {}

    def add(self, path, attrs = None):
        """Add the given path (a list of components) to this manifest."""
        try:
            component = path.pop(0)
        except IndexError:
            raise ValueError("Cannot add null path")
        if not component:
            raise ValueError("Cannot add empty path component")

        if path: # not a leaf entry
            if component not in self: # non-leafs must already exist in manifest
                raise ValueError("Cannot add child before parent")
            return self[component].add(path, attrs)
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

    def getattrs(self):
        return self._attrs.copy()

    def setattrs(self, attrs):
        self._attrs = dict(attrs)

    def write(self, f, level = 0, indent = "\t", attrkeys = None):
        """Write this Manifest in parse()able text format to the given file.

        'attrkeys' is the set of attributes to be output, defaults to all.
        """
        from manifest_file import ManifestFileWriter
        ManifestFileWriter().write(self, f, level, indent, attrkeys)

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
        """Analogue to os.walk(). Yield (path, entries, attrs) recursively.

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
        yield path, names, self.getattrs() # Caller may modify names
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
        for path, names, attrs in self.walk():
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
