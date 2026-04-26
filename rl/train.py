"""
Prahari RL — Curriculum PPO Training Pipeline.

Trains a PPO agent through progressive environment stages,
graduating when mean reward exceeds threshold.
"""

import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback

# Import environment registrations
import rl.envs  # noqa: F401
import gymnasium as gym


CURRICULA = [
    # (env_id, timesteps, reward_threshold, description)
    ("PrahariDispatch-v1", 50_000, 15.0, "Stage 1: Static dispatch"),
    ("PrahariDispatch-v2", 100_000, 10.0, "Stage 2: Dynamic arrivals"),
    ("PrahariDispatch-v3", 200_000, 8.0, "Stage 3: Multi-skill"),
    ("PrahariDispatch-v4", 200_000, 6.0, "Stage 4: Geography"),
    ("PrahariDispatch-v5", 250_000, 5.0, "Stage 5: Road closures"),
    ("PrahariDispatch-v6", 250_000, 4.0, "Stage 6: Partial obs"),
    ("PrahariDispatch-v7", 300_000, 3.0, "Stage 7: Multi-zone"),
    ("PrahariDispatch-v8", 300_000, 2.0, "Stage 8: Fatigue"),
    ("PrahariDispatch-v9", 350_000, 1.0, "Stage 9: Comm delay"),
    ("KeralaFlood-v1", 400_000, 0.0, "Stage 10: Weather"),
    ("KeralaFlood-v2", 400_000, -2.0, "Stage 11: Weather+roads"),
    ("KeralaFlood-v3", 500_000, -3.0, "Stage 12: Multi-zone alloc"),
    ("KeralaFlood-v4", 500_000, -5.0, "Stage 13: Adversarial"),
    ("KeralaFlood-v5", 600_000, -8.0, "Stage 14: Real skills"),
    ("KeralaFlood-v6", 1_000_000, -10.0, "Stage 15: Full Kerala"),
]

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
TB_DIR = os.path.join(os.path.dirname(__file__), "tensorboard")


def train_stage(env_id: str, timesteps: int, stage_num: int,
                prev_model_path: str = None):
    """Train PPO on a single curriculum stage."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(TB_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"STAGE {stage_num}: {env_id}")
    print(f"Timesteps: {timesteps:,}")
    print(f"{'='*60}\n")

    # Create environment
    env = gym.make(env_id)

    # Validate on first stage
    if stage_num == 1:
        print("Running Gymnasium API compliance checks...")
        check_env(env)
        print("✅ Environment passed all checks.\n")

    # Initialize or load model
    if prev_model_path and os.path.exists(prev_model_path):
        print(f"Loading weights from: {prev_model_path}")
        model = PPO.load(
            prev_model_path, env=env, tensorboard_log=TB_DIR,
            custom_objects={
                "observation_space": env.observation_space,
                "action_space": env.action_space,
            },
        )
    else:
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=3e-4,
            gamma=0.99,
            clip_range=0.2,
            ent_coef=0.01,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            verbose=1,
            tensorboard_log=TB_DIR,
        )

    # Callbacks
    eval_env = gym.make(env_id)
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=os.path.join(MODEL_DIR, f"stage_{stage_num}_best"),
        log_path=os.path.join(TB_DIR, f"stage_{stage_num}_eval"),
        eval_freq=5000,
        deterministic=True,
        render=False,
    )
    checkpoint_cb = CheckpointCallback(
        save_freq=10000,
        save_path=os.path.join(MODEL_DIR, f"stage_{stage_num}_checkpoints"),
        name_prefix=f"ppo_stage{stage_num}",
    )

    # Train
    model.learn(
        total_timesteps=timesteps,
        callback=[eval_cb, checkpoint_cb],
        tb_log_name=f"stage_{stage_num}_{env_id}",
    )

    # Save final model
    save_path = os.path.join(MODEL_DIR, f"ppo_dispatch_stage{stage_num}")
    model.save(save_path)
    print(f"\n✅ Stage {stage_num} model saved: {save_path}")

    # Evaluate
    mean_reward, std_reward = evaluate_policy(
        model, eval_env, n_eval_episodes=10, deterministic=True
    )
    print(f"📊 Evaluation: mean_reward={mean_reward:.2f} ± {std_reward:.2f}")

    eval_env.close()
    env.close()

    return save_path, mean_reward


def train_curriculum(start_stage: int = 1, end_stage: int = 15,
                     timesteps_override: int = None):
    """Run the full curriculum training pipeline."""
    prev_model = None

    for i, (env_id, ts, threshold, desc) in enumerate(CURRICULA):
        stage_num = i + 1
        if stage_num < start_stage:
            # Check if model exists from previous run
            prev_path = os.path.join(MODEL_DIR, f"ppo_dispatch_stage{stage_num}.zip")
            if os.path.exists(prev_path):
                prev_model = prev_path
            continue
        if stage_num > end_stage:
            break

        ts = timesteps_override or ts
        save_path, mean_reward = train_stage(
            env_id, ts, stage_num, prev_model
        )
        prev_model = save_path + ".zip"

        if mean_reward >= threshold:
            print(f"🎓 Stage {stage_num} graduated! (reward {mean_reward:.2f} >= {threshold})")
        else:
            print(f"⚠️  Stage {stage_num} below threshold (reward {mean_reward:.2f} < {threshold})")

    print(f"\n{'='*60}")
    print("🏁 CURRICULUM TRAINING COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prahari RL Training Pipeline")
    parser.add_argument("--stage", type=int, default=None, help="Train single stage (1-15)")
    parser.add_argument("--start", type=int, default=1, help="Start stage for curriculum")
    parser.add_argument("--end", type=int, default=15, help="End stage for curriculum")
    parser.add_argument("--timesteps", type=int, default=None, help="Override timesteps")
    args = parser.parse_args()

    if args.stage:
        env_id, ts, _, desc = CURRICULA[args.stage - 1]
        ts = args.timesteps or ts
        prev = None
        if args.stage > 1:
            prev = os.path.join(MODEL_DIR, f"ppo_dispatch_stage{args.stage - 1}.zip")
            if not os.path.exists(prev):
                prev = None
        train_stage(env_id, ts, args.stage, prev)
    else:
        train_curriculum(args.start, args.end, args.timesteps)
