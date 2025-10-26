from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import asyncio
import base64
from typing import List

app = FastAPI(title="Weavy Automation (Local Browser - No Browserless)")

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
    Automates Weavy workflow using LOCAL browser (no Browserless needed)
    This avoids Google CAPTCHA issues!
    """
    try:
        async with async_playwright() as p:
            print("🚀 Launching local browser (avoiding CAPTCHA)...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security'
                ]
            )
            
            # Set user agent to look like real browser
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            print("🌐 Opening Weavy...")
            await page.goto("https://app.weavy.ai/signin", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            print("🔐 Looking for Google Sign-in button...")
            # Try multiple selectors for Google button
            google_btn = None
            selectors = [
                'button:has-text("Google")',
                'button[aria-label*="Google"]',
                'button:has-text("google")',
                'button:has(path[d*="M22.56"])',  # Google icon SVG
                'button[class*="google"]',
                'a:has-text("Google")'
            ]
            
            for selector in selectors:
                try:
                    google_btn = await page.wait_for_selector(selector, timeout=5000)
                    if google_btn:
                        print(f"✅ Found Google button with: {selector}")
                        break
                except:
                    continue
            
            if not google_btn:
                await page.screenshot(path="/tmp/signin-page.png")
                raise Exception("Google Sign-in button not found. Screenshot saved.")
            
            print("👆 Clicking Google button...")
            async with page.expect_popup(timeout=60000) as popup_info:
                await google_btn.click()
            popup = await popup_info.value
            
            print("📧 Filling email...")
            await popup.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            
            email_input = await popup.wait_for_selector("input[type=email]", timeout=30000)
            await email_input.fill(request.weavy_email)
            print(f"✅ Email entered: {request.weavy_email}")
            await asyncio.sleep(1)
            
            print("👉 Clicking Next...")
            await popup.click("#identifierNext")
            await asyncio.sleep(5)
            
            print("🔑 Waiting for password field...")
            # Check what page we're on
            page_content = await popup.content()
            
            if "verify" in page_content.lower() or "authentication" in page_content.lower():
                await popup.screenshot(path="/tmp/2fa-screen.png")
                raise Exception("2FA/Verification detected! Please disable 2FA or use app-specific password.")
            
            if "captcha" in page_content.lower() or "recaptcha" in page_content.lower():
                await popup.screenshot(path="/tmp/captcha-screen.png")
                raise Exception("CAPTCHA detected! This should not happen with local browser. Check Railway logs.")
            
            if "couldn't find" in page_content.lower():
                raise Exception(f"Google account not found: {request.weavy_email}")
            
            # Wait for password field
            password_input = await popup.wait_for_selector("input[type=password]", timeout=120000)
            await password_input.fill(request.weavy_password)
            print("✅ Password entered")
            await asyncio.sleep(1)
            
            print("👉 Clicking Next (password)...")
            await popup.click("#passwordNext")
            await popup.wait_for_event("close", timeout=180000)
            
            print("✅ Login successful!")
            await asyncio.sleep(5)
            
            print(f"🔍 Looking for workflow: {request.workflowName}")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            # Find workflow with multiple strategies
            workflow_found = False
            selectors = [
                f'text="{request.workflowName}"',
                f'text={request.workflowName}',
                f'[title="{request.workflowName}"]',
                f'button:has-text("{request.workflowName}")',
                f'a:has-text("{request.workflowName}")',
                f'div:has-text("{request.workflowName}")'
            ]
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    await page.click(selector)
                    workflow_found = True
                    print(f"✅ Workflow clicked with: {selector}")
                    break
                except:
                    continue
            
            if not workflow_found:
                await page.screenshot(path="/tmp/workflows-page.png")
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
                print("⚠️ Timeout waiting for NANO - continuing anyway")
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
                print("⚠️ Timeout waiting for SEEDANCE - continuing anyway")
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
            
            print(f"✅ Success! File: {file_name}, Size: {len(video_base64)} bytes")
            
            await browser.close()
            
            return {
                "success": True,
                "fileName": file_name,
                "base64": video_base64,
                "message": "Automation completed successfully"
            }
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "service": "Weavy Automation (Local Browser - No Browserless)",
        "status": "ready",
        "endpoint": "/automate",
        "note": "Uses local browser to avoid CAPTCHA issues"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
