import unittest

from manifest import Manifest
from manifest_dir import ManifestDirWalker
from test_utils import t_path, unpacked_tar, Manifest_from_walking_unpacked_tar

class Test_ManifestDirWalker(unittest.TestCase):

    def setUp(self):
        self.mdw = ManifestDirWalker(Manifest)

    def must_equal(self, tar_path, expect):
        m = Manifest_from_walking_unpacked_tar(tar_path)
        self.assertEqual(m, expect)

    def test_missing_raises_ValueError(self):
        self.assertRaises(ValueError, self.mdw.build, t_path("missing"))

    def test_not_a_dir(self):
        self.assertRaises(ValueError, self.mdw.build, t_path("plain_file"))

    def test_empty_dir(self):
        self.must_equal("empty.tar", {})

    def test_empty_dir_trailing_slash(self):
        with unpacked_tar("empty.tar") as d:
            m = self.mdw.build(d + "/")
        self.assertEqual(m, {})

    def test_single_file(self):
        self.must_equal("single_file.tar", {"foo": {}})

    def test_two_files(self):
        self.must_equal("two_files.tar", {"foo": {}, "bar": {}})

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir.tar", {"file": {}, "subdir": {}})

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar",
                        {"file": {}, "subdir": {"foo": {}}})

    def test_file_and_subdir_trailing_slash(self):
        with unpacked_tar("file_and_subdir.tar") as d:
            m = self.mdw.build(d + "/")
        self.assertEqual(m, {"file": {}, "subdir": {"foo": {}}})

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar",{
            "foo": {},
            "bar": {},
            "baz": {
                "foo": {},
                "bar": {},
                "baz": {"foo": {}, "bar": {}, "baz": {}}
            }
        })

    def test_files_with_contents(self):
        self.must_equal("files_with_contents.tar",{
            "foo": {},
            "bar": {"baz": {}},
            "symlink_to_bar_baz": {},
        })

class Test_ManifestDirWalker_w_attrs(unittest.TestCase):

    empty_sha1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    empty_attrs = { "mode": 0o100644, "size": 0, "sha1": empty_sha1 }
    dir_attrs = { "mode": 0o040755 }

    def must_equal(self, tar_path, expect, expect_attrs, attrkeys = None):
        if attrkeys is None:
            attrkeys = ["size", "sha1", "mode"]
        m = Manifest_from_walking_unpacked_tar(tar_path, attrkeys)
        self.assertEqual(m, expect)
        for path, e_attrs in expect_attrs.items():
            self.assertEqual(m.resolve(path).getattrs(), e_attrs)

    def test_empty_dir(self):
        self.must_equal("empty.tar", {}, {})

    def test_single_file_attrs_none(self):
        self.must_equal("single_file.tar", {"foo": {}}, {"foo": {}}, [])

    def test_single_file_attrs_size(self):
        self.must_equal("single_file.tar",
                        {"foo": {}},
                        {"foo": { "size": 0 }},
                        ["size"])

    def test_single_file_attrs_sha1(self):
        self.must_equal("single_file.tar",
                        {"foo": {}},
                        {"foo": { "sha1": self.empty_sha1 }},
                        ["sha1"])

    def test_single_file_attrs_mode(self):
        self.must_equal("single_file.tar",
                        {"foo": {}},
                        {"foo": { "mode": 0o100644 }},
                        ["mode"])

    def test_single_file(self):
        self.must_equal("single_file.tar",
                        {"foo": {}},
                        {"foo": self.empty_attrs})

    def test_two_files(self):
        self.must_equal("two_files.tar",
                        {"foo": {}, "bar": {}},
                        {"foo": self.empty_attrs,
                         "bar": self.empty_attrs})

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir.tar",
                        {"file": {}, "subdir": {}},
                        {"file": self.empty_attrs,
                         "subdir": self.dir_attrs})

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar",
                        {"file": {}, "subdir": {"foo": {}}},
                        {"file": self.empty_attrs,
                         "subdir": self.dir_attrs,
                         "subdir/foo": self.empty_attrs})

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar",
                        {"foo": {}, "bar": {}, "baz":
                             {"foo": {}, "bar": {}, "baz":
                                  {"foo": {}, "bar": {}, "baz": {}}}},
                        {"foo": self.empty_attrs,
                         "bar": self.empty_attrs,
                         "baz": self.dir_attrs,
                         "baz/foo": self.empty_attrs,
                         "baz/bar": self.empty_attrs,
                         "baz/baz": self.dir_attrs,
                         "baz/baz/foo": self.empty_attrs,
                         "baz/baz/bar": self.empty_attrs,
                         "baz/baz/baz": self.empty_attrs})

    def test_files_with_contents(self):
        self.must_equal("files_with_contents.tar", {
            "foo": {},
            "bar": {"baz": {}},
            "symlink_to_bar_baz": {}
        }, {
            "foo": {
                "size": 12,
                "sha1": "fc6da897c87c7b9c3b67d1d5af32085e561db793",
                "mode": 0o100644 },
            "bar": self.dir_attrs,
            "bar/baz": {
                "size": 12,
                "sha1": "7508a86c26bcda1d3f298f67de33f7c48a3fe047",
                "mode": 0o100644 },
            "symlink_to_bar_baz": {
                "mode": 0o120777 },
        })

if __name__ == '__main__':
    unittest.main()
