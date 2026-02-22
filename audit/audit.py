import os
import json

errors = []

# 必须存在的核心引擎文件
def must_exist(path):
    if not os.path.exists(path):
        errors.append(f"missing: {path}")

# 禁止存在的非核心模块或目录
def must_not_exist(path):
    if os.path.exists(path):
        errors.append(f"forbidden: {path}")

# 核心链路文件检查
def check_core_files():
    core_files = [
        'engine_main.py', 
        'strategy.py', 
        'risk.py', 
        'funds.py', 
        'execution.py', 
        'state.py'
    ]
    for file in core_files:
        must_exist(file)

# 检查 WebSocket 与 REST API 一致性
def check_websocket_and_api():
    # WebSocket 与 REST API 一致性检查
    if not os.path.exists("inbox/backend/websocket"):
        errors.append("missing: WebSocket handler")
    if not os.path.exists("inbox/backend/api"):
        errors.append("missing: API handler")
    
# 禁止存在的模块
def check_forbidden_modules():
    must_not_exist("inbox/frontend")
    must_not_exist("inbox/backend/plugins")
    must_not_exist("inbox/backend/api")

# 资金管理与风控检查
def check_risk_and_funds():
    if not os.path.exists("inbox/backend/risk_engine"):
        errors.append("missing: Risk Engine")
    if not os.path.exists("inbox/backend/fund_engine"):
        errors.append("missing: Fund Engine")

# 日志检查
def check_logs():
    log_files = ["engine_log.txt", "strategy_log.txt"]
    for log in log_files:
        must_exist(log)

# 生成审计报告
def generate_report():
    report = {
        "errors": errors,
        "pass": len(errors) == 0
    }
    with open("audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=4)

def audit():
    print("===== ENGINE SPEC AUDIT =====")
    
    # 核心文件检查
    check_core_files()

    # 禁止模块检查
    check_forbidden_modules()

    # 风控和资金管理检查
    check_risk_and_funds()

    # WebSocket 和 API 一致性检查
    check_websocket_and_api()

    # 日志检查
    check_logs()

    # 生成报告
    generate_report()

    # 审计结果输出
    if errors:
        print("AUDIT FAIL")
        for error in errors:
            print(error)
        exit(1)

    print("AUDIT PASS")

if __name__ == "__main__":
    audit()