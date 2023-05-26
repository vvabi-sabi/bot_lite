import os
import threading
import telebot
import requests

import config
from dialog_manager.screens import ScreenManager
from dialog_manager.bot_utils import File

#TG_TOKEN = os.getenv("BoT_TOKEN")
TG_TOKEN = config.BOT_TOKEN

def run_bot(bot):
    try:
        bot.polling(none_stop = True)
    except Exception as e:
        if e == 'KeyboardInterrupt':
            return 0
        print('reboot bot', e)
        run_bot(bot)

def get_file(bot, message):
    file = File()
    if message.content_type == 'document':
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        file_request = requests.get(f'https://api.telegram.org/file/bot{TG_TOKEN}/{file_info.file_path}')
        if str(file_request) == '<Response [200]>':
            downloaded_file = bot.download_file(file_info.file_path)
            file_name = message.document.file_name
        else:
            downloaded_file = None
            file_name = None
    else:
        message.file_name = message.json['photo'][-1]['file_unique_id']+'.jpg'
        file_id = message.json['photo'][-1]['file_id']
        file_info = bot.get_file(file_id)
        file_request = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TG_TOKEN, file_info.file_path))
        if str(file_request) == '<Response [200]>':
            downloaded_file = bot.download_file(file_info.file_path)
            file_name = message.file_name
        else:
            downloaded_file = None
            file_name = None
    file.data = downloaded_file
    file.name = file_name
    return file


def extract_chat_data(message):
    try:
        return message.chat_id, message.text
    except:
        return message.chat.id, message.text


def edit_messages(bot, responder, mess):
    for text in responder.info_list:
        bot.edit_message_text(
                    chat_id=mess.chat.id,
                    message_id=mess.message_id,
                    text=text
                    )
    if os.path.isfile(responder.results_png):
        results_png = open(responder.results_png, 'rb')
        bot.send_photo(mess.chat.id,
                       results_png,
                       )

if __name__ == '__main__':
    bot = telebot.TeleBot(TG_TOKEN)
    sm = ScreenManager()
    
    @bot.message_handler(commands=['start'])
    def command_handler(message):
        chat_id, command = extract_chat_data(message)
        bot.send_chat_action(chat_id, 'typing')
        responder = sm.current_screen(chat_id, command)
        messages_list = responder.run()
        for text, keyboard in messages_list: #[(text1,keyboard1), (text2,keyboard2), ...]
            bot.send_message(
                        chat_id,
                        text=text,
                        reply_markup=keyboard
                        )
        print(responder.next_screen_name)
        sm.update_screen(chat_id, responder.next_screen_name)
    
    @bot.message_handler(content_types=['text'])
    def text_handler(message):
        chat_id, text = extract_chat_data(message)
        bot.send_chat_action(chat_id, 'typing')
        responder = sm.current_screen(chat_id, text)
        messages_list = responder.run()
        print('messages_list', messages_list)
        for text, keyboard in messages_list:
            mess = bot.send_message(
                        chat_id,
                        text=text,
                        reply_markup=keyboard
                        )
        sm.update_screen(chat_id, responder.next_screen_name)
        
        if sm.chats_dict[chat_id] == 'TrainScreen': # responder.__class__.__name__ == 'TrainScreen'
            responder = sm.current_screen(chat_id, '/train')
            t = threading.Thread(target=edit_messages, args = (bot, responder, mess), daemon=True)
            t.start()
            int8_tmfile_path = responder.train()
            if os.path.isfile(int8_tmfile_path):
                int8_tmfile = open(int8_tmfile_path, "rb")
                bot.send_document(chat_id, int8_tmfile)
                int8_tmfile.close()
    
    @bot.message_handler(content_types=['document','photo'])
    def doc_handler(message):
        chat_id, text = extract_chat_data(message)
        bot.send_chat_action(chat_id, 'typing')
        file = get_file(bot, message)
        responder = sm.current_screen(chat_id, file)
        messages_list = responder.run()
        for text, keyboard in messages_list:
            if text.endswith(('bmp', 'jpg', 'png', 'jpeg', 'JPG', 'JPEG')):
                photo = open(text, 'rb')
                bot.send_photo(message.chat.id, 
                           photo,
                           reply_markup=keyboard)
            else:
                bot.send_message(
                            chat_id,
                            text=text,
                            reply_markup=keyboard
                            )
        sm.update_screen(chat_id, responder.next_screen_name)
    
    run_bot(bot)
