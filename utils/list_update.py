#!/usr/bin/env python3

from datetime import timedelta, datetime
import json, re
import requests
from requests.adapters import HTTPAdapter

# 文件路径定义
sub_list_json = './sub/sub_list.json'

with open(sub_list_json, 'r', encoding='utf-8') as f:  # 载入订阅链接
    raw_list = json.load(f)
    f.close()


class UpdateUrl:
    def __init__(self):
        self.s = requests.Session()
        self.s.mount('http://', HTTPAdapter(max_retries=2))
        self.s.mount('https://', HTTPAdapter(max_retries=2))

    def url_judge(self, url):
        # 判断远程远程链接是否已经更新
        try:
            resp = self.s.get(url, timeout=2)
            status = resp.status_code
        except Exception:
            return False
        return True if status == 200 else False

    def update_main(self):
        for sub in raw_list:
            id = sub['id']
            current_url = sub['url']
            try:
                if sub['update_method'] != 'auto' and sub['enabled'] == True:
                    print(f'Finding available update for ID{id}')
                    if sub['update_method'] == 'change_date':
                        new_url = self.change_date(id, current_url)
                        if new_url == current_url:
                            print(f'No available update for ID{id}\n')
                        else:
                            sub['url'] = new_url
                            print(f'ID{id} url updated to {new_url}\n')
                    elif sub['update_method'] == 'page_release':
                        new_url = self.find_link(id, current_url)
                        if new_url == current_url:
                            print(f'No available update for ID{id}\n')
                        else:
                            sub['url'] = new_url
                            print(f'ID{id} url updated to {new_url}\n')
            except KeyError:
                print(f'{id} Url not changed! Please define update method.')

            updated_list = json.dumps(raw_list, sort_keys=False, indent=2, ensure_ascii=False)
            file = open(sub_list_json, 'w', encoding='utf-8')
            file.write(updated_list)
            file.close()

    def change_date(self, id, current_url):
        new_url = ''
        if id == 36:
            today = datetime.today().strftime('%Y%m%d')
            new_url = 'https://nodefree.org/dy/{}/{}.txt'.format(today[:6], today)
        if id == 0:
            today = datetime.today().strftime('%m%d')
            url_front = 'https://raw.githubusercontent.com/pojiezhiyuanjun/freev2/master/'
            url_end = '.txt'
            new_url = url_front + today + url_end

        if self.url_judge(new_url):
            return new_url
        else:
            return current_url

    def find_link(self, id, current_url):
        if id == 33:
            url_update = 'https://v2cross.com/archives/1884'
            if self.url_judge(url_update):
                resp = requests.get(url_update, timeout=5)
                raw_content = resp.text

                try:
                    raw_content = raw_content.replace('amp;', '')
                    pattern = re.compile(r'https://shadowshare.v2cross.com/publicserver/servers/temp/\w{16}')

                    new_url = re.findall(pattern, raw_content)[0]
                    return new_url
                except Exception:
                    return current_url
            else:
                return current_url


if __name__ == '__main__':
    UpdateUrl().update_main()
