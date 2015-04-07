# zipextended - Zipfile Extension ![](https://travis-ci.org/gambl/zipextended.svg)

Module provides class **ZipFileExtended** an extension of pythons zipfile implementation to support **rename** and **removal** of files from a zip archive.

ZipFileExtended: Class with methods to open, read, write, remove, rename, close and list Zip files.

        zip = ZipFileExtended(file,mode="r", compression=ZIP_STORED, allowZip64=True)


 `file`: Either the path to the file, or a file-like object.
 If it is a path, the file will be opened and closed by UCF.

 `mode`: The mode can be either read "r", write "w" or append "a".

 `compression`: The compression type to be used for this archive.
 e.g. `zipfile.ZIP_STORED` (no compression), `zipfile.ZIP_DEFLATED` (requires zlib).


 `allowZip64`: if True ZipFile will create files with ZIP64 extensions when
 needed, otherwise it will raise an exception when this would
 be necessary.
 
The main additional methods provided:
 
 `ZipFileExtended.`**remove**(*zinfo_or_arcname*):
  Remove a member from the archive.

  Args:
  - `zinfo_or_arcname` (ZipInfo, str) ZipInfo object or filename of the
   member.

  Raises:
  - `RuntimeError`: If attempting to modify an Zip archive that is closed.
  
`ZipFileExtended`.**rename**(*zinfo_or_arcname*, *filename*):
  Rename a member in the archive.

  Args:
  - `zinfo_or_arcname` (ZipInfo, str): ZipInfo object or filename of the
            member.
  - `filename` (str): the new name for the member.

  Raises:
  - `RuntimeError`: If attempting to modify an Zip archive that is closed.
