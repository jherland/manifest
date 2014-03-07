import os
import hashlib

from manifest_builder import ManifestBuilder

def size_from_path(path):
    if os.path.isfile(path) and not os.path.islink(path):
        return os.path.getsize(path)
    return None # we consider non-files to have no size

def sha1_from_path(path):
    if os.path.isfile(path) and not os.path.islink(path):
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    return None # we consider non-files to have no SHA1

class ManifestDirWalker(ManifestBuilder):
    """Walk a directory structure to generate a Manifest."""

    attr_handlers = {
        # name: handler (full path -> parsed value)
        "size": size_from_path,
        "sha1": sha1_from_path,
    }

    def supported_attrs(self):
        return self.attr_handlers.keys()

    def build(self, path, attrkeys = None):
        """Generate a Manifest from the directory structure rooted at 'path'.

        Recursively walk the directory structure under 'path' and generate a
        Manifest tree that mirrors the structure. Return the top Manifest
        object, which corresponding to 'path'.

        The optional 'attrkeys' specifies a set of known attributes to be
        populated in the generated manifest. This set must be a subset of
        supported_attrs().
        """
        if attrkeys is not None:
            for k in attrkeys:
                assert k in self.attr_handlers
        else:
            attrkeys = self.supported_attrs()

        if not os.path.isdir(path):
            raise ValueError("'%s' is not a directory" % (path))

        top = self.manifest_class()
        top_path = path.rstrip(os.sep)
        for dirpath, dirnames, filenames in os.walk(path):
            assert dirpath.startswith(top_path)
            rel_path = dirpath[len(top_path):].lstrip(os.sep)
            components = rel_path.split(os.sep) if rel_path else []
            for name in filenames + dirnames:
                attrs = {}
                fullpath = os.path.join(dirpath, name)
                for k in attrkeys:
                    v = self.attr_handlers[k](fullpath)
                    if v is not None:
                        attrs[k] = v
                top.add(components + [name], attrs)
        return top
