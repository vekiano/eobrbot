import os
import telebot
import feedparser
import time
from datetime import datetime, timedelta
import re
from html import unescape
import json
from threading import Lock

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

# Inicialização do bot com configurações específicas para evitar conflitos
bot = telebot.TeleBot(BOT_TOKEN)
last_check = datetime.now() - timedelta(hours=1)
posted_links = set()
lock = Lock()

def clean_html(text):
    """Remove tags HTML e formata o texto"""
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_message(entry, source_name):
    """Formata a mensagem para o Telegram"""
    try:
        # Título com fonte
        message = f"*{entry.title}*\n"
        message += f"📰 Via {source_name}\n\n"
        
        # Conteúdo
        if hasattr(entry, 'content'):
            content = entry.content[0].value
        elif hasattr(entry, 'description'):
            content = entry.description
        else:
            content = ""
            
        content = clean_html(content)
        
        # Limita tamanho do conteúdo
        if len(content) > 800:
            content = content[:800] + "..."
            
        message += f"{content}\n\n"
        
        # Adiciona link
        message += f"[Legi pli →]({entry.link})"
        
        # Adiciona data se disponível
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

/start - Komenci la boton
/help - Montri ĉi tiun helpon
/feeds - Montri ĉiujn fontojn de novaĵoj
/about - Pri la boto
/status - Montri la staton de la boto
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

@bot.message_handler(commands=['status'])
def send_status(message):
    global last_check
    status_text = f"""
Bot Status:

📡 Bot: {BOT_USERNAME}
🕒 Última verificação: {last_check.strftime('%d/%m/%Y %H:%M:%S')}
📚 Links processados: {len(posted_links)}
📰 Feeds monitorados: {len(FEEDS)}
⏱️ Intervalo: {CHECK_INTERVAL} segundos
    """
    bot.reply_to(message, status_text)

def check_feeds():
    global last_check
    
    while True:
        try:
            with lock:
                current_time = datetime.now()
                print(f"\n📥 Verificando feeds em: {current_time.strftime('%H:%M:%S')}")
                
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
                                            posted_links.add(entry.link)
                                            # Limita o tamanho do set para evitar uso excessivo de memória
                                            if len(posted_links) > 1000:
                                                posted_links.clear()
                                            time.sleep(2)
                                        except Exception as e:
                                            print(f"Erro ao enviar mensagem: {str(e)}")
                                            
                    except Exception as e:
                        print(f"Erro ao processar feed {feed_name}: {str(e)}")
                        continue
                
                last_check = current_time
                
        except Exception as e:
            print(f"Erro geral: {str(e)}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    print("Iniciando EoBr-Bot...")
    
    # Inicia verificação de feeds em background
    import threading
    feed_thread = threading.Thread(target=check_feeds)
    feed_thread.daemon = True
    feed_thread.start()
    
    # Inicia o bot com configurações para evitar conflitos
    bot.infinity_polling(timeout=60, long_polling_timeout=30, allowed_updates=["message"])
