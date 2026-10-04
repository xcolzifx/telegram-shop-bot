import os
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip()

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set!")

DB_FILE = "shop.db"


# =========================
# DATABASE
# =========================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            total REAL,
            payment_method TEXT,
            transaction_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            banned INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    defaults = {
        "bkash": "Not configured",
        "nagad": "Not configured",
        "stars": "Telegram Stars",
        "crypto": "Not configured",
        "support": SUPPORT_USERNAME or "Not configured",
    }

    for key, value in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()


def get_setting(key):
    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
    )

    row = cur.fetchone()
    conn.close()

    return row[0] if row else "Not configured"


def set_setting(key, value):
    conn = db()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
        (key, value),
    )

    conn.commit()
    conn.close()


def save_user(user):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users(
            user_id,
            username,
            first_name,
            created_at
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (
        user.id,
        user.username or "",
        user.first_name or "",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))

    conn.commit()
    conn.close()


def is_banned(user_id):
    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT banned FROM users WHERE user_id=?",
        (user_id,),
    )

    row = cur.fetchone()
    conn.close()

    return bool(row and row[0] == 1)


# =========================
# ADMIN
# =========================

def is_admin(update):
    if not ADMIN_ID:
        return False

    return str(update.effective_user.id) == ADMIN_ID


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ ADD PRODUCT",
                callback_data="admin_add"
            ),
            InlineKeyboardButton(
                "✏️ EDIT",
                callback_data="admin_edit"
            ),
        ],
        [
            InlineKeyboardButton(
                "🗑️ DELETE",
                callback_data="admin_delete"
            ),
            InlineKeyboardButton(
                "📦 PRODUCTS",
                callback_data="admin_products"
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 ORDERS",
                callback_data="admin_orders"
            ),
            InlineKeyboardButton(
                "👤 USERS",
                callback_data="admin_users"
            ),
        ],
        [
            InlineKeyboardButton(
                "📊 STATS",
                callback_data="admin_stats"
            ),
            InlineKeyboardButton(
                "⚙️ SETTINGS",
                callback_data="admin_settings"
            ),
        ],
    ])


# =========================
# USER MENU
# =========================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛍️ SHOP",
                callback_data="shop"
            )
        ],
        [
            InlineKeyboardButton(
                "📦 MY ORDERS",
                callback_data="orders"
            ),
            InlineKeyboardButton(
                "📞 SUPPORT",
                callback_data="support"
            ),
        ],
    ])


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)

    if is_banned(update.effective_user.id):
        await update.message.reply_text(
            "🚫 You are banned from this shop."
        )
        return

    await update.message.reply_text(
        "🛍️ <b>WELCOME TO OUR SHOP!</b>\n\n"
        "✨ Premium digital products & services\n"
        "⚡ Fast delivery\n"
        "🔒 Safe & simple ordering\n\n"
        "👇 Choose an option:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# =========================
# SHOP
# =========================

async def show_shop(query):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, price, stock
        FROM products
        WHERE active=1
        ORDER BY id DESC
    """)

    products = cur.fetchall()
    conn.close()

    if not products:
        await query.edit_message_text(
            "🛍️ <b>SHOP</b>\n\n"
            "📦 No products are available yet.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🏠 HOME",
                        callback_data="home"
                    )
                ]
            ]),
            parse_mode="HTML",
        )
        return

    buttons = []

    for product_id, name, price, stock in products:
        buttons.append([
            InlineKeyboardButton(
                f"🛒 {name} • ৳{price:g}",
                callback_data=f"product:{product_id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🏠 HOME",
            callback_data="home"
        )
    ])

    await query.edit_message_text(
        "🛍️ <b>OUR PRODUCTS</b>\n\n"
        "Choose a product:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="HTML",
    )


async def show_product(query, product_id):
    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, price, stock
        FROM products
        WHERE id=? AND active=1
        """,
        (product_id,),
    )

    product = cur.fetchone()
    conn.close()

    if not product:
        await query.answer(
            "Product not found.",
            show_alert=True
        )
        return

    pid, name, price, stock = product

    if stock <= 0:
        stock_text = "❌ Out of stock"
    else:
        stock_text = f"📦 Stock: {stock}"

    keyboard = [
        [
            InlineKeyboardButton(
                "🛒 BUY NOW",
                callback_data=f"buy:{pid}"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data="shop"
            )
        ],
    ]

    await query.edit_message_text(
        f"🛍️ <b>{name}</b>\n\n"
        f"💰 Price: ৳{price:g}\n"
        f"{stock_text}\n\n"
        "🔥 Ready to order?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# =========================
# PAYMENT
# =========================

async def choose_payment(query, context, product_id):
    conn = db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT name, price, stock
        FROM products
        WHERE id=? AND active=1
        """,
        (product_id,),
    )

    product = cur.fetchone()
    conn.close()

    if not product:
        await query.answer(
            "Product unavailable.",
            show_alert=True
        )
        return

    name, price, stock = product

    if stock <= 0:
        await query.answer(
            "Out of stock!",
            show_alert=True
        )
        return

    context.user_data["buy_product"] = product_id

    keyboard = [
        [
            InlineKeyboardButton(
                "⭐ TELEGRAM STARS",
                callback_data="pay:stars"
            )
        ],
        [
            InlineKeyboardButton(
                "💵 bKash",
                callback_data="pay:bkash"
            ),
            InlineKeyboardButton(
                "💚 Nagad",
                callback_data="pay:nagad"
            ),
        ],
        [
            InlineKeyboardButton(
                "🪙 CRYPTO",
                callback_data="pay:crypto"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data=f"product:{product_id}"
            )
        ],
    ]

    await query.edit_message_text(
        f"🛒 <b>ORDER</b>\n\n"
        f"📦 Product: {name}\n"
        f"💰 Price: ৳{price:g}\n\n"
        "💳 Choose your payment method:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def choose_quantity(query, context, payment_method):
    product_id = context.user_data.get("buy_product")

    if not product_id:
        await query.answer(
            "Order session expired.",
            show_alert=True
        )
        return

    context.user_data["payment_method"] = payment_method
    context.user_data["awaiting_quantity"] = True

    await query.edit_message_text(
        "🔢 <b>QUANTITY</b>\n\n"
        "Send the quantity you want.\n\n"
        "Example: <code>1</code>",
        parse_mode="HTML",
    )


# =========================
# TEXT PROCESSING
# =========================

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user)

    if is_banned(update.effective_user.id):
        return

    text = update.message.text.strip()

    # ADMIN PASSWORD
    if context.user_data.get("awaiting_admin_password"):

        context.user_data["awaiting_admin_password"] = False

        if text == ADMIN_PASSWORD:
            context.user_data["admin"] = True

            await update.message.reply_text(
                "🔓 <b>ADMIN PANEL UNLOCKED</b>",
                reply_markup=admin_menu(),
                parse_mode="HTML",
            )
        else:
            await update.message.reply_text(
                "❌ Wrong password."
            )

        return

    # ADMIN FUNCTIONS
    if context.user_data.get("admin"):
        handled = await handle_admin_text(
            update,
            context
        )

        if handled:
            return

    # QUANTITY
    if context.user_data.get("awaiting_quantity"):

        try:
            quantity = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ Please send a number.\n\n"
                "Example: 1"
            )

            context.user_data["awaiting_quantity"] = True
            return

        if quantity < 1:
            await update.message.reply_text(
                "❌ Quantity must be at least 1."
            )

            context.user_data["awaiting_quantity"] = True
            return

        product_id = context.user_data.get("buy_product")
        payment_method = context.user_data.get(
            "payment_method"
        )

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT name, price, stock
            FROM products
            WHERE id=?
            """,
            (product_id,),
        )

        product = cur.fetchone()
        conn.close()

        if not product:
            await update.message.reply_text(
                "❌ Product no longer exists."
            )
            return

        name, price, stock = product

        if quantity > stock:
            await update.message.reply_text(
                f"❌ Only {stock} item(s) available."
            )

            context.user_data["awaiting_quantity"] = True
            return

        total = price * quantity

        context.user_data["quantity"] = quantity
        context.user_data["total"] = total
        context.user_data["awaiting_transaction"] = True

        setting_key = {
            "Telegram Stars": "stars",
            "bKash": "bkash",
            "Nagad": "nagad",
            "Crypto": "crypto",
        }.get(payment_method, "support")

        instruction = get_setting(setting_key)

        await update.message.reply_text(
            f"💳 <b>{payment_method.upper()}</b>\n\n"
            f"📦 Product: {name}\n"
            f"🔢 Quantity: {quantity}\n"
            f"💰 Total: ৳{total:g}\n\n"
            f"💸 Payment Info:\n"
            f"<code>{instruction}</code>\n\n"
            "After payment, send your "
            "<b>Transaction ID</b> here.",
            parse_mode="HTML",
        )

        return

    # TRANSACTION ID
    if context.user_data.get("awaiting_transaction"):

        context.user_data["awaiting_transaction"] = False

        product_id = context.user_data.get(
            "buy_product"
        )
        quantity = context.user_data.get(
            "quantity"
        )
        total = context.user_data.get(
            "total"
        )
        payment_method = context.user_data.get(
            "payment_method"
        )

        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT name FROM products WHERE id=?",
            (product_id,),
        )

        row = cur.fetchone()

        if not row:
            conn.close()

            await update.message.reply_text(
                "❌ Product not found."
            )
            return

        product_name = row[0]

        cur.execute(
            """
            INSERT INTO orders(
                user_id,
                username,
                product_id,
                product_name,
                quantity,
                total,
                payment_method,
                transaction_id,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                update.effective_user.id,
                update.effective_user.username or "",
                product_id,
                product_name,
                quantity,
                total,
                payment_method,
                text,
                "pending",
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ),
        )

        order_id = cur.lastrowid

        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"✅ <b>ORDER RECEIVED!</b>\n\n"
            f"🧾 Order ID: <code>#{order_id}</code>\n"
            f"📦 Product: {product_name}\n"
            f"🔢 Quantity: {quantity}\n"
            f"💰 Total: ৳{total:g}\n"
            f"💳 Payment: {payment_method}\n"
            f"🟡 Status: Pending\n\n"
            "⏳ Admin will verify your payment.",
            parse_mode="HTML",
        )

        # ADMIN NOTIFICATION
        if ADMIN_ID:

            try:
                await context.bot.send_message(
                    chat_id=int(ADMIN_ID),
                    text=(
                        "🚨 <b>NEW ORDER!</b>\n\n"
                        f"🧾 Order: #{order_id}\n"
                        f"👤 User: @{update.effective_user.username or 'NoUsername'}\n"
                        f"🆔 ID: <code>{update.effective_user.id}</code>\n"
                        f"📦 Product: {product_name}\n"
                        f"🔢 Quantity: {quantity}\n"
                        f"💰 Total: ৳{total:g}\n"
                        f"💳 Payment: {payment_method}\n"
                        f"🧾 TXID: <code>{text}</code>\n\n"
                        "🟡 Status: Pending"
                    ),
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(
                                "✅ ACCEPT",
                                callback_data=f"accept:{order_id}"
                            ),
                            InlineKeyboardButton(
                                "❌ REJECT",
                                callback_data=f"reject:{order_id}"
                            ),
                        ]
                    ]),
                )

            except Exception as e:
                print(
                    "Admin notification error:",
                    e
                )

        return


# =========================
# ADMIN TEXT FUNCTIONS
# =========================

async def handle_admin_text(update, context):

    text = update.message.text.strip()

    # ADD PRODUCT
    if context.user_data.get("admin_add"):

        parts = text.split("|")

        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Format:\n\n"
                "Product Name | Price | Stock\n\n"
                "Example:\n"
                "CC Pack | 100 | 20"
            )
            return True

        try:
            name = parts[0].strip()
            price = float(parts[1].strip())
            stock = int(parts[2].strip())
        except ValueError:
            await update.message.reply_text(
                "❌ Price and Stock must be numbers."
            )
            return True

        conn = db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO products(
                name,
                price,
                stock
            )
            VALUES (?, ?, ?)
            """,
            (name, price, stock),
        )

        conn.commit()
        conn.close()

        context.user_data["admin_add"] = False

        await update.message.reply_text(
            f"✅ <b>PRODUCT ADDED!</b>\n\n"
            f"📦 {name}\n"
            f"💰 ৳{price:g}\n"
            f"📦 Stock: {stock}",
            parse_mode="HTML",
        )

        return True

    # EDIT PRODUCT
    if context.user_data.get("admin_edit"):

        parts = text.split("|")

        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Format:\n\n"
                "Product ID | New Price | New Stock\n\n"
                "Example:\n"
                "1 | 150 | 30"
            )
            return True

        try:
            product_id = int(parts[0].strip())
            price = float(parts[1].strip())
            stock = int(parts[2].strip())
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid numbers."
            )
            return True

        conn = db()
        cur = conn.cursor()

        cur.execute(
            # =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    print(
        "ERROR:",
        context.error
    )


# =========================
# START BOT
# =========================

init_db()

app = Application.builder().token(TOKEN).build()

app.add_handler(
    CommandHandler(
        "start",
        start
    )
)

app.add_handler(
    CommandHandler(
        "admin",
        admin
    )
)

app.add_handler(
    CallbackQueryHandler(
        callback_handler
    )
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        process_text
    )
)

app.add_error_handler(
    error_handler
)

print(
    "🤖 SHOP BOT IS RUNNING..."
)

app.run_polling()
   
