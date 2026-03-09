# Biochar Reactor Design Review – Minimal-Instrumentation Vertical Retort Concept

## Purpose

This document summarizes a practical, low-complexity concept for a **biochar-first woody biomass reactor** intended to:

- convert variable-moisture woody biomass into biochar,
- use evolved pyrolysis gas as the primary heat source after startup,
- recover hot exhaust gas for feed drying,
- minimize operator attention,
- and keep the equipment simple enough for a pilot or demonstration system.

The recommended concept is a **vertical oxygen-limited retort / shaft-style pyrolysis reactor** with:

- top rotary airlock feed,
- gravity-driven solids movement,
- externally heated combustion annulus / oxidizer,
- bottom hot-duty rotary airlock discharge,
- enclosed water-cooled char auger,
- sealed product bin,
- and a simple hot-gas dryer for wet feedstock.

This is not a fabrication package or detailed P&ID. It is a basis-of-design concept for technical review.

---

## 1. Recommended Process Concept

### 1.1 Process objective

The process should be designed to maximize **biochar production and heat recovery**, not to make engine-grade syngas.

The preferred operating concept is:

1. Feed woody biomass through a gravity hopper and top rotary airlock.
2. Move biomass downward through a vertical oxygen-limited retort.
3. Heat the retort indirectly using a surrounding combustion zone / annulus.
4. Route released pyrolysis vapors and gases to the external combustor / thermal oxidizer.
5. Use combustor heat first to maintain pyrolysis temperature.
6. Recover remaining hot exhaust for drying wet incoming feedstock.
7. Discharge hot char through a bottom rotary airlock.
8. Cool char in an enclosed water-cooled auger.
9. Transfer cooled char into a sealed product bin.

This approach is simpler and more robust than a gasifier-generator concept, because low-Btu pyrolysis gas is much easier to burn for process heat than to clean and stabilize for engine use.

### 1.2 Key design philosophy

The design should follow these principles:

- **Biochar is the main product.**
- **Process heat is internally recovered wherever possible.**
- **Feed drying is essential for efficiency.**
- **Gas side should run at slight negative pressure.**
- **Air ingress must be minimized.**
- **Hot char must remain isolated until cooled to a safe temperature.**
- **Instrumentation should be minimal but sufficient for safe unmanned operation.**

---

## 2. Why This Concept is Preferred

### 2.1 Advantages over power generation from syngas

Using syngas in a generator is a poor primary value proposition for this project because:

- grid electricity in Richland is relatively inexpensive,
- dual-fuel engine operation still requires diesel pilot fuel,
- small systems suffer from poor economics and added maintenance,
- gas cleanup for engine use is much more demanding,
- and the generator route shifts the project away from its strongest case: **biochar from forest residues**.

The biochar-first heat-integrated design is stronger because:

- it better supports wildfire-risk-reduction and wood-residue-utilization messaging,
- it avoids the hardest syngas-cleaning problems,
- it supports a cleaner carbon-storage story via biochar,
- and it better matches a simple demonstration plant architecture.

### 2.2 Main efficiency drivers

The system efficiency will depend primarily on:

1. **Feed moisture content**
2. **Air leakage through feed and discharge systems**
3. **Quality of heat integration**
4. **Heat loss through vessel walls and ducting**
5. **How safely and efficiently hot biochar is cooled**

This means the project will live or die more on solids handling and thermal integration than on the reactor shell itself.

---

## 3. Recommended Process Flow Description

### 3.1 Feed handling and metering

Woody biomass is stored in a gravity-fed hopper with steep walls. The hopper should include simple anti-bridging features such as:

- external vibrators or knockers,
- steep wall geometry,
- optional live-bottom or agitation if needed.

**Important recommendation:** do **not** inject plant compressed air into the hot solids zone as a normal anti-bridging strategy. Ambient air intrusion reduces char yield, creates local oxidation, and hurts efficiency.

Feed exits the hopper through a **high-temperature top rotary airlock valve**. The valve provides:

- basic solids metering,
- partial gas isolation,
- reduced oxygen ingress to the reactor.

If better feed-rate control is required, an additional metering screw can be added above or below the rotary valve.

### 3.2 Reactor section

The reactor is a **vertical shaft-style retort** operated in an oxygen-limited manner.

Biomass descends by gravity through three functional zones:

- **Top zone:** drying / preheating
- **Middle zone:** active pyrolysis
- **Bottom zone:** hot char hold-up / discharge preparation

The vessel should be insulated heavily, and refractory may be required depending on final operating temperature and shell design.

The reactor should not be run as a positive-pressure vessel for normal operation. Instead, the gas side should be maintained at **slight negative pressure** so that leaks tend to draw inward rather than push hot combustible gas outward.

### 3.3 External heating and gas use

Pyrolysis gas released from the reactor should be routed **hot** to a surrounding **combustion annulus** or a dedicated **thermal oxidizer**.

The purpose of this combustion zone is to:

- fully oxidize pyrolysis vapors and gases,
- provide process heat to maintain pyrolysis,
- avoid raw tar condensation,
- and create a usable hot exhaust stream for drying.

A propane startup burner or pilot-assisted burner should be included to bring the system up to temperature before pyrolysis gas production becomes self-sustaining.

### 3.4 Heat recovery and feed drying

Hot exhaust from the combustor should be used for **feed drying**.

This is one of the most important design features because wet biomass strongly reduces thermal efficiency. The dryer can be a simple hot-gas drying section upstream of the reactor.

The project should be marketed as **tolerant of variable-moisture biomass with integrated drying**, not as a magical system that can process extremely wet feed with no efficiency penalty.

### 3.5 Char discharge and cooling

Hot biochar exits the bottom of the reactor through a **high-temperature bottom rotary airlock valve**.

The char is then transferred into an **enclosed water-cooled screw auger**. The purpose of the cooling auger is to:

- reduce char temperature below safe handling / storage conditions,
- keep the char isolated from ambient oxygen,
- and deliver product continuously to a sealed collection bin.

The cooled char should not be discharged openly to atmosphere until it is verified to be at a safe temperature.

### 3.6 Product storage

Biochar should be discharged into a **sealed char bin** or covered storage vessel.

This reduces the risk of:

- re-ignition,
- smoldering,
- dust release,
- and uncontrolled oxygen exposure.

---

## 4. Complete ASCII Process Sketch

```text
                          ┌──────────────────────────────────────────────┐
                          │                FEED HOPPER                  │
                          │  gravity-fed, steep walls, level switches   │
                          │  optional external vibrator / knocker       │
                          └───────────────┬──────────────────────────────┘
                                          │
                                   LT-101 │  High hopper level
                                   LT-102 │  Low hopper level
                                          │
                                ┌─────────▼─────────┐
                                │   RV-101          │
                                │ TOP ROTARY AIRLOCK│
                                └─────────┬─────────┘
                                          │
                                   TT-101 │ Feed inlet temp
                                   PT-101 │ Reactor top pressure
                                          │
                 ┌────────────────────────▼────────────────────────┐
                 │         VERTICAL PYROLYSIS / RETORT VESSEL      │
                 │                                                 │
                 │   Zone 1: Drying / Preheat                      │
                 │      TT-102                                     │
                 │                                                 │
                 │   Zone 2: Active Pyrolysis                      │
                 │      TT-103                                     │
                 │                                                 │
                 │   Zone 3: Hot Char Hold-up                      │
                 │      TT-104                                     │
                 │                                                 │
                 │   external vibrator pads / knockers only        │
                 └───────────────┬─────────────────────────────────┘
                                 │
                                 │ char downflow
                           ┌─────▼─────┐
                           │ RV-102    │
                           │BOTTOM     │
                           │ROTARY     │
                           │AIRLOCK    │
                           └─────┬─────┘
                                 │
                           TT-105│ Hot char discharge temp
                                 │
                   ┌─────────────▼─────────────────┐
                   │ WATER-COOLED CHAR AUGER       │
                   │ enclosed / sealed             │
                   │ CW in/out                     │
                   └─────────────┬─────────────────┘
                                 │
                           TT-106│ Char outlet temp
                           FS-101│ Cooling water flow switch
                           TT-107│ CW inlet temp
                           TT-108│ CW outlet temp
                                 │
                        ┌────────▼────────┐
                        │ SEALED CHAR BIN │
                        │ with temp check │
                        └─────────────────┘


   PYROLYSIS GAS FROM TOP/SIDE OF RETORT
                                 │
                           TT-109│ Raw gas temp
                           PT-102│ Raw gas pressure
                                 │
                                 ▼
          ┌────────────────────────────────────────────────────┐
          │   COMBUSTION ANNULUS / THERMAL OXIDIZER           │
          │   burns pyrolysis gas for reactor process heat    │
          │                                                    │
Startup   │   propane startup burner / pilot                  │
fuel ---->│   XV-101 gas shutoff                              │
          │   TT-110 combustor temp                           │
          │   O2-101 stack O2                                 │
          └──────────────────┬────────────────────────────────┘
                             │ hot clean exhaust
                             ▼
                ┌──────────────────────────────────┐
                │ FEED DRYER / HOT GAS DRYING ZONE │
                │ for wet biomass                   │
                │ TT-111 dryer inlet gas temp       │
                │ TT-112 dryer outlet gas temp      │
                └──────────────────┬───────────────┘
                                   │
                                   ▼
                             to stack / flare / existing
                             cleanup train if needed

OPTIONAL DRAFT CONTROL:
small induced draft fan OR existing downstream draft device
maintaining slight negative pressure on gas side

SAFETY / CONTROL:
PSV / rupture panel on reactor if required by final design
CO monitor near equipment
flame supervision on startup burner
ESD shuts feed + fuel and maintains safe cooldown