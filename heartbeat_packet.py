import configparser

import cv2
import requests
import json
import time
import yuketang_video_downloader

config = configparser.ConfigParser()
config.read('config.ini')

# credentials
university_id = config.get('credentials', 'university_id')
classroom_id = config.get('credentials', 'classroom_id')
sign = config.get('credentials', 'sign')
term = config.get('credentials', 'term')

# header
user_agent = config.get('header', 'user-agent')
cookie = config.get('header', 'cookie')
xtbz = config.get('header', 'xtbz')
content_type = config.get('header', 'content-type')

# urls
urls = config['urls']
base_url = urls.get('base_url')
heartbeat_url = urls.get('heartbeat_url').format(base_url=base_url)

user_id = yuketang_video_downloader.user_id
course_id = yuketang_video_downloader.course_id
video_ids = yuketang_video_downloader.video_ids
video_urls = yuketang_video_downloader.video_urls

for video_id in video_ids:
    headers = {
        'user-agent': user_agent,
        'cookie': cookie,
        'origin': base_url,
        'referer': video_urls[video_ids.index(video_id)],
        'xtbz': xtbz,
        'content-type': content_type
    }


    def get_video_info(video_id):
        '''
        获取视频部分信息
        :param video_id: 视频 ID
        :return: 包含视频 SKU ID, ccid 和视频名称的元组
        '''
        video_info_url = urls.get('video_info_url').format(base_url=base_url,
                                                           classroom_id=classroom_id,
                                                           video_id=video_id,
                                                           sign=sign, term=term,
                                                           university_id=university_id)
        video_info = requests.get(video_info_url, headers=headers)
        video_info.encoding = video_info.apparent_encoding
        data = json.loads(video_info.text)['data']
        sku_id = data['sku_id']
        cc = data['content_info']['media']['ccid']
        video_name = data['name']
        return sku_id, cc, video_name


    def get_video_len(video_id):
        '''
        获取视频长度
        :param video_id: 视频 ID
        :return: 视频时长（以秒为单位）
        '''
        video_play_url = urls.get('video_play_url').format(base_url=base_url,
                                                           _date=str(int(time.time() * 1000)),
                                                           video_id=get_video_info(video_id)[1])
        video_play = requests.get(video_play_url, headers=headers)
        video_play.encoding = video_play.apparent_encoding
        try:
            video_play = json.loads(video_play.text)['data']['playurl']['sources']['quality10'][0]
        except:
            video_play = json.loads(video_play.text)['data']['playurl']['sources']['quality20'][0]
        cap = cv2.VideoCapture(video_play)
        if cap.isOpened():
            fps = cap.get(5)
            framenum = cap.get(7)
            duration = int(framenum / fps)
            return duration
        else:
            return 0


    sku_id, cc, video_name = get_video_info(video_id)
    d = get_video_len(video_id)

    # 心跳包模板，包含通用的信息
    template = {
        'c': course_id,  # 课程ID
        'cards_ed': 0,  # 固定设置为0
        'cc': cc,  # 每个视频的特定参数
        'classroomid': classroom_id,  # 教室ID
        'cp': 0,  # 当前播放时长
        'd': d,  # 总时长
        'et': '',  # 心跳包类型
        'fp': 0,  # 视频起始播放位置
        'i': 5,  # 固定设置为5
        'lob': 'cloud4',  # 固定设置为”cloud4“
        'n': 'ali-cdn.xuetangx.com',  # 固定设置为”ali-cdn.xuetangx.com“
        'p': 'web',  # 固定设置为”web“
        'pg': video_id + '_ro1f',  # 视频id_随机字符串
        'skuid': sku_id,  # SKU ID
        'slide': 0,  # 固定设置为0
        'sp': 1,  # 播放速度
        'sq': 0,  # 心跳包序列号
        't': 'video',  # 固定设置为”video“
        'tp': 0,  # 上一次看视频的播放位置
        'ts': int(time.time() * 1000),  # 时间戳，标识事件发生的时间戳
        'u': user_id,  # 用户ID
        'uip': '',  # 固定设置为”“
        'v': video_id,  # 视频ID
        'v_url': ''  # 固定设置为”“
    }

    rate_url = urls.get('rate_url').format(base_url=base_url,
                                           course_id=course_id,
                                           user_id=user_id,
                                           classroom_id=classroom_id,
                                           video_id=video_id,
                                           university_id=university_id)
    while True:
        rate = requests.get(rate_url, headers=headers)
        rate.encoding = rate.apparent_encoding
        rate = json.loads(rate.text)[video_id]['completed']
        if rate == 1:
            print(f'视频<{video_name}>已看完')
            break
        else:
            # 1. 发送空的心跳包
            requests.post(heartbeat_url, headers=headers, data=json.dumps({"heart_data": []}))

            '''
            loadstart --> seeking --> loadeddata --> play --> playing --> heartbeat --> ... ---> heartbeat  (size(heartbeat)=10) [发送]
            --> heartbeat --> heartbeat --> ... ---> heartbeat  (size(heartdata)=10) [发送]
            --> heartbeat --> heartbeat --> ... ---> heartbeat  (size(heartdata)=10) [发送]
            --> heartbeat --> heartbeat --> ... ---> heartbeat  (size(heartdata)=10) [发送]
            ...
            --> pause --> videoend [发送]
            '''

            # 2. 构建新的心跳包
            heart_data = []
            # 2.1 添加初始心跳包数据
            for etype, sq in [('loadstart', 1), ('seeking', 2), ('loadeddata', 3), ('play', 4), ('playing', 5)]:
                data = template.copy()
                data['et'] = etype
                data['sq'] = sq
                heart_data.append(data)
            sq = 6
            # 2.2 生成心跳包序列并发送
            for i in range(0, d, 5):
                # 2.2.1 迭代生成心跳包
                hb = template.copy()
                hb['et'] = 'heartbeat'
                hb['cp'] = i
                hb['sq'] = sq
                heart_data.append(hb)
                sq += 1
                if len(heart_data) == 10:  # 累积了一定数量的心跳包（10）
                    # 2.2.2 发送心跳包
                    send = requests.post(heartbeat_url, headers=headers, data=json.dumps({'heart_data': heart_data}))
                    try:
                        rate = requests.get(rate_url, headers=headers)
                        rate = json.loads(rate.text)
                        percentage = float(rate[video_id]['rate']) * 100
                        print('{} 观看进度:{.2f}%'.format(video_name, percentage))
                    except:
                        pass
                    # 2.2.3 清空心跳包列表
                    heart_data.clear()
                    time.sleep(1)
            # 3. 添加结束心跳包数据
            for etype in ['heartbeat', 'pause', 'videoend']:
                data = template.copy()
                data['et'] = etype
                data['cp'] = d
                data['sq'] = sq
                heart_data.append(data)
            requests.post(heartbeat_url, headers=headers, data=json.dumps({'heart_data': heart_data}))
