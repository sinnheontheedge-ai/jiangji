import os

def check_exists(path):
    if not os.path.exists(path):
        raise Exception(f"Missing: {path}")

def check_backend():
    check_exists("inbox/backend")

def check_frontend():
    check_exists("inbox/frontend")

def check_docker():
    check_exists("inbox/docker-compose.yml")

def check_plugins():
    base = "inbox/backend/plugins"
    required = [
        "execution_engine",
        "risk_engine",
        "fund_engine",
        "notification_engine",
        "data_source"
    ]

    for r in required:
        p = os.path.join(base, r)
        if not os.path.exists(p):
            raise Exception(f"Missing plugin: {r}")

def audit():
    print("===== ENGINE AUDIT START =====")

    check_backend()
    check_frontend()
    check_docker()
    check_plugins()

    print("===== AUDIT PASS =====")

if __name__ == "__main__":
    audit()