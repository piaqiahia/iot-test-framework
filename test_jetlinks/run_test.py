#!/usr/bin/env python3
"""
IoT 平台一键测试脚本（跨平台）
用法：
    python run_tests.py               # 本地运行（自动启动Docker）
    python run_tests.py --ci          # CI 模式（跳过Docker启停）
    python run_tests.py --skip-docker # 跳过Docker操作
"""

import argparse
import subprocess
import os
import sys
import time
import requests   # 用于健康检查

# ==================== 配置区 ====================
# 本地 Windows Docker Compose 文件目录
DOCKER_COMPOSE_DIR = r"F:\JetLinks\jetlinks-community\docker\run-all"
# CI 环境 Docker 目录（根据实际修改，也可用环境变量覆盖）
DOCKER_COMPOSE_CI_DIR = os.getenv("JETLINKS_DOCKER_DIR", "/app/docker/run-all")

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
HEALTH_URL = "http://localhost:8848/authorize/login"
PYTEST_CMD = ["pytest", "-s", "--alluredir=allure-results", "testcase/"]

# ==================== 功能函数 ====================
def run_command(cmd, shell=False):
    print(f"[CMD] {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    subprocess.run(cmd, shell=shell, check=True)

def wait_for_jetlinks(timeout=300):
    """使用 requests 等待 JetLinks API 可访问"""
    print("⏳ 等待 JetLinks 启动...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(HEALTH_URL, timeout=3)
            # 只要能返回 HTTP 响应（包括 401/404），就认为服务已就绪
            print(f"✅ JetLinks 已响应 (HTTP {resp.status_code})")
            return
        except requests.ConnectionError:
            pass
        except requests.Timeout:
            pass
        print("  等待中...")
        time.sleep(3)
    raise TimeoutError("JetLinks 未能在规定时间内启动")

def start_docker(is_ci):
    if is_ci:
        print("ℹ CI 模式，跳过 Docker 启动")
        return
    # 根据操作系统选择目录
    if sys.platform == "win32":
        compose_file = os.path.join(DOCKER_COMPOSE_DIR, "docker-compose.yml")
        ci_compose_file = os.path.join(DOCKER_COMPOSE_DIR, "docker-compose.ci.yml")
    else:
        compose_file = os.path.join(DOCKER_COMPOSE_CI_DIR, "docker-compose.yml")
        ci_compose_file = os.path.join(DOCKER_COMPOSE_CI_DIR, "docker-compose.ci.yml")

    if os.path.exists(ci_compose_file):
        cmd = f'docker compose -f "{compose_file}" -f "{ci_compose_file}" up -d'
    else:
        cmd = f'docker compose -f "{compose_file}" up -d'
    print("📦 启动 Docker 服务...")
    run_command(cmd, shell=True)

def stop_docker(is_ci):
    if is_ci:
        return
    if sys.platform == "win32":
        compose_file = os.path.join(DOCKER_COMPOSE_DIR, "docker-compose.yml")
        ci_compose_file = os.path.join(DOCKER_COMPOSE_DIR, "docker-compose.ci.yml")
    else:
        compose_file = os.path.join(DOCKER_COMPOSE_CI_DIR, "docker-compose.yml")
        ci_compose_file = os.path.join(DOCKER_COMPOSE_CI_DIR, "docker-compose.ci.yml")

    if os.path.exists(ci_compose_file):
        cmd = f'docker compose -f "{compose_file}" -f "{ci_compose_file}" down'
    else:
        cmd = f'docker compose -f "{compose_file}" down'
    print("🧹 停止 Docker 服务...")
    run_command(cmd, shell=True)

def install_dependencies():
    req_file = os.path.join(TEST_DIR, "requirements.txt")
    if os.path.exists(req_file):
        print("📦 安装 Python 依赖...")
        run_command([sys.executable, "-m", "pip", "install", "-r", req_file])

def run_tests():
    print("🧪 运行测试用例...")
    os.chdir(TEST_DIR)
    run_command(PYTEST_CMD)

def generate_allure_report():
    try:
        subprocess.run(["allure", "--version"], capture_output=True, check=True)
        report_dir = os.path.join(TEST_DIR, "allure-report")
        results_dir = os.path.join(TEST_DIR, "allure-results")
        run_command(["allure", "generate", results_dir, "-o", report_dir, "--clean"])
        print(f"🔗 报告路径: {report_dir}/index.html")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ allure 命令行未安装，跳过报告生成")

# ==================== 主流程 ====================
def main():
    parser = argparse.ArgumentParser(description="IoT 平台一键测试脚本")
    parser.add_argument("--ci", action="store_true", help="CI 模式，跳过 Docker 启停")
    parser.add_argument("--skip-docker", action="store_true", help="跳过 Docker 操作")
    args = parser.parse_args()

    is_ci = args.ci or args.skip_docker

    try:
        install_dependencies()
        start_docker(is_ci)
        wait_for_jetlinks()
        run_tests()
        generate_allure_report()
    except Exception as e:
        print(f"❌ 运行失败: {e}")
        sys.exit(1)
    finally:
        stop_docker(is_ci)
        print("🎉 完成")

if __name__ == "__main__":
    main()