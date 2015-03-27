import io
import os
import zipfile
import tempfile
import types
from zipfile import ZipFile
from zipfile import (ZIP_DEFLATED, ZIP_STORED, ZIP_LZMA, ZIP64_LIMIT)

class ZipFileExt(ZipFile):

    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED, allowZip64=True):
        super().__init__(file,mode=mode,compression=compression,allowZip64=allowZip64)
        self.requires_commit = False

    def remove(self, zinfo_or_arcname):
        if not self.fp:
            raise RuntimeError(
                "Attempt to modify to ZIP archive that was already closed")

        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            zinfo = zinfo_or_arcname
        else:
            zinfo = self.getinfo(zinfo_or_arcname)

        self.filelist.remove(zinfo)
        del self.NameToInfo[zinfo.filename]
        self._didModify = True
        self.requires_commit = True

    def rename(self, zinfo_or_arcname, filename):
        if not self.fp:
            raise RuntimeError(
                "Attempt to modify to ZIP archive that was already closed")

        # Terminate the file name at the first null byte.  Null bytes in file
        # names are used as tricks by viruses in archives.
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        # This is used to ensure paths in generated ZIP files always use
        # forward slashes as the directory separator, as required by the
        # ZIP format specification.
        if os.sep != "/" and os.sep in filename:
            filename = filename.replace(os.sep, "/")

        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            zinfo = zinfo_or_arcname
        else:
            zinfo = self.getinfo(zinfo_or_arcname)

        zinfo.filename = filename
        self.NameToInfo[zinfo.filename] = zinfo

        self._didModify = True
        self.requires_commit = True


    def close(self):
        """Close the file, and for mode "w" and "a" write the ending
        records."""
        if self.fp is None:
            return

        try:
            if self.mode in ("w", "a") and self._didModify: # write ending records

                if self.requires_commit:
                    # Commit will create a new zipfile and swap it in for this
                    # zip's filepointer - this will have its end record written
                    # upon close
                    self.commit()
                else:
                    # Don't need to commit any changes - just write the end record
                    with self._lock:
                        try:
                            self.fp.seek(self.start_dir)
                        except (AttributeError, io.UnsupportedOperation):
                            # Some file-like objects can provide tell() but not seek()
                            pass
                        self._write_end_record()
        finally:
            fp = self.fp
            self.fp = None
            self._fpclose(fp)

    #TODO: Let clone take a filter for the files to include?
    #TODO: need to instead validate *after* the file has closed?
    @classmethod
    def clone(cls, zipf, file):
        with ZipFileExt(file,mode="w") as new_zip:
            for fileinfo in zipf.infolist():
                bytes = zipf.read_compressed(fileinfo.filename)
                new_zip.write_compressed(fileinfo,bytes)
            badfile = new_zip.testzip()
        if(badfile):
            raise zipfile.BadZipFile("Error when cloning zipfile, failed zipfile check: {} file is corrupt".format(badfile))
        return new_zip

    def read_compressed(self, name, pwd=None):
        """Return file bytes uncompressed for name."""
        with self.open(name, "r", pwd) as fp:
        #Replace the read, _read1 methods for the ZipExtFile file pointer fp
	    #with those defined in this module to support reading the compressed
	    #version of the file
            fp.read = types.MethodType(read,fp)
            fp._read1 = types.MethodType(_read1,fp)
            return fp.read(decompress=False)

    def write_compressed(self, zinfo, data, compress_type=None):
        """Write a file into the archive using the already compressed bytes.
        The contents is 'data', which is the already compressed bytes.
        'zinfo' is a ZipInfo instance proving the required metadata to
        sucessfully write this file.
        """
        if not self.fp:
            raise RuntimeError(
                "Attempt to write to ZIP archive that was already closed")
        zinfo.file_size = len(data)            # Uncompressed size

        with self._lock:
            try:
                self.fp.seek(self.start_dir)
            except (AttributeError, io.UnsupportedOperation):
                # Some file-like objects can provide tell() but not seek()
                pass

            #ensure the two match as the header is about to be re-written
            #TODO we might need to retain the original unsanitised rename?
            zinfo.orig_filename = zinfo.filename

            zinfo.header_offset = self.fp.tell()    # update start of header
            if compress_type is not None:
                zinfo.compress_type = compress_type
            if zinfo.compress_type == ZIP_LZMA:
                # Compressed data includes an end-of-stream (EOS) marker
                zinfo.flag_bits |= 0x02

            #TODO actually requires a slightly less stringent _writecheck as
            #we don't care about the compression type used
            self._writecheck(zinfo)
            self._didModify = True

            zinfo.compress_size = len(data)    # Compressed size

            zip64 = zinfo.file_size > ZIP64_LIMIT or \
                zinfo.compress_size > ZIP64_LIMIT
            if zip64 and not self._allowZip64:
                raise LargeZipFile("Filesize would require ZIP64 extensions")
            self.fp.write(zinfo.FileHeader(zip64))
            self.fp.write(data)
            if zinfo.flag_bits & 0x08:
                # Write CRC and file sizes after the file data
                fmt = '<LQQ' if zip64 else '<LLL'
                self.fp.write(struct.pack(fmt, zinfo.CRC, zinfo.compress_size,
                                          zinfo.file_size))
            self.fp.flush()
            self.start_dir = self.fp.tell()
            self.filelist.append(zinfo)
            self.NameToInfo[zinfo.filename] = zinfo


    def reset(self):
        #TODO instead of reusing __init__ it would be nicer to establish
        #what really needs doing to reset.
        self.__init__(file=self.fp,mode='a',compression=self.compression,allowZip64=self._allowZip64)

    def commit(self):
        #Do we need to try to create the temp files in the same directory initially?
        new_zip = self.clone(self,tempfile.NamedTemporaryFile(delete=False))
        old = tempfile.NamedTemporaryFile(delete=False)
        #Is this a File?
        if isinstance(self.filename,str) and self.filename is not None and os.path.exists(self.filename):
            #if things are filebased then we can used the OS to move files around.
            #mv self.filename to old, new to self.filename, and then remove old
            old.close()
            os.rename(self.filename,old.name)
            os.rename(new_zip.filename,self.filename)
            self.reset()
        #Is it a file-like stream?
        elif hasattr(self.fp,'write'):
            #Not a file but has write, looks like self.fp is a stream
            self.fp.seek(0)
            for b in self.fp:
                old.write(b)
            old.close()
            #Set up to write new bytes
            self.fp.seek(0)
            self.fp.truncate()
            with open(new_zip.filename,'rb') as fp:
                for b in fp:
                    self.fp.write(b)
            self.reset()

            #cleanup
            if os.path.exists(old.name):
                #TODO check valid zip again before we unlink the old?
                os.unlink(old.name)

def read(self, n=-1, decompress=True):
    """Read and return up to n bytes.
    If the argument is omitted, None, or negative, data is read and returned until EOF is reached..
    """
    if n is None or n < 0:
        buf = self._readbuffer[self._offset:]
        self._readbuffer = b''
        self._offset = 0
        while not self._eof:
            buf += self._read1(self.MAX_N,decompress=decompress)
        return buf

    end = n + self._offset
    if end < len(self._readbuffer):
        buf = self._readbuffer[self._offset:end]
        self._offset = end
        return buf

    n = end - len(self._readbuffer)
    buf = self._readbuffer[self._offset:]
    self._readbuffer = b''
    self._offset = 0
    while n > 0 and not self._eof:
        data = self._read1(n,decompress=decompress)
        if n < len(data):
            self._readbuffer = data
            self._offset = n
            buf += data[:n]
            break
        buf += data
        n -= len(data)
    return buf

def _read1(self, n, decompress=True):
    # Read up to n compressed bytes with at most one read() system call,
    # decrypt and decompress them.
    if self._eof or n <= 0:
        return b''

    # Read from file.
    if self._compress_type == ZIP_DEFLATED:
        ## Handle unconsumed data.
        data = self._decompressor.unconsumed_tail
        if n > len(data):
            data += self._read2(n - len(data))
    else:
        data = self._read2(n)

    if self._compress_type == ZIP_STORED or not decompress:
        self._eof = self._compress_left <= 0
    elif self._compress_type == ZIP_DEFLATED:
        n = max(n, self.MIN_READ_SIZE)
        data = self._decompressor.decompress(data, n)
        self._eof = (self._decompressor.eof or
                     self._compress_left <= 0 and
                     not self._decompressor.unconsumed_tail)
        if self._eof:
            data += self._decompressor.flush()
    else:
        data = self._decompressor.decompress(data)
        self._eof = self._decompressor.eof or self._compress_left <= 0

    data = data[:self._left]
    self._left -= len(data)
    if self._left <= 0:
        self._eof = True
    self._update_crc(data)
    return data
