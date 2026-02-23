"""Interactive CLI chat simulator — test the auth flow without WhatsApp."""

import asyncio

from whatsapp_agent.database.engine import async_session_factory, init_db
from whatsapp_agent.services.message_router import MessageRouter
from whatsapp_agent.services.session_manager import SessionManager

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


async def main() -> None:
    print(f"\n{BOLD}{'=' * 52}")
    print(f"  🤖  WhatsApp Agent — Chat Simulator")
    print(f"{'=' * 52}{RESET}\n")

    # ── Initialise database ──────────────────────────────
    await init_db()

    # ── Ask for a phone number to simulate ───────────────
    print(f"{DIM}Tip: Use +15551234567 (known) or +19999999999 (unknown){RESET}")
    print(f"{DIM}     Type 'quit' to exit, 'switch' to change phone number{RESET}\n")

    phone = input(f"{YELLOW}Enter phone number to simulate: {RESET}").strip()
    if not phone:
        phone = "+19999999999"
    print(f"{DIM}Simulating as {phone}{RESET}\n")

    # ── Set up the framework ─────────────────────────────
    session_manager = SessionManager()
    router = MessageRouter(session_manager)

    while True:
        try:
            user_input = input(f"{BLUE}{BOLD}You:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print(f"{DIM}Goodbye!{RESET}")
            break

        if user_input.lower() == "switch":
            phone = input(f"{YELLOW}New phone number: {RESET}").strip()
            print(f"{DIM}Switched to {phone}{RESET}\n")
            continue

        if user_input.lower() == "logout":
            session_manager.clear(phone)
            print(f"{GREEN}{BOLD}Agent:{RESET} 👋 You have been logged out. Send any message to start again.\n")
            continue

        # ── Route the message through the framework ──────
        async with async_session_factory() as db_session:
            response = await router.route(
                phone=phone,
                message=user_input,
                db_session=db_session,
            )
            await db_session.commit()

        print(f"{GREEN}{BOLD}Agent:{RESET} {response.reply_text}\n")


if __name__ == "__main__":
    asyncio.run(main())
