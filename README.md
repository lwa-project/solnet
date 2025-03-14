# solnet
[![GHA](https://github.com/lwa-project/solnet/actions/workflows/main.yml/badge.svg)](https://github.com/lwa-project/solnet/actions/workflows/main.yml)

solnet is a Python package for accessing, processing, and visualizing Solar
Radio Spectrograph (SRS) data from the [Radio Solar Telescope Network (RSTN)](https://www.ncei.noaa.gov/products/space-weather/legacy-data/solar-electro-optical-network).

From NOAA:
> The SRS detects spectral solar radio frequency emissions within the meter and
> decameter (tens of meters) region of the radio spectrum

## Usage:
To look for data on Junary 10, 2025:
```
import solnet
sites = solnet.check_data_availability('2025-01-10')
print(f"Sites with data on January 10: {sites}")
```

Download the data from San Vito and save it to the local directory:
```
filename = solnet.download_data('2025-01-10', sites='San Vito', save_dir='.')
```

Load and plot the data:
```
srs = solnet.load_srs_data(filename)

import solnet.plot
from matplotlib import pyplot as plt
fig = solnet.plot.plot_srs(srs)
fig.tight_layout()
plt.show()
```


