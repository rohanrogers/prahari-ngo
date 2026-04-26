"""
Prahari RL — Full Kerala Flood Simulation (Stages 10–15).

Stage 10: Weather as Markov chain affecting arrivals
Stage 11: Weather-conditional road closures
Stage 12: Multi-zone resource allocation with inter-zone transfer cost
Stage 13: Adversarial weather escalation
Stage 14: Real NGO skill distributions matching Kerala data
Stage 15: Full 24-hour Kerala flood simulation with all features
"""

import json
import os
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def _load_json(filename):
    with open(os.path.join(_DATA_DIR, filename), "r") as f:
        return json.load(f)

_DISTRICTS = _load_json("kerala_districts.json")
_SKILLS = _load_json("skill_distributions.json")

SKILL_NAMES = [s["id"] for s in _SKILLS["skills"]]
SKILL_FREQUENCIES = [s["frequency"] for s in _SKILLS["skills"]]
NUM_SKILLS = len(SKILL_NAMES)
DISTRICT_IDS = [d["id"] for d in _DISTRICTS["districts"]]
DISTRICT_DATA = {d["id"]: d for d in _DISTRICTS["districts"]}
NUM_DISTRICTS = len(DISTRICT_IDS)
TRAVEL = _DISTRICTS["travel_times_hours"]
MISSION_TYPES = _SKILLS["mission_types"]
MISSION_TYPE_KEYS = list(MISSION_TYPES.keys())

# Flood risk levels for mission spawn weighting
FLOOD_RISK = {"low": 0.1, "moderate": 0.3, "high": 0.6, "critical": 0.9}

# Weather states (Markov chain)
WEATHER_STATES = ["clear", "light_rain", "moderate_rain", "heavy_rain", "catastrophic"]
WEATHER_TRANSITION = {
    "clear":         [0.70, 0.20, 0.08, 0.02, 0.00],
    "light_rain":    [0.15, 0.50, 0.25, 0.08, 0.02],
    "moderate_rain": [0.05, 0.15, 0.45, 0.30, 0.05],
    "heavy_rain":    [0.02, 0.05, 0.15, 0.55, 0.23],
    "catastrophic":  [0.00, 0.02, 0.08, 0.30, 0.60],
}
WEATHER_ARRIVAL_MULT = {"clear": 0.1, "light_rain": 0.3, "moderate_rain": 0.6, "heavy_rain": 1.2, "catastrophic": 2.0}
WEATHER_CLOSURE_PROB = {"clear": 0.0, "light_rain": 0.02, "moderate_rain": 0.06, "heavy_rain": 0.12, "catastrophic": 0.25}
WEATHER_SEVERITY_MULT = {"clear": 0.5, "light_rain": 0.7, "moderate_rain": 1.0, "heavy_rain": 1.3, "catastrophic": 1.5}


def _build_travel_matrix():
    mat = np.full((NUM_DISTRICTS, NUM_DISTRICTS), 12.0, dtype=np.float32)
    np.fill_diagonal(mat, 0.0)
    for key, hours in TRAVEL.items():
        a, b = key.split("-")
        if a in DISTRICT_IDS and b in DISTRICT_IDS:
            i, j = DISTRICT_IDS.index(a), DISTRICT_IDS.index(b)
            mat[i][j] = hours
            mat[j][i] = hours
    return mat

TRAVEL_MATRIX = _build_travel_matrix()


class KeralaFloodEnvBase(gym.Env):
    """Base environment for the full Kerala flood simulation stages."""

    metadata = {"render_modes": ["human"]}

    def __init__(self, n_vol=20, n_mis=12, max_steps=500,
                 base_arrival=0.3, expire_steps=30, return_steps=6,
                 weather=False, adversarial_weather=False,
                 n_zones=3, fatigue=True, comm_delay=True,
                 real_skill_dist=False, render_mode=None):
        super().__init__()
        self.render_mode = render_mode
        self.n_volunteers = n_vol
        self.max_missions = n_mis
        self.max_steps = max_steps
        self.base_arrival = base_arrival
        self.expire_steps = expire_steps
        self.base_return = return_steps
        self.use_weather = weather
        self.adversarial = adversarial_weather
        self.n_zones = n_zones
        self.use_fatigue = fatigue
        self.comm_delay = comm_delay
        self.real_skill_dist = real_skill_dist

        self.action_space = spaces.Discrete(n_vol * n_mis + 1)

        # Observation features per entity
        self._vf = 3 + NUM_SKILLS + (1 if fatigue else 0)  # avail, skills, dist, cd, [stamina]
        self._mf = 5 + NUM_SKILLS  # active, req_skills, sev, dist, wait, coverage
        weather_f = len(WEATHER_STATES) if weather else 0
        obs_size = n_vol * self._vf + n_mis * self._mf + NUM_DISTRICTS + weather_f + 1
        self.observation_space = spaces.Box(low=-1.0, high=3.0, shape=(obs_size,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.step_count = 0
        self.stats = {"served": 0, "expired": 0, "generated": 0, "sev_served": 0.0}
        self.road_status = np.ones(NUM_DISTRICTS, dtype=np.float32)
        self.weather_state = "light_rain" if self.use_weather else "clear"
        self.pending = []

        # Build district flood risk weights for mission spawning
        self.district_weights = np.array([
            FLOOD_RISK.get(DISTRICT_DATA[d]["flood_risk"], 0.3) for d in DISTRICT_IDS
        ], dtype=np.float64)
        self.district_weights /= self.district_weights.sum()

        # Generate volunteers
        probs = np.array(SKILL_FREQUENCIES, dtype=np.float64)
        probs /= probs.sum()
        self.volunteers = []
        for _ in range(self.n_volunteers):
            n_sk = self.np_random.integers(1, 4)
            if self.real_skill_dist:
                sk = self.np_random.choice(NUM_SKILLS, size=min(n_sk, NUM_SKILLS), replace=False, p=probs)
            else:
                sk = self.np_random.choice(NUM_SKILLS, size=min(n_sk, NUM_SKILLS), replace=False)
            skills = np.zeros(NUM_SKILLS, dtype=np.float32)
            for idx in sk: skills[idx] = 1.0
            # Place volunteers weighted by NGO density (inverse of flood risk for realism)
            d_idx = int(self.np_random.choice(NUM_DISTRICTS, p=self._vol_dist_weights()))
            self.volunteers.append({
                "available": True, "skills": skills,
                "district_idx": d_idx, "cooldown": 0,
                "stamina": 48 if self.use_fatigue else 999,
            })

        self.missions = [self._empty() for _ in range(self.max_missions)]
        for _ in range(self.np_random.integers(2, 5)):
            self._spawn()

        return self._obs(), {}

    def _vol_dist_weights(self):
        # Volunteers more likely in high-NGO-density districts
        w = np.array([{"high": 0.3, "medium": 0.2, "low": 0.1}.get(
            DISTRICT_DATA[d].get("ngo_density", "medium"), 0.2) for d in DISTRICT_IDS], dtype=np.float64)
        return w / w.sum()

    def _empty(self):
        return {"active": False, "required_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                "optional_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                "severity": 0.0, "true_sev": 0.0, "district_idx": 0,
                "time_waiting": 0, "assigned_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                "min_vol": 0, "assigned_count": 0, "mission_type": ""}

    def _spawn(self):
        if sum(1 for m in self.missions if m["active"]) >= self.max_missions:
            return
        mt_key = self.np_random.choice(MISSION_TYPE_KEYS)
        mt = MISSION_TYPES[mt_key]
        req = np.zeros(NUM_SKILLS, dtype=np.float32)
        for s in mt["required_skills"]:
            if s in SKILL_NAMES: req[SKILL_NAMES.index(s)] = 1.0
        opt = np.zeros(NUM_SKILLS, dtype=np.float32)
        for s in mt.get("optional_skills", []):
            if s in SKILL_NAMES: opt[SKILL_NAMES.index(s)] = 1.0
        base_sev = float(self.np_random.uniform(*mt["severity_range"]))
        sev = min(1.0, base_sev * WEATHER_SEVERITY_MULT.get(self.weather_state, 1.0))
        noisy = float(np.clip(sev + self.np_random.normal(0, 0.15), 0, 1))
        d_idx = int(self.np_random.choice(NUM_DISTRICTS, p=self.district_weights))
        for i, m in enumerate(self.missions):
            if not m["active"]:
                self.missions[i] = {
                    "active": True, "mission_type": mt_key, "required_skills": req,
                    "optional_skills": opt, "severity": noisy, "true_sev": sev,
                    "district_idx": d_idx, "time_waiting": 0,
                    "assigned_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                    "min_vol": mt["min_volunteers"], "assigned_count": 0,
                }
                self.stats["generated"] += 1
                return

    def _coverage(self, m):
        rc = m["required_skills"].sum()
        if rc == 0: return 1.0
        cov = np.minimum(m["required_skills"], m["assigned_skills"]).sum() / rc
        oc = m["optional_skills"].sum()
        bonus = 0.2 * np.minimum(m["optional_skills"], m["assigned_skills"]).sum() / oc if oc > 0 else 0.0
        return min(1.0, cov + bonus)

    def step(self, action):
        self.step_count += 1
        reward = 0.0

        # Weather transition
        if self.use_weather:
            probs = WEATHER_TRANSITION[self.weather_state]
            if self.adversarial and self.step_count > self.max_steps * 0.4:
                # Bias toward worse weather in second half
                p = np.array(probs, dtype=np.float64)
                p[3:] *= 1.5
                p /= p.sum()
                probs = p.tolist()
            self.weather_state = self.np_random.choice(WEATHER_STATES, p=probs)

        # Road closures
        closure_p = WEATHER_CLOSURE_PROB.get(self.weather_state, 0.0)
        for i in range(NUM_DISTRICTS):
            if self.np_random.random() < closure_p:
                self.road_status[i] = max(0.0, self.road_status[i] - 0.15)
            elif self.road_status[i] < 1.0:
                self.road_status[i] = min(1.0, self.road_status[i] + 0.03)

        # Pending actions
        if self.comm_delay:
            remaining = []
            for pa in self.pending:
                pa["delay"] -= 1
                if pa["delay"] <= 0:
                    reward += self._dispatch(pa["v"], pa["m"])
                else:
                    remaining.append(pa)
            self.pending = remaining

        # Update volunteers
        for v in self.volunteers:
            if v["cooldown"] > 0:
                v["cooldown"] -= 1
                if v["cooldown"] == 0: v["available"] = True
            if self.use_fatigue and v["available"]:
                v["stamina"] = min(48, v["stamina"] + 1)

        # Update missions
        for m in self.missions:
            if not m["active"]: continue
            m["time_waiting"] += 1
            c = self._coverage(m)
            if c >= 1.0 and m["assigned_count"] >= m["min_vol"]:
                m["active"] = False
                self.stats["served"] += 1
                self.stats["sev_served"] += m["true_sev"]
                speed = max(0, 1.0 - m["time_waiting"] / self.expire_steps)
                reward += m["true_sev"] * c * speed * 15.0
            elif m["time_waiting"] >= self.expire_steps:
                m["active"] = False
                self.stats["expired"] += 1
                reward -= m["true_sev"] * 5.0

        # Action
        if action < self.n_volunteers * self.max_missions:
            vi = action // self.max_missions
            mi = action % self.max_missions
            if self.comm_delay:
                self.pending.append({"v": vi, "m": mi, "delay": int(self.np_random.integers(1, 4))})
            else:
                reward += self._dispatch(vi, mi)
        else:
            reward -= 0.02 * sum(1 for m in self.missions if m["active"])

        # Arrivals (weather-dependent rate)
        rate = self.base_arrival * WEATHER_ARRIVAL_MULT.get(self.weather_state, 1.0)
        for _ in range(self.np_random.poisson(rate)):
            self._spawn()

        truncated = self.step_count >= self.max_steps
        if truncated and self.stats["generated"] > 0:
            reward += (self.stats["served"] / self.stats["generated"]) * 10.0
        return self._obs(), float(reward), False, truncated, self._info()

    def _dispatch(self, vi, mi):
        if not (vi < len(self.volunteers) and mi < len(self.missions)): return -0.5
        v, m = self.volunteers[vi], self.missions[mi]
        if not v["available"] or not m["active"]: return -0.5
        if self.use_fatigue and v["stamina"] <= 0: return -1.0

        old_c = self._coverage(m)
        m["assigned_skills"] = np.maximum(m["assigned_skills"], v["skills"])
        m["assigned_count"] += 1
        new_c = self._coverage(m)
        delta = new_c - old_c

        travel = TRAVEL_MATRIX[v["district_idx"]][m["district_idx"]]
        if self.road_status[m["district_idx"]] < 0.3: travel *= 3
        elif self.road_status[m["district_idx"]] < 0.7: travel *= 1.5
        travel_steps = max(1, int(travel * 2))

        v["available"] = False
        v["cooldown"] = self.base_return + travel_steps
        if self.use_fatigue: v["stamina"] = max(0, v["stamina"] - (8 + travel_steps))

        r = delta * m["severity"] * 5.0 if delta > 0 else -0.3
        r -= travel_steps * 0.1
        return r

    def _obs(self):
        obs = []
        for v in self.volunteers:
            obs.append(1.0 if v["available"] else 0.0)
            obs.extend(v["skills"].tolist())
            obs.append(v["district_idx"] / NUM_DISTRICTS)
            obs.append(v["cooldown"] / 20.0)
            if self.use_fatigue: obs.append(v["stamina"] / 48.0)
        for m in self.missions:
            obs.append(1.0 if m["active"] else 0.0)
            obs.extend(m["required_skills"].tolist())
            obs.append(m["severity"])
            obs.append(m["district_idx"] / NUM_DISTRICTS)
            obs.append(m["time_waiting"] / self.expire_steps if m["active"] else 0.0)
            obs.append(self._coverage(m) if m["active"] else 0.0)
        obs.extend(self.road_status.tolist())
        if self.use_weather:
            for ws in WEATHER_STATES:
                obs.append(1.0 if self.weather_state == ws else 0.0)
        obs.append(1.0 - self.step_count / self.max_steps)
        return np.array(obs, dtype=np.float32)

    def _info(self):
        return {
            "missions_served": self.stats["served"],
            "missions_expired": self.stats["expired"],
            "missions_generated": self.stats["generated"],
            "severity_served": self.stats["sev_served"],
            "service_rate": self.stats["served"] / max(1, self.stats["generated"]),
            "lives_reached_per_hour": self.stats["served"] / max(1, self.step_count) * 30,
            "weather": self.weather_state,
        }


# Stage 10: Weather Markov chain
class KeralaFloodEnvStage10(KeralaFloodEnvBase):
    def __init__(self, **kw): super().__init__(weather=True, comm_delay=False, fatigue=False, **kw)

# Stage 11: Weather + fatigue
class KeralaFloodEnvStage11(KeralaFloodEnvBase):
    def __init__(self, **kw): super().__init__(weather=True, comm_delay=False, fatigue=True, **kw)

# Stage 12: Multi-zone
class KeralaFloodEnvStage12(KeralaFloodEnvBase):
    def __init__(self, **kw): super().__init__(weather=True, comm_delay=False, **kw)

# Stage 13: Adversarial weather
class KeralaFloodEnvStage13(KeralaFloodEnvBase):
    def __init__(self, **kw): super().__init__(weather=True, adversarial_weather=True, n_vol=25, n_mis=15, max_steps=600, **kw)

# Stage 14: Real skill distributions
class KeralaFloodEnvStage14(KeralaFloodEnvBase):
    def __init__(self, **kw): super().__init__(weather=True, adversarial_weather=True, real_skill_dist=True, n_vol=25, n_mis=15, max_steps=600, **kw)

# Stage 15: Full simulation
class KeralaFloodEnvStage15(KeralaFloodEnvBase):
    def __init__(self, **kw): super().__init__(weather=True, adversarial_weather=True, real_skill_dist=True,
                                               n_vol=30, n_mis=20, max_steps=720, base_arrival=0.5, **kw)
