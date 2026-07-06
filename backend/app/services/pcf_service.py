import logging
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PCFDataSource(ABC):
    """Abstract base class for PCF data sources."""

    @abstractmethod
    def get_pcf_by_facility(self, facility: str) -> float:
        """Get PCF value for a facility."""
        pass

    @abstractmethod
    def get_pcf_by_supplier(self, supplier_id: str, product: str) -> float:
        """Get PCF value for a supplier and product."""
        pass


class DummyPCFDataSource(PCFDataSource):
    """
    Dummy PCF data source with realistic emission factors
    for the 5-stage supply chain model.
    """

    # Stage 1: Harvest emission (kg CO2e per kg fresh fruit)
    HARVEST_EMISSION = 0.35

    # Stage 2: Transport Estate -> Mill (kg CO2e per kg per km)
    TRANSPORT_ESTATE_TO_MILL_RATE = 0.00012

    # Stage 3: Mill processing emission (kg CO2e per kg CPO produced)
    MILL_PROCESSING_EMISSION = 0.65

    # Stage 4: Transport Mill -> Refinery (kg CO2e per kg per km)
    TRANSPORT_MILL_TO_REFINERY_RATE = 0.00015

    # Stage 5: Refinery processing emission (kg CO2e per kg refined product)
    REFINERY_PROCESSING_EMISSION = 0.85

    # Average distances (km) for transport estimates
    AVG_ESTATE_TO_MILL_KM = 85.0
    AVG_MILL_TO_REFINERY_KM = 420.0

    # Facility-level PCF for quick lookup
    FACILITY_PCF = {
        "Lubuk Gaung Refinery": 2.45,
        "Lampung Refinery": 2.80,
        "Marunda Refinery": 2.30,
        "Belawan Refinery": 2.60,
        "Tarjun Refinery": 2.70,
        "Surabaya Refinery": 2.55,
    }

    def get_pcf_by_facility(self, facility: str) -> float:
        return float(self.FACILITY_PCF.get(facility, 2.50))

    def get_pcf_by_supplier(self, supplier_id: str, product: str) -> float:
        return float(self.FACILITY_PCF.get(supplier_id, 2.50))

    def calculate_5stage_pcf(
        self,
        estate_volume_kg: float,
        estate_to_mill_km: float = 85.0,
        mill_processing_kg: float = 0.0,
        mill_to_refinery_km: float = 420.0,
        refinery_processing_kg: float = 0.0,
    ) -> Dict[str, float]:
        """
        Calculate 5-stage PCF emissions.

        Args:
            estate_volume_kg: Volume harvested from estate (FFB)
            estate_to_mill_km: Distance from estate to mill (km)
            mill_processing_kg: Volume processed at mill (kg)
            mill_to_refinery_km: Distance from mill to refinery (km)
            refinery_processing_kg: Volume processed at refinery (kg)

        Returns:
            Dict with stage-wise and total emissions
        """
        stage1_harvest = float(estate_volume_kg) * self.HARVEST_EMISSION
        stage2_transport_em = float(estate_to_mill_km) * self.TRANSPORT_ESTATE_TO_MILL_RATE * float(estate_volume_kg)
        stage3_mill = float(mill_processing_kg) * self.MILL_PROCESSING_EMISSION if mill_processing_kg > 0 else float(estate_volume_kg) * 0.20 * self.MILL_PROCESSING_EMISSION
        stage4_transport_mr = float(mill_to_refinery_km) * self.TRANSPORT_MILL_TO_REFINERY_RATE * float(mill_processing_kg if mill_processing_kg > 0 else estate_volume_kg * 0.20)
        stage5_refinery = float(refinery_processing_kg) * self.REFINERY_PROCESSING_EMISSION

        total = stage1_harvest + stage2_transport_em + stage3_mill + stage4_transport_mr + stage5_refinery

        return {
            "stage1_harvest_emission_kg_co2e": round(stage1_harvest, 4),
            "stage2_transport_estate_to_mill_kg_co2e": round(stage2_transport_em, 4),
            "stage3_mill_processing_emission_kg_co2e": round(stage3_mill, 4),
            "stage4_transport_mill_to_refinery_kg_co2e": round(stage4_transport_mr, 4),
            "stage5_refinery_processing_emission_kg_co2e": round(stage5_refinery, 4),
            "total_pcf_kg_co2e": round(total, 4),
        }


class PCFCalculationService:
    """Service for calculating and managing PCF metrics using 5-stage model."""

    def __init__(self, data_source: Optional[PCFDataSource] = None):
        self.data_source = data_source or DummyPCFDataSource()

    def _ensure_dict(self, node: Any, context: str = "node") -> Dict[str, Any]:
        """Defensive: ensure node is a dict, not a string or other type."""
        if isinstance(node, dict):
            return node
        logger.warning(f"Expected dict for {context}, got {type(node).__name__}: {str(node)[:80]}")
        return {"supplier_id": str(node) if node else "UNKNOWN", "product": "CPO", "quantity": 0.0}

    def calculate_node_pcf(
        self,
        node: Union[Dict[str, Any], str, Any],
        facility: Optional[str] = None,
    ) -> float:
        """
        Calculate PCF for a supply chain node using 5-stage model.

        Args:
            node: Node dict with supplier_id, product, quantity, or raw string
            facility: Optional facility context

        Returns:
            PCF per unit value (kg CO2e per kg product)
        """
        node = self._ensure_dict(node, "calculate_node_pcf")
        supplier_id = str(node.get("supplier_id", "UNKNOWN"))
        product = str(node.get("product", "CPO"))
        quantity = float(node.get("quantity", 1.0))

        if quantity <= 0:
            return 0.0

        # Use the 5-stage model for realistic total emission
        emitter = self.data_source
        if isinstance(emitter, DummyPCFDataSource):
            raw_supplier_type = str(node.get("supplier_type", "")).upper().strip()
            node_type_field = raw_supplier_type

            is_estate = (
                node_type_field == "ESTATE"
                or "ESTATE" in supplier_id.upper()
            )
            is_mill = (
                node_type_field == "MILL"
                or (not is_estate and "MILL" in supplier_id.upper())
            )
            is_vendor = (
                node_type_field in ("VENDOR", "TRUSTED_VENDOR", "THIRD_PARTY")
                or (
                    not is_estate
                    and not is_mill
                    and ("VENDOR" in supplier_id.upper() or "TRUSTED" in supplier_id.upper())
                )
            )
            is_refinery = (
                node_type_field == "REFINERY"
                or "REFINERY" in supplier_id.upper()
            )

            # Determine which stage volumes apply
            estate_vol = quantity if (is_estate or is_vendor) else 0.0
            mill_vol = quantity if is_mill else 0.0

            # Apply CPO extraction ratio: ~20% of FFB becomes CPO
            if is_estate or is_vendor:
                mill_vol = float(quantity) * 0.20

            # Refinery processes the mill output (OER ~94%)
            ref_vol = float(mill_vol) * 0.94 if mill_vol > 0 else (float(quantity) * 0.94 if is_mill else 0.0)
            if is_refinery:
                ref_vol = float(quantity)

            # If node type is unknown, treat conservatively as a full-chain node
            if not (is_estate or is_mill or is_vendor or is_refinery):
                estate_vol = float(quantity)
                mill_vol = float(quantity) * 0.20
                ref_vol = float(mill_vol) * 0.94

            stages = emitter.calculate_5stage_pcf(
                estate_volume_kg=estate_vol if estate_vol > 0 else float(quantity),
                estate_to_mill_km=85.0,
                mill_processing_kg=mill_vol,
                mill_to_refinery_km=420.0,
                refinery_processing_kg=ref_vol,
            )
            return float(stages["total_pcf_kg_co2e"]) / max(float(quantity), 1.0)

        return self.data_source.get_pcf_by_supplier(supplier_id, product)

    def calculate_tree_total_pcf(
        self,
        tree: Any,
        facility: Optional[str] = None,
    ) -> float:
        """
        Calculate total PCF footprint for entire supply chain tree.
        Handles trees where nodes may be strings or malformed.

        Args:
            tree: List of nodes in the tree (or any iterable)
            facility: Optional facility context

        Returns:
            Total PCF (kg CO2 equivalent)
        """
        if not isinstance(tree, (list, tuple)):
            logger.warning(f"Expected list/tuple tree, got {type(tree).__name__}")
            return 0.0

        if not tree:
            return 0.0

        total_pcf = 0.0
        for node in tree:
            node = self._ensure_dict(node, "calculate_tree_total_pcf")
            node_pcf_per_unit = self.calculate_node_pcf(node, facility)
            quantity = float(node.get("quantity", 1.0))
            total_pcf += node_pcf_per_unit * quantity

        return round(total_pcf, 2)

    def calculate_per_unit_pcf(
        self,
        tree: Any,
        total_quantity: float,
        facility: Optional[str] = None,
    ) -> float:
        """
        Calculate PCF per unit of delivered product.
        Returns 0.0 only if total_quantity is truly 0.

        Args:
            tree: List of nodes in the tree
            total_quantity: Total quantity of final product (kg)
            facility: Optional facility context

        Returns:
            PCF per unit (kg CO2 per kg product)
        """
        total_quantity = float(total_quantity)
        if total_quantity <= 0:
            return 0.0

        total_pcf = self.calculate_tree_total_pcf(tree, facility)
        return round(total_pcf / total_quantity, 4)

    def add_pcf_to_tree(
        self,
        tree: Any,
        facility: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enrich tree nodes with PCF metrics — SINGLE PASS.
        Every node gets:
          - pcf_per_unit       : float (kg CO2e / kg of this node's product)
          - pcf_total          : float (pcf_per_unit * quantity)
          - pcf_stage_breakdown: dict  with 5 stage values + metadata
        """
        if not isinstance(tree, (list, tuple)) or not tree:
            return list(tree) if tree else []

        emitter = self.data_source
        enriched_tree = []

        for raw_node in tree:
            node = self._ensure_dict(raw_node, "add_pcf_to_tree")
            node_copy = dict(**node)
            quantity = float(node.get("quantity", 1.0))

            if quantity <= 0:
                node_copy["pcf_per_unit"]       = 0.0
                node_copy["pcf_total"]           = 0.0
                node_copy["pcf_stage_breakdown"] = None
                enriched_tree.append(node_copy)
                continue

            supplier_id       = str(node.get("supplier_id", "UNKNOWN"))
            raw_supplier_type = str(node.get("supplier_type", "")).upper().strip()

            is_estate  = raw_supplier_type == "ESTATE"  or "ESTATE"  in supplier_id.upper()
            is_mill    = (not is_estate) and (raw_supplier_type == "MILL"    or "MILL"    in supplier_id.upper())
            is_vendor  = (not is_estate and not is_mill) and (
                raw_supplier_type in ("VENDOR", "TRUSTED_VENDOR", "THIRD_PARTY")
                or "VENDOR" in supplier_id.upper() or "TRUSTED" in supplier_id.upper()
            )
            is_refinery = (not is_estate and not is_mill and not is_vendor) and (
                raw_supplier_type == "REFINERY" or "REFINERY" in supplier_id.upper()
            )

            if isinstance(emitter, DummyPCFDataSource):
                # Determine volumes for each stage in one step
                if is_estate or is_vendor:
                    estate_vol = quantity
                    mill_vol   = quantity * 0.20
                    ref_vol    = mill_vol * 0.94
                elif is_mill:
                    estate_vol = quantity / 0.20
                    mill_vol   = quantity
                    ref_vol    = quantity * 0.94
                elif is_refinery:
                    ref_vol    = quantity
                    mill_vol   = quantity / 0.94
                    estate_vol = mill_vol / 0.20
                else:
                    estate_vol = quantity
                    mill_vol   = quantity * 0.20
                    ref_vol    = mill_vol * 0.94

                em_km = emitter.AVG_ESTATE_TO_MILL_KM
                mr_km = emitter.AVG_MILL_TO_REFINERY_KM

                s1 = round(estate_vol * emitter.HARVEST_EMISSION, 4)
                s2 = round(estate_vol * em_km * emitter.TRANSPORT_ESTATE_TO_MILL_RATE, 4)
                s3 = round(mill_vol   * emitter.MILL_PROCESSING_EMISSION, 4)
                s4 = round(mill_vol   * mr_km * emitter.TRANSPORT_MILL_TO_REFINERY_RATE, 4)
                s5 = round(ref_vol    * emitter.REFINERY_PROCESSING_EMISSION, 4)

                total_emission = round(s1 + s2 + s3 + s4 + s5, 4)
                pcf_per_unit   = round(total_emission / max(quantity, 1.0), 6)

                # Only emit stages relevant for this node type
                node_copy["pcf_stage_breakdown"] = {
                    "node_type":    raw_supplier_type or "UNKNOWN",
                    "product":      str(node.get("product", "CPO")).upper(),
                    "quantity_kg":  round(quantity, 2),
                    "stage1_harvest_emission_kg_co2e":                    s1  if (is_estate or is_vendor) else 0.0,
                    "stage2_transport_estate_to_mill_kg_co2e":            s2  if (is_estate or is_vendor) else 0.0,
                    "stage3_mill_processing_emission_kg_co2e":            s3  if (is_estate or is_vendor or is_mill) else 0.0,
                    "stage4_transport_mill_to_refinery_kg_co2e":          s4  if (is_mill or is_estate or is_vendor) else 0.0,
                    "stage5_refinery_processing_emission_kg_co2e":        s5  if is_refinery else 0.0,
                    "total_pcf_kg_co2e":                                  total_emission,
                    "pcf_per_unit_kg_co2e_per_kg":                        pcf_per_unit,
                    "estate_to_mill_km":                                  em_km,
                    "mill_to_refinery_km":                                mr_km,
                }
            else:
                # Non-dummy data source: use existing calculate_node_pcf
                try:
                    pcf_per_unit = self.calculate_node_pcf(node, facility)
                except Exception as exc:
                    logger.warning("PCF calc failed for %s: %s", supplier_id, exc)
                    pcf_per_unit = 0.0
                node_copy["pcf_stage_breakdown"] = None

            node_copy["pcf_per_unit"] = float(pcf_per_unit)
            node_copy["pcf_total"]    = round(float(pcf_per_unit) * quantity, 4)
            enriched_tree.append(node_copy)

        return enriched_tree

    def calculate_tree_total_pcf(
        self,
        tree: Any,
        facility: Optional[str] = None,
    ) -> float:
        """
        Calculate total PCF for the tree.
        If nodes already have pcf_total from add_pcf_to_tree, reuse them (zero extra cost).
        """
        if not isinstance(tree, (list, tuple)) or not tree:
            return 0.0

        total = 0.0
        for raw_node in tree:
            node = self._ensure_dict(raw_node, "calculate_tree_total_pcf")
            # Fast path: already enriched
            if "pcf_total" in node:
                total += float(node["pcf_total"])
            else:
                pcf_pu   = self.calculate_node_pcf(node, facility)
                quantity = float(node.get("quantity", 1.0))
                total   += pcf_pu * quantity

        return round(total, 2)

    def calculate_per_unit_pcf(
        self,
        tree: Any,
        total_quantity: float,
        facility: Optional[str] = None,
    ) -> float:
        total_quantity = float(total_quantity)
        if total_quantity <= 0:
            return 0.0
        return round(self.calculate_tree_total_pcf(tree, facility) / total_quantity, 4)


# Global service instance
_pcf_service: Optional[PCFCalculationService] = None


def get_pcf_service() -> PCFCalculationService:
    """Get or create PCF service instance."""
    global _pcf_service
    if _pcf_service is None:
        _pcf_service = PCFCalculationService()
    return _pcf_service


def set_pcf_data_source(data_source: PCFDataSource) -> None:
    """Allow swapping the PCF data source (for testing or real data)."""
    global _pcf_service
    _pcf_service = PCFCalculationService(data_source=data_source)
