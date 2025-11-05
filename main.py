import asyncio
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient, events
import random
import time
import os
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# بيانات API والجلسة
API_ID = 20529343
API_HASH = "1BJWap1sAUKCga9Dy1BqPcz5tmD1gA_PLH7-X8xC188Xn0vvZrnqUwh7O0jWMKIcIhzYz0tjwSAlYepRnH1pzhWcDFmN8gy-SgE9XzUuufmNnnvh7PTvMp2UUAYp_LndEphU799jH3_GbSCoZ3CpD-_clEtR1La1Kz_WuITPOUsOpSh5ipBEOmDygRQ6bUCUveRorp0Rxu2Whg9eVR_QZWR4ra2HJaOVF4iYZx-Odoj5zOhE9JxI1R0bQSaJoMcBoZJDfVkPJk5xmT3m1RFKGV35YS32GX71vBDtjg6lN4yqPtdeDpUFlsLPPptzBF3nV7NV3I6QC2yHqF-uNSYGsq4m0QD-DoWA="

# إنشاء كائن العميل
client = TelegramClient(
    session=None,
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)
TIMEZONE = pytz.timezone('Africa/Tripoli')

# نظام الحماية من Flood
last_schedule_time = 0
min_delay = 13
max_delay = 32

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
    """إنشاء قائمة بالأوقات لمدة 24 ساعة كاملة"""
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
    """إنشاء قائمة بالأوقات المستقبلية فقط بدءاً من الوقت الحالي لمدة 24 ساعة"""
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
        if current_time <= end_time:
            time_slots.append(current_time)
        current_time += timedelta(minutes=15)
    
    return time_slots

def generate_today_time_slots():
    """إنشاء قائمة بالأوقات المستقبلية لليوم الحالي فقط"""
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
            logger.info(f"تم جدولة: {message_text} في {schedule_time.strftime('%H:%M')}")
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
            
            await event.reply(f"جاري جدولة {len(time_slots)} رسالة...")
            
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
            
            report = f"تم الجدولة: {successful} رسالة\nفشل: {failed} رسالة\nالأسطر: {len(split_messages)}\nالأوقات: {len(time_slots)}"
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
            
            await event.reply(f"جاري جدولة {len(time_slots)} رسالة لليوم...")
            
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
            
            report = f"تم جدولة اليوم: {successful} رسالة\nفشل: {failed} رسالة\nالأسطر: {len(split_messages)}\nالأوقات: {len(time_slots)}"
            await event.reply(report)
            
        except Exception as e:
            await event.reply(f"خطأ: {e}")
            logger.error(f"خطأ رئيسي: {e}")

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
            
            await event.reply(f"جاري جدولة {len(time_slots)} رسالة لمدة 24 ساعة...")
            
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
            
            report = f"تم جدولة 24 ساعة: {successful} رسالة\nفشل: {failed} رسالة\nالأسطر: {len(split_messages)}\nالأوقات: {len(time_slots)}"
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
        await event.reply("✅ البوت يعمل بشكل طبيعي\n📍 التوقيت: ليبيا\n⏰ الوقت الحالي: " + datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S'))
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
                logger.info(f"تم حذف رسالة مجدولة: {msg.id}")
                
                delay = get_random_delay()
                await asyncio.sleep(delay)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"خطأ في حذف رسالة {msg.id}: {e}")
                continue
        
        report = f"تم الانتهاء من الحذف:\n- تم الحذف: {deleted_count}\n- فشل الحذف: {failed_count}"
        await event.reply(report)
        
    except Exception as e:
        error_msg = f"خطأ في الحذف: {str(e)}"
        await event.reply(error_msg)
        logger.error(f"خطأ رئيسي في الحذف: {e}")

@client.on(events.NewMessage(pattern='عرض المجدول'))
async def show_scheduled_handler(event):
    try:
        scheduled_messages = await client.get_scheduled_messages(event.chat_id)
        
        if not scheduled_messages:
            await event.reply("لا توجد رسائل مجدولة")
            return
        
        scheduled_messages.sort(key=lambda x: x.date)
        
        response = f"الرسائل المجدولة ({len(scheduled_messages)}):\n\n"
        
        for i, msg in enumerate(scheduled_messages[:10], 1):
            message_preview = msg.message[:50] + "..." if len(msg.message) > 50 else msg.message
            schedule_time = msg.date.astimezone(TIMEZONE).strftime('%Y-%m-%d %H:%M')
            response += f"{i}. {schedule_time} - {message_preview}\n"
        
        if len(scheduled_messages) > 10:
            response += f"\nو {len(scheduled_messages) - 10} رسالة أخرى..."
        
        await event.reply(response)
        
    except Exception as e:
        await event.reply(f"خطأ في العرض: {e}")

@client.on(events.NewMessage(pattern='تفاصيل المجدول'))
async def detailed_scheduled_handler(event):
    """عرض تفاصيل أكثر عن الرسائل المجدولة"""
    try:
        scheduled_messages = await client.get_scheduled_messages(event.chat_id)
        
        if not scheduled_messages:
            await event.reply("لا توجد رسائل مجدولة")
            return
        
        scheduled_messages.sort(key=lambda x: x.date)
        
        now = datetime.now(TIMEZONE)
        today_count = 0
        future_count = 0
        
        for msg in scheduled_messages:
            if msg.date.date() == now.date():
                today_count += 1
            elif msg.date > now:
                future_count += 1
        
        response = f"إحصائيات الرسائل المجدولة:\n"
        response += f"📊 الإجمالي: {len(scheduled_messages)}\n"
        response += f"📅 لليوم: {today_count}\n"
        response += f"⏳ للمستقبل: {future_count}\n\n"
        
        response += "أحدث الرسائل:\n"
        for i, msg in enumerate(scheduled_messages[:5], 1):
            message_preview = msg.message[:30] + "..." if len(msg.message) > 30 else msg.message
            schedule_time = msg.date.astimezone(TIMEZONE).strftime('%m/%d %H:%M')
            time_left = msg.date - now
            
            if time_left.total_seconds() > 0:
                hours_left = int(time_left.total_seconds() // 3600)
                mins_left = int((time_left.total_seconds() % 3600) // 60)
                time_info = f"بعد {hours_left}h {mins_left}m"
            else:
                time_info = "انتهى الوقت"
            
            response += f"{i}. {schedule_time} ({time_info}) - {message_preview}\n"
        
        await event.reply(response)
        
    except Exception as e:
        await event.reply(f"خطأ في العرض التفصيلي: {e}")

@client.on(events.NewMessage(pattern='مساعدة'))
async def help_handler(event):
    """عرض جميع الأوامر المتاحة"""
    help_text = """
🎯 **أوامر البوت:**

📅 **الجدولة:**
• `جدول` - الرد على رسالة لجدولتها كاملة
• `جدولة اليوم` - جدولة لبقية اليوم
• `جدولة 24 ساعة` - جدولة لـ24 ساعة قادمة

🛠️ **أدوات:**
• `تقسيم` - الرد على رسالة لتقسيمها وخلطها
• `فحص` - فحص حالة البوت
• `مساعدة` - عرض هذه الرسالة

🗑️ **إدارة المجدول:**
• `عرض المجدول` - عرض الرسائل المجدولة
• `تفاصيل المجدول` - إحصائيات مفصلة
• `حذف المجدول` - حذف جميع الرسائل المجدولة

⏰ **معلومات:**
• التوقيت: ليبيا (Africa/Tripoli)
• الفاصل الزمني: 15 دقيقة
• الحماية: نظام مضاد للفلود
"""
    await event.reply(help_text)

async def main():
    try:
        await client.start()
        me = await client.get_me()
        
        logger.info(f"✅ البوت يعمل باسم: {me.first_name}")
        logger.info("📍 التوقيت: ليبيا (Africa/Tripoli)")
        logger.info("📅 جاهز لاستقبال الأوامر")
        logger.info(f"⏰ وقت البدء: {datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # إرسال رسالة بدء التشغيل (اختياري)
        # await client.send_message('me', '✅ البوت يعمل على Render!')
        
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء البوت: {e}")

if __name__ == '__main__':
    # تشغيل البوت
    client.loop.run_until_complete(main())
