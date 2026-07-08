"""Whiskers' two lookup abilities — and nothing else.

Marge's rule (email.txt #4/#5): Whiskers must be able to *actually look things up*
rather than guess, and must NOT be able to poke around servers or the internet.
So the agent's entire toolset is the two in-process tools defined here, exposed as
an SDK MCP server. No Read/Glob/Grep/Bash/Web — see app.py's allowed_tools.

The data below is small, curated, and deliberately conservative. Whiskers is not a
vet; these ranges/lists exist to ground answers, and the system prompt always defers
to a real veterinarian for anything serious.
"""

from claude_agent_sdk import create_sdk_mcp_server, tool

# --- Reference data -------------------------------------------------------

# Normal resting ranges for an adult domestic cat.
VITAL_RANGES = {
    "temperature_c": (37.8, 39.2),   # °C  (≈100.0–102.5 °F)
    "heart_rate_bpm": (140, 220),    # beats per minute
    "resp_rate_bpm": (20, 30),       # breaths per minute at rest
}

# Food & plant safety. Keys are lowercase; matched by substring so "dark chocolate"
# hits "chocolate". Level is one of: "emergency", "toxic", "caution", "safe".
FOOD_SAFETY = {
    # Emergencies — time-critical, tell them to go to the vet NOW.
    "lily": ("emergency", "Lilies are extremely toxic to cats — even pollen or vase water can cause fatal kidney failure. This is an emergency."),
    "chocolate": ("emergency", "Chocolate contains theobromine, which is toxic to cats and can cause seizures and heart problems."),
    "grape": ("emergency", "Grapes and raisins can cause acute kidney failure in cats."),
    "raisin": ("emergency", "Grapes and raisins can cause acute kidney failure in cats."),
    "onion": ("toxic", "Onions (and garlic, leeks, chives) damage cat red blood cells and cause anemia. Toxic even cooked or powdered."),
    "garlic": ("toxic", "Garlic is even more potent than onion for cats — it damages red blood cells and causes anemia."),
    "xylitol": ("toxic", "Xylitol (a sugar-free sweetener) is toxic to cats."),
    "alcohol": ("toxic", "Alcohol is toxic to cats even in small amounts."),
    "caffeine": ("toxic", "Caffeine is toxic to cats."),
    "tulip": ("toxic", "Tulips are toxic to cats, especially the bulb."),
    "poinsettia": ("caution", "Poinsettia is mildly irritating — usually causes drooling or an upset stomach rather than serious harm."),
    "milk": ("caution", "Most adult cats are lactose intolerant; milk often causes stomach upset and diarrhea."),
    "cheese": ("caution", "Cheese is not toxic but many cats are lactose intolerant — small amounts at most, and it's high in fat/salt."),
    "tuna": ("caution", "Tuna is fine as an occasional treat, but not as a diet — too much can cause mercury exposure and nutritional imbalance."),
    "raw fish": ("caution", "Raw fish can carry parasites and an enzyme that destroys vitamin B1 (thiamine). Cook it first."),
    "dog food": ("caution", "Dog food isn't toxic but lacks taurine and other nutrients cats need — not a substitute for cat food."),
    "bread": ("safe", "Plain baked bread is generally safe in small amounts, but offers no nutritional value. Avoid raw dough."),
    "carrot": ("safe", "Cooked plain carrot is safe in small amounts as an occasional treat."),
    "chicken": ("safe", "Plain cooked chicken (no bones, no seasoning) is a safe, well-loved treat."),
    "salmon": ("safe", "Plain cooked salmon is safe in small amounts as an occasional treat."),
    "pumpkin": ("safe", "Plain cooked pumpkin is safe and can even help with mild digestive issues."),
    "catnip": ("safe", "Catnip is safe and non-addictive — enjoy the zoomies."),
    "blueberry": ("safe", "Blueberries are safe as an occasional small treat."),
    "spinach": ("safe", "Plain spinach is safe in small amounts for most cats (avoid if the cat has a history of urinary/kidney stones)."),
}


# --- Tools ----------------------------------------------------------------

@tool(
    "check_vitals",
    "Check a cat's vital signs (body temperature in Celsius, heart rate in beats/min, "
    "respiratory rate in breaths/min) against normal feline ranges. Pass whichever "
    "values the customer gave; omit the rest.",
    {"temperature_c": float, "heart_rate_bpm": float, "resp_rate_bpm": float},
)
async def check_vitals(args):
    labels = {
        "temperature_c": ("Body temperature", "°C"),
        "heart_rate_bpm": ("Heart rate", "bpm"),
        "resp_rate_bpm": ("Respiratory rate", "breaths/min"),
    }
    lines = []
    any_abnormal = False
    for key, (label, unit) in labels.items():
        value = args.get(key)
        if value is None:
            continue
        low, high = VITAL_RANGES[key]
        if value < low:
            verdict = f"LOW (normal {low}–{high} {unit})"
            any_abnormal = True
        elif value > high:
            verdict = f"HIGH (normal {low}–{high} {unit})"
            any_abnormal = True
        else:
            verdict = f"normal ({low}–{high} {unit})"
        lines.append(f"- {label}: {value} {unit} → {verdict}")

    if not lines:
        text = ("No vital signs were provided. Ask the customer for a body temperature (°C), "
                "heart rate (bpm), or respiratory rate (breaths/min).")
    else:
        summary = ("One or more readings are outside the normal range — advise the customer to "
                   "contact a veterinarian." if any_abnormal
                   else "All provided readings are within normal range.")
        text = "Vital sign check:\n" + "\n".join(lines) + f"\n\n{summary}"

    return {"content": [{"type": "text", "text": text}]}


@tool(
    "check_food_safety",
    "Look up whether a food or plant is safe, caution, toxic, or an emergency for cats. "
    "Pass the item the customer mentioned (e.g. 'chocolate', 'lily', 'tuna').",
    {"item": str},
)
async def check_food_safety(args):
    item = (args.get("item") or "").strip().lower()
    if not item:
        return {"content": [{"type": "text", "text": "No item was provided to look up."}]}

    match = next((data for key, data in FOOD_SAFETY.items() if key in item), None)

    if match is None:
        text = (f"'{item}' is not in Whiskers' safety database. Do not guess — tell the customer "
                "you don't have a confirmed answer and recommend they check with their veterinarian "
                "or the ASPCA Animal Poison Control Center before letting their cat have it.")
    else:
        level, reason = match
        headers = {
            "emergency": "🚨 EMERGENCY — TOXIC TO CATS",
            "toxic": "❌ TOXIC — do not feed",
            "caution": "⚠️ CAUTION — small amounts / not recommended",
            "safe": "✅ SAFE in moderation",
        }
        text = f"Food/plant safety for '{item}':\n{headers[level]}\n{reason}"
        if level == "emergency":
            text += "\n\nThis is time-critical — the customer should get to an emergency vet immediately."

    return {"content": [{"type": "text", "text": text}]}


# In-process MCP server carrying Whiskers' only two abilities.
whiskers_server = create_sdk_mcp_server(
    name="whiskers",
    version="1.0.0",
    tools=[check_vitals, check_food_safety],
)

# Fully-qualified tool names for the agent's allowlist (mcp__<server>__<tool>).
WHISKERS_TOOL_NAMES = [
    "mcp__whiskers__check_vitals",
    "mcp__whiskers__check_food_safety",
]
