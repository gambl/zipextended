from zipfileext import zipext
import zipfile
import unittest
from tempfile import TemporaryFile
from random import randint, random, getrandbits
from tempfile import NamedTemporaryFile
#from test.support import (TESTFN, unlink)
import io
import os

from .support import (TESTFN, TESTFN2, TESTFN3, unlink, get_files,requires_zlib,
                      requires_gzip, requires_bz2, requires_lzma)

class AbstractZipExtTestWithSourceFile:

    @classmethod
    def setUpClass(cls):
        cls.line_gen = [bytes("Zipfile test line %d. random float: %f\n" %
                              (i, random()), "ascii")
                        for i in range(10)]   #test_zipfile.FIXEDTEST_SIZE
        cls.data = b''.join(cls.line_gen)

    def setUp(self):
        # Make a source file with some lines
        with open(TESTFN, "wb") as fp:
            fp.write(self.data)

    def make_test_archive(self, f, compression):
        # Create the ZIP archive
        with zipext.ZipFileExt(f, "w", compression) as zipfp:
            zipfp.write(TESTFN, "another.name")
            zipfp.write(TESTFN, TESTFN)
            zipfp.writestr("strfile", self.data)


    def zip_remove_file_from_existing_test(self,f,compression):
        self.make_test_archive(f,compression)

        with zipext.ZipFileExt(f, "a", compression) as zipfp:

            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)

            zipfp.remove(TESTFN)
            #Check remaining data
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

        with zipext.ZipFileExt(f, "r", compression) as zipfp:

            #Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data, "Error reading file: another.name")
            self.assertEqual(zipfp.read("strfile"), self.data,"Error reading file: strfile")

            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 2, "Incorrect number of files in archive namelist - archive has {:d} entries, should be 2".format(len(names)))
            # Check present files
            self.assertIn("another.name", names, "File another.name is missing from archive namelist")
            self.assertIn("strfile", names,"File strfile is missing from archive namelist")
            # Check removed file
            self.assertNotIn(TESTFN, names,"File {:s} should not be present in namelist".format(TESTFN))

            # Check infolist
            infos = zipfp.infolist()
            names = [i.filename for i in infos]
            self.assertEqual(len(names),2,"Incorrect number of files in archive infolist - archive has {:d} entries, should be 2".format(len(names)))
            self.assertIn("another.name", names,"File another.name is missing from archive infolist")
            self.assertIn("strfile", names,"File strfile is missing from archive infolist")
            self.assertNotIn(TESTFN, names,"File {:s} should not be present in infolist".format(TESTFN))
            for i in infos:
                self.assertEqual(i.file_size, len(self.data), "Filesize {:d} is not equal to expected: {:d}".format(i.file_size,len(self.data)))

            # check getinfo
            for nm in ("another.name", "strfile"):
                info = zipfp.getinfo(nm)
                self.assertEqual(info.filename, nm,"Filename {:s} is not equal to expected name: {:s}".format(info.filename,nm))
                self.assertEqual(info.file_size, len(self.data),"Filesize {:d} is not equal to expected: {:d}".format(i.file_size,len(self.data)))

            # Check that testzip doesn't raise an exception
            zipfp.testzip()


    def test_remove_file_from_existing(self):
        for f in get_files(self):
            print("Remove from zipfile of FileType - ", f)
            self.zip_remove_file_from_existing_test(f,self.compression)

    def test_rename_file_in_existing(self):
        for f in get_files(self):
            print("Rename in zipfile of FileType - ", f)
            self.zip_rename_file_in_existing_test(f,self.compression)

    def zip_rename_file_in_existing_test(self, f, compression):
        self.make_test_archive(f,compression)

        with zipext.ZipFileExt(f, "a", compression) as zipfp:
            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            TESTFN_NEW = ''.join(["new",TESTFN])
            zipfp.rename(TESTFN,TESTFN_NEW)

            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 3)
            #Check renamed file
            self.assertIn(TESTFN_NEW, names)
            self.assertNotIn(TESTFN, names)
            # Check present files
            self.assertIn("another.name", names)
            self.assertIn("strfile", names)

            #Check remaining data
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

        with zipext.ZipFileExt(f, "r", compression) as zipfp:
            #Check remaining data
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            self.assertEqual(zipfp.read(TESTFN_NEW), self.data)
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 3)
            #Check renamed file
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


            # check getinfo
            for nm in ("another.name", "strfile", TESTFN_NEW):
                info = zipfp.getinfo(nm)
                self.assertEqual(info.filename, nm)
                self.assertEqual(info.file_size, len(self.data))

            # Check that testzip doesn't raise an exception
            zipfp.testzip()

    def test_remove_nonexistent_file(self):
        for f in get_files(self):
            print("Remove non-existent file from zipfile of FileType - ", f)
            self.zip_remove_nonexistent_file_test(f,self.compression)

    def zip_remove_nonexistent_file_test(self, f, compression):
        self.make_test_archive(f,compression)

        with zipext.ZipFileExt(f, "a", compression) as zipfp:
            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            with self.assertRaises(KeyError):
                zipfp.remove("non.existent.file")

    def test_rename_nonexistent_file(self):
        for f in get_files(self):
            print("Rename non-existent file from zipfile of FileType - ", f)
            self.zip_remove_nonexistent_file_test(f,self.compression)

    def zip_rename_nonexistent_file_test(self, f, compression):
        self.make_test_archive(f,compression)

        with zipext.ZipFileExt(f, "a", compression) as zipfp:
            self.assertEqual(zipfp.read(TESTFN), self.data)
            self.assertEqual(zipfp.read("another.name"), self.data)
            self.assertEqual(zipfp.read("strfile"), self.data)
            TESTFN_NEW = ''.join(["new",TESTFN])
            with self.assertRaises(KeyError):
                zipfp.rename("non.existent.file",TESTFN_NEW)

    def test_rename_and_remove_wrong_permissions(self):
        for f in get_files(self):
            self.zip_rename_and_remove_wrong_permissions(f,self.compression)

    def zip_rename_and_remove_wrong_permissions(self, f, compression):
        self.make_test_archive(f,compression)

        with zipext.ZipFileExt(f, "r", compression) as zipfp:
            with self.assertRaises(RuntimeError):
                zipfp.rename("another.name","test")
            with self.assertRaises(RuntimeError):
                zipfp.remove("another.name")

    def test_clone(self):
        for f in get_files(self):
            self.zip_clone_test(f,self.compression)

    def zip_clone_test(self, f, compression):
        self.make_test_archive(f,compression)
        f = zipext.ZipFileExt(f)
        with zipext.ZipFileExt.clone(f,TESTFN3) as zipfp:
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 3)
            #Check remaining data
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
            self.zip_clone_with_filenames_test(f,self.compression)

    def zip_clone_with_filenames_test(self, f, compression):
        self.make_test_archive(f,compression)
        f = zipext.ZipFileExt(f)
        with zipext.ZipFileExt.clone(f,TESTFN3,["another.name","strfile"]) as zipfp:
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 2)
            #Check remaining data
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
            self.zip_clone_with_fileinfos_test(f,self.compression)

    def zip_clone_with_fileinfos_test(self, f, compression):
        self.make_test_archive(f,compression)
        f = zipext.ZipFileExt(f)
        fileinfos = [info for info in f.infolist() if info.filename in ["another.name","strfile"]]
        with zipext.ZipFileExt.clone(f,TESTFN3,fileinfos) as zipfp:
            # Check the namelist
            names = zipfp.namelist()
            self.assertEqual(len(names), 2)
            #Check remaining data
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

    def tearDown(self):
        unlink(TESTFN)
        unlink(TESTFN2)


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
