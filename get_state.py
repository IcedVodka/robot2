from Robotic_Arm.rm_robot_interface import *


left_robot = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
left_handle = left_robot.rm_create_robot_arm("192.168.0.19", 8080)

state = left_robot.rm_get_current_arm_state()
print(state)

right_robot = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
right_handle = right_robot.rm_create_robot_arm("192.168.0.18", 8080)
state = right_robot.rm_get_current_arm_state()
print(state)






