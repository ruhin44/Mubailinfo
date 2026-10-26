import asyncio
import logging
import os
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = "8820740325:AAGeSShZeaG2eTriYQMV__QkE5GYxsM9dSY"
ADMIN_CHAT_ID = "8087857994"  # Apnar telegram id bosiye deben

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Notun Brand ebong Budget filter er jonno FSM State
class FilterState(StatesGroup):
    waiting_for_brand = State()
    waiting_for_budget = State()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Kivabe search korben?", callback_data="help_info")
    builder.button(text="💰 Brand o Bozet diye khujun", callback_data="price_filter_start")
    builder.button(text="🌐 Mobile Dokan Visit", url="https://www.mobiledokan.co")
    builder.adjust(1)

    welcome_text = (
        "Shagotom Ostad! 🚀\n\n"
        "Eti apnar mobile dokaner official info bot.\n"
        "Jekono phones thik price, RAM, ROM, battery o specification dekhte soraSori phones nam lekhe pathan othoba niche 'Brand o Bozet diye khujun' batone click korun."
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "help_info")
async def callback_help(callback: types.CallbackQuery):
    await callback.message.answer(
        "💡 **Babohareer niyom:**\n"
        "1. SoraSori jekono phones nam likhe pathan (jehon: `Vivo Y35+`).\n"
        "2. Othoba specific brand ebong bozet-er modhye phone khujte 'Brand o Bozet diye khujun' baton babohar korun.",
        parse_mode="Markdown"
    )
    await callback.answer()

# Brand o Budget diye khujar baton handler (Notun add kora hoyeche)
@dp.callback_query(F.data == "price_filter_start")
async def callback_price_filter(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📱 **Brand Name:**\n"
        "Doya kore mobile-er brand-ti likhun (jehon: `Samsung`, `Vivo`, `Xiaomi`, `Realme` itadi):",
        parse_mode="Markdown"
    )
    await state.set_state(FilterState.waiting_for_brand)
    await callback.answer()

# User brand likhle porer step-e bozet nibe
@dp.message(FilterState.waiting_for_brand)
async def process_brand(message: types.Message, state: FSMContext):
    brand_name = message.text.strip()
    await state.update_data(brand=brand_name)
    
    await message.answer(
        f"💰 Apni select korechen: **{brand_name}**\n\n"
        "Ekhon doya kore apnar mohabojet ba taka-r poriman songkhay likhun (jehon: `20000` ba `30000`):",
        parse_mode="Markdown"
    )
    await state.set_state(FilterState.waiting_for_budget)

# User budget dile brand ebong budget mile phone khunje ber korbe
@dp.message(FilterState.waiting_for_budget)
async def process_budget(message: types.Message, state: FSMContext):
    budget_text = message.text.strip()
    budget_nums = "".join([c for c in budget_text if c.isdigit()])
    
    if not budget_nums:
        await message.answer("⚠️ Doya kore sothik songkhay bozet likhun (jehon: `20000`):")
        return
    
    max_budget = int(budget_nums)
    user_data = await state.get_data()
    brand_name = user_data.get("brand", "")
    await state.clear()
    
    waiting_msg = await message.answer(f"🔍 {brand_name} brand-er ৳{max_budget} ba tar kom bozet-er shera phone-ti khunje ber kora hocche...")

    url = "https://www.mobiledokan.co/wp-admin/admin-ajax.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Redmi 7A)",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.mobiledokan.co",
        "Referer": "https://www.mobiledokan.co/"
    }
    
    matched_phone = None
    matched_price_val = 0
    
    try:
        response = requests.post(url, headers=headers, data={"action": "tie_ajax_search", "query": brand_name}, timeout=10)
        if response.status_code == 200:
            suggestions = response.json().get("suggestions", [])
            product_items = [item for item in suggestions if "View all results" not in item.get("value", "")]
            
            for item in product_items:
                p_url = item.get("url")
                p_name = item.get("value")
                
                if brand_name.lower() in p_name.lower():
                    try:
                        p_res = requests.get(p_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        if p_res.status_code == 200:
                            p_soup = BeautifulSoup(p_res.text, 'html.parser')
                            price_tag = p_soup.find('span', {'class': 'aps-feature-price'}) or p_soup.select_one('.aps-price')
                            if price_tag:
                                price_str = price_tag.get_text(strip=True)
                                digits = "".join([c for c in price_str if c.isdigit()])
                                if digits:
                                    price_val = int(digits)
                                    if price_val <= max_budget:
                                        matched_phone = item
                                        matched_price_val = price_val
                                        break
                    except:
                        continue
                        
        if not matched_phone:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=waiting_msg.message_id,
                text=f"❌ Dukkito Ostad, {brand_name} brand-er modhye ৳{max_budget} bozet-er kono phone ekhon paoa jayni."
            )
            return

        await bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)

        product_name = matched_phone.get("value")
        product_url = matched_phone.get("url")
        layout_html = matched_phone.get("layout")
        
        soup = BeautifulSoup(layout_html, 'html.parser')
        img_tag = soup.find('img')
        img_url = img_tag['src'] if img_tag else ""

        price_text = f"৳{matched_price_val:,}"
        specs_list = []
        
        page_res = requests.get(product_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if page_res.status_code == 200:
            page_soup = BeautifulSoup(page_res.text, 'html.parser')
            spec_items = page_soup.select('.aps-features-iconic li')
            if spec_items:
                for spec in spec_items:
                    text_val = spec.get_text(strip=True)
                    if text_val:
                        specs_list.append(text_val)

        specs_formatted = "\n".join([f"🔹 {s}" for s in specs_list]) if specs_list else "🔹 Details paoa jayni."

        caption = (
            f"🎯 **Brand & Budget Match Phone:**\n"
            f"📱 **Model:** {product_name}\n"
            f"💰 **Price:** {price_text}\n\n"
            f"📊 **Specifications:**\n"
            f"{specs_formatted}"
        )
        
        if img_url:
            await message.answer_photo(photo=img_url, caption=caption, parse_mode="Markdown")
        else:
            await message.answer(caption, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Brand filter error: {e}")
        await message.answer("⚠️ Filter korar somoy ekti truti ghoteche, Ostad!")

# Sadharon text ba phone-er nam diye search korar mul function (Purber moto thik rakha hoyeche)
@dp.message()
async def search_mobile(message: types.Message):
    query_text = message.text.strip()
    
    if not query_text or query_text.startswith("/"):
        return

    waiting_msg = await message.answer("🔍 Phoner shothik tottho o dam khunje hocche, apekka korun...")

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
                    text="❌ Dukkito Ostad, ei namer kono mobile paoa jayni! Sothik namti lekhe abar chesta korun."
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

            price_text = "Totho nei"
            specs_list = []
            
            try:
                page_res = requests.get(product_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                if page_res.status_code == 200:
                    page_soup = BeautifulSoup(page_res.text, 'html.parser')
                    
                    price_tag = page_soup.find('span', {'class': 'aps-feature-price'}) or page_soup.select_one('.aps-price')
                    if price_tag:
                        price_text = price_tag.get_text(strip=True)
                    else:
                        for tr in page_soup.select('tr'):
                            if 'Price' in tr.get_text():
                                tds = tr.select('td')
                                if len(tds) > 1:
                                    price_text = tds[1].get_text(strip=True)
                                    break

                    spec_items = page_soup.select('.aps-features-iconic li')
                    if spec_items:
                        for spec in spec_items:
                            text_val = spec.get_text(strip=True)
                            if text_val:
                                specs_list.append(text_val)
                    else:
                        spec_rows = page_soup.select('.aps-specs-table tr')
                        for row in spec_rows[:7]:
                            specs_list.append(row.get_text(separator=": ", strip=True))

            except Exception as err:
                logging.error(f"Scraping error: {err}")

            specs_formatted = "\n".join([f"🔹 {s}" for s in specs_list]) if specs_list else "🔹 Details paoa jayni."

            caption = (
                f"📱 **Model:** {product_name}\n"
                f"💰 **Price:** {price_text}\n\n"
                f"📊 **Specifications:**\n"
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
                text="⚠️ Server-e connect korte somossha hocche, Ostad!"
            )
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("⚠️ Ekti truti ghoteche, Ostad!")

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
                text="✅ **Update Done, Ostad!**\n\nApnar mobile info bot-e notun brand o budget filter feature safolvabe add kora hoyeche. 🚀",
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
