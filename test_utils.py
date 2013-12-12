import os
from contextlib import contextmanager
import tempfile
import subprocess
import shutil

# Absolute path to t/ subdir
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "t")

def t_path(path):
    """Return absolute path to 'path' inside t/."""
    return os.path.join(TEST_DIR, path)

@contextmanager
def unpacked_tar(tar_path):
    try:
        tempdir = tempfile.mkdtemp()
        subprocess.check_call(["tar", "-xf", t_path(tar_path)], cwd = tempdir)
        yield tempdir
    finally:
        shutil.rmtree(tempdir)

def Manifest_from_tar(tar_path):
    from manifest import Manifest
    with unpacked_tar(tar_path) as d:
        return Manifest.from_walk(d)
