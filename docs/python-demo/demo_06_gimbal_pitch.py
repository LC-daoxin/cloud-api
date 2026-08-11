"""
demo_06_gimbal_pitch.py -- 云台复位（gimbal_reset）

仅支持 gimbal_reset（4 种复位模式）。
camera_aim / camera_screen_drag 不在服务端已实现的指令列表中，已移除。

运行：
    python3 demo_06_gimbal_pitch.py
"""
from config import DRONE_SN, PAYLOAD_INDEX
from demo_common import (
    DemoError,
    login,
    print_error_and_hint,
    require_config,
    seize_payload_authority,
    send_payload_command,
)

RESET_MODES = {0: "回中", 1: "向下", 2: "偏航回中", 3: "向下45度"}


def _payload_command(token, cmd: str, data: dict):
    try:
        return send_payload_command(token, cmd, data, sn=DRONE_SN, timeout=10)
    except DemoError as exc:
        print_error_and_hint(exc)
        return None


def gimbal_reset(token, mode: int = 0):
    """云台复位：0=回中 1=向下 2=偏航回中 3=向下45度"""
    return _payload_command(token, "gimbal_reset", {
        "payload_index": PAYLOAD_INDEX,
        "reset_mode": mode,
    })


def _ok(result):
    return bool(result and result.get("code") == 0)


def _print_result(label, result):
    if result is None:
        return
    mark = "✓" if _ok(result) else "✗"
    msg = result.get("message", "")
    print(f"  [{mark}] {label}: {msg}")


if __name__ == "__main__":
    try:
        require_config(YOOX_DRONE_SN=DRONE_SN, YOOX_PAYLOAD_INDEX=PAYLOAD_INDEX)
        print(f"[*] 目标设备: {DRONE_SN}")
        print(f"[*] 负载索引: {PAYLOAD_INDEX}\n")

        token = login()
        seize_payload_authority(token, PAYLOAD_INDEX, sn=DRONE_SN)
    except DemoError as exc:
        print_error_and_hint(exc)
        raise SystemExit(1)

    print("""═══ 云台复位指令 ═══

── gimbal_reset（云台复位） ──
  r0 / horizon   回中       (mode=0)
  r1 / down90    向下       (mode=1)
  r2             偏航回中   (mode=2)
  r3             向下45度   (mode=3)

  q  退出
""")

    while True:
        cmd = input("输入指令: ").strip().lower()

        if not cmd:
            continue

        if cmd == "q":
            break
        elif cmd in ("r0", "horizon"):
            _print_result(f"云台复位({RESET_MODES[0]})", gimbal_reset(token, mode=0))
        elif cmd in ("r1", "down90"):
            _print_result(f"云台复位({RESET_MODES[1]})", gimbal_reset(token, mode=1))
        elif cmd == "r2":
            _print_result(f"云台复位({RESET_MODES[2]})", gimbal_reset(token, mode=2))
        elif cmd == "r3":
            _print_result(f"云台复位({RESET_MODES[3]})", gimbal_reset(token, mode=3))

        else:
            print("  未知指令，输入 q 退出")
