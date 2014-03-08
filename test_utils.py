import os
import glob
import tempfile
import subprocess
import shutil
from contextlib import contextmanager

# Absolute path to t/ subdir
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "t")

def t_path(path):
    """Return absolute path to 'path' inside t/."""
    return os.path.join(TEST_DIR, path)

TEST_TARS = glob.glob(t_path("*.tar"))

@contextmanager
def unpacked_tar(tar_path):
    try:
        tempdir = tempfile.mkdtemp()
        subprocess.check_call(["tar", "-xf", t_path(tar_path)], cwd = tempdir)
        yield tempdir
    finally:
        shutil.rmtree(tempdir)

def Manifest_from_walking_unpacked_tar(tar_path, attrkeys = None):
    """Create a Manifest from the given tar file.

    Convenience helper for unpacking the given tar file into a temp dir, and
    then returning the result of ManifestDirWalker.build() on that temp dir.
    """
    from manifest_dir import ManifestDirWalker
    with unpacked_tar(tar_path) as d:
        return ManifestDirWalker().build(d, attrkeys)
