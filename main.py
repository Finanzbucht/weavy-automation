from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
import asyncio
import base64
import os
import json
from typing import List

app = FastAPI(title="Weavy Automation with StorageState (No Login!)")

class ClipData(BaseModel):
    index: int
    text: str

class WeavyRequest(BaseModel):
    clipCount: int
    nanoClips: List[ClipData]
    seedClips: List[ClipData]
    workflowName: str

@app.post("/automate")
async def automate_weavy(request: WeavyRequest):
    """
    Automates Weavy workflow using saved storageState
    NO LOGIN NEEDED - uses pre-authenticated session!
    """
    try:
        # Check if storageState exists
        storage_state_path = "/app/storageState.json"
        if not os.path.exists(storage_state_path):
            raise Exception("storageState.json not found! Please upload it to Railway.")
        
        print("📋 Loading storageState...")
        with open(storage_state_path, 'r') as f:
            storage_state = json.load(f)
        
        async with async_playwright() as p:
            print("🚀 Launching browser with saved session...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            # Use saved storage state - NO LOGIN NEEDED!
            context = await browser.new_context(storage_state=storage_state)
            page = await context.new_page()
            
            print("🌐 Opening Weavy (already logged in!)...")
            await page.goto("https://app.weavy.ai", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            # Check if we're really logged in
            current_url = page.url
            if "signin" in current_url:
                raise Exception("Session expired! Please create a new storageState.json")
            
            print("✅ Already logged in! Skipping authentication.")
            
            print(f"🔍 Looking for workflow: {request.workflowName}")
            await asyncio.sleep(2)
            
            # Find workflow
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
                    print(f"✅ Workflow clicked: {selector}")
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
                "message": "Automation completed successfully (with storageState)"
            }
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    storage_exists = os.path.exists("/app/storageState.json")
    return {
        "service": "Weavy Automation with StorageState",
        "status": "ready" if storage_exists else "waiting for storageState.json",
        "endpoint": "/automate",
        "storageState": "loaded" if storage_exists else "missing",
        "note": "No login needed - uses saved session!"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
