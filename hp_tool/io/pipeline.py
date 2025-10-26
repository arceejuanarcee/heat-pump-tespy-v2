# hp_tool/io/pipeline.py
from __future__ import annotations
from typing import Dict, Any, List
import os
import re
import pandas as pd
import numpy as np
from ..config import ColumnMap
from ..models.heat_pump import HeatPumpModel


# ========== Normalization / fuzzy matching ==========

def _norm(s: str) -> str:
    """Normalize a header for robust matching."""
    s = str(s)
    s = s.replace("°", "deg")
    s = s.strip().lower()
    s = re.sub(r"[\[\]\(\){}]", "", s)
    s = re.sub(r"\s+", "", s)
    return s

def _resolve(df: pd.DataFrame, desired: str, fallbacks: list[str]) -> str:
    """
    Try to find a column 'like' desired (or any of fallbacks) in df.
    Raises KeyError with a helpful message if not found.
    """
    cols = list(df.columns)
    nmap = {c: _norm(c) for c in cols}
    target = _norm(desired)

    # exact normalized match
    for c, n in nmap.items():
        if n == target:
            return c

    # substring matches for fallbacks
    for fb in [desired] + fallbacks:
        fb_n = _norm(fb)
        for c, n in nmap.items():
            if fb_n in n or n in fb_n:
                return c

    raise KeyError(
        f"Could not find a column like '{desired}' in sheet '{df.attrs.get('sheet','?')}'.\n"
        f"Available columns: {cols}"
    )


# ========== Time utilities ==========

def _mid_time(df: pd.DataFrame, start_col: str, end_col: str) -> pd.Series:
    """Midpoint timestamp between start and end measurement."""
    ts = pd.to_datetime(df[start_col], errors="coerce")
    te = pd.to_datetime(df[end_col], errors="coerce")
    return ts + (te - ts) / 2

def _infer_interval_hours(times: pd.Series) -> float:
    """Infer typical sampling interval (hours) from a timestamp series."""
    dt = times.sort_values().diff().dropna().dt.total_seconds() / 3600.0
    return float(np.median(dt)) if len(dt) else 1.0


# ========== Load + merge both sheets (robust) ==========

def _load_source_sink(excel_path: str, cmap: ColumnMap) -> pd.DataFrame:
    # Read sheets
    src = pd.read_excel(excel_path, sheet_name=cmap.sheet_source)
    snk = pd.read_excel(excel_path, sheet_name=cmap.sheet_sink)
    src.attrs["sheet"] = cmap.sheet_source
    snk.attrs["sheet"] = cmap.sheet_sink

    # Resolve required time columns
    src_start = _resolve(src, cmap.time_start_source, ["start", "startmeasurement", "begin"])
    src_end   = _resolve(src, cmap.time_end_source,   ["end", "endmeasurement", "finish"])
    snk_start = _resolve(snk, cmap.time_start_sink,   ["start", "startmeasurement", "begin"])
    snk_end   = _resolve(snk, cmap.time_end_sink,     ["end", "endmeasurement", "finish"])

    # Build mid-time stamps
    src["__time"] = _mid_time(src, src_start, src_end)
    snk["__time"] = _mid_time(snk, snk_start, snk_end)

    # Resolve plant-side columns (source loop)
    src_T_in  = _resolve(src, cmap.src_T_in,  ["tin", "source", "evap", "inlet"])
    src_T_out = None
    if cmap.src_T_out:
        try:
            src_T_out = _resolve(src, cmap.src_T_out, ["tout", "outlet", "evap"])
        except KeyError:
            src_T_out = None  # optional

    # Resolve plant-side columns (sink loop)
    sink_T_out = _resolve(snk, cmap.sink_T_out, ["tout", "sink", "cond", "outlet"])
    sink_T_in = None
    if cmap.sink_T_in:
        try:
            sink_T_in = _resolve(snk, cmap.sink_T_in, ["tin", "inlet", "return"])
        except KeyError:
            sink_T_in = None  # optional

    # Energy / Power columns on sink sheet
    sink_Q_kw = None
    if cmap.sink_Q_cond_kW:
        try:
            sink_Q_kw = _resolve(snk, cmap.sink_Q_cond_kW, ["q", "power", "kw"])
        except KeyError:
            sink_Q_kw = None

    sink_E_kwh = None
    if cmap.sink_Energy_kWh:
        try:
            sink_E_kwh = _resolve(snk, cmap.sink_Energy_kWh, ["energy", "kwh"])
        except KeyError:
            sink_E_kwh = None

    # Trim frames to what we need
    keep_src = ["__time", src_T_in] + ([src_T_out] if src_T_out else [])
    keep_snk = ["__time", sink_T_out] + ([sink_T_in] if sink_T_in else []) \
               + ([sink_Q_kw] if sink_Q_kw else []) + ([sink_E_kwh] if sink_E_kwh else [])
    src = src[keep_src].dropna(subset=["__time"])
    snk = snk[keep_snk].dropna(subset=["__time"])

    # Rename to standard internal names
    ren_src = {src_T_in: "_src_T_in"}
    if src_T_out: ren_src[src_T_out] = "_src_T_out"
    src = src.rename(columns=ren_src)

    ren_snk = {sink_T_out: "_sink_T_out"}
    if sink_T_in: ren_snk[sink_T_in] = "_sink_T_in"
    if sink_Q_kw: ren_snk[sink_Q_kw] = "_Q_cond_kW"
    if sink_E_kwh: ren_snk[sink_E_kwh] = "_Energy_kWh"
    snk = snk.rename(columns=ren_snk)

    # Merge by nearest timestamp
    src = src.sort_values("__time")
    snk = snk.sort_values("__time")
    df = pd.merge_asof(src, snk, on="__time", direction="nearest")

    # Convert kWh → kW if needed
    if "_Q_cond_kW" not in df.columns and "_Energy_kWh" in df.columns:
        interval_h = _infer_interval_hours(df["__time"])
        df["_Q_cond_kW"] = pd.to_numeric(df["_Energy_kWh"], errors="coerce") / max(interval_h, 1e-9)

    # Save interval for reference
    df["__interval_h"] = _infer_interval_hours(df["__time"])
    return df


# ========== Map plant temps → refrigerant targets ==========

def _derive_refrigerant_targets(df: pd.DataFrame, cmap: ColumnMap) -> pd.DataFrame:
    # Evaporator refrigerant (from source loop inlet)
    T_evap = pd.to_numeric(df["_src_T_in"], errors="coerce") - cmap.evap_approach_K
    T_evap = T_evap.clip(lower=cmap.evap_min_C, upper=cmap.evap_max_C)

    # Condenser refrigerant (from sink loop outlet + approach) or fixed setpoint
    if cmap.sink_approach_K > 0.0 and "_sink_T_out" in df.columns:
        T_cond = pd.to_numeric(df["_sink_T_out"], errors="coerce") + cmap.sink_approach_K
    else:
        T_cond = pd.Series(cmap.sink_setpoint_C, index=df.index)
    T_cond = T_cond.clip(lower=cmap.cond_min_C, upper=cmap.cond_max_C)

    return df.assign(_T_source_ref_C=T_evap, _T_sink_ref_C=T_cond)


# ========== Design heuristic & logging ==========

def _design_from_df(df: pd.DataFrame, design_eta_s: float) -> Dict[str, float]:
    T_source = float(df["_T_source_ref_C"].dropna().iloc[0])
    T_sink   = float(df["_T_sink_ref_C"].dropna().iloc[0])
    Q_cond = float(df["_Q_cond_kW"].median()) if "_Q_cond_kW" in df and df["_Q_cond_kW"].notna().any() else 1000.0
    return dict(T_source_C=T_source, T_sink_C=T_sink, Q_cond_kW=Q_cond, eta_s=design_eta_s)

def _write_design_summary(outdir: str, design: Dict[str, float]) -> None:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "design_summary.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("TESPy Heat Pump — Design Condition\n")
        f.write("----------------------------------\n")
        for k, v in design.items():
            f.write(f"{k:15s}: {v}\n")


# ========== Main pipeline ==========

def run_pipeline(excel_path: str,
                 outdir: str,
                 cmap: ColumnMap,
                 design_eta_s: float = 0.85,
                 save_csv: str = "hp_timeseries.csv") -> pd.DataFrame:
    """
    Load 'Heat source' + 'Heat sink', align by time, convert Energy→Power, map plant temps
    to refrigerant targets, run TESPy design + off-design, save CSV and a design summary.
    """
    # 1) Load & merge both sheets
    df = _load_source_sink(excel_path, cmap)

    # 2) Derive refrigerant targets (evap/condenser)
    df = _derive_refrigerant_targets(df, cmap)

    # 3) Build TESPy model, compute design, save state
    hp = HeatPumpModel().build_network()
    design = _design_from_df(df, design_eta_s)

    # Print & save design condition so you can verify it
    print("\n--- Design Condition ---")
    for k, v in design.items():
        print(f"{k:15s}: {v}")
    print("------------------------\n")
    _write_design_summary(outdir, design)

    hp.set_design_point(**design).solve_design().save_design_state()

    # 4) Time series off-design
    rows: List[Dict[str, Any]] = []

    # Tiny shim: map our internal column names to what HeatPumpModel expects
    class _Shim:
        T_source_C = "_T_source_ref_C"
        T_sink_C   = "_T_sink_ref_C"
        Q_cond_kW  = "_Q_cond_kW"
        eta_s_pct  = None

    for _, row in df.iterrows():
        hp.apply_row_specs(row, _Shim, fallback_eta_s=design["eta_s"], allow_vary_Q=True)
        hp.solve_offdesign()
        rows.append({**row.to_dict(), **hp.metrics()})

    out = pd.DataFrame(rows)
    os.makedirs(outdir, exist_ok=True)
    out.to_csv(os.path.join(outdir, save_csv), index=False)
    return out
