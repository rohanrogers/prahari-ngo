"""
Prahari RL — Advanced Dispatch Environments (Stages 4–9).

Stage 4: Real Kerala district graph with travel times
Stage 5: Stochastic road closures
Stage 6: Partial observability (noisy severity estimates)
Stage 7: Multiple simultaneous disaster zones
Stage 8: Volunteer fatigue modeling (8-hour shifts)
Stage 9: Communication delays (actions take 1–3 steps)
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
NUM_DISTRICTS = len(DISTRICT_IDS)

# Build adjacency and travel time matrices
_ADJ = _DISTRICTS["adjacency"]
_TRAVEL = _DISTRICTS["travel_times_hours"]

def _build_travel_matrix():
    """Build NxN travel time matrix from district data."""
    mat = np.full((NUM_DISTRICTS, NUM_DISTRICTS), 12.0, dtype=np.float32)
    np.fill_diagonal(mat, 0.0)
    for key, hours in _TRAVEL.items():
        a, b = key.split("-")
        if a in DISTRICT_IDS and b in DISTRICT_IDS:
            i, j = DISTRICT_IDS.index(a), DISTRICT_IDS.index(b)
            mat[i][j] = hours
            mat[j][i] = hours
    return mat

TRAVEL_MATRIX = _build_travel_matrix()
MISSION_TYPES = _SKILLS["mission_types"]
MISSION_TYPE_KEYS = list(MISSION_TYPES.keys())


class _BaseAdvancedEnv(gym.Env):
    """Shared logic for Stages 4–9."""

    metadata = {"render_modes": ["human"]}

    def __init__(self, n_vol=12, n_mis=8, max_steps=300,
                 arrival_rate=0.35, expire_steps=25, return_steps=6,
                 use_roads=False, road_closure_prob=0.0,
                 partial_obs=False, noise_std=0.0,
                 multi_zone=False, n_zones=1,
                 fatigue=False, max_stamina=48,
                 comm_delay=False, render_mode=None):
        super().__init__()
        self.render_mode = render_mode
        self.n_volunteers = n_vol
        self.max_active_missions = n_mis
        self.max_steps = max_steps
        self.arrival_rate = arrival_rate
        self.mission_expire_steps = expire_steps
        self.base_return_steps = return_steps
        self.use_roads = use_roads
        self.road_closure_prob = road_closure_prob
        self.partial_obs = partial_obs
        self.noise_std = noise_std
        self.multi_zone = multi_zone
        self.n_zones = n_zones
        self.use_fatigue = fatigue
        self.max_stamina = max_stamina
        self.comm_delay = comm_delay

        self.action_space = spaces.Discrete(n_vol * n_mis + 1)

        # Obs: vol(avail + skills(10) + district + cooldown + stamina) = 14
        #    + mis(active + req_skills(10) + sev + district + wait + coverage + zone) = 15
        #    + road_status(14) + time
        vol_feat = 3 + NUM_SKILLS + (1 if fatigue else 0)
        mis_feat = 4 + NUM_SKILLS + 1 + (1 if multi_zone else 0)
        road_feat = NUM_DISTRICTS if use_roads else 0
        obs_size = n_vol * vol_feat + n_mis * mis_feat + road_feat + 1
        self.observation_space = spaces.Box(low=-1.0, high=2.0, shape=(obs_size,), dtype=np.float32)

        self._vol_feat = vol_feat
        self._mis_feat = mis_feat
        self._road_feat = road_feat

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.stats = {"served": 0, "expired": 0, "generated": 0, "severity_served": 0.0}
        self.road_status = np.ones(NUM_DISTRICTS, dtype=np.float32)
        self.pending_actions = []

        probs = np.array(SKILL_FREQUENCIES, dtype=np.float64)
        probs /= probs.sum()

        self.volunteers = []
        for _ in range(self.n_volunteers):
            n_sk = self.np_random.integers(1, 4)
            sk_idx = self.np_random.choice(NUM_SKILLS, size=min(n_sk, NUM_SKILLS), replace=False, p=probs)
            skills = np.zeros(NUM_SKILLS, dtype=np.float32)
            for idx in sk_idx:
                skills[idx] = 1.0
            self.volunteers.append({
                "available": True, "skills": skills,
                "district_idx": int(self.np_random.integers(0, NUM_DISTRICTS)),
                "cooldown": 0, "stamina": self.max_stamina,
            })

        self.missions = [self._empty_mission() for _ in range(self.max_active_missions)]
        for _ in range(self.np_random.integers(1, 3)):
            self._spawn_mission()

        return self._get_obs(), {}

    def _empty_mission(self):
        return {"active": False, "required_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                "optional_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                "severity": 0.0, "true_severity": 0.0, "district_idx": 0,
                "time_waiting": 0, "assigned_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                "min_volunteers": 0, "assigned_count": 0, "zone": 0, "mission_type": ""}

    def _spawn_mission(self):
        if sum(1 for m in self.missions if m["active"]) >= self.max_active_missions:
            return
        mt_key = self.np_random.choice(MISSION_TYPE_KEYS)
        mt = MISSION_TYPES[mt_key]
        req = np.zeros(NUM_SKILLS, dtype=np.float32)
        for s in mt["required_skills"]:
            if s in SKILL_NAMES: req[SKILL_NAMES.index(s)] = 1.0
        opt = np.zeros(NUM_SKILLS, dtype=np.float32)
        for s in mt.get("optional_skills", []):
            if s in SKILL_NAMES: opt[SKILL_NAMES.index(s)] = 1.0
        sev = float(self.np_random.uniform(*mt["severity_range"]))
        noisy_sev = sev + float(self.np_random.normal(0, self.noise_std)) if self.partial_obs else sev
        noisy_sev = float(np.clip(noisy_sev, 0.0, 1.0))
        d_idx = int(self.np_random.integers(0, NUM_DISTRICTS))
        zone = int(self.np_random.integers(0, self.n_zones)) if self.multi_zone else 0

        mission = {"active": True, "mission_type": mt_key, "required_skills": req,
                   "optional_skills": opt, "severity": noisy_sev, "true_severity": sev,
                   "district_idx": d_idx, "time_waiting": 0,
                   "assigned_skills": np.zeros(NUM_SKILLS, dtype=np.float32),
                   "min_volunteers": mt["min_volunteers"], "assigned_count": 0, "zone": zone}
        for i, m in enumerate(self.missions):
            if not m["active"]:
                self.missions[i] = mission
                self.stats["generated"] += 1
                return

    def _compute_coverage(self, m):
        req = m["required_skills"]
        asg = m["assigned_skills"]
        rc = req.sum()
        if rc == 0: return 1.0
        covered = np.minimum(req, asg).sum()
        ratio = covered / rc
        oc = m["optional_skills"].sum()
        bonus = 0.2 * (np.minimum(m["optional_skills"], asg).sum() / oc) if oc > 0 else 0.0
        return min(1.0, ratio + bonus)

    def _get_travel_time(self, from_d, to_d):
        base = TRAVEL_MATRIX[from_d][to_d]
        if self.use_roads:
            if self.road_status[to_d] < 0.3:
                base *= 3.0
            elif self.road_status[to_d] < 0.7:
                base *= 1.5
        return max(1, int(base * 2))

    def step(self, action):
        self.current_step += 1
        reward = 0.0

        # Road closures
        if self.use_roads and self.road_closure_prob > 0:
            for i in range(NUM_DISTRICTS):
                if self.np_random.random() < self.road_closure_prob:
                    self.road_status[i] = max(0.0, self.road_status[i] - 0.2)
                elif self.road_status[i] < 1.0:
                    self.road_status[i] = min(1.0, self.road_status[i] + 0.05)

        # Process pending delayed actions
        if self.comm_delay:
            new_pending = []
            for pa in self.pending_actions:
                pa["delay"] -= 1
                if pa["delay"] <= 0:
                    reward += self._execute_dispatch(pa["vol_id"], pa["mis_id"])
                else:
                    new_pending.append(pa)
            self.pending_actions = new_pending

        # Update cooldowns + fatigue
        for v in self.volunteers:
            if v["cooldown"] > 0:
                v["cooldown"] -= 1
                if v["cooldown"] == 0:
                    v["available"] = True
            if self.use_fatigue and v["available"]:
                v["stamina"] = min(self.max_stamina, v["stamina"] + 1)

        # Update missions
        for m in self.missions:
            if m["active"]:
                m["time_waiting"] += 1
                cov = self._compute_coverage(m)
                if cov >= 1.0 and m["assigned_count"] >= m["min_volunteers"]:
                    m["active"] = False
                    self.stats["served"] += 1
                    self.stats["severity_served"] += m["true_severity"]
                    speed = max(0, 1.0 - m["time_waiting"] / self.mission_expire_steps)
                    reward += m["true_severity"] * cov * speed * 15.0
                elif m["time_waiting"] >= self.mission_expire_steps:
                    m["active"] = False
                    self.stats["expired"] += 1
                    reward -= m["true_severity"] * 5.0

        # Process action
        if action < self.n_volunteers * self.max_active_missions:
            vol_id = action // self.max_active_missions
            mis_id = action % self.max_active_missions
            if self.comm_delay:
                delay = int(self.np_random.integers(1, 4))
                self.pending_actions.append({"vol_id": vol_id, "mis_id": mis_id, "delay": delay})
            else:
                reward += self._execute_dispatch(vol_id, mis_id)
        else:
            reward -= 0.02 * sum(1 for m in self.missions if m["active"])

        # Arrivals
        for _ in range(self.np_random.poisson(self.arrival_rate)):
            self._spawn_mission()

        truncated = self.current_step >= self.max_steps
        if truncated and self.stats["generated"] > 0:
            reward += (self.stats["served"] / self.stats["generated"]) * 10.0

        return self._get_obs(), float(reward), False, truncated, self._get_info()

    def _execute_dispatch(self, vol_id, mis_id):
        if not (vol_id < len(self.volunteers) and mis_id < len(self.missions)):
            return -0.5
        vol, mis = self.volunteers[vol_id], self.missions[mis_id]
        if not vol["available"] or not mis["active"]:
            return -0.5
        if self.use_fatigue and vol["stamina"] <= 0:
            return -1.0

        old_cov = self._compute_coverage(mis)
        mis["assigned_skills"] = np.maximum(mis["assigned_skills"], vol["skills"])
        mis["assigned_count"] += 1
        new_cov = self._compute_coverage(mis)
        delta = new_cov - old_cov

        travel = self._get_travel_time(vol["district_idx"], mis["district_idx"])
        vol["available"] = False
        vol["cooldown"] = self.base_return_steps + travel
        if self.use_fatigue:
            vol["stamina"] = max(0, vol["stamina"] - (8 + travel))

        r = delta * mis["severity"] * 5.0 if delta > 0 else -0.3
        r -= travel * 0.1
        return r

    def _get_obs(self):
        obs = []
        for v in self.volunteers:
            obs.append(1.0 if v["available"] else 0.0)
            obs.extend(v["skills"].tolist())
            obs.append(v["district_idx"] / NUM_DISTRICTS)
            obs.append(v["cooldown"] / (self.base_return_steps + 10))
            if self.use_fatigue:
                obs.append(v["stamina"] / self.max_stamina)
        for m in self.missions:
            obs.append(1.0 if m["active"] else 0.0)
            obs.extend(m["required_skills"].tolist())
            obs.append(m["severity"])
            obs.append(m["district_idx"] / NUM_DISTRICTS)
            obs.append(m["time_waiting"] / self.mission_expire_steps if m["active"] else 0.0)
            obs.append(self._compute_coverage(m) if m["active"] else 0.0)
            if self.multi_zone:
                obs.append(m["zone"] / max(1, self.n_zones))
        if self.use_roads:
            obs.extend(self.road_status.tolist())
        obs.append(1.0 - self.current_step / self.max_steps)
        return np.array(obs, dtype=np.float32)

    def _get_info(self):
        return {
            "missions_served": self.stats["served"],
            "missions_expired": self.stats["expired"],
            "missions_generated": self.stats["generated"],
            "severity_served": self.stats["severity_served"],
            "service_rate": self.stats["served"] / max(1, self.stats["generated"]),
            "lives_reached_per_hour": self.stats["served"] / max(1, self.current_step) * 30,
        }


# Stage 4: Geography
class DispatchEnvStage4(_BaseAdvancedEnv):
    def __init__(self, **kw):
        super().__init__(use_roads=True, **kw)

# Stage 5: Road closures
class DispatchEnvStage5(_BaseAdvancedEnv):
    def __init__(self, **kw):
        super().__init__(use_roads=True, road_closure_prob=0.05, **kw)

# Stage 6: Partial observability
class DispatchEnvStage6(_BaseAdvancedEnv):
    def __init__(self, **kw):
        super().__init__(use_roads=True, road_closure_prob=0.05, partial_obs=True, noise_std=0.15, **kw)

# Stage 7: Multi-zone
class DispatchEnvStage7(_BaseAdvancedEnv):
    def __init__(self, **kw):
        super().__init__(n_vol=15, n_mis=10, max_steps=400, use_roads=True,
                        road_closure_prob=0.05, partial_obs=True, noise_std=0.15,
                        multi_zone=True, n_zones=3, **kw)

# Stage 8: Fatigue
class DispatchEnvStage8(_BaseAdvancedEnv):
    def __init__(self, **kw):
        super().__init__(n_vol=15, n_mis=10, max_steps=400, use_roads=True,
                        road_closure_prob=0.05, partial_obs=True, noise_std=0.15,
                        multi_zone=True, n_zones=3, fatigue=True, **kw)

# Stage 9: Communication delays
class DispatchEnvStage9(_BaseAdvancedEnv):
    def __init__(self, **kw):
        super().__init__(n_vol=15, n_mis=10, max_steps=400, use_roads=True,
                        road_closure_prob=0.08, partial_obs=True, noise_std=0.2,
                        multi_zone=True, n_zones=3, fatigue=True, comm_delay=True, **kw)
