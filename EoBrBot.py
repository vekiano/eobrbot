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
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Token deve ser configurado no Railway
CHANNEL_USERNAME = '@esperantobr'
RSS_URL = 'https://pma.brazilo.org/na-rede/feed'
CHECK_INTERVAL = 300  # 5 minutos
TEMP_FILE = '/tmp/last_check.json'  # Arquivo temporário para controle

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
    except:
        pass

def clean_html(text):
    """Remove tags HTML e formata o texto"""
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_message(entry):
    """Formata a mensagem para o Telegram"""
    try:
        # Título
        message = f"*{entry.title}*\n\n"
        
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
        message += f"[Leia o post completo]({entry.link})"
        
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

def check_and_send_updates(bot):
    """Verifica e envia atualizações do feed"""
    try:
        last_check = load_last_check()
        print(f"\n📥 Verificando feed RSS em: {datetime.now().strftime('%H:%M:%S')}")
        
        feed = feedparser.parse(RSS_URL)
        if not feed.entries:
            print("Nenhuma entrada encontrada no feed")
            return
        
        new_entries = []
        for entry in feed.entries:
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                if pub_date > last_check:
                    new_entries.append(entry)
        
        if not new_entries:
            print("Nenhuma entrada nova encontrada")
            return
            
        print(f"📬 Encontradas {len(new_entries)} entradas novas")
        
        for entry in new_entries[:5]:  # Processa até 5 entradas por vez
            try:
                message = format_message(entry)
                if message:
                    print(f"\n📤 Enviando: {entry.title}")
                    bot.send_message(
                        chat_id=CHANNEL_USERNAME,
                        text=message,
                        parse_mode='Markdown',
                        disable_web_page_preview=False
                    )
                    print("✅ Mensagem enviada com sucesso!")
                    time.sleep(2)  # Evita flood
                
            except Exception as e:
                print(f"❌ Erro ao enviar mensagem: {str(e)}")
        
        save_last_check()
                
    except Exception as e:
        print(f"❌ Erro ao verificar feed: {str(e)}")

def main():
    """Função principal"""
    print("\n=== Bot RSS do Esperanto Brasil ===")
    print(f"📢 Canal: {CHANNEL_USERNAME}")
    print(f"🔗 Feed: {RSS_URL}")
    print(f"⏱️ Intervalo: {CHECK_INTERVAL} segundos")
    
    try:
        bot = telebot.TeleBot(BOT_TOKEN)
        print("✅ Bot iniciado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {str(e)}")
        return
    
    while True:
        try:
            check_and_send_updates(bot)
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ Erro no loop principal: {str(e)}")
            time.sleep(60)  # Espera 1 minuto antes de tentar novamente

if __name__ == "__main__":
    main()
