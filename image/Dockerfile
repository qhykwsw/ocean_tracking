# Base Images
FROM registry.cn-shanghai.aliyuncs.com/tcc-public/python:3

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

RUN pip install numpy==1.19.5
RUN pip install pandas==1.2.2
RUN pip install scipy==1.6.1
RUN pip install lightgbm==3.1.1
RUN pip install netCDF4==1.5.6

## 把当前文件夹里的文件构建到镜像的根目录下
ADD . /

## 指定默认工作目录为根目录（需要把run.sh和生成的结果文件都放在该文件夹下，提交后才能运行）
WORKDIR /
