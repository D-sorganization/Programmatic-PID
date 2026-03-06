"""conftest.py - pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest

from python.pid.controller import PIDConfig, PIDController


@pytest.fixture
def basic_pid_config() -> PIDConfig:
    """Return a standard PID config for testing."""
    return PIDConfig(kp=1.0, ki=0.1, kd=0.05, dt=0.01)


@pytest.fixture
def basic_controller(basic_pid_config: PIDConfig) -> PIDController:
    """Return an initialized PID controller."""
    return PIDController(basic_pid_config)
