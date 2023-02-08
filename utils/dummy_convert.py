#!usr/bin/python
# -*- coding: utf-8 -*-
import base64
import json
import os
import time
import re
import yaml
from sub_convert import SubConvert

config_file = './config/config.yml'


class NoAliasDumper(yaml.SafeDumper):  # https://ttl255.com/yaml-anchors-and-aliases-and-how-to-disable-them/
    def ignore_aliases(self, data):
        return True


def read_json(file):  # 将 out.json 内容读取为列表
    while os.path.isfile(file) == False:
        print('Awaiting speedtest complete')
        time.sleep(30)
    with open(file, 'r', encoding='utf-8') as f:
        print('Reading out.json')
        proxies_all = json.load(f)
        f.close()
    return proxies_all['nodes']


def output(list, num):
    output_list = []
    for index in range(num):
        proxy = list[index]['link']
        output_list.append(proxy)
    content = base64.b64encode('\n'.join(output_list).encode('utf-8')).decode('ascii')
    with open('./Eternity', 'w+', encoding='utf-8') as f:
        f.write(content)
        print('Write Success!')
        f.close()
    return content


def eternity_convert(file, output):
    file_eternity = open(file, 'r', encoding='utf-8')
    sub_content = file_eternity.read()
    file_eternity.close()
    all_provider = SubConvert().main(sub_content, 'content', 'YAML',
                                     custom_set={'dup_rm_enabled': False, 'format_name_enabled': True})

    # 创建并写入 provider 
    lines = re.split(r'\n+', all_provider)
    # proxy_all = []
    proxy_all_wo_cn = []
    us_proxy = []
    hk_proxy = []
    sg_proxy = []
    jp_proxy = []
    cn_proxy = []
    others_proxy = []
    for line in lines:
        if line != 'proxies:':
            line = '  ' + line
            # proxy_all.append(line)
            if not ('CN' in line or '中国' in line):
                proxy_all_wo_cn.append(line)
            if 'US' in line or '美国' in line:
                us_proxy.append(line)
            elif 'HK' in line or '香港' in line:
                hk_proxy.append(line)
            elif 'SG' in line or '新加坡' in line:
                sg_proxy.append(line)
            elif 'JP' in line or '日本' in line:
                jp_proxy.append(line)
            elif 'CN' in line or '中国' in line:
                cn_proxy.append(line)
            else:
                others_proxy.append(line)

    eternity_providers = {
        'all_wo_cn': 'proxies:\n' + '\n'.join(proxy_all_wo_cn),
        'all': all_provider,
        'others': 'proxies:\n' + '\n'.join(others_proxy),
        'us': 'proxies:\n' + '\n'.join(us_proxy),
        'hk': 'proxies:\n' + '\n'.join(hk_proxy),
        'sg': 'proxies:\n' + '\n'.join(sg_proxy),
        'jp': 'proxies:\n' + '\n'.join(jp_proxy),
        'cn': 'proxies:\n' + '\n'.join(cn_proxy),
    }

    # 创建完全配置的Eternity.yml
    config_f = open(config_file, 'r', encoding='utf-8')
    config_raw = config_f.read()
    config_f.close()

    config = yaml.safe_load(config_raw)

    provider_dic = {}
    for key in eternity_providers.keys():  # 将节点转换为字典形式
        provider_dic[key] = {}
        provider_load = yaml.safe_load(eternity_providers[key])
        provider_dic[key].update(provider_load)

    # 创建节点名列表
    name_dict = {}
    for key in provider_dic.keys():
        name_dict[key] = []
        if not provider_dic[key]['proxies'] is None:
            for proxy in provider_dic[key]['proxies']:
                name_dict[key].append(proxy['name'])
        if provider_dic[key]['proxies'] is None:
            name_dict[key].append('DIRECT')

    # 策略分组添加节点名
    proxy_groups = config['proxy-groups']
    proxy_group_fill = []
    for rule in proxy_groups:
        if rule['proxies'] is None:  # 不是空集加入待加入名称列表
            proxy_group_fill.append(rule['name'])
    for rule_name in proxy_group_fill:
        for rule in proxy_groups:
            if rule['name'] == rule_name:
                if '美国' in rule_name:
                    rule.update({'proxies': name_dict['us']})
                elif '香港' in rule_name:
                    rule.update({'proxies': name_dict['hk']})
                elif '狮城' in rule_name or '新加坡' in rule_name:
                    rule.update({'proxies': name_dict['sg']})
                elif '中国' in rule_name:
                    rule.update({'proxies': name_dict['cn']})
                elif '日本' in rule_name:
                    rule.update({'proxies': name_dict['jp']})
                elif '其他' in rule_name:
                    rule.update({'proxies': name_dict['others']})
                else:
                    rule.update({'proxies': name_dict['all_wo_cn']})

    config.update(provider_dic['all'])
    config.update({'proxy-groups': proxy_groups})

    config_yaml = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True, width=750, indent=2,
                            Dumper=NoAliasDumper)
    Eternity_yml = open(output, 'w+', encoding='utf-8')
    Eternity_yml.write(config_yaml)
    Eternity_yml.close()


if __name__ == '__main__':
    output(read_json('./out.json'), 100)
    eternity_convert('./Eternity', output='./dummy')
