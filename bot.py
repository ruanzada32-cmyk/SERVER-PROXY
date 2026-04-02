import logging
import requests
import random
import string
import io
import json
import os
from datetime import datetime
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

# Canal/ID para Logs
LOG_CHANNEL_ID = ADMIN_ID 

# Arquivo para salvar revendedores (Simples JSON para persistência)
RESELLERS_FILE = "resellers.json"

# ─── ESTADOS DA CONVERSA ─────────────────────────────────────────────────────
(
    GERAR_QTD, GERAR_DIAS,
    DELETAR_KEY,
    CHECAR_KEY,
    UPDATE_KEY, UPDATE_IP,
    ADD_RESELLER_ID, ADD_RESELLER_SALDO,
    REM_RESELLER_ID,
) = range(9)

# ─── LOGGING ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── BANCO DE DADOS LOCAL (REVENDA) ──────────────────────────────────────────
def load_resellers():
    if os.path.exists(RESELLERS_FILE):
        with open(RESELLERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_resellers(data):
    with open(RESELLERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_ID

def is_reseller(user_id: int) -> bool:
    resellers = load_resellers()
    return str(user_id) in resellers

def get_reseller_balance(user_id: int) -> int:
    resellers = load_resellers()
    return resellers.get(str(user_id), {}).get("balance", 0)

def update_reseller_balance(user_id: int, amount: int):
    resellers = load_resellers()
    uid = str(user_id)
    if uid in resellers:
        resellers[uid]["balance"] += amount
        save_resellers(resellers)
        return True
    return False

def api_get(endpoint: str, params: dict) -> dict:
    try:
        params["key"] = API_KEY
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        data = r.json() if r.text else {}
        is_ok = data.get("status") == "success"
        return {"ok": is_ok, "data": data, "raw": r.text}
    except Exception as e:
        logger.error(f"Erro na chamada API: {e}")
        return {"ok": False, "error": str(e)}

async def send_log(context: ContextTypes.DEFAULT_TYPE, message: str):
    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"🔔 <b>LOG DE ATIVIDADE</b>\n\n{message}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Erro ao enviar log: {e}")

def menu_keyboard(user_id: int):
    buttons = [
        [InlineKeyboardButton("🔑 Gerar Keys",    callback_data="menu_gerar")],
        [InlineKeyboardButton("🔍 Checar Key",   callback_data="menu_checar")],
        [InlineKeyboardButton("🌐 Atualizar IP", callback_data="menu_update_ip")],
    ]
    
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("🗑️ Deletar Key",  callback_data="menu_deletar")])
        buttons.append([InlineKeyboardButton("👥 Revendedores", callback_data="menu_resellers")])
        buttons.append([InlineKeyboardButton("📊 Estatísticas", callback_data="menu_stats")])
    
    return InlineKeyboardMarkup(buttons)

BANNER = (
    "╔══════════════════════════════╗\n"
    "║   🤖  <b>PAINEL DE CONTROLE</b>      ║\n"
    "║      Gerenciador de Keys     ║\n"
    "╚══════════════════════════════╝\n\n"
    "Escolha uma opção abaixo 👇"
)

# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(update) and not is_reseller(user_id):
        await update.message.reply_text("⛔ Acesso negado.")
        return

    msg = BANNER
    if is_reseller(user_id):
        balance = get_reseller_balance(user_id)
        msg += f"\n\n💰 <b>Seu Saldo:</b> {balance} keys"

    await update.message.reply_text(
        msg,
        parse_mode="HTML",
        reply_markup=menu_keyboard(user_id),
    )

# ─── CALLBACK DO MENU ─────────────────────────────────────────────────────────
async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    if not is_admin(update) and not is_reseller(user_id):
        await query.edit_message_text("⛔ Acesso negado.")
        return

    data = query.data

    if data == "menu_gerar":
        await query.edit_message_text(
            "🔑 <b>GERAR KEYS</b>\n\n"
            "Quantas chaves você deseja gerar? (Ex: 1, 5, 10):",
            parse_mode="HTML",
        )
        return GERAR_QTD

    elif data == "menu_deletar" and user_id == ADMIN_ID:
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

    elif data == "menu_resellers" and user_id == ADMIN_ID:
        resellers = load_resellers()
        msg = "👥 <b>GERENCIAR REVENDEDORES</b>\n\n"
        if not resellers:
            msg += "Nenhum revendedor cadastrado."
        else:
            for rid, info in resellers.items():
                msg += f"• ID: <code>{rid}</code> | Saldo: {info['balance']}\n"
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Adicionar", callback_data="reseller_add"), 
             InlineKeyboardButton("➖ Remover", callback_data="reseller_rem")],
            [InlineKeyboardButton("🏠 Voltar", callback_data="menu_voltar")]
        ])
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
        return ConversationHandler.END

    elif data == "reseller_add" and user_id == ADMIN_ID:
        await query.edit_message_text("👤 Digite o <b>ID do Telegram</b> do novo revendedor:")
        return ADD_RESELLER_ID

    elif data == "reseller_rem" and user_id == ADMIN_ID:
        await query.edit_message_text("👤 Digite o <b>ID do Telegram</b> para remover:")
        return REM_RESELLER_ID

    elif data == "menu_stats" and user_id == ADMIN_ID:
        resellers = load_resellers()
        total_balance = sum(r['balance'] for r in resellers.values())
        await query.edit_message_text(
            "📊 <b>ESTATÍSTICAS</b>\n\n"
            f"👥 <b>Revendedores:</b> {len(resellers)}\n"
            f"💰 <b>Total Saldo Revendas:</b> {total_balance}\n"
            f"📅 <b>Data:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Voltar", callback_data="menu_voltar")]])
        )
        return ConversationHandler.END

    elif data == "menu_voltar":
        msg = BANNER
        if is_reseller(user_id):
            balance = get_reseller_balance(user_id)
            msg += f"\n\n💰 <b>Seu Saldo:</b> {balance} keys"
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=menu_keyboard(user_id))
        return ConversationHandler.END

# ─── FLUXO: GERAR KEYS ───────────────────────────────────────────────────────
async def gerar_qtd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    qtd_txt = update.message.text.strip()
    
    if not qtd_txt.isdigit() or int(qtd_txt) <= 0:
        await update.message.reply_text("❌ Número inválido.")
        return GERAR_QTD
    
    qtd = int(qtd_txt)
    
    # Verificar saldo se for revendedor
    if not is_admin(update):
        balance = get_reseller_balance(user_id)
        if qtd > balance:
            await update.message.reply_text(f"❌ Saldo insuficiente! Você tem apenas {balance} créditos.")
            return ConversationHandler.END

    ctx.user_data["gerar_qtd"] = qtd
    await update.message.reply_text(f"✅ Qtd: {qtd}\nInforme os <b>dias</b> de validade:")
    return GERAR_DIAS

async def gerar_dias(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    dias_txt = update.message.text.strip()
    if not dias_txt.isdigit():
        await update.message.reply_text("❌ Dias inválidos.")
        return GERAR_DIAS

    qtd = ctx.user_data["gerar_qtd"]
    dias = int(dias_txt)
    
    await update.message.reply_text(f"⏳ Gerando {qtd} chaves...")

    keys_geradas = []
    for _ in range(qtd):
        resp = api_get("/generate", {"days": dias})
        if resp["ok"]:
            keys_geradas.append(resp["data"].get("key"))

    if keys_geradas:
        # Descontar saldo se for revendedor
        if not is_admin(update):
            update_reseller_balance(user_id, -len(keys_geradas))
        
        await send_log(ctx, f"👤 <b>{'Admin' if user_id == ADMIN_ID else 'Revendedor ' + str(user_id)}</b> gerou {len(keys_geradas)} keys.\n\nKeys:\n<code>" + "\n".join(keys_geradas) + "</code>")

        txt_content = "\n".join(keys_geradas)
        file_stream = io.BytesIO(txt_content.encode('utf-8'))
        file_stream.name = f"keys_{dias}dias.txt"
        
        await update.message.reply_document(
            document=file_stream,
            caption=f"📄 {len(keys_geradas)} keys geradas com sucesso!",
            reply_markup=menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text("❌ Falha ao gerar chaves na API.", reply_markup=menu_keyboard(user_id))
    
    return ConversationHandler.END

# ─── FLUXO: GERENCIAR REVENDEDORES ───────────────────────────────────────────
async def add_reseller_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["new_reseller_id"] = update.message.text.strip()
    await update.message.reply_text("💰 Qual o <b>saldo inicial</b> para este revendedor?")
    return ADD_RESELLER_ID + 1 # ADD_RESELLER_SALDO

async def add_reseller_saldo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rid = ctx.user_data["new_reseller_id"]
    saldo = update.message.text.strip()
    if not saldo.isdigit():
        await update.message.reply_text("❌ Saldo deve ser um número.")
        return ADD_RESELLER_SALDO

    resellers = load_resellers()
    resellers[rid] = {"balance": int(saldo), "added_at": datetime.now().isoformat()}
    save_resellers(resellers)
    
    await update.message.reply_text(f"✅ Revendedor <code>{rid}</code> adicionado com {saldo} créditos!", parse_mode="HTML", reply_markup=menu_keyboard(ADMIN_ID))
    await send_log(ctx, f"👥 Novo revendedor adicionado: <code>{rid}</code> com {saldo} créditos.")
    return ConversationHandler.END

async def rem_reseller_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rid = update.message.text.strip()
    resellers = load_resellers()
    if rid in resellers:
        del resellers[rid]
        save_resellers(resellers)
        await update.message.reply_text(f"✅ Revendedor <code>{rid}</code> removido.", parse_mode="HTML", reply_markup=menu_keyboard(ADMIN_ID))
        await send_log(ctx, f"👥 Revendedor removido: <code>{rid}</code>")
    else:
        await update.message.reply_text("❌ ID não encontrado.")
    return ConversationHandler.END

# ─── OUTROS FLUXOS (MANTIDOS) ────────────────────────────────────────────────
async def deletar_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    resp = api_get("/delete", {"generated_key": key})
    if resp["ok"]:
        await update.message.reply_text(f"✅ Key <code>{key}</code> deletada!", parse_mode="HTML", reply_markup=menu_keyboard(ADMIN_ID))
        await send_log(ctx, f"🗑️ Key deletada: <code>{key}</code>")
    else:
        await update.message.reply_text("❌ Erro ao deletar.")
    return ConversationHandler.END

async def checar_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    resp = api_get("/check", {"generated_key": key})
    if resp["ok"]:
        data = resp["data"]
        msg = f"🔍 <b>Key:</b> <code>{key}</code>\n📅 <b>Expira:</b> {data.get('expire_at')}\n🌐 <b>IP:</b> {data.get('ip')}"
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=menu_keyboard(update.effective_user.id))
    else:
        await update.message.reply_text("❌ Key não encontrada.")
    return ConversationHandler.END

async def update_key(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["update_key"] = update.message.text.strip()
    await update.message.reply_text("🌐 Digite o <b>novo IP</b>:")
    return UPDATE_IP

async def update_ip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    key = ctx.user_data["update_key"]
    ip = update.message.text.strip()
    resp = api_get("/update", {"generated_key": key, "new_ip": ip})
    if resp["ok"]:
        await update.message.reply_text(f"✅ IP atualizado para <code>{ip}</code>", parse_mode="HTML", reply_markup=menu_keyboard(update.effective_user.id))
        await send_log(ctx, f"🌐 IP Atualizado: <code>{key}</code> -> <code>{ip}</code>")
    else:
        await update.message.reply_text("❌ Erro ao atualizar IP.")
    return ConversationHandler.END

async def cancelar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelado.", reply_markup=menu_keyboard(update.effective_user.id))
    return ConversationHandler.END

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_callback)],
        states={
            GERAR_QTD:   [MessageHandler(filters.TEXT & ~filters.COMMAND, gerar_qtd)],
            GERAR_DIAS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, gerar_dias)],
            DELETAR_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, deletar_key)],
            CHECAR_KEY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, checar_key)],
            UPDATE_KEY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, update_key)],
            UPDATE_IP:   [MessageHandler(filters.TEXT & ~filters.COMMAND, update_ip)],
            ADD_RESELLER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reseller_id)],
            ADD_RESELLER_SALDO: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reseller_saldo)],
            REM_RESELLER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, rem_reseller_id)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar), CallbackQueryHandler(menu_callback, pattern="^menu_voltar$")],
        allow_reentry=True,
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
