import unittest

from manifest import Manifest
from manifest_tar import ManifestTarWalker
from test_utils import t_path, TEST_TARS, Manifest_from_walking_unpacked_tar

class Test_Manifest_from_tar(unittest.TestCase):

    def setUp(self):
        self.mtw = ManifestTarWalker(Manifest)

    def must_equal(self, tar_path, expect):
        self.assertEqual(self.mtw.build(t_path(tar_path)), expect)

    def test_missing_raises_ValueError(self):
        self.assertRaises(Exception, self.mtw.build, t_path("missing.tar"))

    def test_not_a_tar(self):
        self.assertRaises(Exception, self.mtw.build, t_path("not_tar"))

    def test_empty_dir(self):
        self.must_equal("empty.tar", {})

    def test_single_file(self):
        self.must_equal("single_file.tar", {"foo": {}})

    def test_two_files(self):
        self.must_equal("two_files.tar", {"foo": {}, "bar": {}})

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir.tar", {"file": {}, "subdir": {}})

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar",
                        {"file": {}, "subdir": {"foo": {}}})

    def test_file_and_subdir_at_subdir(self):
        m = self.mtw.build(t_path("file_and_subdir.tar"), "./subdir/")
        self.assertEqual(m, {"foo": {}})

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar", {
            "foo": {},
            "bar": {},
            "baz": {
                "foo": {},
                "bar": {},
                "baz": {"foo": {}, "bar": {}, "baz": {}}
            }
        })

    def test_files_at_many_levels_at_subdir(self):
        m = self.mtw.build(t_path("files_at_many_levels.tar"), "./baz/")
        self.assertEqual(m, {
            "foo": {}, "bar": {}, "baz": { "foo": {}, "bar": {}, "baz": {} } })

    def test_from_tar_against_walking_unpacked_tars(self):
        for tar in TEST_TARS:
            m_walk = Manifest_from_walking_unpacked_tar(tar)
            m_tar = self.mtw.build(tar)
            self.assertEqual(m_tar, m_walk)

class Test_Manifest_from_tar_w_attrs(unittest.TestCase):

    empty_sha1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    empty_attrs = { "size": 0, "sha1": empty_sha1 }

    def must_equal(self, tar_path, expect, expect_attrs, attrkeys = None):
        if attrkeys is None:
            attrkeys = ["size", "sha1"]
        m = ManifestTarWalker().build(t_path(tar_path), attrkeys = attrkeys)
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
                         "subdir": {}})

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar",
                        {"file": {}, "subdir": {"foo": {}}},
                        {"file": self.empty_attrs,
                         "subdir": {},
                         "subdir/foo": self.empty_attrs})

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar",
                        {"foo": {}, "bar": {}, "baz":
                             {"foo": {}, "bar": {}, "baz":
                                  {"foo": {}, "bar": {}, "baz": {}}}},
                        {"foo": self.empty_attrs,
                         "bar": self.empty_attrs,
                         "baz": {},
                         "baz/foo": self.empty_attrs,
                         "baz/bar": self.empty_attrs,
                         "baz/baz": {},
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
                "sha1": "fc6da897c87c7b9c3b67d1d5af32085e561db793" },
            "bar": {},
            "bar/baz": {
                "size": 12,
                "sha1": "7508a86c26bcda1d3f298f67de33f7c48a3fe047" },
            "symlink_to_bar_baz": {},
        })

if __name__ == '__main__':
    unittest.main()
