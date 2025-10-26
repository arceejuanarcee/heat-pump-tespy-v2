from dataclasses import dataclass
from typing import Optional

DEFAULT_FLUID = "R134a"

@dataclass
class ColumnMap:
    # --- Excel sheets ---
    sheet_source: str = "Heat source"
    sheet_sink: str = "Heat sink"

    # --- time columns (in each sheet) ---
    time_start_source: str = "start measurement"
    time_end_source: str = "end measurement"
    time_start_sink: str = "start measurement"
    time_end_sink: str = "end measurement"

    # --- plant-side columns ---
    # Source (cold side / evaporator loop)
    src_T_in: str = "T_in[degC]"
    src_T_out: Optional[str] = "T_out[degC]"

    # Sink (hot side / condenser loop)
    sink_T_in: Optional[str] = "T_in[degC]"
    sink_T_out: str = "T_out[degC]"
    sink_Energy_kWh: str = "Energy[kWh]"   # per interval; will be converted to kW if present
    sink_Q_cond_kW: Optional[str] = None   # if you already have instantaneous kW, set this

    # --- mapping parameters (plant → refrigerant targets) ---
    evap_approach_K: float = 5.0           # T_evap,ref = src_T_in - approach
    sink_setpoint_C: float = 80.0          # fallback condenser outlet if not using sink_T_out
    sink_approach_K: float = 0.0           # if >0, T_cond,ref = sink_T_out + approach

    # --- safety bounds (keeps valve physics valid) ---
    evap_min_C: float = -15.0
    evap_max_C: float = 25.0
    cond_min_C: float = 60.0
    cond_max_C: float = 95.0

def tespy_units_kwargs():
    return dict(T_unit="degC", p_unit="bar", h_unit="kJ / kg", Q_unit="kW", P_unit="kW")
