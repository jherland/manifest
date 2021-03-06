import unittest

from manifest import Manifest
from manifest_file import ManifestFileParser
from manifest_dir import ManifestDirWalker
from test_utils import unpacked_tar, Manifest_from_walking_unpacked_tar

class Test_Manifest_walk_visits_all_paths(unittest.TestCase):

    def check_visited_paths(self, tar_path, expect):
        m = Manifest_from_walking_unpacked_tar(tar_path)
        self.assertEqual(["/".join(path) for path, entries, attrs in m.walk()],
                         expect)

    def test_empty(self):
        self.check_visited_paths("empty.tar", [""])

    def test_single_file(self):
        self.check_visited_paths("single_file.tar", ["", "foo"])

    def test_two_files(self):
        self.check_visited_paths("two_files.tar", ["", "bar", "foo"])

    def test_file_and_empty_subdir(self):
        self.check_visited_paths("file_and_empty_subdir.tar",
                                 ["", "file", "subdir"])

    def test_file_and_subdir(self):
        self.check_visited_paths("file_and_subdir.tar",
                                 ["", "file", "subdir", "subdir/foo"])

    def test_file_and_subdir_trailing_slash(self):
        with unpacked_tar("file_and_subdir.tar") as d:
            m = ManifestDirWalker().build(d + "/")
        self.assertEqual(["/".join(path) for path, entries, attrs in m.walk()],
                         ["", "file", "subdir", "subdir/foo"])

    def test_files_at_many_levels(self):
        self.check_visited_paths("files_at_many_levels.tar", [
            "",
            "bar",
            "baz",
            "baz/bar",
            "baz/baz",
            "baz/baz/bar",
            "baz/baz/baz",
            "baz/baz/foo",
            "baz/foo",
            "foo",
        ])

    def test_nonrecursive(self):
        m = ManifestFileParser().build("""\
            foo
                child1
                child2
            bar
            baz
                child3
            """.split("\n"))
        result = []
        for path, names, attrs in m.walk():
            result.append("/".join(path))
            del names[:]
        self.assertEqual(result, [""])
        result = []
        for path, names, attrs in m.walk():
            result.append("/".join(path))
            if path:
                del names[:]
        self.assertEqual(result, ["", "bar", "baz", "foo"])

class Test_Manifest_walk_selective_recurse(unittest.TestCase):

    def setUp(self):
        self.m = ManifestFileParser().build("""\
            a
                a
                    a
                    b
                    c
                b
                    a
                    b
                    c
                c
                    a
                    b
                    c
            b
                a
                    a
                    b
                    c
                b
                    a
                    b
                    c
                c
                    a
                    b
                    c
            c
                a
                    a
                    b
                    c
                b
                    a
                    b
                    c
                c
                    a
                    b
                    c
            """.split("\n"))

        self.all = ["",
            "a", "a/a", "a/a/a", "a/a/b", "a/a/c",
                 "a/b", "a/b/a", "a/b/b", "a/b/c",
                 "a/c", "a/c/a", "a/c/b", "a/c/c",
            "b", "b/a", "b/a/a", "b/a/b", "b/a/c",
                 "b/b", "b/b/a", "b/b/b", "b/b/c",
                 "b/c", "b/c/a", "b/c/b", "b/c/c",
            "c", "c/a", "c/a/a", "c/a/b", "c/a/c",
                 "c/b", "c/b/a", "c/b/b", "c/b/c",
                 "c/c", "c/c/a", "c/c/b", "c/c/c"]

    def check_paths(self, pred, expect):
        actual = []
        for path, names, attrs in self.m.walk():
            if pred(path, names):
                actual.append("/".join(path))
        self.assertEqual(actual, expect)

    def test_all(self):
        def modifier(path, names):
            return True
        self.check_paths(modifier, self.all)

    def test_none(self):
        def modifier(path, names):
            return False
        self.check_paths(modifier, [])

    def test_first(self):
        def modifier(path, names):
            del names[:]
            return True
        self.check_paths(modifier, [""])

        def modifier(path, names):
            return not path
        self.check_paths(modifier, [""])

    def test_not_first(self):
        def modifier(path, names):
            return path
        self.check_paths(modifier, self.all[1:])

    def test_no_a(self):
        expect = [
            "", "b", "b/b", "b/b/b", "b/b/c", "b/c", "b/c/b", "b/c/c",
            "c", "c/b", "c/b/b", "c/b/c", "c/c", "c/c/b", "c/c/c"]
        def modifier(path, names):
            try:
                del names[names.index("a")]
            except:
                pass
            return True
        self.check_paths(modifier, expect)

        def modifier(path, names):
            return "a" not in path
        self.check_paths(modifier, expect)

    def test_only_a(self):
        expect = ["", "a", "a/a", "a/a/a"]
        def modifier(path, names):
            names[:] = ["a"] if "a" in names else []
            return True
        self.check_paths(modifier, expect)

        def modifier(path, names):
            return not any(True for p in path if p != "a")
        self.check_paths(modifier, expect)

    def test_starts_with_a(self):
        expect = [
            "a", "a/a", "a/a/a", "a/a/b", "a/a/c",
                 "a/b", "a/b/a", "a/b/b", "a/b/c",
                 "a/c", "a/c/a", "a/c/b", "a/c/c"]
        def modifier(path, names):
            if not path:
                names[:] = ["a"] if "a" in names else []
                return False
            else:
                return True
        self.check_paths(modifier, expect)

        def modifier(path, names):
            return path and path[0] == "a"
        self.check_paths(modifier, expect)

    def test_ends_with_a(self):
        expect = [
            "a", "a/a", "a/a/a", "a/b/a", "a/c/a",
                 "b/a", "b/a/a", "b/b/a", "b/c/a",
                 "c/a", "c/a/a", "c/b/a", "c/c/a"]
        def modifier(path, names):
            return path and path[-1] == "a"
        self.check_paths(modifier, expect)

class Test_Manifest_walk_visits_all_paths_w_attrs(unittest.TestCase):

    empty_sha1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    empty_attrs = { "size": 0, "sha1": empty_sha1 }

    def check_visited_paths(self, tar_path, expect):
        m = Manifest_from_walking_unpacked_tar(tar_path, ['size', 'sha1'])
        self.assertEqual(
            [("/".join(path), attrs) for path, entries, attrs in m.walk()],
            expect)

    def test_empty(self):
        self.check_visited_paths("empty.tar", [("", {})])

    def test_single_file(self):
        self.check_visited_paths("single_file.tar",
                                 [("", {}), ("foo", self.empty_attrs)])

    def test_two_files(self):
        self.check_visited_paths("two_files.tar", [
            ("", {}), ("bar", self.empty_attrs), ("foo", self.empty_attrs)])

    def test_file_and_empty_subdir(self):
        self.check_visited_paths("file_and_empty_subdir.tar", [
            ("", {}), ("file", self.empty_attrs), ("subdir", {})])

    def test_file_and_subdir(self):
        self.check_visited_paths("file_and_subdir.tar", [
            ("", {}), ("file", self.empty_attrs), ("subdir", {}),
            ("subdir/foo", self.empty_attrs)])

    def test_files_at_many_levels(self):
        self.check_visited_paths("files_at_many_levels.tar", [
            ("", {}),
            ("bar", self.empty_attrs),
            ("baz", {}),
            ("baz/bar", self.empty_attrs),
            ("baz/baz", {}),
            ("baz/baz/bar", self.empty_attrs),
            ("baz/baz/baz", self.empty_attrs),
            ("baz/baz/foo", self.empty_attrs),
            ("baz/foo", self.empty_attrs),
            ("foo", self.empty_attrs),
        ])

    def test_files_with_contents(self):
        self.check_visited_paths("files_with_contents.tar", [
            ("", {}),
            ("bar", {}),
            ("bar/baz", {
                "size": 12,
                "sha1": "7508a86c26bcda1d3f298f67de33f7c48a3fe047"}),
            ("foo", {
                "size": 12,
                "sha1": "fc6da897c87c7b9c3b67d1d5af32085e561db793"}),
            ("symlink_to_bar_baz", {}),
        ])

class Test_Manifest_paths(unittest.TestCase):

    def must_equal(self, tar_path, expect):
        m = Manifest_from_walking_unpacked_tar(tar_path)
        self.assertEqual(list(m.paths()), expect)

    def test_empty(self):
        self.must_equal("empty.tar", [])

    def test_single_file(self):
        self.must_equal("single_file.tar", ["foo"])

    def test_two_files(self):
        self.must_equal("two_files.tar", ["bar", "foo"])

    def test_file_and_empty_subdir(self):
        self.must_equal("file_and_empty_subdir.tar", ["file", "subdir"])

    def test_file_and_subdir(self):
        self.must_equal("file_and_subdir.tar", ["file", "subdir", "subdir/foo"])

    def test_file_and_subdir_trailing_slash(self):
        with unpacked_tar("file_and_subdir.tar") as d:
            m = ManifestDirWalker().build(d + "/")
        self.assertEqual(list(m.paths()), ["file", "subdir", "subdir/foo"])

    def test_files_at_many_levels(self):
        self.must_equal("files_at_many_levels.tar", [
            "bar",
            "baz",
            "baz/bar",
            "baz/baz",
            "baz/baz/bar",
            "baz/baz/baz",
            "baz/baz/foo",
            "baz/foo",
            "foo",
        ])

    def test_nonrecursive(self):
        m = ManifestFileParser().build("""\
            foo
                child1
                child2
            bar
            baz
                child3
            """.split("\n"))
        self.assertEqual(list(m.paths(recursive = False)),
                         ["bar", "baz", "foo"])

if __name__ == '__main__':
    unittest.main()
