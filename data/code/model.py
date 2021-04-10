import os
import argparse
import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime
from datetime import timedelta
import math
from math import radians, cos
from util import query_wind, query_current
import time
import warnings
warnings.filterwarnings('ignore')


# 计算与xx分钟之前位置的diff
def calculate_diff(data, diff_time, rolling_time, time_range):
    data.set_index('datetime', inplace=True)
    for i in range(time_range[0], time_range[1]):
        data['U10_{}'.format(i)] = data['U10_{}'.format(i)].rolling(rolling_time).mean()
        data['V10_{}'.format(i)] = data['V10_{}'.format(i)].rolling(rolling_time).mean()
        data['u_{}'.format(i)] = data['u_{}'.format(i)].rolling(rolling_time).mean()
        data['v_{}'.format(i)] = data['v_{}'.format(i)].rolling(rolling_time).mean()

    data['lng_diff'] = data['lng'].diff(diff_time).rolling(rolling_time).mean()
    data['lat_diff'] = data['lat'].diff(diff_time).rolling(rolling_time).mean()
    return data.iloc[diff_time:]


def in_area(lat, lng, in_fix_area, fix_area):
    if in_fix_area == 1:
        return in_fix_area
    lat1, lng1, lat2, lng2 = fix_area
    return 1 if lat<lat1 and lat>lat2 and lng>lng1 and lng<lng2 else 0


def first_point(data):
    return data.iloc[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="../prediction_result", help="path of output file")
    parser.add_argument("--diff_time", type=int, default=30, help="diff time")
    parser.add_argument("--rolling_time", type=str, default="1min", help="rolling time")
    parser.add_argument("--interpolation", type=str, required=True, choices=['cubic', 'linear'], help="use which interpolation method")
    parser.add_argument("--nearest_circle", type=int, default=3, help="interpolation range")
    parser.add_argument("--time_start", type=int, default=-4, help="start time")
    parser.add_argument("--time_end", type=int, default=4, help="end time")
    args = parser.parse_args()

    output_dir = args.output
    diff_time = args.diff_time
    rolling_time = args.rolling_time
    kind = args.interpolation
    nearest_circle = args.nearest_circle
    time_start = args.time_start
    time_end = args.time_end

    # 返回X小时前到X小时后此地的wind, current数据
    time_range = [time_start, time_end+1]


    # ./当前目录 ../上级目录
    data_path = '../user_data'
    save_path = '../prediction_result/'
    current_path = '../raw_data/current'
    wind_path = '../raw_data/wind'

    fix_areas = [
        [25.5412, 118.3832, 24.8304, 118.7072], # 陆地范围
        [29.1456, 121.8432, 29.1042, 121.9043], # 狭窄河道
        [25.3021, 121.5842, 25.2774, 121.6116], # 海岸沿线
        [25.7121, 119.6668, 25.5870, 119.8117], # 小岛周围
        [24.5794, 118.3682, 24.5504, 118.4046], # 海岸沿线
        [25.5139, 119.3264, 25.3949, 119.4568], # 海岸沿线
        [26.6806, 119.9127, 26.5627, 120.0555], # 海岸沿线
        [27.3498, 120.2203, 27.2436, 120.3534], # 狭窄河道
    ]

    # 训练数据
    data = pd.read_csv(os.path.join(data_path, 'train.csv'), parse_dates=['datetime'])
    data['in_fix_area'] = 0
    df = data.groupby('id').apply(first_point).reset_index(drop=True)
    for fix_area in fix_areas:
        df.loc[df.index, 'in_fix_area'] = df.apply(lambda x: in_area(x.lat, x.lng, x.in_fix_area, fix_area), axis = 1)
    data = data[data['id'].isin(df[df['in_fix_area']==0]['id'])]

    # 测试数据
    test = pd.read_csv('../raw_data/test.csv')
    test['datetime'] = test['date']+'-'+ test['time']
    test['datetime'] = test['datetime'].map(lambda x: datetime.strptime(x, '%Y-%m-%d-%H:%M'))
    test['in_fix_area'] = 0
    for fix_area in fix_areas:
        test.loc[test.index, 'in_fix_area'] = test.apply(lambda x: in_area(x.lat, x.lng, x.in_fix_area, fix_area), axis = 1)
    fix_ids = test[test['in_fix_area']==1]['id'].to_list()

    data = data.groupby('id').apply(calculate_diff, diff_time=diff_time, rolling_time=rolling_time, time_range=time_range).reset_index(level='id', drop=True)

    # 构建lat和东西向速度的组合特征
    data['lat_code'] = data['lat'].map(radians).map(cos)
    for i in range(time_range[0], time_range[1]):
        data['U10_{}'.format(i)] = data['U10_{}'.format(i)] / data['lat_code']
        data['u_{}'.format(i)] = data['u_{}'.format(i)] / data['lat_code']

    # 只用当下时刻的wind和current数据
    features_lng = ['U10_0', 'u_0']
    features_lat = ['V10_0', 'v_0']

    lgb_lng_params = {
        'random_state': 2021,
        'n_jobs': 4,
        'force_col_wise': True,
        'learning_rate': 0.1,
        'n_estimators': 200,
        'max_bin': 455,
        'num_leaves': 61,
        'max_depth': 13,
    }
    lgb_lat_params = {
        'random_state': 2021,
        'n_jobs': 4,
        'force_col_wise': True,
        'learning_rate': 0.1,
        'n_estimators':200,
        'max_bin': 475,
        'num_leaves': 61,
        'max_depth': 11,
    }


    target_lng = 'lng_diff'
    target_lat = 'lat_diff'

    train = data.copy()

    # 训练经度模型
    train_X, train_y = train[features_lng], train[target_lng]
    trn_data = lgb.Dataset(train[features_lng], label=train[target_lng], free_raw_data=False)
    lgb_lng = lgb.train(
        params=lgb_lng_params,
        train_set=trn_data,
    )
    # 训练纬度模型
    train_X, train_y = train[features_lat], train[target_lat]
    trn_data = lgb.Dataset(train[features_lat], label=train[target_lat], free_raw_data=False)
    lgb_lat = lgb.train(
        params=lgb_lat_params,
        train_set=trn_data,
    )

    rows_list = []
    for i in range(test.shape[0]):
        id = test.loc[i, 'id']
        lng = test.loc[i, 'lng']
        lat = test.loc[i, 'lat']
        date = test.loc[i, 'date']
        time = test.loc[i, 'time']
        datetime = test.loc[i, 'datetime']
        rows_list.append({'id':id, 'date':date, 'time':time, 'lng':lng, 'lat':lat, 'datetime':datetime})
        if id in fix_ids:
            for j in range(1, 96):
                datetime += timedelta(seconds=1800)
                date = datetime.strftime('%Y-%m-%d')
                time = datetime.strftime('%H:%M')
                rows_list.append({'id':id, 'date':date, 'time':time, 'lng':lng, 'lat':lat, 'datetime':datetime})
        else:
            for j in range(1, 2880):
                if j % diff_time == 0:
                    wind_list = query_wind(wind_path, datetime, lng, lat, nearest_circle, kind, time_range)
                    current_list = query_current(current_path, datetime, lng, lat, nearest_circle, kind, time_range)
                    lat_code = cos(radians(lat))

                    data_lng = pd.DataFrame([list(map(lambda x: x/lat_code, [wind_list[time_end*2], current_list[time_end*2]]))], columns=features_lng)
                    data_lat = pd.DataFrame([[wind_list[time_end*2+1], current_list[time_end*2+1]]], columns=features_lat)

                    predictions_lng = lgb_lng.predict(data_lng)[0]
                    predictions_lat = lgb_lat.predict(data_lat)[0]

                    lng += predictions_lng
                    lat += predictions_lat
                    datetime += timedelta(seconds=diff_time*60)
                    date = datetime.strftime('%Y-%m-%d')
                    time = datetime.strftime('%H:%M')
                    if j % 30 == 0:
                        rows_list.append({'id':id, 'date':date, 'time':time, 'lng':lng, 'lat':lat, 'datetime':datetime})

    submit = pd.DataFrame(rows_list)[['id', 'date', 'time', 'lng', 'lat']]
    submit.to_csv(os.path.join(output_dir, 'result.csv'), index=False, encoding="utf-8")
