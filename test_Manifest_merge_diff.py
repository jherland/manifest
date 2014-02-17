import unittest

from manifest import Manifest
from test_utils import TEST_TARS, Manifest_from_tar

class Test_Manifest_merge(unittest.TestCase):

    def test_nothing(self):
        self.assertEqual(list(Manifest.merge()), [])

    def test_one_empty(self):
        m = Manifest()
        self.assertEqual(list(Manifest.merge(m)), [])

    def test_two_empties(self):
        m1, m2 = Manifest(), Manifest_from_tar("empty.tar")
        self.assertEqual(list(Manifest.merge(m1, m2)), [])

    def test_one_single_file(self):
        m = Manifest_from_tar("single_file.tar")
        self.assertEqual(list(Manifest.merge(m)), [("foo",)])

    def test_single_file_x2(self):
        m1 = Manifest_from_tar("single_file.tar")
        m2 = Manifest.parse(["foo"])
        self.assertEqual(list(Manifest.merge(m1, m2)), [("foo", "foo")])

    def test_three_different_singles(self):
        m1, m2, m3 = map(Manifest.parse, (["foo"], ["bar"], ["baz"]))
        self.assertEqual(list(Manifest.merge(m1, m2, m3)), [
            (None, "bar", None), (None, None, "baz"), ("foo", None, None)])

    def test_three_mixed_singles(self):
        m1, m2, m3 = map(Manifest.parse, (["foo"], ["bar"], ["foo"]))
        self.assertEqual(list(Manifest.merge(m1, m2, m3)), [
            (None, "bar", None), ("foo", None, "foo")])

    def test_three_with_overlap(self):
        ms = map(Manifest.parse,
                 (["foo", "same"], ["bar", "same"], ["baz", "same"]))
        self.assertEqual(list(Manifest.merge(*ms)), [
            (None, "bar", None), (None, None, "baz"), ("foo", None, None),
            ("same", "same", "same")])

    def test_empty_subdir_vs_nonepty_subdir(self):
        m1 = Manifest_from_tar("file_and_empty_subdir.tar")
        m2 = Manifest_from_tar("file_and_subdir.tar")
        self.assertEqual(list(Manifest.merge(m1, m2)), [
            ("file", "file"), ("subdir", "subdir"), (None, "subdir/foo")])

    def test_custom_key(self):
        m1 = Manifest.parse(["1foo", "2bar", "3baz"])
        m2 = Manifest.parse(["abc", "def", "ghi"])
        m3 = Manifest.parse(["123", "456", "789"])
        self.assertEqual(
            list(Manifest.merge(m1, m2, m3, key = lambda px: True)), [
                ("1foo", "abc", "123"),
                ("2bar", "def", "456"),
                ("3baz", "ghi", "789")])

    def test_nonrecursive(self):
        m1 = Manifest.parse(["bar", "foo", "  bar", "  foo"])
        m2 = Manifest.parse(["foo", "  foo", "xyzzy"])
        m3 = Manifest.parse(["foo", "  bar", "    baz", "  foo", "    foo"])
        self.assertEqual(list(Manifest.merge(m1, m2, m3)), [
            ("bar", None, None),
            ("foo", "foo", "foo"),
            ("foo/bar", None, "foo/bar"),
            (None, None, "foo/bar/baz"),
            ("foo/foo", "foo/foo", "foo/foo"),
            (None, None, "foo/foo/foo"),
            (None, "xyzzy", None)])

        # now without recursion
        self.assertEqual(list(Manifest.merge(m1, m2, m3, recursive = False)), [
            ("bar", None, None),
            ("foo", "foo", "foo"),
            (None, "xyzzy", None)])

        # and finally with selective recursion (only recurse into "foo"s)
        actual = []
        gen = Manifest.merge(m1, m2, m3, recursive = False)
        try:
            t = next(gen)
            while True:
                actual.append(t)
                paths = filter(lambda x: x is not None, t)
                self.assertTrue(paths)
                path = paths[0]
                self.assertEqual([path] * len(paths), paths)
                try:
                    last_component = path.rsplit("/", 1)[1]
                except:
                    last_component = path
                if last_component == "foo":
                    t = gen.send(True)
                else:
                    t = next(gen)
        except StopIteration:
            pass

        self.assertEqual(actual, [
            ("bar", None, None),
            ("foo", "foo", "foo"),
            ("foo/bar", None, "foo/bar"),
            ("foo/foo", "foo/foo", "foo/foo"),
            (None, None, "foo/foo/foo"),
            (None, "xyzzy", None)])

class Test_Manifest_diff(unittest.TestCase):

    def test_diff_empties(self):
        m1 = Manifest()
        m2 = Manifest.parse([""])
        m3 = Manifest_from_tar("empty.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [])
        self.assertEqual(list(Manifest.diff(m1, m3)), [])
        self.assertEqual(list(Manifest.diff(m2, m1)), [])
        self.assertEqual(list(Manifest.diff(m2, m3)), [])
        self.assertEqual(list(Manifest.diff(m3, m1)), [])
        self.assertEqual(list(Manifest.diff(m3, m2)), [])
        self.assertEqual(m1, m2)
        self.assertEqual(m2, m3)
        self.assertEqual(m3, m1)

    def test_diff_like(self):
        for t in TEST_TARS:
            m1, m2 = Manifest_from_tar(t), Manifest_from_tar(t)
            self.assertEqual(list(Manifest.diff(m1, m2)), [])
            self.assertEqual(list(Manifest.diff(m2, m1)), [])
            self.assertEqual(m1, m2)
            self.assertEqual(m2, m1)

    def test_diff_unlike(self):
        shifted = TEST_TARS[:]
        shifted.append(shifted.pop(0))
        for t1, t2 in zip(TEST_TARS, shifted):
            m1, m2 = Manifest_from_tar(t1), Manifest_from_tar(t2)
            self.assertTrue(list(Manifest.diff(m1, m2)))
            self.assertTrue(list(Manifest.diff(m2, m1)))
            self.assertNotEqual(m1, m2)
            self.assertNotEqual(m2, m1)

            self.assertEqual(len(list(Manifest.diff(m1, m2))),
                             len(list(Manifest.diff(m2, m1))))

    def test_diff_empty_vs_single_file(self):
        m1 = Manifest_from_tar("empty.tar")
        m2 = Manifest_from_tar("single_file.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [(None, "foo")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [("foo", None)])

    def test_diff_single_file_vs_two_files(self):
        m1 = Manifest_from_tar("single_file.tar")
        m2 = Manifest_from_tar("two_files.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [(None, "bar")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [("bar", None)])

    def test_diff_two_files_vs_file_and_empty_subdir(self):
        m1 = Manifest_from_tar("two_files.tar")
        m2 = Manifest_from_tar("file_and_empty_subdir.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [
            ("bar", None), (None, "file"), ("foo", None), (None, "subdir")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [
            (None, "bar"), ("file", None), (None, "foo"), ("subdir", None)])

    def test_diff_file_and_empty_subdir_vs_file_and_subdir(self):
        m1 = Manifest_from_tar("file_and_empty_subdir.tar")
        m2 = Manifest_from_tar("file_and_subdir.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [(None, "subdir/foo")])
        self.assertEqual(list(Manifest.diff(m2, m1)), [("subdir/foo", None)])

    def test_min_diff_two_files_vs_files_at_many_levels(self):
        m1 = Manifest_from_tar("two_files.tar")
        m2 = Manifest_from_tar("files_at_many_levels.tar")
        self.assertEqual(list(Manifest.diff(m1, m2)), [(None, "baz")])

    def test_max_diff_two_files_vs_files_at_many_levels(self):
        m1 = Manifest_from_tar("two_files.tar")
        m2 = Manifest_from_tar("files_at_many_levels.tar")
        self.assertEqual(list(Manifest.diff(m1, m2, recursive = True)), [
            (None, "baz"), (None, "baz/bar"), (None, "baz/baz"),
            (None, "baz/baz/bar"), (None, "baz/baz/baz"), (None, "baz/baz/foo"),
            (None, "baz/foo")])

    def test_min_max_diff_with_diff_at_muliples_levels(self):
        m1 = Manifest.parse("""\
            1foo
            2bar
                1xyzzy
                    1blah
                2zyxxy
                3diff
            3baz
            """.split("\n"))
        m2 = Manifest.parse("""\
            1foo
            2bar
                1xyzzy
                    1blah
                    2diff
                2zyxxy
            3baz
            4diff
                1diff
            """.split("\n"))
        self.assertEqual(list(Manifest.diff(m1, m2)), [
            (None, "2bar/1xyzzy/2diff"),
            ("2bar/3diff", None),
            (None, "4diff"),
        ])
        self.assertEqual(list(Manifest.diff(m1, m2, recursive = True)), [
            (None, "2bar/1xyzzy/2diff"),
            ("2bar/3diff", None),
            (None, "4diff"),
            (None, "4diff/1diff"),
        ])

if __name__ == '__main__':
    unittest.main()
