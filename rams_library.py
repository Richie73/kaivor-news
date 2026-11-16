"""Standard hazard library for RAMS drafting (FP100).

Groundworks and civils hazards with typical controls. The drafter
offers the user these as tick-boxes; the selected hazards' controls
go into the AI prompt as the starting point, and the user reviews
every line before the RAMS is saved or printed. Nothing here is a
substitute for the author's own judgement on the day.
"""
from __future__ import annotations

HAZARDS = [
    {
        "id": "excavation-collapse",
        "name": "Excavation collapse",
        "who": "Operatives in and around the excavation",
        "severity": 5,
        "likelihood": 3,
        "controls": [
            "Batter or step the sides, or use trench support, to the design.",
            "Keep spoil, plant and materials back from the edge (minimum 1m).",
            "Inspect the excavation daily and after rain or any ground movement.",
            "No one enters an unsupported excavation deeper than 1.2m.",
            "Safe access (ladder) provided at regular intervals.",
        ],
    },
    {
        "id": "underground-services",
        "name": "Striking underground services",
        "who": "Operatives, plant operators",
        "severity": 5,
        "likelihood": 3,
        "controls": [
            "Obtain service drawings before work starts.",
            "CAT and Genny scan before breaking ground.",
            "Hand-dig trial holes over suspected services.",
            "Maintain safe digging distances from known services.",
            "Stop work and report any unknown service found.",
        ],
    },
    {
        "id": "plant-movement",
        "name": "Plant and vehicle movement",
        "who": "All site personnel, public",
        "severity": 4,
        "likelihood": 3,
        "controls": [
            "Banksman for reversing and slewing operations.",
            "Exclusion zones around slewing plant.",
            "Hi-vis worn at all times on site.",
            "Designated pedestrian routes, kept clear.",
            "Plant inspected daily; keys removed when not in use.",
        ],
    },
    {
        "id": "manual-handling",
        "name": "Manual handling",
        "who": "Operatives",
        "severity": 3,
        "likelihood": 4,
        "controls": [
            "Use mechanical aids where reasonably practicable.",
            "Two-person lifts for loads over 25kg.",
            "Correct lifting technique briefed at induction.",
            "Keep carry routes clear and level.",
            "Suitable gloves provided and worn.",
        ],
    },
    {
        "id": "dust-silica",
        "name": "Dust (silica) and fumes",
        "who": "Operatives, nearby workers",
        "severity": 4,
        "likelihood": 3,
        "controls": [
            "Water suppression on cutting, grinding and breaking.",
            "FFP3 masks where dust cannot be controlled at source.",
            "No dry sweeping of dust.",
            "COSHH assessments in place for materials used.",
            "Plant exhausts directed away from workers.",
        ],
    },
    {
        "id": "noise",
        "name": "Noise",
        "who": "Operatives, nearby workers",
        "severity": 3,
        "likelihood": 4,
        "controls": [
            "Hearing protection worn in signed zones.",
            "Quietest plant reasonably practicable for the task.",
            "Limit time in high-noise areas; rotate where needed.",
            "Warn nearby workers before noisy work starts.",
        ],
    },
    {
        "id": "vibration",
        "name": "Hand-arm vibration",
        "who": "Operatives using vibrating tools",
        "severity": 3,
        "likelihood": 3,
        "controls": [
            "Lowest-vibration tools available for the task.",
            "Trigger-time limits and job rotation.",
            "Anti-vibration gloves provided.",
            "Health surveillance where exposure is regular.",
        ],
    },
    {
        "id": "falls-height",
        "name": "Falls from height",
        "who": "Operatives working at height",
        "severity": 5,
        "likelihood": 2,
        "controls": [
            "Edge protection or fall restraint in place.",
            "Ladders inspected before use and footed or tied.",
            "No working at height in high winds.",
            "Harness worn where the assessment requires it.",
            "Exclusion zone maintained below the work.",
        ],
    },
    {
        "id": "slips-trips",
        "name": "Slips, trips and falls (same level)",
        "who": "All site personnel",
        "severity": 3,
        "likelihood": 4,
        "controls": [
            "Keep walkways clear, level and free of debris.",
            "Good housekeeping throughout the shift.",
            "Mark or remove trip hazards promptly.",
            "Adequate lighting on all routes.",
            "Suitable safety footwear worn.",
        ],
    },
    {
        "id": "traffic-management",
        "name": "Traffic management / road works",
        "who": "Operatives, road users, public",
        "severity": 4,
        "likelihood": 3,
        "controls": [
            "Chapter 8 signing, lighting and guarding.",
            "Trained traffic management operatives only.",
            "Hi-vis Class R2 worn in live traffic.",
            "Works vehicles fitted with beacons.",
            "Pedestrian diversion where footways are affected.",
        ],
    },
    {
        "id": "lifting",
        "name": "Lifting operations",
        "who": "Operatives, banksman, public",
        "severity": 4,
        "likelihood": 2,
        "controls": [
            "Lift plan in place for all lifting operations.",
            "Competent slinger/signaller used.",
            "Lifting accessories inspected before use.",
            "Exclusion zone maintained under the load.",
            "Never lift a load over people.",
        ],
    },
    {
        "id": "confined-spaces",
        "name": "Confined spaces",
        "who": "Entrants, attendants",
        "severity": 5,
        "likelihood": 2,
        "controls": [
            "Permit to work issued before entry.",
            "Atmosphere tested before entry and monitored.",
            "Trained entrant and top man in place.",
            "Rescue plan agreed and equipment on site.",
            "Ventilation provided where required.",
        ],
    },
    {
        "id": "asbestos",
        "name": "Unexpected asbestos",
        "who": "All site personnel",
        "severity": 5,
        "likelihood": 2,
        "controls": [
            "Stop work immediately if suspected material is found.",
            "Do not disturb the material.",
            "Report to the site manager at once.",
            "Licensed contractor to assess and remove.",
            "Asbestos awareness training kept current.",
        ],
    },
    {
        "id": "weather",
        "name": "Adverse weather",
        "who": "All site personnel",
        "severity": 3,
        "likelihood": 3,
        "controls": [
            "Stop work in high winds, lightning or heavy rain where it makes the task unsafe.",
            "Grit icy walkways and keep routes clear.",
            "Welfare and drying facilities available.",
            "Reassess ground conditions after rain.",
        ],
    },
]


def hazard_by_id(hazard_id):
    for hazard in HAZARDS:
        if hazard["id"] == hazard_id:
            return hazard
    return None
