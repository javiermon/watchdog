#!/usr/bin/env python

from distutils.core import setup

setup(name='watchdog',
      version='1.0',
      description='process watchdog',
      author='Javier Monteagugo',
      url='https://github.com/javiermon/watchdog',
      scripts = ['src/watchdog'],
      data_files = [('/etc/watchdog/', ['conffiles/watchdog.ini'])]
     )
