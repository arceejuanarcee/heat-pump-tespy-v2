from __future__ import annotations
from typing import Dict, Any, Optional
from tespy.networks import Network
from tespy.components import CycleCloser, Compressor, Valve, SimpleHeatExchanger
from tespy.connections import Connection
from ..config import DEFAULT_FLUID, tespy_units_kwargs, ColumnMap
import pandas as pd

def _safe_get(row: pd.Series, col: Optional[str], default: Optional[float]):
    if col is None:
        return default
    if col not in row or pd.isna(row[col]):
        return default
    try:
        return float(row[col])
    except Exception:
        return default

class HeatPumpModel:
    def __init__(self, fluid: str = DEFAULT_FLUID):
        self.fluid = fluid
        self.nw: Optional[Network] = None
        self.cc: Optional[CycleCloser] = None
        self.co: Optional[SimpleHeatExchanger] = None
        self.ev: Optional[SimpleHeatExchanger] = None
        self.va: Optional[Valve] = None
        self.cp: Optional[Compressor] = None
        self.c1 = self.c2 = self.c3 = self.c4 = self.c0 = None
        self.design_saved = False
        self.design_path = "design_state"

    # --- Build ---
    def build_network(self) -> "HeatPumpModel":
        self.nw = Network()
        self.nw.set_attr(**tespy_units_kwargs())

        self.cc = CycleCloser("cycle closer")
        self.co = SimpleHeatExchanger("condenser")
        self.ev = SimpleHeatExchanger("evaporator")
        self.va = Valve("expansion valve")
        self.cp = Compressor("compressor")

        self.c1 = Connection(self.cc, "out1", self.ev, "in1", label="1")
        self.c2 = Connection(self.ev, "out1", self.cp, "in1", label="2")
        self.c3 = Connection(self.cp, "out1", self.co, "in1", label="3")
        self.c4 = Connection(self.co, "out1", self.va, "in1", label="4")
        self.c0 = Connection(self.va, "out1", self.cc, "in1", label="0")
        self.nw.add_conns(self.c1, self.c2, self.c3, self.c4, self.c0)

        self.co.set_attr(pr=0.98)
        self.ev.set_attr(pr=0.98)
        self.c2.set_attr(fluid={self.fluid: 1.0}, x=1)  # sat. vapor
        self.c4.set_attr(x=0)                           # liquid
        self.cp.set_attr(eta_s=0.85)
        return self

    # --- Specs ---
    def set_design_point(self, T_source_C: float, T_sink_C: float, Q_cond_kW: float, eta_s: float) -> "HeatPumpModel":
        assert self.nw is not None
        self.cp.set_attr(eta_s=eta_s)
        # TESPy condenser sign: heat rejected by working fluid is negative
        self.co.set_attr(Q=-abs(Q_cond_kW))
        self.c2.set_attr(T=T_source_C)
        self.c4.set_attr(T=T_sink_C)
        return self

    # --- Solve ---
    def solve_design(self) -> "HeatPumpModel":
        self.nw.solve(mode="design")
        return self

    def save_design_state(self) -> "HeatPumpModel":
        self.nw.save(self.design_path)
        self.design_saved = True
        return self

    def apply_row_specs(self, row: pd.Series, cmap: ColumnMap, fallback_eta_s: float,
                        allow_vary_Q: bool = True) -> None:
        T_src = _safe_get(row, cmap.T_source_C, self.c2.T.val)
        T_sink = _safe_get(row, cmap.T_sink_C, self.c4.T.val)
        self.c2.set_attr(T=T_src)
        self.c4.set_attr(T=T_sink)

        eta_pct = _safe_get(row, cmap.eta_s_pct, None)
        self.cp.set_attr(eta_s=(eta_pct / 100.0) if eta_pct is not None else fallback_eta_s)

        if allow_vary_Q and cmap.Q_cond_kW:
            q = _safe_get(row, cmap.Q_cond_kW, None)
            if q is not None:
                self.co.set_attr(Q=-abs(q))

    def solve_offdesign(self) -> "HeatPumpModel":
        if self.design_saved:
            self.nw.solve(mode="offdesign", design_path=self.design_path)
        else:
            self.nw.solve(mode="design")
        return self

    # --- Metrics ---
    def metrics(self) -> Dict[str, Any]:
        P = self.cp.P.val
        Qc = self.co.Q.val
        Qe = self.ev.Q.val
        m = self.c1.m.val
        cop = abs(Qc) / P if P not in (None, 0) else float("nan")
        return {
            "m_dot_kg_s": m,
            "P_comp_kW": P,
            "Q_cond_kW": Qc,
            "Q_evap_kW": Qe,
            "COP": cop,
            "T2_C": self.c2.T.val if self.c2.T.is_set else None,
            "T4_C": self.c4.T.val if self.c4.T.is_set else None,
        }
