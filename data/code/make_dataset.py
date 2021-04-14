import os
import argparse
import pandas as pd
import numpy as np
import time
from datetime import datetime
from util import query_wind, query_current
import warnings
warnings.filterwarnings('ignore')


# 根据经纬度和时间查询出所在区域的wind信息
def create_dataset(data, data_path, wind_path, current_path, nearest_circle, kind, time_range, start, end):
    num = data.shape[0]
    for i in range(start, end):
        date = data.loc[i, 'date']
        time = data.loc[i, 'time']
        lng = data.loc[i, 'lng']
        lat = data.loc[i, 'lat']
        datetime = data.loc[i, 'datetime']
        wind_list = query_wind(wind_path, datetime, lng, lat, nearest_circle, kind, time_range)
        current_list = query_current(current_path, datetime, lng, lat, nearest_circle, kind, time_range)

        for k, j in enumerate(range(time_range[0], time_range[1])):
            data.loc[i, 'U10_{}'.format(j)] = wind_list[2*k]
            data.loc[i, 'V10_{}'.format(j)] = wind_list[2*k+1]
            data.loc[i, 'u_{}'.format(j)] = current_list[2*k]
            data.loc[i, 'v_{}'.format(j)] = current_list[2*k+1]

    data.iloc[start:end].to_csv(os.path.join(data_path, 'train_{}.csv'.format(start//5169)), index=False)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="../user_data", help="path of output file")
    parser.add_argument("--interpolation", type=str, required=True, choices=['cubic', 'linear'], help="use which interpolation method")
    parser.add_argument("--nearest_circle", type=int, default=3, help="interpolation range")
    parser.add_argument("--time_start", type=int, default=-4, help="start time")
    parser.add_argument("--time_end", type=int, default=4, help="end time")
    parser.add_argument("--start", type=int, help="start")
    parser.add_argument("--end", type=int, help="end")
    args = parser.parse_args()

    output_dir = args.output
    kind = args.interpolation
    nearest_circle = args.nearest_circle
    time_start = args.time_start
    time_end = args.time_end
    start = args.start
    end = args.end

    # 返回4小时前到4小时后此地的wind, current数据
    time_range = [time_start, time_end+1]

    raw_data_path = '../raw_data'
    current_path = '../raw_data/current'
    wind_path = '../raw_data/wind'

    # id: 人员编码, date & time: 定位时间, lat: 纬度, lng: 经度
    train = pd.read_csv(os.path.join(raw_data_path, 'train.csv'))
    test = pd.read_csv(os.path.join(raw_data_path, 'test.csv'))

    train['datetime'] = train['date']+'-'+ train['time']
    train['datetime'] = train['datetime'].map(lambda x: datetime.strptime(x, '%Y-%m-%d-%H:%M'))

    create_dataset(train, output_dir, wind_path, current_path, nearest_circle, kind, time_range, start, end)
