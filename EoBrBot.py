import os
import telebot
import feedparser
import time
from datetime import datetime, timedelta
import re
from html import unescape
from dotenv import load_dotenv
import json

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = '@eobr_bot'
RSS_URL = 'https://pma.brazilo.org/na-rede/feed'
CHECK_INTERVAL = 300
TEMP_FILE = '/tmp/last_check.json'
HISTORY_FILE = '/tmp/posted_links.json'

# Lista de feeds
FEEDS = {
    'PMA Brazilo': 'https://pma.brazilo.org/na-rede/feed',
    'Esperanto Brasil': 'https://esperanto.org.br/feed',
    # Adicione mais feeds aqui
}

# Inicializa o bot
bot = telebot.TeleBot(BOT_TOKEN)

# Comandos do bot
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
Bonvenon al la EoBr-Bot! 🌟

Mi estas roboto kiu aŭtomate kolektas kaj dissendas Esperantajn novaĵojn.

Uzu /help por vidi ĉiujn komandojn.
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
Disponaj komandoj:

/start - Bonvenon al la bot
/help - Montri ĉi tiun helpon
/feeds - Montri ĉiujn fontojn de novaĵoj
/about - Pri la bot
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['feeds'])
def show_feeds(message):
    feeds_text = "Aktivaj fontoj de novaĵoj:\n\n"
    for name, url in FEEDS.items():
        feeds_text += f"📰 {name}\n{url}\n\n"
    bot.reply_to(message, feeds_text)

@bot.message_handler(commands=['about'])
def send_about(message):
    about_text = """
EoBr-Bot - RSS-Roboto por Esperanto-Novaĵoj

Ĉi tiu roboto aŭtomate kolektas kaj dissendas la plej freŝajn novaĵojn pri Esperanto el diversaj fontoj.

Programita de @vekiano
    """
    bot.reply_to(message, about_text)

[... resto das funções existentes ...]

def check_and_send_updates(bot):
    """Verifica e envia atualizações do feed"""
    try:
        last_check = load_last_check()
        print(f"\n📥 Verificando feed RSS em: {datetime.now().strftime('%H:%M:%S')}")
        
        for feed_name, feed_url in FEEDS.items():
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"Nenhuma entrada encontrada no feed: {feed_name}")
                continue
            
            new_entries = []
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    if pub_date > last_check and not is_already_posted(entry.link):
                        new_entries.append(entry)
            
            if not new_entries:
                print(f"Nenhuma entrada nova encontrada em: {feed_name}")
                continue
                
            print(f"📬 Encontradas {len(new_entries)} entradas novas em {feed_name}")
            
            for entry in new_entries[:5]:
                try:
                    if not is_already_posted(entry.link):
                        message = format_message(entry)
                        if message:
                            print(f"\n📤 Enviando: {entry.title}")
                            
                            # Envia para o próprio bot
                            bot.send_message(
                                chat_id="@eobr_bot",  # ID numérico ou username do bot
                                text=message,
                                parse_mode='Markdown',
                                disable_web_page_preview=False
                            )
                            
                            save_posted_link(entry.link)
                            print("✅ Mensagem enviada com sucesso!")
                            time.sleep(2)
                    
                except Exception as e:
                    print(f"❌ Erro ao enviar mensagem: {str(e)}")
        
        save_last_check()
                
    except Exception as e:
        print(f"❌ Erro ao verificar feed: {str(e)}")

def main():
    """Função principal"""
    print("\n=== Bot RSS do Esperanto Brasil ===")
    print(f"📢 Bot: {BOT_USERNAME}")
    print(f"🔗 Feeds: {len(FEEDS)} configurados")
    print(f"⏱️ Intervalo: {CHECK_INTERVAL} segundos")
    
    # Inicia o polling em uma thread separada
    import threading
    polling_thread = threading.Thread(target=bot.polling, args=(True,))
    polling_thread.daemon = True
    polling_thread.start()
    
    while True:
        try:
            check_and_send_updates(bot)
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ Erro no loop principal: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()
