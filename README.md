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

python -m venv .venv
# Windows
.venv\Scripts\activate

pip install tespy pandas matplotlib openpyxl
