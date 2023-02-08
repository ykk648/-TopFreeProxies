#!/usr/bin/env python3

import json
import os
import re
from urllib import request
import yaml

from list_update import UpdateUrl
from sub_convert import SubConvert
from cv2box.utils import os_call

# 文件路径定义
Eterniy = './Eternity'
readme = './README.md'

sub_list_json = './sub/sub_list.json'
sub_merge_path = './sub/'
sub_list_path = './sub/list/'
yaml_p = '{}/sub_merge_yaml.yaml'.format(sub_merge_path)


def content_write(file, output_type):
    file = open(file, 'w+', encoding='utf-8')
    file.write(output_type)
    file.close()


class SubMerge:
    def __init__(self):
        self.sc = SubConvert()

    def sub_merge(self, url_list):  # 将转换后的所有 Url 链接内容合并转换 YAML or Base64, ，并输出文件，输入订阅列表。

        content_list = []
        os_call('rm -f ./sub/list/*')

        for index in range(len(url_list)):
            content = self.sc.convert_remote(url_list[index]['url'], output_type='url', host='http://127.0.0.1:25500')
            ids = url_list[index]['id']
            remarks = url_list[index]['remarks']
            if content == 'Url 解析错误':
                content = self.sc.main(self.read_list(sub_list_json)[index]['url'], input_type='url', output_type='url')
                if content != 'Url 解析错误':
                    content_list.append(content)
                    print(f'Writing content of {remarks} to {ids:0>2d}.txt\n')
                else:
                    print(f'Writing error of {remarks} to {ids:0>2d}.txt\n')
                file = open(f'{sub_list_path}{ids:0>2d}.txt', 'w+', encoding='utf-8')
                file.write('Url 解析错误')
                file.close()
            elif content == 'Url 订阅内容无法解析':
                file = open(f'{sub_list_path}{ids:0>2d}.txt', 'w+', encoding='utf-8')
                file.write('Url 订阅内容无法解析')
                file.close()
                print(f'Writing error of {remarks} to {ids:0>2d}.txt\n')
            elif content != None:
                content_list.append(content)
                file = open(f'{sub_list_path}{ids:0>2d}.txt', 'w+', encoding='utf-8')
                file.write(content)
                file.close()
                print(f'Writing content of {remarks} to {ids:0>2d}.txt\n')
            else:
                file = open(f'{sub_list_path}{ids:0>2d}.txt', 'w+', encoding='utf-8')
                file.write('Url 订阅内容无法解析')
                file.close()
                print(f'Writing error of {remarks} to {ids:0>2d}.txt\n')

        print('Merging nodes...\n')
        content_raw = ''.join(
            content_list)  # https://python3-cookbook.readthedocs.io/zh_CN/latest/c02/p14_combine_and_concatenate_strings.html
        content_yaml = self.sc.main(content_raw, 'content', 'YAML',
                                    {'dup_rm_enabled': True, 'format_name_enabled': True})
        content_write(yaml_p, content_yaml)

        # content_base64 = self.sc.base64_encode(content_raw)
        # content = content_raw
        # write_list = [f'{sub_merge_path}/sub_merge.txt', f'{sub_merge_path}/sub_merge_base64.txt', yaml_p]
        # content_type = (content, content_base64, content_yaml)
        # for index in range(len(write_list)):
        #     content_write(write_list[index], content_type[index])

        # # delete CN nodes
        # with open(yaml_p, 'rb') as f:
        #     old_data = yaml.load(f)
        # new_data = {'proxies': []}
        # for i in range(len(old_data['proxies'])):
        #     if 'CN' not in old_data['proxies'][i]['name']:
        #         new_data['proxies'].append(old_data['proxies'][i])
        # # print(len(new_data['proxies']))
        # with open(yaml_p, 'w', encoding='utf-8') as f:
        #     yaml.dump(new_data, f)
        # print('Done!\n')

    def read_list(self, json_file, split=False):  # 将 sub_list.json Url 内容读取为列表
        with open(json_file, 'r', encoding='utf-8') as f:
            raw_list = json.load(f)
        input_list = []
        for index in range(len(raw_list)):
            if raw_list[index]['enabled']:
                if split == False:
                    urls = re.split('\|', raw_list[index]['url'])
                else:
                    urls = raw_list[index]['url']
                raw_list[index]['url'] = urls
                input_list.append(raw_list[index])
        return input_list

    def geoip_update(self, url):
        print('Downloading Country.mmdb...')
        try:
            request.urlretrieve(url, './utils/Country.mmdb')
            print('Success!\n')
        except Exception:
            print('Failed!\n')

    def readme_update(self, readme_file='./README.md', sub_list=[]):  # 更新 README 节点信息
        print('更新 README.md 中')
        with open(readme_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            f.close()
        # 获得当前名单及各仓库节点数量
        thanks = []
        repo_amount_dic = {}
        for repo in sub_list:
            line = ''
            if repo['enabled'] == True:
                id = repo['id']
                remarks = repo['remarks']
                repo_site = repo['site']

                sub_file = f'./sub/list/{id:0>2d}.txt'
                with open(sub_file, 'r', encoding='utf-8') as f:
                    proxies = f.readlines()
                    if proxies == ['Url 解析错误'] or proxies == ['订阅内容解析错误']:
                        amount = 0
                    else:
                        amount = len(proxies)
                    f.close()
                repo_amount_dic.setdefault(id, amount)
                line = f'- [{remarks}]({repo_site}), 节点数量: `{amount}`\n'
            if remarks != "alanbobs999/TopFreeProxies":
                thanks.append(line)

        # 所有节点打印
        for index in range(len(lines)):
            if lines[index] == '## 所有节点\n':  # 目标行内容
                # 清除旧内容
                lines.pop(index + 1)  # 删除节点数量

                with open('./sub/sub_merge_yaml.yaml', 'r', encoding='utf-8') as f:
                    proxies = f.read()
                    proxies = proxies.split('\n- ')
                    top_amount = len(proxies) - 1

                lines.insert(index + 1, f'合并节点总数: `{top_amount}`\n')
                break
        # 节点来源打印
        for index in range(len(lines)):
            if lines[index] == '## 节点来源\n':
                # 清除旧内容
                while lines[index + 1] != '\n':
                    lines.pop(index + 1)

                for i in thanks:
                    index += 1
                    lines.insert(index, i)
                break

        # 写入 README 内容
        with open(readme_file, 'w', encoding='utf-8') as f:
            data = ''.join(lines)
            print('完成!\n')
            f.write(data)


if __name__ == '__main__':
    UpdateUrl().update_main()
    sm = SubMerge()
    # sm.geoip_update('https://raw.githubusercontent.com/Loyalsoldier/geoip/release/Country.mmdb')

    sub_list_remote = sm.read_list(sub_list_json, split=True)
    sm.sub_merge(sub_list_remote)
    sm.readme_update(readme, sub_list_remote)
