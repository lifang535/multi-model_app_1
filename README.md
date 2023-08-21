# multi-model_app_1
This is a test of multi-model_app.

updated version of multi-model_application:
https://github.com/lifang535/multi-model_application/tree/main

## 更新内容

`Model_2` 模型换为 `'google/vit-base-patch16-224'` 进行车辆的图像分类

`Model_3` 模型换为 `'nateraw/vit-age-classifier'` 进行行人年龄检测

为请求设置结构体打包并合理编号，传输数据由 `path` 改为 `image_array`

`Model_4` 打包单个视频帧的处理信息并同时处理

传输数据的渠道由相邻模块公用 `list` 改为公用 `queue`

`latency` 监测


