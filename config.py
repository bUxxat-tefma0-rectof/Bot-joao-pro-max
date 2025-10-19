import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do Bot
BOT_TOKEN = os.getenv('BOT_TOKEN', '8464485123:AAGfibOpvx6ASRrcepmQJlZ1GuoAAYml6Ws')
ADMIN_ID = int(os.getenv('ADMIN_ID', '6995978182'))

# Configurações do Stripe
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY', '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')

# Configurações da Loja
SHOP_NAME = "@SuaLoja"
MIN_RECHARGE = 1.00
SUPPORT_GROUP = "https://t.me/seu_suporte"
CUSTOMER_GROUP = "https://t.me/seu_grupo"

# Configurações de Comissão de Afiliados
AFFILIATE_COMMISSION = 0.50  # 50%
