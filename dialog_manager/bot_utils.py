import os
import shutil
import PIL
import base64
import io
import numpy as np
import json
import subprocess
import telebot

import yolov5.detect as detect
import yolov5.export as export

PRE_PATH = '/root/bot_lite'
VALID_DATA_PERCENTAGE = 0.2
BUSY = False

class EpochsLogger():
    
    def __init__(self):
        self.epochs_number = 300
        self.epoch = 0
        self.save_dir = ''
    
    def csv_file(self, chat_id):
        proj_dir = os.path.join(PRE_PATH, str(chat_id))
        result_dir = os.path.join(proj_dir,'train')
        exp = os.listdir(result_dir)
        if len(exp) == 0:
            return
        exp.sort()
        exp.sort(key=len)
        if '.ipynb' in exp[-1]:
            _ = exp.pop()
        exp = exp[-1]
        self.save_dir = os.path.join(result_dir, f'{exp}')
        csv_file = os.path.join(result_dir, f'{exp}', 'results.csv')
        return csv_file

    def current_epoch(self, chat_id):
        print('read results.csv')
        csv_file = self.csv_file(chat_id)
        with open(csv_file, newline='') as csvfile:
            log_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
            for row in log_reader:
                if row != []:
                    epoch = row[0]
        return int(epoch)

    def set_epochs(self, epochs):
        self.epochs_number = epochs


epochs_logger = EpochsLogger()

class File:
    
    def __init__(self):
        self.data = None
        self.name = None

class Folder:
    
    def __init__(self, path, file_number):
        self.path = path
        self.number = file_number

class States:
    
    def __init__(self):
        self.commands = {'/start' : 'StartScreen',
                         '/info' : 'InfoScreen',
                         '/app' : 'AppDownloadScreen',
                         '/train' : 'TrainScreen',
                         '/group': 'GroupScreen',
                        }
        self.buttons_text = {}
        self.docs = {'jpg' : 'PhotoScreen',
                     'jpeg' : 'PhotoScreen',
                     'png' : 'PhotoScreen',
                     'bmp' : 'PhotoScreen',
                     'JPG' : 'PhotoScreen',
                     'JPEG' : 'PhotoScreen',
                     'json' : 'DataScreen',
                     'yaml' : 'DataScreen',
                    }
    
    def command(self, command):
        return self.commands.get(command)
    
    def document(self, document):
        doc_name = document.name
        doc_type = doc_name.split('.')[1]
        return self.docs.get(doc_type)


class MessagesMaker:
    
    @staticmethod
    def reply_keyboard(buttons_data_list,
                                resize=True,
                                one_time = True):
        if buttons_data_list is None:
            return None
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=resize,
                                                     one_time_keyboard = one_time)
        for buttons_data in buttons_data_list: #[('Кнопка1',), ('Кнопка2','Кнопка3'), ('...')]
            if type(buttons_data) == type(()):
                button_text1, button_text2 = buttons_data[0], buttons_data[1]
                button1 = telebot.types.KeyboardButton(button_text1)
                button2 = telebot.types.KeyboardButton(button_text2)
                keyboard.row(button1, button2)
            else:
                button = telebot.types.KeyboardButton(buttons_data)
                keyboard.row(button)
        return keyboard
    
    def inline_keyboard(self):
        pass
    
    @staticmethod
    def adapter(messages_list):
        correct_message = []
        if isinstance(messages_list, str):
            return messages_list, None
        for message in messages_list:
            if isinstance(message, str):
                correct_message.append((message, None))
                continue
            if message is None:
                continue
            correct_message.append((message[0], MessagesMaker.reply_keyboard(message[1])))
        return correct_message

class J2Y:
    
    def __init__(self, project_dir = 'common_project', json_name = 'test.json'):
        self.flag_new_labels = False
        self.project_dir = os.path.join(PRE_PATH, project_dir) #./yolov5_bot_lite/777777
        self.dataset_dir = os.path.join(PRE_PATH, project_dir, 'dataset') # ./yolov5_bot_lite/777777/dataset
        self.json_name = json_name
        self.json = self.load_json(json_name)
    
    def load_json(self, json_name):
        path_to_load = os.path.join(self.project_dir, json_name)
        with open(path_to_load , "r") as read_file:
            loaded_json = json.load(read_file)
        return loaded_json
    
    def _save_annot(self, path_to_save): # path_to_save = dataset/train
        self.path_to_save = os.path.join(self.project_dir, path_to_save) #./yolov5_bot_lite/777777, /dataset/train
        _break, res = self.json_to_img()
        if _break:
            return res
        _break, res = self.json_to_labels()
        if _break:
            return res
        _break, res = self.save_yaml_config()
        if _break:
            return res
        res = f'Файл: {self.json_name} сохранен.'
        return res
    
    def json_to_img(self):
        img_name = self.json_name[:-5] + '.png'
        path_to_save = os.path.join(self.path_to_save, 'images', img_name)
        try:
            img_b64 = self.json['imageData']
            img_data = base64.b64decode(img_b64) 
            f = io.BytesIO()
            f.write(img_data)
            img_pil = PIL.Image.open(f)
            img_pil.save(path_to_save)
            return False, 'Изображение сохранено, label.txt - ещё нет.'
        except:
            return True, 'Возникли проблемы с сохранением изображения. Проверьте json "imageData".'
    
    def json_to_labels(self): # load_json, path_to_labels):
        lbl_name = self.json_name[:-5] + '.txt'
        labels_set = set()
        for shape in self.json['shapes']:
            labels_set.add(shape['label'])
        labels_list = self.get_labels(labels_set)
        if self.json['shapes'][0].get('points'):
            labels_data = self.poligon_to_box(labels_list)
        
        path_to_labels = os.path.join(self.path_to_save, 'labels', lbl_name)
        self.labels_list = labels_list
        try:
            with open(path_to_labels, 'w') as label_file:
                label_file.write(labels_data)
            return False, 'Файл аннотаций (label.txt) сохранен.'
        except:
            return True, 'Файл аннотаций (label.txt) НЕ сохранен! Проверьте данные.'
    
    def get_labels(self, labels_set):
        labels_list = list(labels_set)
        config_file = self.dataset_dir + '/custom.yaml'
        try:
            with open(config_file, 'r') as config:
                line = config.readlines()[-1]
                names = line[7:]
                names = names.replace("'", " ")
                names = names.replace("[", " ")
                names = names.replace("]", " ")
                names = names.replace(",", " ")
                base_labels = names.split()
        except:
            base_labels = []
        for new_label in labels_list:
            if new_label not in base_labels:
                self.flag_new_labels = True
                base_labels.append(new_label)
        return base_labels
    
    def poligon_to_box(self, labels_list):
        labels_data = ''
        for shape in self.json['shapes']:
            min_x = min_y = 10000
            max_x = max_y = 0
            label_name = shape['label']
            label = labels_list.index(label_name)
            for point in shape['points']:
                min_x = min(min_x, point[0])
                max_x = max(max_x, point[0])
                min_y = min(min_y, point[1])
                max_y = max(max_y, point[1])
            width = max_x - min_x
            height = max_y - min_y
            x_c = (min_x + width/2)/self.json['imageWidth']
            y_c = (min_y + height/2)/self.json['imageHeight']
            labels_data += f'{label} {x_c} {y_c} {width/self.json["imageWidth"]} {height/self.json["imageHeight"]}\n'
        return labels_data
    
    def save_yaml_config(self):
        nc = len(self.labels_list)
        # Yaml creation
        dataset_path = f"path: {self.dataset_dir}/\n"
        train_path = "train: train/images\n"
        val_path = "val: valid/images\n"
        class_number = f"nc: {nc}\n"
        class_name = f"names: {self.labels_list}"
        head = dataset_path+\
                train_path+\
                val_path+\
                class_number+\
                class_name
        path_to_config = self.dataset_dir + '/custom.yaml'
        try:
            with open(path_to_config, 'w') as config_file:
                config_file.write(head)
            return False, 'Конфигурационный файл сохранен.'
        except:
            return True, 'Конфигурационный файл НЕ был сохранен!'
        

def client_catalogs_exist(path):
    path = os.path.join(PRE_PATH, str(path))
    return os.path.exists(path)

def client_catalogs_create(path):
    user_directories = ['dataset', 'detect', 'train']
    data_directories = ['dataset/train', 'dataset/valid']
    type_data_dir = ['images', 'labels']
    path = os.path.join(PRE_PATH, str(path))
    os.mkdir(path)
    for directory in user_directories:
        user_dir = os.path.join(path, directory)
        os.mkdir(user_dir)
    for directory in data_directories:
        data_dir = os.path.join(path, directory)
        os.mkdir(data_dir)
        for img_lbl in type_data_dir:
            img_lbl_path =  os.path.join(data_dir, img_lbl)
            os.mkdir(img_lbl_path)
    return True

def get_files_list(path):
    train_folder, valid_folder = dataset_scan(path)
    m_name, _ = model_scan(path)
    if train_folder.number == 0:
        text = f'Dataset:\n      train : 0 imgs \n      valid : 0 imgs\nModel:\n      {m_name}'
    else:
        text = f'Dataset:\n      train : {train_folder.number} imgs \n      valid : {valid_folder.number} imgs\nModel:\n      {m_name}'
    
    return text

def random_file_name():
    alphabet = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    alphabet = [symb for symb in alphabet]
    new_name = np.random.choice(alphabet, size=(1,9), replace = True)
    new_name = list(new_name[0])
    new_name.append('.json')
    new_name = ''.join(new_name)
    return new_name


def save_file(file, path):
    data_dir = os.path.join(PRE_PATH, str(path))
    file_name = file.name
    path_to_save = os.path.join(data_dir, file_name)
    if client_catalogs_exist(path):
        try:
            with open(path_to_save, 'wb') as new_file:
                new_file.write(file.data)
            return 'Файл загружен, но не "сконвертирован", возможно, проблема с данными.'
        except:
            return 'Файл не был загружен. Попробуйте поменять название файла.'
    else:
        return 'Отсутствует директория пользователя. Для правильной работы бота нажмите /start ещё раз.'

def model_scan(path):
    models_name = 'yolov5m_leaky.pt'
    models_path = os.path.join(PRE_PATH, models_name)
    data_dir = os.path.join(PRE_PATH, str(path))
    if 'best.pt' in os.listdir(data_dir):
        models_name = 'best.pt'
        models_path = os.path.join(data_dir, models_name)
    return models_name, models_path 

def dataset_scan(path):
    path = os.path.join(PRE_PATH, str(path))
    train_folder = Folder('dataset/train', 0)
    valid_folder = Folder('dataset/valid', 0)
    data_directories = [train_folder, valid_folder]
    for folder in data_directories:
        data_dir = os.path.join(path, folder.path, 'images')
        folder.number = len(os.listdir(data_dir))
    return train_folder, valid_folder

def choose_folder(path):
    train_folder, valid_folder = dataset_scan(path)
    if train_folder.number == 0:
        return train_folder.path
    data_number = train_folder.number + valid_folder.number + 1
    to_valid = data_number*VALID_DATA_PERCENTAGE
    to_train = data_number*(1-VALID_DATA_PERCENTAGE)
    train_delta = to_train - train_folder.number
    valid_delta = to_valid - valid_folder.number
    if train_delta > valid_delta:
        return train_folder.path
    else:
        return valid_folder.path

def convert_json(proj_path, file_name, path_to_save): # path_to_save = 'dataset/train'
    j2y = J2Y(str(proj_path), file_name)
    result = j2y._save_annot(path_to_save)
    #result = f'Файл: {file_name} сохранен.'
    if j2y.flag_new_labels is True:
        result = result + f'\nДобавлены новые классы: {j2y.labels_list}'
    return result

def delete_file(path, file_name):
    path = os.path.join(PRE_PATH, str(path), file_name)
    os.remove(path)
    return

def delete_project(path):
    path = os.path.join(PRE_PATH, str(path))
    if os.path.isfile(os.path.join(path, 'best.pt')):
        os.remove(os.path.join(path, 'best.pt'))
    if os.path.isfile(os.path.join(path, 'dataset/custom.yaml')):
        os.remove(os.path.join(path, 'dataset/custom.yaml'))
    data_directories = ['dataset/train', 'dataset/valid']
    type_data_dir = ['images', 'labels']
    for directory in data_directories:
        data_dir = os.path.join(path, directory)
        for img_lbl in type_data_dir:
            img_lbl_path =  os.path.join(data_dir, img_lbl)
            #files = os.listdir(img_lbl_path)
            files = [f for f in os.listdir(img_lbl_path) if os.path.isfile(os.path.join(img_lbl_path, f))]
            for file_name in files:
                delete_path = os.path.join(img_lbl_path, file_name) 
                os.remove(delete_path)
            try:
                shutil.rmtree(os.path.join(img_lbl_path, '.ipynb_checkpoints'))
            except FileNotFoundError as e:
                print('No such file or directory')
    return 

def bestpt_copy(path):
    path = os.path.join(PRE_PATH, str(path))
    if os.path.isfile(os.path.join(path, 'best.pt')):
        os.remove(os.path.join(path, 'best.pt'))
    result_dir = os.path.join(path, 'train')
    exp = os.listdir(result_dir)
    if len(exp) == 0:
        return
    exp.sort()
    exp.sort(key=len)
    if '.ipynb' in exp[-1]:
        _ = exp.pop()
    exp = exp[-1]
    weights = os.path.join(result_dir, f'{exp}', 'weights', 'best.pt')
    shutil.copyfile(weights, path+'/best.pt')
    return

def train_yolo(path):
    global BUSY
    if BUSY is True:
        text = train_info()
        return f'В данный момент идет обучение чужой модели ({text}). \nДождитесь окончания.', '' # png_path
    epochs_n = 300 # get_epoch_n()
    proj_dir = os.path.join(PRE_PATH, str(path))
    weights = 'yolov5m_leaky.pt'
    batch = 16
    num_epochs = epochs_n
    result_dir = os.path.join(proj_dir,'train')
    data_dir = os.path.join(proj_dir,'dataset')
    config_dir = os.path.join(data_dir,'custom.yaml')
    model_dir = os.path.join(PRE_PATH, 'yolov5/models/yolov5m.yaml')
    #_, weights = model_scan(path) Всегда начинаем тренировку с 'yolov5m_leaky.pt'
    weights = 'yolov5m_leaky.pt'
    freeze = 10
    if len(os.listdir(os.path.join(data_dir,'valid/labels'))) <= 1:
        return 'Добавьте ещё данных. Тренировка не была запущена.', '' # png_path
    BUSY = True
    savedPath = os.getcwd()
    os.chdir('/root/bot_lite/yolov5/')
    command = '/root/bot_lite/yolov5/train.py'
    params = f'--weights {weights} --data {config_dir} --cfg {model_dir} --batch {batch} --freeze {freeze} --epochs {num_epochs} --project {result_dir}'
    popen = subprocess.Popen('python3 '+ command +' ' +  params, executable='/bin/bash', shell=True)
    popen.wait()
    os.chdir(savedPath)
    BUSY = False
    png_path = os.path.join(epochs_logger.save_dir, 'results.png')
    return 'Обучение закончено. Модель "best.pt" обновилась. \nЧерез минуту я пришлю квантованную модель.', png_path

def train_info(path):
    current_epoch = epochs_logger.current_epoch(path)
    epochs_number = epochs_logger.epochs_number
    train_text = f'Количество эпох {current_epoch} из {epochs_number}'
    return train_text

def yolo_detect(path, file_name):
    proj_dir = os.path.join(PRE_PATH, str(path))
    weights = 'yolov5m_leaky.pt'
    result_dir = os.path.join(PRE_PATH, 'runs', 'detect')
    if os.path.isfile(os.path.join(proj_dir, 'best.pt')):
        weights = os.path.join(proj_dir, 'best.pt')
        result_dir = os.path.join(proj_dir,'detect')
    opt = detect.parse_opt()
    opt.weights = weights
    opt.iou_thres = 0.25
    opt.source = os.path.join(proj_dir, file_name) # path_to_source_img
    opt.project = result_dir
    opt.name = 'exp'
    detect.main(opt)
    
    result_path = os.listdir(result_dir)
    result_path.sort()
    result_path.sort(key=len)
    result_path = os.path.join(result_dir, result_path[-1], file_name)
    return result_path

def pt2onnx(path):
    proj_dir = os.path.join(PRE_PATH, str(path))
    weights_path = os.path.join(proj_dir, 'best.pt')
    config_file = os.path.join(proj_dir,'dataset','custom.yaml')
    opt = export.parse_opt()
    opt.weights = weights_path
    opt.data = config_file
    opt.opset = 11
    export.main(opt)
    onnx_path = os.path.join(proj_dir, 'best.onnx')
    return onnx_path

def onnx2tmfile(path):
    '''
        -f onnx 
        -m input model (best.onnx)
        -o output model (best.tmfile)

    '''
    proj_dir = os.path.join(PRE_PATH, str(path))
    onnx_path = os.path.join(proj_dir, 'best.onnx')
    tmfile_path = os.path.join(proj_dir, 'best.tmfile')
    args = ('/path/to/convert_tool/convert_tool',
                '-f', 'onnx',
                '-m', onnx_path,
                '-o', tmfile_path)
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    print('process', popen.returncode)
    return tmfile_path

def quantization(path):
    proj_dir = os.path.join(PRE_PATH, str(path))
    input_img = os.path.join(proj_dir, 'dataset', 'train', 'images') #'/path/to/img_calib'
    
    model_input_path = os.path.join(proj_dir, 'best.tmfile')
    model_output_path = os.path.join(proj_dir, 'best_int8.tmfile')

    args = ('/path/to/quant_tool/quant_tool_uint8',
                      '-m', model_input_path,
                      '-i', input_img,
                      '-o', model_output_path,
                      '-g', '3,352,352',
                      '-a', '0',
                      '-w', '0,0,0',
                      '-s', '0.003921,0.003921,0.003921',
                      '-c', '0',
                      '-t', '4',
                      '-b', '1',
                      '-k', '1',
                      '-y', '352,352'
                     )
    popen = subprocess.Popen(args, stdout=subprocess.PIPE)
    popen.wait()
    return model_output_path