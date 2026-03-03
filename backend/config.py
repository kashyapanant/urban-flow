"""Configuration settings for the Urban Flow simulation."""

from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    """Configuration for the traffic simulation.

    All timing values are in ticks. Runtime configuration changes
    take effect on the next tick to maintain determinism.
    """

    # Grid dimensions
    grid_width: int = Field(default=10, ge=1, le=100)
    grid_height: int = Field(default=10, ge=1, le=100)

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
