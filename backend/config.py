"""Configuration settings for the Urban Flow simulation."""

from pydantic import BaseModel, Field

# Grid dimension bounds — single source of truth used by both SimulationConfig
# validation and Grid.__init__() runtime guards.
MIN_GRID_SIZE: int = 1
MAX_GRID_SIZE: int = 100

# Street/avenue spacing for the city-blocks pattern.  Streets run every
# STREET_SPACING rows starting at row 0; avenues every STREET_SPACING columns
# starting at column 0.  E.g. spacing=3 on a 10×10 grid gives {0,3,6,9}.
# Future improvement: derive spacing dynamically from grid dimensions so that
# larger grids produce proportionally spaced street grids.
STREET_SPACING: int = 3


class SimulationConfig(BaseModel):
    """Configuration for the traffic simulation.

    All timing values are in ticks. Runtime configuration changes
    take effect on the next tick to maintain determinism.
    """

    # Grid dimensions
    grid_width: int = Field(default=10, ge=MIN_GRID_SIZE, le=MAX_GRID_SIZE)
    grid_height: int = Field(default=10, ge=MIN_GRID_SIZE, le=MAX_GRID_SIZE)

    # Simulation timing
    tick_speed: int = Field(default=1, ge=1, le=10, description="Ticks per second")

    # Vehicle spawning
    spawn_rate: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Probability per edge cell per tick"
    )
    emergency_probability: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Probability that spawned vehicle is emergency",
    )

    # Traffic light timing
    phase_duration: int = Field(
        default=3, ge=1, le=20, description="Ticks per traffic light phase"
    )


# Default configuration instance
DEFAULT_CONFIG = SimulationConfig()
