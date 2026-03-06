# Positive-Pressure Biochar Retort Concept – Updated Documentation

## Purpose

This document updates the prior concept to reflect a **slight positive-pressure operating philosophy** for the biochar reactor system.

The design basis here is **low positive pressure**, on the order of approximately **1 psig or less as a nominal operating target**, rather than a vacuum or negative-draft configuration.

This update reflects the following design viewpoints:

- all leaks are undesirable,
- slight vacuum does not make leakage acceptable,
- pressure relief is still required even for systems operating under vacuum,
- and any blower or rotating outlet device can become an obstruction or “cork” if it trips, slows, fouls, or otherwise fails to pass the required gas flow.

Accordingly, this version does **not** treat negative pressure as inherently safer or inherently more correct. It treats pressure philosophy as a design choice with its own control and failure-mode consequences.

---

## 1. Updated Design Philosophy

The revised concept is a:

> **low-positive-pressure, controlled-atmosphere biochar retort system with metered process air, deliberate pressure control, downstream hot-gas utilization for drying, sealed hot-char discharge, and dedicated overpressure protection independent of rotating equipment.**

Key intent:

- only the air intentionally introduced to the process should enter the system,
- the process should not depend on ambient inleakage through cold-zone leaks,
- raw gas should not need to be sucked through a dirty-gas blower,
- and the pressure boundary should be treated seriously even at low pressure.

This is especially relevant for a hot, dirty, solids-handling reactor where:
- suctioning raw gas through downstream equipment can create fouling and temperature constraints,
- cold-zone air ingress can disrupt oxygen exclusion and reaction control,
- and blower failure can create a blocked-outlet condition if not accounted for.

---

## 2. Recommended Positive-Pressure Process Concept

### 2.1 Overall flow scheme

1. Wet biomass enters a feed hopper.
2. Feed is pre-dried using recovered hot exhaust gas.
3. Dried feed passes through a top rotary airlock into the reactor.
4. The reactor operates at slight positive pressure under controlled atmosphere.
5. Pyrolysis gas exits the reactor to an external combustor / thermal oxidizer.
6. Combustor exhaust provides heat for:
   - reactor duty,
   - and upstream feed drying.
7. Hot biochar exits through a bottom rotary airlock.
8. Biochar is cooled in a sealed water-cooled auger.
9. Product transfers to a sealed char receiver or bin.
10. Independent overpressure protection and emergency venting are provided so that normal outlet devices are not the only pressure release path.

### 2.2 Key distinction versus the earlier version

This version does **not** rely on:
- a dirty-gas suction fan pulling vacuum on raw gas,
- ambient leakage being tolerated as “inward” and therefore acceptable,
- or rotating outlet equipment being implicitly trusted as the only path for pressure release.

Instead, it relies on:
- metered inlet air and/or combustion air,
- pressure measurement and active control,
- controlled exhaust resistance/backpressure,
- and independent relief / emergency vent capacity.

---

## 3. Updated Pressure-Control Philosophy

### 3.1 Operating target

- **Nominal operating pressure:** slight positive pressure, approximately **0.2 to 1.0 psig** depending on final design and controllability.
- Pressure should be high enough to avoid unwanted ambient ingress through cold leaks.
- Pressure should be low enough to avoid unnecessary stress, leakage rate increase, and sealing difficulty.

This should be treated as a controllable operating envelope, not a vague “about a psi.”

### 3.2 Basic control architecture

The recommended positive-pressure strategy is:

- **PT-101** measures reactor/gas-space pressure.
- **PIC-101** controls process pressure.
- **Manipulated variables** may include:
  - process air blower speed,
  - combustion air control valve,
  - vent/backpressure control valve,
  - or a combination of inlet flow control plus downstream backpressure trim.

A practical arrangement is:

- one **process air / combustion air blower** upstream,
- one **control valve or damper** on the hot-gas discharge or oxidizer path,
- one **independent emergency relief device** that does not depend on blower operation.

This avoids the design mistake of assuming the fan itself is the safety path.

### 3.3 Why this matters

If the outlet path includes a blower, damper, oxidizer, flare, or fouling-prone ducting, then any of these can:
- slow flow,
- stop flow,
- choke flow,
- or act as a restriction under upset conditions.

So the control system must distinguish between:
- **normal flow control**, and
- **independent pressure protection**.

Those are not the same thing.

---

## 4. Required Safety Functions for Positive Pressure

### 4.1 Independent overpressure protection

A positive-pressure version should include:

- **PSV and/or rupture panel**
- **dedicated vent path**
- **safe discharge location**
- **high-high pressure trip**
- and ideally a path that remains available even if the blower is off or a rotating device trips.

This is mandatory in principle, not optional polish.

### 4.2 Gas detection

Because the reactor and associated hot-gas spaces operate above ambient pressure, outward leakage must be assumed possible. Include at minimum:

- **CO detector(s)**
- **LEL / combustible gas detector(s)** near likely leak points:
  - airlocks,
  - seals,
  - burner train area,
  - hot-gas duct transitions,
  - auger enclosure interfaces.

### 4.3 Startup and shutdown discipline

For a positive-pressure system, startup and shutdown logic must explicitly define:

- pre-start permissives,
- purge logic,
- ignition sequence,
- process-air enable sequence,
- burner enable sequence,
- reactor-pressure limits,
- relief device status,
- blower/fan running status,
- and controlled burn-down or cooldown sequence.

Do not assume operators will improvise these consistently.

---

## 5. Updated Equipment Philosophy

### 5.1 Feed hopper and feed system

Recommended:

- gravity hopper with steep walls,
- external knocker / vibrator,
- top rotary airlock,
- optional feed screw if tighter metering is needed.

The top rotary airlock must be treated as:

- a solids feeder,
- a gas isolation component,
- and part of the effective pressure boundary.

### 5.2 Reactor body

Recommended reactor:

- vertical retort / shaft-style reactor,
- externally heated or jacket-heated,
- closed top,
- pressure-rated only to the degree justified by the selected operating pressure and upset scenarios,
- no casual assumption that “low pressure” means design discipline can be relaxed.

### 5.3 Combustor / thermal oxidizer

The combustor should:

- receive raw pyrolysis gas,
- provide heat to the reactor,
- generate hot exhaust for drying,
- and have its own combustion-air and temperature controls.

If positive pressure is used upstream, the combustor and connecting ductwork should be reviewed carefully for:
- propagation risk,
- isolation logic,
- and pressure interaction with the reactor.

### 5.4 Bottom discharge and hot-char handling

Recommended:

- bottom rotary airlock,
- sealed water-cooled auger,
- sealed char receiver.

The bottom airlock is a pressure-boundary component and hot-solids device simultaneously. It should be specified accordingly.

Do **not** rely on cooling air under the discharge as a standard feature of the process concept.

### 5.5 Dryer

Keep the dryer upstream of the reactor feed valve and use recovered hot exhaust gas.

This remains one of the best thermal integration steps in the entire concept.

---

## 6. Updated Instrumentation List

The minimum instrumentation should now explicitly support a positive-pressure operating philosophy.

### 6.1 Feed section

- **LT-101** – hopper high level
- **LT-102** – hopper low level

### 6.2 Dryer

- **TT-111** – dryer inlet gas temperature
- **TT-112** – dryer outlet gas temperature

### 6.3 Reactor

- **PT-101** – reactor pressure
- **PSHH-101** – reactor high-high pressure shutdown logic
- **TT-102** – upper-zone temperature
- **TT-103** – active pyrolysis-zone temperature
- **TT-104** – lower-zone temperature

### 6.4 Gas path / combustor

- **PT-102** – raw gas pressure or combustor inlet pressure
- **TT-109** – raw gas temperature
- **TT-110** – combustor temperature
- **O2-101** – oxidizer exhaust oxygen
- **FT/FIC-101** – process/combustion air flow

### 6.5 Char cooling and discharge

- **TT-105** – hot-char inlet temperature to auger
- **TT-106** – cooled-char discharge temperature
- **FS-101** – cooling-water flow switch
- **TT-107** – cooling-water inlet temperature
- **TT-108** – cooling-water outlet temperature

### 6.6 Safety detection

- **CO detector(s)**
- **LEL detector(s)**
- flame safeguard on startup burner
- motor overloads on airlocks, auger, and blower/fan

---

## 7. Updated Control Loops

### 7.1 Pressure control loop

**PIC-101**
- PV: PT-101
- MV: process air blower speed and/or backpressure valve
- Objective: maintain slight positive reactor/gas-space pressure

Recommended concept:
- maintain stable controlled positive pressure,
- avoid oscillation,
- avoid depending on blower speed alone if downstream restriction varies significantly.

### 7.2 Reactor temperature control

**TIC-103**
- PV: TT-103
- MV: combustor duty, burner trim, combustion-air trim
- Objective: maintain active pyrolysis temperature

### 7.3 Dryer control

**TIC-111 / TIC-112**
- PV: dryer inlet/outlet temperatures
- MV: recovered hot-gas flow or bypass
- Objective: hit feed moisture target without overheating or wasting heat

### 7.4 Char discharge permissive

**TIC-106**
- PV: TT-106
- MV: product discharge permissive / block transfer
- Objective: prevent transfer of unsafe hot char to storage

### 7.5 Cooling-water flow protection

**FSL-101**
- PV: FS-101
- MV: feed shutdown permissive
- Objective: stop feed if char cooling is compromised

---

## 8. Updated Shutdown and Interlock Philosophy

### Trips that should stop feed immediately

- reactor high-high pressure
- loss of pressure-control capability
- loss of burner flame when burner is required
- loss of cooling-water flow
- high char outlet temperature
- top or bottom rotary valve overload/jam
- auger overload/jam
- high CO or LEL alarm
- loss of required blower/fan status if part of the operating mode
- loss of safe vent / relief availability if monitored

### Safe shutdown sequence

1. Stop biomass feed.
2. Stop top rotary airlock.
3. Maintain controlled burnout path if safe to do so.
4. Isolate burner fuel if required by sequence.
5. Maintain cooling-water flow to char auger.
6. Maintain vent path / pressure control as long as required for safe cooldown.
7. Alarm operator and transition to monitored shutdown state.

---

## 9. Updated Engineering Notes on Leakage

This design basis should explicitly state:

- **all leaks are undesirable, regardless of pressure philosophy**
- vacuum does not make a leak “acceptable”
- positive pressure does not make a leak “acceptable”
- the design objective is to minimize leakage, detect leakage, and manage upset consequences

This means:
- sealing quality matters,
- shaft seals matter,
- gasketing matters,
- rotary airlock condition matters,
- inspection and maintenance matter,
- and the control system should never assume leakage is benign.

---

## 10. Revised P&ID Guidance for the Positive-Pressure Variant

The P&ID or conceptual drawing should now include, at minimum:

- top and bottom rotary airlocks
- closed reactor
- process/combustion air blower
- pressure transmitter PT-101
- pressure controller PIC-101
- high-high pressure trip logic
- independent relief device
- dedicated vent path
- combustor / thermal oxidizer
- feed dryer
- water-cooled sealed auger
- sealed char receiver
- CO detector
- LEL detector
- burner management / flame safeguard

The drawing should also show that:
- the blower is part of the operating flow path,
- but **not** the only pressure-protection path.

---

## 11. Updated YAML / Workflow Guidance

For the open DXF workflow, the positive-pressure YAML variant should add or modify:

- `pressure_mode: positive`
- operating pressure setpoint
- relief device details
- vent-path details
- process air blower details
- LEL detector(s)
- extra shutdown logic
- explicit note that blower trip must not trap pressure

Suggested additions:

```yaml
pressure_control:
  mode: "positive"
  normal_operating_pressure_psig: 0.5
  allowable_range_psig: [0.2, 1.0]
  control_strategy:
    - "PT-101 to PIC-101"
    - "PIC-101 trims process air blower and/or backpressure valve"
  independent_relief_required: true
  notes:
    - "Normal rotating equipment must not be the only overpressure path."
    - "Provide independent vent / PSV / rupture panel."