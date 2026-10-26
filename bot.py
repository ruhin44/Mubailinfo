import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# আপনার টেলিগ্রাম বট টোকেন
TOKEN = "8820740325:AAGeSShZeaG2eTriYQMV__QkE5GYxsM9dSY"

# [গুরুত্বপূর্ণ] বটের রিস্টার্ট বা আপডেট হলে যে চ্যাট আইডিতে নোটিফিকেশন যাবে (আপনার টেলিগ্রাম ইউজার আইডি এখানে দিন)
ADMIN_CHAT_ID = "8087857994"  # যেমন: 123456789 (সংখ্যাটি এখানে বসিয়ে দেবেন)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# /start কমান্ড এবং ইনলাইন বাটন সেটআপ
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 কীভাবে সার্চ করবেন?", callback_data="help_info")
    builder.button(text="🌐 মোবাইল ডোকান ভিজিট", url="https://www.mobiledokan.co")
    builder.adjust(1)

    welcome_text = (
        "স্বাগতম ওস্তাদ! 🚀\n\n"
        "এটি আপনার মোবাইল দোকানের অফিশিয়াল ইনফো বট।\n"
        "যেকোনো ফোনের সঠিক প্রাইস, র‍্যাম, রম, ব্যাটারি ও স্পেসিফিকেশন দেখতে সরাসরি ফোনের নাম (যেমন: `Vivo X300 Ultra` বা `Samsung A55`) লিখে পাঠান।"
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

# হেল্প বাটন কলব্যাক হ্যান্ডলার
@dp.callback_query(F.data == "help_info")
async def callback_help(callback: types.CallbackQuery):
    await callback.message.answer(
        "💡 **ব্যবহারের নিয়ম:**\n"
        "বটের চ্যাটে শুধু আপনার কাঙ্ক্ষিত ফোনের নাম লিখুন (যেমন: `Redmi Note 13`). বট সাথে সাথে ওয়েবসাইট থেকে রিয়েল-ডেটা ফেচ করে আপনাকে সব ডিটেইলস ও ছবিসহ জানিয়ে দেবে!",
        parse_mode="Markdown"
    )
    await callback.answer()

# টেক্সট দিয়ে মোবাইল সার্চ করার মূল ফাংশন
@dp.message()
async def search_mobile(message: types.Message):
    query_text = message.text.strip()
    
    if not query_text or query_text.startswith("/"):
        return

    waiting_msg = await message.answer("🔍 ফোনের সঠিক তথ্য ও দাম খোঁজা হচ্ছে, একটু অপেক্ষা করুন...")

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
            
            # "View all results" বা ফালতু অপশন বাদ দেওয়া
            product_items = [item for item in suggestions if "View all results" not in item.get("value", "")]
            
            # যদি কোনো সঠিক ফোন না পাওয়া যায়
            if not product_items:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=waiting_msg.message_id,
                    text="❌ দুঃখিত ওস্তাদ, এই নামের কোনো মোবাইল পাওয়া যায়নি! সঠিক নামটি লিখে আবার চেষ্টা করুন।"
                )
                return

            await bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)

            # সবচেয়ে নিখুঁত ও প্রথম রেজাল্টটি নিয়ে কাজ করা
            item = product_items[0]
            product_name = item.get("value")
            product_url = item.get("url")
            layout_html = item.get("layout")
            
            # প্রিভিউ ইমেজ বের করা
            soup = BeautifulSoup(layout_html, 'html.parser')
            img_tag = soup.find('img')
            img_url = img_tag['src'] if img_tag else ""

            # প্রোডাক্ট পেজ থেকে প্রাইস এবং স্পেসিফিকেশন স্ক্র্যাপ করা
            price_text5 = "তথ্য নেই"
            specs_list = []
            
            try:
                page_res = requests.get(product_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                if page_res.status_code == 200:
                    page_soup = BeautifulSoup(page_res.text, 'html.parser')
                    
                    # প্রাইস ট্যাগ সংগ্রহ
                    price_tag = page_soup.find('span', {'class': 'aps-price'}) or page_soup.find('div', {'class': 'price'})
                    if price_tag:
                        price_text5 = price_tag.get_text(strip=True)
                    
                    # স্পেসিফিকেশন হাইলাইটস (RAM, ROM, Battery ইত্যাদি)
                    spec_items = page_soup.select('.aps-specs-item, .specs-content li, .aps-single-features li')
                    for spec in spec_items[:7]:
                        text_val = spec.get_text(strip=True)
                        if text_val not in specs_list:
                            specs_list.append(text_val)
            except Exception as err:
                logging.error(f"Scraping error: {err}")

            # স্পেসিফিকেশন সুন্দর করে সাজানো
            specs_formatted = "\n".join([f"🔸 {s}" for s in specs_list]) if specs_list else "🔹 বিস্তারিত তথ্য সংগ্রহ করা যায়নি।"

            caption = (
                f"📱 **মডেল:** {product_name}\n"
                f"💰 **মূল্য:** {price_text5}\n\n"
                f"📊 **স্পেসিফিকেশন ও হাইলাইটস:**\n"
                f"{specs_formatted}"
            )
            
            # ফটোসহ বা ফটো না থাকলে শুধু টেক্সট পাঠানো
            if img_url:
                await message.answer_photo(photo=img_url, caption=caption, parse_mode="Markdown")
            else:
                await message.answer(caption, parse_mode="Markdown")
                
        else:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=waiting_msg.message_id,
                text="⚠️ সার্ভারে কানেক্ট করতে সমস্যা হচ্ছে, ওস্তাদ!"
            )
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("⚠️ একটি ত্রুটি ঘটেছে, ওস্তাদ!")

# বট স্টার্ট হওয়ার সময় স্বয়ংক্রিয় নোটিফিকেশন পাঠানোর ফাংশন
async def on_startup():
    if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "YOUR_TELEGRAM_CHAT_ID":
        try:
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="✅ **Update Done, ওস্তাদ!**\n\nআপনার মোবাইল ইনফো বট সফলভাবে রেন্ডার বা সার্ভারে আপডেট হয়ে লাইভ হয়েছে। 🚀",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Startup notification error: {e}")

# বট রান করার মূল ফাংশন
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot Stopped!")
