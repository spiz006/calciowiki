#!/usr/bin/env python

from distutils.core import setup

setup(
    name='calciowiki',
    version='0.5.1',
    description='Use wikipedia as a datasource.',
    author='Spiz ',
    author_email='spizster@gmail.com',
    url='https://github.com/',
    packages=['calciowiki'],
    install_requires=[
          'mwparserfromhell',
          'parsedatetime',
          'pillow',
          'pandas',
          'numpy'
      ],
      zip_safe=False
    )
 