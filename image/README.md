## 镜像使用方法

#### 构建容器(两种方法均可)

* dockerfile
  在image目录下执行
  `docker build -t ocean:1.0 .`
* load tar文件
  `docker load -i ocean.tar`
  由于gitee容量限制，ocean.tar放在了百度云上，链接: https://pan.baidu.com/s/1W0gKJAQPkx-_QCHt4WbLaw 提取码: 1g5y

#### 运行模型

`docker run -v /home/xxx/xxx/data/:/data 镜像id sh run.sh`
