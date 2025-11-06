import asyncio
from datetime import datetime, timedelta
import pytz
import random
import time
import os
import logging
import sys

# إعداد تسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# بيانات API - مع قيم افتراضية آمنة
try:
    API_ID = int(os.getenv('API_ID', '20529343'))
except (ValueError, TypeError):
    API_ID = 20529343

API_HASH = os.getenv('API_HASH', '656199efaf0935e731164fb9d02e4aa6')
SESSION_STRING = os.getenv('SESSION_STRING', '')

TIMEZONE = pytz.timezone('Africa/Tripoli')

# إعدادات الحماية
last_schedule_time = 0
min_delay = 15
max_delay = 35

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import InputDeviceInfo

# إعدادات الجهاز كـ iPhone 17 Pro Max
device_model = "iPhone 17 Pro Max"
system_version = "iOS 18.1.0"
app_version = "10.5.0"
lang_code = "ar"

# إنشاء العميل مع إعدادات الجهاز
client = TelegramClient(
    session=StringSession(SESSION_STRING),
    api_id=API_ID,
    api_hash=API_HASH,
    device_model=device_model,
    system_version=system_version,
    app_version=app_version,
    lang_code=lang_code
)

def can_schedule():
    global last_schedule_time
    current_time = time.time()
    if current_time - last_schedule_time < min_delay:
        return False
    return True

def update_schedule_time():
    global last_schedule_time
    last_schedule_time = time.time()

def get_random_delay():
    return random.uniform(min_delay, max_delay)

def split_and_shuffle_messages(message_text):
    """تقسيم الرسالة إلى أسطر وخلطها عشوائياً"""
    lines = message_text.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    
    if len(lines) <= 1:
        return lines
    
    random.shuffle(lines)
    return lines

def generate_time_slots():
    """إنشاء قائمة بالأوقات كل 15 دقيقة"""
    time_slots = []
    now = datetime.now(TIMEZONE)
    
    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=23, minute=45, second=0, microsecond=0)
    
    current_time = start_time
    
    while current_time <= end_time:
        time_slots.append(current_time)
        current_time += timedelta(minutes=15)
    
    return time_slots

def generate_future_time_slots():
    """إنشاء قائمة بالأوقات المستقبلية كل 15 دقيقة"""
    time_slots = []
    now = datetime.now(TIMEZONE)
    
    start_time = now.replace(second=0, microsecond=0)
    end_time = start_time + timedelta(hours=24)
    
    current_minute = start_time.minute
    remainder = current_minute % 15
    if remainder > 0:
        start_time += timedelta(minutes=(15 - remainder))
    
    current_time = start_time
    
    while current_time <= end_time:
        time_slots.append(current_time)
        current_time += timedelta(minutes=15)
    
    return time_slots

def generate_today_time_slots():
    """إنشاء قائمة بالأوقات لليوم كل 15 دقيقة"""
    time_slots = []
    now = datetime.now(TIMEZONE)
    
    start_time = now.replace(second=0, microsecond=0)
    end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=0)
    
    current_minute = start_time.minute
    remainder = current_minute % 15
    if remainder > 0:
        start_time += timedelta(minutes=(15 - remainder))
    
    current_time = start_time
    
    while current_time <= end_of_today:
        time_slots.append(current_time)
        current_time += timedelta(minutes=15)
    
    return time_slots

async def schedule_message(chat_id, message_text, schedule_time):
    try:
        now = datetime.now(TIMEZONE)
        time_difference = schedule_time - now
        
        if time_difference.total_seconds() > 0:
            await client.send_message(
                chat_id,
                message_text,
                schedule=schedule_time
            )
            logger.info(f"تم الجدولة: {schedule_time.strftime('%H:%M')}")
            return True
        else:
            logger.info(f"الوقت مضى: {schedule_time.strftime('%H:%M')}")
            return False
    except Exception as e:
        logger.error(f"خطأ في الجدولة: {e}")
        return False

@client.on(events.NewMessage(pattern='جدول'))
async def schedule_message_handler(event):
    if not can_schedule():
        wait_time = int(min_delay - (time.time() - last_schedule_time))
        await event.reply(f"انتظر {wait_time} ثانية قبل الجدولة مرة أخرى")
        return
    
    update_schedule_time()
    
    if event.is_reply:
        try:
            reply_message = await event.get_reply_message()
            message_text = reply_message.text
            
            if not message_text:
                await event.reply("الرسالة فارغة")
                return
            
            split_messages = split_and_shuffle_messages(message_text)
            
            if not split_messages:
                await event.reply("لا توجد رسائل صالحة للجدولة")
                return
            
            time_slots = generate_time_slots()
            
            successful = 0
            failed = 0
            
            await event.reply(f"جاري جدولة {len(time_slots)} رسالة كل 15 دقيقة...")
            
            for i, schedule_time in enumerate(time_slots):
                if i < len(split_messages):
                    message_to_schedule = split_messages[i % len(split_messages)]
                else:
                    message_to_schedule = split_messages[i % len(split_messages)]
                
                success = await schedule_message(event.chat_id, message_to_schedule, schedule_time)
                if success:
                    successful += 1
                else:
                    failed += 1
                
                delay = get_random_delay()
                await asyncio.sleep(delay)
            
            report = f"تم الجدولة: {successful} رسالة\nفشل: {failed} رسالة\nكل 15 دقيقة"
            await event.reply(report)
            
        except Exception as e:
            await event.reply(f"خطأ: {e}")
            logger.error(f"خطأ رئيسي: {e}")
    else:
        await event.reply("الرد على الرسالة المراد جدولتها")

@client.on(events.NewMessage(pattern='جدولة اليوم'))
async def schedule_today_handler(event):
    if not can_schedule():
        wait_time = int(min_delay - (time.time() - last_schedule_time))
        await event.reply(f"انتظر {wait_time} ثانية قبل الجدولة مرة أخرى")
        return
    
    update_schedule_time()
    
    if event.is_reply:
        try:
            reply_message = await event.get_reply_message()
            message_text = reply_message.text
            
            if not message_text:
                await event.reply("الرسالة فارغة")
                return
            
            split_messages = split_and_shuffle_messages(message_text)
            
            if not split_messages:
                await event.reply("لا توجد رسائل صالحة للجدولة")
                return
            
            time_slots = generate_today_time_slots()
            
            if not time_slots:
                await event.reply("لا توجد أوقات متاحة للجدولة اليوم")
                return
            
            successful = 0
            failed = 0
            
            await event.reply(f"جاري جدولة {len(time_slots)} رسالة لليوم كل 15 دقيقة...")
            
            for i, schedule_time in enumerate(time_slots):
                if i < len(split_messages):
                    message_to_schedule = split_messages[i % len(split_messages)]
                else:
                    message_to_schedule = split_messages[i % len(split_messages)]
                
                success = await schedule_message(event.chat_id, message_to_schedule, schedule_time)
                if success:
                    successful += 1
                else:
                    failed += 1
                
                delay = get_random_delay()
                await asyncio.sleep(delay)
            
            report = f"تم جدولة اليوم: {successful} رسالة\nفشل: {failed} رسالة\nكل 15 دقيقة"
            await event.reply(report)
            
        except Exception as e:
            await event.reply(f"خطأ: {e}")
            logger.error(f"خطأ رئيسي: {e}")
    else:
        await event.reply("الرد على الرسالة المراد جدولتها")

@client.on(events.NewMessage(pattern='جدولة 24 ساعة'))
async def schedule_24hours_handler(event):
    if not can_schedule():
        wait_time = int(min_delay - (time.time() - last_schedule_time))
        await event.reply(f"انتظر {wait_time} ثانية قبل الجدولة مرة أخرى")
        return
    
    update_schedule_time()
    
    if event.is_reply:
        try:
            reply_message = await event.get_reply_message()
            message_text = reply_message.text
            
            if not message_text:
                await event.reply("الرسالة فارغة")
                return
            
            split_messages = split_and_shuffle_messages(message_text)
            
            if not split_messages:
                await event.reply("لا توجد رسائل صالحة للجدولة")
                return
            
            time_slots = generate_future_time_slots()
            
            if not time_slots:
                await event.reply("لا توجد أوقات متاحة للجدولة")
                return
            
            successful = 0
            failed = 0
            
            await event.reply(f"جاري جدولة {len(time_slots)} رسالة لمدة 24 ساعة كل 15 دقيقة...")
            
            for i, schedule_time in enumerate(time_slots):
                if i < len(split_messages):
                    message_to_schedule = split_messages[i % len(split_messages)]
                else:
                    message_to_schedule = split_messages[i % len(split_messages)]
                
                success = await schedule_message(event.chat_id, message_to_schedule, schedule_time)
                if success:
                    successful += 1
                else:
                    failed += 1
                
                delay = get_random_delay()
                await asyncio.sleep(delay)
            
            report = f"تم جدولة 24 ساعة: {successful} رسالة\nفشل: {failed} رسالة\nكل 15 دقيقة"
            await event.reply(report)
            
        except Exception as e:
            await event.reply(f"خطأ: {e}")
            logger.error(f"خطأ رئيسي: {e}")
    else:
        await event.reply("الرد على الرسالة المراد جدولتها")

@client.on(events.NewMessage(pattern='تقسيم'))
async def split_only_handler(event):
    if event.is_reply:
        try:
            reply_message = await event.get_reply_message()
            message_text = reply_message.text
            
            if not message_text:
                await event.reply("الرسالة فارغة")
                return
            
            split_messages = split_and_shuffle_messages(message_text)
            
            if not split_messages:
                await event.reply("لا توجد رسائل صالحة")
                return
            
            response = f"الأسطر بعد التقسيم ({len(split_messages)}):\n\n"
            for i, line in enumerate(split_messages, 1):
                response += f"{i}. {line}\n"
            
            await event.reply(response)
            
        except Exception as e:
            await event.reply(f"خطأ: {e}")
    else:
        await event.reply("الرد على الرسالة المراد تقسيمها")

@client.on(events.NewMessage(pattern='فحص'))
async def test_handler(event):
    try:
        status = f"""📱 البوت يعمل بشكل طبيعي
📱 الجهاز: iPhone 17 Pro Max
📍 التوقيت: ليبيا
⏰ الفاصل: 15 دقيقة
🕒 الوقت: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}"""
        await event.reply(status)
        logger.info("تم فحص البوت")
    except Exception as e:
        logger.error(f"خطأ في الفحص: {e}")

@client.on(events.NewMessage(pattern='حذف المجدول'))
async def delete_scheduled_handler(event):
    if not can_schedule():
        wait_time = int(min_delay - (time.time() - last_schedule_time))
        await event.reply(f"انتظر {wait_time} ثانية قبل الحذف مرة أخرى")
        return
    
    update_schedule_time()
    
    try:
        scheduled_messages = await client.get_scheduled_messages(event.chat_id)
        
        if not scheduled_messages:
            await event.reply("لا توجد رسائل مجدولة")
            return
        
        await event.reply(f"جاري حذف {len(scheduled_messages)} رسالة مجدولة...")
        
        deleted_count = 0
        failed_count = 0
        
        for msg in scheduled_messages:
            try:
                await client.delete_messages(event.chat_id, msg.id)
                deleted_count += 1
                logger.info(f"تم حذف رسالة مجدولة")
                
                delay = get_random_delay()
                await asyncio.sleep(delay)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"خطأ في حذف رسالة: {e}")
                continue
        
        report = f"تم الانتهاء من الحذف:\n- تم الحذف: {deleted_count}\n- فشل الحذف: {failed_count}"
        await event.reply(report)
        
    except Exception as e:
        error_msg = f"خطأ في الحذف: {str(e)}"
        await event.reply(error_msg)
        logger.error(f"خطأ رئيسي في الحذف: {e}")

@client.on(events.NewMessage(pattern='مساعدة'))
async def help_handler(event):
    help_text = """📱 **أوامر البوت - iPhone 17 Pro Max**

📅 **الجدولة:**
• `جدول` - جدولة 96 رسالة كل 15 دقيقة
• `جدولة اليوم` - جدولة لبقية اليوم كل 15 دقيقة
• `جدولة 24 ساعة` - جدولة لـ24 ساعة كل 15 دقيقة

🛠️ **أدوات:**
• `تقسيم` - تقسيم وخلط الرسائل
• `فحص` - فحص حالة البوت
• `مساعدة` - عرض هذه الرسالة

🗑️ **إدارة المجدول:**
• `حذف المجدول` - حذف جميع الرسائل

📊 **معلومات:**
• التوقيت: ليبيا
• الفاصل: 15 دقيقة
• الإجمالي: 96 رسالة/يوم
• الجهاز: iPhone 17 Pro Max"""
    await event.reply(help_text)

async def main():
    try:
        # بدء العميل مع معالجة خاصة للجلسات
        await client.start()
        me = await client.get_me()
        
        logger.info(f"✅ البوت يعمل على GitHub Actions")
        logger.info(f"📱 الجهاز: iPhone 17 Pro Max")
        logger.info(f"👤 الاسم: {me.first_name}")
        logger.info("📍 التوقيت: ليبيا")
        logger.info("⏰ الفاصل: 15 دقيقة")
        logger.info("🚀 جاهز لاستقبال الأوامر")
        
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء البوت: {e}")
        # إعادة المحاولة بعد 30 ثانية
        await asyncio.sleep(30)
        await main()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
