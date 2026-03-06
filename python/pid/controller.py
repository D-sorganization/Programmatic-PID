"""Core PID controller implementation.

Provides a discrete-time PID controller with anti-windup, derivative filter,
and bumpless transfer support.

Design by Contract:
- All gain values must be non-negative
- dt (sample period) must be strictly positive
- output limits must satisfy low <= high
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PIDConfig:
    """Configuration for a PID controller.

    Attributes:
        kp: Proportional gain (>= 0)
        ki: Integral gain (>= 0)
        kd: Derivative gain (>= 0)
        dt: Sample period in seconds (> 0)
        output_min: Lower output clamp (default: -inf)
        output_max: Upper output clamp (default: +inf)
        derivative_filter_n: Derivative filter coefficient N (default: 10)
            Higher = less filtering, lower = more filtering.
        name: Optional controller name for logging.
    """

    kp: float
    ki: float
    kd: float
    dt: float
    output_min: float = float("-inf")
    output_max: float = float("inf")
    derivative_filter_n: float = 10.0
    name: str = "PID"

    def __post_init__(self) -> None:
        """Validate configuration contracts."""
        if self.kp < 0:
            raise ValueError(f"kp must be >= 0, got {self.kp}")
        if self.ki < 0:
            raise ValueError(f"ki must be >= 0, got {self.ki}")
        if self.kd < 0:
            raise ValueError(f"kd must be >= 0, got {self.kd}")
        if self.dt <= 0:
            raise ValueError(f"dt must be > 0, got {self.dt}")
        if self.output_min > self.output_max:
            raise ValueError(
                f"output_min ({self.output_min}) must be <= output_max ({self.output_max})"
            )
        if self.derivative_filter_n <= 0:
            raise ValueError(f"derivative_filter_n must be > 0, got {self.derivative_filter_n}")


@dataclass
class PIDState:
    """Internal state of a PID controller (mutable during operation)."""

    integral: float = 0.0
    derivative_filtered: float = 0.0
    prev_error: float = 0.0
    prev_measurement: float = 0.0
    last_output: float = 0.0
    initialized: bool = False
    _history: list[tuple[float, float, float]] = field(default_factory=list)


class PIDController:
    """Discrete-time PID controller with anti-windup and derivative filter.

    Uses the velocity form of the PID with:
    - Back-calculation anti-windup to prevent integrator wind-up
    - First-order derivative filter to reduce noise amplification
    - Measurement-based derivative (avoids setpoint kick on SP changes)

    Example:
        >>> cfg = PIDConfig(kp=1.0, ki=0.1, kd=0.05, dt=0.01)
        >>> ctrl = PIDController(cfg)
        >>> u = ctrl.update(setpoint=10.0, measurement=0.0)
    """

    def __init__(self, config: PIDConfig) -> None:
        """Initialize the PID controller.

        Args:
            config: Validated PID configuration.
        """
        self.config = config
        self.state = PIDState()
        logger.info(
            "[%s] Initialized: Kp=%.3f Ki=%.3f Kd=%.3f dt=%.4fs",
            config.name,
            config.kp,
            config.ki,
            config.kd,
            config.dt,
        )

    def update(self, setpoint: float, measurement: float) -> float:
        """Compute the next control output.

        Args:
            setpoint: Desired process value.
            measurement: Current measured process value.

        Returns:
            Control output, clamped to [output_min, output_max].
        """
        cfg = self.config
        st = self.state

        error = setpoint - measurement

        # --- Proportional term ---
        p_term = cfg.kp * error

        # --- Integral term with back-calculation anti-windup ---
        st.integral += cfg.ki * error * cfg.dt

        # --- Derivative term (on measurement to avoid setpoint kick) ---
        # Discrete filtered derivative: D_filter = N / (1 + N*dt) * (D_filter*0 + ...)
        # Uses first-order Tustin approximation of: N*s / (s + N)
        alpha = cfg.derivative_filter_n * cfg.dt / (1.0 + cfg.derivative_filter_n * cfg.dt)
        d_raw = -(measurement - st.prev_measurement) / cfg.dt if st.initialized else 0.0
        st.derivative_filtered = (1.0 - alpha) * st.derivative_filtered + alpha * d_raw
        d_term = cfg.kd * st.derivative_filtered

        # --- Sum and clamp ---
        output_unclamped = p_term + st.integral + d_term
        output = max(cfg.output_min, min(cfg.output_max, output_unclamped))

        # Back-calculation anti-windup: subtract clamped excess from integral
        clamp_error = output - output_unclamped
        if abs(clamp_error) > 1e-10 and cfg.ki > 0:
            st.integral += clamp_error  # pull integral back

        # --- Update state ---
        st.prev_error = error
        st.prev_measurement = measurement
        st.last_output = output
        st.initialized = True
        st._history.append((setpoint, measurement, output))

        logger.debug(
            "[%s] SP=%.3f PV=%.3f e=%.3f P=%.3f I=%.3f D=%.3f u=%.3f",
            cfg.name,
            setpoint,
            measurement,
            error,
            p_term,
            st.integral,
            d_term,
            output,
        )
        return output

    def reset(self) -> None:
        """Reset controller state (useful for mode switches or re-initialization)."""
        self.state = PIDState()
        logger.info("[%s] State reset.", self.config.name)

    @property
    def history(self) -> list[tuple[float, float, float]]:
        """Return list of (setpoint, measurement, output) tuples recorded so far."""
        return list(self.state._history)

    def set_gains(
        self,
        kp: float | None = None,
        ki: float | None = None,
        kd: float | None = None,
    ) -> None:
        """Update gains at runtime (bumpless — does not reset integral).

        Args:
            kp: New proportional gain, or None to keep current.
            ki: New integral gain, or None to keep current.
            kd: New derivative gain, or None to keep current.

        Raises:
            ValueError: If any new gain is negative.
        """
        if kp is not None:
            if kp < 0:
                raise ValueError(f"kp must be >= 0, got {kp}")
            self.config.kp = kp
        if ki is not None:
            if ki < 0:
                raise ValueError(f"ki must be >= 0, got {ki}")
            self.config.ki = ki
        if kd is not None:
            if kd < 0:
                raise ValueError(f"kd must be >= 0, got {kd}")
            self.config.kd = kd
        logger.info(
            "[%s] Gains updated: Kp=%.3f Ki=%.3f Kd=%.3f",
            self.config.name,
            self.config.kp,
            self.config.ki,
            self.config.kd,
        )
