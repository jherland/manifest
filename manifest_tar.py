import tarfile
import hashlib

from manifest_builder import ManifestBuilder

def size_from_tarinfo(tf, ti):
    if ti.isfile():
        return ti.size
    return None

def sha1_from_tarinfo(tf, ti):
    if ti.isfile():
        f = tf.extractfile(ti)
        return hashlib.sha1(f.read()).hexdigest()
    return None

class ManifestTarWalker(ManifestBuilder):
    """Walk the contents of a tar file to generate a Manifest."""

    attr_handlers = {
        # name: handler (tarfile, tarinfo -> parsed value)
        "size": size_from_tarinfo,
        "sha1": sha1_from_tarinfo,
    }

    def supported_attrs(self):
        return self.attr_handlers.keys()

    def build(self, tarpath, subdir = "./", attrkeys = None):
        """Generate a Manifest from the given tar file.

        The given 'tarpath' filename is processed (using python's built-in
        tarfile module), and a new manifest is built (and returned) based on
        the contents of the tar archive.
        """
        # In python2.6, TarFile objects are not context managers, so we cannot
        # do "with tarfile.open(...) as tf:". Also, in python2.6 a TarFile's
        # .errorlevel defaults to 0, whereas later versions default to 1.
        if attrkeys is not None:
            for k in attrkeys:
                assert k in self.attr_handlers
        else:
            attrkeys = self.supported_attrs()

        tf = tarfile.open(tarpath, errorlevel=1)
        top = self.manifest_class()
        for ti in tf:
            if not ti.name.startswith(subdir):
                continue
            attrs = {}
            for k in attrkeys:
                v = self.attr_handlers[k](tf, ti)
                if v is not None:
                    attrs[k] = v
            rel_path = ti.name[len(subdir):]
            top.add(rel_path.split('/'), attrs)
        tf.close()
        return top
