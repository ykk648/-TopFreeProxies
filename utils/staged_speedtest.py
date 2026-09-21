#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SPEED_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[KMGT]?B/s)", re.I)
UNIT_MULTIPLIERS = {
    "B/S": 1,
    "KB/S": 1024,
    "MB/S": 1024**2,
    "GB/S": 1024**3,
    "TB/S": 1024**4,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a low-traffic, three-stage speed test for Clash proxies."
    )
    parser.add_argument("--config", default="sub/sub_merge_yaml.yaml")
    parser.add_argument("--binary", default="./speedtest-clash-darwin-arm64")
    parser.add_argument("--output-dir", default="speedtest-staged")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--stage1-size", type=int, default=64 * 1024)
    parser.add_argument("--stage1-timeout", default="5s")
    parser.add_argument("--stage1-concurrency", type=int, default=32)
    parser.add_argument("--stage2-size", type=int, default=1024 * 1024)
    parser.add_argument("--stage2-timeout", default="15s")
    parser.add_argument("--stage2-concurrency", type=int, default=8)
    parser.add_argument("--stage3-size", type=int, default=10 * 1024 * 1024)
    parser.add_argument("--stage3-timeout", default="45s")
    parser.add_argument("--stage3-concurrency", type=int, default=2)
    return parser.parse_args()


def clean_output(output):
    return ANSI_RE.sub("", output).replace("\r", "\n")


def extract_proxy_json(output):
    cleaned = clean_output(output)
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            value, _ = decoder.raw_decode(cleaned[match.start() :])
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        message = value.get("message", "")
        if not message.startswith("json: "):
            continue
        try:
            proxies = json.loads(message[6:])
        except json.JSONDecodeError:
            continue
        if isinstance(proxies, list):
            return proxies
    return []


def endpoint(proxy):
    return f"{proxy.get('server')}:{proxy.get('port')}"


def extract_metrics(output, proxies):
    lines = clean_output(output).splitlines()
    metrics = []
    for proxy in proxies:
        address = endpoint(proxy)
        matching_line = next(
            (line for line in lines if address in line and SPEED_RE.search(line)), None
        )
        if not matching_line:
            continue
        speed_match = SPEED_RE.search(matching_line)
        unit = speed_match.group("unit").upper()
        speed_bps = float(speed_match.group("value")) * UNIT_MULTIPLIERS[unit]
        columns = re.split(r"\s{2,}", matching_line.strip())
        speed_index = next(
            (index for index, value in enumerate(columns) if SPEED_RE.search(value)), None
        )
        metrics.append(
            {
                "name": proxy.get("name", ""),
                "endpoint": address,
                "speed": speed_match.group(0),
                "speed_bps": round(speed_bps, 2),
                "ttfb": columns[speed_index + 1]
                if speed_index is not None and len(columns) > speed_index + 1
                else "N/A",
                "latency_ms": columns[speed_index + 2]
                if speed_index is not None and len(columns) > speed_index + 2
                else "N/A",
                "proxy": proxy,
            }
        )
    return sorted(metrics, key=lambda item: item["speed_bps"], reverse=True)


def write_config(path, proxies):
    path.write_text(
        yaml.safe_dump(
            {"proxies": proxies},
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )


def unique_proxy_names(proxies):
    counts = {}
    unique = []
    for index, proxy in enumerate(proxies, 1):
        proxy = dict(proxy)
        base_name = str(proxy.get("name") or f"Proxy {index}")
        counts[base_name] = counts.get(base_name, 0) + 1
        proxy["name"] = (
            base_name if counts[base_name] == 1 else f"{base_name} #{counts[base_name]}"
        )
        unique.append(proxy)
    return unique


def write_clash_verge_config(path, proxies):
    proxies = unique_proxy_names(proxies)
    names = [proxy["name"] for proxy in proxies]
    config = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "external-controller": "127.0.0.1:9090",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "节点选择",
                "type": "select",
                "proxies": ["自动选择", "故障切换", *names, "DIRECT"],
            },
            {
                "name": "自动选择",
                "type": "url-test",
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 100,
                "lazy": True,
                "proxies": list(names),
            },
            {
                "name": "故障切换",
                "type": "fallback",
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
                "lazy": True,
                "proxies": list(names),
            },
        ],
        "rules": ["MATCH,节点选择"],
    }
    path.write_text(
        yaml.safe_dump(
            config,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )


def run_stage(name, binary, config, size, timeout, concurrency, output_dir):
    command = [
        str(binary),
        "-c",
        str(config),
        "-size",
        str(size),
        "-timeout",
        timeout,
        "-concurrent-bandwidth",
        str(concurrency),
        "-sort",
        "b",
    ]
    env = os.environ.copy()
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        env.pop(key, None)

    print(f"\n[{name}] size={size} timeout={timeout} concurrency={concurrency}")
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    output = result.stdout.decode("utf-8", errors="replace")
    sys.stdout.write(output)
    log_path = output_dir / f"{name}.log"
    log_path.write_text(output, encoding="utf-8")

    proxies = extract_proxy_json(output)
    metrics = extract_metrics(output, proxies)
    print(f"[{name}] completed downloads: {len(metrics)}")
    return {
        "name": name,
        "exit_code": result.returncode,
        "tested_config": str(config),
        "size": size,
        "timeout": timeout,
        "concurrency": concurrency,
        "metrics": metrics,
        "log": str(log_path),
    }


def public_stage(stage):
    return {
        key: value
        for key, value in stage.items()
        if key != "metrics"
    } | {
        "completed_downloads": len(stage["metrics"]),
        "results": [
            {key: value for key, value in metric.items() if key != "proxy"}
            for metric in stage["metrics"]
        ],
    }


def main():
    args = parse_args()
    config = Path(args.config).resolve()
    binary = Path(args.binary).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not config.is_file():
        raise SystemExit(f"Config not found: {config}")
    if not binary.is_file():
        raise SystemExit(f"Speed test binary not found: {binary}")

    stage1 = run_stage(
        "stage1-quick",
        binary,
        config,
        args.stage1_size,
        args.stage1_timeout,
        args.stage1_concurrency,
        output_dir,
    )
    stage1_proxies = [item["proxy"] for item in stage1["metrics"]]
    if not stage1_proxies:
        print("No proxy completed the quick test; stopping.")
        stages = [stage1]
        selected = []
    else:
        stage2_config = output_dir / "stage2-candidates.yaml"
        write_config(stage2_config, stage1_proxies)
        stage2 = run_stage(
            "stage2-medium",
            binary,
            stage2_config,
            args.stage2_size,
            args.stage2_timeout,
            args.stage2_concurrency,
            output_dir,
        )
        stage2_proxies = [item["proxy"] for item in stage2["metrics"][: args.top]]
        stages = [stage1, stage2]

        if not stage2_proxies:
            print("No proxy completed the medium test; stopping.")
            selected = []
        else:
            stage3_config = output_dir / "stage3-top.yaml"
            write_config(stage3_config, stage2_proxies)
            stage3 = run_stage(
                "stage3-final",
                binary,
                stage3_config,
                args.stage3_size,
                args.stage3_timeout,
                args.stage3_concurrency,
                output_dir,
            )
            stages.append(stage3)
            selected = [item["proxy"] for item in stage3["metrics"]]

    selected_path = output_dir / "selected-proxies.yaml"
    write_config(selected_path, selected)
    clash_verge_path = output_dir / "clash-verge-config.yaml"
    write_clash_verge_config(clash_verge_path, selected)
    report = {
        "created_at": datetime.now().astimezone().isoformat(),
        "source_config": str(config),
        "selected_config": str(selected_path),
        "clash_verge_config": str(clash_verge_path),
        "selected_count": len(selected),
        "stages": [public_stage(stage) for stage in stages],
    }
    report_path = output_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nSelected proxies: {len(selected)}")
    print(f"Config: {selected_path}")
    print(f"Clash Verge: {clash_verge_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
