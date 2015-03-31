import os
import io
from tempfile import NamedTemporaryFile, TemporaryFile
import unittest

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



TESTFN = '@test'
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
