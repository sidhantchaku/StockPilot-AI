import pandas as pd
import unittest

from core_logic import calculate_reorder_metrics, optimize_transfer_plan, prepare_prophet_timeseries


class CoreLogicTests(unittest.TestCase):
    def test_prepare_prophet_timeseries_requires_multiple_time_points(self):
        df = pd.DataFrame({"date": ["2026-01-01"], "qty": [10]})
        with self.assertRaises(ValueError):
            prepare_prophet_timeseries(df, "date", "qty")

    def test_reorder_metrics_triggers_order_when_stock_is_low(self):
        metrics = calculate_reorder_metrics(
            current_stock=20,
            forecast_daily_demand=8,
            demand_std=3,
            lead_time_days=7,
            service_level=0.95,
        )
        self.assertGreater(metrics["reorder_point"], 20)
        self.assertGreater(metrics["recommended_order_qty"], 0)

    def test_optimize_transfer_plan_returns_routes(self):
        geo = pd.DataFrame(
            [
                {"Area": "A", "lat": 19.07, "lon": 72.87, "SurplusDeficit": 120, "EstDemand7d": 60, "Stock": 200},
                {"Area": "B", "lat": 12.97, "lon": 77.59, "SurplusDeficit": -80, "EstDemand7d": 120, "Stock": 40},
            ]
        )
        mode_profiles = {"🚛 Van": {"co2": 2.0, "cost": 1.2}}
        plan_df, coverage_df, totals = optimize_transfer_plan(
            geo_df=geo,
            area_col="Area",
            mode_profiles=mode_profiles,
            mode_strategy="🚛 Van",
            weight_cost=0.5,
            weight_co2=0.3,
            weight_risk=0.2,
            max_total_cost=None,
            max_total_co2=None,
            max_qty_per_route=100,
            min_fill_ratio=0.5,
        )
        self.assertFalse(plan_df.empty)
        self.assertFalse(coverage_df.empty)
        self.assertGreater(totals["qty"], 0)

    def test_optimize_transfer_plan_respects_budget_constraint(self):
        geo = pd.DataFrame(
            [
                {"Area": "A", "lat": 19.07, "lon": 72.87, "SurplusDeficit": 120, "EstDemand7d": 60, "Stock": 200},
                {"Area": "B", "lat": 12.97, "lon": 77.59, "SurplusDeficit": -80, "EstDemand7d": 120, "Stock": 40},
            ]
        )
        mode_profiles = {"🚚 Truck": {"co2": 3.0, "cost": 1000.0}}
        plan_df, _, totals = optimize_transfer_plan(
            geo_df=geo,
            area_col="Area",
            mode_profiles=mode_profiles,
            mode_strategy="🚚 Truck",
            weight_cost=1.0,
            weight_co2=0.0,
            weight_risk=0.0,
            max_total_cost=50.0,
            max_total_co2=None,
            max_qty_per_route=100,
            min_fill_ratio=0.5,
        )
        self.assertTrue(plan_df.empty)
        self.assertEqual(totals["qty"], 0)

if __name__ == "__main__":
    unittest.main()
