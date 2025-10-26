"""
Lokales Script um Weavy Login State zu speichern
Einmal ausführen, dann hast du storageState.json!
"""
import asyncio
from playwright.async_api import async_playwright

async def create_storage_state():
    async with async_playwright() as p:
        print("🚀 Launching browser...")
        browser = await p.chromium.launch(headless=False)  # NICHT headless - du musst manuell einloggen!
        
        context = await browser.new_context()
        page = await context.new_page()
        
        print("🌐 Opening Weavy...")
        await page.goto("https://app.weavy.ai/signin")
        
        print("\n" + "="*60)
        print("👉 JETZT BIST DU DRAN:")
        print("="*60)
        print("1. Click auf 'Sign in with Google'")
        print("2. Logge dich ein (mit Passkey, 2FA, etc.)")
        print("3. Warte bis du auf der Weavy Hauptseite bist")
        print("4. Dann drücke ENTER hier im Terminal")
        print("="*60 + "\n")
        
        input("Drücke ENTER wenn du eingeloggt bist...")
        
        print("💾 Saving storage state...")
        await context.storage_state(path="storageState.json")
        
        print("✅ storageState.json wurde erstellt!")
        print("📁 Die Datei liegt jetzt hier:")
        import os
        print(f"   {os.path.abspath('storageState.json')}")
        
        await browser.close()
        
        print("\n🎉 Fertig! Jetzt kannst du diese Datei zu Railway hochladen.")

if __name__ == "__main__":
    asyncio.run(create_storage_state())
