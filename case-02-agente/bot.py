import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agente import chat, enviar_telegram, gerar_relatorio, salvar_chat_id

load_dotenv()

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _split(texto: str, limite: int = 4096) -> list[str]:
    if len(texto) <= limite:
        return [texto]
    partes = []
    while texto:
        if len(texto) <= limite:
            partes.append(texto)
            break
        corte = texto.rfind("\n", 0, limite)
        if corte == -1:
            corte = limite
        partes.append(texto[:corte])
        texto = texto[corte:].lstrip("\n")
    return partes


async def _send(update: Update, texto: str) -> None:
    for parte in _split(texto):
        try:
            await update.message.reply_text(parte, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(parte)


# ── handlers ──────────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_text(
        "Olá! Sou o agente de dados do e-commerce.\n\n"
        "Comandos disponíveis:\n"
        "• /relatorio — gera o relatório executivo diário\n"
        "• Qualquer pergunta — consulto o banco e respondo\n\n"
        "Exemplo: *Qual foi a receita total da última semana?*",
        parse_mode="Markdown",
    )


async def relatorio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text("Gerando relatório executivo, aguarde...")
    try:
        relatorio = await asyncio.to_thread(gerar_relatorio)
        await _send(update, relatorio)
    except Exception as e:
        await update.message.reply_text(f"Erro ao gerar relatório: {e}")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    salvar_chat_id(update.message.chat_id)
    pergunta = update.message.text.strip()
    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        resposta = await asyncio.to_thread(chat, pergunta)
        await _send(update, resposta)
    except Exception as e:
        await update.message.reply_text(f"Erro ao processar pergunta: {e}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    token = os.getenv("TELEGRAM")
    if not token:
        raise RuntimeError("Variável TELEGRAM não definida no .env")

    logger.info("Iniciando bot Telegram...")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("relatorio", relatorio_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot rodando! Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()
