import json
import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://zuscoffee.com/category/store/kuala-lumpur-selangor/page/{}/"

def generate_opening_summary(hours: dict) -> str:
    values = list(set(hours.values()))
    if len(values) == 1:
        return f"Monday–Sunday: {values[0]}"
    return "; ".join([f"{day}: {time}" for day, time in hours.items()])


def build_description(name, address, services, summary, link):
    services_str = ", ".join(services) if services else "various services"
    return f"{name} is located at {address}. It offers {services_str}. Open hours: {summary}. Google Maps: {link}"

def scrape_google_maps_services():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--lang=en")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        results = []
        id_counter = 101

        for page in range(1, 23):
            url = BASE_URL.format(page) if page > 1 else BASE_URL.replace("/page/{}/", "")
            print(f"📄 Scraping page {page}: {url}")
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            containers = soup.find_all("div", attrs={"data-elementor-type": "loop", "data-elementor-id": "2883"})

            for container in containers:
                name_tag = container.find("p", class_="elementor-heading-title")
                normal_p = container.find("p")

                name = name_tag.get_text(strip=True) if name_tag else "Unknown"
                address = normal_p.get_text(strip=True) if normal_p else "Unknown"

                direction_a = container.find("a", class_="premium-button premium-button-none premium-btn-lg premium-button-none")
                if direction_a and "Direction" in direction_a.get_text(strip=True):
                    maps_link = direction_a.get("href")
                    print(f"🌐 Opening: {maps_link}")

                    driver.get(maps_link)
                    time.sleep(1)

                    # Opening hours
                    opening_hours = {}
                    try:
                        soup_hours = BeautifulSoup(driver.page_source, 'html.parser')
                        rows = soup_hours.select('tr.y0skZc')
                        for row in rows:
                            day_div = row.find('td', class_='ylH6lf')
                            time_td = row.find('td', class_='mxowUb')
                            if day_div and time_td:
                                day = day_div.get_text(strip=True)
                                hour_range = time_td.get_text(strip=True)
                                opening_hours[day] = hour_range
                        print("✅ Extracted hours:", opening_hours)
                    except Exception as e:
                        print(f"❌ Hours error: {e}")

                    # Expand services section
                    try:
                        expand_icon = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "span.TRbhbd.google-symbols.Q6EWEd"))
                        )
                        driver.execute_script("arguments[0].click();", expand_icon)
                        time.sleep(1)
                    except:
                        print("⚠️ Expand icon failed.")

                    # Services
                    services = []
                    try:
                        service_div = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "iP2t7d") and .//h2[text()="Service options"]]'))
                        )
                        li_elements = service_div.find_elements(By.CSS_SELECTOR, 'li.hpLkke')
                        for li in li_elements:
                            try:
                                span = li.find_element(By.XPATH, './/span[@aria-label]')
                                label = span.get_attribute('aria-label')
                                label = label.replace("Offers ", "").replace("Serves ", "").strip()
                                services.append(label)
                            except:
                                continue
                    except:
                        print("⚠️ No services info found.")

                    # Compose final object
                    opening_summary = generate_opening_summary(opening_hours)
                    full_desc = build_description(name, address, services, opening_summary, maps_link)

                    result = {
                        "id": id_counter,
                        "name": name,
                        "address": address,
                        "google_maps_link": maps_link,
                        "services": services,
                        "opening_hours": opening_hours,
                        "opening_hours_summary": opening_summary,
                        "full_description": full_desc
                    }

                    results.append(result)
                    id_counter += 1
                    print(f"✅ {name} added.")

        return results

    finally:
        driver.quit()

def save_to_json(data, filename="scraped_data/zus_outlets.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ Data saved to {filename}")

if __name__ == "__main__":
    data = scrape_google_maps_services()
    save_to_json(data)
