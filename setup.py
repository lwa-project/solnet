import os
import glob
import shutil

from setuptools import setup, find_namespace_packages

setup(name                 = "solnet",
      version              = "0.1.0",
      description          = "Access SRS data from the RTSN",
      long_description     = "Acces Solar Radio Spectrograph data from the Radio Solar Telescope Network",
      author               = "J. Dowell",
      author_email         = "jdowell@unm.edu",
      license              = 'GPL',
      classifiers          = ['Development Status :: 4 - Beta',
                              'Intended Audience :: Science/Research',
                              'License :: OSI Approved :: GNU General Public License (GPL)',
                              'Topic :: Scientific/Engineering :: Astronomy'],
      packages             = find_namespace_packages(),
      scripts              = glob.glob('scripts/*.py'),
      include_package_data = True,
      python_requires      = '>=3.8',
      install_requires     = ['numpy', 'astropy', 'ephem', 'pytz'],
      zip_safe             = False
)
