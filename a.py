from Robot.robot.realman_controller import RealmanController


if __name__ == "__main__":
    master = RealmanController("Master")
    master.set_up("192.168.1.19", 8080)  # 修改为你的 master 机械臂 IP
    master.set_arm_joints_block([0, 0, 0, 0, 0, 0])
    master.set_arm_init_joint()


    slave = RealmanController("Slave")
    slave.set_up("192.168.1.18", 8080)   # 修改为你的 slave 机械臂 IP
    slave.set_arm_joints_block([0, 0, 0, 0, 0, 0])
    slave.set_arm_init_joint()

    # slave.reset_zero_position()
    # slave.set_arm_init_joint()
    # angle1 =[30000,65535,65535,65535,65535,0]
    # angle2 =[0,0,0,0,0,0]
    # slave.set_hand_pos(angle2,True)
