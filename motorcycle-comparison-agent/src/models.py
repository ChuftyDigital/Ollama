"""
Data models for motorcycles, dealers, and scoring.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConditionRating(Enum):
    EXCELLENT = 5
    GOOD = 4
    FAIR = 3
    BELOW_AVERAGE = 2
    POOR = 1


class ServiceHistoryRating(Enum):
    FULL_DEALER = 5
    FULL_INDEPENDENT = 4
    PARTIAL = 3
    MINIMAL = 2
    NONE = 1


@dataclass
class DealerInfo:
    name: str
    address: str
    city: str
    region: str  # e.g. "England", "Wales", "Scotland"
    postcode: str
    phone: str
    email: str
    website: str = ""
    highlights: list[str] = field(default_factory=list)

    @property
    def full_address(self) -> str:
        return f"{self.address}, {self.city}, {self.postcode}"


@dataclass
class MotorcycleSpecs:
    engine_cc: int
    engine_type: str
    power_bhp: float
    torque_nm: float
    weight_kg: float
    seat_height_mm: int
    fuel_capacity_litres: float
    top_speed_mph: int
    zero_to_sixty_secs: float


@dataclass
class AnnualCosts:
    servicing: float
    insurance_estimate: float  # mid-range estimate
    fuel: float
    tyres: float
    consumables: float  # brake pads, chain, fluids etc.
    mot: float = 29.65

    @property
    def total(self) -> float:
        return (
            self.servicing
            + self.insurance_estimate
            + self.fuel
            + self.tyres
            + self.consumables
            + self.mot
        )


@dataclass
class MotorcycleListing:
    model_name: str
    year: int
    price: float
    mileage: int
    condition: ConditionRating
    service_history: ServiceHistoryRating
    optional_extras: list[str] = field(default_factory=list)
    dealer: Optional[DealerInfo] = None
    colour: str = ""
    description: str = ""
    url: str = ""
    specs: Optional[MotorcycleSpecs] = None
    annual_costs: Optional[AnnualCosts] = None
    known_issues: list[str] = field(default_factory=list)
    common_problems: list[str] = field(default_factory=list)
    group: str = ""  # "middleweight" or "supernaked"
    is_wildcard: bool = False
    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reference specifications for each model
# ---------------------------------------------------------------------------

REFERENCE_SPECS: dict[str, MotorcycleSpecs] = {
    "Triumph Street Triple R 675": MotorcycleSpecs(
        engine_cc=675,
        engine_type="Inline-3",
        power_bhp=106,
        torque_nm=68,
        weight_kg=189,
        seat_height_mm=800,
        fuel_capacity_litres=17.4,
        top_speed_mph=140,
        zero_to_sixty_secs=3.6,
    ),
    "KTM Duke 790": MotorcycleSpecs(
        engine_cc=799,
        engine_type="Parallel-Twin",
        power_bhp=105,
        torque_nm=87,
        weight_kg=189,
        seat_height_mm=825,
        fuel_capacity_litres=14.0,
        top_speed_mph=137,
        zero_to_sixty_secs=3.5,
    ),
    "Aprilia Shiver 750": MotorcycleSpecs(
        engine_cc=750,
        engine_type="V-Twin",
        power_bhp=95,
        torque_nm=76,
        weight_kg=218,
        seat_height_mm=810,
        fuel_capacity_litres=15.0,
        top_speed_mph=130,
        zero_to_sixty_secs=3.8,
    ),
    "Triumph Speed Triple": MotorcycleSpecs(
        engine_cc=1050,
        engine_type="Inline-3",
        power_bhp=135,
        torque_nm=108,
        weight_kg=213,
        seat_height_mm=815,
        fuel_capacity_litres=15.5,
        top_speed_mph=155,
        zero_to_sixty_secs=3.1,
    ),
    "KTM Super Duke": MotorcycleSpecs(
        engine_cc=1301,
        engine_type="V-Twin",
        power_bhp=180,
        torque_nm=140,
        weight_kg=200,
        seat_height_mm=835,
        fuel_capacity_litres=16.0,
        top_speed_mph=160,
        zero_to_sixty_secs=2.9,
    ),
    "Aprilia Tuono": MotorcycleSpecs(
        engine_cc=1077,
        engine_type="V4",
        power_bhp=175,
        torque_nm=121,
        weight_kg=209,
        seat_height_mm=825,
        fuel_capacity_litres=18.5,
        top_speed_mph=165,
        zero_to_sixty_secs=3.0,
    ),
}

# ---------------------------------------------------------------------------
# Estimated annual running costs per model
# ---------------------------------------------------------------------------

REFERENCE_ANNUAL_COSTS: dict[str, AnnualCosts] = {
    "Triumph Street Triple R 675": AnnualCosts(
        servicing=380,
        insurance_estimate=520,
        fuel=650,
        tyres=240,
        consumables=150,
    ),
    "KTM Duke 790": AnnualCosts(
        servicing=420,
        insurance_estimate=490,
        fuel=620,
        tyres=250,
        consumables=160,
    ),
    "Aprilia Shiver 750": AnnualCosts(
        servicing=400,
        insurance_estimate=460,
        fuel=680,
        tyres=230,
        consumables=145,
    ),
    "Triumph Speed Triple": AnnualCosts(
        servicing=450,
        insurance_estimate=680,
        fuel=780,
        tyres=300,
        consumables=180,
    ),
    "KTM Super Duke": AnnualCosts(
        servicing=520,
        insurance_estimate=780,
        fuel=850,
        tyres=320,
        consumables=200,
    ),
    "Aprilia Tuono": AnnualCosts(
        servicing=510,
        insurance_estimate=750,
        fuel=820,
        tyres=310,
        consumables=195,
    ),
}

# ---------------------------------------------------------------------------
# Common problems / buyer-beware items per model
# ---------------------------------------------------------------------------

COMMON_PROBLEMS: dict[str, list[str]] = {
    "Triumph Street Triple R 675": [
        "Regulator/rectifier failures on pre-2013 models causing charging issues",
        "Cam chain tensioner wear — listen for rattle on cold start",
        "Sprag clutch failure (starter motor one-way bearing)",
        "Coolant hose weeping at header connections",
        "Speed sensor failure causing erratic speedo readings",
        "Exhaust header studs can corrode and snap",
    ],
    "KTM Duke 790": [
        "Fuel pump relay failures — bike cuts out unexpectedly",
        "Quickshifter sensor issues on early models (2018-2019)",
        "Radiator fan relay sticking — overheating in slow traffic",
        "Display TFT screen pixel failures or water ingress",
        "Rear shock linkage bearings wear prematurely",
        "Throttle-by-wire hesitation at low RPM in some ECU map versions",
    ],
    "Aprilia Shiver 750": [
        "Starter motor solenoid failures — clicking but no crank",
        "Wiring loom chafing near the headstock",
        "Rear wheel bearing premature wear",
        "Fuel injector clogging with ethanol-blend fuel",
        "Dashboard LCD pixel fade on older models",
        "Water pump seal weeping around 20k-30k miles",
    ],
    "Triumph Speed Triple": [
        "Stator / charging system failures on 1050 models",
        "Cam chain tensioner wear — ticking on startup",
        "Coolant pipe cracking on high-mileage examples",
        "TPS (Throttle Position Sensor) drift causing rough idle",
        "Wheel bearing wear, especially front, on pre-2016 models",
        "Exhaust butterfly valve servo failure — CEL codes",
    ],
    "KTM Super Duke": [
        "Head gasket weeping on 1290 engines at high mileage",
        "Fuel pump module failures",
        "Rear shock reservoir mount cracking (early 1290 models)",
        "Exhaust valve servo linkage breakage",
        "Rear hub cush drive rubber degradation",
        "Oil weeping from cylinder base gaskets on high-mileage units",
    ],
    "Aprilia Tuono": [
        "Valve clearance checks expensive and frequent (every 15k miles)",
        "Gear position sensor failures causing false neutrals",
        "Aprilia wiring loom quality — check for chafed harnesses",
        "Rear shock linkage bearing corrosion",
        "ABS unit failures on pre-2017 models",
        "Water pump impeller wear leading to overheating",
    ],
}

# ---------------------------------------------------------------------------
# Wildcard alternatives
# ---------------------------------------------------------------------------

WILDCARD_MODELS: dict[str, dict] = {
    "middleweight": {
        "model": "Yamaha MT-07",
        "reason": (
            "Exceptional reliability, low running costs, and the CP2 twin "
            "engine is one of the most characterful in the middleweight class. "
            "Huge aftermarket support and strong residuals."
        ),
        "specs": MotorcycleSpecs(
            engine_cc=689,
            engine_type="Parallel-Twin (CP2)",
            power_bhp=74,
            torque_nm=68,
            weight_kg=182,
            seat_height_mm=805,
            fuel_capacity_litres=14.0,
            top_speed_mph=125,
            zero_to_sixty_secs=3.8,
        ),
        "annual_costs": AnnualCosts(
            servicing=280,
            insurance_estimate=380,
            fuel=520,
            tyres=200,
            consumables=120,
        ),
        "common_problems": [
            "Clutch basket rattle at idle — cosmetic, not mechanical",
            "Fuel tank seam corrosion on 2014-2016 models",
            "OEM exhaust corrodes quickly if not treated",
            "Headlight output poor — LED upgrade recommended",
            "Suspension soft for spirited riding — aftermarket fork internals common upgrade",
        ],
    },
    "supernaked": {
        "model": "Ducati Monster 1200",
        "reason": (
            "The Testastretta 11-degree engine is hugely characterful with "
            "excellent mid-range torque. Desmo servicing is expensive but the "
            "Monster 1200 has strong styling, excellent brakes, and holds "
            "its value well as a modern classic."
        ),
        "specs": MotorcycleSpecs(
            engine_cc=1198,
            engine_type="L-Twin Desmodromic",
            power_bhp=150,
            torque_nm=126,
            weight_kg=209,
            seat_height_mm=810,
            fuel_capacity_litres=16.5,
            top_speed_mph=155,
            zero_to_sixty_secs=3.0,
        ),
        "annual_costs": AnnualCosts(
            servicing=580,
            insurance_estimate=720,
            fuel=780,
            tyres=290,
            consumables=190,
        ),
        "common_problems": [
            "Desmo valve service expensive (£600-900 at dealer intervals)",
            "Rear shock linkage corrosion if not greased regularly",
            "Clutch slave cylinder weeping",
            "Dashboard display delamination on 2014-2016 models",
            "Exhaust flapper valve servo failures",
            "Battery drain if left standing — trickle charger essential",
        ],
    },
}
