#!/usr/bin/env python3

import argparse
from datetime import datetime

import solnet
import solnet.plot

from matplotlib import pyplot as plt
import matplotlib.dates as mdates


def main(args):
    # Check for data
    sites = solnet.check_data_availability(args.date)
    if not sites:
        raise RuntimeError(f"No data found for {args.date}")
        
    # We have something, download it, and load it in
    datafiles = solnet.download_data(args.date, save_dir=args.save_dir)
    srs = [solnet.load_srs_data(filename) for filename in datafiles]
    t_min = min([s.datetime_range[0] for s in srs])
    t_max = max([s.datetime_range[-1] for s in srs])
    
    fig = plt.figure()
    for i,s in enumerate(srs):
        ax = fig.add_subplot(len(srs), 1, i+1)
        
        solnet.plot.plot_srs(s, fig=fig)
        
        ax.set_xlim([t_min, t_max])
    fig.tight_layout()
    plt.show()

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='download and plot SRS data from the RTSN for a particular UTC date',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument('date', type=str,
                        help='UTC date as either YYYY/MM/DD or YYYY-MM-DD')
    parser.add_argument('-s', '--save-dir', type=str, default='.',
                        help='directory to save downloaded data to')
    args = parser.parse_args()
    main(args)
