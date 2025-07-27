import os
os.environ["INFO_LEVEL"] = "DEBUG"
def debug_print(name, info, level="INFO"):
    levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
    if level not in levels.keys():
        debug_print("DEBUG_PRINT", f"level setting error : {level}", "ERROR")
        return
    env_level = os.getenv("INFO_LEVEL", "INFO").upper()
    env_level_value = levels.get(env_level, 20)

    msg_level_value = levels.get(level.upper(), 20)

    if msg_level_value < env_level_value:
        return

    colors = {
        "DEBUG": "\033[94m",   # blue
        "INFO": "\033[92m",    # green
        "WARNING": "\033[93m", # yellow
        "ERROR": "\033[91m",   # red
        "ENDC": "\033[0m",
    }
    color = colors.get(level.upper(), "")
    endc = colors["ENDC"]
    print(f"{color}[{level}][{name}] {info}{endc}") 

if __name__ == "__main__":
    debug_print("TEST", "这是一个测试", "DEBUG")
    debug_print("TEST", "这是一个测试", "INFO")
    debug_print("TEST", "这是一个测试", "WARNING")
    debug_print("TEST", "这是一个测试", "ERROR")

    debug_print("TEST", "这是一个测试", "DEBUG")
    debug_print("TEST", "这是一个测试", "INFO")
    debug_print("TEST", "这是一个测试", "WARNING")
    debug_print("TEST", "这是一个测试", "ERROR")