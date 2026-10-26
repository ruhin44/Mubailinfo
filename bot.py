import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

TOKEN = "8820740325:AAGeSShZeaG2eTriYQMV__QkE5GYxsM9dSY"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        "স্বাগতম ওস্তাদ! 🚀\n\n"
        "মোবাইল দোকানের সঠিক প্রাইস, র‍্যাম-রম, ব্যাটারি এবং ফুল স্পেসিফিকেশন জানতে যেকোনো নির্দিষ্ট ফোনের নাম (যেমন: `Vivo X300 Ultra` বা `Samsung A55`) লিখে পাঠান।"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message()
async def search_mobile(message: types.Message):
    query_text = message.text.strip()
    
    if not query_text:
        return

    waiting_msg = await message.answer("🔍 ফোনের প্রাইস ও স্পেসিফিকেশন সংগ্রহ করা হচ্ছে, একটু অপেক্ষা করুন...")

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
                    text="❌ দুঃখিত ওস্তাদ, এই নামের কোনো সঠিক মোবাইল পাওয়া যায়নি!"
                )
                return

            await bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)

            # সবচেয়ে মিলে যাওয়া প্রথম ফোনটি নেওয়া
            item = product_items[0]
            product_name = item.get("value")
            product_url = item.get("url")
            layout_html = item.get("layout")
            
            soup = BeautifulSoup(layout_html, 'html.parser')
            img_tag = soup.find('img')
            img_url = img_tag['src'] if img_tag else ""

            # প্রোডাক্ট পেজ থেকে প্রাইস এবং স্পেসিফিকেশন স্ক্র্যাপ করা
            price_text = "তথ্য নেই"
            specs_list = []
            
            try:
                page_res = requests.get(product_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                if page_res.status_code == 200:
                    page_soup = BeautifulSoup(page_res.text, 'html.parser')
                    
                    # প্রাইস খুঁজে বের করা
                    price_tag = page_soup.find('span', {'class': 'aps-price'}) or page_soup.find('div', {'class': 'price'})
                    if price_tag:
                        price_text = price_tag.get_text(strip=True)
                    
                    # স্পেসিফিকেশন টেবিল বা লিস্ট থেকে তথ্য সংগ্রহ (যেমন: RAM, ROM, Battery ইত্যাদি)
                    spec_items = page_soup.select('.aps-specs-item, .specs-content li, .aps-single-features li')
                    for spec in spec_items[:6]: # মূল হাইলাইটসগুলো নেওয়ার জন্য
                        specs_list.append(spec.get_text(strip=True))
            except Exception as err:
                logging.error(f"Scraping error: {err}")

            # স্পেসিফিকেশন সুন্দর করে সাজানো
            specs_formatted = "\n".join([f"🔹 {s}" for s in specs_list]) if specs_list else "🔹 বিস্তারিত তথ্য ওয়েবসাইটে আপডেট করা হচ্ছে।"

            caption = (
                f"📱 **মডেল:** {product_name}\n"
                f"💰 **অফিশিয়াল/আনঅফিশিয়াল দাম:** {price_text}\n\n"
                f"📊 **মূল বৈশিষ্ট্য ও স্পেসিফিকেশন:**\n"
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

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot Stopped!")
