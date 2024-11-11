import os
import telebot
import feedparser
import time
from datetime import datetime, timedelta
import re
from html import unescape
from collections import deque
import pytz
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN não encontrado nas variáveis de ambiente!")

BOT_USERNAME = '@eobr_bot'
CHANNEL_ID = '@esperantobr'
CHECK_INTERVAL = 900  # 15 minutos

# Configuração do timezone
TIMEZONE_BR = pytz.timezone('America/Sao_Paulo')

# Lista de feeds
FEEDS = {
    'PMA Brazilo': 'https://pma.brazilo.org/na-rede/feed', 
    'Esperanto Brazilo': 'https://esperantobrazilo.blogspot.com/feeds/posts/default',
    'Esperanto Blogo': 'https://esperanto-blogo.blogspot.com/feeds/posts/default'
}

# Inicialização
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
posted_links = deque(maxlen=500)  # Cache de links já postados
last_check = TIMEZONE_BR.localize(datetime.now() - timedelta(hours=1))

def get_br_time():
    """Retorna o horário atual em Brasília"""
    return datetime.now(TIMEZONE_BR)

def remove_webhook():
    """Remove webhook se existir"""
    try:
        print("Removendo webhook...")
        bot.delete_webhook()
        time.sleep(1)
        print("Webhook removido com sucesso!")
    except Exception as e:
        print(f"Erro ao remover webhook: {str(e)}")

def parse_date(date_str):
    """Converte string de data para datetime com timezone"""
    try:
        # Tenta primeiro o formato comum de RSS
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
    except ValueError:
        try:
            # Tenta formato sem timezone
            dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S')
            dt = TIMEZONE_BR.localize(dt)
        except ValueError:
            try:
                # Tenta formato ISO
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                dt = dt.astimezone(TIMEZONE_BR)
            except ValueError:
                return None
    return dt.astimezone(TIMEZONE_BR)

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
        message = f"*{entry.title}*\n"
        message += f"📰 Via {source_name}\n\n"
        
        if hasattr(entry, 'content'):
            content = entry.content[0].value
        elif hasattr(entry, 'description'):
            content = entry.description
        else:
            content = ""
            
        content = clean_html(content)
        if len(content) > 500:
            content = content[:500] + "..."
            
        message += f"{content}\n\n"
        message += f"[Legi pli →]({entry.link})"
        
        if hasattr(entry, 'published'):
            try:
                date = parse_date(entry.published)
                if date:
                    message += f"\n\n📅 {date.strftime('%d/%m/%Y %H:%M')} (BRT)"
            except Exception as e:
                print(f"Erro ao processar data: {str(e)}")
        
        return message
    except Exception as e:
        print(f"Erro ao formatar mensagem: {str(e)}")
        return None

def send_message_to_all(message_text, retry_count=3):
    """Envia mensagem para todos os destinos com retry"""
    destinations = [BOT_USERNAME, CHANNEL_ID]
    
    for destination in destinations:
        for attempt in range(retry_count):
            try:
                bot.send_message(
                    chat_id=destination,
                    text=message_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=False
                )
                print(f"✅ Mensagem enviada com sucesso para {destination}")
                time.sleep(2)  # Intervalo entre envios
                break
            except telebot.apihelper.ApiTelegramException as e:
                print(f"❌ Erro da API do Telegram ({attempt + 1}/{retry_count}): {str(e)}")
                if "Too Many Requests" in str(e):
                    time.sleep(60)
                else:
                    time.sleep(5)
            except Exception as e:
                print(f"❌ Erro genérico ({attempt + 1}/{retry_count}): {str(e)}")
                time.sleep(5)

def check_feeds():
    """Verifica e processa feeds RSS"""
    global last_check
    current_time = get_br_time()
    print(f"\n📥 Verificando feeds em: {current_time.strftime('%H:%M:%S')} (BRT)")
    
    for feed_name, feed_url in FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo == 1:
                print(f"⚠️ Aviso ao processar {feed_name}: {feed.bozo_exception}")
                continue
            
            if not feed.entries:
                print(f"ℹ️ Nenhuma entrada encontrada em: {feed_name}")
                continue
            
            print(f"📚 Processando {feed_name}...")
            for entry in feed.entries[:3]:  # Processa apenas os 3 posts mais recentes
                if hasattr(entry, 'published') and hasattr(entry, 'link'):
                    pub_date = parse_date(entry.published)
                    
                    if pub_date and pub_date > last_check and entry.link not in posted_links:
                        message = format_message(entry, feed_name)
                        if message:
                            try:
                                print(f"📤 Enviando: {entry.title} ({pub_date.strftime('%d/%m/%Y %H:%M')} BRT)")
                                send_message_to_all(message)
                                posted_links.append(entry.link)
                            except Exception as e:
                                print(f"❌ Erro ao enviar mensagem: {str(e)}")
                                
        except Exception as e:
            print(f"❌ Erro ao processar feed {feed_name}: {str(e)}")
            continue
    
    last_check = current_time
    print(f"✅ Verificação concluída em: {get_br_time().strftime('%H:%M:%S')} (BRT)")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Manipula o comando /start"""
    welcome_text = """
Bonvenon al la EoBr-Bot! 🌟

Mi estas roboto kiu aŭtomate kolektas kaj dissendas Esperantajn novaĵojn.

Uzu /help por vidi ĉiujn komandojn.
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
def send_help(message):
    """Manipula o comando /help"""
    help_text = """
Disponaj komandoj:

/start - Komenci la boton
/help - Montri ĉi tiun helpon
/feeds - Montri ĉiujn fontojn de novaĵoj
/about - Pri la boto
/status - Montri la staton de la boto
/force_check - Devigi kontroli la fluojn
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['feeds'])
def show_feeds(message):
    """Manipula o comando /feeds"""
    feeds_text = "Aktivaj fontoj de novaĵoj:\n\n"
    for name, url in FEEDS.items():
        feeds_text += f"📰 {name}\n{url}\n\n"
    bot.reply_to(message, feeds_text)

@bot.message_handler(commands=['about'])
def send_about(message):
    """Manipula o comando /about"""
    about_text = """
EoBr-Bot - RSS-Roboto por Esperanto-Novaĵoj

Ĉi tiu roboto aŭtomate kolektas kaj dissendas la plej freŝajn novaĵojn pri Esperanto el diversaj fontoj.

Programita de @vekiano
    """
    bot.reply_to(message, about_text)

@bot.message_handler(commands=['status'])
def send_status(message):
    """Manipula o comando /status"""
    current_time = get_br_time()
    status = f"""
Bot Status:

📡 Bot
