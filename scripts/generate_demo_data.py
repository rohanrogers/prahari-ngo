"""
Generate synthetic demo data for the Kerala 2018 replay.
Creates ~200 realistic volunteer records across Kerala districts.
"""

import json
import random
import uuid
from datetime import datetime

# Kerala district volunteer distribution from BLUEPRINT.md
DISTRICTS = {
    "Alappuzha": {"count": 40, "lat": 9.4981, "lon": 76.3388},
    "Ernakulam": {"count": 30, "lat": 9.9312, "lon": 76.2673},
    "Thrissur": {"count": 30, "lat": 10.5276, "lon": 76.2144},
    "Kottayam": {"count": 25, "lat": 9.5916, "lon": 76.5222},
    "Pathanamthitta": {"count": 25, "lat": 9.2648, "lon": 76.7870},
    "Idukki": {"count": 20, "lat": 9.8494, "lon": 76.9710},
    "Chennai": {"count": 15, "lat": 13.0827, "lon": 80.2707},
    "Bengaluru": {"count": 15, "lat": 12.9716, "lon": 77.5946},
}

# Realistic Kerala names
FIRST_NAMES_ML = [
    "Rajan", "Suresh", "Priya", "Anitha", "Vijay", "Lakshmi", "Arun", "Deepa",
    "Rajesh", "Meena", "Santhosh", "Bindu", "Manoj", "Jaya", "Gopinath", "Sindhu",
    "Harish", "Asha", "Ramesh", "Kavitha", "Sreelal", "Divya", "Babu", "Nisha",
    "Unnikrishnan", "Lekha", "Shibu", "Sreeja", "Ajith", "Mini", "Sajeev", "Remya",
    "Pramod", "Athira", "Kiran", "Reshma", "Dileep", "Sumathi", "Vinod", "Jayashree",
    "Aneesh", "Aparna", "Sajith", "Neethu", "Biju", "Shijina", "Jithin", "Swathy",
]

LAST_NAMES_ML = [
    "Nair", "Menon", "Pillai", "Kurup", "Krishnan", "Varma", "Das", "Kumar",
    "Thomas", "Joseph", "George", "Mathew", "Philip", "Abraham", "Cherian",
    "Mohan", "Rajan", "Unni", "Babu", "Lal", "Kutty", "Amma", "Panicker",
]

FIRST_NAMES_OTHER = [
    "Rahul", "Sneha", "Arjun", "Kavya", "Vikram", "Pooja", "Siddharth", "Anjali",
    "Rohan", "Divya", "Aditya", "Neha", "Varun", "Priyanka", "Karthik", "Shreya",
]

SKILL_SETS = {
    "fisherman": {
        "raw": ["fishing boat owner", "knows backwaters", "can swim", "country boat (vallam)"],
        "normalized": ["boat_operation", "swimming", "local_knowledge"],
        "probability": 0.2,
    },
    "nurse": {
        "raw": ["registered nurse", "CPR trained", "first aid certified"],
        "normalized": ["medical_professional", "first_aid"],
        "probability": 0.1,
    },
    "driver": {
        "raw": ["auto driver", "own jeep", "knows all routes"],
        "normalized": ["driving", "transport_vehicle", "local_knowledge"],
        "probability": 0.15,
    },
    "teacher": {
        "raw": ["school teacher", "speaks Malayalam and English", "can coordinate group"],
        "normalized": ["language_translation", "coordination"],
        "probability": 0.1,
    },
    "student": {
        "raw": ["college student", "can help with logistics", "physically fit"],
        "normalized": ["logistics"],
        "probability": 0.15,
    },
    "cook": {
        "raw": ["can cook for large groups", "own gas stove", "catering experience"],
        "normalized": ["cooking"],
        "probability": 0.08,
    },
    "farmer": {
        "raw": ["farmer with tractor", "knows the land well", "strong"],
        "normalized": ["transport_vehicle", "local_knowledge"],
        "probability": 0.07,
    },
    "electrician": {
        "raw": ["electrician", "has generator", "can fix wiring"],
        "normalized": ["electrical"],
        "probability": 0.05,
    },
    "social_worker": {
        "raw": ["NGO volunteer", "field work experience", "disaster response training"],
        "normalized": ["social_work", "coordination"],
        "probability": 0.05,
    },
    "medical_doctor": {
        "raw": ["MBBS doctor", "emergency medicine", "trauma care"],
        "normalized": ["medical_professional", "first_aid"],
        "probability": 0.05,
    },
}


def generate_phone():
    """Generate a realistic Indian mobile number."""
    prefix = random.choice(["9", "8", "7", "6"])
    return prefix + "".join([str(random.randint(0, 9)) for _ in range(9)])


def generate_volunteer(district_name, district_info):
    """Generate one realistic volunteer record."""
    is_kerala = district_name not in ["Chennai", "Bengaluru"]
    
    if is_kerala:
        first = random.choice(FIRST_NAMES_ML)
        last = random.choice(LAST_NAMES_ML)
        languages = ["ml", "en"]
        if random.random() < 0.2:
            languages.append("hi")
    else:
        first = random.choice(FIRST_NAMES_OTHER)
        last = random.choice(LAST_NAMES_ML + ["Sharma", "Reddy", "Rao", "Singh"])
        languages = ["en", "hi"]
        if district_name == "Chennai":
            languages = ["ta", "en"]
        elif district_name == "Bengaluru":
            languages = ["kn", "en"]
    
    # Pick skill set weighted by probability
    skill_type = random.choices(
        list(SKILL_SETS.keys()),
        weights=[s["probability"] for s in SKILL_SETS.values()],
    )[0]
    skill_set = SKILL_SETS[skill_type]
    
    # Add some location jitter
    lat = district_info["lat"] + random.uniform(-0.05, 0.05)
    lon = district_info["lon"] + random.uniform(-0.05, 0.05)
    
    state_map = {
        "Alappuzha": "Kerala", "Ernakulam": "Kerala", "Thrissur": "Kerala",
        "Kottayam": "Kerala", "Pathanamthitta": "Kerala", "Idukki": "Kerala",
        "Chennai": "Tamil Nadu", "Bengaluru": "Karnataka",
    }
    
    return {
        "id": str(uuid.uuid4()),
        "name": f"{first} {last}",
        "phone": generate_phone(),
        "email": f"{first.lower()}.{last.lower()}@gmail.com" if random.random() < 0.3 else None,
        "location": {
            "city": district_name,
            "district": district_name,
            "state": state_map[district_name],
            "lat": round(lat, 4),
            "lon": round(lon, 4),
        },
        "skills": skill_set["normalized"],
        "skills_raw": skill_set["raw"],
        "languages": languages,
        "availability": {
            "days": random.choice([
                ["monday", "tuesday", "wednesday", "thursday", "friday"],
                ["saturday", "sunday"],
                ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            ]),
            "hours": random.choice(["9am-6pm", "24x7", "evenings only", "flexible"]),
        },
        "source": {
            "type": random.choice(["whatsapp", "pdf", "excel", "form"]),
            "file_name": f"volunteer_data_{district_name.lower()}.{'txt' if random.random() < 0.5 else 'xlsx'}",
            "confidence": round(random.uniform(0.7, 0.98), 2),
        },
    }


def generate_whatsapp_export(volunteers, group_name):
    """Generate a realistic WhatsApp export text from volunteer data."""
    lines = []
    base_date = "15/08/18"
    hour = 6
    
    for vol in volunteers:
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        
        # Some casual messages
        if random.random() < 0.3:
            lines.append(f"[{base_date}, {hour:02d}:{minute:02d}:{second:02d}] {vol['name']}: Good morning everyone 🙏")
        
        # Volunteer offer
        skills_text = ", ".join(vol["skills_raw"][:2])
        lines.append(
            f"[{base_date}, {hour:02d}:{minute:02d}:{second:02d}] "
            f"{vol['name']}: I can help with {skills_text}. "
            f"Contact me at +91{vol['phone']}"
        )
        
        if random.random() < 0.4:
            lines.append(
                f"[{base_date}, {hour:02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}] "
                f"{vol['name']}: I'm in {vol['location']['district']} area"
            )
        
        hour = min(hour + random.randint(0, 1), 23)
    
    return "\n".join(lines)


def main():
    all_volunteers = []
    whatsapp_exports = {}
    
    for district_name, district_info in DISTRICTS.items():
        count = district_info["count"]
        district_volunteers = [
            generate_volunteer(district_name, district_info)
            for _ in range(count)
        ]
        all_volunteers.extend(district_volunteers)
        
        # Generate WhatsApp exports for Kerala districts
        if district_name in ["Alappuzha", "Ernakulam"]:
            wa_text = generate_whatsapp_export(
                district_volunteers,
                f"Kerala Flood Relief - {district_name}"
            )
            whatsapp_exports[district_name] = wa_text
    
    # Save all volunteers as JSON
    with open("replay-data/volunteer-corpus/all-volunteers.json", "w") as f:
        json.dump(all_volunteers, f, indent=2, default=str)
    
    # Save WhatsApp exports
    for district, text in whatsapp_exports.items():
        filename = f"replay-data/volunteer-corpus/whatsapp-{district.lower()}.txt"
        with open(filename, "w") as f:
            f.write(text)
    
    print(f"Generated {len(all_volunteers)} volunteers across {len(DISTRICTS)} districts")
    print(f"Generated {len(whatsapp_exports)} WhatsApp export files")
    
    # Stats
    for district_name in DISTRICTS:
        count = len([v for v in all_volunteers if v["location"]["district"] == district_name])
        print(f"  {district_name}: {count} volunteers")


if __name__ == "__main__":
    main()
