#!/bin/bash

# Exit on any failure.
set -e

ctrlc() {
	killall python
	mn -c
	exit
}

trap ctrlc INT

cd data/code

echo "make dataset"
# 利用16个进程制作数据集
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 0 --end 5169 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 5169 --end 10338 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 10338 --end 15507 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 15507 --end 20676 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 20676 --end 25845 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 25845 --end 31014 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 31014 --end 36183 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 36183 --end 41352 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 41352 --end 46521 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 46521 --end 51690 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 51690 --end 56859 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 56859 --end 62028 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 62028 --end 67197 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 67197 --end 72366 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 72366 --end 77535 & \
python make_dataset.py --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4 --start 77535 --end 82699

# 每隔60s检查一次, 直到16个子文件全部生成
while true
do
    i=0
    for a in $( seq 0 15 )
    do
        if [ -f "../user_data/train_$a.csv" ];then
            i=`expr $i + 1`
        fi
    done

    if [ $i -eq 16 ];then
        break
    fi
    sleep 60
done

# 将16个数据集合并为一个
echo "combine dataset"
python combine_dataset.py
sleep 1

# 开始训练模型并预测
echo "train model"
python model.py --diff_time 30 --rolling_time 15min --interpolation linear --nearest_circle 3 --time_start -4 --time_end 4
