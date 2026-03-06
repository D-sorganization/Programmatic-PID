"""Run a PID simulation from a YAML configuration file."""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys

import yaml

# Allow running from repo root
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from python.pid.controller import PIDConfig, PIDController
from python.simulation.runner import SimulationRunner, first_order_plant, second_order_plant

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_config(path: pathlib.Path) -> dict:  # type: ignore[type-arg]
    """Load YAML configuration from disk."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def build_plant(sim_cfg: dict) -> object:  # type: ignore[type-arg]
    """Instantiate a plant model from configuration dict."""
    plant_type = sim_cfg.get("plant_type", "first_order")
    p = sim_cfg.get("plant", {})
    if plant_type == "first_order":
        return first_order_plant(
            time_constant=float(p.get("time_constant", 1.0)),
            gain=float(p.get("gain", 1.0)),
        )
    elif plant_type == "second_order":
        return second_order_plant(
            natural_freq=float(p.get("natural_freq", 1.0)),
            damping_ratio=float(p.get("damping_ratio", 0.7)),
            gain=float(p.get("gain", 1.0)),
        )
    else:
        raise ValueError(f"Unknown plant_type: {plant_type!r}")


def main() -> None:
    """Entry point for the simulation runner CLI."""
    parser = argparse.ArgumentParser(description="Run a PID simulation from YAML config.")
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=pathlib.Path("config/example_controller.yaml"),
        help="Path to YAML configuration file.",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Show step-response plot after simulation.",
    )
    args = parser.parse_args()

    cfg_dict = load_config(args.config)
    ctrl_cfg = cfg_dict["controller"]
    sim_cfg = cfg_dict["simulation"]

    gains = ctrl_cfg["gains"]
    limits = ctrl_cfg.get("output_limits", {})

    pid_config = PIDConfig(
        kp=float(gains["kp"]),
        ki=float(gains["ki"]),
        kd=float(gains["kd"]),
        dt=float(ctrl_cfg.get("sample_period_s", 0.01)),
        output_min=float(limits.get("min", float("-inf"))),
        output_max=float(limits.get("max", float("inf"))),
        name=ctrl_cfg.get("name", "PID"),
    )
    controller = PIDController(pid_config)
    plant = build_plant(sim_cfg)

    runner = SimulationRunner(
        controller=controller,
        plant_fn=plant,  # type: ignore[arg-type]
        duration=float(sim_cfg.get("duration", 10.0)),
    )

    result = runner.run(
        setpoint=float(sim_cfg.get("setpoint", 1.0)),
        initial_state=float(sim_cfg.get("initial_state", 0.0)),
    )

    logger.info("=== Simulation Results ===")
    logger.info("  Steady-state error : %.4f", result.steady_state_error)
    logger.info("  Overshoot          : %.1f%%", result.overshoot_pct)
    logger.info("  Rise time          : %.3f s", result.rise_time)
    logger.info("  Settling time      : %.3f s", result.settling_time)

    if args.plot:
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        ax1.plot(result.time, result.setpoint, "r--", label="Setpoint")
        ax1.plot(result.time, result.measurement, "b-", label="Measurement")
        ax1.set_ylabel("Process Value")
        ax1.legend()
        ax1.grid(True)
        ax2.plot(result.time, result.control_output, "g-", label="Control Output")
        ax2.set_ylabel("Control Output")
        ax2.set_xlabel("Time (s)")
        ax2.legend()
        ax2.grid(True)
        plt.suptitle(f"PID Step Response — {pid_config.name}")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()
