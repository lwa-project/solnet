import unittest
import shutil
import tempfile
import os
from datetime import datetime
import hashlib

import solnet

_DATA = os.path.join(os.path.dirname(__file__), 'data', 'sv241001.srs.gz')


class solnet_tests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix='test-solnet-', suffix='.tmp')
        
    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)
        
    def test_load_data(self):
        """Test loading in a SRS file"""
        
        data = solnet.load_srs_data(_DATA)
        self.assertEqual(data.site, 'San Vito')
        
        self.assertEqual(data.freq_range[0], 25e6)
        self.assertEqual(data.freq_range[-1], 180e6)
        
        self.assertEqual(data.datetime_range[0], datetime(2024, 10, 1, 4, 52, 36, 0))
        self.assertEqual(data.datetime_range[-1], datetime(2024, 10, 1, 16, 29, 53, 0))
        
    def test_check_data(self):
        """Test checking SRS data availability"""
        
        dlist = solnet.check_data_availability('2024/10/01')
        self.assertTrue('san-vito' in dlist)
        
    def test_download_data(self):
        """Test downloading SRS data"""
        
        dlist = solnet.download_data('2024/10/01', sites=['San Vito', 'Learmonth'],
                                     save_dir=self.tempdir)
        self.assertTrue('sv241001.srs.gz' in [os.path.basename(d) for d in dlist])
        
        ref_md5 = hashlib.md5()
        with open(_DATA, 'rb') as fh:
            for chunk in iter(lambda: fh.read(32*4096), b''):
                ref_md5.update(chunk)
                
        new_md5 = hashlib.md5()
        with open(os.path.join(self.tempdir, 'sv241001.srs.gz'), 'rb') as fh:
            for chunk in iter(lambda: fh.read(32*4096), b''):
                new_md5.update(chunk)
                
        self.assertEqual(ref_md5.hexdigest(), new_md5.hexdigest())


class solnet_test_suite(unittest.TestSuite):
    def __init__(self):
        unittest.TestSuite.__init__(self)
        
        loader = unittest.TestLoader()
        self.addTests(loader.loadTestsFromTestCase(solnet_tests))


if __name__ == '__main__':
    unittest.main()
