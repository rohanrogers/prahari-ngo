"""
Prahari RL — Deterministic Policy Evaluation.

Evaluates trained models with detailed metrics:
- Service rate, severity served, lives reached per hour
- Comparison against random and greedy baselines
"""

import argparse
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
import rl.envs  # noqa: F401
import gymnasium as gym
import numpy as np


MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


def evaluate_model(model_path: str, env_id: str, n_episodes: int = 10):
    """Evaluate a trained model with detailed metrics."""
    env = gym.make(env_id)
    model = PPO.load(model_path, env=env)

    # PPO evaluation
    all_infos = []
    for ep in range(n_episodes):
        obs, info = env.reset()
        done = False
        ep_reward = 0.0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
        info["episode_reward"] = ep_reward
        all_infos.append(info)

    # Aggregate
    results = {
        "model": os.path.basename(model_path),
        "env": env_id,
        "episodes": n_episodes,
        "mean_reward": float(np.mean([i["episode_reward"] for i in all_infos])),
        "std_reward": float(np.std([i["episode_reward"] for i in all_infos])),
        "mean_service_rate": float(np.mean([i.get("service_rate", 0) for i in all_infos])),
        "mean_severity_served": float(np.mean([i.get("severity_served", 0) for i in all_infos])),
        "mean_lives_per_hour": float(np.mean([i.get("lives_reached_per_hour", 0) for i in all_infos])),
        "mean_missions_served": float(np.mean([i.get("missions_served", 0) for i in all_infos])),
        "mean_missions_expired": float(np.mean([i.get("missions_expired", 0) for i in all_infos])),
    }

    env.close()
    return results


def evaluate_random(env_id: str, n_episodes: int = 10):
    """Baseline: random actions."""
    env = gym.make(env_id)
    all_infos = []
    for _ in range(n_episodes):
        obs, _ = env.reset()
        done = False
        ep_reward = 0.0
        while not done:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
        info["episode_reward"] = ep_reward
        all_infos.append(info)
    env.close()
    return {
        "model": "random_baseline",
        "mean_reward": float(np.mean([i["episode_reward"] for i in all_infos])),
        "mean_service_rate": float(np.mean([i.get("service_rate", 0) for i in all_infos])),
        "mean_lives_per_hour": float(np.mean([i.get("lives_reached_per_hour", 0) for i in all_infos])),
    }


def compare(model_path: str, env_id: str, n_episodes: int = 10):
    """Compare trained model vs random baseline."""
    print(f"\n{'='*60}")
    print(f"EVALUATION: {env_id}")
    print(f"{'='*60}")

    ppo = evaluate_model(model_path, env_id, n_episodes)
    rand = evaluate_random(env_id, n_episodes)

    print(f"\n{'Metric':<25} {'PPO Agent':>15} {'Random':>15} {'Improvement':>15}")
    print("-" * 70)
    for key in ["mean_reward", "mean_service_rate", "mean_lives_per_hour"]:
        p, r = ppo.get(key, 0), rand.get(key, 0)
        imp = ((p - r) / abs(r) * 100) if r != 0 else float("inf")
        print(f"{key:<25} {p:>15.2f} {r:>15.2f} {imp:>14.1f}%")

    # Save results
    os.makedirs(MODEL_DIR, exist_ok=True)
    results = {"ppo": ppo, "random": rand}
    out_path = os.path.join(MODEL_DIR, "evaluation_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📊 Results saved: {out_path}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prahari RL Evaluation")
    parser.add_argument("--model", required=True, help="Path to trained model .zip")
    parser.add_argument("--env", default="PrahariDispatch-v1", help="Environment ID")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--compare", action="store_true", help="Compare vs random")
    args = parser.parse_args()

    if args.compare:
        compare(args.model, args.env, args.episodes)
    else:
        results = evaluate_model(args.model, args.env, args.episodes)
        print(json.dumps(results, indent=2))
