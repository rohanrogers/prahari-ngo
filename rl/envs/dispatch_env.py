"""
Prahari RL — Foundation Dispatch Environments (Stages 1–3).

Stage 1: Static world, single skill, perfect information
Stage 2: Dynamic arrivals via Poisson process
Stage 3: Multi-skill constraints with skill combination bonuses

The agent learns to dispatch volunteers to crisis missions,
optimizing lives reached per hour.
"""

import json
import os
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_json(filename: str) -> dict:
    with open(os.path.join(_DATA_DIR, filename), "r") as f:
        return json.load(f)


# Preload Kerala data
_DISTRICTS = _load_json("kerala_districts.json")
_SKILLS = _load_json("skill_distributions.json")

# Skill registry
SKILL_NAMES = [s["id"] for s in _SKILLS["skills"]]
SKILL_FREQUENCIES = [s["frequency"] for s in _SKILLS["skills"]]
NUM_SKILLS = len(SKILL_NAMES)

# District registry
DISTRICT_IDS = [d["id"] for d in _DISTRICTS["districts"]]
NUM_DISTRICTS = len(DISTRICT_IDS)


# ─────────────────────────────────────────────────────────────
# Stage 1: Static Dispatch — Single Skill, Perfect Information
# ─────────────────────────────────────────────────────────────

class DispatchEnvStage1(gym.Env):
    """
    Simplest dispatch environment.
    
    - Fixed volunteers (5) each with 1 skill, at known locations
    - Fixed missions (3) each requiring 1 skill, with known severity
    - Agent assigns one volunteer to one mission per step
    - Episode ends when all missions are served or steps exhausted
    
    State: [vol_available(5), vol_skill(5), mission_active(3), mission_skill(3), mission_severity(3)]
    Action: Discrete(5*3 + 1) — volunteer_id × mission_id + NO_OP
    Reward: severity_resolved × skill_match_bonus − time_penalty
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode: Optional[str] = None):
        super().__init__()

        self.render_mode = render_mode
        self.n_volunteers = 5
        self.n_missions = 3

        # Action: which volunteer (0..4) to send to which mission (0..2)
        # Plus NO_OP action (wait one step)
        self.action_space = spaces.Discrete(self.n_volunteers * self.n_missions + 1)

        # Observation: flat vector of volunteer + mission states
        # vol_available(5) + vol_skill_id(5) + vol_district(5) +
        # mission_active(3) + mission_skill_required(3) + mission_severity(3) + mission_district(3) +
        # time_remaining(1)
        obs_size = self.n_volunteers * 3 + self.n_missions * 4 + 1
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(obs_size,), dtype=np.float32
        )

        # Internal state
        self.volunteers = None
        self.missions = None
        self.current_step = 0
        self.max_steps = 200

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0

        # Generate volunteers: each has 1 skill, 1 district
        self.volunteers = []
        for i in range(self.n_volunteers):
            skill_idx = self.np_random.integers(0, NUM_SKILLS)
            district_idx = self.np_random.integers(0, NUM_DISTRICTS)
            self.volunteers.append({
                "available": True,
                "skill_idx": skill_idx,
                "district_idx": district_idx,
            })

        # Generate missions: each needs 1 skill, has severity, has location
        self.missions = []
        for i in range(self.n_missions):
            skill_idx = self.np_random.integers(0, NUM_SKILLS)
            district_idx = self.np_random.integers(0, NUM_DISTRICTS)
            severity = float(self.np_random.uniform(0.3, 1.0))
            self.missions.append({
                "active": True,
                "skill_required": skill_idx,
                "severity": severity,
                "district_idx": district_idx,
                "time_waiting": 0,
            })

        return self._get_obs(), {}

    def step(self, action):
        self.current_step += 1
        reward = 0.0
        terminated = False
        truncated = False

        # Increment waiting time for all active missions
        for m in self.missions:
            if m["active"]:
                m["time_waiting"] += 1

        if action < self.n_volunteers * self.n_missions:
            # Decode action: volunteer_id and mission_id
            vol_id = action // self.n_missions
            mis_id = action % self.n_missions

            vol = self.volunteers[vol_id]
            mis = self.missions[mis_id]

            if vol["available"] and mis["active"]:
                # Calculate skill match
                skill_match = 1.0 if vol["skill_idx"] == mis["skill_required"] else 0.3

                # Calculate distance penalty (same district = 0, different = penalty)
                if vol["district_idx"] == mis["district_idx"]:
                    distance_factor = 1.0
                else:
                    distance_factor = 0.6

                # Reward: severity × match × distance − waiting penalty
                reward = (
                    mis["severity"] * skill_match * distance_factor * 10.0
                    - mis["time_waiting"] * 0.1
                )

                # Mark volunteer as busy, mission as served
                vol["available"] = False
                mis["active"] = False
            else:
                # Invalid action: penalty
                reward = -1.0
        else:
            # NO_OP: small penalty for waiting (people are suffering)
            reward = -0.05 * sum(1 for m in self.missions if m["active"])

        # Check if all missions are served
        if all(not m["active"] for m in self.missions):
            terminated = True
            reward += 5.0  # Completion bonus

        # Check truncation
        truncated = self.current_step >= self.max_steps

        # Penalty for unserved missions at episode end
        if terminated or truncated:
            unserved = sum(1 for m in self.missions if m["active"])
            reward -= unserved * 3.0

        return self._get_obs(), float(reward), terminated, truncated, self._get_info()

    def _get_obs(self) -> np.ndarray:
        obs = []

        # Volunteer state
        for v in self.volunteers:
            obs.append(1.0 if v["available"] else 0.0)
            obs.append(v["skill_idx"] / NUM_SKILLS)
            obs.append(v["district_idx"] / NUM_DISTRICTS)

        # Mission state
        for m in self.missions:
            obs.append(1.0 if m["active"] else 0.0)
            obs.append(m["skill_required"] / NUM_SKILLS)
            obs.append(m["severity"])
            obs.append(m["district_idx"] / NUM_DISTRICTS)

        # Time remaining
        obs.append(1.0 - self.current_step / self.max_steps)

        return np.array(obs, dtype=np.float32)

    def _get_info(self) -> dict:
        served = sum(1 for m in self.missions if not m["active"])
        total_severity = sum(m["severity"] for m in self.missions)
        served_severity = sum(
            m["severity"] for m in self.missions if not m["active"]
        )
        return {
            "missions_served": served,
            "missions_total": self.n_missions,
            "severity_served": served_severity,
            "severity_total": total_severity,
            "steps_taken": self.current_step,
            "service_rate": served / self.n_missions if self.n_missions > 0 else 0,
        }


# ─────────────────────────────────────────────────────────────
# Stage 2: Dynamic Arrivals — Poisson Process
# ─────────────────────────────────────────────────────────────

class DispatchEnvStage2(gym.Env):
    """
    Adds dynamic mission arrivals over time.
    
    - Volunteers start available (8 total)
    - Missions arrive stochastically (Poisson, λ=0.3 per step)
    - Agent must decide: dispatch now or wait for better match
    - Missions expire after 20 steps (lives lost)
    - Dispatched volunteers return after 5 steps
    
    Key learning: the value of WAITING for a better match vs acting NOW.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode: Optional[str] = None):
        super().__init__()

        self.render_mode = render_mode
        self.n_volunteers = 8
        self.max_active_missions = 6
        self.mission_expire_steps = 20
        self.volunteer_return_steps = 5
        self.arrival_rate = 0.3  # Poisson λ

        # Action: vol(0..7) × mission(0..5) + NO_OP
        self.action_space = spaces.Discrete(
            self.n_volunteers * self.max_active_missions + 1
        )

        # Observation: vol states + mission states + global time
        obs_size = (
            self.n_volunteers * 4  # available, skill, district, cooldown
            + self.max_active_missions * 5  # active, skill, severity, district, time_waiting
            + 1  # time_remaining
        )
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(obs_size,), dtype=np.float32
        )

        self.volunteers = None
        self.missions = None
        self.current_step = 0
        self.max_steps = 200
        self.total_missions_generated = 0
        self.total_missions_served = 0
        self.total_missions_expired = 0
        self.total_severity_served = 0.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.total_missions_generated = 0
        self.total_missions_served = 0
        self.total_missions_expired = 0
        self.total_severity_served = 0.0

        # Initialize volunteers
        self.volunteers = []
        for i in range(self.n_volunteers):
            skill_idx = self.np_random.integers(0, NUM_SKILLS)
            district_idx = self.np_random.integers(0, NUM_DISTRICTS)
            self.volunteers.append({
                "available": True,
                "skill_idx": skill_idx,
                "district_idx": district_idx,
                "cooldown": 0,
            })

        # Start with 1–2 initial missions
        self.missions = []
        n_initial = self.np_random.integers(1, 3)
        for _ in range(n_initial):
            self._spawn_mission()

        # Pad to fixed size so observation shape is consistent
        while len(self.missions) < self.max_active_missions:
            self.missions.append({
                "active": False,
                "skill_required": 0,
                "severity": 0.0,
                "district_idx": 0,
                "time_waiting": 0,
            })

        return self._get_obs(), {}

    def _spawn_mission(self):
        if len(self.missions) >= self.max_active_missions:
            return
        skill_idx = self.np_random.integers(0, NUM_SKILLS)
        district_idx = self.np_random.integers(0, NUM_DISTRICTS)
        severity = float(self.np_random.uniform(0.2, 1.0))
        self.missions.append({
            "active": True,
            "skill_required": skill_idx,
            "severity": severity,
            "district_idx": district_idx,
            "time_waiting": 0,
        })
        self.total_missions_generated += 1

    def step(self, action):
        self.current_step += 1
        reward = 0.0

        # 1. Update volunteer cooldowns
        for v in self.volunteers:
            if v["cooldown"] > 0:
                v["cooldown"] -= 1
                if v["cooldown"] == 0:
                    v["available"] = True

        # 2. Update mission wait times, expire old missions
        expired_this_step = []
        for i, m in enumerate(self.missions):
            if m["active"]:
                m["time_waiting"] += 1
                if m["time_waiting"] >= self.mission_expire_steps:
                    m["active"] = False
                    self.total_missions_expired += 1
                    expired_this_step.append(i)
                    reward -= m["severity"] * 5.0  # Heavy penalty for expired missions

        # 3. Process action
        if action < self.n_volunteers * self.max_active_missions:
            vol_id = action // self.max_active_missions
            mis_id = action % self.max_active_missions

            if (
                vol_id < len(self.volunteers)
                and mis_id < len(self.missions)
                and self.volunteers[vol_id]["available"]
                and self.missions[mis_id]["active"]
            ):
                vol = self.volunteers[vol_id]
                mis = self.missions[mis_id]

                # Skill match
                skill_match = 1.0 if vol["skill_idx"] == mis["skill_required"] else 0.3

                # Distance factor
                dist_match = 1.0 if vol["district_idx"] == mis["district_idx"] else 0.5

                # Response time bonus (faster = better)
                speed_bonus = max(0, 1.0 - mis["time_waiting"] / self.mission_expire_steps)

                reward = mis["severity"] * skill_match * dist_match * speed_bonus * 10.0

                # Update states
                vol["available"] = False
                vol["cooldown"] = self.volunteer_return_steps
                mis["active"] = False
                self.total_missions_served += 1
                self.total_severity_served += mis["severity"]
            else:
                reward = -0.5  # Invalid action
        else:
            # NO_OP: small ongoing penalty per active mission
            active_count = sum(1 for m in self.missions if m["active"])
            reward = -0.02 * active_count

        # 4. Spawn new missions (Poisson arrivals)
        n_new = self.np_random.poisson(self.arrival_rate)
        for _ in range(n_new):
            self._spawn_mission()

        # 5. Clean up served/expired missions (keep slots available)
        self.missions = [m for m in self.missions if m["active"]]

        # Pad missions list to max_active_missions
        while len(self.missions) < self.max_active_missions:
            self.missions.append({
                "active": False,
                "skill_required": 0,
                "severity": 0.0,
                "district_idx": 0,
                "time_waiting": 0,
            })

        truncated = self.current_step >= self.max_steps
        terminated = False

        # End-of-episode stats
        if truncated:
            if self.total_missions_generated > 0:
                service_rate = self.total_missions_served / self.total_missions_generated
                reward += service_rate * 10.0  # Bonus for high service rate

        return self._get_obs(), float(reward), terminated, truncated, self._get_info()

    def _get_obs(self) -> np.ndarray:
        obs = []

        for v in self.volunteers:
            obs.append(1.0 if v["available"] else 0.0)
            obs.append(v["skill_idx"] / NUM_SKILLS)
            obs.append(v["district_idx"] / NUM_DISTRICTS)
            obs.append(v["cooldown"] / self.volunteer_return_steps if v["cooldown"] > 0 else 0.0)

        for m in self.missions:
            obs.append(1.0 if m["active"] else 0.0)
            obs.append(m["skill_required"] / NUM_SKILLS)
            obs.append(m["severity"])
            obs.append(m["district_idx"] / NUM_DISTRICTS)
            obs.append(m["time_waiting"] / self.mission_expire_steps if m["active"] else 0.0)

        obs.append(1.0 - self.current_step / self.max_steps)

        return np.array(obs, dtype=np.float32)

    def _get_info(self) -> dict:
        return {
            "missions_served": self.total_missions_served,
            "missions_expired": self.total_missions_expired,
            "missions_generated": self.total_missions_generated,
            "severity_served": self.total_severity_served,
            "service_rate": (
                self.total_missions_served / max(1, self.total_missions_generated)
            ),
            "lives_reached_per_hour": (
                self.total_missions_served / max(1, self.current_step) * 30
            ),
        }


# ─────────────────────────────────────────────────────────────
# Stage 3: Multi-Skill Constraints — Skill Combinations Matter
# ─────────────────────────────────────────────────────────────

class DispatchEnvStage3(gym.Env):
    """
    Adds multi-skill requirements for missions.
    
    - Volunteers have 1–3 skills each
    - Missions require specific skill COMBINATIONS (e.g., water_rescue needs boat_op + swimming)
    - Partial matches get partial reward; full matches get bonus
    - Multiple volunteers can be assigned to the same mission
    - The agent learns skill synergies
    
    Key learning: A medic and a boat operator are both needed for water rescue.
    Sending them separately to different missions is suboptimal.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode: Optional[str] = None):
        super().__init__()

        self.render_mode = render_mode
        self.n_volunteers = 10
        self.max_active_missions = 6
        self.mission_expire_steps = 25
        self.volunteer_return_steps = 6
        self.arrival_rate = 0.35

        # Load mission type definitions
        self.mission_types = _SKILLS["mission_types"]
        self.mission_type_keys = list(self.mission_types.keys())

        # Action: vol(0..9) × mission(0..5) + NO_OP
        self.action_space = spaces.Discrete(
            self.n_volunteers * self.max_active_missions + 1
        )

        # Observation: vol states + mission states + mission skill coverage + time
        # vol: available, skills(10), district, cooldown = 13 per vol
        # mission: active, required_skills(10), severity, district, time_waiting, coverage(1) = 14 per mission
        obs_size = self.n_volunteers * (2 + NUM_SKILLS + 1) + self.max_active_missions * (3 + NUM_SKILLS + 1 + 1) + 1
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(obs_size,), dtype=np.float32
        )

        self.volunteers = None
        self.missions = None
        self.current_step = 0
        self.max_steps = 200
        self.total_missions_generated = 0
        self.total_missions_served = 0
        self.total_missions_expired = 0
        self.total_severity_served = 0.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.total_missions_generated = 0
        self.total_missions_served = 0
        self.total_missions_expired = 0
        self.total_severity_served = 0.0

        # Generate volunteers with 1–3 skills
        self.volunteers = []
        for i in range(self.n_volunteers):
            n_skills = self.np_random.integers(1, 4)  # 1, 2, or 3 skills
            # Weight skill selection by frequency
            probs = np.array(SKILL_FREQUENCIES, dtype=np.float64)
            probs /= probs.sum()
            skill_indices = self.np_random.choice(
                NUM_SKILLS, size=min(n_skills, NUM_SKILLS), replace=False, p=probs
            )
            skills = np.zeros(NUM_SKILLS, dtype=np.float32)
            for idx in skill_indices:
                skills[idx] = 1.0

            district_idx = self.np_random.integers(0, NUM_DISTRICTS)
            self.volunteers.append({
                "available": True,
                "skills": skills,
                "district_idx": district_idx,
                "cooldown": 0,
            })

        # Spawn initial missions
        self.missions = []
        for _ in range(self.np_random.integers(1, 3)):
            self._spawn_mission()

        # Pad to max
        while len(self.missions) < self.max_active_missions:
            self.missions.append(self._empty_mission())

        return self._get_obs(), {}

    def _empty_mission(self):
        return {
            "active": False,
            "mission_type": "",
            "required_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
            "optional_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
            "severity": 0.0,
            "district_idx": 0,
            "time_waiting": 0,
            "assigned_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
            "min_volunteers": 0,
            "assigned_count": 0,
        }

    def _spawn_mission(self):
        if sum(1 for m in self.missions if m["active"]) >= self.max_active_missions:
            return

        # Pick a random mission type
        mt_key = self.np_random.choice(self.mission_type_keys)
        mt = self.mission_types[mt_key]

        required = np.zeros(NUM_SKILLS, dtype=np.float32)
        for skill_name in mt["required_skills"]:
            if skill_name in SKILL_NAMES:
                required[SKILL_NAMES.index(skill_name)] = 1.0

        optional = np.zeros(NUM_SKILLS, dtype=np.float32)
        for skill_name in mt.get("optional_skills", []):
            if skill_name in SKILL_NAMES:
                optional[SKILL_NAMES.index(skill_name)] = 1.0

        severity = float(self.np_random.uniform(*mt["severity_range"]))
        district_idx = self.np_random.integers(0, NUM_DISTRICTS)

        mission = {
            "active": True,
            "mission_type": mt_key,
            "required_skills": required,
            "optional_skills": optional,
            "severity": severity,
            "district_idx": district_idx,
            "time_waiting": 0,
            "assigned_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
            "min_volunteers": mt["min_volunteers"],
            "assigned_count": 0,
        }

        # Replace an inactive slot
        for i, m in enumerate(self.missions):
            if not m["active"]:
                self.missions[i] = mission
                self.total_missions_generated += 1
                return

    def step(self, action):
        self.current_step += 1
        reward = 0.0

        # 1. Update cooldowns
        for v in self.volunteers:
            if v["cooldown"] > 0:
                v["cooldown"] -= 1
                if v["cooldown"] == 0:
                    v["available"] = True

        # 2. Update missions
        for m in self.missions:
            if m["active"]:
                m["time_waiting"] += 1

                # Check if mission is fully staffed → mark served
                coverage = self._compute_coverage(m)
                if coverage >= 1.0 and m["assigned_count"] >= m["min_volunteers"]:
                    m["active"] = False
                    self.total_missions_served += 1
                    self.total_severity_served += m["severity"]
                    speed_bonus = max(0, 1.0 - m["time_waiting"] / self.mission_expire_steps)
                    reward += m["severity"] * coverage * speed_bonus * 15.0

                # Check expiry
                elif m["time_waiting"] >= self.mission_expire_steps:
                    m["active"] = False
                    self.total_missions_expired += 1
                    reward -= m["severity"] * 5.0

        # 3. Process action
        if action < self.n_volunteers * self.max_active_missions:
            vol_id = action // self.max_active_missions
            mis_id = action % self.max_active_missions

            if (
                vol_id < len(self.volunteers)
                and mis_id < len(self.missions)
                and self.volunteers[vol_id]["available"]
                and self.missions[mis_id]["active"]
            ):
                vol = self.volunteers[vol_id]
                mis = self.missions[mis_id]

                # Check if this volunteer adds value (has needed skills)
                old_coverage = self._compute_coverage(mis)
                mis["assigned_skills"] = np.maximum(
                    mis["assigned_skills"], vol["skills"]
                )
                mis["assigned_count"] += 1
                new_coverage = self._compute_coverage(mis)

                # Immediate reward for improving coverage
                coverage_delta = new_coverage - old_coverage
                if coverage_delta > 0:
                    reward += coverage_delta * mis["severity"] * 5.0
                else:
                    # Redundant assignment — slight penalty
                    reward -= 0.3

                # Distance factor
                if vol["district_idx"] != mis["district_idx"]:
                    reward -= 0.5

                vol["available"] = False
                vol["cooldown"] = self.volunteer_return_steps
            else:
                reward -= 0.5
        else:
            # NO_OP
            active_count = sum(1 for m in self.missions if m["active"])
            reward -= 0.02 * active_count

        # 4. New arrivals
        n_new = self.np_random.poisson(self.arrival_rate)
        for _ in range(n_new):
            self._spawn_mission()

        truncated = self.current_step >= self.max_steps
        terminated = False

        if truncated:
            if self.total_missions_generated > 0:
                service_rate = self.total_missions_served / self.total_missions_generated
                reward += service_rate * 10.0

        return self._get_obs(), float(reward), terminated, truncated, self._get_info()

    def _compute_coverage(self, mission: dict) -> float:
        """Compute how well the assigned skills cover the required skills."""
        required = mission["required_skills"]
        assigned = mission["assigned_skills"]
        optional = mission["optional_skills"]

        req_count = required.sum()
        if req_count == 0:
            return 1.0

        # Required coverage (what % of required skills are covered)
        req_covered = np.minimum(required, assigned).sum()
        req_ratio = req_covered / req_count

        # Optional bonus (up to 20% extra)
        opt_count = optional.sum()
        if opt_count > 0:
            opt_covered = np.minimum(optional, assigned).sum()
            opt_bonus = 0.2 * (opt_covered / opt_count)
        else:
            opt_bonus = 0.0

        return min(1.0, req_ratio + opt_bonus)

    def _get_obs(self) -> np.ndarray:
        obs = []

        for v in self.volunteers:
            obs.append(1.0 if v["available"] else 0.0)
            obs.extend(v["skills"].tolist())
            obs.append(v["district_idx"] / NUM_DISTRICTS)
            obs.append(v["cooldown"] / self.volunteer_return_steps if v["cooldown"] > 0 else 0.0)

        for m in self.missions:
            obs.append(1.0 if m["active"] else 0.0)
            obs.extend(m["required_skills"].tolist())
            obs.append(m["severity"])
            obs.append(m["district_idx"] / NUM_DISTRICTS)
            obs.append(m["time_waiting"] / self.mission_expire_steps if m["active"] else 0.0)
            obs.append(self._compute_coverage(m) if m["active"] else 0.0)

        obs.append(1.0 - self.current_step / self.max_steps)

        return np.array(obs, dtype=np.float32)

    def _get_info(self) -> dict:
        return {
            "missions_served": self.total_missions_served,
            "missions_expired": self.total_missions_expired,
            "missions_generated": self.total_missions_generated,
            "severity_served": self.total_severity_served,
            "service_rate": (
                self.total_missions_served / max(1, self.total_missions_generated)
            ),
            "lives_reached_per_hour": (
                self.total_missions_served / max(1, self.current_step) * 30
            ),
        }
