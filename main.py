from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import asyncio
import base64
from typing import List, Dict

app = FastAPI(title="Weavy Automation Service (WITHOUT Browserless)")

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
    Automates Weavy workflow using LOCAL Playwright browser (no Browserless)
    """
    try:
        async with async_playwright() as p:
            print("🚀 Launching local browser...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu'
                ]
            )
            
            context = await browser.new_context()
            page = await context.new_page()
            
            print("🌐 Opening Weavy...")
            await page.goto("https://app.weavy.ai/signin")
            await asyncio.sleep(2)
            
            print("🔐 Clicking Google Sign-in...")
            async with page.expect_popup() as popup_info:
                await page.click("text=Sign in with Google")
            popup = await popup_info.value
            
            print("📧 Filling email...")
            await popup.wait_for_load_state("domcontentloaded")
            await popup.fill("input[type=email]", request.weavy_email)
            await popup.click("#identifierNext")
            
            print("🔑 Filling password...")
            await popup.wait_for_selector("input[type=password]", timeout=120000)
            await popup.fill("input[type=password]", request.weavy_password)
            await popup.click("#passwordNext")
            await popup.wait_for_event("close", timeout=180000)
            
            print("✅ Login successful")
            await asyncio.sleep(5)
            
            print(f"🔍 Looking for workflow: {request.workflowName}")
            await page.wait_for_selector(f"text={request.workflowName}", timeout=120000)
            await page.click(f"text={request.workflowName}")
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
        "service": "Weavy Automation (WITHOUT Browserless - Local Browser)",
        "status": "ready",
        "endpoint": "/automate"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
