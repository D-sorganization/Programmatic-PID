"""Tests for the PID controller core."""

from __future__ import annotations

import pytest

from python.pid.controller import PIDConfig, PIDController


class TestPIDConfig:
    """Tests for PIDConfig validation contracts."""

    def test_valid_config(self) -> None:
        """A valid configuration should initialize without error."""
        cfg = PIDConfig(kp=1.0, ki=0.5, kd=0.1, dt=0.01)
        assert cfg.kp == 1.0
        assert cfg.ki == 0.5
        assert cfg.kd == 0.1
        assert cfg.dt == 0.01

    def test_negative_kp_raises(self) -> None:
        """Negative Kp should raise ValueError."""
        with pytest.raises(ValueError, match="kp must be"):
            PIDConfig(kp=-1.0, ki=0.0, kd=0.0, dt=0.01)

    def test_negative_ki_raises(self) -> None:
        """Negative Ki should raise ValueError."""
        with pytest.raises(ValueError, match="ki must be"):
            PIDConfig(kp=0.0, ki=-0.1, kd=0.0, dt=0.01)

    def test_negative_kd_raises(self) -> None:
        """Negative Kd should raise ValueError."""
        with pytest.raises(ValueError, match="kd must be"):
            PIDConfig(kp=0.0, ki=0.0, kd=-0.5, dt=0.01)

    def test_zero_dt_raises(self) -> None:
        """Zero dt should raise ValueError."""
        with pytest.raises(ValueError, match="dt must be"):
            PIDConfig(kp=1.0, ki=0.0, kd=0.0, dt=0.0)

    def test_negative_dt_raises(self) -> None:
        """Negative dt should raise ValueError."""
        with pytest.raises(ValueError, match="dt must be"):
            PIDConfig(kp=1.0, ki=0.0, kd=0.0, dt=-0.01)

    def test_inverted_output_limits_raises(self) -> None:
        """output_min > output_max should raise ValueError."""
        with pytest.raises(ValueError, match="output_min"):
            PIDConfig(kp=1.0, ki=0.0, kd=0.0, dt=0.01, output_min=10.0, output_max=0.0)

    def test_zero_gains_valid(self) -> None:
        """All-zero gains (pure pass-through) should be valid."""
        cfg = PIDConfig(kp=0.0, ki=0.0, kd=0.0, dt=0.01)
        assert cfg.kp == 0.0


class TestPIDController:
    """Tests for PIDController behaviour."""

    def _make_controller(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        dt: float = 0.01,
        output_min: float = float("-inf"),
        output_max: float = float("inf"),
    ) -> PIDController:
        cfg = PIDConfig(
            kp=kp,
            ki=ki,
            kd=kd,
            dt=dt,
            output_min=output_min,
            output_max=output_max,
        )
        return PIDController(cfg)

    def test_proportional_only(self) -> None:
        """P-only controller should output kp * error."""
        ctrl = self._make_controller(kp=2.0, ki=0.0, kd=0.0)
        u = ctrl.update(setpoint=5.0, measurement=0.0)
        # First step: error=5, P=2*5=10, I=0, D=0
        assert abs(u - 10.0) < 0.01

    def test_zero_error_zero_output(self) -> None:
        """With setpoint == measurement (no history), output should be ~0."""
        ctrl = self._make_controller(kp=1.0, ki=0.0, kd=0.0)
        u = ctrl.update(setpoint=0.0, measurement=0.0)
        assert abs(u) < 1e-10

    def test_integral_accumulates(self) -> None:
        """Integral term should accumulate over multiple steps."""
        ctrl = self._make_controller(kp=0.0, ki=1.0, kd=0.0, dt=0.1)
        error = 2.0
        u1 = ctrl.update(setpoint=error, measurement=0.0)
        u2 = ctrl.update(setpoint=error, measurement=0.0)
        # I-only: u1 = ki*error*dt = 0.2, u2 = 0.4
        assert u2 > u1
        assert abs(u1 - 0.2) < 1e-9
        assert abs(u2 - 0.4) < 1e-9

    def test_output_clamping(self) -> None:
        """Output should be clamped to [output_min, output_max]."""
        ctrl = self._make_controller(kp=10.0, output_min=-5.0, output_max=5.0)
        u = ctrl.update(setpoint=100.0, measurement=0.0)
        assert u == 5.0
        u_neg = ctrl.update(setpoint=-100.0, measurement=0.0)
        assert u_neg == -5.0

    def test_anti_windup_prevents_excess_integral(self) -> None:
        """Anti-windup: integral should not grow unboundedly when clamped."""
        ctrl = self._make_controller(kp=0.0, ki=1.0, kd=0.0, dt=0.1, output_max=1.0)
        for _ in range(100):
            ctrl.update(setpoint=10.0, measurement=0.0)
        # Integral should be pulled back by anti-windup, not > output_max
        assert ctrl.state.integral <= 1.0 + 0.01  # small tolerance

    def test_reset_clears_state(self) -> None:
        """Reset should zero all internal state."""
        ctrl = self._make_controller(kp=1.0, ki=1.0, kd=0.0, dt=0.1)
        ctrl.update(setpoint=5.0, measurement=0.0)
        ctrl.reset()
        assert ctrl.state.integral == 0.0
        assert ctrl.state.prev_measurement == 0.0
        assert ctrl.state.prev_error == 0.0

    def test_set_gains_updates_runtime(self) -> None:
        """set_gains should update gains without resetting integral."""
        ctrl = self._make_controller(kp=1.0, ki=1.0, kd=0.0, dt=0.1)
        ctrl.update(setpoint=5.0, measurement=0.0)
        old_integral = ctrl.state.integral
        ctrl.set_gains(kp=2.0)
        assert ctrl.config.kp == 2.0
        assert ctrl.state.integral == old_integral  # bumpless

    def test_set_gains_negative_raises(self) -> None:
        """set_gains with negative value should raise ValueError."""
        ctrl = self._make_controller(kp=1.0)
        with pytest.raises(ValueError):
            ctrl.set_gains(kp=-1.0)

    def test_history_records_steps(self) -> None:
        """History should accumulate one entry per update call."""
        ctrl = self._make_controller(kp=1.0)
        ctrl.update(setpoint=1.0, measurement=0.0)
        ctrl.update(setpoint=1.0, measurement=0.5)
        assert len(ctrl.history) == 2

    def test_derivative_on_measurement_no_setpoint_kick(self) -> None:
        """Derivative is taken on measurement: SP step should not cause huge D spike."""
        ctrl = self._make_controller(kp=0.0, ki=0.0, kd=1.0, dt=0.01)
        # Measurement stays at 0; setpoint jumps from 0 to 10
        u = ctrl.update(setpoint=10.0, measurement=0.0)
        # D term based on measurement change, which is 0 on first step
        assert abs(u) < 0.1  # no kick expected
