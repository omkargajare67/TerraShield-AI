"""Optional transparent budget and tree allocation model across ranked candidate parcels."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.core.recommendations.ranking import EvaluatedParcel


class BudgetAllocationConfig(BaseModel):
    """User-supplied economic parameters for exploratory sapling allocation."""
    total_budget_inr: float = Field(..., gt=0.0, description="Available planting budget in INR")
    cost_per_sapling_inr: float = Field(default=150.0, gt=0.0, description="Estimated procurement & planting cost per sapling")
    fixed_parcel_setup_cost_inr: float = Field(default=5000.0, ge=0.0, description="Site preparation and transport cost per parcel")
    default_planting_density_stems_ha: float = Field(
        default=400.0, gt=0.0, description="Default silvicultural planting density if calibrated geotechnical density is absent"
    )
    max_stems_per_ha_cap: float = Field(default=1000.0, gt=0.0, description="Maximum allowable silvicultural density cap")


class ParcelAllocation(BaseModel):
    """Budget and stem allocation for a single eligible parcel."""
    parcel_id: str
    rank: int
    plantable_area_ha: float
    stems_allocated: int
    target_density_stems_ha: float
    parcel_cost_inr: float
    density_source: str


class AllocationResult(BaseModel):
    """Overall budget allocation summary across ranked candidate parcels."""
    total_budget_inr: float
    total_budget_spent_inr: float
    remaining_budget_inr: float
    total_stems_allocated: int
    parcels_funded_count: int
    allocations: List[ParcelAllocation]
    assumptions_note: str


def allocate_planting_budget(
    ranked_parcels: List[EvaluatedParcel],
    config: BudgetAllocationConfig,
) -> AllocationResult:
    """Greedily allocate planting budget to highest-ranked eligible parcels until budget exhaustion.

    Rules:
    - Only eligible parcels with positive plantable area are considered.
    - Allocates strictly in rank order (Rank 1, Rank 2, etc.).
    - Never allocates negative trees or exceeds available budget.
    - Uses calibrated geotechnical stem density if available, else configured default density.
    - Clamped to max_stems_per_ha_cap.
    """
    remaining_budget = config.total_budget_inr
    allocations: List[ParcelAllocation] = []
    total_stems = 0

    for parcel in ranked_parcels:
        if parcel.rank is None or parcel.plantable_area_ha <= 0:
            continue

        if remaining_budget < (config.fixed_parcel_setup_cost_inr + config.cost_per_sapling_inr):
            # Cannot fund even minimal parcel setup
            break

        # Determine target density
        calibrated_density = parcel.metrics.get("tree_density_mean_stems_ha")
        if calibrated_density is not None and calibrated_density > 0:
            target_density = min(calibrated_density, config.max_stems_per_ha_cap)
            density_source = f"Calibrated geotechnical target density ({calibrated_density:.1f} stems/ha)"
        else:
            target_density = min(config.default_planting_density_stems_ha, config.max_stems_per_ha_cap)
            density_source = f"Configured default silvicultural density ({config.default_planting_density_stems_ha:.1f} stems/ha)"

        # Calculate needed stems for plantable area
        desired_stems = int(round(target_density * parcel.plantable_area_ha))
        if desired_stems <= 0:
            continue

        # Calculate cost
        desired_cost = config.fixed_parcel_setup_cost_inr + (desired_stems * config.cost_per_sapling_inr)

        if desired_cost <= remaining_budget:
            # Fully fund this parcel
            stems_to_plant = desired_stems
            cost_incurred = desired_cost
        else:
            # Partially fund this parcel with remaining budget
            budget_for_saplings = remaining_budget - config.fixed_parcel_setup_cost_inr
            if budget_for_saplings >= config.cost_per_sapling_inr:
                stems_to_plant = int(budget_for_saplings // config.cost_per_sapling_inr)
                cost_incurred = config.fixed_parcel_setup_cost_inr + (stems_to_plant * config.cost_per_sapling_inr)
            else:
                # Cannot afford fixed setup + even 1 tree
                break

        remaining_budget -= cost_incurred
        total_stems += stems_to_plant

        allocations.append(
            ParcelAllocation(
                parcel_id=parcel.parcel_id,
                rank=parcel.rank,
                plantable_area_ha=parcel.plantable_area_ha,
                stems_allocated=stems_to_plant,
                target_density_stems_ha=round(stems_to_plant / max(0.01, parcel.plantable_area_ha), 1),
                parcel_cost_inr=round(cost_incurred, 2),
                density_source=density_source,
            )
        )

    spent = round(config.total_budget_inr - remaining_budget, 2)

    note = (
        "EXPLORATORY BUDGET SIMULATION: Budget allocation model is an illustrative greedy heuristic. "
        "Actual restoration costs vary significantly with terrain accessibility, native nursery supply, "
        "labor rates, and post-planting maintenance."
    )

    return AllocationResult(
        total_budget_inr=config.total_budget_inr,
        total_budget_spent_inr=spent,
        remaining_budget_inr=round(remaining_budget, 2),
        total_stems_allocated=total_stems,
        parcels_funded_count=len(allocations),
        allocations=allocations,
        assumptions_note=note,
    )
