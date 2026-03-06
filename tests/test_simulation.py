"""Tests for the simulation runner and plant models."""

from __future__ import annotations

import math

import pytest

from python.pid.controller import PIDConfig, PIDController
from python.simulation.runner import (
    SimulationResult,
    SimulationRunner,
    first_order_plant,
    second_order_plant,
)


class TestFirstOrderPlant:
    """Tests for first_order_plant factory."""

    def test_step_response_reaches_setpoint(self) -> None:
        """After many time constants, output should be near the input."""
        plant = first_order_plant(time_constant=1.0, gain=1.0)
        x = 0.0
        dt = 0.001
        for _ in range(5000):  # 5 time constants
            _, x = plant(1.0, x, dt)
        assert abs(x - 1.0) < 0.01

    def test_invalid_time_constant_raises(self) -> None:
        """Non-positive time constant should raise ValueError."""
        with pytest.raises(ValueError, match="time_constant"):
            first_order_plant(time_constant=0.0)

    def test_negative_dead_time_raises(self) -> None:
        """Negative dead_time should raise ValueError."""
        with pytest.raises(ValueError, match="dead_time"):
            first_order_plant(time_constant=1.0, dead_time=-0.1)


class TestSecondOrderPlant:
    """Tests for second_order_plant factory."""

    def test_invalid_natural_freq_raises(self) -> None:
        """Zero natural frequency should raise ValueError."""
        with pytest.raises(ValueError, match="natural_freq"):
            second_order_plant(natural_freq=0.0, damping_ratio=0.7)

    def test_invalid_damping_raises(self) -> None:
        """Zero damping ratio should raise ValueError."""
        with pytest.raises(ValueError, match="damping_ratio"):
            second_order_plant(natural_freq=1.0, damping_ratio=0.0)


class TestSimulationRunner:
    """Tests for SimulationRunner integration."""

    def _make_runner(
        self,
        kp: float = 2.0,
        ki: float = 1.0,
        kd: float = 0.1,
        duration: float = 5.0,
    ) -> SimulationRunner:
        cfg = PIDConfig(kp=kp, ki=ki, kd=kd, dt=0.01)
        ctrl = PIDController(cfg)
        plant = first_order_plant(time_constant=1.0, gain=1.0)
        return SimulationRunner(ctrl, plant, duration=duration)

    def test_step_response_settles(self) -> None:
        """A well-tuned PID should settle near the setpoint after 5 seconds."""
        runner = self._make_runner()
        result = runner.run(setpoint=1.0)
        assert result.steady_state_error < 0.05

    def test_result_arrays_correct_length(self) -> None:
        """Result arrays should have n_steps = duration / dt entries."""
        runner = self._make_runner(duration=2.0)
        result = runner.run(setpoint=1.0)
        expected_steps = int(2.0 / 0.01)
        assert len(result.time) == expected_steps
        assert len(result.measurement) == expected_steps
        assert len(result.control_output) == expected_steps

    def test_zero_setpoint_zero_output(self) -> None:
        """With setpoint=0 and initial state=0, output should stay near 0."""
        runner = self._make_runner()
        result = runner.run(setpoint=0.0)
        assert result.steady_state_error < 1e-6

    def test_invalid_duration_raises(self) -> None:
        """Zero duration should raise ValueError."""
        cfg = PIDConfig(kp=1.0, ki=0.0, kd=0.0, dt=0.01)
        ctrl = PIDController(cfg)
        plant = first_order_plant(time_constant=1.0)
        with pytest.raises(ValueError, match="duration"):
            SimulationRunner(ctrl, plant, duration=0.0)

    def test_overshoot_is_non_negative(self) -> None:
        """Overshoot percentage should never be negative."""
        runner = self._make_runner()
        result = runner.run(setpoint=1.0)
        assert result.overshoot_pct >= 0.0

    def test_rise_time_is_positive(self) -> None:
        """Rise time should be positive for a positive step."""
        runner = self._make_runner()
        result = runner.run(setpoint=1.0)
        # With good tuning, rise time should exist
        if math.isfinite(result.rise_time):
            assert result.rise_time > 0.0

    def test_settling_time_less_than_duration(self) -> None:
        """For a well-tuned PID, settling time should be < total duration."""
        runner = self._make_runner(duration=10.0)
        result = runner.run(setpoint=1.0)
        if math.isfinite(result.settling_time):
            assert result.settling_time < 10.0
