import access, read, util, plot

files = access.download_data('2024/11/30')
srss = [read.read_srs(f) for f in files]
srs = util.combine_srs(srss)
plot.plot_srs(srs)

srs2 = util.rectify_combined(srs)
print(srs2._data_adjustments)
plot.plot_srs(srs2)
