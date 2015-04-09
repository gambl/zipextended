import os
import io
from tempfile import NamedTemporaryFile, TemporaryFile
import unittest
import sys

# Python<=3.2 doesn't have FileNotFound and NotADirectory
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = OSError
    NotADirectoryError = OSError

try:
    import zlib
except ImportError:
    zlib = None

try:
    import gzip
except ImportError:
    gzip = None

try:
    import bz2
except ImportError:
    bz2 = None

try:
    import lzma
except ImportError:
    lzma = None


requires_zlib = unittest.skipUnless(zlib, 'requires zlib')

requires_gzip = unittest.skipUnless(gzip, 'requires gzip')

requires_bz2 = unittest.skipUnless(bz2, 'requires bz2')

requires_lzma = unittest.skipUnless(lzma, 'requires lzma')



TESTFN = '.@test'
TESTFN = "{}_{}_tmp".format(TESTFN, os.getpid())

TESTFN2 = TESTFN + "2"
TESTFN3 = TESTFN + "3"

def unlink(filename):
    try:
        os.unlink(filename)
    except (FileNotFoundError, NotADirectoryError):
        pass

def get_files(test):
    yield TESTFN2
    with TemporaryFile() as f:
        yield f
        test.assertFalse(f.closed)
    with io.BytesIO() as f:
        yield f
        test.assertFalse(f.closed)


TEST_HOME_DIR = os.path.dirname(os.path.abspath(__file__))

# TEST_DATA_DIR is used as a target download location for remote resources
TEST_DATA_DIR = os.path.join(TEST_HOME_DIR, "data")

def findfile(filename, subdir=None):
    """Try to find a file on sys.path or in the test directory.  If it is not
    found the argument passed to the function is returned (this does not
    necessarily signal failure; could still be the legitimate path).

    Setting *subdir* indicates a relative path to use to find the file
    rather than looking directly in the path directories.
    """
    if os.path.isabs(filename):
        return filename
    if subdir is not None:
        filename = os.path.join(subdir, filename)
    path = [TEST_HOME_DIR] + sys.path
    for dn in path:
        fn = os.path.join(dn, filename)
        if os.path.exists(fn): return fn
    return filename
