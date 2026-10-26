
import asyncio
import logging
import sys
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# আপনার দেওয়া টেলিগ্রাম বট টোকেন
TOKEN = "8820740325:AAGeSShZeaG2eTriYQMV__QkE5GYxsM9dSY"

# লোগিং সেটআপ
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# /start কমান্ড হ্যান্ডলার
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        "স্বাগতম ওস্তাদ! 🚀\n\n"
        "মোবাইল দোকানের প্রাইস ও স্পেসিফিকেশন জানতে যেকোনো ফোনের নাম (যেমন: `Vivo`, `Samsung`, `Redmi`) লিখে পাঠান।"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

# যেকোনো টেক্সট মেসেজ বা ফোনের নাম সার্চ করার হ্যান্ডলার
@dp.message()
async def search_mobile(message: types.Message):
    query_text = message.text.strip()
    
    if not query_text:
        return

    # ইউজারকে প্রোগ্রেস দেখানোর জন্য ওয়েটিং মেসেজ
    waiting_msg = await message.answer("🔍 মোবাইল খোঁজা হচ্ছে, একটু অপেক্ষা করুন...")

    url = "https://www.mobiledokan.co/wp-admin/admin-ajax.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Redmi 7A)",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.mobiledokan.co",
        "Referer": "https://www.mobiledokan.co/"
    }
    data = {
        "action": "tie_ajax_search",
        "query": query_text
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        
        if response.status_code == 200:
            res_json = response.json()
            suggestions = res_json.get("suggestions", [])
            
            # শেষের "View all results" অপশনটি বাদ দিয়ে ফিল্টার করা
            product_items = [item for item in suggestions if "View all results" not in item.get("value", "")]
            
            if not product_items:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=waiting_msg.message_id,
                    text="❌ দুঃখিত ওস্তাদ, এই নামে কোনো মোবাইল পাওয়া যায়নি!"
                )
                return

            # ওয়েটিং মেসেজটি ডিলিট করে দেওয়া
            await bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)

            # সর্বোচ্চ ৫টি ফোন একসাথে শো করবে (স্পিড ভালো রাখার জন্য)
            count = 0
            for item in product_items[:5]:
                product_name = item.get("value")
                product_url = item.get("url")
                layout_html = item.get("layout")
                
                # BeautifulSoup দিয়ে HTML থেকে ছবির লিংক বের করা
                soup = BeautifulSoup(layout_html, 'html.parser')
                img_tag = soup.find('img')
                img_url = img_tag['src'] if img_tag else ""
                
                # টেলিগ্রাম ক্যাপশন ফরম্যাট
                caption = f"📱 **{product_name}**\n\n🔗 [ওয়েবসাইটে বিস্তারিত দেখুন]({product_url})"
                
                if img_url:
                    await message.answer_photo(photo=img_url, caption=caption, parse_mode="Markdown")
                else:
                    await message.answer(caption, parse_mode="Markdown")
                
                count += 1
                
            if count == 0:
                await message.answer("দুঃখিত ওস্তাদ, কোনো ফলাফল প্রদর্শন করা সম্ভব হয়নি।")
        else:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=waiting_msg.message_id,
                text="⚠️ সার্ভারে কানেক্ট করতে সমস্যা হচ্ছে, একটু পরে আবার চেষ্টা করুন।"
            )
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("⚠️ একটি ত্রুটি ঘটেছে, ওস্তাদ!")

# বট রান করার মূল ফাংশন
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot Stopped!")
