import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from datetime import datetime, timedelta
import sqlite3
import json
import io

from config import BOT_TOKEN, ADMIN_ID, SHOP_NAME, MIN_RECHARGE, SUPPORT_GROUP, CUSTOMER_GROUP
from database import Database
from payment import PaymentProcessor
from admin import admin_panel, handle_admin_callback, handle_admin_message

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Estados da conversação
AWAITING_RECHARGE_AMOUNT, AWAITING_PRODUCT_SEARCH = range(2)

class ShopBot:
    def __init__(self):
        self.db = Database()
        self.payment_processor = PaymentProcessor()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        # Registrar usuário se não existir
        self.db.create_user(user_id, user.username)
        
        # Mensagem de boas-vindas
        welcome_text = (
            "🥇 **Descubra como nosso bot pode transformar sua experiência de compras!**\n\n"
            "Ele facilita a busca por diversos produtos e serviços, garantindo que você encontre "
            "o que precisa com o melhor preço e excelente custo-benefício.\n\n"
            "**Importante:** Não realizamos reembolsos em dinheiro. O suporte estará disponível "
            "por até 48 horas após a entrega das informações, com reembolso em créditos no bot, se necessário.\n\n"
            f"👥 **Grupo De Clientes:** {CUSTOMER_GROUP}\n\n"
            f"👨‍💻 **Link De Suporte:** {SUPPORT_GROUP}\n\n"
            "ℹ️ **Seus Dados:**\n"
            f"🆔 **ID:** `{user_id}`\n"
            "💸 **Saldo Atual:** R$0,00\n"
            f"🪪 **Usuário:** @{user.username if user.username else 'Não informado'}\n\n"
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSltpwF6kTey6ImHK0Z76OBq2AmdNgMsS7irFzm7Xv4Ji9whMxq-eD6PO2Y&s=10"
        )
        
        # Teclado principal
        keyboard = [
            [InlineKeyboardButton("💎 Logins | Contas Premium", callback_data="premium_products")],
            [
                InlineKeyboardButton("🪪 PERFIL", callback_data="profile"),
                InlineKeyboardButton("💰 RECARGA", callback_data="recharge")
            ],
            [
                InlineKeyboardButton("🎖️ Ranking", callback_data="ranking"),
                InlineKeyboardButton("👩‍💻 Suporte", url=SUPPORT_GROUP)
            ],
            [
                InlineKeyboardButton("ℹ️ Informações", callback_data="info"),
                InlineKeyboardButton("🔎 Pesquisar Serviços", callback_data="search_services")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def premium_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        balance = user_data[2] if user_data else 0.0
        
        products = self.db.get_products('premium')
        
        text = (
            f"🎟️ **Logins Premium | Acesso Exclusivo**\n\n"
            f"🏦 **Carteira**\n"
            f"💸 **Saldo Atual:** R$ {balance:.2f}\n\n"
            "**Produtos Disponíveis:**\n"
        )
        
        keyboard = []
        for product in products:
            product_id, name, description, price, stock, warranty, category, is_active, sales_count = product
            if is_active and stock > 0:
                keyboard.append([InlineKeyboardButton(
                    f"{name} - R$ {price:.2f}", 
                    callback_data=f"product_{product_id}"
                )])
        
        keyboard.append([InlineKeyboardButton("↩️ Voltar", callback_data="back_to_start")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[1])
        product = self.db.get_product(product_id)
        
        if not product:
            await query.edit_message_text("❌ Produto não encontrado!")
            return
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        balance = user_data[2] if user_data else 0.0
        
        product_id, name, description, price, stock, warranty, category, is_active, sales_count = product
        
        text = (
            f"⚜️ **ACESSO: {name}** ⚜️\n\n"
            f"💵 **Preço:** R$ {price:.2f}\n"
            f"💼 **Saldo Atual:** R$ {balance:.2f}\n"
            f"📥 **Estoque Disponível:** {stock}\n\n"
            f"🗒️ **Descrição:** {description}\n\n"
            "**Aviso Importante:**\n"
            "O acesso é disponibilizado na hora. Não atendemos ligações nem ouvimos mensagens de áudio; "
            "pedimos que aguarde sua vez.\n"
            "Informamos que não realizamos reembolsos via Pix, apenas em créditos no bot, correspondendo "
            "aos dias restantes até o vencimento.\n"
            "Agradecemos pela compreensão e desejamos boas compras!\n\n"
            f"♻️ **Garantia:** {warranty} dias"
        )
        
        keyboard = [
            [InlineKeyboardButton("🛒 Comprar", callback_data=f"buy_{product_id}")],
            [InlineKeyboardButton("↩️ Voltar", callback_data="premium_products")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def buy_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[1])
        product = self.db.get_product(product_id)
        
        if not product:
            await query.edit_message_text("❌ Produto não encontrado!")
            return
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        balance = user_data[2] if user_data else 0.0
        
        product_id, name, description, price, stock, warranty, category, is_active, sales_count = product
        
        if balance < price:
            missing = price - balance
            text = (
                f"❌ **Saldo insuficiente! Faltam R$ {missing:.2f}**\n\n"
                f"**Faça uma recarga e tente novamente.**\n"
                f"💸 **Seu saldo:** R$ {balance:.2f}"
            )
            
            keyboard = [
                [InlineKeyboardButton("💰 Recarregar", callback_data="recharge")],
                [InlineKeyboardButton("↩️ Voltar", callback_data=f"product_{product_id}")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        if stock <= 0:
            await query.edit_message_text("❌ Produto sem estoque disponível!")
            return
        
        # Processar compra
        self.db.update_user_balance(user.id, -price)
        self.db.update_product_stock(product_id, 1)
        self.db.increment_product_sales(product_id)
        
        # Gerar credenciais (simulado)
        credentials = f"Email: user{user.id}@service.com\nSenha: password123"
        
        # Registrar pedido
        order_id = self.db.create_order(user.id, product_id, 1, price, credentials)
        
        text = (
            f"✅ **Compra realizada com sucesso!**\n\n"
            f"📦 **Produto:** {name}\n"
            f"💰 **Valor:** R$ {price:.2f}\n"
            f"🆔 **Pedido:** #{order_id}\n\n"
            f"🔐 **Credenciais:**\n```\n{credentials}\n```\n\n"
            f"♻️ **Garantia:** {warranty} dias\n\n"
            "📞 **Suporte:** " + SUPPORT_GROUP
        )
        
        keyboard = [
            [InlineKeyboardButton("🛍️ Ver Mais Produtos", callback_data="premium_products")],
            [InlineKeyboardButton("🪪 Perfil", callback_data="profile")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        
        if not user_data:
            await query.edit_message_text("❌ Usuário não encontrado!")
            return
        
        user_id, username, balance, affiliate_code, referred_by, total_recharged, total_purchases, total_gift_rescued, reg_date = user_data
        
        # Buscar estatísticas do usuário
        orders = self.db.get_user_orders(user.id)
        
        text = (
            "🙋‍♂️ **Meu Perfil**\n\n"
            "🔎 **Veja aqui os detalhes da sua conta:**\n\n"
            "👤 **Informações:**\n"
            f"🆔 **ID da Carteira:** `{user_id}`\n"
            f"💰 **Saldo Atual:** R$ {balance:.2f}\n\n"
            "📊 **Suas movimentações:**\n"
            f"— 🛒 **Compras Realizadas:** {len(orders)}\n"
            f"— 💠 **Pix Inseridos:** {total_recharged:.2f}\n"
            f"— 🎁 **Gifts Resgatados:** R$ {total_gift_rescued:.2f}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🛍️ Histórico De Compras", callback_data="purchase_history")],
            [InlineKeyboardButton("↩️ Voltar", callback_data="back_to_start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def purchase_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        orders = self.db.get_user_orders(user.id)
        
        # Criar arquivo de histórico
        history_text = f"HISTORICO DETALHADO\n{SHOP_NAME}\n" + "_" * 30 + "\n\nCOMPRAS:\n"
        
        for order in orders:
            order_id, user_id, product_id, quantity, total_price, status, order_date, credentials, product_name = order
            history_text += f"\n📦 {product_name}\n"
            history_text += f"   💵 R$ {total_price:.2f}\n"
            history_text += f"   📅 {order_date}\n"
            history_text += f"   🆔 #{order_id}\n"
            history_text += "-" * 20 + "\n"
        
        history_text += "\nPAGAMENTOS:\n[Histórico de pagamentos será implementado]"
        
        # Enviar como arquivo
        file = io.BytesIO(history_text.encode())
        file.name = "historico_compras.txt"
        
        await context.bot.send_document(
            chat_id=user.id,
            document=InputFile(file, filename="historico_compras.txt"),
            caption="📄 **Seu histórico de compras**"
        )

    async def recharge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_data = self.db.get_user(user.id)
        balance = user_data[2] if user_data else 0.0
        
        text = (
            f"💼 **ID da Carteira:** `{user.id}`\n"
            f"💵 **Saldo Disponível:** R$ {balance:.2f}\n\n"
            "💡 **Selecione uma opção para recarregar:**"
        )
        
        keyboard = [
            [InlineKeyboardButton("PUSHIN PAY", callback_data="recharge_payment")],
            [InlineKeyboardButton("↩️ Voltar", callback_data="back_to_start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def recharge_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        text = (
            "ℹ️ **Informe o valor que deseja recarregar:**\n\n"
            f"🔻 **Recarga mínima:** R$ {MIN_RECHARGE:.2f}\n\n"
            "⚠️ **Por favor, envie o valor que deseja recarregar agora.**\n\n"
            f"**{SHOP_NAME}**\n"
            "Informe o valor que deseja recarregar:"
        )
        
        await query.edit_message_text(text, parse_mode='Markdown')
        return AWAITING_RECHARGE_AMOUNT

    async def handle_recharge_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            amount = float(update.message.text.replace(',', '.'))
            
            if amount < MIN_RECHARGE:
                await update.message.reply_text(
                    f"❌ Valor mínimo de recarga é R$ {MIN_RECHARGE:.2f}"
                )
                return AWAITING_RECHARGE_AMOUNT
            
            # Processar pagamento com Stripe
            payment_result = self.payment_processor.create_payment_intent(amount)
            
            if not payment_result['success']:
                await update.message.reply_text("❌ Erro ao processar pagamento!")
                return ConversationHandler.END
            
            # Simulação de dados de pagamento (substituir pela integração real)
            expiry_time = datetime.now() + timedelta(minutes=30)
            
            text = (
                "**Gerando pagamento...**\n\n"
                "💰 **Comprar Saldo com Pix Automático:**\n\n"
                f"⏱️ **Expira em:** {expiry_time.strftime('%H:%M')}\n"
                f"💵 **Valor:** R$ {amount:.2f}\n"
                f"✨ **ID da Recarga:** {payment_result['payment_intent_id'][-8:]}\n\n"
                "🗞️ **Atenção:** Este código é válido para apenas um único pagamento.\n"
                "Se você utilizá-lo mais de uma vez, o saldo adicional será perdido sem direito a reembolso.\n\n"
                "💎 **Pix Copia e Cola:**\n"
                "```\n00020126580014br.gov.bcb.pix0136aae0d5a-8a7d-4c3a-9b2e-1f3a5b7c9d12f5204000053039865406"
                f"{amount:.2f}5802BR5925{SHOP_NAME}6008Sao Paulo62360532aae0d5a8a7d4c3a9b2e1f3a5b7c9d126304\n```\n\n"
                "💡 **Dica:** Clique no código acima para copiar.\n\n"
                "🇧🇷 **Após o pagamento, seu saldo será liberado instantaneamente.**"
            )
            
            keyboard = [[InlineKeyboardButton("⏰ Aguardando Pagamento", callback_data="check_payment")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
            
            # Armazenar dados da recarga
            context.user_data['recharge_data'] = {
                'amount': amount,
                'payment_intent_id': payment_result['payment_intent_id'],
                'expiry_time': expiry_time
            }
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text("❌ Por favor, envie um valor numérico válido!")
            return AWAITING_RECHARGE_AMOUNT

    async def ranking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        text = "🏆 **Ranking**\n\nSelecione uma categoria:"
        
        keyboard = [
            [InlineKeyboardButton("📊 Serviços", callback_data="ranking_services")],
            [InlineKeyboardButton("💰 Recargas", callback_data="ranking_recharges")],
            [InlineKeyboardButton("🛒 Compras", callback_data="ranking_purchases")],
            [InlineKeyboardButton("🎁 Gift Card", callback_data="ranking_gifts")],
            [InlineKeyboardButton("💎 Saldo", callback_data="ranking_balance")],
            [InlineKeyboardButton("↩️ Voltar", callback_data="back_to_start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def ranking_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        top_products = self.db.get_top_products()
        
        text = "🏆 **Ranking dos serviços mais vendidos (deste mês)**\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4°)", "5°)", "6°)", "7°)", "8°)", "9°)", "10°)"]
        
        for i, (name, sales_count) in enumerate(top_products):
            if i < len(medals):
                text += f"{medals[i]} {name} - Com {sales_count} pedidos\n"
            else:
                text += f"{i+1}°) {name} - Com {sales_count} pedidos\n"
        
        keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="ranking")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # Implementar outros rankings de forma similar...

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        text = (
            "ℹ️ **SOFTWARE INFO:**\n"
            f"🤖 **BOT:** {SHOP_NAME}\n"
            "🤖 **VERSION:** 2.0\n\n"
            "🛠️ **DEVELOPER INFO:**\n"
            "O Desenvolvedor não possui responsabilidade alguma sobre este Bot e nem sobre o adm do mesmo, "
            "caso entre em contato para reclamar sobre material ou pedir para chamar o adm deste Bot ou algo do tipo, "
            "será bloqueado de imediato... Apenas o chame, caso queira conhecer os Bots disponíveis."
        )
        
        keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def search_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔍 **Pesquisar Serviços**\n\n"
            f"Digite o nome do produto que deseja procurar:\n\n"
            f"Exemplo: `Netflix` ou `Premium`"
        )
        
        return AWAITING_PRODUCT_SEARCH

    async def handle_product_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        search_term = update.message.text.lower()
        products = self.db.get_products('premium')
        
        found_products = []
        for product in products:
            product_id, name, description, price, stock, warranty, category, is_active, sales_count = product
            if search_term in name.lower() and is_active:
                found_products.append(product)
        
        if not found_products:
            await update.message.reply_text("❌ Nenhum produto encontrado!")
            return ConversationHandler.END
        
        text = "🔍 **Resultados da Pesquisa:**\n\n"
        
        for product in found_products[:5]:  # Limitar a 5 resultados
            product_id, name, description, price, stock, warranty, category, is_active, sales_count = product
            short_desc = (description[:50] + '...') if len(description) > 50 else description
            text += f"**{name}** - R$ {price:.2f}\n"
            text += f"Descrição: {short_desc}\n\n"
        
        keyboard = [[InlineKeyboardButton("🛒 Ver Produtos", callback_data="premium_products")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return ConversationHandler.END

    # Comandos de texto
    async def handle_pix_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            amount = float(context.args[0].replace(',', '.'))
            
            if amount < MIN_RECHARGE:
                await update.message.reply_text(f"❌ Valor mínimo é R$ {MIN_RECHARGE:.2f}")
                return
            
            # Similar ao processo de recarga...
            await update.message.reply_text(f"💰 Processando recarga de R$ {amount:.2f}...")
            
        except (IndexError, ValueError):
            await update.message.reply_text(
                "❌ **Formato incorreto!**\n\n"
                "Use: `/pix valor`\n\n"
                "**Exemplos:**\n"
                "`/pix 10`\n"
                "`/pix 6.26`",
                parse_mode='Markdown'
            )

    async def handle_id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(f"🆔 **Seu ID é:** `{user.id}`", parse_mode='Markdown')

    async def handle_afiliados_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        
        if user_data:
            affiliate_code = user_data[3] or f"ref_{user.id}"
            total_affiliates = 0  # Implementar contagem de afiliados
            
            text = (
                "ℹ️ **Status:**\n\n"
                f"📊 **Comissão por Indicação:** {50}%\n"
                f"👥 **Total de Afiliados:** {total_affiliates}\n"
                f"🔗 **Link para Indicar:** https://t.me/{context.bot.username}?start={affiliate_code}\n\n"
                "**Como Funciona?**\n"
                "Copie seu link de indicação e envie para outras pessoas.\n"
                "Cada vez que alguém indicado por você fizer uma recarga no bot, você receberá uma porcentagem desse valor!\n\n"
                f"**Exemplo:** Com uma comissão de 50%, se 5 pessoas indicadas recarregarem R$10,00 cada, você receberá R$25,00.\n\n"
                "Indique mais e aumente seus ganhos!"
            )
        else:
            text = "❌ Erro ao carregar informações de afiliados."
        
        await update.message.reply_text(text, parse_mode='Markdown')

def main():
    # Criar aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Inicializar bot
    shop_bot = ShopBot()
    
    # Configurar dados do bot
    application.bot_data['admin_id'] = ADMIN_ID
    
    # Handlers de comando
    application.add_handler(CommandHandler("start", shop_bot.start))
    application.add_handler(CommandHandler("pix", shop_bot.handle_pix_command))
    application.add_handler(CommandHandler("id", shop_bot.handle_id_command))
    application.add_handler(CommandHandler("afiliados", shop_bot.handle_afiliados_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Handler de conversação para recarga
    recharge_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(shop_bot.recharge_payment, pattern="^recharge_payment$")],
        states={
            AWAITING_RECHARGE_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shop_bot.handle_recharge_amount)
            ]
        },
        fallbacks=[]
    )
    application.add_handler(recharge_conv)
    
    # Handler de conversação para pesquisa
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(shop_bot.search_services, pattern="^search_services$")],
        states={
            AWAITING_PRODUCT_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, shop_bot.handle_product_search)
            ]
        },
        fallbacks=[]
    )
    application.add_handler(search_conv)
    
    # Handlers de callback
    application.add_handler(CallbackQueryHandler(shop_bot.premium_products, pattern="^premium_products$"))
    application.add_handler(CallbackQueryHandler(shop_bot.show_product, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(shop_bot.buy_product, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(shop_bot.profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(shop_bot.purchase_history, pattern="^purchase_history$"))
    application.add_handler(CallbackQueryHandler(shop_bot.recharge, pattern="^recharge$"))
    application.add_handler(CallbackQueryHandler(shop_bot.ranking, pattern="^ranking$"))
    application.add_handler(CallbackQueryHandler(shop_bot.ranking_services, pattern="^ranking_services$"))
    application.add_handler(CallbackQueryHandler(shop_bot.info, pattern="^info$"))
    application.add_handler(CallbackQueryHandler(shop_bot.start, pattern="^back_to_start$"))
    
    # Handlers administrativos
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))
    application.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), handle_admin_message))
    
    # Iniciar bot
    print("🤖 Bot iniciado com sucesso!")
    application.run_polling()

if __name__ == '__main__':
    main()
