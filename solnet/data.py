import gzip
import pytz
import numpy as np
import struct
from datetime import datetime
from textwrap import fill as tw_fill

from typing import List, Optional, Union, BinaryIO

from astropy.time import Time

__version__ = '0.1'
__all__ = ['SolarRadioSpectrograph', 'read_srs']

_UTC = pytz.utc

_SITE_ID_TO_NAME = {1: 'Palehau',
                    2: 'Holloman',
                    3: 'Learmonth',
                    4: 'San Vito',
                    5: 'Sagamore Hill'}


def _build_repr(name, attrs=[]):
    name = '.'.join(name.split('.')[-2:])
    output = "<%s" % name
    first = True
    for key,value in attrs:
        output += "%s %s=%s" % (('' if first else ','), key, value)
        first = False
    output += ">"
    return output


class DummyFileOpener(object):
    """
    Wrapper class to make it easier to pass in a filename or open file handle.
    """
    
    def __init__(self, fh: BinaryIO, mode: Optional[str]=None):
        self._fh = fh
        
    def __enter__(self):
        return self._fh
        
    def __exit__(self, exc_type, exc_value, exc_tb):
        pass


class SolarRadioSpectrograph(object):
    """
    Class to hold data from a RSTB SRS file.  Fields include:
     * site_id - Site ID number
     * site - Site Name
     * freq_range - A list of frequencies (in Hz) for each bin the spectrogram
     * time_range - A list of UNIX timestamps for each bin the spectrogram
     * data - A numpy.ndarray containing the spectrogram
    """
    
    def __init__(self, site_id: int, frequency_range: List[float],
                       time_range: Optional[List[float]]=None,
                       data: Optional[np.ndarray]=None):
        self.site_id = site_id
        self.site = _SITE_ID_TO_NAME[site_id]
        self.freq_range = frequency_range
        if time_range is None:
            time_range = []
        self.time_range = time_range
        if data is None:
            data = []
        else:
            if data.shape[1] != self.freq_range.size:
                raise RuntimeError("Mis-match between data frequency axis and size of frequency_range")
        self._data = list(data)
        
    def __repr__(self):
        n = self.__class__.__module__+'.'+self.__class__.__name__
        a = [(attr,getattr(self, attr, None)) for attr in ('site_id', 'site')]
        if self.freq_range.size:
            a.append(('freq_range', [self.freq_range[0], self.freq_range[-1]]))
        if self.time_range:
            a.append(('time_range', [self.time_range[0], self.time_range[-1]]))
        if self._data:
            a.append(('nchan', self._data[0].size))
            a.append(('ntime', len(self.time_range)))
            a.append(('dtype', self._data[0].dtype))
        return tw_fill(_build_repr(n,a), subsequent_indent='    ')
        
    @property
    def datetime_range(self) -> List[float]:
        """
        Return the timestamps as a collection of datetime instances.
        """
        
        return [datetime.utcfromtimestamp(t) for t in self.time_range]
        
    @property
    def mjd_range(self) -> List[Time]:
        """
        Return the timestamps as a collection of MJDs.
        """
        
        return [Time(t, format='unix', scale='utc').mjd for t in self.time_range]
        
    def append(self, timestamp: float, spec: np.ndarray):
        """
        Append a new timestamp, spectrum pair to the spectrogram.
        """
        
        if spec.size != self.freq_range.size:
            raise RuntimeError(f"Expected a spectrum of length {self.freq_range.size} but found {data.size}")
            
        self.time_range.append(timestamp)
        self._data.append(spec)
        
    def extend(self, timestamps: List[float], specs: Union[List[np.ndarray], np.ndarray]):
        if len(timestamps) != len(specs):
            raise RuntimeError(f"Different numbers of timestamps ({len(timestamps)})  and spectra ({len(specs)})")
        for s in specs:
            if s.size != self.freq_range.size:
                raise RuntimeError(f"Expected a spectrum of length {self.freq_range.size} but found {data.size}")
                
        self.time_ranges.extend(timestamps)
        self._data.extend(specs)
                    
    @property
    def data(self) -> np.ndarray:
        """
        Return the spectrogram as a 2D numpy.ndarray.  The shape is time by
        frequency.
        """
        
        return np.array(self._data)
        
    @classmethod
    def from_file(kls, filename_or_fh: Union[str, BinaryIO]) -> 'SolarRadioSpectrograph':
        """
        Given a filename, load in the data and return a fully populated
        SolarRadioSpectrograph instance.
        
        Based on:  https://www.astro.umd.edu/~white/gb/read_rstn_srs.pro
        """
        
        srs = kls(1, [])
        
        # Pick how to open the file (or wrap it if it's already open)
        opener = open
        if isinstance(filename_or_fh, str):
            if filename_or_fh.lower().endswith('.gz'):
                opener = gzip.open
        else:
            opener = DummyFileOpener
            
        # Go!
        with opener(filename_or_fh, 'rb') as fh:
            first_frame = True
            while True:
                ## Read in the header
                header = fh.read(24)
                if len(header) < 24:
                    break
                    
                ## Parse the header
                header = struct.unpack('>BBBBBBBBHHHBBHHHBB', header)
                year_offset = 2000
                if header[0] > 50:
                    year_offset = 1900
                    
                ## If this happens to be the first frame save out the site ID and the
                ## complete frequency list
                if first_frame:
                    site_id = header[6]
                    f1B, f1E = header[8], header[9]
                    freq1 = np.linspace(f1B, f1E, 401)
                    
                    f2B, f2E = header[13], header[14]
                    freq2 = np.linspace(f2B, f2E, 401)
                    
                    freq = np.concatenate([freq1, freq2])
                    
                    srs.site_id = site_id
                    srs.site = _SITE_ID_TO_NAME[site_id]
                    srs.freq_range = freq*1e6
                    first_frame = False
                    
                ## Convert the date to a UTC-aware datetime instance
                dt = datetime(year=header[0]+year_offset, month=header[1], day=header[2],
                              hour=header[3], minute=header[4], second=header[5], microsecond=0,
                              tzinfo=_UTC)
                
                ## Load in the reference and attenuator values so that we can correct
                ## the data
                f1Ref, f1Atten = header[11], header[12]
                f2Ref, f2Atten = header[16], header[17]
                
                ## Load in the data
                ### Part 1
                data0 = fh.read(401)
                if len(data0) < 401:
                    break
                data0 = np.frombuffer(data0, dtype=np.uint8)
                data0 = data0*1.0 + f1Ref + f1Atten
                ### Part 2
                data1 = fh.read(401)
                if len(data1) < 401:
                    break
                data1 = np.frombuffer(data1, dtype=np.uint8)
                data1 = data1*1.0 + f2Ref + f2Atten
                
                ## Save
                srs.append(dt.timestamp(), np.concatenate([data0, data1]))
                
        # Done
        return srs


def load_srs_data(filename: str) -> SolarRadioSpectrograph:
    """
    Given a RSTN SRS file, load in the data and return a fully populated
    SolarRadioSpectrograph instance.  If there was a problem reading the file
    None is returned.
    """
    
    return SolarRadioSpectrograph.from_file(filename)
