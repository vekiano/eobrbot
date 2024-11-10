import os
import telebot
import feedparser
import time
from datetime import datetime, timedelta
import re
from html import unescape
from dotenv import load_dotenv
import json
import threading

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = '@eobr_bot'
CHECK_INTERVAL = 300  # 5 minutos
TEMP_FILE = '/tmp/last_check.json'
HISTORY_FILE = '/tmp/posted_links.json'

# Lista de feeds
FEEDS = {
    'PMA Brazilo': 'https://pma.brazilo.org/na-rede/feed',
    'Esperanto Brazilo': 'https://esperantobrazilo.blogspot.com/feeds/posts/default',
    'Esperanto Blogo': 'https://esperanto-blogo.blogspot.com/feeds/posts/default',
    'Brazilaj Babiladoj': 'https://brazilajbabiladoj.blogspot.com/feeds/posts/default'
}

# Inicializa o bot
bot = telebot.TeleBot(BOT_TOKEN)

def load_posted_links():
    """Carrega histórico de links já postados"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_posted_link(link):
    """Salva link no histórico"""
    try:
        links = load_posted_links()
        if link not in links:
            links.append(link)
            links = links[-100:]  # Mantém apenas os últimos 100 links
            with open(HISTORY_FILE, 'w') as f:
                json.dump(links, f)
    except Exception as e:
        print(f"Erro ao salvar link: {str(e)}")

def is_already_posted(link):
    """Verifica se o link já foi postado"""
    return link in load_posted_links()

def load_last_check():
    """Carrega a data da última verificação"""
    try:
        if os.path.exists(TEMP_FILE):
            with open(TEMP_FILE, 'r') as f:
                data = json.load(f)
                return datetime.fromisoformat(data['last_check'])
    except:
        pass
    return datetime.now() - timedelta(hours=1)

def save_last_check():
    """Salva a data da última verificação"""
    try:
        with open(TEMP_FILE, 'w') as f:
            json.dump({
                'last_check': datetime.now().isoformat()
            }, f)
    except Exception as e:
        print(f"Erro ao salvar última verificação: {str(e)}")

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

/start - Komenci la boton
/help - Montri ĉi tiun helpon
/feeds - Montri ĉiujn fontojn de novaĵoj
/about - Pri la boto
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

def check_and_send_updates(bot):
    """Verifica e envia atualizações do feed"""
    try:
        last_check = load_last_check()
        print(f"\n📥 Kontrolas RSS-fluojn je: {datetime.now().strftime('%H:%M:%S')}")
        
        for feed_name, feed_url in FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                if not feed.entries:
                    print(f"Neniu enigo trovita en: {feed_name}")
                    continue
                
                new_entries = []
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        if pub_date > last_check and not is_already_posted(entry.link):
                            new_entries.append(entry)
                
                if not new_entries:
                    print(f"Neniu nova enigo en: {feed_name}")
                    continue
                    
                print(f"📬 Trovis {len(new_entries)} novajn enigojn en {feed_name}")
                
                for entry in new_entries[:5]:
                    try:
                        if not is_already_posted(entry.link):
                            message = format_message(entry, feed_name)
                            if message:
                                print(f"\n📤 Sendas: {entry.title}")
                                bot.send_message(
                                    chat_id="@eobr_bot",
                                    text=message,
                                    parse_mode='Markdown',
                                    disable_web_page_preview=False
                                )
                                save_posted_link(entry.link)
                                print("✅ Mesaĝo sukcese sendita!")
                                time.sleep(2)
                        
                    except Exception as e:
                        print(f"❌ Eraro dum sendo de mesaĝo: {str(e)}")
                        
            except Exception as e:
                print(f"❌ Eraro dum kontrolo de fluo {feed_name}: {str(e)}")
                continue
        
        save_last_check()
                
    except Exception as e:
        print(f"❌ Ĝenerala eraro: {str(e)}")

def main():
    """Função principal"""
    print("\n=== EoBr-Bot - RSS-Roboto por Esperanto-Novaĵoj ===")
    print(f"📢 Bot: {BOT_USERNAME}")
    print(f"🔗 RSS-Fluoj: {len(FEEDS)} configuritaj")
    print(f"⏱️ Intervalo: {CHECK_INTERVAL} sekundoj")
    
    # Inicia o polling em uma thread separada
    polling_thread = threading.Thread(target=bot.polling, args=(True,))
    polling_thread.daemon = True
    polling_thread.start()
    
    # Loop principal
    while True:
        try:
            check_and_send_updates(bot)
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ Eraro en la ĉefa ciklo: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()
