# TESPy Heat Pump - Case Study Package

This repo contains a modular, object-oriented tool that models a heat pump in TESPy, solves a design point, and then simulates a full off-design time-series driven by the excel data.

## What's inside

hp_tool/
├─ __main__.py        # entrypoint: python -m hp_tool

├─ cli.py             # argument parsing; wiring of config → pipeline → plots

├─ config.py          # declarative ColumnMap + default sheet/column names & mapping knobs

├─ io/
│  └─ pipeline.py     # core ETL + TESPy workflow (merge sheets, map to refrigerant, solve)

├─ models/
│  └─ heat_pump.py    # OOP TESPy model (build, design/offdesign, metrics)

└─ viz/
   └─ plots.py        # time-aware plots (COP, power, Q)

## How to run the program

### Install new virtual environment

```python -m venv .venv```

```.venv\Scripts\activate```

```pip install tespy pandas matplotlib openpyxl ```

### Run from the project root

PowerShell (Windows):

(Copy-Paste this)
python -m hp_tool `

  --excel "data/HP_case_data.xlsx" `

  --sheet_source "Heat source" `

  --sheet_sink "Heat sink" `

  --src_T_in "T_in[degC]" `

  --sink_T_out "T_out[degC]" `

  --sink_Energy_kWh "Energy[kWh]" `

  --outdir results

### Where to see results

After it finishes, open the results/ folder:

design_summary.txt → the design condition TESPy used (T_source, T_sink, Q̇_cond, ηₛ).

hp_timeseries.csv → full time-series of COP, P_comp, Q̇_evap, Q̇_cond, ṁ, and timestamps.

plot_COP.png → COP vs time

plot_P_comp.png → Compressor power vs time

plot_Q.png → Heat transfer rates vs time