import tarfile
import stat
import hashlib

from manifest_builder import ManifestBuilder

def mode_from_tarinfo(tf, ti):
    ret = ti.mode
    if ti.isfifo():
        ret |= stat.S_IFIFO
    elif ti.ischr():
        ret |= stat.S_IFCHR
    elif ti.isdir():
        ret |= stat.S_IFDIR
    elif ti.isblk():
        ret |= stat.S_IFBLK
    elif ti.isreg():
        ret |= stat.S_IFREG
    elif ti.issym():
        ret |= stat.S_IFLNK
    else:
        raise ValueError("Cannot deduce mode from %s/%s" % (tf, ti))
    return ret

def sha1_from_tarinfo(tf, ti):
    if ti.isfile():
        return hashlib.sha1(tf.extractfile(ti).read()).hexdigest()
    return None

class ManifestTarWalker(ManifestBuilder):
    """Walk the contents of a tar file to generate a Manifest."""

    attr_handlers = {
        # name: handler (tarfile, tarinfo -> parsed value)
        "mode": mode_from_tarinfo,
        "size": lambda tf, ti: ti.size if ti.isfile() else None,
        "sha1": sha1_from_tarinfo,
    }

    def supported_attrs(self):
        return self.attr_handlers.keys()

    def find_attrs(self, tf, ti, attrkeys):
        if not attrkeys:
            return {}

        attrs = {}
        for k in attrkeys:
            v = self.attr_handlers[k](tf, ti)
            if v is not None:
                attrs[k] = v
        return attrs

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
            attrs = self.find_attrs(tf, ti, attrkeys)
            rel_path = ti.name[len(subdir):]
            top.add(rel_path.split('/'), attrs)
        tf.close()
        return top
