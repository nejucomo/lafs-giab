#!/usr/bin/env python

from distutils.core import setup

setup(name='lafs_giab',
      description='Configure/start/stop a self-contained Tahoe-LAFS grid.',
      version='0.1',
      author='Nathan Wilcox',
      author_email='nejucomo@gmail.com',
      license='GPLv3',
      url='https://github.com/nejucomo/lafs-giab',
      scripts=['lafs_giab.py'],
      )
