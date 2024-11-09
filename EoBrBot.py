import telebot
import feedparser
import time
from datetime import datetime
import hashlib
import re
from html import unescape

# Configure seu bot
BOT_TOKEN = '7637289473:AAFiefB-2Am56-GcleFjgp_nBK-5P51kNLo'  # Substitua pelo seu token
CHANNEL_USERNAME = '@esperantobr'
RSS_URL = 'https://pma.brazilo.org/na-rede/feed'
CHECK_INTERVAL = 300

# Inicializa o bot
try:
    print("Iniciando bot...")
    bot = telebot.TeleBot(BOT_TOKEN)
    print("Bot iniciado com sucesso!")
except Exception as e:
    print(f"Erro ao iniciar bot: {str(e)}")
    input("Pressione Enter para sair...")
    exit()

def clean_html(text):
    """Remove tags HTML e formata o texto"""
    # Remove tags HTML
    text = re.sub(r'<[^>]+>', '', text)
    # Converte entidades HTML
    text = unescape(text)
    # Remove múltiplas linhas em branco
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Remove espaços extras
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def format_message(entry):
    try:
        # Título formatado em negrito
        message = f"*{entry.title}*\n\n"
        
        # Trata o conteúdo
        if hasattr(entry, 'content'):
            content = entry.content[0].value
        elif hasattr(entry, 'description'):
            content = entry.description
        else:
            content = ""
            
        # Limpa e formata o conteúdo
        content = clean_html(content)
        
        # Limita o tamanho do conteúdo (Telegram tem limite de 4096 caracteres)
        if len(content) > 800:
            content = content[:800] + "..."
            
        message += f"{content}\n\n"
        
        # Adiciona link para o post completo
        message += f"[Leia o post completo]({entry.link})"
        
        # Adiciona data de publicação se disponível
        if hasattr(entry, 'published'):
            try:
                # Converte a data para formato mais amigável
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
        
        for entry in feed.entries[:5]:
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
                    time.sleep(2)
                
            except Exception as e:
                print(f"✗ Erro ao enviar mensagem: {str(e)}")
                
    except Exception as e:
        print(f"Erro ao verificar feed: {str(e)}")

def main():
    print("\n=== Bot RSS do Esperanto Brasil ===")
    print(f"Canal: {CHANNEL_USERNAME}")
    print(f"Feed: {RSS_URL}")
    print(f"Intervalo de verificação: {CHECK_INTERVAL} segundos")
    print("\nPressione Ctrl+C para encerrar o bot")
    print("\nIniciando monitoramento do feed...")
    
    try:
        while True:
            check_and_send_updates()
            for i in range(CHECK_INTERVAL, 0, -1):
                print(f"\rPróxima verificação em {i} segundos...", end="")
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nBot encerrado pelo usuário")
        input("\nPressione Enter para sair...")
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")
        input("\nPressione Enter para sair...")

if __name__ == "__main__":
    main()