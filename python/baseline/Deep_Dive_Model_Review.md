# Deep Dive Review: Integrated Process Simulator / Gasification Model

**Reviewer:** Claude (requested by Dieter)
**Date:** March 6, 2026
**Scope:** Core thermodynamic engine, equilibrium solver, energy balance, kinetic models, architecture, and input management

---

## 1. How the Model Works — High-Level Summary

Your model is a **Gibbs free energy minimization-based equilibrium gasification simulator** with an optional kinetic modeling layer. Here's the flow:

1. **Feedstock definition** — Ultimate/proximate analysis (C, H, O, N, S, Ash, Moisture) feeds in via `FeedstockModel` or raw dict.
2. **Element accounting** — The `EquilibriumSolver` converts mass or mole fractions into an elemental inventory (moles of C, H, O, N, S, etc.).
3. **Species selection** — The `UnifiedGibbsMinimizer` queries a species database to find all thermodynamically relevant species for those elements (CO, CO2, H2, H2O, CH4, N2, H2S, etc.), filtering by phase stability.
4. **Gibbs energy evaluation** — For each candidate species at the given T and P, the system calculates the standard Gibbs free energy using one of many backends (CoolProp, Cantera, JANAF polynomials, NASA, DIPPR, etc.).
5. **Constrained minimization** — SLSQP (scipy) minimizes the total Gibbs energy `G = Σ nᵢ·(Gᵢ° + RT·ln(xᵢ))` subject to element balance constraints `A·n = b` and non-negativity bounds.
6. **Energy balance** — A separate `EnergyBalance` module computes stream enthalpies (feed, reactants, products) to close the first-law energy balance.
7. **Kinetic layer** (separate) — Zone-based reactor models (drying, pyrolysis, oxidation, reduction) solve ODE systems for spatial evolution of species and temperature.

---

## 2. Fundamental Issues Found

### 2.1 CRITICAL: Entropy Calculation Approximation in JANAF Engine (janaf_engine.py, line ~327)

```python
# Line 327-328 in _accumulate_species_entropy
cp_avg = polys["cp"].evaluate((temperature + t_ref) / 2)
delta_s_temp = cp_avg * np.log(temperature / t_ref)
```

**The problem:** You're evaluating Cp at the midpoint temperature and treating it as constant for the entropy integral. The correct integral is `∫(Cp/T)dT`, not `Cp_avg · ln(T2/T1)`. These are mathematically different unless Cp is truly constant. For gasification temperatures (800-1500 K) versus reference (298 K), the error can be several percent.

**The fix:** Either integrate the Cp polynomial analytically (which the DIPPR107 model already does correctly — see `calculate_entropy_integral`), or use numerical quadrature. You have the polynomial coefficients; the analytical integral of `(a₀ + a₁T + a₂T² + ...)/T` is `a₀·ln(T) + a₁·T + a₂·T²/2 + ...`, which is straightforward to implement.

**Impact:** This propagates to Gibbs energy via G = H - TS, affecting equilibrium compositions when using the JANAF engine.

### 2.2 SIGNIFICANT: Biomass Initial Composition Ignores Actual Elemental Analysis (initial_composition_calculator.py, lines ~136-186)

```python
def _calculate_biomass_initial_composition(self, feed_inputs, ...):
    # Gets C, H, O from feed_inputs, normalizes them...
    # Then IGNORES them and uses hardcoded cellulose/lignin/protein fractions:
    cellulose_fraction = 0.6
    lignin_fraction = 0.25
    protein_fraction = 0.15
```

**The problem:** The method reads the actual C, H, O, N, S values from `feed_inputs`, normalizes them... and then doesn't use them at all. Instead it uses hardcoded 60/25/15 splits for cellulose/lignin/protein. The variables `C`, `H`, `O_frac`, `N`, `S`, `Ash` are computed but never referenced in the element mapping below. This means every biomass feedstock produces the same initial composition regardless of its actual analysis.

**Impact:** For the equilibrium solver this matters less (Gibbs minimization will find the right answer from the element balance), but for kinetic models that use these initial compositions as boundary conditions, the wrong starting point could cause convergence issues or incorrect zone profiles.

### 2.3 SIGNIFICANT: Duplicate Atomic Weights Defined in Multiple Places

I found atomic weight dictionaries defined in at least **four separate locations**:

- `config/physical_constants.py` — `ATOMIC_WEIGHTS` (g/mol)
- `core/equilibrium_solver.py` — `_ATOMIC_WEIGHTS` (kg/mol)
- `core/energy_balance/core.py` — `_ATOMIC_WEIGHTS` (g/mol, includes "Ash": 60.0)
- `core/energy_balance/streams.py` — `ATOMIC_WEIGHTS` (g/mol, includes "Ash": 60.0)

**The problem:** Different units (g/mol vs kg/mol) and different species coverage. The EquilibriumSolver uses kg/mol while the energy balance uses g/mol. If someone updates one and not the others, you get a silent unit mismatch. Also, "Ash" is given an assumed molecular weight of 60 g/mol in the energy balance but is not in the config constants — this could cause inconsistencies.

**The fix:** Use `config/physical_constants.py` as the single source of truth. Import from there everywhere. Convert units at the point of use.

### 2.4 MODERATE: Heat of Formation Calculator Uses BTU/lbmol Constants (heat_of_formation.py)

```python
HEAT_OF_FORMATION_PRODUCTS = {
    "CO2": -169290,  # BTU/lbmol
    "H2O": -122970,  # BTU/lbmol
    "SO2": -127710,  # BTU/lbmol
}
```

**The problem:** The rest of your model is consistently SI (kJ/mol, J/mol, Pa, K). This module uses BTU/lb and BTU/lbmol. While the internal math may be self-consistent within this calculator, at the boundary where it interfaces with the rest of the model, unit conversion errors are a real risk. There's no explicit conversion layer visible.

**Recommendation:** Convert these constants to SI at definition time and add clear unit annotations, or at minimum add a documented conversion factor at the interface boundary.

### 2.5 MODERATE: Energy Balance Calculates Feed/Product Enthalpies Twice

In `core/energy_balance/core.py`, `calculate_energy_balance()` calls:

- `calculate_feed_enthalpy(params)`
- `calculate_product_enthalpy(params, equilibrium_results)`

Then `calculate_sensible_heat_change()` calls those same two methods again. And `calculate_reaction_heat()` does further redundant work. For a single energy balance calculation, you're computing feed and product enthalpies at least 2-3 times.

**Impact:** Performance penalty, especially during parameter sweeps. Not a correctness error, but worth fixing with simple caching or computing once and passing values through.

### 2.6 MODERATE: `_calculate_gibbs_cached` Is Not Actually Cached

```python
def _calculate_gibbs_cached(self, species, temperature, pressure, engine_value):
    """Cached wrapper for Gibbs free energy calculation (Issue #9 fix)."""
    return self._calculate_gibbs_uncached(species, temperature, pressure, engine_value)
```

The docstring says "cached wrapper" and references Issue #9, but the method just passes straight through to the uncached version. The `@lru_cache` decorator that presumably existed before the mixin extraction is gone. During temperature sweeps with many species, this means recalculating Gibbs energies from scratch for every call.

**Fix:** Add `@lru_cache(maxsize=4096)` back, or implement manual memoization keyed on `(species, temperature, pressure, engine_value)`.

---

## 3. Things That Don't Make Sense

### 3.1 The engine_mapping Dict Is Defined Twice

In `unified_gibbs_minimizer.py`, the `_ENGINE_MAPPING` class attribute maps `EngineType → DatabaseType`. Then in `gibbs_energy_calculation_mixin.py` line ~106, the _exact same mapping_ is rebuilt from scratch as a local variable inside `_calculate_gibbs_uncached`. This is the kind of thing that leads to one getting updated and the other not.

### 3.2 Coal Molecular Weight Assumption

```python
# Coal average molecular weight ~12 g/mol (primarily carbon)
total_moles = 1.0 / 12.0
```

Coal is not a molecule. Using a single "molecular weight" for coal doesn't have physical meaning. The correct approach (which you already do in the elemental fallback path) is to convert each element's mass fraction to moles using that element's atomic weight. The coal-specific method adds complexity without adding accuracy.

### 3.3 The Constant Cp Model Default

```python
class ConstantCpModel:
    def __init__(self, cp_value: float = 1.0):
```

A default Cp of 1.0 kJ/(mol·K) is extremely high — that's roughly 30× the actual Cp of most gases. If this default ever gets used inadvertently (which silent fallbacks in the error handling could trigger), it would produce wildly wrong results. A safer default would be something like 0.029 kJ/(mol·K) (≈ Cp of N₂), or better yet, no default at all (require it to be specified).

### 3.4 Magic Fallback Values in Error Handlers

Throughout the energy balance code, error handlers fall back to rough approximations:

```python
except (...) as e:
    h = 1.0 * (temperature - self.T_ref)  # Cp ≈ 1.0 ???
    total_enthalpy += molar_flow * h
```

and:

```python
except (...) as e:
    return feed_rate * 1.5 * (temperature - self.T_ref) / 3600
```

These "Cp ≈ 1.0" or "Cp ≈ 1.5" fallbacks are orders of magnitude wrong and silently produce garbage results without warning the user. It would be better to fail loudly or return a clearly flagged error state.

---

## 4. The Input File Question — You Are NOT Overcomplicating Things

Your instinct is right. Let me explain why, and what the best approach is.

### 4.1 Current State: Inputs Are Scattered

Right now, process parameters enter the model through:

- Raw Python dicts passed to `calculate_energy_balance(params, equilibrium_results)`
- `FeedstockModel` dataclass (good, but only covers feedstock)
- `EquilibriumInput` Pydantic model (good, but only covers solver inputs)
- `GasificationRequest` Pydantic model (API layer only)
- `AppConfig` / `ThermodynamicConfig` (Pydantic settings, only covers engine config)
- Hardcoded defaults sprinkled throughout (e.g., `feed_rate=100.0`, `temperature=1000.0`, `heat_loss=500.0`)

The `params` dict is the worst offender — it's an untyped bag where any caller can put whatever they want. Different functions expect different keys (`"feed_rate"` vs `"Feed Rate"` vs `"flow_rate"`), and defaults are scattered across dozens of methods.

### 4.2 Yes, Create a Standardized Input File — Here's the Right Way

The pattern you want is a **case definition file**. In process simulation, this is standard practice (Aspen Plus has "bkp" files, HYSYS has "hsc" files, DWSIM uses XML). Here's what I'd recommend:

**Use a YAML or TOML input file** with a corresponding Pydantic model for validation. YAML is more readable for engineers; TOML is simpler but less expressive. Given your use case, YAML is probably better.

Here's a concrete schema:

```yaml
# gasification_case.yaml
case_name: "Illinois No. 6 Baseline"
description: "Baseline gasification of Illinois No. 6 coal at 1 atm"

feedstock:
  name: "Illinois No. 6 Coal"
  ultimate_analysis: # dry basis, wt%
    carbon: 63.75
    hydrogen: 4.50
    oxygen: 6.88
    nitrogen: 1.25
    sulfur: 2.51
    ash: 9.70
  proximate_analysis:
    moisture: 11.12
    volatile_matter: 36.86
    fixed_carbon: 44.19
    ash: 9.70
  heating_value:
    hhv_btu_per_lb: 11666
  feed_rate_kg_h: 1000.0

reactor:
  temperature_k: 1200.0
  pressure_kpa: 101.325
  type: "equilibrium" # or "kinetic_downdraft", "kinetic_coupled"

oxidant:
  type: "air" # "air", "oxygen", "enriched_air"
  equivalence_ratio: 0.35
  temperature_k: 298.15

steam:
  flow_kg_h: 200.0
  temperature_k: 473.15

energy_balance:
  power_input_kw: 0.0
  heat_loss_kw: 500.0

solver:
  engine: "auto" # "coolprop", "janaf", "cantera", etc.
  tolerance: 1.0e-8
  max_iterations: 1000

output:
  include_energy_balance: true
  include_sankey: false
  export_format: "json"
```

Then define a Pydantic model that mirrors this:

```python
class GasificationCase(BaseModel):
    case_name: str
    feedstock: FeedstockConfig
    reactor: ReactorConfig
    oxidant: OxidantConfig
    steam: SteamConfig = SteamConfig()
    energy_balance: EnergyBalanceConfig = EnergyBalanceConfig()
    solver: SolverConfig = SolverConfig()
```

### 4.3 Why This Is the Right Approach

- **Reproducibility** — Every run is fully defined by a single file. You can version-control cases, share them, diff them.
- **Validation at the boundary** — Pydantic catches errors at load time, not deep inside a calculation. No more "KeyError: 'feed_rate'" at line 437.
- **No more scattered defaults** — Defaults live in one place (the Pydantic model), not sprinkled across 50 methods.
- **Parameter sweeps become trivial** — Load a base case, override one field, run. You could even support a `sweep` section in the YAML.
- **Frontend/API/CLI all use the same input** — The API already has `GasificationRequest`; a case file just serializes it.

### 4.4 Implementation Strategy (Incremental, Low Risk)

You don't need to rewrite everything at once. Here's the path:

1. **Define the Pydantic model** (`GasificationCase`) with all the fields, including sensible defaults.
2. **Add a `load_case(path: str) -> GasificationCase`** function that reads YAML and validates.
3. **Add a `to_legacy_params(case: GasificationCase) -> dict`** adapter that converts to the current `params` dict format. This lets all existing code work unchanged.
4. **Gradually migrate** individual functions from accepting `dict` to accepting the typed model, removing the adapter layer piece by piece.

This way you get the benefits immediately (validated input files, reproducibility) without breaking anything.

---

## 5. Architecture Suggestions

### 5.1 Consolidate the "Params Dict" Pattern

The single biggest improvement would be replacing the anonymous `params: dict[str, Any]` that flows through the energy balance with a typed dataclass or Pydantic model. Right now, functions like `calculate_feed_enthalpy(params)` silently fall back to `params.get("feed_rate", 100.0)` — which means if you typo the key name, you get the default with no warning.

### 5.2 Separate Thermodynamic Property Lookup from Equilibrium Solving

Your `UnifiedGibbsMinimizer` does two very different things: (1) looking up/computing Gibbs energies for species, and (2) running the constrained optimization. These should be separate classes. The property lookup service can then be shared with the energy balance, kinetic models, and any other module that needs thermodynamic data — right now each of those has its own slightly different way of getting properties.

### 5.3 Consider a Stream Object

Process simulators universally use a "stream" abstraction — an object that carries composition, temperature, pressure, flow rate, and can compute its own enthalpy/entropy. You have `GasStream` in the `ips_tools` package, but the core model doesn't use it consistently. Making all inter-module communication happen via stream objects would eliminate most of the unit confusion and key-name mismatches.

### 5.4 Unit System Discipline

I found at least four different unit conventions:

- kJ/mol (Gibbs minimizer)
- J/mol (JANAF engine internal)
- BTU/lb (heat of formation calculator)
- kW and kJ/mol mixed in energy balance

Pick one internal unit system (SI: J/mol, Pa, K) and convert at the boundaries only. Document it in a central place.

---

## 6. Quick-Win Fixes (Low Effort, High Value)

| Priority | Issue                                               | Fix                                                   | Effort   |
| -------- | --------------------------------------------------- | ----------------------------------------------------- | -------- |
| **P0**   | Biomass initial composition ignores actual analysis | Use feed_inputs values instead of hardcoded fractions | 1 hour   |
| **P0**   | `_calculate_gibbs_cached` not actually cached       | Add `@lru_cache` or manual memo dict                  | 30 min   |
| **P1**   | JANAF entropy approximation                         | Implement analytical Cp/T integral                    | 2 hours  |
| **P1**   | Duplicate atomic weights                            | Import from `physical_constants.py` everywhere        | 1 hour   |
| **P1**   | Silent fallback Cp values                           | Replace with explicit error/warning                   | 1 hour   |
| **P2**   | Redundant enthalpy calculations                     | Cache feed/product enthalpy in energy balance         | 1 hour   |
| **P2**   | Duplicate engine mapping                            | Remove local copy in mixin                            | 15 min   |
| **P3**   | BTU/lbmol constants in HoF calculator               | Convert to SI                                         | 2 hours  |
| **P3**   | Input file system                                   | Implement YAML + Pydantic case file                   | 1-2 days |

---

## 7. Summary

Your model is architecturally sound in its fundamentals — Gibbs free energy minimization with SLSQP and element balance constraints is the correct approach for equilibrium gasification. The multi-engine backend system (CoolProp, Cantera, JANAF, NASA) is well-designed and the fallback chain is thoughtful. The kinetic model layer with zone-based reactor modeling is also a solid design choice.

The main areas for improvement are:

1. **A few real bugs** that affect numerical accuracy (the JANAF entropy approximation, the unused biomass composition, the missing cache on Gibbs calculations).
2. **Scattered input management** — the `params` dict pattern is the single biggest source of fragility. An input file system with Pydantic validation would be a major improvement and you're absolutely right to be thinking about it.
3. **Unit discipline** — picking one unit system internally and converting at boundaries would prevent a whole class of bugs.
4. **DRY violations** — constants defined in multiple places will eventually lead to silent inconsistencies.

None of these are showstoppers, and the core thermodynamic math is solid. The model is well-structured for something that's grown organically — you've clearly put a lot of thought into the design-by-contract patterns, the error handling, and the modularity. The suggestions above are about taking it from "works correctly most of the time" to "works correctly all of the time and is easy to maintain."
