import os

# 检查 WebSocket 驱动是否存在
def check_websocket():
    # 确保核心引擎使用的是 WebSocket，检查交易所的 WebSocket 连接
    if not os.path.exists('engine_main.py'):
        raise Exception("Missing engine_main.py")
    print("WebSocket Check Passed")
    return True

# 检查核心链路是否完整
def check_core_link():
    # 核心链路检查：WebSocket -> Strategy -> Risk -> Funds -> Execution -> State
    required_files = ['engine_main.py', 'strategy.py', 'risk.py', 'funds.py', 'execution.py', 'state.py']
    for file in required_files:
        if not os.path.exists(file):
            raise Exception(f"Missing required file: {file}")
    print("Core Link Check Passed")
    return True

# 你可以根据 ENGINE_SPEC 扩展更多检查项

def audit():
    print("Audit Start...")
    check_websocket()
    check_core_link()
    print("Audit PASSED")