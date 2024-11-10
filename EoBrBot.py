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
CHANNEL_ID = '@esperantobr'  # Canal principal
CHECK_INTERVAL = 300  # 5 minutos

# Lista de feeds
FEEDS = {
    'PMA Brazilo': 'https://pma.brazilo.org/na-rede/feed' }
   # ,'Esperanto Brazilo': 'https://esperantobrazilo.blogspot.com/feeds/posts/default',
   # 'Esperanto Blogo': 'https://esperanto-blogo.blogspot.com/feeds/posts/default',
   # 'Brazilaj Babiladoj': 'https://brazilajbabiladoj.blogspot.com/feeds/posts/default'


# Inicialização
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
posted_links = deque(maxlen=1000)
last_check = datetime.now() - timedelta(days=1)  # Aumentado para 1 dia para pegar posts mais antigos

def remove_webhook():
    """Remove webhook se existir"""
    try:
        print("Removendo webhook...")
        bot.delete_webhook()
        time.sleep(1)
        print("Webhook removido com sucesso!")
    except Exception as e:
        print(f"Erro ao remover webhook: {str(e)}")

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
                break
            except Exception as e:
                print(f"❌ Tentativa {attempt + 1} falhou para {destination}: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(5)  # Espera 5 segundos antes de tentar novamente
                continue
        time.sleep(2)  # Intervalo entre envios para diferentes destinos

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
    bot.reply_to(message, """
EoBr-Bot - RSS-Roboto por Esperanto-Novaĵoj

Ĉi tiu roboto aŭtomate kolektas kaj dissendas la plej freŝajn novaĵojn pri Esperanto el diversaj fontoj.

Programita de @vekiano
    """)

@bot.message_handler(commands=['status'])
def send_status(message):
    """Manipula o comando /status"""
    status = f"""
Bot Status:

📡 Bot: {BOT_USERNAME}
📢 Canal: {CHANNEL_ID}
🕒 Última verificação: {last_check.strftime('%d/%m/%Y %H:%M:%S')}
📚 Links processados: {len(posted_links)}
📰 Feeds monitorados: {len(FEEDS)}
⏱️ Intervalo: {CHECK_INTERVAL} segundos
    """
    bot.reply_to(message, status)

@bot.message_handler(commands=['force_check'])
def force_check(message):
    """Força uma verificação imediata dos feeds"""
    bot.reply_to(message, "Iniciando verificação forçada dos feeds...")
    check_feeds()
    bot.reply_to(message, "Verificação concluída!")

def check_feeds():
    """Verifica e processa feeds RSS"""
    global last_check
    current_time = datetime.now()
    print(f"\n📥 Verificando feeds em: {current_time.strftime('%H:%M:%S')}")
    
    for feed_name, feed_url in FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"Nenhuma entrada encontrada em: {feed_name}")
                continue
            
            print(f"Processando {feed_name}...")
            for entry in feed.entries[:5]:
                if hasattr(entry, 'published_parsed') and hasattr(entry, 'link'):
                    pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    
                    if pub_date > last_check and entry.link not in posted_links:
                        message = format_message(entry, feed_name)
                        if message:
                            try:
                                print(f"Enviando: {entry.title}")
                                send_message_to_all(message)
                                posted_links.append(entry.link)
                            except Exception as e:
                                print(f"❌ Erro ao enviar mensagem: {str(e)}")
                                
        except Exception as e:
            print(f"❌ Erro ao processar feed {feed_name}: {str(e)}")
            continue
    
    last_check = current_time
    print(f"✅ Verificação concluída em: {datetime.now().strftime('%H:%M:%S')}")

def main():
    """Função principal"""
    print("\n=== EoBr-Bot - RSS-Roboto por Esperanto-Novaĵoj ===")
    print(f"📢 Bot: {BOT_USERNAME}")
    print(f"📢 Canal: {CHANNEL_ID}")
    print(f"🔗 RSS-Fluoj: {len(FEEDS)} configuritaj")
    print(f"⏱️ Intervalo: {CHECK_INTERVAL} segundos")
    
    # Remove webhook antes de iniciar
    remove_webhook()
    
    # Primeira verificação imediata
    check_feeds()
    
    while True:
        try:
            # Processa mensagens do bot
            print("\n👂 Aguardando comandos...")
            bot.polling(non_stop=False, interval=1, timeout=20)
            
            # Verifica feeds periodicamente
            check_feeds()
            
            # Aguarda próximo ciclo
            print(f"\n⏰ Aguardando {CHECK_INTERVAL} segundos...")
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"❌ Erro geral: {str(e)}")
            time.sleep(60)
            remove_webhook()

if __name__ == "__main__":
    main()
