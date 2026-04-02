import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

# ─── CONFIGURAÇÕES ───────────────────────────────────────────────────────────
BOT_TOKEN = "8778041920:AAFGhVtNSlEPOYHbGUCY-A2OeLZFqFJGHH4"
ADMIN_ID   = 5881589518
API_BASE   = "http://212.227.7.153:9945"
API_KEY    = "43FUHF78FWIUTPULMH"  # sua chave mestra para autenticar na API

# ─── ESTADOS DA CONVERSA ─────────────────────────────────────────────────────
(
    GERAR_NOME, GERAR_DIAS,
    DELETAR_KEY,
    CHECAR_KEY,
    UPDATE_KEY, UPDATE_IP,
) = range(6)

# ─── LOGGING ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

def api_get(endpoint: str, params: dict) -> dict:
    try:
        params["key"] = API_KEY
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return {"ok": True, "data": r.json() if r.text else {}, "raw": r.text}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": str(e)}

def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Gerar Key",    callback_data="menu_gerar")],
        [InlineKeyboardButton("🗑️ Deletar Key",  callback_data="menu_deletar")],
        [InlineKeyboardButton("🔍 Checar Key",   callback_data="menu_checar")],
        [InlineKeyboardButton("🌐 Atualizar IP", callback_data="menu_update_ip")],
    ])

BANNER = (
    "╔══════════════════════════════╗\n"
    "║   🤖  <b>PAINEL DE CONTROLE</b>      ║\n"
    "║      Gerenciador de Keys     ║\n"
    "╚══════════════════════════════╝\n\n"
    "Escolha uma opção abaixo 👇"
)

# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Acesso negado.")
        return

    await update.message.reply_text(
        BANNER,
        parse_mode="HTML",
        reply_markup=menu_keyboard(),
    )

# ─── /menu ────────────────────────────────────────────────────────────────────
async def menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Acesso negado.")
        return

    await update.message.reply_text(
        BANNER,
        parse_mode="HTML",
        reply_markup=menu_keyboard(),
    )

# ─── CALLBACK DO MENU ─────────────────────────────────────────────────────────
async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        await query.edit_message_text("⛔ Acesso negado.")
        return

    data = query.data

    if data == "menu_gerar":
        await query.edit_message_text(
            "🔑 <b>GERAR KEY</b>\n\n"
            "Digite o <b>nome</b> da key que deseja criar:",
            parse_mode="HTML",
        )
        return GERAR_NOME

    elif data == "menu_deletar":
        await query.edit_message_text(
            "🗑️ <b>DELETAR KEY</b>\n\n"
            "Digite a <b>key</b> que deseja deletar:",
            parse_mode="HTML",
        )
        return DELETAR_KEY

    elif data == "menu_checar":
        await query.edit_message_text(
            "🔍 <b>CHECAR KEY</b>\n\n"
            "Digite a <b>key</b> que deseja verificar:",
            parse_mode="HTML",
        )
        return CHECAR_KEY

    elif data == "menu_update_ip":
        await query.edit_message_text(
            "🌐 <b>ATUALIZAR IP</b>\n\n"
            "Digite a <b>key</b> que deseja atualizar o IP:",
            parse_mode="HTML",
        )
        return UPDATE_KEY

    elif data == "menu_voltar":
        await query.edit_message_text(
            BANNER,
            parse_mode="HTML",
            reply_markup=menu_keyboard(),
        )
        return ConversationHandler.END

# ─── FLUXO: GERAR KEY ────────────────────────────────────────────────────────
async def gerar_nome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["gerar_nome"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Nome: <b>{ctx.user_data['gerar_nome']}</b>\n\n"
        "Agora informe a <b>quantidade de dias</b> de validade:",
        parse_mode="HTML",
    )
    return GERAR_DIAS

async def gerar_dias(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dias_txt = update.message.text.strip()
    if not dias_txt.isdigit():
        await update.message.reply_text("❌ Por favor, informe um número válido de dias.")
        return GERAR_DIAS

    nome = ctx.user_data["gerar_nome"]
    dias = int(dias_txt)

    resp = api_get("/generate", {"key": nome, "days": dias})

    if resp["ok"]:
        data = resp["data"]
        msg = (
            "╔══════════════════════════╗\n"
            "║  ✅  <b>KEY GERADA COM SUCESSO</b>  ║\n"
            "╚══════════════════════════╝\n\n"
            f"🔑 <b>Key:</b> <code>{nome}</code>\n"
            f"📅 <b>Dias:</b> {dias}\n"
        )
        if isinstance(data, dict):
            for k, v in data.items():
                msg += f"📌 <b>{k}:</b> <code>{v}</code>\n"
        else:
            msg += f"📄 <b>Resposta:</b> <code>{resp['raw']}</code>\n"
    else:
        msg = f"❌ <b>Erro ao gerar key:</b>\n<code>{resp['error']}</code>"

    await update.message.reply_text(
        msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Voltar ao Menu", callback_data="menu_voltar")]
        ]),
    )
    return ConversationHandler.END

# ─── FLUXO: DELETAR KEY ──────────────────────────────────────────────────────
async def deletar_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    resp = api_get("/delete", {"generated_key": key})

    if resp["ok"]:
        msg = (
            "╔══════════════════════════╗\n"
            "║  🗑️  <b>KEY DELETADA</b>           ║\n"
            "╚══════════════════════════╝\n\n"
            f"🔑 <b>Key:</b> <code>{key}</code>\n"
            f"📄 <b>Resposta:</b> <code>{resp['raw']}</code>"
        )
    else:
        msg = f"❌ <b>Erro ao deletar key:</b>\n<code>{resp['error']}</code>"

    await update.message.reply_text(
        msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Voltar ao Menu", callback_data="menu_voltar")]
        ]),
    )
    return ConversationHandler.END

# ─── FLUXO: CHECAR KEY ───────────────────────────────────────────────────────
async def checar_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    resp = api_get("/check", {"generated_key": key})

    if resp["ok"]:
        data = resp["data"]
        msg = (
            "╔══════════════════════════╗\n"
            "║  🔍  <b>INFORMAÇÕES DA KEY</b>     ║\n"
            "╚══════════════════════════╝\n\n"
            f"🔑 <b>Key:</b> <code>{key}</code>\n"
        )
        if isinstance(data, dict):
            for k, v in data.items():
                msg += f"📌 <b>{k}:</b> <code>{v}</code>\n"
        else:
            msg += f"📄 <b>Resposta:</b> <code>{resp['raw']}</code>\n"
    else:
        msg = f"❌ <b>Erro ao checar key:</b>\n<code>{resp['error']}</code>"

    await update.message.reply_text(
        msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Voltar ao Menu", callback_data="menu_voltar")]
        ]),
    )
    return ConversationHandler.END

# ─── FLUXO: ATUALIZAR IP ─────────────────────────────────────────────────────
async def update_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["update_key"] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Key: <b>{ctx.user_data['update_key']}</b>\n\n"
        "Agora informe o <b>novo IP</b>:",
        parse_mode="HTML",
    )
    return UPDATE_IP

async def update_ip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    new_ip = update.message.text.strip()
    key    = ctx.user_data["update_key"]

    resp = api_get("/update", {"generated_key": key, "new_ip": new_ip})

    if resp["ok"]:
        msg = (
            "╔══════════════════════════╗\n"
            "║  🌐  <b>IP ATUALIZADO</b>          ║\n"
            "╚══════════════════════════╝\n\n"
            f"🔑 <b>Key:</b> <code>{key}</code>\n"
            f"🌐 <b>Novo IP:</b> <code>{new_ip}</code>\n"
            f"📄 <b>Resposta:</b> <code>{resp['raw']}</code>"
        )
    else:
        msg = f"❌ <b>Erro ao atualizar IP:</b>\n<code>{resp['error']}</code>"

    await update.message.reply_text(
        msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Voltar ao Menu", callback_data="menu_voltar")]
        ]),
    )
    return ConversationHandler.END

# ─── CANCELAR ────────────────────────────────────────────────────────────────
async def cancelar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Operação cancelada.",
        reply_markup=menu_keyboard(),
    )
    return ConversationHandler.END

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_callback, pattern="^menu_")],
        states={
            GERAR_NOME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, gerar_nome)],
            GERAR_DIAS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, gerar_dias)],
            DELETAR_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, deletar_key)],
            CHECAR_KEY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, checar_key)],
            UPDATE_KEY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, update_key)],
            UPDATE_IP:   [MessageHandler(filters.TEXT & ~filters.COMMAND, update_ip)],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar),
            CallbackQueryHandler(menu_callback, pattern="^menu_voltar$"),
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu",  menu))
    app.add_handler(conv)

    logger.info("✅ Bot iniciado com sucesso!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
