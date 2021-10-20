import json
import logging
import requests
from typing import Dict
from  data  import BOT_TOKEN, CHANNEL
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

CHOICES = 'نوع الزواج|الاسم و اللقب|العمر|الطول|الوزن|لون البشرة|القبيلة|المستوى التعليمي|الحالة الإجتماعية|المهر|المصروف الشهري|السكن|مواصفات الزوج المطلوب|معلومات إضافية'
CButtons = CHOICES.split('|')

reply_keyboard = [
    [CButtons[0], CButtons[1]],
    [CButtons[2], CButtons[3]],
    [CButtons[4], CButtons[5]],
    [CButtons[6], CButtons[7]],
    [CButtons[8], CButtons[9]],
    [CButtons[10], CButtons[11]],
    [CButtons[12], CButtons[13]],
    ['معاينة'],
    ['إرسال'],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

def  helper(update: Update, choice) :
    if choice == 'نوع الزواج' : update.message.reply_text('الرجاء تحديد نوع الزواج عادي أو مسيار', reply_markup=markup)


def facts_to_str(user_data: Dict[str, str]) -> str:
    facts = [f'{choice} - {user_data[choice]}' for choice in CButtons if choice in user_data]
    return "\n".join(facts).join(['\n', '\n'])

def missing(user_data: Dict[str, str]) -> str:
    msd = [f'{choice} - فارغ' for choice in CButtons if choice not in user_data and choice != 'معلومات إضافية'] 
    return "\n".join(msd).join(['\n', '\n'])

def check(user_data: Dict[str, str]) -> bool:
    for choice in CButtons :
        if choice not in user_data and choice != 'معلومات إضافية':
            return True
    return False

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "مرحبا بكي في بوت الزواج! هذا البوت مصمم لاستلام و نشر إعلانات الزواج على قناة الإعلانات، الرجاء ملئ الخانات المطلوبة ثم الضغط على ارسال",
        reply_markup=markup,
    )

    return CHOOSING


def regular_choice(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    context.user_data['choice'] = text
    helper(update, text.lower())
    update.message.reply_text(f'الرجاء إرسال {text.lower()} : ')

    return TYPING_REPLY


def review(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    if 'choice' in user_data:
        del user_data['choice']
    
    user = update.message.from_user
    msg = f"الإعلان رقم: {user.id} {facts_to_str(user_data)} {missing(user_data)}"
    update.message.reply_text(
        msg,
        reply_markup=markup,
    )
    
    return CHOOSING 


def received_information(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    text = update.message.text
    category = user_data['choice']
    if sum(i.isdigit() for i in text )>7 :
        update.message.reply_text(
            'لا يجب أن تحتوي الرسالة على أكثر من 7 أرقام\n الرجاء الاختيار مجدداٌ',
            reply_markup=markup,
        )
        return CHOOSING

    user_data[category] = text
    del user_data['choice']

    update.message.reply_text(
        "رائع! تم حفظ : "
        f"{facts_to_str(user_data)} يمكنكي تعديل الإجابة بالضغط مجدداً على زر {facts_to_str(user_data).split('-')[0]} ",
        reply_markup=markup,
    )

    return CHOOSING

def done(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    if check(user_data) :
        update.message.reply_text(
            'الرجاء ملئ جميع الحقول المطلوبة.\n استخدمي خيار المعاينة لعرض الحقول الفارغة',
            reply_markup=markup,
        )
        return CHOOSING
    
    if 'choice' in user_data:
        del user_data['choice']
    
    user = update.message.from_user
    msg = f"الإعلان رقم: {user.id} {facts_to_str(user_data)}"
    update.message.reply_text(
        msg,
        reply_markup=ReplyKeyboardRemove(),
    )
    rep = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHANNEL}&text={msg}')
    msg = json.loads(rep.text)
    logger.info(msg['result']['message_id'])
    user_data['msgid'] = msg['result']['message_id']
    return ConversationHandler.END


def main() -> None:

    updater = Updater(BOT_TOKEN)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(
                    Filters.regex(f'^({CHOICES})$'), regular_choice
                ),
                MessageHandler(Filters.regex('^معاينة$'), review),
            ],
            TYPING_CHOICE: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^إرسال$')), regular_choice
                )
            ],
            TYPING_REPLY: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^إرسال$')),
                    received_information,
                )
            ],
        },
        fallbacks=[MessageHandler(Filters.regex('^إرسال$'), done)],
    )
    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
