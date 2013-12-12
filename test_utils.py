import os
import tempfile
import subprocess
import shutil

from manifest import Manifest

# Absolute path to t/ subdir
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "t")

def t_path(path):
    """Return absolute path to 'path' inside t/."""
    return os.path.join(TEST_DIR, path)

def Manifest_from_tar(tar_path):
    try:
        tempdir = tempfile.mkdtemp()
        subprocess.check_call(["tar", "-xf", t_path(tar_path)],
                                cwd = tempdir)
        return Manifest.from_walk(tempdir)
    finally:
        shutil.rmtree(tempdir)
