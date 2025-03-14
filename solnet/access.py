import os
import sys
import gzip
import zlib
import warnings
from datetime import datetime
from urllib.request import Request, urlopen
from functools import lru_cache

from typing import Union, List

from astropy.time import Time as Time

from .typehints import *

__version__ = '0.1'
__all__ = ['check_data_availability', 'download_data']


_NOAA_URL = 'https://www.ngdc.noaa.gov/stp/space-weather/solar-data/solar-features/solar-radio/rstn-spectral/'

_NOAA_SITES = {'HO': 'holloman',
               'LM': 'learmonth',
               'PA': 'palehua',
               'KP': 'palehua',
               'K7': 'sagamore-hill',
               'sv': 'san-vito'}

_WDC_URL = 'https://www.sws.bom.gov.au/Category/World%20Data%20Centre/Data%20Display%20and%20Download/Spectrograph/station/'

_WDC_SITES = {'LM': 'learmonth'}


_default = lambda x: x
_lowercase = lambda x: x.lower()


@lru_cache(maxsize=16)
def _date_to_noaa(utc_date: SRSDate) -> str:
    """
    Helper function to take a datetime/MJD/Y-M-D string and convert it into a 
    NOAA URL segment.
    """
    
    if isinstance(utc_date, datetime):
        utc_date = utc_date.strftime("%Y/%m/___%y%m%d")
    elif isinstance(utc_date, (int, float)):
        utc_date = Time(utc_data, format='mjd', scale='utc')
        utc_date = utc_date.datetime.strftime("%Y/%m/___%y%m%d")
    elif isinstance(utc_date, str):
        utc_date = utc_date.replace('/', '-')
        utc_date = datetime.strptime(f"{utc_date} 12:00:00", "%Y-%m-%d %H:%M:%S")
        utc_date = utc_date.strftime("%Y/%m/___%y%m%d")
    else:
        raise TypeError(f"Unknown UTC date '{utc_date}'")
        
    return utc_date


@lru_cache(maxsize=16)
def _date_to_wdc(utc_date: SRSDate) -> str:
    """
    Helper function similar to _date_to_noaa but builds URL segement for the WDC.
    """
    
    if isinstance(utc_date, datetime):
        utc_date = utc_date.strftime("%y/___%y%m%d")
    elif isinstance(utc_date, (int, float)):
        utc_date = Time(utc_data, format='mjd', scale='utc')
        utc_date = utc_date.datetime.strftime("%y/___%y%m%d")
    elif isinstance(utc_date, str):
        utc_date = utc_date.replace('/', '-')
        utc_date = datetime.strptime(f"{utc_date} 12:00:00", "%Y-%m-%d %H:%M:%S")
        utc_date = utc_date.strftime("%y/___%y%m%d")
    else:
        raise TypeError(f"Unknown UTC date '{utc_date}'")
        
    return utc_date


@lru_cache(maxsize=16)
def check_data_availability(utc_date: SRSDate, timeout: float=30,
                            return_urls: bool=False) -> List[str]:
    """
    Given a date as one of a datetime instance, a MJD value, or a "YYYY-MM-DD"
    string, find all available RSTN SRS data and return a list of site names.
    If `return_urls` is set to True then the return list is for URLs to directly
    access the data.
    
    If no data are available for the specified date then an empty list is
    returned.
    """
    
    available = []
    available_url = []
    
    # Part 1 - Sites hosted by NOAA
    url_segment = _date_to_noaa(utc_date)
    for site,url_dir in _NOAA_SITES.items():
        ## Build the base URL
        url = f"{_NOAA_URL}/{url_dir}/{url_segment}.SRS.gz".replace('___', site)
        
        ## Try different version of the base URL to deal with changes over time
        found = False
        for modifier in (_default, _lowercase):
            ### Query
            murl = modifier(url)
            req = Request(murl)
            try:
                with urlopen(req, timeout=timeout) as uh:
                    remote_size = int(uh.headers["Content-Length"])
                available.append(url_dir)
                available_url.append(murl)
                found = True
            except Exception:
                pass
                
            if found:
                break
                
    # Part 2 - Sites hosted by WDC
    url_segment = _date_to_wdc(utc_date)
    for site,url_dir in _WDC_SITES.items():
        ## There is some overlap between NOAA and WDC.  If we already have data
        ## for the site from NOAA skip WDC
        if url_dir in available:
            continue
            
        ## Build the base URL
        url = f"{_WDC_URL}/{url_dir}/raw/{url_segment}.srs".replace('___', site)
        
        ## Query
        req = Request(url)
        try:
            with urlopen(req, timeout=timeout) as uh:
                remote_size = int(uh.headers["Content-Length"])
            available.append(url_dir)
            available_url.append(url)
        except Exception:
            pass
            
    # Swap out the site list with the URL list, if requested
    if return_urls:
        available = available_url
    return available


def download_data(utc_date: SRSDate, sites: Union[List[str], str]='all',
                  save_dir: str='.', timeout: float=30, overwrite: bool=False,
                  verbose: bool=True) -> List[str]:
    """
    Given a date as one of a datetime instance, a MJD value, or a "YYYY-MM-DD"
    string, find all avaliable RSTN SRS data, save them to the directory
    specified by `safe_dir`, and return a list of the downloaded files.
    
    If no data are available for the specified date then an empty list is
    returned.
    """
    
    # Find all of the relevant data and get the URLs for those data
    urls = check_data_availability(utc_date, return_urls=True)
    if len(urls) == 0:
        raise RuntimeError(f"No data avaliable for {utc_date}")
    
    # Filter the list of URL to only include the sites we're looking for
    ## Find what codes we need
    codes_to_keep = []
    if isinstance(sites, str):
        sites = [sites,]
    for site in sites:
        if site == 'all':
            codes_to_keep.extend([code for code,_ in _NOAA_SITES.items()])
            codes_to_keep.extend([code for code,_ in _WDC_SITES.items()])
        else:
            lsite = site.lower().replace(' ', '-')
            found = False
            for data_sites in (_NOAA_SITES, _WDC_SITES):
                for code,name in data_sites.items():
                    if name == lsite:
                        codes_to_keep.append(code)
                        found = True
                        
            if not found:
                raise ValueError(f"Unknown RTSN site '{site}'")
                
    ## Weed out the codes we don't want
    clean_urls = []
    for url in urls:
        for code in codes_to_keep:
            if url.find(code.lower()) != -1 or url.find(code) != -1:
                clean_urls.append(url)
                break
    urls = clean_urls
    
    # Convert the save path to a full path
    save_dir = os.path.abspath(save_dir)
    
    # Go!
    downloaded = []
    for url in urls:
        ## Build the request, asking for gzip'd encoding for files that aren't
        ## already gzip'd
        req = Request(url)
        if not url.endswith('.gz'):
            req.add_header('Accept-Encoding', 'gzip')
        if verbose:
            print(f"Downloading {url}...")
            
        ## Check to make sure we aren't going to overwrite something already on
        ## disk (unless we are asked to)
        filename = os.path.join(save_dir, os.path.basename(url).replace('.SRS', '.srs'))
        if os.path.exists(filename) or os.path.exists(filename+'.gz'):
            if not overwrite:
                warnings.warn(f"File {filename} already exists, skipping", RuntimeWarning)
                if not filename.endswith('.gz'):
                    tempname = os.path.join(save_dir, os.path.basename(url)+'.gz')
                    filename = tempname
                downloaded.append(filename)
                continue
                
        ## Download!
        with open(filename, 'wb') as fh:
            received = 0
            remote_size = 0
            with urlopen(req, timeout=timeout) as uh:
                remote_size = int(uh.headers["Content-Length"])
                is_gzip = (uh.headers['Content-Encoding'] == 'gzip')
                if is_gzip:
                    decomp = zlib.decompressobj(zlib.MAX_WBITS|32)
                    
                received = 0
                while True:
                    data = uh.read(1024**2)
                    if len(data) == 0:
                        break
                    received += len(data)
                    
                    if is_gzip:
                        data = decomp.decompress(data)
                    fh.write(data)
                    
        ## Compress so save disk space
        if not filename.endswith('.gz'):
            tempname = os.path.join(save_dir, os.path.basename(url)+'.gz')
            with open(filename, 'rb') as fh:
                with gzip.open(tempname, 'wb') as oh:
                    oh.write(fh.read())
            os.unlink(filename)
            filename = tempname
            
        if verbose:
            print(f"  Downloaded {remote_size} B and saved {received} B to disk")
            
        downloaded.append(filename)
        
    return downloaded
