import os
import pandas as pd
import numpy as np
import netCDF4 as nc
from datetime import datetime
from datetime import timedelta
import math
from math import radians, cos, sin, asin, sqrt, floor
from scipy import interpolate
import time


# 插值
def interpolate_points(lngs, lats, value, center_lng, center_lat, kind):
    func = interpolate.interp2d(lngs, lats, value, kind=kind)
    center_value = func(center_lng, center_lat)
    return center_value[0]


# 根据经纬度计算距离
def geodistance(lng1, lat1, lng2, lat2):
    lng1, lat1, lng2, lat2 = map(radians, [float(lng1), float(lat1), float(lng2), float(lat2)])
    dlng = lng2-lng1
    dlat = lat2-lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    distance = 2 * asin(sqrt(a)) * 6371.393 * 1000
    distance = round(distance, 5)
    return distance


# @pysnooper.snoop('./log/file.log')
def nearest_wind_points(wind_obj, center_lng, center_lat, time_idx, nearest_circle, kind, time_range):
    LONGITUDE1_151 = wind_obj.variables['LONGITUDE1_151'][:]
    LATITUDE1_151 = wind_obj.variables['LATITUDE1_151'][:]
    U10 = wind_obj.variables['U10'][:]
    V10 = wind_obj.variables['V10'][:]

    # 找到离该点最近的西南角wind网格位置
    floor_lat = floor((center_lat-10)/0.2)
    floor_lng = floor((center_lng-105)/0.2)

    # 插值范围为该点左右nearest_circle, 上下nearest_circle
    lat_bottom, lat_top, lng_bottom, lng_top = floor_lat-nearest_circle+1, floor_lat+nearest_circle+1, floor_lng-nearest_circle+1, floor_lng+nearest_circle+1
    lat_idx = np.arange(lat_bottom, lat_top)
    lng_idx = np.arange(lng_bottom, lng_top)

    return_list = []

    # 返回X小时前, 当前时刻, X小时后此地的wind数据
    for i in range(time_range[0], time_range[1]):
        U10_l = U10[time_idx+i, lat_bottom:lat_top, lng_bottom:lng_top].flatten()
        V10_l = V10[time_idx+i, lat_bottom:lat_top, lng_bottom:lng_top].flatten()
        return_list.append(interpolate_points(LONGITUDE1_151[lng_idx], LATITUDE1_151[lat_idx], U10_l, center_lng, center_lat, kind=kind))
        return_list.append(interpolate_points(LONGITUDE1_151[lng_idx], LATITUDE1_151[lat_idx], V10_l, center_lng, center_lat, kind=kind))

    return return_list


# 根据经纬度和时间查询出所在区域的wind信息
def query_wind(wind_path, datetime, lng, lat, nearest_circle, kind, time_range):
    datetime -= timedelta(1)
    date = datetime.strftime('%Y%m%d')
    wind_file = 'wind_hour_{}12.nc'.format(date)
    if os.path.exists(os.path.join(wind_path, wind_file)):
        wind_obj = nc.Dataset(os.path.join(wind_path, wind_file))
        time_idx = datetime.hour+4
    else:  # 如果文件缺失, 需要再往前倒腾一天
        datetime -= timedelta(1)
        date = datetime.strftime('%Y%m%d')
        wind_file = 'wind_hour_{}12.nc'.format(date)
        wind_obj = nc.Dataset(os.path.join(wind_path, wind_file))
        time_idx = datetime.hour+28

    return_list = nearest_wind_points(wind_obj, lng, lat, time_idx, nearest_circle, kind, time_range)
    return return_list


def nearest_current_points(current_obj_1, current_obj_2, center_lng, center_lat, time_idx, nearest_circle, kind, time_range):
    u_1 = current_obj_1.variables['u']
    v_1 = current_obj_1.variables['v']
    u_2 = current_obj_2.variables['u']
    v_2 = current_obj_2.variables['v']
    u = np.concatenate((u_1, u_2), axis=0)
    v = np.concatenate((v_1, v_2), axis=0)

    lng = current_obj_1.variables['lon'][:]
    lat = current_obj_1.variables['lat'][:]
    locations = pd.DataFrame({'lng':lng.flatten(), 'lat':lat.flatten()})

    locations['distance'] = locations.apply(lambda x: geodistance(x.lng, x.lat, center_lng, center_lat), axis = 1)

    df = locations.loc[locations['distance'].nsmallest(nearest_circle*nearest_circle*4).index]
    df['idx'] = df.index

    return_list = []

    for i in range(time_range[0], time_range[1]):
        df['u_{}'.format(i)] = df.apply(lambda x: u[time_idx+i, 0, int(x.idx//321), int(x.idx%321)], axis = 1)
        df['v_{}'.format(i)] = df.apply(lambda x: v[time_idx+i, 0, int(x.idx//321), int(x.idx%321)], axis = 1)
        df['u_{}'.format(i)] = df['u_{}'.format(i)].astype(float)
        df['v_{}'.format(i)] = df['v_{}'.format(i)].astype(float)
        return_list.append(interpolate_points(df['lng'], df['lat'], df['u_{}'.format(i)], center_lng, center_lat, kind=kind))
        return_list.append(interpolate_points(df['lng'], df['lat'], df['v_{}'.format(i)], center_lng, center_lat, kind=kind))

    return return_list


# 根据经纬度和时间查询出所在区域的current信息
def query_current(current_path, datetime, lng, lat, nearest_circle, kind, time_range):
    # 如果是0点-9点之间需要找寻一天前的水流预报
    if datetime.hour < 9:
        datetime -= timedelta(1)
        current_file_1 = 'current_hour_{}.nc'.format(datetime.strftime('%Y%m%d'))
        current_obj_1 = nc.Dataset(os.path.join(current_path, current_file_1))
        time_idx = datetime.hour+13
        # 再取第二天的数据拼接到后面, 防止在边界上出现超过数组长度的情况
        datetime += timedelta(1)
        current_file_2 = 'current_hour_{}.nc'.format(datetime.strftime('%Y%m%d'))
        current_obj_2 = nc.Dataset(os.path.join(current_path, current_file_2))
    # 如果是9点之后需要找寻当天的水流预报
    else:
        date = datetime.strftime('%Y%m%d')
        current_file_2 = 'current_hour_{}.nc'.format(datetime.strftime('%Y%m%d'))
        current_obj_2 = nc.Dataset(os.path.join(current_path, current_file_2))
        time_idx = datetime.hour-9+24
        datetime -= timedelta(1)
        current_file_1 = 'current_hour_{}.nc'.format(datetime.strftime('%Y%m%d'))
        current_obj_1 = nc.Dataset(os.path.join(current_path, current_file_1))

    return_list = nearest_current_points(current_obj_1, current_obj_2, lng, lat, time_idx, nearest_circle=nearest_circle, kind=kind, time_range=time_range)
    return return_list
