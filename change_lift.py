from Robot.sensor.lift import SerialLiftingMotor

#可能要改以下几个地方的升降机高度
# 初始化
# 识别处方单
# 抓取药品逻辑 三层 四层
# 放置药框

app = SerialLiftingMotor()
app.cmd_vel_callback(380)








