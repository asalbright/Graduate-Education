################################################################################################################
# File Name: load_env.py
# Author: Andrew Albright 
# 
# Description: file for loading in the .urdf file of the single leg to visualize everything
# Notes: https://gerardmaggiolino.medium.com/creating-openai-gym-environments-with-pybullet-part-1-13895a622b24
################################################################################################################

import time
import numpy as np
import gym
import pybullet as p
import pybullet_data
from time import sleep
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
print(matplotlib.matplotlib_fname())

from gym_single_leg.gym_single_leg.envs.single_leg_env import SingleLegEnv
from stable_baselines3.common.env_checker import check_env

EPISODE_STEPS = 240*10
MOTOR_MAX_POS = np.deg2rad(30)
MOTOR_MAX_VEL = np.deg2rad(330) # 55 RPM -> 330 deg/s
SPRING_K = 0.75
SPRING_DAMPING = 1
FLEX_MAX_POS = np.deg2rad(15)

DEBUG = False

def main():
    '''
    Run this file as a script. To exit program and plot data, press the "Close" button
    in the GUI presented. 

    Wait for data to be plotted. The data is collected at every timestep during sim (240Hz).
    The longer the sim is allowed to run, the more data there will be.

    To see changes in solver analytics data, change parameters. 
    '''

    # Declare the env
    env = SingleLegEnv(robotType="USER_SPECIFIED",
                       robotLocation="flexible/basic_flex_jumper/basic_flex_jumper.urdf",
                       showGUI=True,
                       flexible=True,
                       epSteps=EPISODE_STEPS,
                       maxMotorPos=MOTOR_MAX_POS,
                       maxMotorVel=MOTOR_MAX_VEL,  # RPM
                       maxMotorForce=100,
                       positionGain=SPRING_K,
                       velocityGain=SPRING_DAMPING,
                       maxFlexPosition=FLEX_MAX_POS,
                       controlMode="POSITION_CONTROL",
                       captureData=False,
                       saveDataName=None,
                       saveDataLocation=None)

    # check_env(env)

    obs = env.reset()

    # Set debug parameters
    motor_one = p.addUserDebugParameter('Motor1', -MOTOR_MAX_VEL, MOTOR_MAX_VEL, 0, physicsClientId=env.client)
    motor_two = p.addUserDebugParameter('Motor2', -MOTOR_MAX_VEL, MOTOR_MAX_VEL, 0, physicsClientId=env.client)
    force = p.addUserDebugParameter('Force', -5, 10, 0, physicsClientId=env.client)
    position_gain = p.addUserDebugParameter('Kp', 0.01, 1.5, 0.75, physicsClientId=env.client)
    velocity_gain = p.addUserDebugParameter('Kv', 0.01, 1, 0.5, physicsClientId=env.client)
    break_simulation = p.addUserDebugParameter('Close', 1, 0, 0, physicsClientId=env.client)
    
    # Lists for storing solver iterations and error data
    num_iterations = []
    error = []
    # Listed for storing flex joint position values
    flex_positions = [[], []]
    flex_velocities = [[], []]
    motor_positions = [[], []]
    motor_velocities = [[], []]

    while p.isConnected():
        # Read debug parameters from GUI
        motor_one_input = p.readUserDebugParameter(motor_one, physicsClientId=env.client)
        motor_two_input = p.readUserDebugParameter(motor_two, physicsClientId=env.client)
        force_input = p.readUserDebugParameter(force, physicsClientId=env.client)
        position_gain_input = p.readUserDebugParameter(position_gain, physicsClientId=env.client)
        velocity_gain_input = p.readUserDebugParameter(velocity_gain, physicsClientId=env.client)
        break_simulation_input = p.readUserDebugParameter(break_simulation, physicsClientId=env.client)
        if break_simulation_input: break

        # Set the gains for the flex joints according to the sliders in the GUI
        env.leg.position_gain = position_gain_input
        env.leg.velocity_gain = velocity_gain_input

        # Apply the motor debug parameters to the env motors
        action = motor_one_input, motor_two_input
        # Apply the debug force parameter to the env
        p.applyExternalForce(env.leg.leg,
                             0,
                             [0,0,-force_input], 
                             [0,0,0],
                             flags=p.LINK_FRAME,
                             physicsClientId=env.client)
        # Apply step in env
        obs, _, done, _ = env.step(action)

        # Get solver analytics from env
        solver_analytics = env.solver_analytics
        # Append solver analytics to the data lists
        num_iterations.append(solver_analytics["numIterationsUsed"])
        error.append(solver_analytics["remainingResidual"])

        # Print analytics to the consol
        # print(f" Solver Iterations: {num_iterations}")
        # print(f"Residual Error: {error}")

        # Get the information about the flex joints
        flex_joint_states = env.leg.get_joint_states(env.leg.flex_joints)
        flex_positions[0].append(flex_joint_states[0,0])
        flex_positions[1].append(flex_joint_states[1,0])
        flex_velocities[0].append(flex_joint_states[0,1])
        flex_velocities[1].append(flex_joint_states[1,1])

        # Get the information about the motor joints
        motor_joint_states = env.leg.get_joint_states(env.leg.motor_joints)
        motor_positions[0].append(motor_joint_states[0,0])
        motor_positions[1].append(motor_joint_states[1,0])
        motor_velocities[0].append(motor_joint_states[0,1])
        motor_velocities[1].append(motor_joint_states[1,1])


        # time.sleep(1/240)

        p.configureDebugVisualizer(p.COV_ENABLE_SINGLE_STEP_RENDERING,1)

        if done:
            obs = env.reset()
            time.sleep(1/30)
        
    env.close()

    # When the sim is closed, plot the solver analytics data
    if DEBUG:
        sim_time = np.array(range(len(motor_positions[0])))
        sim_time = sim_time / 240

        # num iterations plot
        fig = plt.figure(figsize=(6,4))
        plt.xlabel('Timestep')
        plt.ylabel('Num Iterations')
        plt.plot(list(range(len(num_iterations))), num_iterations, linewidth=2, linestyle='-')
        # solver error plot
        fig = plt.figure(figsize=(6,4))
        plt.xlabel('Timestep')
        plt.ylabel('Residual Error')
        plt.plot(list(range(len(error))), error, linewidth=2, linestyle='-')
        # positions
        fig = plt.figure(figsize=(6,4))
        plt.xlabel('Time (s)')
        plt.ylabel('Motor Positions')
        plt.plot(sim_time, np.rad2deg(motor_positions[0]), linewidth=2, linestyle='-')
        plt.plot(sim_time, np.rad2deg(motor_positions[1]), linewidth=2, linestyle='-')
        # velocities
        fig = plt.figure(figsize=(6,4))
        plt.xlabel('Time (s)')
        plt.ylabel('Flex Positions')
        plt.plot(sim_time, np.rad2deg(flex_positions[0]), linewidth=2, linestyle='-')
        plt.plot(sim_time, np.rad2deg(flex_positions[1]), linewidth=2, linestyle='-')

        plt.show()

if __name__ == '__main__':
    main()
    