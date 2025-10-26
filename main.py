from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import asyncio
import base64
from typing import List, Dict

app = FastAPI(title="Weavy Automation Service (WITH Browserless)")

class ClipData(BaseModel):
    index: int
    text: str

class WeavyRequest(BaseModel):
    clipCount: int
    nanoClips: List[ClipData]
    seedClips: List[ClipData]
    workflowName: str
    weavy_email: str
    weavy_password: str

@app.post("/automate")
async def automate_weavy(request: WeavyRequest):
    """
    Automates Weavy workflow using Browserless WebSocket
    """
    try:
        async with async_playwright() as p:
            print("🔗 Connecting to Browserless...")
            browser = await p.chromium.connect(
                ws_endpoint="wss://production-sfo.browserless.io/chromium/playwright?token=2TIL1C6Yxk0ZmEM72ed69a2147ef229b4d58eb97a57439b1c"
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            print("🌐 Opening Weavy...")
            await page.goto("https://app.weavy.ai/signin", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            print("🔐 Clicking Google Sign-in...")
            # Warte bis Seite geladen
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # Finde Google Button (mehrere Selektoren probieren)
            google_btn = None
            selectors = [
                'button:has-text("Google")',
                'button[aria-label*="Google"]',
                'button:has(svg) >> text=/google/i',
                'button:has(.google-icon)',
                'button >> text=/^Google$/i'
            ]
            
            for selector in selectors:
                try:
                    google_btn = await page.wait_for_selector(selector, timeout=5000)
                    if google_btn:
                        print(f"Found Google button with selector: {selector}")
                        break
                except:
                    continue
            
            if not google_btn:
                raise Exception("Google Sign-in button not found")
            
            async with page.expect_popup(timeout=60000) as popup_info:
                await google_btn.click()
            popup = await popup_info.value
            
            print("📧 Filling email...")
            await popup.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            
            # Email Feld finden und füllen
            email_input = await popup.wait_for_selector("input[type=email]", timeout=30000)
            await email_input.fill(request.weavy_email)
            print(f"Email entered: {request.weavy_email}")
            await asyncio.sleep(1)
            
            # Next Button klicken
            print("Clicking Next button...")
            await popup.click("#identifierNext")
            await asyncio.sleep(5)  # Länger warten für Google's Response
            
            print("🔑 Waiting for password field...")
            # Screenshot für Debugging (optional)
            try:
                await popup.screenshot(path="/tmp/before-password.png")
                print("Screenshot saved for debugging")
            except:
                pass
            
            print("🔑 Filling password...")
            
            # Warte auf verschiedene mögliche Screens
            print("Checking what page we're on...")
            page_content = await popup.content()
            
            # Check für 2FA/Verification
            if "verify" in page_content.lower() or "authentication" in page_content.lower():
                raise Exception("2FA/Verification detected! Please disable 2FA on this account or use an app-specific password.")
            
            # Check für CAPTCHA
            if "captcha" in page_content.lower() or "recaptcha" in page_content.lower():
                raise Exception("CAPTCHA detected! Browserless may be blocked by Google. Try using a different IP or authentication method.")
            
            # Check für "wrong email"
            if "couldn't find your google account" in page_content.lower() or "couldn't sign you in" in page_content.lower():
                raise Exception(f"Google account not found or email incorrect: {request.weavy_email}")
            
            # Versuche Password-Feld zu finden
            password_input = await popup.wait_for_selector("input[type=password]", timeout=120000)
            await password_input.fill(request.weavy_password)
            print("Password entered")
            await asyncio.sleep(1)
            await popup.click("#passwordNext")
            await popup.wait_for_event("close", timeout=180000)
            
            print("✅ Login successful")
            await asyncio.sleep(5)
            
            print(f"🔍 Looking for workflow: {request.workflowName}")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            # Suche Workflow mit mehreren Strategien
            workflow_found = False
            selectors = [
                f'text="{request.workflowName}"',
                f'text={request.workflowName}',
                f'[title="{request.workflowName}"]',
                f'button:has-text("{request.workflowName}")',
                f'a:has-text("{request.workflowName}")'
            ]
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    await page.click(selector)
                    workflow_found = True
                    print(f"Workflow found with selector: {selector}")
                    break
                except:
                    continue
            
            if not workflow_found:
                raise Exception(f"Workflow '{request.workflowName}' not found")
            
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(5)
            
            print("🎨 Filling NANO prompts...")
            nano_areas = await page.query_selector_all("textarea")
            print(f"Found {len(nano_areas)} textareas")
            
            for i in range(min(request.clipCount, len(nano_areas))):
                print(f"Filling NANO clip {i+1}")
                await nano_areas[i].click(click_count=3)
                await nano_areas[i].fill(request.nanoClips[i].text)
                await asyncio.sleep(0.5)
            
            print("▶️ Clicking Run (NANO)...")
            run_btn = await page.query_selector('button:has-text("Run")')
            if run_btn:
                await run_btn.click()
            await asyncio.sleep(5)
            
            print("⏳ Waiting for NANO completion...")
            try:
                await page.wait_for_selector("text=Completed", timeout=600000)
            except:
                pass
            await asyncio.sleep(3)
            
            print("🎬 Filling SEEDANCE prompts...")
            seed_areas = await page.query_selector_all("textarea")
            
            for i in range(min(request.clipCount, len(seed_areas))):
                print(f"Filling SEEDANCE clip {i+1}")
                await seed_areas[i].click(click_count=3)
                await seed_areas[i].fill(request.seedClips[i].text)
                await asyncio.sleep(0.5)
            
            print("▶️ Clicking Run (SEEDANCE)...")
            run_btn = await page.query_selector('button:has-text("Run")')
            if run_btn:
                await run_btn.click()
            await asyncio.sleep(5)
            
            print("⏳ Waiting for SEEDANCE completion...")
            try:
                await page.wait_for_selector("text=Completed", timeout=600000)
            except:
                pass
            await asyncio.sleep(5)
            
            print("📥 Starting export...")
            async with page.expect_download(timeout=600000) as download_info:
                await page.click("text=Export")
            download = await download_info.value
            
            print("💾 Processing download...")
            file_name = download.suggested_filename
            path = await download.path()
            
            with open(path, "rb") as f:
                video_bytes = f.read()
            
            video_base64 = base64.b64encode(video_bytes).decode("utf-8")
            
            print(f"✅ Export successful! File: {file_name}, Size: {len(video_base64)}")
            
            await browser.close()
            
            return {
                "success": True,
                "fileName": file_name,
                "base64": video_base64,
                "message": "Automation completed successfully"
            }
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "service": "Weavy Automation (WITH Browserless)",
        "status": "ready",
        "endpoint": "/automate"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
