import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://127.0.0.1:8000/ui")
        
        # Click "Vos services" button
        # The button text is "Vos services"
        await page.click("button:has-text('Vos services')")
        
        # Wait 5 seconds
        await asyncio.sleep(5)
        
        # Take screenshot
        await page.screenshot(path="scratch/chat_after_click.png")
        print("Screenshot saved to scratch/chat_after_click.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
