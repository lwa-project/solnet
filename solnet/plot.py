import numpy as np
from datetime import datetime

from typing import Optional

from scipy.stats import scoreatpercentile as percentile

from matplotlib.figure import Figure
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

from .data import SolarRadioSpectrograph

__version__ = '0.1'
__all__ = ['plot_srs']

def plot_srs(srs: SolarRadioSpectrograph, fig: Optional[Figure]=None,
             vmin_percentile: float=5, vmax_percentile: float=95) -> Figure:
    t = srs.datetime_range
    f = srs.freq_range
    d = srs.data
    
    formatter = mdates.DateFormatter('%H:%M')
    
    if fig is None:
        fig = fig = plt.figure()
    ax = fig.gca()
    
    vmin, vmax = percentile(d, [vmin_percentile, vmax_percentile])
    
    cb = ax.imshow(d.T, vmin=vmin, vmax=vmax, origin='lower',
                   extent=(mdates.date2num(t[0]), mdates.date2num(t[-1]), f[0]/1e6, f[-1]/1e6))
    fig.colorbar(cb, ax=ax, label='PSD [dB]')
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(formatter)
    ax.axis('auto')
    ax.set_xlabel('UTC Time')
    ax.set_ylabel('Frequency [MHz]')
    ax.set_title(f"{srs.site} @ {t[len(t)//2].strftime('%Y-%m-%d')}")
    
    return fig
