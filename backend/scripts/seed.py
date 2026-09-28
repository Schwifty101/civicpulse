"""Idempotent demo-data seed: >=30 realistic Urdu-influenced-English complaints spread
across every category. Classified with RuleBasedTriage directly (fast, deterministic, no
network) so seeding never depends on an LLM key or quota. Safe to run twice — each
complaint is skipped if a row with that exact text already exists.

Usage: docker compose exec backend python -m scripts.seed
"""

from app.db.session import get_sessionmaker
from app.providers.triage.rules import RuleBasedTriage
from app.repositories import complaints_repo

COMPLAINTS: list[dict] = [
    # --- water ---
    {
        "text": "Sir the water supply line has busted since fajr namaz time, whole gali is "
        "under water please send someone fast.",
        "location": "Street 12, G-9/1, Islamabad",
        "reporter_contact": "0300-1234567",
    },
    {
        "text": "Humare ghar ke samne water pipe leak ho raha hai 3 din se, bohat paani zaya "
        "ho raha hai.",
        "location": "Gulshan Block 4, Karachi",
        "reporter_contact": None,
    },
    {
        "text": "Tap water is coming completely dirty and smells bad since yesterday, whole "
        "street is affected badly.",
        "location": "Model Town Block C, Lahore",
        "reporter_contact": "0321-9988776",
    },
    {
        "text": "Water tanker line broken near the masjid, flooding the street badly, "
        "children cannot walk to school safely.",
        "location": "Al-Noor Colony, Faisalabad",
        "reporter_contact": None,
    },
    {
        "text": "No water supply in our area since four days, please check the main pipe "
        "urgently, we are suffering a lot.",
        "location": "Johar Town Phase 2, Lahore",
        "reporter_contact": "0333-4455667",
    },
    {
        "text": "Sewer line mix ho gayi hai water supply ke sath, paani peela aa raha hai, "
        "sehat ka bara masla ban gaya hai.",
        "location": "Malir Extension, Karachi",
        "reporter_contact": None,
    },
    # --- electricity ---
    {
        "text": "Transformer is sparking loudly near the masjid since evening, very "
        "dangerous for children playing nearby.",
        "location": "Street 7, F-10, Islamabad",
        "reporter_contact": "0301-2223344",
    },
    {
        "text": "Bijli ka wire latak raha hai school ke bahar, koi bacha touch kar sakta hai, "
        "bohat khatarnak hai.",
        "location": "Township, Lahore",
        "reporter_contact": None,
    },
    {
        "text": "Power outage in the whole mohalla since six hours, please restore "
        "electricity urgently, fridge items are getting spoiled.",
        "location": "Satellite Town, Rawalpindi",
        "reporter_contact": "0345-1112233",
    },
    {
        "text": "Electric meter box caught a fire spark yesterday night, we are scared to "
        "go near it now.",
        "location": "Gulberg III, Lahore",
        "reporter_contact": None,
    },
    {
        "text": "Voltage fluctuation is damaging our home appliances daily, the transformer "
        "urgently needs checking by wapda staff.",
        "location": "North Nazimabad, Karachi",
        "reporter_contact": "0312-6677889",
    },
    {
        "text": "Open electric cable hanging low on the main road, someone got a mild shock "
        "yesterday evening.",
        "location": "Cantt Area, Multan",
        "reporter_contact": None,
    },
    # --- sanitation ---
    {
        "text": "Kachra is not lifted since five days, mohalla is smelling very bad, "
        "mosquitoes bhi bohat ho gaye hain.",
        "location": "Liaquatabad, Karachi",
        "reporter_contact": "0334-5566778",
    },
    {
        "text": "Sewage drain is overflowing onto the street, very bad smell and a real "
        "health risk for the kids playing outside.",
        "location": "Shadman Colony, Lahore",
        "reporter_contact": None,
    },
    {
        "text": "Garbage dump near the park has grown huge, stray dogs and flies are "
        "everywhere now, please clear it soon.",
        "location": "Peoples Colony, Faisalabad",
        "reporter_contact": "0300-7788990",
    },
    {
        "text": "Gutter line blocked hai humari gali mein, ganda pani sadak par phail raha "
        "hai roz.",
        "location": "Latifabad Unit 6, Hyderabad",
        "reporter_contact": None,
    },
    {
        "text": "Waste collection truck has not come in two weeks, garbage is piling up "
        "outside every house on our street.",
        "location": "Wapda Town, Lahore",
        "reporter_contact": "0321-3344556",
    },
    {
        "text": "Open drain beside the mosque is full of sewage waste, namazi log bohat "
        "pareshan hain is wajah se.",
        "location": "Green Town, Lahore",
        "reporter_contact": None,
    },
    # --- roads ---
    {
        "text": "Big gaddha pothole in front of the government school, a bike wala gir gaya "
        "kal raat isi wajah se.",
        "location": "Main Boulevard, Gulberg, Lahore",
        "reporter_contact": "0300-9988112",
    },
    {
        "text": "Road has huge cracks after the rain, cars are getting damaged daily, please "
        "repair it soon before an accident happens.",
        "location": "University Road, Peshawar",
        "reporter_contact": None,
    },
    {
        "text": "Manhole cover is missing on the main road, very dangerous at night for "
        "pedestrians walking home.",
        "location": "Saddar, Karachi",
        "reporter_contact": "0345-2233445",
    },
    {
        "text": "Speed breaker is broken and too high now, scooty walon ko bohat problem ho "
        "rahi hai roz subah.",
        "location": "DHA Phase 5, Lahore",
        "reporter_contact": None,
    },
    {
        "text": "Footpath is completely damaged, senior citizens cannot walk safely near "
        "the market anymore.",
        "location": "Anarkali Bazaar, Lahore",
        "reporter_contact": "0333-6655443",
    },
    {
        "text": "Traffic signal is not working at the main chowk since three days, bohat "
        "accidents ka khatra ban gaya hai.",
        "location": "Kalma Chowk, Lahore",
        "reporter_contact": None,
    },
    # --- streetlights ---
    {
        "text": "Street light band hai since one week, ladies feel unsafe walking at night "
        "in this gali now.",
        "location": "Model Colony, Karachi",
        "reporter_contact": "0301-7788221",
    },
    {
        "text": "Pole light near the park is flickering and now completely dead, whole "
        "area is very dark at night.",
        "location": "Bahria Town Phase 4, Rawalpindi",
        "reporter_contact": None,
    },
    {
        "text": "All streetlights on our road are off since the storm, chain snatching "
        "incidents have increased a lot.",
        "location": "Airport Road, Multan",
        "reporter_contact": "0312-4433221",
    },
    {
        "text": "Lamp post is leaning dangerously and the street light wire is exposed, "
        "children play right next to it.",
        "location": "Samanabad, Lahore",
        "reporter_contact": None,
    },
    {
        "text": "Dark street at night because streetlights never turn on anymore, we "
        "request urgent repair from the department.",
        "location": "Sector I-8, Islamabad",
        "reporter_contact": "0300-1122334",
    },
    # --- other ---
    {
        "text": "Stray dogs have increased a lot in our park area, people are scared to "
        "send children outside to play now.",
        "location": "F-11 Markaz, Islamabad",
        "reporter_contact": None,
    },
    {
        "text": "Noise pollution from the wedding hall goes on till 3am daily, residents "
        "cannot sleep properly the whole week.",
        "location": "Cavalry Ground, Lahore",
        "reporter_contact": "0321-5566990",
    },
    {
        "text": "Public park equipment is all broken, swings are unsafe for children to "
        "use anymore, please fix or remove them.",
        "location": "Nasheman-e-Iqbal, Lahore",
        "reporter_contact": None,
    },
    {
        "text": "Illegal encroachment on the footpath by shopkeepers has blocked the whole "
        "walking area for pedestrians.",
        "location": "Urdu Bazaar, Karachi",
        "reporter_contact": "0345-8899001",
    },
    {
        "text": "Community center roof is leaking badly and plaster is falling, unsafe for "
        "events now, needs urgent repair.",
        "location": "PECHS Block 6, Karachi",
        "reporter_contact": None,
    },
    {
        "text": "Unauthorized construction debris dumped on the empty plot, children play "
        "there daily and can easily get hurt.",
        "location": "Johar Town, Lahore",
        "reporter_contact": "0300-6677001",
    },
]


def run() -> None:
    session = get_sessionmaker()()
    provider = RuleBasedTriage()
    inserted = 0
    try:
        for complaint in COMPLAINTS:
            if complaints_repo.exists_with_text(session, complaint["text"]):
                continue
            result = provider.triage(complaint["text"], complaint["location"])
            complaints_repo.create(
                session,
                text=complaint["text"],
                location=complaint["location"],
                reporter_contact=complaint["reporter_contact"],
                category=result.category.value,
                priority=result.priority.value,
                ai_summary=result.summary,
                triaged_by="rules",
                triage_latency_ms=0,
            )
            inserted += 1
        skipped = len(COMPLAINTS) - inserted
        print(f"Seed complete: inserted {inserted} new, skipped {skipped} already present.")
    finally:
        session.close()


if __name__ == "__main__":
    run()
