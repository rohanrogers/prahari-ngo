"""
Prahari RL Environments — Dynamic Mission Assignment under Uncertainty.

Registers custom Gymnasium environments for volunteer dispatch optimization
during crisis events, using real Kerala district geography.
"""

import gymnasium as gym

# Stage 1–3: Foundation environments
gym.register(
    id="PrahariDispatch-v1",
    entry_point="rl.envs.dispatch_env:DispatchEnvStage1",
    max_episode_steps=200,
)

gym.register(
    id="PrahariDispatch-v2",
    entry_point="rl.envs.dispatch_env:DispatchEnvStage2",
    max_episode_steps=200,
)

gym.register(
    id="PrahariDispatch-v3",
    entry_point="rl.envs.dispatch_env:DispatchEnvStage3",
    max_episode_steps=200,
)

# Stage 4–9: Advanced environments
gym.register(
    id="PrahariDispatch-v4",
    entry_point="rl.envs.advanced_env:DispatchEnvStage4",
    max_episode_steps=300,
)

gym.register(
    id="PrahariDispatch-v5",
    entry_point="rl.envs.advanced_env:DispatchEnvStage5",
    max_episode_steps=300,
)

gym.register(
    id="PrahariDispatch-v6",
    entry_point="rl.envs.advanced_env:DispatchEnvStage6",
    max_episode_steps=300,
)

gym.register(
    id="PrahariDispatch-v7",
    entry_point="rl.envs.advanced_env:DispatchEnvStage7",
    max_episode_steps=400,
)

gym.register(
    id="PrahariDispatch-v8",
    entry_point="rl.envs.advanced_env:DispatchEnvStage8",
    max_episode_steps=400,
)

gym.register(
    id="PrahariDispatch-v9",
    entry_point="rl.envs.advanced_env:DispatchEnvStage9",
    max_episode_steps=400,
)

# Stage 10–15: Full Kerala simulation
gym.register(
    id="KeralaFlood-v1",
    entry_point="rl.envs.kerala_flood_env:KeralaFloodEnvStage10",
    max_episode_steps=500,
)

gym.register(
    id="KeralaFlood-v2",
    entry_point="rl.envs.kerala_flood_env:KeralaFloodEnvStage11",
    max_episode_steps=500,
)

gym.register(
    id="KeralaFlood-v3",
    entry_point="rl.envs.kerala_flood_env:KeralaFloodEnvStage12",
    max_episode_steps=500,
)

gym.register(
    id="KeralaFlood-v4",
    entry_point="rl.envs.kerala_flood_env:KeralaFloodEnvStage13",
    max_episode_steps=600,
)

gym.register(
    id="KeralaFlood-v5",
    entry_point="rl.envs.kerala_flood_env:KeralaFloodEnvStage14",
    max_episode_steps=600,
)

gym.register(
    id="KeralaFlood-v6",
    entry_point="rl.envs.kerala_flood_env:KeralaFloodEnvStage15",
    max_episode_steps=720,  # 24 hours × 30 steps/hour
)
