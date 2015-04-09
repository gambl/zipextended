from zipextended import zipfileextended
import zipfile
import unittest
from tempfile import TemporaryFile
from random import randint, random, getrandbits
from tempfile import NamedTemporaryFile
import io
import os

from .support import (TESTFN, TESTFN2, TESTFN3, unlink, get_files, requires_zlib,
                      requires_gzip, requires_bz2, requires_lzma, findfile)


class AbstractZipExtTestWithSourceFile:

    @classmethod
    def setUpClass(cls):
        cls.line_gen = [bytes("Zipfile test line %d. random float: %f\n" %
                              (i, random()), "ascii")
                        for i in range(10)]  # test_zipfile.FIXEDTEST_SIZE
        cls.data = b''.join(cls.line_gen)

    def setUp(self):
        # Make a source file with some lines
        with open(TESTFN, "wb") as fp:
            fp.write(self.data)

    def make_test_archive(self, f, compression):
        # Create the ZIP archive
        with zipfileextended.ZipFileExtended(f, "w", compression) as zipfp:
            zipfp.write(TESTFN, "another.name")
            zipfp.write(TESTFN, TESTFN)
            zipfp.writestr("strfile", self.data)

    def zip_remove_file_from_existing_test(self, f, compression):
        self.make_test_archive(f, compression)

        with zipfileextended.ZipFileExtended(f, "a", compression) as zipfp:

            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)

            zipfp.remove(TESTFN)
            # Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 2)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            # Check removed file
            self.assertNotIn(TESTFN, names)

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names), 2)
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            self.assertNotIn(TESTFN, names)
            for i in infos:
                self.assertEqual(i.file_size, len(self.data))

        with zipfileextended.ZipFileExtended(f, "r", compression) as zipfp:

            # Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)

            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 2)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            # Check removed file
            self.assertNotIn(TESTFN, names)

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names), 2)
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            self.assertNotIn(TESTFN, names)
            for i in infos:
                self.assertEqual(i.file_size, len(self.data))

            # check getinfo
            for nm in ("another.name", "strfile"):
                info = zipfp.getinfo(nm)
                self.assertEqual(info.filename, nm)
                self.assertEqual(info.file_size, len(self.data))

            # Check that testzip doesn't raise an exception
            zipfp.testzip()

    def test_remove_file_from_existing(self):
        for f in get_files(self):
            self.zip_remove_file_from_existing_test(f, self.compression)

    def test_rename_file_in_existing(self):
        for f in get_files(self):
            self.zip_rename_file_in_existing_test(f, self.compression)

    def zip_rename_file_in_existing_test(self, f, compression):
        self.make_test_archive(f, compression)

        with zipfileextended.ZipFileExtended(f, "a", compression) as zipfp:
            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            TESTFN_NEW = ''.join(["new", TESTFN])
            zipfp.rename(TESTFN, TESTFN_NEW)

            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 3)
            # Check renamed file
            self.assertIn(TESTFN_NEW, names)
            self.assertNotIn(TESTFN, names)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)

            # Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            self.assertEqual(zipfp.read(TESTFN_NEW), self.data)

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names), 3)
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            self.assertIn(TESTFN_NEW, names)

            for i in infos:
                self.assertEqual(i.file_size, len(self.data))

        with zipfileextended.ZipFileExtended(f, "r", compression) as zipfp:
            # Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            self.assertEqual(zipfp.read(TESTFN_NEW), self.data)
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 3)
            # Check renamed file
            self.assertIn(TESTFN_NEW, names)
            self.assertNotIn(TESTFN, names)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names), 3)
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)
            self.assertIn(TESTFN_NEW, names)
            self.assertNotIn(TESTFN, names)

            for i in infos:
                self.assertEqual(i.file_size, len(self.data))

            # Check getinfo
            for nm in ("another.name", "strfile", TESTFN_NEW):
                info = zipfp.getinfo(nm)
                self.assertEqual(info.filename, nm)
                self.assertEqual(info.file_size, len(self.data))

            # Check that testzip doesn't raise an exception
            zipfp.testzip()

    def test_remove_nonexistent_file(self):
        for f in get_files(self):
            self.zip_remove_nonexistent_file_test(f, self.compression)

    def zip_remove_nonexistent_file_test(self, f, compression):
        self.make_test_archive(f, compression)

        with zipfileextended.ZipFileExtended(f, "a", compression) as zipfp:
            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            with self.assertRaises(KeyError):
                zipfp.remove("non.existent.file")

    def test_rename_nonexistent_file(self):
        for f in get_files(self):
            self.zip_remove_nonexistent_file_test(f, self.compression)

    def zip_rename_nonexistent_file_test(self, f, compression):
        self.make_test_archive(f, compression)

        with zipfileextended.ZipFileExtended(f, "a", compression) as zipfp:
            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            TESTFN_NEW = ''.join(["new", TESTFN])
            with self.assertRaises(KeyError):
                zipfp.rename("non.existent.file", TESTFN_NEW)

    def test_rename_and_remove_wrong_permissions(self):
        for f in get_files(self):
            self.zip_rename_and_remove_wrong_permissions(f, self.compression)

    def zip_rename_and_remove_wrong_permissions(self, f, compression):
        self.make_test_archive(f, compression)

        with zipfileextended.ZipFileExtended(f, "r", compression) as zipfp:
            with self.assertRaises(RuntimeError):
                zipfp.rename("another.name", "test")
            with self.assertRaises(RuntimeError):
                zipfp.remove("another.name")

    def test_clone(self):
        for f in get_files(self):
            self.zip_clone_test(f, self.compression)

    def zip_clone_test(self, f, compression):
        self.make_test_archive(f, compression)
        with zipfileextended.ZipFileExtended(f) as f:
            with f.clone(TESTFN3) as zipfp:
                # Check the namelist
                names = zipfp.namelist()
                self.assertEqual(len(names), 3)
                # Check remaining data
                self.assertEqual(zipfp.read("another.name"), self.data)
                self.assertEqual(zipfp.read("strfile"), self.data)
                self.assertEqual(zipfp.read(TESTFN), self.data)

                # Check present files
                self.assertIn("another.name", names)
                self.assertIn("strfile", names)
                self.assertIn(TESTFN, names)
                # Check infolist
                infos = zipfp.infolist()
                names = [i.filename for i in infos]
                self.assertEqual(len(names), 3)
                for i in infos:
                    self.assertEqual(i.file_size, len(self.data))

    def test_clone_with_filenames(self):
        for f in get_files(self):
            self.zip_clone_with_filenames_test(f, self.compression)

    def zip_clone_with_filenames_test(self, f, compression):
        self.make_test_archive(f, compression)
        with zipfileextended.ZipFileExtended(f) as f:
            with f.clone(TESTFN3, ["another.name", "strfile"]) as zipfp:
                # Check the namelist
                names = zipfp.namelist()
                self.assertEqual(len(names), 2)
                # Check remaining data
                self.assertEqual(zipfp.read("another.name"), self.data)
                self.assertEqual(zipfp.read("strfile"), self.data)

                # Check present files
                self.assertIn("another.name", names)
                self.assertIn("strfile", names)
                self.assertNotIn(TESTFN, names)
                # Check infolist
                infos = zipfp.infolist()
                names = [i.filename for i in infos]
                self.assertEqual(len(names), 2)
                for i in infos:
                    self.assertEqual(i.file_size, len(self.data))

    def test_clone_with_fileinfos(self):
        for f in get_files(self):
            self.zip_clone_with_fileinfos_test(f, self.compression)

    def zip_clone_with_fileinfos_test(self, f, compression):
        self.make_test_archive(f, compression)
        with zipfileextended.ZipFileExtended(f) as f:
            fileinfos = [info for info in f.infolist()
                         if info.filename in ["another.name", "strfile"]]
            with f.clone(TESTFN3, fileinfos) as zipfp:
                # Check the namelist
                names = zipfp.namelist()
                self.assertEqual(len(names), 2)
                # Check remaining data
                self.assertEqual(zipfp.read("another.name"), self.data)
                self.assertEqual(zipfp.read("strfile"), self.data)

                # Check present files
                self.assertIn("another.name", names)
                self.assertIn("strfile", names)
                self.assertNotIn(TESTFN, names)
                # Check infolist
                infos = zipfp.infolist()
                names = [i.filename for i in infos]
                self.assertEqual(len(names), 2)
                for i in infos:
                    self.assertEqual(i.file_size, len(self.data))

    def test_hidden_files(self):
        f = findfile("zip_hiddenfiles.zip")
        hidden_data = [b'This is a prefix.\n',
                       b'Intermediate data\n',
                       b'PK\x03\x04\x14\x00\x00\x00\x00\x00\x0cgYF\xf39@\x12\x0c\x00\x00\x00\x0c\x00\x00\x00\x04\x00\x00\x00fourHidden file\n']

        with zipfileextended.ZipFileExtended(f) as f:
            hidden_files = f._hidden_files()
            self.assertEqual(len(hidden_files), 3)

            for file, hidden in zip(hidden_files, hidden_data):
                data = file.read(file.length)
                self.assertEqual(data, hidden)

    def test_clone_with_hidden_files(self):
        f = findfile("zip_hiddenfiles.zip")
        hidden_data = [b'This is a prefix.\n',
                       b'Intermediate data\n',
                       b'PK\x03\x04\x14\x00\x00\x00\x00\x00\x0cgYF\xf39@\x12\x0c\x00\x00\x00\x0c\x00\x00\x00\x04\x00\x00\x00fourHidden file\n']

        with zipfileextended.ZipFileExtended(f) as f:
            original_files = {fileinfo.filename: f.read(fileinfo.filename)
                              for fileinfo in f.infolist()}
            with f.clone(TESTFN3, filenames_or_infolist=f.infolist()) as zipfp:
                # Check the namelist
                names = zipfp.namelist()
                self.assertEqual(len(names), 4)
                # check the hidden files persisted
                hidden_files = zipfp._hidden_files()
                self.assertEqual(len(hidden_files), 3)

                for file, hidden in zip(hidden_files, hidden_data):
                    data = file.read(file.length)
                    self.assertEqual(data, hidden)
                names = zipfp.namelist()
                self.assertIn("one", names)
                self.assertIn("two", names)
                self.assertIn("three", names)
                self.assertIn("five", names)
                self.assertNotIn("four", names)

                # check data
                new_files = {fileinfo.filename: zipfp.read(fileinfo.filename)
                             for fileinfo in zipfp.infolist()}
                for name, data in new_files.items():
                    self.assertEqual(data, original_files[name])
                # Check infolist
                infos = zipfp.infolist()
                names = [i.filename for i in infos]
                self.assertEqual(len(names), 4)

    def test_clone_ignore_hidden_files(self):
        f = findfile("zip_hiddenfiles.zip")
        with zipfileextended.ZipFileExtended(f) as f:
            original_files = {fileinfo.filename: f.read(fileinfo.filename)
                              for fileinfo in f.infolist()}
            with f.clone(TESTFN3, ignore_hidden_files=True) as zipfp:
                # Check the namelist
                names = zipfp.namelist()
                self.assertEqual(len(names), 4)

                # check the hidden files persisted
                hidden_files = zipfp._hidden_files()
                self.assertEqual(len(hidden_files), 0)

                names = zipfp.namelist()
                self.assertIn("one", names)
                self.assertIn("two", names)
                self.assertIn("three", names)
                self.assertIn("five", names)
                self.assertNotIn("four", names)

                # Check data
                new_files = {fileinfo.filename: zipfp.read(fileinfo.filename)
                             for fileinfo in zipfp.infolist()}
                for name, data in new_files.items():
                    self.assertEqual(data, original_files[name])

                # Check infolist
                infos = zipfp.infolist()
                names = [i.filename for i in infos]
                self.assertEqual(len(names), 4)

    def tearDown(self):
        unlink(TESTFN)
        unlink(TESTFN2)
        unlink(TESTFN3)


class StoredZipExtTestWithSourceFile(AbstractZipExtTestWithSourceFile,unittest.TestCase):

    compression = zipfile.ZIP_STORED

@requires_zlib
class DeflateTestsWithSourceFile(AbstractZipExtTestWithSourceFile,
                                 unittest.TestCase):
    compression = zipfile.ZIP_DEFLATED

@requires_bz2
class Bzip2TestsWithSourceFile(AbstractZipExtTestWithSourceFile,
                               unittest.TestCase):
    compression = zipfile.ZIP_BZIP2

@requires_lzma
class LzmaTestsWithSourceFile(AbstractZipExtTestWithSourceFile,
                              unittest.TestCase):
    compression = zipfile.ZIP_LZMA

class TestsWithLargeSourceFile(unittest.TestCase):

    def setUp(self):
        # Create test data.
        line_gen = ("Test of zipfile line %d." % i for i in range(1000000))
        self.data = '\n'.join(line_gen).encode('ascii')

        # And write it to a file.
        fp = open(TESTFN, "wb")
        fp.write(self.data)
        fp.close()

class StoredZipExtTestWithLargeSourceFile(TestsWithLargeSourceFile, AbstractZipExtTestWithSourceFile,unittest.TestCase):

    compression = zipfile.ZIP_STORED

@requires_zlib
class DeflateTestsWithLargeSourceFile(TestsWithLargeSourceFile, AbstractZipExtTestWithSourceFile,
                                 unittest.TestCase):
    compression = zipfile.ZIP_DEFLATED
