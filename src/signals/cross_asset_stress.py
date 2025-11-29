import pandas as pd
import numpy as np
from typing import Dict, Any, Union


def calculate_cross_asset_signal(
    credit_spreads: pd.DataFrame,
    vix: pd.Series,
    oas_jump_bps: float = 15,
    stress_z: float = 2.0,
    vix_z: float = 2.0,
    window: int = 20,  # Short window for stress moves
    return_series: bool = False
) -> Union[Dict[str, Any], pd.DataFrame]:
  """
  Calculates Cross-Asset Stress Overlay.
  Global signal, applies to all tickers usually, or used as a filter.

  Args:
      credit_spreads: DataFrame with 'IG_OAS', 'HY_OAS'.
      vix: Series of VIX closes.
      return_series: If True, returns Series of Stress Score (0 or 1 usually, or continuous).

  Returns:
      Dictionary with a single 'global' key, or Series if return_series=True.
  """

  # 1. Credit Spreads
  # Delta OAS (Daily change in bps)
  # IG_OAS is usually in percent (e.g. 1.50 for 1.50%). bps = diff * 100.

  if credit_spreads.empty:
    if return_series:
      return pd.Series(0, index=vix.index if not vix.empty else [])
    return {"GLOBAL": {"name": "Cross-Asset", "value": 0, "triggered": False, "details": "No Credit Data"}}

  # Ensure we have data
  ig_oas = credit_spreads.get('IG_OAS')
  hy_oas = credit_spreads.get('HY_OAS')

  # Calculate continuous stress score for backtesting
  # Simple boolean OR logic mapped to 0/1, or sum of Z-scores?
  # Let's create a composite stress signal:
  # Stress = (IG_Z > 2) | (VIX_Z > 2) | (OAS_Jump > 15)

  # Calculate components separately and sum at the end to avoid in-place `+=` issues.
  ig_z_stress = pd.Series(0.0, index=credit_spreads.index)
  ig_jump_stress = pd.Series(0.0, index=credit_spreads.index)
  vix_stress = pd.Series(0.0, index=credit_spreads.index)

  if ig_oas is not None:
    ig_mean = ig_oas.rolling(window=126).mean()
    ig_std = ig_oas.rolling(window=126).std()
    ig_z = (ig_oas - ig_mean) / ig_std
    ig_z_stress = (ig_z > stress_z).astype(float)

    # Add stress if Jump > threshold
    ig_jump = ig_oas.diff() * 100
    ig_jump_stress = (ig_jump > oas_jump_bps).astype(float)

  if not vix.empty:
    # Align VIX index
    vix = vix.reindex(credit_spreads.index).ffill()
    vix_mean = vix.rolling(window=126).mean()
    vix_std = vix.rolling(window=126).std()
    vix_z_series = (vix - vix_mean) / vix_std
    vix_stress = (vix_z_series > vix_z).astype(float)

  # Cap at 1.0 or keep as intensity?
  # Scorer expects ~2.0 for triggered.
  # Let's just return the raw intensity (0, 1, 2, 3...)
  stress_series = (ig_z_stress + ig_jump_stress + vix_stress).fillna(0)

  if return_series:
    return stress_series

  triggered_reasons = []

  # OAS Jump
  if ig_oas is not None:
    ig_change_bps = ig_oas.diff().iloc[-1] * 100
    if pd.notna(ig_change_bps) and ig_change_bps >= oas_jump_bps:
      triggered_reasons.append(f"IG OAS +{ig_change_bps:.0f}bps")

  if hy_oas is not None:
    hy_change_bps = hy_oas.diff().iloc[-1] * 100
    if pd.notna(hy_change_bps) and hy_change_bps >= oas_jump_bps:
      triggered_reasons.append(f"HY OAS +{hy_change_bps:.0f}bps")

  # OAS Z-Score
  # Using IG as primary proxy for stress
  if ig_oas is not None:
    curr_ig_z = ig_z.iloc[-1] if not ig_z.empty else np.nan

    if pd.notna(curr_ig_z) and curr_ig_z >= stress_z:
      triggered_reasons.append(f"IG Stress Z: {curr_ig_z:.2f}")

  # VIX Z-Score
  if not vix.empty:
    curr_vix_z = vix_z_series.iloc[-1] if not vix_z_series.empty else np.nan

    if pd.notna(curr_vix_z) and curr_vix_z >= vix_z:
      triggered_reasons.append(f"VIX Z: {curr_vix_z:.2f}")

  triggered = len(triggered_reasons) > 0

  return {
      "GLOBAL": {
          "name": "Cross-Asset Stress",
          "value": 1.0 if triggered else 0.0,
          "zscore": None,  # Aggregate
          "triggered": triggered,
          "details": ", ".join(triggered_reasons) if triggered else "Normal"
      }
  }
