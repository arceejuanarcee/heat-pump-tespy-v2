import os
import matplotlib.pyplot as plt
import pandas as pd


def plot_series(df: pd.DataFrame, outdir: str) -> None:
    """
    Plot COP, compressor power, and heat-transfer rates.
    If a '__time' column exists, it will be used for the x-axis.
    """
    os.makedirs(outdir, exist_ok=True)

    # Prefer real timestamps if available
    if "__time" in df.columns:
        x = pd.to_datetime(df["__time"], errors="coerce")
        x_label = "Time"
    else:
        x = df.index
        x_label = "Index"

    # --- COP plot ---
    plt.figure()
    plt.plot(x, df["COP"], lw=1.5)
    plt.title("COP over Time")
    plt.xlabel(x_label)
    plt.ylabel("COP")
    plt.grid(True)
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "plot_COP.png"), dpi=180)

    # --- Compressor Power ---
    plt.figure()
    plt.plot(x, df["P_comp_kW"], lw=1.5)
    plt.title("Compressor Power over Time")
    plt.xlabel(x_label)
    plt.ylabel("P_comp [kW]")
    plt.grid(True)
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "plot_P_comp.png"), dpi=180)

    # --- Heat Transfer Rates ---
    plt.figure()
    plt.plot(x, df["Q_evap_kW"], label="Q_evap_kW", lw=1.5)
    plt.plot(x, df["Q_cond_kW"], label="Q_cond_kW", lw=1.5)
    plt.title("Heat Transfer Rates over Time")
    plt.xlabel(x_label)
    plt.ylabel("Q [kW]")
    plt.grid(True)
    plt.legend()
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "plot_Q.png"), dpi=180)

    plt.close('all')
