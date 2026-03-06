"""Simulation harness for closed-loop PID control.

Provides a generic plant model interface and a time-domain simulation runner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from python.pid.controller import PIDController, PIDConfig

logger = logging.getLogger(__name__)

# Type alias for a plant transfer function: f(u, x, dt) -> (y, x_new)
PlantFn = Callable[[float, float, float], tuple[float, float]]


@dataclass
class SimulationResult:
    """Results from a closed-loop simulation run."""

    time: np.ndarray
    setpoint: np.ndarray
    measurement: np.ndarray
    control_output: np.ndarray
    error: np.ndarray

    @property
    def steady_state_error(self) -> float:
        """Return the mean error over the last 10% of simulation time."""
        n = max(1, len(self.error) // 10)
        return float(np.mean(np.abs(self.error[-n:])))

    @property
    def overshoot_pct(self) -> float:
        """Return percent overshoot relative to setpoint step magnitude.

        Assumes a step from 0 to setpoint[0].
        """
        sp = self.setpoint[0]
        if abs(sp) < 1e-10:
            return 0.0
        peak = float(np.max(self.measurement))
        return max(0.0, (peak - sp) / abs(sp) * 100.0)

    @property
    def rise_time(self) -> float:
        """Return 10-90% rise time in seconds.

        Returns float('inf') if the setpoint is never reached.
        """
        sp = self.setpoint[0]
        if abs(sp) < 1e-10:
            return 0.0
        idx_10 = np.argmax(self.measurement >= 0.1 * sp)
        idx_90 = np.argmax(self.measurement >= 0.9 * sp)
        if idx_10 == 0 and self.measurement[0] < 0.1 * sp:
            return float("inf")
        if idx_90 == 0 and self.measurement[0] < 0.9 * sp:
            return float("inf")
        return float(self.time[idx_90] - self.time[idx_10])

    @property
    def settling_time(self) -> float:
        """Return time to settle within 2% of setpoint.

        Returns float('inf') if never settled.
        """
        sp = self.setpoint[0]
        band = 0.02 * abs(sp)
        # Find last time outside the band, then +1 step = settled
        outside = np.where(np.abs(self.measurement - sp) > band)[0]
        if len(outside) == 0:
            return 0.0
        last_outside = outside[-1]
        if last_outside + 1 >= len(self.time):
            return float("inf")
        return float(self.time[last_outside + 1])


def first_order_plant(
    time_constant: float, gain: float = 1.0, dead_time: float = 0.0
) -> PlantFn:
    """Create a first-order plant model: G(s) = K / (tau*s + 1) * e^(-L*s).

    Args:
        time_constant: Plant time constant tau (seconds).
        gain: Static plant gain K.
        dead_time: Transport delay L (seconds). Currently ignored in simulation.

    Returns:
        PlantFn usable by SimulationRunner.

    Raises:
        ValueError: If time_constant <= 0.
    """
    if time_constant <= 0:
        raise ValueError(f"time_constant must be > 0, got {time_constant}")
    if dead_time < 0:
        raise ValueError(f"dead_time must be >= 0, got {dead_time}")

    def _plant(u: float, x: float, dt: float) -> tuple[float, float]:
        # Euler integration: dx/dt = (-x + K*u) / tau
        dx = (-x + gain * u) / time_constant
        x_new = x + dx * dt
        return x_new, x_new  # output y = x for first-order system

    return _plant


def second_order_plant(
    natural_freq: float,
    damping_ratio: float,
    gain: float = 1.0,
) -> PlantFn:
    """Create a second-order plant model.

    G(s) = K * wn^2 / (s^2 + 2*zeta*wn*s + wn^2)

    Args:
        natural_freq: Natural frequency wn (rad/s).
        damping_ratio: Damping ratio zeta.
        gain: Static gain K.

    Returns:
        PlantFn for simulation.

    Raises:
        ValueError: If natural_freq <= 0 or damping_ratio <= 0.
    """
    if natural_freq <= 0:
        raise ValueError(f"natural_freq must be > 0, got {natural_freq}")
    if damping_ratio <= 0:
        raise ValueError(f"damping_ratio must be > 0, got {damping_ratio}")

    # State-space: x = [position, velocity]
    _state: list[np.ndarray] = [np.zeros(2)]

    def _plant(u: float, _x: float, dt: float) -> tuple[float, float]:
        wn = natural_freq
        zeta = damping_ratio
        x = _state[0]
        # dx1/dt = x2
        # dx2/dt = -wn^2*x1 - 2*zeta*wn*x2 + K*wn^2*u
        dx = np.array([
            x[1],
            -wn**2 * x[0] - 2 * zeta * wn * x[1] + gain * wn**2 * u,
        ])
        _state[0] = x + dx * dt
        return float(_state[0][0]), float(_state[0][0])

    return _plant


class SimulationRunner:
    """Runs a closed-loop PID simulation over a defined time span.

    Example:
        >>> cfg = PIDConfig(kp=2.0, ki=0.5, kd=0.1, dt=0.01)
        >>> ctrl = PIDController(cfg)
        >>> plant = first_order_plant(time_constant=1.0)
        >>> runner = SimulationRunner(ctrl, plant, duration=10.0)
        >>> result = runner.run(setpoint=1.0)
    """

    def __init__(
        self,
        controller: PIDController,
        plant_fn: PlantFn,
        duration: float,
    ) -> None:
        """Initialize the simulation runner.

        Args:
            controller: PID controller instance.
            plant_fn: Plant model function.
            duration: Total simulation time in seconds.

        Raises:
            ValueError: If duration <= 0.
        """
        if duration <= 0:
            raise ValueError(f"duration must be > 0, got {duration}")
        self.controller = controller
        self.plant_fn = plant_fn
        self.duration = duration

    def run(
        self,
        setpoint: float,
        initial_state: float = 0.0,
    ) -> SimulationResult:
        """Execute the simulation.

        Args:
            setpoint: Target value (step input from initial_state).
            initial_state: Initial plant state (default: 0.0).

        Returns:
            SimulationResult with time-domain arrays.
        """
        dt = self.controller.config.dt
        n_steps = int(self.duration / dt)

        time_arr = np.zeros(n_steps)
        sp_arr = np.zeros(n_steps)
        pv_arr = np.zeros(n_steps)
        u_arr = np.zeros(n_steps)

        self.controller.reset()
        x = initial_state
        pv = x

        for k in range(n_steps):
            t = k * dt
            u = self.controller.update(setpoint=setpoint, measurement=pv)
            _, pv = self.plant_fn(u, x, dt)
            x = pv

            time_arr[k] = t
            sp_arr[k] = setpoint
            pv_arr[k] = pv
            u_arr[k] = u

        error_arr = sp_arr - pv_arr
        logger.info(
            "Simulation complete: %.1f s, SSE=%.4f, Overshoot=%.1f%%",
            self.duration,
            np.mean(np.abs(error_arr[-max(1, n_steps // 10):])),
            max(0.0, (float(np.max(pv_arr)) - setpoint) / abs(setpoint) * 100.0)
            if abs(setpoint) > 1e-10 else 0.0,
        )

        return SimulationResult(
            time=time_arr,
            setpoint=sp_arr,
            measurement=pv_arr,
            control_output=u_arr,
            error=error_arr,
        )
