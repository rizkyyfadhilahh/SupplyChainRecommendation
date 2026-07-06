"""
Gap Analysis Service
====================
Handles buyer demand projection, supply baseline calculation,
and gap (shortfall) analysis for the Predictive Fulfillment feature.

All buyer data is currently seeded as dummy/mock data.
Real buyer data can be plugged in by replacing HistoricalBuyerData.BUYER_DATA.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from cachetools import cached, TTLCache

from app.config import CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PROJECTION_YEAR = 2026  # Current projection horizon per PRD


class HistoricalBuyerData:
    """
    Mock historical buyer data — 2 years of order history (2024–2025).
    Each buyer has:
      - max_pcf_limit  : Maximum accepted PCF (kg CO2e / kg product)
      - country        : Buyer HQ country
      - segment        : Industry segment
      - preferred_products: List of products they typically order
      - historical_orders : List of individual orders with date, product, quantity (ton)
    """

    BUYER_DATA: Dict[str, Dict[str, Any]] = {
        # ------------------------------------------------------------------ #
        # 1. Neste Oil (Finland) — biodiesel / SAF producer                  #
        # ------------------------------------------------------------------ #
        "Neste Oil": {
            "max_pcf_limit": 2.5,
            "country": "Finland",
            "segment": "Renewable Fuels",
            "preferred_products": ["CPO", "RBDPO"],
            "historical_orders": [
                {"date": "2024-01-15", "product": "CPO",   "quantity": 5000.0},
                {"date": "2024-03-10", "product": "CPO",   "quantity": 4500.0},
                {"date": "2024-06-20", "product": "RBDPO", "quantity": 3000.0},
                {"date": "2024-09-05", "product": "CPO",   "quantity": 5500.0},
                {"date": "2024-11-30", "product": "RBDPO", "quantity": 3500.0},
                {"date": "2025-01-10", "product": "CPO",   "quantity": 5200.0},
                {"date": "2025-04-20", "product": "RBDPO", "quantity": 3800.0},
                {"date": "2025-07-15", "product": "CPO",   "quantity": 5800.0},
                {"date": "2025-10-01", "product": "RBDPO", "quantity": 4000.0},
            ],
        },
        # ------------------------------------------------------------------ #
        # 2. Unilever (UK/Netherlands) — FMCG giant                          #
        # ------------------------------------------------------------------ #
        "Unilever": {
            "max_pcf_limit": 2.0,
            "country": "United Kingdom",
            "segment": "Consumer Goods",
            "preferred_products": ["RBDPO", "CPO", "CPKO"],
            "historical_orders": [
                {"date": "2024-01-20", "product": "RBDPO", "quantity": 6000.0},
                {"date": "2024-04-15", "product": "CPO",   "quantity": 4000.0},
                {"date": "2024-07-10", "product": "RBDPO", "quantity": 5500.0},
                {"date": "2024-10-05", "product": "CPO",   "quantity": 3500.0},
                {"date": "2025-01-25", "product": "RBDPO", "quantity": 6200.0},
                {"date": "2025-04-10", "product": "CPKO",  "quantity": 2000.0},
                {"date": "2025-07-20", "product": "RBDPO", "quantity": 5800.0},
                {"date": "2025-10-15", "product": "CPO",   "quantity": 4200.0},
            ],
        },
        # ------------------------------------------------------------------ #
        # 3. Reckitt Benckiser (UK) — personal care & hygiene                #
        # ------------------------------------------------------------------ #
        "Reckitt Benckiser": {
            "max_pcf_limit": 2.3,
            "country": "United Kingdom",
            "segment": "Personal Care",
            "preferred_products": ["CPO", "RBDPO"],
            "historical_orders": [
                {"date": "2024-02-10", "product": "CPO",   "quantity": 3500.0},
                {"date": "2024-05-20", "product": "RBDPO", "quantity": 4000.0},
                {"date": "2024-08-15", "product": "CPO",   "quantity": 3800.0},
                {"date": "2024-11-10", "product": "RBDPO", "quantity": 4200.0},
                {"date": "2025-02-05", "product": "CPO",   "quantity": 3600.0},
                {"date": "2025-05-15", "product": "RBDPO", "quantity": 4500.0},
                {"date": "2025-08-20", "product": "CPO",   "quantity": 3900.0},
            ],
        },
        # ------------------------------------------------------------------ #
        # 4. Cargill (USA) — commodity trading & food processing              #
        # ------------------------------------------------------------------ #
        "Cargill": {
            "max_pcf_limit": 2.8,
            "country": "United States",
            "segment": "Commodity Trading",
            "preferred_products": ["CPO", "PKO", "CPKO"],
            "historical_orders": [
                {"date": "2024-01-08", "product": "CPO",  "quantity": 8000.0},
                {"date": "2024-03-22", "product": "PKO",  "quantity": 2500.0},
                {"date": "2024-06-05", "product": "CPO",  "quantity": 7500.0},
                {"date": "2024-09-12", "product": "CPKO", "quantity": 3000.0},
                {"date": "2024-12-01", "product": "CPO",  "quantity": 8200.0},
                {"date": "2025-02-18", "product": "PKO",  "quantity": 2800.0},
                {"date": "2025-05-10", "product": "CPO",  "quantity": 7800.0},
                {"date": "2025-08-25", "product": "CPKO", "quantity": 3200.0},
                {"date": "2025-11-15", "product": "CPO",  "quantity": 8500.0},
            ],
        },
        # ------------------------------------------------------------------ #
        # 5. Wilmar International (Singapore) — largest palm oil processor   #
        # ------------------------------------------------------------------ #
        "Wilmar International": {
            "max_pcf_limit": 3.0,
            "country": "Singapore",
            "segment": "Agribusiness",
            "preferred_products": ["CPO", "RBDPO", "PKO"],
            "historical_orders": [
                {"date": "2024-02-01", "product": "CPO",   "quantity": 10000.0},
                {"date": "2024-04-18", "product": "RBDPO", "quantity": 7000.0},
                {"date": "2024-07-30", "product": "CPO",   "quantity": 9500.0},
                {"date": "2024-10-20", "product": "PKO",   "quantity": 3500.0},
                {"date": "2025-01-15", "product": "CPO",   "quantity": 10500.0},
                {"date": "2025-04-05", "product": "RBDPO", "quantity": 7500.0},
                {"date": "2025-07-10", "product": "CPO",   "quantity": 10200.0},
                {"date": "2025-10-28", "product": "PKO",   "quantity": 3800.0},
            ],
        },
        # ------------------------------------------------------------------ #
        # 6. AAK (Sweden) — specialty fats & vegetable oils                  #
        # ------------------------------------------------------------------ #
        "AAK": {
            "max_pcf_limit": 1.8,
            "country": "Sweden",
            "segment": "Specialty Fats",
            "preferred_products": ["RBDPO", "CPKO"],
            "historical_orders": [
                {"date": "2024-03-10", "product": "RBDPO", "quantity": 2800.0},
                {"date": "2024-06-25", "product": "CPKO",  "quantity": 1500.0},
                {"date": "2024-09-15", "product": "RBDPO", "quantity": 3000.0},
                {"date": "2024-12-10", "product": "CPKO",  "quantity": 1600.0},
                {"date": "2025-03-05", "product": "RBDPO", "quantity": 3200.0},
                {"date": "2025-06-20", "product": "CPKO",  "quantity": 1700.0},
                {"date": "2025-09-10", "product": "RBDPO", "quantity": 3100.0},
            ],
        },
        # ------------------------------------------------------------------ #
        # 7. Procter & Gamble (USA) — household & personal care              #
        # ------------------------------------------------------------------ #
        "Procter & Gamble": {
            "max_pcf_limit": 2.1,
            "country": "United States",
            "segment": "Consumer Goods",
            "preferred_products": ["RBDPO", "CPO"],
            "historical_orders": [
                {"date": "2024-01-30", "product": "RBDPO", "quantity": 4500.0},
                {"date": "2024-04-20", "product": "CPO",   "quantity": 3000.0},
                {"date": "2024-07-25", "product": "RBDPO", "quantity": 4800.0},
                {"date": "2024-11-05", "product": "CPO",   "quantity": 3200.0},
                {"date": "2025-02-12", "product": "RBDPO", "quantity": 5000.0},
                {"date": "2025-05-28", "product": "CPO",   "quantity": 3400.0},
                {"date": "2025-08-15", "product": "RBDPO", "quantity": 4700.0},
            ],
        },
        # ------------------------------------------------------------------ #
        # 8. BASF (Germany) — oleochemicals & specialty chemicals            #
        # ------------------------------------------------------------------ #
        "BASF": {
            "max_pcf_limit": 2.6,
            "country": "Germany",
            "segment": "Oleochemicals",
            "preferred_products": ["CPO", "PKO"],
            "historical_orders": [
                {"date": "2024-02-20", "product": "CPO",  "quantity": 4200.0},
                {"date": "2024-05-15", "product": "PKO",  "quantity": 1800.0},
                {"date": "2024-08-10", "product": "CPO",  "quantity": 4500.0},
                {"date": "2024-11-20", "product": "PKO",  "quantity": 2000.0},
                {"date": "2025-02-08", "product": "CPO",  "quantity": 4800.0},
                {"date": "2025-05-22", "product": "PKO",  "quantity": 2100.0},
                {"date": "2025-09-01", "product": "CPO",  "quantity": 4600.0},
            ],
        },
    }

    @staticmethod
    def get_buyer_data(buyer_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve historical buyer data."""
        return HistoricalBuyerData.BUYER_DATA.get(buyer_name)

    @staticmethod
    def get_all_buyers() -> List[str]:
        """Get list of all buyer names."""
        return list(HistoricalBuyerData.BUYER_DATA.keys())

    @staticmethod
    @cached(cache=TTLCache(maxsize=1024, ttl=CACHE_TTL_SECONDS))
    def get_buyer_profiles() -> List[Dict[str, Any]]:
        """
        Get enriched buyer profile list for frontend dropdown.
        Returns name, country, segment, max_pcf_limit, and preferred_products.
        """
        profiles = []
        for name, data in HistoricalBuyerData.BUYER_DATA.items():
            profiles.append({
                "name": name,
                "country": data.get("country", "—"),
                "segment": data.get("segment", "—"),
                "max_pcf_limit": data.get("max_pcf_limit", 2.5),
                "preferred_products": data.get("preferred_products", []),
            })
        return profiles


# ---------------------------------------------------------------------------
# Demand Projection Engine
# ---------------------------------------------------------------------------

class DemandProjectionEngine:
    """
    Projects future demand based on historical order patterns.
    Uses actual date span (months) for annualization — not order count.
    """

    @staticmethod
    def project_annual_demand(
        historical_orders: List[Dict[str, Any]],
        projection_year: int = _PROJECTION_YEAR,
    ) -> Dict[str, Any]:
        """
        Project annual demand based on historical orders.

        Annualization is based on the real date span (months) between
        the earliest and latest order, ensuring statistical correctness.
        If the span is < 1 month, defaults to 12 months to avoid inflate.

        Args:
            historical_orders : List of dicts with 'date', 'product', 'quantity'
            projection_year   : Target year for projection label

        Returns:
            Dict with projected quantities and product breakdown
        """
        if not historical_orders:
            return {
                "total_quantity": 0.0,
                "product_breakdown": {},
                "monthly_average": 0.0,
                "confidence_score": 0.0,
                "projection_year": projection_year,
            }

        # Parse dates robustly
        dates: List[datetime] = []
        for order in historical_orders:
            raw = order.get("date", "")
            try:
                dates.append(datetime.strptime(str(raw), "%Y-%m-%d"))
            except (ValueError, TypeError):
                pass

        # Compute month span from earliest to latest order
        if len(dates) >= 2:
            dates_sorted = sorted(dates)
            earliest, latest = dates_sorted[0], dates_sorted[-1]
            # Number of months: difference in years*12 + months
            month_span = max(
                (latest.year - earliest.year) * 12 + (latest.month - earliest.month),
                1,
            )
        else:
            month_span = 12  # default: assume 1 full year

        # Aggregate totals
        total_qty = sum(float(o.get("quantity", 0)) for o in historical_orders)
        product_breakdown: Dict[str, float] = {}
        for order in historical_orders:
            product = str(order.get("product", "CPO")).upper()
            qty = float(order.get("quantity", 0))
            product_breakdown[product] = product_breakdown.get(product, 0.0) + qty

        # Monthly average based on actual time span
        monthly_average = total_qty / month_span
        projected_annual = monthly_average * 12

        # Normalize product breakdown proportionally
        projected_breakdown = {
            p: round(qty / total_qty * projected_annual, 2)
            for p, qty in product_breakdown.items()
        }

        # Confidence: higher if more orders and longer span
        order_count = len(historical_orders)
        confidence = min(0.60 + (order_count / 20) * 0.25 + (month_span / 24) * 0.15, 0.99)

        return {
            "total_quantity": round(projected_annual, 2),
            "product_breakdown": projected_breakdown,
            "monthly_average": round(monthly_average, 2),
            "confidence_score": round(confidence, 2),
            "projection_year": projection_year,
            "history_month_span": month_span,
            "history_order_count": order_count,
        }


# ---------------------------------------------------------------------------
# Supply Baseline Calculator
# ---------------------------------------------------------------------------

class SupplyBaselineCalculator:
    """
    Calculates current annual supply baseline per refinery facility.
    Values are based on mock operational data; can be replaced by real
    stock/capacity data from the CSV pipeline.
    """

    # Monthly production capacity (ton) and current utilization per refinery
    # Note: utilization here reflects how much capacity is ALREADY committed to
    # existing contracts — leaving the remainder as "available" for new demand.
    FACILITY_BASELINE: Dict[str, Dict[str, float]] = {
        "Lubuk Gaung Refinery": {"monthly_capacity": 5500.0, "utilization": 0.72},
        "Lampung Refinery":     {"monthly_capacity": 6200.0, "utilization": 0.78},
        "Marunda Refinery":     {"monthly_capacity": 5800.0, "utilization": 0.68},
        "Belawan Refinery":     {"monthly_capacity": 4800.0, "utilization": 0.82},
        "Tarjun Refinery":      {"monthly_capacity": 5200.0, "utilization": 0.70},
        "Surabaya Refinery":    {"monthly_capacity": 7000.0, "utilization": 0.75},
    }

    # Fraction of total facility capacity reserved per buyer (simulates multiple buyers
    # sharing the same refinery — each buyer only gets a slice of available capacity).
    # In real deployments, this would come from contract data.
    BUYER_CAPACITY_SHARE: Dict[str, float] = {
        "Neste Oil":            0.75,   # ~75% of free capacity → MODERATE gap
        "Unilever":             0.85,   # large contract share → MODERATE/CRITICAL
        "Reckitt Benckiser":    0.80,
        "Cargill":              0.90,   # biggest buyer → CRITICAL at small facilities
        "Wilmar International": 1.10,   # demand exceeds any single facility's free cap
        "AAK":                  0.60,   # smaller buyer → MINOR or FULFILLED
        "Procter & Gamble":     0.72,
        "BASF":                 0.68,
    }

    @staticmethod
    def calculate_supply_baseline(facility: str, buyer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate annual supply baseline for a given facility.

        The available supply is calculated as:
            annual_capacity × (1 - utilization) × buyer_capacity_share

        This reflects that only the uncommitted capacity slice is available for
        the requesting buyer (since other buyers and existing contracts already
        consume the utilized portion).

        Args:
            facility   : Facility name (must match FACILITY_BASELINE keys)
            buyer_name : Optional buyer name to apply per-buyer capacity share

        Returns:
            Dict with capacity, utilization, and available supply fields
        """
        defaults = {"monthly_capacity": 5000.0, "utilization": 0.75}
        data = SupplyBaselineCalculator.FACILITY_BASELINE.get(facility, defaults)

        monthly_cap = float(data["monthly_capacity"])
        utilization = float(data["utilization"])
        annual_cap = monthly_cap * 12

        # Uncommitted (free) annual capacity
        free_annual_cap = annual_cap * (1.0 - utilization)

        # Apply buyer-specific share of free capacity
        buyer_share = SupplyBaselineCalculator.BUYER_CAPACITY_SHARE.get(
            buyer_name or "", 0.30
        )
        available_supply = free_annual_cap * buyer_share

        return {
            "facility": facility,
            "monthly_capacity_kg": monthly_cap,
            "annual_capacity_kg": round(annual_cap, 2),
            "current_utilization_rate": utilization,
            "available_supply_kg": round(available_supply, 2),
        }


# ---------------------------------------------------------------------------
# Gap Analysis Service  (main orchestrator)
# ---------------------------------------------------------------------------

class GapAnalysisService:
    """Core gap analysis engine — combines projection + baseline → gap."""

    @staticmethod
    def analyze_buyer_gap(
        buyer_name: str,
        facility: str,
    ) -> Dict[str, Any]:
        """
        Analyze supply-demand gap for a buyer × facility pair.

        Args:
            buyer_name : Name of the buyer (must exist in HistoricalBuyerData)
            facility   : Target refinery facility name

        Returns:
            Structured dict with projected_demand, supply_baseline, gap_analysis,
            and buyer meta (max_pcf_limit, etc.). Returns {"error": ...} on failure.
        """
        buyer_data = HistoricalBuyerData.get_buyer_data(buyer_name)
        if not buyer_data:
            return {
                "error": (
                    f"Buyer '{buyer_name}' not found. "
                    f"Available buyers: {HistoricalBuyerData.get_all_buyers()}"
                )
            }

        # --- Step 1: Project demand ---
        projection = DemandProjectionEngine.project_annual_demand(
            buyer_data["historical_orders"],
            projection_year=_PROJECTION_YEAR,
        )

        # --- Step 2: Baseline supply ---
        baseline = SupplyBaselineCalculator.calculate_supply_baseline(facility, buyer_name)

        # --- Step 3: Compute gap ---
        projected_demand: float = projection["total_quantity"]
        available_supply: float = baseline["available_supply_kg"]
        shortfall: float = max(projected_demand - available_supply, 0.0)
        fulfillment_rate: float = (
            (available_supply / projected_demand * 100.0)
            if projected_demand > 0
            else 0.0
        )
        fulfillment_rate = min(fulfillment_rate, 100.0)  # cap at 100%

        if shortfall <= 0:
            gap_status = "FULFILLED"
        elif shortfall > projected_demand * 0.30:
            gap_status = "CRITICAL"
        elif shortfall > projected_demand * 0.10:
            gap_status = "MODERATE"
        else:
            gap_status = "MINOR"

        return {
            "buyer_name": buyer_name,
            "facility": facility,
            "max_pcf_limit": float(buyer_data["max_pcf_limit"]),
            "segment": buyer_data.get("segment", "—"),
            "country": buyer_data.get("country", "—"),
            "preferred_products": buyer_data.get("preferred_products", []),
            "projected_demand": {
                "annual_kg": round(projected_demand, 2),
                "monthly_average_kg": round(projection["monthly_average"], 2),
                "product_breakdown": projection["product_breakdown"],
                "projection_year": projection["projection_year"],
                "confidence_score": projection["confidence_score"],
            },
            "supply_baseline": {
                "available_supply_kg": round(available_supply, 2),
                "monthly_capacity_kg": baseline["monthly_capacity_kg"],
                "utilization_rate": baseline["current_utilization_rate"],
            },
            "gap_analysis": {
                "fulfillment_rate_percent": round(fulfillment_rate, 2),
                "shortfall_kg": round(shortfall, 2),
                "shortfall_percentage": round(max(100.0 - fulfillment_rate, 0.0), 2),
                "gap_status": gap_status,
            },
        }

    @staticmethod
    def generate_fulfillment_routes(
        gap_analysis: Dict[str, Any],
        buyer_name: str,
        facility: str,
        metrics_calc: Any,
        pcf_service: Any,
    ) -> Dict[str, Any]:
        """
        Generate optimized 3-hop routes (Estate -> Mill -> Refinery) specifically to fulfill
        the identified supply gap. Includes all 4 enterprise metrics.
        """
        shortfall: float = float(gap_analysis["gap_analysis"]["shortfall_kg"])
        buyer_max_pcf: float = float(gap_analysis.get("max_pcf_limit", 2.5))

        product_breakdown: Dict[str, float] = gap_analysis["projected_demand"].get(
            "product_breakdown", {}
        )
        primary_product: str = (
            max(product_breakdown, key=lambda p: product_breakdown[p])
            if product_breakdown
            else "CPO"
        )

        route_base_volume = shortfall if shortfall > 0 else float(
            gap_analysis["projected_demand"]["annual_kg"]
        ) * 0.25

        buyer_hist = HistoricalBuyerData.get_buyer_data(buyer_name) or {}
        buyer_historical_volumes: List[float] = [
            float(o.get("quantity", 0))
            for o in buyer_hist.get("historical_orders", [])
            if float(o.get("quantity", 0)) > 0
        ] or [4500.0, 5000.0, 5500.0]

        def _build_route(
            route_id: str,
            route_label: str,
            optimization_focus: str,
            estate_id: str,
            estate_name: str,
            estate_type: str,
            mill_id: str,
            mill_name: str,
            volume_fraction: float,
            estate_to_mill_km: float,
            mill_to_refinery_km: float,
            estimated_days: int,
            fulfillment_share_pct: float,
        ) -> Dict[str, Any]:
            ffb_volume = route_base_volume * volume_fraction
            cpo_volume = ffb_volume * 0.20
            refined_volume = cpo_volume * 0.94

            tree: List[Dict[str, Any]] = [
                {
                    "level": 0,
                    "supplier_id": estate_id,
                    "supplier_name": estate_name,
                    "supplier_type": estate_type,
                    "receiver_id": mill_id,
                    "product": "FFB",
                    "quantity": round(ffb_volume, 2),
                    "estimated_days": 3,
                    "node_type": "estate",
                },
                {
                    "level": 1,
                    "supplier_id": mill_id,
                    "supplier_name": mill_name,
                    "supplier_type": "MILL",
                    "receiver_id": facility,
                    "product": primary_product,
                    "quantity": round(cpo_volume, 2),
                    "estimated_days": estimated_days - 3,
                    "node_type": "mill",
                },
                {
                    "level": 2,
                    "supplier_id": facility,
                    "supplier_name": facility,
                    "supplier_type": "REFINERY",
                    "receiver_id": "BUYER_" + buyer_name.upper().replace(" ", "_"),
                    "product": primary_product,
                    "quantity": round(refined_volume, 2),
                    "estimated_days": 2,
                    "node_type": "refinery",
                },
            ]

            pcf_total = pcf_service.calculate_tree_total_pcf(tree, facility)
            pcf_per_unit = (
                pcf_service.calculate_per_unit_pcf(tree, refined_volume, facility)
                if refined_volume > 0
                else 0.0
            )

            enterprise_metrics = metrics_calc.calculate_all_metrics(
                tree=tree,
                facility=facility,
                requested_quantity=refined_volume,
                pcf_total=pcf_total,
                pcf_per_unit=pcf_per_unit,
                buyer_historical_volumes=buyer_historical_volumes,
                buyer_max_pcf=buyer_max_pcf,
                route_distance_km=estate_to_mill_km + mill_to_refinery_km,
            )

            return {
                "route_id": route_id,
                "route_label": route_label,
                "facility": facility,
                "routed_volume_kg": round(refined_volume, 2),
                "supply_chain_path": tree,
                "enterprise_metrics": enterprise_metrics,
                "estimated_days": estimated_days,
                "fulfillment_share_percent": fulfillment_share_pct,
                "optimization_focus": optimization_focus,
            }

        route1 = _build_route(
            route_id="GAP-ROUTE-1",
            route_label="Volume-Optimized",
            optimization_focus="VOLUME",
            estate_id="ESTATE_SUMATERA_RAYA",
            estate_name="Estate Raya Lestari (Sumatra)",
            estate_type="ESTATE",
            mill_id="MILL_KUALA_TANJUNG",
            mill_name="Kuala Tanjung Processing Mill",
            volume_fraction=0.50,
            estate_to_mill_km=75.0,
            mill_to_refinery_km=380.0,
            estimated_days=8,
            fulfillment_share_pct=50.0,
        )

        route2 = _build_route(
            route_id="GAP-ROUTE-2",
            route_label="PCF-Optimized (Low Carbon)",
            optimization_focus="PCF",
            estate_id="ESTATE_CERTIFIED_ISCC",
            estate_name="Green Valley Estate (ISCC Certified)",
            estate_type="ESTATE",
            mill_id="MILL_DUMAI",
            mill_name="Dumai Integrated Processing Mill",
            volume_fraction=0.30,
            estate_to_mill_km=45.0,
            mill_to_refinery_km=290.0,
            estimated_days=6,
            fulfillment_share_pct=30.0,
        )

        route3 = _build_route(
            route_id="GAP-ROUTE-3",
            route_label="Distance-Optimized",
            optimization_focus="DISTANCE",
            estate_id="ESTATE_TRACEABLE_LESTARI",
            estate_name="Estate Lestari Jaya",
            estate_type="ESTATE",
            mill_id="MILL_BELAWAN",
            mill_name="Belawan Integrated Mill",
            volume_fraction=0.20,
            estate_to_mill_km=15.0,
            mill_to_refinery_km=110.0,
            estimated_days=2,
            fulfillment_share_pct=20.0,
        )

        recommended_routes: List[Dict[str, Any]] = [route1, route2, route3]

        total_routed = sum(r["routed_volume_kg"] for r in recommended_routes)
        projected_annual = float(gap_analysis["projected_demand"]["annual_kg"])
        combined_fulfillment = (
            (total_routed / projected_annual * 100.0) if projected_annual > 0 else 0.0
        )

        return {
            "gap_analysis": gap_analysis,
            "recommended_routes": recommended_routes,
            "total_routed_volume_kg": round(total_routed, 2),
            "combined_fulfillment_percent": round(min(combined_fulfillment, 100.0), 2),
        }


def get_gap_analysis_service() -> GapAnalysisService:
    """Factory — returns a fresh GapAnalysisService instance."""
    return GapAnalysisService()
