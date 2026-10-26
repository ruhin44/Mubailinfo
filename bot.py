import asyncio
import logging
import os
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = "8820740325:AAGeSShZeaG2eTriYQMV__QkE5GYxsM9dSY"
ADMIN_CHAT_ID = "8087857994"  # আপনার টেলিগ্রাম চ্যাট আইডি এখানে বসাবেন

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 কীভাবে সার্চ করবেন?", callback_data="help_info")
    builder.button(text="🌐 মোবাইল ডোকান ভিজিট", url="https://www.mobiledokan.co")
    builder.adjust(1)

    welcome_text = (
        "স্বাগতম ওস্তাদ! 🚀\n\n"
        "এটি আপনার মোবাইল দোকানের অফিশিয়াল ইনফো বট।\n"
        "যেকোনো ফোনের সঠিক প্রাইস, র‍্যাম, রম, ব্যাটারি ও স্পেসিফিকেশন দেখতে সরাসরি ফোনের নাম (যেমন: `Vivo Y35+` বা `Samsung A55`) লিখে পাঠান।"
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "help_info")
async def callback_help(callback: types.CallbackQuery):
    await callback.message.answer(
        "💡 **ব্যবহারের নিয়ম:**\n"
        "বটের চ্যাটে শুধু আপনার কাঙ্ক্ষিত ফোনের নাম লিখুন (যেমন: `Vivo Y35+`). বট সাথে সাথে ওয়েবসাইট থেকে রিয়েল-ডেটা ফেচ করে আপনাকে সব ডিটেইলস ও ছবিসহ জানিয়ে দেবে!",
        parse_mode="Markdown"
    )
    await callback.answer()

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
            
            product_items = [item for item in suggestions if "View all results" not in item.get("value", "")]
            
            if not product_items:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=waiting_msg.message_id,
                    text="❌ দুঃখিত ওস্তাদ, এই নামের কোনো মোবাইল পাওয়া যায়নি! সঠিক নামটি লিখে আবার চেষ্টা করুন।"
                )
                return

            await bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)

            item = product_items[0]
            product_name = item.get("value")
            product_url = item.get("url")
            layout_html = item.get("layout")
            
            soup = BeautifulSoup(layout_html, 'html.parser')
            img_tag = soup.find('img')
            img_url = img_tag['src'] if img_tag else ""

            price_text = "তথ্য নেই"
            specs_list = []
            
            try:
                page_res = requests.get(product_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                if page_res.status_code == 200:
                    page_soup = BeautifulSoup(page_res.text, 'html.parser')
                    
                    # ১. সঠিক ক্লাস টার্গেট করে প্রাইস খোঁজা (ইনস্পেক্ট কোড অনুযায়ী)
                    price_tag = page_soup.find('span', {'class': 'aps-feature-price'}) or page_soup.select_one('.aps-price')
                    if price_tag:
                        price_text = price_tag.get_text(strip=True)
                    else:
                        # ফলব্যাক: টেবিল থেকে প্রাইস খোঁজা
                        for tr in page_soup.select('tr'):
                            if 'Price' in tr.get_text():
                                tds = tr.select('td')
                                if len(tds) > 1:
                                    price_text = tds[1].get_text(strip=True)
                                    break

                    # ২. সঠিক হাইলাইট লিস্ট থেকে স্পেসিফিকেশন নেওয়া (ইনস্পেক্ট কোড অনুযায়ী `.aps-features-iconic li`)
                    spec_items = page_soup.select('.aps-features-iconic li')
                    if spec_items:
                        for spec in spec_items:
                            text_val = spec.get_text(strip=True)
                            if text_val:
                                specs_list.append(text_val)
                    else:
                        # ফলব্যাক: টেবিল থেকে স্পেস নেওয়া
                        spec_rows = page_soup.select('.aps-specs-table tr')
                        for row in spec_rows[:7]:
                            specs_list.append(row.get_text(separator=": ", strip=True))

            except Exception as err:
                logging.error(f"Scraping error: {err}")

            specs_formatted = "\n".join([f"🔹 {s}" for s in specs_list]) if specs_list else "🔹 বিস্তারিত তথ্য পাওয়া যায়নি।"

            caption = (
                f"📱 **মডেল:** {product_name}\n"
                f"💰 **মূল্য:** {price_text}\n\n"
                f"📊 **স্পেসিফিকেশন ও হাইলাইটস:**\n"
                f"{specs_formatted}"
            )
            
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

async def handle_ping(request):
    return web.Response(text="Bot Web Service is running smoothly, Oustad!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server successfully bound to port {port}")

async def on_startup():
    if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "YOUR_TELEGRAM_CHAT_ID":
        try:
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="✅ **Update Done, ওস্তাদ!**\n\nআপনার মোবাইল ইনফো বট ওয়েব সার্ভিস হিসেবে সফলভাবে রেন্ডারে লাইভ হয়েছে। 🚀",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Startup notification error: {e}")

async def main():
    await on_startup()
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot Stopped!")
