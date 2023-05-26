import time

from dialog_manager import bot_utils
from dialog_manager.bot_utils import File, States, MessagesMaker

GROUP_MODE = False

class ScreenManager:

    def __init__(self):
        self.states = States()
        self.chats_dict = {} # {chat_id: ScreenName}

    def current_screen(self, user_id, user_data):
        # Если команда или файл, определяем текущего screen,
        # Если текст, то отдаем текущего screen как есть, а он уже разбирается
        # После ответа на текст, вызывается метод update_screen
        if isinstance(user_data, str):
            if user_data.startswith('/'):
                screen_name = self.states.command(user_data)
            else: # текст кнопки (отдаем текущего screen как есть)
                screen_name = self.chats_dict.get(user_id)
        elif isinstance(user_data, File):
            screen_name = self.states.document(user_data)
        self._update_chats_dict(user_id, screen_name)
        screen = ScreenBuilder().new(screen_name)
        if GROUP_MODE is True:
            user_id = 'common_project'
        screen.chat_id = user_id
        screen.user_data = user_data
        return screen

    def update_screen(self, user_id, next_screen):
        self._update_chats_dict(user_id, next_screen)

    def _get_screen(self, user_id):
        try:
            current_screen = self.get_state(user_id)
            return current_screen
        except:
            self._add_client(user_id)
            return self._get_screen(user_id)

    def get_state(self, user_id):
        return self.chats_dict[user_id] 
    
    def _update_chats_dict(self, user_id, screen):
        self.chats_dict[user_id] = screen

class ScreenBuilder:

    def __init__(self):
        self.screens_dict = {'user_text.lower()' : 'ScreenName',
                             }
        self.chat_id = None
        self._front_face = ('', []) # 'Hello world', ['text1', ('text2','text3'), ('...','...')]
        self.answers_list = []
        self.user_data = None # command/text/file
        self.next_screen_name = self.__class__.__name__
    
    def methods_call(self):
        return None

    def define_next_screen(self):
        '''
        determinate next screen name 
        '''
        try:
            user_text = self.user_data.lower()
            print('user_text', user_text)
            self.next_screen_name = self.screens_dict[user_text]
        except:
            # Если текст не совпал, то зацикливаемся (self.__class__.__name__). или переходим к next_screen_name 
            # self.next_screen_name = self.__class__.__name__
            pass

    def new(self, screen_name):
        return globals().get(screen_name)()
    
    @property
    def next_screen(self):
        return globals().get(self.next_screen_name)() # object
    
    def update_answer_list(self, answer):
        self.answers_list.append(answer)
    
    def reset_answer(self):
        self.answers_list = []
    
    def run(self):
        #self.chat_id и self.user_data уже добавил ScreenManager
        self.define_next_screen() # определили след. состояние
        self.update_answer_list(self.next_screen._front_face) # показали экран след. состояния
        self.update_answer_list(self.methods_call()) # ответили на запрос пользователя 
        answer_messages = MessagesMaker.adapter(self.answers_list)
        self.reset_answer()
        return answer_messages

class StartScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        #next_screen_name = self.screens_dict[user_text]
        self.screens_dict = {'файлы' : 'FilesMenu',
                             'тренировка' : 'TrainScreen',
                             '/info' : 'InfoScreen',
                            }
        text = 'Чтобы добавить данные для тренировки скиньте JSON-файлы.\n' +\
               'Чтобы оценить работу модели скиньте изображение.'
        self._front_face = (text, [('Файлы', 'Тренировка')])
        self._train_face = ('Дождитесь окончания.', None)
    
    def methods_call(self):
        if self.user_data.startswith('/'):
            return self.check_directory()
        elif self.user_data.lower() == 'файлы':
            text = bot_utils.get_files_list(str(self.chat_id))
            return text
        elif self.user_data.lower() == 'тренировка':
            return self._train_face
    
    def check_directory(self):
        if bot_utils.client_catalogs_exist(self.chat_id):
            return
        else:
            bot_utils.client_catalogs_create(self.chat_id)
            return

class GroupScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        text = 'Режим работы изменён.\n' +\
               'Скиньте JSON-файлы или изображение.'
        self._front_face = (text, [('Файлы', 'Тренировка')])
    
    def methods_call(self):
        global GROUP_MODE
        GROUP_MODE = not GROUP_MODE
        self.next_screen_name = 'StartScreen'
        return 'group mode '+('on' if GROUP_MODE else 'off')

class InfoScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        text = '1. Перед тренировкой необходимо разметить данные, т.е. обвести контурами интересующие объекты.\n \
2. Размечать лучше всего в программе labelme, которую можно скачать по ссылке\n\
https://disk.yandex.ru/d/-lmmiAIZUIrLYA\n \
3. После запуска программы откройте изображение (кнопка open), выберите инструмент Polygon \
и обведите объект контуром, стараясь точно следовать границе объекта. Укажите имя объекта (label).\n\
4. Сохранить размеченное изображение можно кнопкой "save". После чего должен появиться файл.json  \
в той же папке.\n\
5. Для обучения нейросети скиньте файл в этот чат и нажмите кнопку "Тренировка"'
        self._front_face = (text, [('Файлы', 'Тренировка')])
    
    def methods_call(self):
        self.next_screen_name = 'StartScreen'


class AppDownloadScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        text = 'Установите это приложение и размечайте файлы в своём мобильном.'
        self._front_face = (text, [('Файлы', 'Тренировка')])
        self.app_path = '/root/bot_lite/dialog_manager/app-release.apk'
    
    def methods_call(self):
        self.next_screen_name = 'StartScreen'
        #bot.send_document(message.chat.id, file_nef)
        return self.app_path


class MenuScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        self.screens_dict = {'файлы' : 'FilesMenu',
                             'тренировка' : 'TrainScreen',
                            }
        text = 'Меню:\n' +\
               'Скиньте JSON-файлы или изображение.'
        self._front_face = (text, [('Файлы', 'Тренировка')])
        self._train_face = ('Дождитесь окончания.', None)
    
    def methods_call(self):
        if self.user_data.lower() == 'файлы':
            text = bot_utils.get_files_list(str(self.chat_id))
            return text
        elif self.user_data.lower() == 'тренировка':
            return self._train_face
        return


class FilesMenu(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        self.screens_dict = {'назад' : 'MenuScreen',
                             'очистить' : 'FilesMenu',
                            }
        self._front_face = ('Список файлов:', [('назад', 'очистить')])
        
    def methods_call(self):
        if self.user_data.lower() == 'очистить':
            bot_utils.delete_project(self.chat_id)
            text = bot_utils.get_files_list(str(self.chat_id))
            return text
        return
    

class TrainScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        self.screens_dict = {'назад' : 'MenuScreen',
                            }
        self._front_face = ('Тренировка нейросети:', ['назад'])
        self.train_res = None
        self.results_png = None
    
    def train(self):
        self.train_res, self.results_png = bot_utils.train_yolo(self.chat_id)
        if self.results_png == '': #Тренировка не была запущена.
            return ''
        bot_utils.bestpt_copy(self.chat_id)
        bot_utils.pt2onnx(self.chat_id)
        bot_utils.onnx2tmfile(self.chat_id)
        quant_model_path = bot_utils.quantization(self.chat_id)
        return quant_model_path

    @property
    def info_list(self):
        time.sleep(15)
        info = '...'
        while True:
            if self.train_res is not None:
                break
            time.sleep(5)
            new_info = bot_utils.train_info(self.chat_id)
            if new_info == info:
                continue
            info = new_info
            yield info
        yield self.train_res

class DataScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        self.screens_dict = {'назад' : 'MenuScreen',
                            }
        self._front_face = ('Добавление файлов ... ', ['назад'])
    
    def methods_call(self):
        if isinstance(self.user_data, str):
            return
        if GROUP_MODE is True:
            self.user_data.name = bot_utils.random_file_name()
        res = bot_utils.save_file(self.user_data, self.chat_id)
        try:
            data_folder = bot_utils.choose_folder(self.chat_id) # куда сохранять конвертированные картинки/лэйблы
        except:
            return res
        res = bot_utils.convert_json(self.chat_id, self.user_data.name, data_folder)
        try:
            bot_utils.delete_file(self.chat_id, self.user_data.name)
        except:
            return res
        return res

class PhotoScreen(ScreenBuilder):
    
    def __init__(self):
        super().__init__()
        self.screens_dict = {'назад' : 'MenuScreen',
                            }
        self._front_face = ('Обработка изображения ... ', ['назад'])
        self.next_screen_name = 'MenuScreen'
    
    def methods_call(self):
        if isinstance(self.user_data, str):
            return
        bot_utils.save_file(self.user_data, self.chat_id)
        result_img = bot_utils.yolo_detect(self.chat_id, self.user_data.name)
        bot_utils.delete_file(self.chat_id, self.user_data.name)
        return result_img



















