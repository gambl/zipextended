from distutils.core import setup

setup(name='zipfileext',
      version='0.1',
      description='ZipFile extension to support remove, rename',
      author='Matthew Gamble',
      author_email='matthew.gamble@gmail.com',
      url='https://github.com/gambl/zipfileext',
      packages=['zipfileext', 'zipfileext.tests'],
      package_dir={'zipfileext': '.'},
     )
