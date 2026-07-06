import logging
from typing import Any, Dict, List, Optional, Literal
from app.services.pcf_service import get_pcf_service

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Filters and sorts recommendations based on selected metrics.
    Supports multiple recommendation strategies.
    """
    
    def __init__(self):
        self.pcf_service = get_pcf_service()
    
    def apply_recommendation_metric(
        self,
        trace_result: Dict[str, Any],
        metric: Literal["VOLUME", "LOWEST_PCF"] = "VOLUME",
        facility: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply recommendation filtering based on metric type.
        
        Args:
            trace_result: Original trace result from trace_service
            metric: Recommendation metric type
            facility: Optional facility context for PCF calculation
        
        Returns:
            Enhanced trace result with metric scores
        """
        if metric == "LOWEST_PCF":
            return self._apply_pcf_metric(trace_result, facility)
        else:  # VOLUME
            return self._apply_volume_metric(trace_result)
    
    def _apply_volume_metric(
        self,
        trace_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply volume-based recommendation.
        Also enriches every tree node with PCF data so the frontend
        can display per-node and per-stage carbon footprint regardless
        of which metric was chosen.
        """
        enriched = trace_result.copy()
        enriched["recommendation_metric"] = "VOLUME"
        enriched["metric_description"] = "Sorted by allocation volume (highest first)"

        total_quantity = float(enriched.get("quantity", 1.0))
        recommendation_options = enriched.get("recommendation_options", [])

        if not recommendation_options:
            enriched["total_pcf_kg_co2e"] = 0.0
            enriched["pcf_per_unit_kg_co2e"] = 0.0
            return enriched

        facility = enriched.get("facility")
        enriched_options: List[Dict[str, Any]] = []

        for option in recommendation_options:
            option_copy = option.copy()
            tree = option_copy.get("tree", [])

            if tree:
                enriched_tree = self.pcf_service.add_pcf_to_tree(tree, facility)
                option_copy["tree"] = enriched_tree
                # Reuse pcf_total from enriched nodes — no second pass
                option_copy["total_pcf_kg_co2e"] = round(
                    sum(float(n.get("pcf_total", 0)) for n in enriched_tree), 2
                )
            else:
                option_copy["tree"] = tree
                option_copy["total_pcf_kg_co2e"] = 0.0

            option_copy["pcf_per_unit_kg_co2e"] = (
                round(option_copy["total_pcf_kg_co2e"] / max(total_quantity, 1.0), 4)
                if total_quantity > 0 else 0.0
            )
            enriched_options.append(option_copy)

        enriched["recommendation_options"] = enriched_options

        # Surface primary option totals at order level for frontend compatibility
        primary = enriched_options[0]
        enriched["total_pcf_kg_co2e"] = primary["total_pcf_kg_co2e"]
        enriched["pcf_per_unit_kg_co2e"] = primary["pcf_per_unit_kg_co2e"]
        enriched["tree"] = primary.get("tree", [])

        return enriched
    
    def _apply_pcf_metric(
        self,
        trace_result: Dict[str, Any],
        facility: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply PCF-based recommendation (lowest carbon footprint first).

        IMPORTANT: trace_orders_service() does NOT put the supply-chain
        tree at the top level of the result. The tree lives inside
        trace_result["recommendation_options"][i]["tree"]. Reading
        trace_result.get("tree", []) here always returns an empty list,
        which is why PCF totals were always 0.

        Args:
            trace_result: Original trace result (order-level dict from trace_service)
            facility: Optional facility context

        Returns:
            Result with PCF metrics enriched on each recommendation option,
            plus convenience top-level fields mirroring the primary option
            (so existing frontend code reading activeResult.total_pcf_kg_co2e
            keeps working).
        """
        enriched = trace_result.copy()
        enriched["recommendation_metric"] = "LOWEST_PCF"
        enriched["metric_description"] = "Sorted by product carbon footprint (lowest first)"

        total_quantity = float(enriched.get("quantity", 1.0))
        recommendation_options = enriched.get("recommendation_options", [])

        if not recommendation_options:
            # No unmet demand / nothing to route -> nothing to score.
            enriched["total_pcf_kg_co2e"] = 0.0
            enriched["pcf_per_unit_kg_co2e"] = 0.0
            return enriched

        enriched_options: List[Dict[str, Any]] = []
        for option in recommendation_options:
            option_copy = option.copy()
            tree = option_copy.get("tree", [])

            if tree:
                enriched_tree = self.pcf_service.add_pcf_to_tree(tree, facility)
                option_copy["tree"] = self._sort_tree_by_pcf(enriched_tree)
                # Reuse cached pcf_total — no second pass
                total_pcf = round(sum(float(n.get("pcf_total", 0)) for n in enriched_tree), 2)
            else:
                option_copy["tree"] = tree
                total_pcf = 0.0

            option_copy["total_pcf_kg_co2e"]  = total_pcf
            option_copy["pcf_per_unit_kg_co2e"] = (
                round(total_pcf / max(total_quantity, 1.0), 4) if total_quantity > 0 else 0.0
            )

            enriched_options.append(option_copy)

        enriched["recommendation_options"] = enriched_options

        # Surface the primary (first) option's totals at the order level too,
        # since the frontend reads activeResult.total_pcf_kg_co2e directly.
        primary = enriched_options[0]
        enriched["total_pcf_kg_co2e"] = primary["total_pcf_kg_co2e"]
        enriched["pcf_per_unit_kg_co2e"] = primary["pcf_per_unit_kg_co2e"]
        # Top-level "tree" alias for any older code that still reads it there.
        enriched["tree"] = primary.get("tree", [])

        return enriched

    def _sort_tree_by_pcf(self, tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort root-level (level 0) nodes of a single tree by pcf_per_unit ascending."""
        if not tree:
            return tree

        root_nodes = [n for n in tree if n.get("level", 0) == 0]
        other_nodes = [n for n in tree if n.get("level", 0) != 0]

        root_nodes_sorted = sorted(root_nodes, key=lambda n: n.get("pcf_per_unit", 0.0))

        return root_nodes_sorted + other_nodes
    
    def validate_metric_request(self, metric: str) -> bool:
        """Validate that metric is supported."""
        allowed = {"VOLUME", "LOWEST_PCF"}
        return metric in allowed


# Global recommendation engine instance
_recommendation_engine: Optional[RecommendationEngine] = None

def get_recommendation_engine() -> RecommendationEngine:
    """Get or create recommendation engine instance."""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine