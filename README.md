# Yolov5 telegram bot lite
# Install instruction
## 1. Install the Telegram-YOLO
```
git clone https://github.com/BelotserkovskiyVA/bot_lite.git
cd bot_lite/
pip install -r requirements.txt
```
## 2. Set a BOT_TOKEN into config.py

```
BOT_TOKEN = '12345:abcde' #Your_token
```
## 3. Install ultralytics/yolov5
```
git clone https://github.com/ultralytics/yolov5.git
```
## 4. Make changes to programs:  
```
cp yolov5m_leaky.pt yolov5/yolov5m_leaky.pt
cd yolov5/
pip install r requirements.txt
```
train_insertion.py -> train.py;
export_insertion.py -> export.py;
yolo_insertion.py -> yolo.py;
## 5. Start bot
```
cd ../
python3 main.py
```

