import argparse
import os
from .config import ColumnMap
from .io.pipeline import run_pipeline
from .viz.plots import plot_series

def parse_args():
    ap = argparse.ArgumentParser(description="TESPy Heat Pump — Merge Heat source & Heat sink sheets")

    ap.add_argument("--excel", required=True, help="Path to HP_case_data.xlsx")
    ap.add_argument("--outdir", default="results", help="Output folder")

    # sheet names
    ap.add_argument("--sheet_source", default="Heat source")
    ap.add_argument("--sheet_sink", default="Heat sink")

    # time columns
    ap.add_argument("--time_start_source", default="start measurement")
    ap.add_argument("--time_end_source", default="end measurement")
    ap.add_argument("--time_start_sink", default="start measurement")
    ap.add_argument("--time_end_sink", default="end measurement")

    # source columns
    ap.add_argument("--src_T_in", default="T_in[degC]")
    ap.add_argument("--src_T_out", default="T_out[degC]")

    # sink columns
    ap.add_argument("--sink_T_in", default="T_in[degC]")
    ap.add_argument("--sink_T_out", default="T_out[degC]")
    ap.add_argument("--sink_Energy_kWh", default="Energy[kWh]")
    ap.add_argument("--sink_Q_cond_kW", default=None)

    # mapping & bounds
    ap.add_argument("--evap_approach_K", type=float, default=5.0)
    ap.add_argument("--sink_setpoint_C", type=float, default=80.0)
    ap.add_argument("--sink_approach_K", type=float, default=0.0)

    ap.add_argument("--evap_min_C", type=float, default=-15.0)
    ap.add_argument("--evap_max_C", type=float, default=25.0)
    ap.add_argument("--cond_min_C", type=float, default=60.0)
    ap.add_argument("--cond_max_C", type=float, default=95.0)

    # compressor design eta
    ap.add_argument("--design_eta_s", type=float, default=0.85)

    return ap.parse_args()

def main():
    args = parse_args()

    cmap = ColumnMap(
        sheet_source=args.sheet_source,
        sheet_sink=args.sheet_sink,
        time_start_source=args.time_start_source,
        time_end_source=args.time_end_source,
        time_start_sink=args.time_start_sink,
        time_end_sink=args.time_end_sink,
        src_T_in=args.src_T_in,
        src_T_out=args.src_T_out,
        sink_T_in=args.sink_T_in,
        sink_T_out=args.sink_T_out,
        sink_Energy_kWh=args.sink_Energy_kWh,
        sink_Q_cond_kW=args.sink_Q_cond_kW,
        evap_approach_K=args.evap_approach_K,
        sink_setpoint_C=args.sink_setpoint_C,
        sink_approach_K=args.sink_approach_K,
        evap_min_C=args.evap_min_C, evap_max_C=args.evap_max_C,
        cond_min_C=args.cond_min_C, cond_max_C=args.cond_max_C,
    )

    out = run_pipeline(args.excel, args.outdir, cmap, design_eta_s=args.design_eta_s)
    plot_series(out, args.outdir)
    print(f"Done. Outputs saved to: {os.path.abspath(args.outdir)}")
