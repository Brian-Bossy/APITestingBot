import logging
import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your BotFather token
BOT_TOKEN = ""

# --- HANDLER FUNCTION DEFINITIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hi {user_name}\! I'm your API Endpoint Tester Bot\.\n\n"
        "I can help you quickly test HTTP endpoints\. 🧪\n\n"
        "*Here's how to use me:*\n\n"
        "1️⃣ *GET Request:*\n"
        "   `\/get <URL>`\n"
        "   *Example:* `\/get https:\/\/jsonplaceholder\.typicode\.com\/todos\/1`\n\n"
        "2️⃣ *POST Request:*\n"
        "   `\/post <URL> <JSON_DATA>`\n"
        "   *Example:* `\/post https:\/\/jsonplaceholder\.typicode\.com\/posts \{\"title\":\"foo\",\"body\":\"bar\",\"userId\":1\}`\n\n"
        "3️⃣ *PUT Request:*\n"
        "   `\/put <URL> <JSON_DATA>`\n"
        "   *Example:* `\/put https:\/\/jsonplaceholder\.typicode\.com\/posts\/1 \{\"id\": 1,\"title\":\"foo updated\",\"body\":\"bar updated\",\"userId\":1\}`\n\n"
        "4️⃣ *DELETE Request:*\n"
        "   `\/delete <URL>`\n"
        "   *Example:* `\/delete https:\/\/jsonplaceholder\.typicode\.com\/posts\/1`\n\n"
        "ℹ️ For *POST* and *PUT* requests, the `JSON_DATA` should be a valid JSON string\.\n"
        "Type `\/help` to see this message again\.",
        parse_mode='MarkdownV2' # Ensure this is set
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends help message when the /help command is issued."""
    await start(update, context) # Reuse the start message for help

async def handle_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args

    if not args:
        await update.message.reply_text("Please provide a URL.\nUsage: `/get <URL>`")
        return

    url = args[0]
    # Basic URL validation (optional, can be more robust)
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Invalid URL. Please include http:// or https://")
        return

    await update.message.reply_text(f"▶️ Sending GET request to: {url}...")

    try:
        response = requests.get(url, timeout=15) # 15 second timeout
        status_code = response.status_code
        
        try:
            # Try to parse JSON for pretty printing if it's JSON
            response_json = response.json()
            response_body_formatted = json.dumps(response_json, indent=2, ensure_ascii=False)
        except ValueError:
            response_body_formatted = response.text

        response_headers_formatted = json.dumps(dict(response.headers), indent=2, ensure_ascii=False)

        # Truncate long responses
        if len(response_body_formatted) > 3500:
            response_body_formatted = response_body_formatted[:3500] + "\n\n... (response body truncated)"
        if len(response_headers_formatted) > 1000: # Keep headers concise
            response_headers_formatted = response_headers_formatted[:1000] + "\n\n... (headers truncated)"


        reply_message = (
            f"✅ *GET Response from {url}*\n\n"
            f"*Status Code:* `{status_code} {response.reason}`\n\n"
            f"*Headers:*\n```json\n{response_headers_formatted}\n```\n\n"
            f"*Body:*\n```json\n{response_body_formatted}\n```"
        )
    except requests.exceptions.Timeout:
        reply_message = f"❌ *Timeout Error*\n\nThe request to {url} timed out."
    except requests.exceptions.RequestException as e:
        reply_message = f"❌ *Request Error for {url}*\n\n`{e}`"
    except Exception as e:
        reply_message = f"❌ *An unexpected error occurred for {url}*\n\n`{e}`"

    await update.message.reply_text(reply_message, parse_mode='MarkdownV2')


async def handle_post_put(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str) -> None:
    message_text = update.message.text
    # Expected format: /command <URL> {json_data}
    # Split only on the first two spaces to separate command, URL, and the rest as JSON data
    parts = message_text.split(' ', 2)

    if len(parts) < 2: # Needs at least /command and URL
        await update.message.reply_text(f"Please provide a URL.\nUsage: `/{method.lower()} <URL> <JSON_DATA>`")
        return

    url = parts[1]
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Invalid URL. Please include http:// or https://")
        return

    json_data_str = parts[2] if len(parts) > 2 else "{}" # Default to empty JSON if no data provided

    parsed_json_data = None
    try:
        parsed_json_data = json.loads(json_data_str)
    except json.JSONDecodeError as e:
        await update.message.reply_text(f"Invalid JSON data provided for {method} request.\nError: `{e}`\n"
                                        "Please ensure it's a well-formed JSON string.")
        return

    await update.message.reply_text(f"▶️ Sending {method} request to: {url} with data: `{json_data_str[:200]}{'...' if len(json_data_str)>200 else ''}`...")

    try:
        if method == "POST":
            response = requests.post(url, json=parsed_json_data, timeout=15)
        elif method == "PUT":
            response = requests.put(url, json=parsed_json_data, timeout=15)
        else: # Should not happen if called correctly
            await update.message.reply_text("Unsupported method internally.")
            return
            
        status_code = response.status_code
        try:
            response_json = response.json()
            response_body_formatted = json.dumps(response_json, indent=2, ensure_ascii=False)
        except ValueError:
            response_body_formatted = response.text
        
        response_headers_formatted = json.dumps(dict(response.headers), indent=2, ensure_ascii=False)

        if len(response_body_formatted) > 3500:
            response_body_formatted = response_body_formatted[:3500] + "\n\n... (response body truncated)"
        if len(response_headers_formatted) > 1000:
            response_headers_formatted = response_headers_formatted[:1000] + "\n\n... (headers truncated)"

        reply_message = (
            f"✅ *{method} Response from {url}*\n\n"
            f"*Status Code:* `{status_code} {response.reason}`\n\n"
            # f"*Headers:*\n```json\n{response_headers_formatted}\n```\n\n" # Often too verbose for POST/PUT
            f"*Body:*\n```json\n{response_body_formatted}\n```"
        )
    except requests.exceptions.Timeout:
        reply_message = f"❌ *Timeout Error*\n\nThe {method} request to {url} timed out."
    except requests.exceptions.RequestException as e:
        reply_message = f"❌ *Request Error for {method} to {url}*\n\n`{e}`"
    except Exception as e:
        reply_message = f"❌ *An unexpected error occurred for {method} to {url}*\n\n`{e}`"
        
    await update.message.reply_text(reply_message, parse_mode='MarkdownV2')


async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_post_put(update, context, "POST")

async def handle_put(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_post_put(update, context, "PUT")

async def handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args

    if not args:
        await update.message.reply_text("Please provide a URL.\nUsage: `/delete <URL>`")
        return

    url = args[0]
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("Invalid URL. Please include http:// or https://")
        return
        
    await update.message.reply_text(f"▶️ Sending DELETE request to: {url}...")

    try:
        response = requests.delete(url, timeout=15)
        status_code = response.status_code
        
        # DELETE responses might or might not have a body, and it might or might not be JSON
        response_body_formatted = response.text # Default to text
        if response.content: # Check if there's any content
            try:
                response_json = response.json()
                response_body_formatted = json.dumps(response_json, indent=2, ensure_ascii=False)
            except ValueError:
                pass # Keep as text if not valid JSON

        if len(response_body_formatted) > 3500:
            response_body_formatted = response_body_formatted[:3500] + "\n\n... (response body truncated)"

        reply_message = (
            f"✅ *DELETE Response from {url}*\n\n"
            f"*Status Code:* `{status_code} {response.reason}`\n\n"
            f"*Body:*\n```\n{response_body_formatted if response_body_formatted else '(No response body)'}\n```"
        )
    except requests.exceptions.Timeout:
        reply_message = f"❌ *Timeout Error*\n\nThe DELETE request to {url} timed out."
    except requests.exceptions.RequestException as e:
        reply_message = f"❌ *Request Error for DELETE to {url}*\n\n`{e}`"
    except Exception as e:
        reply_message = f"❌ *An unexpected error occurred for DELETE to {url}*\n\n`{e}`"

    await update.message.reply_text(reply_message, parse_mode='MarkdownV2')


# --- MAIN FUNCTION DEFINITION ---
def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get", handle_get))
    application.add_handler(CommandHandler("post", handle_post))
    application.add_handler(CommandHandler("put", handle_put))
    application.add_handler(CommandHandler("delete", handle_delete))

    # Start the Bot
    logger.info(f"Starting bot polling for token: ...{BOT_TOKEN[-6:]}") # Log last 6 chars of token for verification
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
