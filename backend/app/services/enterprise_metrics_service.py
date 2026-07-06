# filepath: backend/app/services/enterprise_metrics_service.py
import logging
from typing import Any, Dict, List, Optional
import random

logger = logging.getLogger(__name__)


class EnterpriseMetricsCalculator:
    """Calculates 4 core enterprise metrics for supply chain routes."""
    
    @staticmethod
    def calculate_capacity_constraint(
        facility: str,
        requested_quantity: float,
        current_utilization: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Calculate capacity constraint metric.
        
        Args:
            facility: Facility name
            requested_quantity: Quantity being requested
            current_utilization: Current facility utilization (0-1)
        
        Returns:
            Capacity constraint data with warning state
        """
        # Mock facility capacities
        facility_capacities = {
            "Lubuk Gaung Refinery": 3500.0,
            "Lampung Refinery": 4000.0,
            "Marunda Refinery": 3800.0,
            "Belawan Refinery": 3200.0,
            "Tarjun Refinery": 3600.0,
            "Surabaya Refinery": 4200.0,
        }
        
        capacity = facility_capacities.get(facility, 3500.0)
        additional_load = (requested_quantity / capacity) * 100
        projected_utilization = (current_utilization + (additional_load / 100)) * 100
        
        warning_state = "CRITICAL" if projected_utilization > 95 else "WARNING" if projected_utilization > 90 else "NORMAL"
        
        return {
            "facility": facility,
            "current_capacity_percent": round(current_utilization * 100, 2),
            "additional_load_percent": round(additional_load, 2),
            "projected_utilization_percent": round(projected_utilization, 2),
            "warning_state": warning_state,
            "can_fulfill": projected_utilization <= 100,
        }
    
    @staticmethod
    def calculate_route_distance(
        route_distance_km: float,
    ) -> Dict[str, Any]:
        """
        Calculate route distance metric.
        Shorter distances yield higher efficiency scores.
        
        Args:
            route_distance_km: Total distance in km
        
        Returns:
            Distance metric data
        """
        # Base efficiency score (assume 1000km is 0% efficient, 0km is 100% efficient)
        efficiency_score = max(100 - (route_distance_km / 10), 10)
        
        return {
            "total_distance_km": round(route_distance_km, 2),
            "efficiency_score_percent": round(efficiency_score, 2),
            "efficiency_level": "HIGH" if efficiency_score >= 80 else "MEDIUM" if efficiency_score >= 60 else "LOW",
        }
    
    @staticmethod
    def calculate_volume_similarity(
        routed_volume: float,
        historical_patterns: List[float],
    ) -> Dict[str, Any]:
        """
        Calculate historical volume similarity (0-100%).
        Measures how the routed volume aligns with successful historical patterns.
        
        Args:
            routed_volume: Volume being routed
            historical_patterns: List of historical successful volumes
        
        Returns:
            Volume similarity data
        """
        if not historical_patterns:
            historical_patterns = [4500.0, 5000.0, 5500.0]
        
        # Calculate average historical volume
        avg_historical = sum(historical_patterns) / len(historical_patterns)
        
        # Calculate deviation percentage
        deviation = abs(routed_volume - avg_historical) / avg_historical if avg_historical > 0 else 0
        
        # Convert to similarity score (lower deviation = higher similarity)
        similarity_score = max(100 - (deviation * 100), 0)
        
        return {
            "volume_similarity_percent": round(similarity_score, 2),
            "routed_volume_kg": routed_volume,
            "historical_average_kg": round(avg_historical, 2),
            "deviation_percent": round(deviation * 100, 2),
            "risk_level": "LOW" if similarity_score >= 75 else "MEDIUM" if similarity_score >= 50 else "HIGH",
        }
    
    @staticmethod
    def calculate_all_metrics(
        tree: List[Dict[str, Any]],
        facility: str,
        requested_quantity: float,
        pcf_total: float,
        pcf_per_unit: float,
        buyer_historical_volumes: Optional[List[float]] = None,
        buyer_max_pcf: Optional[float] = None,
        route_distance_km: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculate all 4 enterprise metrics for a route.
        
        Args:
            tree: Supply chain tree/path
            facility: Destination facility
            requested_quantity: Volume being routed
            pcf_total: Total PCF for this route
            pcf_per_unit: PCF per unit
            buyer_historical_volumes: Historical volumes for similarity calc
            buyer_max_pcf: Buyer's maximum PCF tolerance (for compliance check)
            route_distance_km: Total distance of the route in km
        
        Returns:
            All 4 enterprise metrics bundled
        """
        # Metric 1: PCF Score — include buyer-specific PCF limit if provided
        benchmark_limit = 2.5
        pcf_benchmark_compliance = (
            "COMPLIANT" if pcf_per_unit <= benchmark_limit else "AT_RISK"
        )
        pcf_metric: Dict[str, Any] = {
            "metric_name": "Universal PCF Score",
            "pcf_total_kg_co2e": round(pcf_total, 2),
            "pcf_per_unit_kg_co2e_per_kg": round(pcf_per_unit, 4),
            "benchmark_compliance": pcf_benchmark_compliance,
        }
        if buyer_max_pcf is not None:
            pcf_metric["buyer_pcf_limit"] = round(float(buyer_max_pcf), 2)
            pcf_metric["buyer_compliance"] = (
                "WITHIN_LIMIT" if pcf_per_unit <= float(buyer_max_pcf) else "EXCEEDS_LIMIT"
            )
        
        # Metric 2: Capacity Constraints
        path_length = len(tree)
        current_util = 0.75 if path_length <= 3 else 0.80 if path_length <= 5 else 0.85
        capacity_metric = EnterpriseMetricsCalculator.calculate_capacity_constraint(
            facility, requested_quantity, current_util
        )
        
        # Metric 3: Route Distance
        distance_metric = EnterpriseMetricsCalculator.calculate_route_distance(
            route_distance_km
        )
        
        # Metric 4: Historical Volume Similarity
        if not buyer_historical_volumes:
            buyer_historical_volumes = [4500.0, 5000.0, 5500.0]
        volume_metric = EnterpriseMetricsCalculator.calculate_volume_similarity(
            requested_quantity, buyer_historical_volumes
        )
        
        return {
            "metrics": {
                "pcf_score": pcf_metric,
                "capacity_constraints": capacity_metric,
                "route_distance": distance_metric,
                "volume_similarity": volume_metric,
            },
            "overall_score": round(
                (
                    (100 - min(pcf_per_unit / 2.5 * 100, 100)) * 0.25 +
                    (100 - min(capacity_metric["projected_utilization_percent"], 100)) * 0.25 +
                    distance_metric["efficiency_score_percent"] * 0.25 +
                    volume_metric["volume_similarity_percent"] * 0.25
                ),
                2
            ),
            "recommendation": "OPTIMAL" if (
                capacity_metric["warning_state"] == "NORMAL" and
                distance_metric["efficiency_level"] == "HIGH" and
                volume_metric["risk_level"] == "LOW"
            ) else "ACCEPTABLE" if (
                capacity_metric["warning_state"] != "CRITICAL" and
                distance_metric["efficiency_level"] != "LOW"
            ) else "RISKY",
        }


def get_enterprise_metrics_calculator() -> EnterpriseMetricsCalculator:
    """Factory for enterprise metrics calculator."""
    return EnterpriseMetricsCalculator()
