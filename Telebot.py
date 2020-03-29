import requests
import telebot
import psycopg2
import math
import Constants


class Requester(object):
    @staticmethod
    def ask_weather(city):
        return requests.get(
            url=f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={Constants.API_KEY}').json()

    @staticmethod
    def convert_answer(name, city, temperature, sky, wind):
        if name != "":
            name = ', ' + name + '.'
        return f'Hello{name}\n' \
               f'Temperature in {city} is {math.ceil(temperature - 273)}°\n' \
               f'Sky: {sky}\n' \
               f'Wind speed is {wind} m/sec'


class Database(object):
    def __init__(self, db_name, user, password, host):
        self.__conn = psycopg2.connect(dbname=db_name, user=user, password=password, host=host)
        self.__conn.autocommit = True
        self.cursor = self.__conn.cursor()


DB = Database(Constants.DBNAME, Constants.DBUSERNAME, Constants.DBPASSWORD, Constants.HOST)
bot = telebot.TeleBot(Constants.TOKEN)
url = 'socks5h://' + Constants.USERNAME + ':' + Constants.PASSWORD + '@' + Constants.ADDRESS + ':' + Constants.PORT
telebot.apihelper.proxy = {
    'https': url,
    'http': url
}


def keyboard_ask(chat_id, dialogue_stage, question, info=""):
    keyboard = telebot.types.InlineKeyboardMarkup()
    key_yes = telebot.types.InlineKeyboardButton(text='Yes',
                                                 callback_data=dialogue_stage + 'yes' + info + '|delim|')
    key_no = telebot.types.InlineKeyboardButton(text='No',
                                                callback_data=dialogue_stage + ' no' + info + '|delim|')
    keyboard.add(key_yes, key_no)
    bot.send_message(chat_id, text=question, reply_markup=keyboard)


class CommandsHandler(object):
    @staticmethod
    @bot.message_handler(commands=['help'])
    def help(message):
        bot.send_message(message.chat.id, Constants.HELP)

    @staticmethod
    @bot.message_handler(commands=['weather'])
    def weather(message):
        DB.cursor.execute('SELECT name , city FROM users WHERE users.user_id = %s', (message.from_user.id,))
        DBresponse = DB.cursor.fetchone()
        if DBresponse is not None:
            name, city = DBresponse
            final_answer = ""
            try:
                server_response = Requester.ask_weather(city)
                final_answer = Requester.convert_answer(name,
                                                        city,
                                                        server_response['main']['temp'],
                                                        server_response['weather'][0]['description'],
                                                        server_response['wind']['speed'])
            except BaseException as ex:
                with open('log.txt', 'a')as file:
                    file.write(str(ex.args) + '\n')
                final_answer = 'Sorry, unable to complete request'

            bot.send_message(message.chat.id, final_answer)
        else:
            bot.send_message(message.chat.id, "Sorry, you haven't registered yet")

    @staticmethod
    @bot.message_handler(commands=['weather_in'])
    def weather_in(message):
        DB.cursor.execute('SELECT name FROM users WHERE users.user_id = %s', (message.from_user.id,))
        name = DB.cursor.fetchone()
        name = "" if name is None else name[0]
        # if name is None:
        #     name = ""
        # else:
        city = message.text[12:]
        final_answer = ""
        try:
            server_response = Requester.ask_weather(city)
            final_answer = Requester.convert_answer(name,
                                                    city,
                                                    server_response['main']['temp'],
                                                    server_response['weather'][0]['description'],
                                                    server_response['wind']['speed'])
        except BaseException as ex:
            with open('log.txt', 'a')as file:
                file.write(str(ex.args) + '\n')
            final_answer = 'Sorry, unable to complete request'

        bot.send_message(message.chat.id, final_answer)

    @staticmethod
    @bot.message_handler(commands=['start'])
    def start_message(message):
        bot.send_message(message.chat.id, Constants.HELP + '\n\\help for help')
        keyboard_ask(message.chat.id, 'S', 'Hello.\nDo you want to register?')

    @staticmethod
    @bot.message_handler(commands=['reg'])
    def reg(message):
        keyboard_ask(message.chat.id, 'S', 'Hello.\nDo you want to register?')


class RegistrationSteps(object):
    @staticmethod
    def learning_name(user_id):
        msg = bot.send_message(user_id, 'Please, introduce yourself.')
        bot.register_next_step_handler(msg, RegistrationSteps.checking_name)

    @staticmethod
    def checking_name(message):
        name = message.text
        keyboard_ask(message.chat.id, 'N', f'Your name is {name}, right?', name)

    @staticmethod
    def learning_city(chat_id, info):
        msg = bot.send_message(chat_id, 'Where do you live?')
        bot.register_next_step_handler(msg, RegistrationSteps.checking_city, info)

    @staticmethod
    def checking_city(message, info):
        city = message.text
        keyboard_ask(message.chat.id, 'C', f'You live in {city}, right?', info + city)

    @staticmethod
    def checking_city(message, info):
        city = message.text
        keyboard_ask(message.chat.id, 'C', f'You live in {city}, right?', info + city)

    @staticmethod
    @bot.callback_query_handler(func=lambda call: True)
    def button_handler(call):
        caller = call.data[0]
        answer = call.data[1:4]
        info = call.data[4:]
        if caller == 'S':
            if answer == 'yes':
                RegistrationSteps.learning_name(call.from_user.id)

        elif caller == 'N':
            if answer == 'yes':
                RegistrationSteps.learning_city(call.from_user.id, info)
            else:
                RegistrationSteps.learning_name(call.from_user.id)
        elif caller == 'C':
            if answer == 'yes':
                data = info.split('|delim|')
                DB.cursor.execute('DELETE FROM users WHERE users.user_id = %s', (call.from_user.id,))
                DB.cursor.execute('INSERT INTO users VALUES (%(user_id)s, %(name)s, %(city)s)',
                                  {'user_id': call.from_user.id, 'name': data[0], 'city': data[1]})
                bot.send_message(call.from_user.id, 'Thank you.\nRegistration is over.')


            else:
                RegistrationSteps.learning_city(call.from_user.id, info.split('|delim|')[0] + '|delim|')


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True)
        except BaseException as ex:
            with open('log.txt', 'a')as file:
                file.write(str(ex.args) + '\n')
