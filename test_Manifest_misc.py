import unittest

from manifest import Manifest
from manifest_file import ManifestFileParser

class Test_Manifest_add(unittest.TestCase):

    def setUp(self):
        self.m = Manifest()

    def test_add_nothing_fails(self):
        self.assertRaises(ValueError, self.m.add, [])
        self.assertEqual(self.m, {})

    def test_add_one(self):
        self.m.add(["foo"])
        self.assertEqual(self.m, {"foo": {}})

    def test_add_two(self):
        self.m.add(["foo"])
        self.m.add(["bar"])
        self.assertEqual(self.m, {"foo": {}, "bar": {}})

    def test_add_sub(self):
        self.m.add(["foo"])
        self.m.add(["foo", "sub"])
        self.assertEqual(self.m, {"foo": {"sub": {}}})

    def test_add_empty_fails(self):
        self.assertRaises(ValueError, self.m.add, [""])
        self.assertEqual(self.m, {})

    def test_add_empty_sub_fails(self):
        self.m.add(["foo"])
        self.assertRaises(ValueError, self.m.add, ["foo", ""])
        self.assertEqual(self.m, {"foo": {}})

    def test_add_sub_without_parent_fails(self):
        self.assertRaises(ValueError, self.m.add, ["foo", "sub"])
        self.assertEqual(self.m, {})

    def test_add_one_w_attrs(self):
        self.m.add(["foo"], {"size": 123, "bar": "baz"})
        self.assertEqual(self.m, {"foo": {}})
        self.assertEqual(self.m["foo"].getattrs(), {"size": 123, "bar": "baz"})

    def test_add_sub_w_attrs(self):
        self.m.add(["foo"], {"blarg": None})
        self.m.add(["foo", "bar"], {"size": 123, "bar": "baz"})
        self.assertEqual(self.m, {"foo": {"bar": {}}})
        self.assertEqual(self.m["foo"].getattrs(), {"blarg": None})
        self.assertEqual(self.m["foo"]["bar"].getattrs(),
                         {"size": 123, "bar": "baz"})

class Test_Manifest_resolve(unittest.TestCase):

    def setUp(self):
        self.mfp = ManifestFileParser()

    def test_empty(self):
        m = Manifest()
        self.assertTrue(m.resolve("") is m)

    def test_single_entry(self):
        m = self.mfp.build(["foo"])
        self.assertTrue(m.resolve("") is m)
        self.assertTrue(m.resolve("foo") is m["foo"])

    def test_missing_is_None(self):
        m = self.mfp.build(["foo"])
        self.assertTrue(m.resolve("bar") is None)

    def test_grandchild(self):
        m = self.mfp.build(["foo", "\tbar"])
        self.assertTrue(m.resolve("") is m)
        self.assertTrue(m.resolve("foo") is m["foo"])
        self.assertTrue(m.resolve("foo/bar") is m["foo"]["bar"])

    def test_dot_path(self):
        m = self.mfp.build(["foo", "\tbar"])
        self.assertTrue(m.resolve("./foo") is m["foo"])
        self.assertTrue(m.resolve("foo/./") is m["foo"])
        self.assertTrue(m.resolve("foo/./bar") is m["foo"]["bar"])
        self.assertTrue(m.resolve("./foo/./bar/.") is m["foo"]["bar"])
        self.assertTrue(m.resolve("./foo/./bar/./") is m["foo"]["bar"])

    def test_dotdot_path(self):
        m = self.mfp.build(["foo", "\tbar"])
        self.assertTrue(m.resolve("foo/..") is m)
        self.assertTrue(m.resolve("foo/../foo") is m["foo"])
        self.assertTrue(m.resolve("foo/../foo/bar") is m["foo"]["bar"])
        self.assertTrue(m.resolve("./foo/./bar/..") is m["foo"])
        self.assertTrue(m.resolve("./foo/bar/../") is m["foo"])
        self.assertTrue(m.resolve("./foo/bar/../..") is m)

    def test_excessive_dotdot_fails(self):
        m = self.mfp.build(["foo", "\tbar"])
        self.assertTrue(m.resolve("..") is None)
        self.assertTrue(m.resolve("../") is None)
        self.assertTrue(m.resolve("foo/../..") is None)
        self.assertTrue(m.resolve("foo/bar/../../..") is None)
        self.assertTrue(m.resolve("foo/bar/../bar/../../..") is None)

if __name__ == '__main__':
    unittest.main()
