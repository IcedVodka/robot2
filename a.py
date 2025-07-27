from Robot.sensor.depth_camera import list_available_devices

devices = list_available_devices()
for device in devices:
    print(f"设备: {device['name']}, 序列号: {device['serial_number']}")