import io
import os
import zipfile
import tempfile
import types
import shutil
from zipfile import ZipFile
from zipfile import (ZIP_DEFLATED, ZIP_STORED, ZIP_LZMA, ZIP64_LIMIT)
import struct
import operator

class ZipFileExtended(ZipFile):
    """
        Class with methods to open, read, write, remove, rename, close and list Zip files.

        zip = ZipFileExtended(file,mode="r", compression=ZIP_STORED, allowZip64=True)


        file: Either the path to the file, or a file-like object.
              If it is a path, the file will be opened and closed by UCF.

        mode: The mode can be either read "r", write "w" or append "a".

        compression: The compression type to be used for this archive.
                     e.g. zipfile.ZIP_STORED (no compression),
                     zipfile.ZIP_DEFLATED (requires zlib).


        allowZip64: if True ZipFile will create files with ZIP64 extensions when
                    needed, otherwise it will raise an exception when this would
                    be necessary.

        """
    def __init__(self, file, mode="r", compression=zipfile.ZIP_STORED, allowZip64=True):
        super().__init__(file,mode=mode,compression=compression,allowZip64=allowZip64)
        self.requires_commit = False

    def _hidden_files(self):
        """Find any files that are hidden between memebers of this archive"""
        #Establish the file boundaries, start - end, for each file
        #initial file boundaries are the start and end of the zip up to the
        #central directory
        file_boundaries = [{"start": 0, "end": 0},{"start": self.start_dir, "end": self.start_dir}]
        for fileinfo in self.filelist:

            #establish the end_offset
            end_offset = fileinfo.header_offset
            end_offset += zipfile.sizeFileHeader
            end_offset += len(fileinfo.orig_filename)
            end_offset += len(fileinfo.extra)
            end_offset += fileinfo.compress_size
            is_encrypted = fileinfo.flag_bits & 0x1
            if is_encrypted:
                end_offset += 12

            #add to the file boundaries
            file_boundaries.append({"start" : fileinfo.header_offset, "end" : end_offset})

        #Look for data inbetween the file boundaries
        file_boundaries.sort(key=operator.itemgetter("start"))
        current = file_boundaries.pop(0)
        hidden_files = []
        for next in file_boundaries:
            if current["end"] > next["start"]:
                #next is contained within current |--c.s---n.s--n.e---c.e--|
                continue
            elif current["end"] != next["start"]:
                #There is some data inbetween
                file = zipfile._SharedFile(self.fp, current["end"], self._fpclose, self._lock)
                file.length = next["start"] - current["end"]
                hidden_files.append(file)
            current = next

        return hidden_files

    def _renamecheck(self, filename):
        """Check for errors before writing a file to the archive."""
        if filename in self.NameToInfo:
            import warnings
            warnings.warn('Duplicate name: %r' % zinfo.filename, stacklevel=3)
        if self.mode not in ('w', 'x', 'a'):
            raise RuntimeError("rename() requires mode 'w', 'x', or 'a'")
        if not self.fp:
            raise RuntimeError(
                "Attempt to modify ZIP archive that was already closed")

    def _removecheck(self):
        """Check for errors before writing a file to the archive."""
        if self.mode not in ('w', 'x', 'a'):
            raise RuntimeError("rename() requires mode 'w', 'x', or 'a'")
        if not self.fp:
            raise RuntimeError(
                "Attempt to modify ZIP archive that was already closed")

    def remove(self, zinfo_or_arcname):
        """
        Remove a member from the archive.

        Args:
          zinfo_or_arcname (ZipInfo, str) ZipInfo object or filename of the
            member.

        Raises:
          RuntimeError: If attempting to modify an Zip archive that is closed.
        """

        if not self.fp:
            raise RuntimeError(
                "Attempt to modify to ZIP archive that was already closed")

        self._removecheck()

        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            zinfo = zinfo_or_arcname
            #perform an existence check
            self.getinfo(zinfo.filename)
        else:
            zinfo = self.getinfo(zinfo_or_arcname)

        self.filelist.remove(zinfo)
        del self.NameToInfo[zinfo.filename]
        self._didModify = True
        self.requires_commit = True

    def rename(self, zinfo_or_arcname, filename):
        """
        Rename a member in the archive.

        Args:
          zinfo_or_arcname (ZipInfo, str): ZipInfo object or filename of the
            member.
          filename (str): the new name for the member.

        Raises:
          RuntimeError: If attempting to modify an Zip archive that is closed.
        """

        if not self.fp:
            raise RuntimeError(
                "Attempt to modify to ZIP archive that was already closed")

        self._renamecheck(filename)

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
            #perform an existence check
            self.getinfo(zinfo.filename)
        else:
            zinfo = self.getinfo(zinfo_or_arcname)

        zinfo.filename = filename
        self.NameToInfo[zinfo.filename] = zinfo

        self._didModify = True
        self.requires_commit = True


    def close(self):
        """Close the file, and for mode "w", 'x' and "a" write the ending
        records."""
        if self.fp is None:
            return

        try:
            if self.mode in ("w", "a", 'x') and self._didModify: # write ending records

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


    @classmethod
    def clone(cls, zipf, file, filenames_or_infolist=None):
        """ Clone the a zip file using the given file (filename or filepointer).

        Args:
          zipf (ZipFile): the ZipFile to be cloned.
          file (File, str): file-like object or filename of file to write the
            new zip file to.
          filenames_or_infolist (list(str), list(ZipInfo), optional): list of
            members from zipf to include in the new zip file.

        Returns:
            At new ZipFile object of the cloned zipfile open in append mode.

        Raises:
            BadZipFile exception.
        """
        if filenames_or_infolist or zipf.requires_commit:
            if filenames_or_infolist is None:
                filenames_or_infolist = zipf.infolist()
            # if we are filtering based on filenames or need to commit changes
            # then create via ZipFile
            with ZipFileExtended(file,mode="w") as clone:
                if isinstance(filenames_or_infolist[0], zipfile.ZipInfo):
                    infolist = filenames_or_infolist
                else:
                    infolist = [zipinfo for zipinfo in zipf.infolist() if zipinfo.filename in filenames_or_infolist]

                for zipinfo in infolist:
                    bytes = zipf.read_compressed(zipinfo.filename)
                    clone.write_compressed(zipinfo,bytes)
        else:
            #We are copying with no modifications - just copy bytes
            zipf.fp.seek(0)
            if isinstance(file,str):
                with open(file,'wb+') as fp:
                    shutil.copyfileobj(zipf.fp,fp)
            else:
                fp = file
                shutil.copyfileobj(zipf.fp,fp)
                fp.seek(0)

        clone = ZipFileExtended(file,mode="a",compression=zipf.compression,allowZip64=zipf._allowZip64)
        badfile = clone.testzip()
        if(badfile):
            raise zipfile.BadZipFile("Error when cloning zipfile, failed zipfile check: {} file is corrupt".format(badfile))
        return clone

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

        with self._lock:
            try:
                self.fp.seek(self.start_dir)
            except (AttributeError, io.UnsupportedOperation):
                # Some file-like objects can provide tell() but not seek()
                pass

            #ensure the two match as the header is about to be re-written
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
        #Reset modification and commit flags
        self._didModify = False
        self.requires_commit = False
        # Reread contents
        self._RealGetContents()
        # seek to start of directory ready for subsequent writes
        self.fp.seek(self.start_dir)


    def commit(self):
        #zip will be validated by clone
        #Try to create tempfiles in same directory first
        if not self._filePassed:
            dir = os.path.dirname(self.filename)
        else:
            dir = None
        try:
            clonefp = tempfile.NamedTemporaryFile(dir=dir, delete=False)
            backupfp = tempfile.NamedTemporaryFile(dir=dir, delete=False)
        except:
            clonefp = tempfile.NamedTemporaryFile(delete=False)
            backupfp = tempfile.NamedTemporaryFile(delete=False)

        #clone the zip to create the up-to-date version - will verify and raise BadZipFile
        #error if it fails
        clone = self.clone(self,clonefp)

        #Now we need to move files around
        #Is this a real file, and does it live on the same mount point?
        if not self._filePassed and os.path.exists(self.filename) and (find_mount_point(self.filename) == find_mount_point(clone.filename)):
            #if things are filebased then we can used the OS to move files around.
            #mv self.filename to backupfp, new to self.filename, and then remove backupfp
            backupfp.close()
            try:
                os.rename(self.filename, backupfp.name)
            except:
                raise RuntimeError("Failed to commit updates to zipfile")
            try:
                os.rename(clone.filename, self.filename)
                self.reset()
            except:
                os.rename(backupfp.name, self.filename)
                raise RuntimeError("Failed to commit updates to zipfile")
        #Is it a file-like stream?
        elif hasattr(self.fp,'write'):
            #self.fp is a stream or lives on another mount point
            try:
                self.fp.seek(0)
                for b in self.fp:
                    backupfp.write(b)
            except:
                raise RuntimeError("Failed to commit updates to zipfile")
            try:
                #Set up to write new bytes
                self.fp.seek(0)
                self.fp.truncate() #might be shorter so truncate
                with open(clone.filename,'rb') as fp:
                    for b in fp:
                        self.fp.write(b)
                self.reset()
            except:
                backupfp.seek(0)
                self.fp.seek(0)
                for b in backup.fp:
                    self.fp.write(b)
                backupfp.close()
                raise RuntimeError("Failed to commit updates to zipfile")
            backupfp.close()
        else:
            #failed to commit
            raise RuntimeError("Failed to commit updates to zipfile")
        #cleanup
        if os.path.exists(backupfp.name):
            os.unlink(backupfp.name)

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
    #We can only check the crc if we are decompressing
    if decompress:
        self._update_crc(data)
    return data

def find_mount_point(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path
