#created with love by Sidhant Chaku

import math
from statistics import NormalDist

import pandas as pd


def haversine(lat1, lon1, lat2, lon2):
    radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def prepare_prophet_timeseries(df: pd.DataFrame, ds_col: str, y_col: str) -> pd.DataFrame:
    ts = df[[ds_col, y_col]].rename(columns={ds_col: "ds", y_col: "y"}).copy()
    ts["ds"] = pd.to_datetime(ts["ds"], errors="coerce")
    ts["y"] = pd.to_numeric(ts["y"], errors="coerce")
    ts = ts.dropna(subset=["ds", "y"]).sort_values("ds")
    if ts["ds"].nunique() < 2:
        raise ValueError("Need at least two time points for forecasting.")
    return ts


def calculate_reorder_metrics(
    current_stock: float,
    forecast_daily_demand: float,
    demand_std: float,
    lead_time_days: int,
    service_level: float,
) -> dict:
    lead_time_days = max(int(lead_time_days), 1)
    service_level = min(max(float(service_level), 0.50), 0.999)
    forecast_daily_demand = max(float(forecast_daily_demand), 0.0)
    demand_std = max(float(demand_std), 0.0)
    z_score = float(NormalDist().inv_cdf(service_level))
    lead_time_demand = forecast_daily_demand * lead_time_days
    safety_stock = z_score * demand_std * math.sqrt(lead_time_days)
    reorder_point = max(int(round(lead_time_demand + safety_stock)), 0)
    recommended_order_qty = max(int(round(reorder_point - float(current_stock))), 0)
    return {
        "z_score": z_score,
        "lead_time_demand": lead_time_demand,
        "safety_stock": safety_stock,
        "reorder_point": reorder_point,
        "recommended_order_qty": recommended_order_qty,
    }


def optimize_transfer_plan(
    geo_df: pd.DataFrame,
    area_col: str,
    mode_profiles: dict,
    mode_strategy: str,
    weight_cost: float,
    weight_co2: float,
    weight_risk: float,
    max_total_cost: float | None,
    max_total_co2: float | None,
    max_qty_per_route: int,
    min_fill_ratio: float,
):
    modes = list(mode_profiles.keys()) if mode_strategy == "Auto (Best Mix)" else [mode_strategy]

    surplus_df = geo_df[geo_df["SurplusDeficit"] > 0].copy()
    deficit_df = geo_df[geo_df["SurplusDeficit"] < 0].copy()
    if surplus_df.empty or deficit_df.empty:
        return pd.DataFrame(), pd.DataFrame(), {"cost": 0.0, "co2": 0.0, "qty": 0}

    deficit_df["NeedQty"] = deficit_df["SurplusDeficit"].abs()
    demand_scale = deficit_df["EstDemand7d"].replace(0, 1)
    need_norm = deficit_df["NeedQty"] / max(float(deficit_df["NeedQty"].max()), 1.0)
    risk_norm = (deficit_df["NeedQty"] / demand_scale) / max(float((deficit_df["NeedQty"] / demand_scale).max()), 1.0)
    deficit_df["Priority"] = (weight_risk * risk_norm) + ((1 - weight_risk) * need_norm)
    deficit_df = deficit_df.sort_values("Priority", ascending=False)

    surplus_state = [
        {
            "area": row[area_col],
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "available": float(row["SurplusDeficit"]),
        }
        for _, row in surplus_df.iterrows()
    ]
    deficit_state = [
        {
            "area": row[area_col],
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "need_total": float(row["NeedQty"]),
            "need_remaining": float(row["NeedQty"]),
            "target_remaining": float(row["NeedQty"] * min_fill_ratio),
            "priority": float(row["Priority"]),
        }
        for _, row in deficit_df.iterrows()
    ]

    total_cost = 0.0
    total_co2 = 0.0
    total_qty = 0
    routes = []

    for phase in ["target", "full"]:
        for deficit in deficit_state:
            remaining = deficit["target_remaining"] if phase == "target" else deficit["need_remaining"]
            while remaining > 0:
                candidates = []
                for s_idx, surplus in enumerate(surplus_state):
                    if surplus["available"] <= 0:
                        continue
                    qty = min(surplus["available"], remaining, max_qty_per_route)
                    if qty <= 0:
                        continue
                    distance = haversine(surplus["lat"], surplus["lon"], deficit["lat"], deficit["lon"])
                    for mode in modes:
                        route_cost = distance * mode_profiles[mode]["cost"]
                        route_co2 = distance * mode_profiles[mode]["co2"]
                        if max_total_cost is not None and (total_cost + route_cost) > max_total_cost:
                            continue
                        if max_total_co2 is not None and (total_co2 + route_co2) > max_total_co2:
                            continue
                        candidates.append(
                            {
                                "surplus_idx": s_idx,
                                "mode": mode,
                                "qty": int(qty),
                                "distance": distance,
                                "cost": route_cost,
                                "co2": route_co2,
                            }
                        )

                if not candidates:
                    break

                min_cost = min(c["cost"] for c in candidates)
                max_cost = max(c["cost"] for c in candidates)
                min_co2 = min(c["co2"] for c in candidates)
                max_co2 = max(c["co2"] for c in candidates)
                cost_span = (max_cost - min_cost) or 1.0
                co2_span = (max_co2 - min_co2) or 1.0

                def candidate_score(candidate):
                    cost_norm = (candidate["cost"] - min_cost) / cost_span
                    co2_norm = (candidate["co2"] - min_co2) / co2_span
                    return (weight_cost * cost_norm) + (weight_co2 * co2_norm)

                best = min(candidates, key=candidate_score)
                source = surplus_state[best["surplus_idx"]]

                source["available"] -= best["qty"]
                deficit["need_remaining"] -= best["qty"]
                deficit["target_remaining"] = max(deficit["target_remaining"] - best["qty"], 0)
                remaining = deficit["target_remaining"] if phase == "target" else deficit["need_remaining"]

                total_cost += best["cost"]
                total_co2 += best["co2"]
                total_qty += best["qty"]
                routes.append(
                    {
                        "From": source["area"],
                        "To": deficit["area"],
                        "Qty": int(best["qty"]),
                        "Mode": best["mode"],
                        "Dist(mi)": round(best["distance"], 1),
                        "Cost($)": round(best["cost"], 2),
                        "CO2(lb)": round(best["co2"], 2),
                        "Priority": round(deficit["priority"], 3),
                    }
                )

    coverage = []
    for deficit in deficit_state:
        moved = deficit["need_total"] - deficit["need_remaining"]
        coverage_pct = 0 if deficit["need_total"] == 0 else (moved / deficit["need_total"]) * 100
        coverage.append(
            {
                "DeficitArea": deficit["area"],
                "NeedQty": int(deficit["need_total"]),
                "MovedQty": int(moved),
                "Coverage(%)": round(coverage_pct, 1),
                "Priority": round(deficit["priority"], 3),
            }
        )

    return (
        pd.DataFrame(routes),
        pd.DataFrame(coverage).sort_values(["Priority", "Coverage(%)"], ascending=[False, True]),
        {"cost": total_cost, "co2": total_co2, "qty": int(total_qty)},
    )
