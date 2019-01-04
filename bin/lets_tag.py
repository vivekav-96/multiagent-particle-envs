#!/usr/bin/env python
import os
import sys

from bin.misc.experience import Experience

sys.path.insert(1, os.path.join(sys.path[0], '..'))

import argparse
import numpy as np
import multiagent.scenarios as scenarios
from multiagent.environment import MultiAgentEnv
from bin.policies.dqn_policy import DQNPolicy

RUNNER_SPEED = 0.3
CHASER_SPEED = 0.2


def is_collision(agent1, agent2):
    delta_pos = agent1.state.p_pos - agent2.state.p_pos
    dist = np.sqrt(np.sum(np.square(delta_pos)))
    dist_min = agent1.size + agent2.size
    return True if dist < dist_min else False


def agent_captured_callback(agent, world):
    for a in world.agents:
        if a == agent:
            continue
        else:
            if agent.adversary:
                if not a.adversary:
                    if is_collision(agent, a):
                        return True
            else:
                if a.adversary:
                    if is_collision(agent, a):
                        return True
    return False


if __name__ == '__main__':
    # parse arguments
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument('-s', '--scenario', default='simple_marl_tag.py', help='Path of the scenario Python script.')
    args = parser.parse_args()

    # load scenario from script
    scenario = scenarios.load(args.scenario).Scenario()
    # create world
    world = scenario.make_world()
    # create multiagent environment
    env = MultiAgentEnv(world, scenario.reset_world, scenario.reward, scenario.observation, info_callback=None,
                        done_callback=agent_captured_callback,
                        shared_viewer=True)
    # render call to create viewer window (necessary only for interactive policies)
    # env.render(mode='rgb_array')

    agents = env.agents
    policies = [DQNPolicy(env, args.scenario, i) for i in range(env.n)]
    experiences = []

    # execution loop
    state_n = env.reset()
    iterations = 0
    while iterations < 500:
        iterations += 1
        # query for action from each agent's policy
        act_n = []
        for policy in policies:
            action = policy.action(state_n[policy.agent_index])
            action_one_hot = np.zeros(policy.action_space)
            action_one_hot[action] = RUNNER_SPEED if agents[policy.agent_index] else CHASER_SPEED
            act_n.append(action_one_hot)

        # step environment
        next_state_n, reward_n, done_n, _ = env.step(act_n)

        for i, p in enumerate(policies):
            p.add_memory(Experience(state_n[i], act_n[i], reward_n[i], next_state_n[i], done_n[i]))

        for p in policies:
            p.adapt()

        state_n = next_state_n

        env.render(mode='rgb_array')

    for p in policies:
        p.save_network()