"""
Seed Firestore with replay data for demos.
Loads volunteers and timeline from the replay-data directory.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).parent.parent)
sys.path.insert(0, PROJECT_ROOT)


def seed_volunteers():
    """Load volunteer corpus into Firestore."""
    from shared.firestore_client import create_volunteer
    from shared.embeddings import generate_embedding, build_volunteer_profile_text
    
    corpus_path = Path(PROJECT_ROOT) / "replay-data" / "volunteer-corpus" / "all-volunteers.json"
    
    if not corpus_path.exists():
        print("No volunteer corpus found. Run generate_demo_data.py first.")
        return
    
    with open(corpus_path) as f:
        volunteers = json.load(f)
    
    print(f"Seeding {len(volunteers)} volunteers into Firestore...")
    
    for i, vol in enumerate(volunteers):
        # Generate embedding
        profile_text = build_volunteer_profile_text(vol)
        vol["embedding"] = generate_embedding(profile_text)
        
        create_volunteer(vol)
        
        if (i + 1) % 20 == 0:
            print(f"  Seeded {i + 1}/{len(volunteers)}")
    
    print(f"✅ Done. {len(volunteers)} volunteers in Firestore.")


def seed_timeline():
    """Load timeline events (for reference, kept in JSON)."""
    timeline_path = Path(PROJECT_ROOT) / "replay-data" / "timeline.json"
    
    if not timeline_path.exists():
        print("No timeline found.")
        return
    
    with open(timeline_path) as f:
        timeline = json.load(f)
    
    print(f"Timeline loaded: {len(timeline['events'])} events")
    print(f"  Scenario: {timeline['scenario']}")
    print(f"  Start: {timeline['replay_start']}")
    print(f"  End: {timeline['replay_end']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed Firestore with demo data")
    parser.add_argument("--volunteers", action="store_true", help="Seed volunteer data")
    parser.add_argument("--timeline", action="store_true", help="Verify timeline data")
    parser.add_argument("--all", action="store_true", help="Seed everything")
    
    args = parser.parse_args()
    
    if args.all or args.volunteers:
        seed_volunteers()
    if args.all or args.timeline:
        seed_timeline()
    
    if not any([args.all, args.volunteers, args.timeline]):
        print("Usage: python seed_firestore.py --all")
        print("  --volunteers  Seed volunteer corpus")
        print("  --timeline    Verify timeline data")
        print("  --all         Seed everything")
