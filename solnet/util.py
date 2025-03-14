from copy import deepcopy
import numpy as np

from typing import Union, Sequence

from .data import SolarRadioSpectrograph

__version__ = '0.1'
__all__ = ['combine_srs', 'rectify_combined']


def combine_srs(*args: Union[SolarRadioSpectrograph, Sequence[SolarRadioSpectrograph]]) -> SolarRadioSpectrograph:
    """
    Given a collection of SolarRadioSpectrograph instances, combine them into a
    single SolarRadioSpectrograph instance.  The files are combined by stepping
    through the full time range of the individual files in 10 s increments and
    picking the spectrum that is cloest to the midpoint of the indivdual
    spectrograms.  If there are gaps in the files being combined the missing
    time ranges will be filled with NaNs.
    """
    
    # Check to see if we have been given a list instead of individual SolarRadioSpectrographs
    if isinstance(args[0], (list, tuple)):
        args = args[0]
        
    # Check for a compatible frequency range
    freq_range = args[0].freq_range
    for srs in args:
        if srs.freq_range.size != freq_range.size:
            raise RuntimeError("Cannot combine SolarRadioSpectrograph instances - mis-matched frequency axis")
        if srs.freq_range[0] != freq_range[0]:
            raise RuntimeError("Cannot combine SolarRadioSpectrograph instances - mis-matched frequency start")
        if srs.freq_range[-1] != freq_range[-1]:
            raise RuntimeError("Cannot combine SolarRadioSpectrograph instances - mis-matched frequency stop")
            
    # Load all of the data and calculate a weight for each timestamp.  The weight is
    # simply 1 - |t - middle_t| / 86400 
    data_sources = []
    time_ranges = []
    weights = []
    data = []
    for i,srs in enumerate(args):
        data_sources.append([i,]*len(srs.time_range))
        time_ranges.append(srs.time_range)
        weights.append(np.array(time_ranges[-1]))
        weights[-1] = 1 - np.abs(weights[-1] - weights[-1][weights[-1].size//2]) / 86400
        data.append(srs.data)
    data_sources = np.concatenate(data_sources)
    time_ranges = np.concatenate(time_ranges)
    weights = np.concatenate(weights)
    data = np.concatenate(data)
    
    # Find the full time range and then walk over it
    t0 = time_ranges.min()
    t1 = time_ranges.max()
    combined_data_sources = []
    combined_time_range = []
    combined_data = []
    while t0 <= t1:
        ## File all data within 10 s of the current time
        match = np.where(np.abs(time_ranges - t0) < 5)[0]
        if len(match) > 0:
            ### Good, we have matches.  Down select from the full data, find the
            ### point with the highest weight, and save that to the combined data.
            s = data_sources[match]
            t = time_ranges[match]
            w = weights[match]
            d = data[match,:]
            best = np.argmax(w)
            combined_data_sources.append(s[best])
            combined_time_range.append(t[best])
            combined_data.append(d[best,:])
        else:
            ### Nope, nothing.  Fill with NaNs.
            combined_data_sources.append(np.nan)
            combined_time_range.append(t0)
            combined_data.append(np.zeros(data.shape[-1])*np.nan)
        t0 += 10
        
    # Build the combined SolarRadioSpectrograph
    combined = SolarRadioSpectrograph(1, freq_range)
    ## Come up with a combined site ID and name
    combined.site_id = 0
    combined.site = ''
    for i,srs in enumerate(args):
        combined.site_id += srs.site_id * 10**i
        combined.site += srs.site+'+'
    combined.site = combined.site[:-1]
    ## Set the time range and data
    combined.time_range = combined_time_range
    combined._data = combined_data
    ## Set the data source since that might help with bandpassing later
    combined._data_source = combined_data_sources
    
    # Done
    return combined


def rectify_combined(srs: SolarRadioSpectrograph) -> SolarRadioSpectrograph:
    """
    Given a SolarRadioSpectrograph created by combine_srs() attempt to remove
    any gain differences between sites.  The approach used is to look for
    consecutive spectra that span two differnent sites.  The median power in the
    50 to 75 MHz range is then used to match the power across that pair of
    sites.  This is applied iteratively until all sites have been adjusted.
    Returns a new SolarRadioSpectrograph with the gain adjusted data.
    """
    
    # Make sure we have a way to sort out what is what
    data_source = getattr(srs, '_data_source', None)
    if data_source is None:
        raise RuntimeError("SolarRadioSpectrograph instance does not appear to be combined")
        
    # Pull out the list of spectra
    _data = srs._data
    
    # Figure out how many data source we have a pick a reference data source
    clean_source = [data_source[i] for i in np.where(np.isfinite(data_source))[0]]
    sources = np.unique(clean_source)
    changes = np.diff(data_source)
    ref = data_source[np.where(changes != 0)[0][0]]
    
    # Loop through the data until we've put everything on the same scale
    attemps = 0
    processed = [ref,]
    adjustments = {ref: 0.0}
    while len(processed) < len(sources):
        attemps += 1
        if attemps > 5*len(sources):
            raise RuntimeError(f"Failed to adjust all sites after {attemps} attemps, aborting")
        
        for s in sources:
            ## Have we already processed this data source?
            if s in processed:
                continue
                
            ## Find all of the spectra that are associated with this data source
            source_set = np.where(data_source == s)[0]
            if source_set[0] > 0:
                ### If there seems to be a data source that contributes *before*
                ### the current source, match up to the median power at the end
                ### of that data source.  We only use the 50-75 MHz range for
                ### this match since >100 MHz has a lot of RFI
                source_before = data_source[source_set[0]-1]
                if source_before in processed:
                    bd = np.median(_data[source_set[0]-1][200:401])
                    cu = np.median(_data[source_set[0]  ][200:401])
                    for i in source_set:
                        _data[i] += bd - cu
                    processed.append(s)
                    adjustments[s] = bd - cu
            elif source_set[-1] < len(data_sources) - 1:
                ### If there seems to be a data source that contributes *after*
                ### the current source, match up to the median power at the start
                ### of that data source.  We only use the 50-75 MHz range for
                ### this match since >100 MHz has a lot of RFI
                source_after = data_source[source_set[-1]+1]
                if source_after in processed:
                    cu = np.median(_data[source_set[-1]  ][200:401])
                    af = np.median(_data[source_set[-1]+1][200:401])
                    for i in source_set:
                        _data[i] += af - cu
                    processed.append(s)
                    adjustments[s] = af - cu
                    
    ## Create a copy, update, and return
    new_srs = deepcopy(srs)
    new_srs._data = _data
    new_srs._data_adjustments = adjustments
    return new_srs
