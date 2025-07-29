 

def print_grasp_poses(above_pose, correct_pose, finally_pose , logger = None):
        """打印抓取位姿信息"""
        if logger:
            logger.debug("\n" + "="*50)
            logger.debug("机械臂抓取位姿计算结果")
            logger.debug("="*50)
        else:
            print("\n" + "="*50)
            print("机械臂抓取位姿计算结果")
            print("="*50)
        
        if above_pose is not None:
            if logger:
                logger.debug("位点1 - 物体上方位姿:")
                logger.debug(f"  X: {above_pose[0]:.3f} m")
                logger.debug(f"  Y: {above_pose[1]:.3f} m") 
                logger.debug(f"  Z: {above_pose[2]:.3f} m")
                logger.debug(f"  RX: {above_pose[3]:.3f} rad")
                logger.debug(f"  RY: {above_pose[4]:.3f} rad")
                logger.debug(f"  RZ: {above_pose[5]:.3f} rad")
                logger.debug("")
            else:
                print("位点1 - 物体上方位姿:")
                print(f"  X: {above_pose[0]:.3f} m")
                print(f"  Y: {above_pose[1]:.3f} m") 
                print(f"  Z: {above_pose[2]:.3f} m")
                print(f"  RX: {above_pose[3]:.3f} rad")
                print(f"  RY: {above_pose[4]:.3f} rad")
                print(f"  RZ: {above_pose[5]:.3f} rad")
                print()
        
        if correct_pose is not None:
            if logger:
                logger.debug("位点2 - 角度调整位姿:")
                logger.debug(f"  X: {correct_pose[0]:.3f} m")
                logger.debug(f"  Y: {correct_pose[1]:.3f} m")
                logger.debug(f"  Z: {correct_pose[2]:.3f} m")
                logger.debug(f"  RX: {correct_pose[3]:.3f} rad")
                logger.debug(f"  RY: {correct_pose[4]:.3f} rad")
                logger.debug(f"  RZ: {correct_pose[5]:.3f} rad")
                logger.debug("")
            else:
                print("位点2 - 角度调整位姿:")
                print(f"  X: {correct_pose[0]:.3f} m")
                print(f"  Y: {correct_pose[1]:.3f} m")
                print(f"  Z: {correct_pose[2]:.3f} m")
                print(f"  RX: {correct_pose[3]:.3f} rad")
                print(f"  RY: {correct_pose[4]:.3f} rad")
                print(f"  RZ: {correct_pose[5]:.3f} rad")
                print()
        
        if finally_pose is not None:
            if logger:
                logger.debug("位点3 - 最终抓取位姿:")
                logger.debug(f"  X: {finally_pose[0]:.3f} m")
                logger.debug(f"  Y: {finally_pose[1]:.3f} m")
                logger.debug(f"  Z: {finally_pose[2]:.3f} m")
                logger.debug(f"  RX: {finally_pose[3]:.3f} rad")
                logger.debug(f"  RY: {finally_pose[4]:.3f} rad")
                logger.debug(f"  RZ: {finally_pose[5]:.3f} rad")
                logger.debug("")
            else:
                print("位点3 - 最终抓取位姿:")
                print(f"  X: {finally_pose[0]:.3f} m")
                print(f"  Y: {finally_pose[1]:.3f} m")
                print(f"  Z: {finally_pose[2]:.3f} m")
                print(f"  RX: {finally_pose[3]:.3f} rad")
                print(f"  RY: {finally_pose[4]:.3f} rad")
                print(f"  RZ: {finally_pose[5]:.3f} rad")
                print()