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

# Configure seu bot
BOT_TOKEN = os.getenv('7637289473:AAFiefB-2Am56-GcleFjgp_nBK-5P51kNLo')
CHANNEL_USERNAME = '@esperantobr'
RSS_URL = 'https://pma.brazilo.org/na-rede/feed'
CHECK_INTERVAL = 300  # 5 minutos
HISTORY_FILE = 'posted_links.json'
MAX_HISTORY = 100  # Número máximo de links para manter no histórico

# Inicializa o bot
try:
    print("Iniciando bot...")
    bot = telebot.TeleBot(BOT_TOKEN)
    print("Bot iniciado com sucesso!")
except Exception as e:
    print(f"Erro ao iniciar bot: {str(e)}")
    raise e

def load_posted_links():
    """Carrega o histórico de links já postados"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Erro ao carregar histórico: {str(e)}")
        return []

def save_posted_links(links):
    """Salva o histórico de links já postados"""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(links[-MAX_HISTORY:], f)  # Mantém apenas os últimos MAX_HISTORY links
    except Exception as e:
        print(f"Erro ao salvar histórico: {str(e)}")

def clean_html(text):
    """Remove tags HTML e formata o texto"""
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_message(entry):
    try:
        message = f"*{entry.title}*\n\n"
        
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
        message += f"[Leia o post completo]({entry.link})"
        
        if hasattr(entry, 'published'):
            try:
                date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                message += f"\n\nPublicado em: {date.strftime('%d/%m/%Y %H:%M')}"
            except:
                pass
        
        return message
    except Exception as e:
        print(f"Erro ao formatar mensagem: {str(e)}")
        return None

def check_and_send_updates():
    try:
        print(f"\nVerificando feed RSS em: {datetime.now().strftime('%H:%M:%S')}")
        feed = feedparser.parse(RSS_URL)
        
        if not feed.entries:
            print("Nenhuma entrada encontrada no feed")
            return
        
        print(f"Encontradas {len(feed.entries)} entradas no feed")
        
        # Carrega links já postados
        posted_links = load_posted_links()
        
        # Filtra apenas entradas novas
        new_entries = [
            entry for entry in feed.entries 
            if entry.link not in posted_links and
            hasattr(entry, 'published_parsed') and
            datetime.fromtimestamp(time.mktime(entry.published_parsed)) > datetime.now() - timedelta(days=7)
        ]
        
        if not new_entries:
            print("Nenhuma entrada nova para postar")
            return
            
        print(f"Encontradas {len(new_entries)} entradas novas")
        
        for entry in new_entries[:5]:  # Processa até 5 entradas novas por vez
            try:
                message = format_message(entry)
                if message:
                    print(f"\nEnviando: {entry.title}")
                    bot.send_message(
                        chat_id=CHANNEL_USERNAME,
                        text=message,
                        parse_mode='Markdown',
                        disable_web_page_preview=False
                    )
                    print("✓ Mensagem enviada com sucesso!")
                    
                    # Adiciona link ao histórico
                    posted_links.append(entry.link)
                    save_posted_links(posted_links)
                    
                    time.sleep(2)  # Evita flood
                
            except Exception as e:
                print(f"✗ Erro ao enviar mensagem: {str(e)}")
                
    except Exception as e:
        print(f"Erro ao verificar feed: {str(e)}")

def main():
    print("\n=== Bot RSS do Esperanto Brasil ===")
    print(f"Canal: {CHANNEL_USERNAME}")
    print(f"Feed: {RSS_URL}")
    print(f"Intervalo de verificação: {CHECK_INTERVAL} segundos")
    
    while True:
        try:
            check_and_send_updates()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"Erro no loop principal: {str(e)}")
            time.sleep(60)  # Espera 1 minuto antes de tentar novamente

if __name__ == "__main__":
    main()
