# TopFreeProxies

## 仓库介绍

收集仍可访问的公开订阅源，生成合并后的 Clash 节点列表，并提供分级测速和 Clash Verge 配置输出。

## 手动运行

```shell
python -m pip install -r utils/requirements.txt
python utils/source_health.py
python utils/list_merge.py
```

`list_merge.py` 默认连接本机 `127.0.0.1:25500` 的 subconverter。远程转换失败时会尝试使用仓库内置解析器处理源内容，单个源失败不会中断其他源的合并。

主要产物：

- `sub/sub_merge_yaml.yaml`：所有已启用源的合并节点列表，仅保存在本地。
- `sub/source_health.json`：最近一次源健康检查结果。
- `clash-verge.yaml`：经过实际下载测试后生成的 Clash Verge 完整配置，仅保存在本地。

节点列表和 Clash Verge 配置包含公开代理凭据，已加入 `.gitignore`，不会提交到远端仓库。

## GitHub Actions

Action 仅支持在 GitHub 页面手动触发 `workflow_dispatch`，没有定时任务，也不会自动运行。

手动任务会：

1. 检查已启用源的状态码、内容大小和订阅格式。
2. 下载固定版本的 subconverter 并校验 SHA-256。
3. 合并仍可用的源并更新节点统计。
4. 仅提交 README 和源健康状态，不公开节点配置。

## macOS ARM 测速

项目根目录已加入 `speedtest-clash-darwin-arm64`，来源为 `xiecang/speedtest-clash` v0.5.1 的官方 Darwin ARM64 Release。

二进制 SHA-256：

```text
d3203818be6cfa3ca2019bcb50262baf493ca2f164518a6d925e16743ba34ccf
```

大量节点应先粗筛再精测，避免给明显失效的节点下载 1 MB 或 100 MB：

```shell
python utils/staged_speedtest.py
```

默认流程：

1. 全量节点下载 64 KB，超时 5 秒，并发 32。
2. 第一轮成功节点下载 1 MB，超时 15 秒，并发 8。
3. 按第二轮速度取前 10 个，下载 10 MB，超时 45 秒，并发 2。

结果保存在 `speedtest-staged/`：`report.json` 是各轮速度和延迟摘要，`selected-proxies.yaml` 是最终通过精测的节点列表，`clash-verge-config.yaml` 是可直接导入 Clash Verge 的完整配置。测速时脚本会清除系统代理环境变量，确保流量确实通过被测节点。

## 所有节点
合并节点总数: `1179` 单一IP地址限制1个节点

## 节点来源
- [ssrsub/ssr](https://github.com/ssrsub/ssr), 节点数量: `134`
- [anaer/Sub](https://github.com/anaer/Sub), 节点数量: `728`
- [ermaozi01/free_clash_vpn](https://github.com/ermaozi01/free_clash_vpn), 节点数量: `6`
- [Pawdroid/Free-servers](https://github.com/Pawdroid/Free-servers), 节点数量: `11`
- [xrayfree/free-ssr-ss-v2ray-vpn-clash](https://github.com/xrayfree/free-ssr-ss-v2ray-vpn-clash), 节点数量: `91`
- [ermaozi/get_subscribe](https://github.com/ermaozi/get_subscribe), 节点数量: `114`
- [Leon406/SubCrawler](https://github.com/Leon406/SubCrawler), 节点数量: `339`
- [735754647/Free-Nodes](https://github.com/735754647/Free-Nodes), 节点数量: `2`
- [steam-100/free-proxy-sub](https://github.com/steam-100/free-proxy-sub), 节点数量: `36`

## 源状态

`python utils/source_health.py` 会生成 `sub/source_health.json`。默认模式只在所有已启用源均失效时返回失败；使用 `--strict` 可在任一源失败时返回失败。

`sub/sub_list.json` 中的检查等级：

- `protocol_ok`：已使用 Mihomo 完成协议级健康检查和实际 HTTP 代理请求。
- `tcp_ok`：订阅可解析，且抽样节点服务器端口可达，尚未逐个完成协议级验证。

## 声明

所有资源来自公开互联网，仅用于代码、爬虫和网络协议学习。公开 HTTP/SOCKS 代理不提供端到端加密，任何免费节点都不应承载账号、支付、Cookie、隐私数据或其他敏感流量。仓库不保证节点的安全性、稳定性或合法性。
