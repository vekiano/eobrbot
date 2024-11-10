import os
import telebot
import feedparser
import time
from datetime import datetime, timedelta
import re
from html import unescape
from collections import deque

# Configurações do bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = '@eobr_bot'
CHECK_INTERVAL = 300  # 5 minutos

# Lista de feeds
FEEDS = {
    'PMA Brazilo': 'https://pma.brazilo.org/na-rede/feed',
    'Esperanto Brazilo': 'https://esperantobrazilo.blogspot.com/feeds/posts/default',
    'Esperanto Blogo': 'https://esperanto-blogo.blogspot.com/feeds/posts/default',
    'Brazilaj Babiladoj': 'https://brazilajbabiladoj.blogspot.com/feeds/posts/default'
}

# Inicialização
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
posted_links = deque(maxlen=1000)
last_check = datetime.now() - timedelta(hours=1)

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_message(entry, source_name):
    try:
        message = f"*{entry.title}*\n"
        message += f"📰 Via {source_name}\n\n"
        
        if hasattr(entry, 'content'):
            content = entry.content[0].value
        elif hasattr(entry, 'description'):
            content = entry.description
        else:
            content = ""
            
        content = clean_html(content)
        if len(content) > 800:
            content = content[:800] + "..."
            
        message += f"{content}\n\n"
        message += f"[Legi pli →]({entry.link})"
        
        if hasattr(entry, 'published'):
            try:
                date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                message += f"\n\n📅 {date.strftime('%d/%m/%Y %H:%M')}"
            except:
                pass
        
        return message
    except Exception as e:
        print(f"Erro ao formatar mensagem: {str(e)}")
        return None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, """
Bonvenon al la EoBr-Bot! 🌟

Mi estas roboto kiu aŭtomate kolektas kaj dissendas Esperantajn novaĵojn.

Uzu /help por vidi ĉiujn komandojn.
    """)

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, """
Disponaj komandoj:

/start - Komenci la boton
/help - Montri ĉi tiun helpon
/feeds - Montri ĉiujn fontojn de novaĵoj
/about - Pri la boto
/status - Montri la staton de la boto
    """)

@bot.message_handler(commands=['feeds'])
def show_feeds(message):
    feeds_text = "Aktivaj fontoj de novaĵoj:\n\n"
    for name, url in FEEDS.items():
        feeds_text += f"📰 {name}\n{url}\n\n"
    bot.reply_to(message, feeds_text)

@bot.message_handler(commands=['about'])
def send_about(message):
    bot.reply_to(message, """
EoBr-Bot - RSS-Roboto por Esperanto-Novaĵoj

Ĉi tiu roboto aŭtomate kolektas kaj dissendas la plej freŝajn novaĵojn pri Esperanto el diversaj fontoj.

Programita de @vekiano
    """)

@bot.message_handler(commands=['status'])
def send_status(message):
    status = f"""
Bot Status:

📡 Bot: {BOT_USERNAME}
🕒 Última verificação: {last_check.strftime('%d/%m/%Y %H:%M:%S')}
📚 Links processados: {len(posted_links)}
📰 Feeds monitorados: {len(FEEDS)}
⏱️ Intervalo: {CHECK_INTERVAL} segundos
    """
    bot.reply_to(message, status)

def check_feeds():
    global last_check
    current_time = datetime.now()
    
    for feed_name, feed_url in FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
            
            for entry in feed.entries[:5]:
                if hasattr(entry, 'published_parsed') and hasattr(entry, 'link'):
                    pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    
                    if pub_date > last_check and entry.link not in posted_links:
                        message = format_message(entry, feed_name)
                        if message:
                            try:
                                bot.send_message(
                                    chat_id="@eobr_bot",
                                    text=message,
                                    parse_mode='Markdown',
                                    disable_web_page_preview=False
                                )
                                posted_links.append(entry.link)
                                time.sleep(2)
                            except Exception as e:
                                print(f"Erro ao enviar mensagem: {str(e)}")
                                
        except Exception as e:
            print(f"Erro ao processar feed {feed_name}: {str(e)}")
            continue
    
    last_check = current_time

def main():
    print("\n=== EoBr-Bot - RSS-Roboto por Esperanto-Novaĵoj ===")
    print(f"📢 Bot: {BOT_USERNAME}")
    print(f"🔗 RSS-Fluoj: {len(FEEDS)} configuritaj")
    print(f"⏱️ Intervalo: {CHECK_INTERVAL} segundos")
    
    while True:
        try:
            # Verifica atualizações do bot
            bot.polling(non_stop=False, interval=0, timeout=30)
            
            # Verifica feeds
            check_feeds()
            
            # Aguarda próximo ciclo
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Erro: {str(e)}")
            time.sleep(60)  # Espera 1 minuto antes de tentar novamente

if __name__ == "__main__":
    main()
