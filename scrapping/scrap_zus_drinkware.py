import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def scrape_section(wrapper, section_name):
    """Scrape all product info inside the given wrapper."""
    products = []
    for card in wrapper.select(".product-card__info"):
        try:
            name = card.select_one(".product-card__title a").get_text(strip=True)
            price = card.select_one("sale-price").get_text(strip=True)

            # Clean variants
            raw_variants = [v.get_text(strip=True) for v in card.select(".sr-only")]
            variants = sorted(set(v for v in raw_variants if v.lower() not in ["sale price", "regular price", ""]))
            
            products.append({
                "name": name,
                "price": price.replace("Sale price", "").replace("Regular price", "").strip(),
                "variants": variants,
                "section": section_name
            })
        except Exception as e:
            print(f"⚠️ Skipping product due to error: {e}")
            continue
    return products

def scrape_tumbler_and_accessories():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # safer for broader environments
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://shop.zuscoffee.com/")
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        all_products = []

        for section_name in ["Tumbler", "Accessories"]:
            title_div = soup.find("div", class_="bl_custom_collections_list-collection_title", string=section_name)
            if not title_div:
                print(f"Section '{section_name}' not found.")
                continue

            wrapper = title_div.find_next_sibling("div", class_="bl_custom_collections_list-collection_wrapper")
            if not wrapper:
                print(f"Wrapper for '{section_name}' not found.")
                continue

            all_products += scrape_section(wrapper, section_name)

        return all_products

    finally:
        driver.quit()

def format_for_rag(products):
    grouped = {}
    for p in products:
        grouped.setdefault(p["section"], []).append(p)

    result = []
    result.append("ZUS Drinkware Products - Tumbler and Accessories\n")
    result.append("This document contains a list of ZUS Coffee's available drinkware products, including tumblers and accessories. Each entry includes product name, price, and available variants.\n")

    counter = 1
    for section in ["Tumbler", "Accessories"]:
        if section in grouped:
            result.append(f"== {section} Products ==")
            for p in grouped[section]:
                line = f"{counter}. {p['name']}\nPrice: {p['price']}"
                if p["variants"]:
                    line += f"\nVariants: {', '.join(p['variants'])}"
                result.append(line)
                counter += 1
            result.append("")  # spacing between sections

    return "\n".join(result)

def save_to_txt(content, filename="database/zus_drinkware_data.txt"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved to {filename}")
    
def save_to_json(products_data, filename="scraped_data/zus_drinkware_products.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(products_data, f, ensure_ascii=False, indent=4)
    print(f"✅ Product data saved to {filename}")

if __name__ == "__main__":
    print("Scraping ZUS website...")
    items = scrape_tumbler_and_accessories()
    save_to_json(items)
