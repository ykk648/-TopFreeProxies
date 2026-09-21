# -- coding: utf-8 --

import base64
import json
import re
import yaml

import geoip2.database
import requests
import socket
import urllib.parse
from requests.adapters import HTTPAdapter
from utils import EMOJI


class SubConvert:

    # {'input_type': ['url', 'content'],'output_type': ['url', 'YAML', 'Base64']}
    def main(self, raw_input, input_type='url', output_type='url', custom_set=None):
        """Convert subscribe content to YAML or Base64 or url.
        首先获取到订阅内容，然后对其进行格式化处理。如果内容不是 “订阅内容解析错误”，在进行去重、改名操作后（可选）输出目标格式，否则输出 “订阅内容解析错误”。
        """
        if custom_set is None:
            custom_set = {'dup_rm_enabled': False,
                          'format_name_enabled': False}
        if input_type == 'url':  # 获取 URL 订阅链接内容
            # sub_content = ''
            if isinstance(raw_input, list):
                a_content = []
                for url in raw_input:
                    s = requests.Session()
                    s.mount('http://', HTTPAdapter(max_retries=5))
                    s.mount('https://', HTTPAdapter(max_retries=5))
                    try:
                        print('Downloading from:' + url)
                        resp = s.get(url, timeout=10)
                        s_content = self.yaml_decode(self.format(resp.content.decode('utf-8')))
                        a_content.append(s_content)
                    except Exception as err:
                        print(err)
                        return 'Url 解析错误'
                sub_content = self.format(''.join(a_content))
            else:
                s = requests.Session()
                s.mount('http://', HTTPAdapter(max_retries=5))
                s.mount('https://', HTTPAdapter(max_retries=5))
                try:
                    print('Downloading from:' + raw_input)
                    resp = s.get(raw_input, timeout=5)
                    sub_content = self.format(resp.content.decode('utf-8'))
                except Exception as err:
                    print(err)
                    return 'Url 解析错误'
        elif input_type == 'content':  # 解析订阅内容
            sub_content = self.format(raw_input)

        if sub_content != '订阅内容解析错误':
            dup_rm_enabled = custom_set['dup_rm_enabled']
            format_name_enabled = custom_set['format_name_enabled']
            final_content = self.makeup(sub_content, dup_rm_enabled, format_name_enabled)
            if output_type == 'YAML':
                return final_content
            elif output_type == 'Base64':
                return self.base64_encode(self.yaml_decode(final_content))
            elif output_type == 'url':
                return self.yaml_decode(final_content)
            else:
                print('Please define right output type.')
                return '订阅内容解析错误'
        else:
            return '订阅内容解析错误'

    def format(self, sub_content, output=False):
        # 对链接文本(Base64, url, YAML)进行格式化处理, 输出节点的配置字典（Clash 配置）, output 为真是输出 YAML 文本
        if '</b>' not in sub_content:
            if 'proxies:' not in sub_content:  # 对 URL 内容进行格式化处理
                url_list = []
                try:
                    if '://' not in sub_content:
                        sub_content = self.base64_decode(sub_content)

                    raw_url_list = re.split(r'\n+', sub_content)

                    for url in raw_url_list:
                        while len(re.split('ss://|ssr://|vmess://|trojan://|vless://', url)) > 2:
                            url_to_split = url[8:]
                            if 'ss://' in url_to_split and 'vmess://' not in url_to_split and 'vless://' not in url_to_split:
                                url_splited = url_to_split.replace('ss://', '\nss://',
                                                                   1)  # https://www.runoob.com/python/att-string-replace.html
                            elif 'ssr://' in url_to_split:
                                url_splited = url_to_split.replace('ssr://', '\nssr://', 1)
                            elif 'vmess://' in url_to_split:
                                url_splited = url_to_split.replace('vmess://', '\nvmess://', 1)
                            elif 'trojan://' in url_to_split:
                                url_splited = url_to_split.replace('trojan://', '\ntrojan://', 1)
                            elif 'vless://' in url_to_split:
                                url_splited = url_to_split.replace('vless://', '\nvless://', 1)
                            url_split = url_splited.split('\n')

                            front_url = url[:8] + url_split[0]
                            url_list.append(front_url)
                            url = url_split[1]

                        url_list.append(url)

                    url_content = '\n'.join(url_list)
                    return self.yaml_encode(url_content, output=False)
                except:
                    print('Sub_content 格式错误')
                    return '订阅内容解析错误'

            elif 'proxies:' in sub_content:  # 对 Clash 内容进行格式化处理
                try:
                    try_load = yaml.safe_load(sub_content)
                    if output:
                        raise ValueError
                    else:
                        content_yaml_dic = try_load
                        for item in content_yaml_dic['proxies']:  # 对转换过程中出现的不标准配置格式转换
                            try:
                                if item['type'] == 'vmess' and 'HOST' in item['ws-headers'].keys():
                                    item['ws-headers']['Host'] = item['ws-headers'].pop("HOST")
                            except KeyError:
                                if '.' not in item['server']:
                                    content_yaml_dic['proxies'].remove(item)
                                pass
                        return content_yaml_dic  # 返回字典, output 值为 True 时返回修饰过的 YAML 文本
                except Exception:
                    try:
                        sub_content = sub_content.replace('\'', '').replace('"', '')
                        url_list = []
                        il_chars = ['|', '?', '[', ']', '@', '!', '%', ':']
                        lines = re.split(r'\n+', sub_content)
                        line_fix_list = []
                        for line in lines:
                            value_list = re.split(r': |, ', line)
                            if len(value_list) > 6:
                                value_list_fix = []
                                for value in value_list:
                                    for char in il_chars:
                                        value_il = False
                                        if char in value:
                                            value_il = True
                                            break
                                    if value_il == True and ('{' not in value and '}' not in value):
                                        value = '"' + value + '"'
                                        value_list_fix.append(value)
                                    elif value_il == True and '}' in value:
                                        if '}}' in value:
                                            host_part = value.replace('}}', '')
                                            host_value = '"' + host_part + '"}}'
                                            value_list_fix.append(host_value)
                                        elif '}}' not in value:
                                            host_part = value.replace('}', '')
                                            host_value = '"' + host_part + '"}'
                                            value_list_fix.append(host_value)
                                    else:
                                        value_list_fix.append(value)
                                    line_fix = line
                                for index in range(len(value_list_fix)):
                                    line_fix = line_fix.replace(value_list[index], value_list_fix[index])
                                line_fix_list.append(line_fix)
                            elif len(value_list) == 2:
                                value_list_fix = []
                                for value in value_list:
                                    for char in il_chars:
                                        value_il = False
                                        if char in value:
                                            value_il = True
                                            break
                                    if value_il == True:
                                        value = '"' + value + '"'
                                    value_list_fix.append(value)
                                line_fix = line
                                for index in range(len(value_list_fix)):
                                    line_fix = line_fix.replace(value_list[index], value_list_fix[index])
                                line_fix_list.append(line_fix)
                            elif len(value_list) == 1:
                                if ':' in line:
                                    line_fix_list.append(line)
                            else:
                                line_fix_list.append(line)

                        sub_content = '\n'.join(line_fix_list).replace('False', 'false').replace('True', 'true')
                        if output:
                            return sub_content
                        else:
                            content_yaml_dic = yaml.safe_load(sub_content)
                            for item in content_yaml_dic['proxies']:  # 对转换过程中出现的不标准配置格式转换
                                try:
                                    if item['type'] == 'vmess' and 'HOST' in item['ws-headers'].keys():
                                        item['ws-headers']['Host'] = item['ws-headers'].pop("HOST")
                                except KeyError:
                                    if '.' not in item['server']:
                                        content_yaml_dic['proxies'].remove(item)
                                    pass

                            return content_yaml_dic  # 返回字典, output 值为 True 时返回修饰过的 YAML 文本
                    except:
                        print('Sub_content 格式错误')
                        return '订阅内容解析错误'
        else:
            print('订阅内容解析错误')
            return '订阅内容解析错误'

    # 输入节点配置字典, 对节点进行区域的筛选和重命名，输出 YAML 文本
    def makeup(self, input, dup_rm_enabled=False, format_name_enabled=False):
        # 区域判断(Clash YAML): https://blog.csdn.net/CSDN_duomaomao/article/details/89712826 (ip-api)
        if isinstance(input, dict):
            sub_content = input
        else:
            sub_content = self.format(input)
        proxies_list = sub_content['proxies']

        if dup_rm_enabled:  # 去重
            raw_length = len(proxies_list)
            seen_servers = set()
            unique_proxies = []
            for proxy in proxies_list:
                server = proxy.get('server')
                if not server or server in seen_servers:
                    continue
                seen_servers.add(server)
                unique_proxies.append(proxy)
            proxies_list = unique_proxies
            repetition = raw_length - len(proxies_list)
            print(
                f'\n-----去重完成-----\n'
                f'起始数量{raw_length}\n'
                f'当前数量{len(proxies_list)}\n'
                f'重复数量{repetition}\n'
            )

        url_list = []

        for proxy_index, proxy in enumerate(proxies_list):  # 改名
            if proxy['server'] != '127.0.0.1':
                if format_name_enabled:
                    server = proxy['server']
                    if server.replace('.', '').isdigit():
                        ip = server
                    else:
                        try:
                            # https://cloud.tencent.com/developer/article/1569841
                            ip = socket.gethostbyname(server)
                        except Exception:
                            ip = server

                    with geoip2.database.Reader('./utils/Country.mmdb') as ip_reader:
                        try:
                            response = ip_reader.country(ip)
                            country_code = response.country.iso_code
                        except Exception:
                            continue

                    if country_code in ['CLOUDFLARE', 'PRIVATE']:
                        country_code = 'RELAY'

                    if country_code in EMOJI:
                        name_emoji = EMOJI[country_code]
                    else:
                        name_emoji = EMOJI['NOWHERE']

                    proxy['name'] = f'{name_emoji}{country_code}-{ip}-{proxy_index:0>4d}'

                proxy_str = str(proxy)
                url_list.append(proxy_str)

        yaml_content_dic = {'proxies': url_list}
        # yaml.dump 显示中文方法 https://blog.csdn.net/weixin_41548578/article/details/90651464 yaml.dump 各种参数 https://blog.csdn.net/swinfans/article/details/88770119
        yaml_content_raw = yaml.dump(yaml_content_dic, default_flow_style=False, sort_keys=False, allow_unicode=True,
                                     width=750, indent=2)
        yaml_content = self.format(yaml_content_raw, output=True)

        return yaml_content  # 输出 YAML 格式文本

    def yaml_encode(self, url_content, output=True):  # 将 URL 内容转换为 YAML 文本, output 为 False 时输出节点配置字典
        url_list = []

        lines = re.split(r'\n+', url_content)

        for line in lines:
            yaml_url = {}
            if 'vmess://' in line:
                try:
                    vmess_json_config = json.loads(self.base64_decode(line.replace('vmess://', '')))
                    vmess_default_config = {
                        'v': 'Vmess Node', 'ps': 'Vmess Node', 'add': '0.0.0.0', 'port': 0, 'id': '',
                        'aid': 0, 'scy': 'auto', 'net': '', 'type': '', 'host': vmess_json_config['add'], 'path': '/',
                        'tls': ''
                    }
                    vmess_default_config.update(vmess_json_config)
                    vmess_config = vmess_default_config

                    yaml_url = {}
                    # yaml_config_str = ['name', 'server', 'port', 'type', 'uuid', 'alterId', 'cipher', 'tls', 'skip-cert-verify', 'network', 'ws-path', 'ws-headers']
                    # vmess_config_str = ['ps', 'add', 'port', 'id', 'aid', 'scy', 'tls', 'net', 'host', 'path']
                    # 生成 yaml 节点字典
                    if vmess_config['id'] == '' or vmess_config['id'] is None:
                        print('节点格式错误')
                    else:
                        yaml_url.setdefault('name', urllib.parse.unquote(str(vmess_config['ps'])))
                        yaml_url.setdefault('server', vmess_config['add'])
                        yaml_url.setdefault('port', int(vmess_config['port']))
                        yaml_url.setdefault('type', 'vmess')
                        yaml_url.setdefault('uuid', vmess_config['id'])
                        yaml_url.setdefault('alterId', int(vmess_config['aid']))
                        yaml_url.setdefault('cipher', vmess_config['scy'])
                        yaml_url.setdefault('skip-cert-vertify', True)
                        if vmess_config['net'] == '' or vmess_config['net'] is False or vmess_config['net'] is None:
                            yaml_url.setdefault('network', 'tcp')
                        else:
                            yaml_url.setdefault('network', vmess_config['net'])
                        if vmess_config['path'] == '' or vmess_config['path'] is False or vmess_config['path'] is None:
                            yaml_url.setdefault('ws-path', '/')
                        else:
                            yaml_url.setdefault('ws-path', vmess_config['path'])
                        if vmess_config['net'] == 'h2' or vmess_config['net'] == 'grpc':
                            yaml_url.setdefault('tls', True)
                        elif vmess_config['tls'] == '' or vmess_config['tls'] is False or vmess_config['tls'] is None:
                            yaml_url.setdefault('tls', False)
                        else:
                            yaml_url.setdefault('tls', True)
                        if vmess_config['host'] == '':
                            yaml_url.setdefault('ws-headers', {'Host': vmess_config['add']})
                        else:
                            yaml_url.setdefault('ws-headers', {'Host': vmess_config['host']})

                        url_list.append(yaml_url)
                except Exception as err:
                    print(f'yaml_encode 解析 vmess 节点发生错误: {err}')
                    pass

            if 'ss://' in line and 'vless://' not in line and 'vmess://' not in line:
                if '#' not in line:
                    line = line + '#SS%20Node'
                try:
                    ss_content = line.replace('ss://', '')
                    part_list = ss_content.split('#', 1)  # https://www.runoob.com/python/att-string-split.html
                    yaml_url.setdefault('name', urllib.parse.unquote(part_list[1]))
                    if '@' in part_list[0]:
                        mix_part = part_list[0].split('@', 1)
                        method_part = self.base64_decode(mix_part[0])
                        server_part = f'{method_part}@{mix_part[1]}'
                    else:
                        server_part = self.base64_decode(part_list[0])

                    server_part_list = server_part.split(':',
                                                         1)  # 使用多个分隔符 https://blog.csdn.net/shidamowang/article/details/80254476 https://zhuanlan.zhihu.com/p/92287240
                    method_part = server_part_list[0]
                    server_part_list = server_part_list[1].rsplit('@', 1)
                    password_part = server_part_list[0]
                    server_part_list = server_part_list[1].split(':', 1)

                    yaml_url.setdefault('server', server_part_list[0])
                    yaml_url.setdefault('port', server_part_list[1])
                    yaml_url.setdefault('type', 'ss')
                    yaml_url.setdefault('cipher', method_part)
                    yaml_url.setdefault('password', password_part)

                    url_list.append(yaml_url)
                except Exception as err:
                    print(f'yaml_encode 解析 ss 节点发生错误: {err}')
                    pass

            if 'ssr://' in line:
                try:
                    ssr_content = self.base64_decode(line.replace('ssr://', ''))

                    parts = re.split(':', ssr_content)
                    if len(parts) != 6:
                        print('SSR 格式错误: %s' % ssr_content)
                    password_and_params = parts[5]
                    password_and_params = re.split('/\?', password_and_params)
                    password_encode_str = password_and_params[0]
                    params = password_and_params[1]

                    param_parts = re.split('\&', params)
                    param_dic = {}
                    for part in param_parts:
                        key_and_value = re.split('\=', part)
                        param_dic[key_and_value[0]] = key_and_value[1]
                    yaml_url.setdefault('name', self.base64_decode(param_dic['remarks']))
                    yaml_url.setdefault('server', parts[0])
                    yaml_url.setdefault('port', parts[1])
                    yaml_url.setdefault('type', 'ssr')
                    yaml_url.setdefault('cipher', parts[3])
                    yaml_url.setdefault('password', self.base64_decode(password_encode_str))
                    yaml_url.setdefault('obfs', parts[4])
                    yaml_url.setdefault('protocol', parts[2])
                    yaml_url.setdefault('obfsparam', self.base64_decode(param_dic['obfsparam']))
                    yaml_url.setdefault('protoparam', self.base64_decode(param_dic['protoparam']))
                    yaml_url.setdefault('group', self.base64_decode(param_dic['group']))

                    url_list.append(yaml_url)
                except Exception as err:
                    print(f'yaml_encode 解析 ssr 节点发生错误: {err}')
                    pass

            if 'trojan://' in line:
                try:
                    parsed = urllib.parse.urlsplit(line)
                    params = urllib.parse.parse_qs(parsed.query)
                    yaml_url.setdefault(
                        'name',
                        urllib.parse.unquote(parsed.fragment) or 'Trojan Node',
                    )
                    yaml_url.setdefault('server', parsed.hostname)
                    yaml_url.setdefault('port', parsed.port or 443)
                    yaml_url.setdefault('type', 'trojan')
                    yaml_url.setdefault('password', urllib.parse.unquote(parsed.username or ''))
                    sni = (params.get('sni') or params.get('peer') or params.get('servername') or [None])[0]
                    if sni:
                        yaml_url.setdefault('sni', sni)
                    network = (params.get('type') or params.get('network') or ['tcp'])[0]
                    if network != 'tcp':
                        yaml_url.setdefault('network', network)
                    path = (params.get('path') or ['/'])[0]
                    host = (params.get('host') or [None])[0]
                    if network == 'ws':
                        ws_opts = {'path': urllib.parse.unquote(path)}
                        if host:
                            ws_opts['headers'] = {'Host': host}
                        yaml_url.setdefault('ws-opts', ws_opts)
                    allow_insecure = (params.get('allowInsecure') or params.get('allow_insecure') or ['0'])[0]
                    yaml_url.setdefault('skip-cert-verify', allow_insecure in ('1', 'true', 'True'))
                    security = (params.get('security') or ['tls'])[0]
                    if security not in ('tls', ''):
                        yaml_url.setdefault('tls', False)

                    url_list.append(yaml_url)
                except Exception as err:
                    print(f'yaml_encode 解析 trojan 节点发生错误: {err}')
                    pass

            if line.startswith(('socks://', 'socks5://', 'http://', 'https://')):
                try:
                    parsed = urllib.parse.urlsplit(line)
                    proxy_type = 'socks5' if parsed.scheme in ('socks', 'socks5') else 'http'
                    default_port = 1080 if proxy_type == 'socks5' else (443 if parsed.scheme == 'https' else 80)
                    yaml_url.setdefault(
                        'name',
                        urllib.parse.unquote(parsed.fragment) or f'{proxy_type.upper()} Node',
                    )
                    yaml_url.setdefault('server', parsed.hostname)
                    yaml_url.setdefault('port', parsed.port or default_port)
                    yaml_url.setdefault('type', proxy_type)
                    if parsed.username is not None:
                        yaml_url.setdefault('username', urllib.parse.unquote(parsed.username))
                    if parsed.password is not None:
                        yaml_url.setdefault('password', urllib.parse.unquote(parsed.password))
                    if parsed.scheme == 'https':
                        yaml_url.setdefault('tls', True)
                    url_list.append(yaml_url)
                except Exception as err:
                    print(f'yaml_encode 解析 HTTP/SOCKS 节点发生错误: {err}')
                    pass

        yaml_content_dic = {'proxies': url_list}
        if output:
            yaml_content = yaml.dump(yaml_content_dic, default_flow_style=False, sort_keys=False, allow_unicode=True,
                                     width=750, indent=2)
        else:
            yaml_content = yaml_content_dic
        return yaml_content

    def base64_encode(self, url_content):  # 将 URL 内容转换为 Base64
        base64_content = base64.b64encode(url_content.encode('utf-8')).decode('ascii')
        return base64_content

    def yaml_decode(self, url_content):  # YAML 文本转换为 URL 链接内容
        try:
            if isinstance(url_content, dict):
                sub_content = url_content
            else:
                sub_content = self.format(url_content)
            proxies_list = sub_content['proxies']

            protocol_url = []
            for index in range(
                    len(proxies_list)):  # 不同节点订阅链接内容 https://github.com/hoochanlon/fq-book/blob/master/docs/append/srvurl.md
                proxy = proxies_list[index]

                if proxy['type'] == 'vmess':  # Vmess 节点提取, 由 Vmess 所有参数 dump JSON 后 base64 encode 得来。

                    yaml_default_config = {
                        'name': 'Vmess Node', 'server': '0.0.0.0', 'port': 0, 'uuid': '', 'alterId': 0,
                        'cipher': 'auto', 'network': 'ws', 'ws-headers': {'Host': proxy['server']},
                        'ws-path': '/', 'tls': '', 'sni': ''
                    }

                    yaml_default_config.update(proxy)
                    proxy_config = yaml_default_config

                    vmess_value = {
                        'v': 2, 'ps': proxy_config['name'], 'add': proxy_config['server'],
                        'port': proxy_config['port'], 'id': proxy_config['uuid'], 'aid': proxy_config['alterId'],
                        'scy': proxy_config['cipher'], 'net': proxy_config['network'], 'type': None,
                        'host': proxy_config['ws-headers']['Host'],
                        'path': proxy_config['ws-path'], 'tls': proxy_config['tls'], 'sni': proxy_config['sni']
                    }

                    vmess_raw_proxy = json.dumps(vmess_value, sort_keys=False, indent=2, ensure_ascii=False)
                    vmess_proxy = str('vmess://' + self.base64_encode(vmess_raw_proxy) + '\n')
                    protocol_url.append(vmess_proxy)

                elif proxy[
                    'type'] == 'ss':  # SS 节点提取, 由 ss_base64_decoded 部分(参数: 'cipher', 'password', 'server', 'port') Base64 编码后 加 # 加注释(URL_encode)
                    ss_base64_decoded = str(proxy['cipher']) + ':' + str(proxy['password']) + '@' + str(
                        proxy['server']) + ':' + str(proxy['port'])
                    ss_base64 = self.base64_encode(ss_base64_decoded)
                    ss_proxy = str('ss://' + ss_base64 + '#' + str(urllib.parse.quote(proxy['name'])) + '\n')
                    protocol_url.append(ss_proxy)

                elif proxy[
                    'type'] == 'trojan':  # Trojan 节点提取, 由 trojan_proxy 中参数再加上 # 加注释(URL_encode) # trojan Go https://p4gefau1t.github.io/trojan-go/developer/url/
                    params = {
                        'allowInsecure': '1' if proxy.get('skip-cert-verify') else '0',
                    }
                    network = proxy.get('network', 'tcp')
                    if network != 'tcp':
                        params['type'] = network
                    if proxy.get('sni'):
                        params['sni'] = proxy['sni']
                    if proxy.get('tls') is False:
                        params['security'] = 'none'
                    ws_opts = proxy.get('ws-opts') or {}
                    ws_path = ws_opts.get('path') or proxy.get('ws-path')
                    if ws_path:
                        params['path'] = ws_path
                    ws_headers = ws_opts.get('headers') or proxy.get('ws-headers') or {}
                    ws_host = ws_headers.get('Host') or ws_headers.get('host')
                    if ws_host:
                        params['host'] = ws_host
                    server = str(proxy['server'])
                    if ':' in server and not server.startswith('['):
                        server = f'[{server}]'
                    trojan_proxy = str(
                        'trojan://'
                        + urllib.parse.quote(str(proxy['password']), safe='')
                        + '@'
                        + server
                        + ':'
                        + str(proxy['port'])
                        + '?'
                        + urllib.parse.urlencode(params)
                        + '#'
                        + str(urllib.parse.quote(proxy['name']))
                        + '\n'
                    )
                    protocol_url.append(trojan_proxy)

                elif proxy['type'] == 'ssr':  # ssr 节点提取, 由 ssr_base64_decoded 中所有参数总体 base64 encode
                    remarks = self.base64_encode(proxy['name']).replace('+', '-')
                    server = proxy['server']
                    port = str(proxy['port'])
                    password = self.base64_encode(proxy['password'])
                    cipher = proxy['cipher']
                    protocol = proxy['protocol']
                    obfs = proxy['obfs']
                    for key in {'group', 'obfsparam', 'protoparam'}:
                        if key in proxy:
                            if key == 'group':
                                group = self.base64_encode(proxy[key])
                            elif key == 'obfsparam':
                                obfsparam = self.base64_encode(proxy[key])
                            elif key == 'protoparam':
                                protoparam = self.base64_encode(proxy[key])
                        else:
                            if key == 'group':
                                group = 'U1NSUHJvdmlkZXI'
                            elif key == 'obfsparam':
                                obfsparam = ''
                            elif key == 'protoparam':
                                protoparam = ''

                    ssr_proxy = 'ssr://' + self.base64_encode(
                        server + ':' + port + ':' + protocol + ':' + cipher + ':' + obfs + ':' + password + '/?group=' + group + '&remarks=' + remarks + '&obfsparam=' + obfsparam + '&protoparam=' + protoparam + '\n')
                    protocol_url.append(ssr_proxy)

                elif proxy['type'] in ('socks', 'socks5', 'http'):
                    proxy_type = proxy['type']
                    if proxy_type in ('socks', 'socks5'):
                        scheme = 'socks5'
                    else:
                        scheme = 'https' if proxy.get('tls') else 'http'
                    username = proxy.get('username')
                    password = proxy.get('password')
                    auth = ''
                    if username is not None:
                        auth = urllib.parse.quote(str(username), safe='')
                        if password is not None:
                            auth += ':' + urllib.parse.quote(str(password), safe='')
                        auth += '@'
                    server = str(proxy['server'])
                    if ':' in server and not server.startswith('['):
                        server = f'[{server}]'
                    name = urllib.parse.quote(str(proxy.get('name', f'{proxy_type.upper()} Node')))
                    protocol_url.append(
                        f'{scheme}://{auth}{server}:{proxy["port"]}#{name}\n'
                    )

            yaml_content = ''.join(protocol_url)
            return yaml_content
        except Exception as err:
            print(f'yaml decode 发生 {err} 错误')
            return '订阅内容解析错误'

    def base64_decode(self, url_content):  # Base64 转换为 URL 链接内容
        if '-' in url_content:
            url_content = url_content.replace('-', '+')
        if '_' in url_content:
            url_content = url_content.replace('_', '/')
        # print(len(url_content))
        missing_padding = len(url_content) % 4
        if missing_padding != 0:
            url_content += '=' * (4 - missing_padding)  # 不是4的倍数后加= https://www.cnblogs.com/wswang/p/7717997.html
        try:
            base64_content = base64.b64decode(url_content.encode('utf-8')).decode('utf-8',
                                                                                  'ignore')  # https://www.codenong.com/42339876/
            base64_content_format = base64_content
            return base64_content_format
        except UnicodeDecodeError:
            base64_content = base64.b64decode(url_content)
            base64_content_format = base64_content
            return str(base64_content)

    # {url='订阅链接', output_type={'clash': 输出 Clash 配置, 'base64': 输出 Base64 配置, 'url': 输出 url 配置}, host='远程订阅转化服务地址'}
    def convert_remote(self, url='', output_type='clash', host='http://127.0.0.1:25500'):
        # 使用远程订阅转换服务，输出相应配置。
        sever_host = host
        url = urllib.parse.quote(url, safe='')  # https://docs.python.org/zh-cn/3/library/urllib.parse.html
        if output_type == 'clash':
            converted_url = sever_host + '/sub?target=clash&url=' + url + '&insert=false&emoji=true&list=true'
            try:
                resp = requests.get(converted_url, timeout=(3, 20))
                resp.raise_for_status()
            except Exception as err:
                print(err)
                return 'Url 解析错误'
            if resp.text == 'No nodes were found!':
                sub_content = 'Url 解析错误'
            else:
                sub_content = self.makeup(self.format(resp.text), dup_rm_enabled=False, format_name_enabled=True)
        elif output_type == 'base64':
            converted_url = sever_host + '/sub?target=mixed&url=' + url + '&insert=false&emoji=true&list=true'
            try:
                resp = requests.get(converted_url, timeout=(3, 20))
                resp.raise_for_status()
            except Exception as err:
                print(err)
                return 'Url 解析错误'
            if resp.text == 'No nodes were found!':
                sub_content = 'Url 解析错误'
            else:
                sub_content = self.base64_encode(resp.text)
        elif output_type == 'url':
            converted_url = sever_host + '/sub?target=mixed&url=' + url + '&insert=false&emoji=true&list=true'
            try:
                resp = requests.get(converted_url, timeout=(3, 20))
                resp.raise_for_status()
            except Exception as err:
                print(err)
                return 'Url 解析错误'
            if resp.text == 'No nodes were found!':
                sub_content = 'Url 解析错误'
            else:
                sub_content = resp.text
        return sub_content


if __name__ == '__main__':
    subscribe = 'https://fastly.jsdelivr.net/gh/alanbobs999/TopFreeProxies@master/sub/sub_merge.txt'
    output_path = './output.txt'

    content = SubConvert().main(subscribe, input_type='url', output_type='YAML',
                                custom_set={'dup_rm_enabled': True, 'format_name_enabled': True})

    file = open(output_path, 'w', encoding='utf-8')
    file.write(content)
    file.close()
    print(f'Writing content to output.txt\n')
