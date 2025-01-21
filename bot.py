import random
import telebot
from PIL import Image, ImageOps
import io
from telebot import types
from TOKEN import TOKEN

bot = telebot.TeleBot(TOKEN)

# Словарь для хранения информации о текущих действиях пользователей
user_states = {}

# разделяет шутки из txt файла
jokes = []
with open('jokes_list.txt', 'r', encoding='utf-8') as file:
    for line in file:
        line = line.strip()
        fields = line.split('\n')
        jokes.append(fields)

# Набор символов, из которых составляется изображение в ASCII-арт
ASCII_CHARS = '@%#*+=-:. '

# Функция изменения размера изображения
def resize_image(image, new_width=100):
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))

# Функция преобразования изображения в оттенки серого
def grayify(image):
    return image.convert("L")

# Функция преобразования изображения в ASCII-арт
def image_to_ascii(image_stream, ascii_chars,new_width=40):
    # Переводим изображение в оттенки серого
    image = Image.open(image_stream).convert('L')

    # Меняем размер изображения, сохраняя пропорции
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(
        aspect_ratio * new_width * 0.55)  # 0,55 так как буквы выше чем шире
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized, ascii_chars)
    img_width = img_resized.width

    # Ограничиваем максимальное количество символов в сообщении
    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art

# Функция преобразования пикселей изображения в ASCII-символы
def pixels_to_ascii(image, ascii_chars):
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += ascii_chars[pixel * len(ascii_chars) // 256]
    return characters


# Функция пикселизации изображения
def pixelate_image(image, pixel_size):
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image

# Функция инверсии цветов изображения
def invert_color(image):
    inverted_image = ImageOps.invert(image)
    return inverted_image

# Функция преобразования картинки в тепловую карту
def convert_to_heatmap(image):
    gray_image = grayify(image)
    heatmap = ImageOps.colorize(gray_image, "blue", "red")
    return heatmap

# Функция для уменьшения размера изображения, сохраняя пропорции
def resize_for_sticker(image, max_size=512):
    image.thumbnail((max_size, max_size))
    return image

# Функция случайной шутки
def random_joke():
    random_joke = random.choice(jokes)
    return random_joke

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Пришлите мне изображение, и я предложу вам варианты!"
                          "\nТак же мы можете написать /joke и получить случайную шутку.")

@bot.message_handler(commands=['joke'])
def send_joke(message):
    bot.send_message(message.chat.id, random_joke())

@bot.message_handler(content_types=['photo', 'text'])
def handle_photo_or_text(message):
    if message.content_type == 'photo':
        bot.reply_to(message, "У меня есть твое фото! Пожалуйста, выберите, что вы хотите с ним сделать.",
                     reply_markup=get_options_keyboard())
        user_states[message.chat.id] = {'photo': message.photo[-1].file_id}
    elif message.content_type == 'text' and 'custom_ascii' in user_states[message.chat.id]:
        user_states[message.chat.id]['custom_ascii_chars'] = message.text
        bot.reply_to(message, "Получили свои собственные символы ASCII! "
                              "Теперь я конвертирую ваше изображение в формат ASCII.")
        ascii_and_send(message)

def get_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Пикселизация", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    custom_ascii_btn = types.InlineKeyboardButton("Пользовательский ASCII Art", callback_data="custom_ascii")
    invert_color_btn = types.InlineKeyboardButton("Инвертировать цвет", callback_data="invert_color")
    mirror_btn = types.InlineKeyboardButton("Зеркало", callback_data="mirror")
    heatmap_btn = types.InlineKeyboardButton("Тепловая карта", callback_data="heatmap")
    resize_btn = types.InlineKeyboardButton("Измените размер для стикера", callback_data="resize")
    keyboard.add(pixelate_btn, ascii_btn, custom_ascii_btn, invert_color_btn, mirror_btn, heatmap_btn, resize_btn)
    return keyboard

def mirror_options_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    mirror_horizontal_btn = types.InlineKeyboardButton("Горизонтально", callback_data="mirror_horizontal")
    mirror_vertical_btn = types.InlineKeyboardButton("Вертикально", callback_data="mirror_vertical")
    keyboard.add(mirror_horizontal_btn, mirror_vertical_btn)
    return keyboard

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Пикселизация вашего изображения...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.answer_callback_query(call.id, "Преобразование вашего изображения в формат ASCII art...")
        ascii_and_send(call.message)
    elif call.data == "custom_ascii":
        bot.answer_callback_query(call.id, "Пожалуйста, присылайте свои собственные символы ASCII.")
        user_states[call.message.chat.id]['custom_ascii'] = True
    elif call.data == "invert_color":
        bot.answer_callback_query(call.id, "Изменение цвета вашего изображения...")
        invert_color_and_send(call.message)
    elif call.data == "mirror":
        bot.answer_callback_query(call.id, "Выберите опцию зеркального отображения.")
        bot.send_message(call.message.chat.id, "Выберите, как отразить ваше изображение в зеркале:",
                         reply_markup=mirror_options_keyboard())
    elif call.data == "mirror_horizontal":
        bot.answer_callback_query(call.id, "Зеркальное отображение вашего изображения по горизонтали...")
        user_states[call.message.chat.id]['mirror_horizontal'] = True
        mirror_and_send(call.message)
    elif call.data == "mirror_vertical":
        bot.answer_callback_query(call.id, "Зеркальное отображение вашего изображения по вертикали...")
        user_states[call.message.chat.id]['mirror_vertical'] = True
        mirror_and_send(call.message)
    elif call.data == "heatmap":
        bot.answer_callback_query(call.id, "Преобразование вашего изображения в тепловую карту...")
        heatmap_and_send(call.message)
    elif call.data == "resize":
        bot.answer_callback_query(call.id, "Изменение размера вашего изображения для наклейки...")
        resize_and_send(call.message)


def pixelate_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)

    pixelated = pixelate_image(image, 20)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def ascii_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)

    ascii_chars = ASCII_CHARS
    if 'custom_ascii_chars' in user_states[message.chat.id]:
        ascii_chars = user_states[message.chat.id]['custom_ascii_chars']
        user_states[message.chat.id].pop('custom_ascii_chars')
    ascii_art = image_to_ascii(image_stream, ascii_chars)

    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")

def invert_color_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)

    inverted = invert_color(image)

    output_stream = io.BytesIO()
    inverted.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def mirror_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)

    if 'mirror_horizontal' in user_states[message.chat.id]:
        mirrored = image.transpose(Image.FLIP_LEFT_RIGHT)
        user_states[message.chat.id].pop('mirror_horizontal')
    elif 'mirror_vertical' in user_states[message.chat.id]:
        mirrored = image.transpose(Image.FLIP_TOP_BOTTOM)
        user_states[message.chat.id].pop('mirror_vertical')

    output_stream = io.BytesIO()
    mirrored.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def heatmap_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)

    heatmap = convert_to_heatmap(image)

    output_stream = io.BytesIO()
    heatmap.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

def resize_and_send(message):
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)

    resized_image = resize_for_sticker(image)

    output_stream = io.BytesIO()
    resized_image.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)

bot.polling(none_stop=True)
