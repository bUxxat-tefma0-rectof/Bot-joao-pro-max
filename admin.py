from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from database import Database
import json

db = Database()

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.bot_data['admin_id']:
        await update.message.reply_text("❌ Acesso negado!")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Adicionar Produto", callback_data="admin_add_product")],
        [InlineKeyboardButton("📊 Estatísticas", callback_data="admin_stats")],
        [InlineKeyboardButton("🔄 Atualizar Produto", callback_data="admin_update_product")],
        [InlineKeyboardButton("📢 Enviar Anúncio", callback_data="admin_broadcast")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👨‍💻 **Painel Administrativo**\n\n"
        "Selecione uma opção:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "admin_add_product":
        await query.edit_message_text(
            "📝 **Adicionar Novo Produto**\n\n"
            "Por favor, envie os dados do produto no formato:\n\n"
            "`Nome|Descrição|Preço|Estoque|Dias Garantia`\n\n"
            "Exemplo:\n"
            "`Netflix Premium|Acesso premium à Netflix|29.90|100|30`",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_product'] = True
    
    elif data == "admin_stats":
        stats = get_admin_stats()
        await query.edit_message_text(stats, parse_mode='Markdown')

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.bot_data['admin_id']:
        return

    if context.user_data.get('awaiting_product'):
        try:
            data = update.message.text.split('|')
            if len(data) >= 5:
                name = data[0].strip()
                description = data[1].strip()
                price = float(data[2].strip())
                stock = int(data[3].strip())
                warranty = int(data[4].strip())
                
                product_id = db.add_product(name, description, price, stock, warranty)
                
                await update.message.reply_text(
                    f"✅ **Produto adicionado com sucesso!**\n\n"
                    f"🆔 ID: {product_id}\n"
                    f"📦 Nome: {name}\n"
                    f"💵 Preço: R$ {price:.2f}\n"
                    f"📥 Estoque: {stock}\n"
                    f"♻️ Garantia: {warranty} dias",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Formato inválido!")
            
            context.user_data['awaiting_product'] = False
            
        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao adicionar produto: {str(e)}")
            context.user_data['awaiting_product'] = False

def get_admin_stats():
    # Implementar estatísticas administrativas
    total_users = 100  # Placeholder
    total_products = 50  # Placeholder
    total_sales = 1000  # Placeholder
    total_revenue = 5000.00  # Placeholder
    
    return (
        "📊 **Estatísticas da Loja**\n\n"
        f"👥 Total de Usuários: {total_users}\n"
        f"📦 Total de Produtos: {total_products}\n"
        f"🛒 Total de Vendas: {total_sales}\n"
        f"💰 Receita Total: R$ {total_revenue:.2f}\n"
        f"📈 Ticket Médio: R$ {total_revenue/total_sales:.2f}"
    )
