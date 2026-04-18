import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException,
    TimeoutException, WebDriverException
)


class ScrapeError(Exception):
    pass


def _safe_href(el):
    try:
        href = el.get_attribute("href") or ""
        if "/p/" not in href and "/reel" not in href and "instagram.com" in href:
            username = href.rstrip("/").split("/")[-1]
            if username:
                return username
    except StaleElementReferenceException:
        pass
    return None


def _parse_count(text):
    if not text:
        return None
    text = text.strip().upper().replace(" ", "").replace(".", "").replace(",", "")
    try:
        if text.endswith("K"):
            return int(float(text[:-1]) * 1_000)
        if text.endswith("M") or text.endswith("B"):
            return int(float(text[:-1]) * 1_000_000)
        return int(text)
    except ValueError:
        return None


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _check_page(driver, account_name):
    page = driver.page_source
    url  = driver.current_url

    if "Page Not Found" in page or "Bu sayfa mevcut değil" in page:
        raise ScrapeError(f"@{account_name} hesabı bulunamadı.")
    if "Bu hesap gizlidir" in page or "This Account is Private" in page:
        raise ScrapeError(f"@{account_name} hesabı gizli.")
    if "accounts/login" in url:
        raise ScrapeError("Oturum kapandı. Lütfen tekrar giriş yap.")


def _load_profile_and_get_count(driver, account_name, link_keyword):
    """Profili yükle ve sayıyı tek seferde al."""
    driver.get(f"https://www.instagram.com/{account_name}/")
    try:
        link = _wait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, f"//a[contains(@href, '{link_keyword}')]")
            )
        )
        for xpath in [".//span[@title]", ".//span/span", ".//span"]:
            try:
                el    = link.find_element(By.XPATH, xpath)
                text  = el.get_attribute("title") or el.text
                count = _parse_count(text)
                if count:
                    return count
            except NoSuchElementException:
                continue
    except TimeoutException:
        pass
    except Exception as e:
        print(f"[WARN] Sayı alınamadı: {e}")
    return None


def _open_dialog(driver, account_name, link_keyword):
    """Sayfa zaten yüklü, direkt tıkla."""
    _check_page(driver, account_name)
    try:
        link = _wait(driver, 8).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//a[contains(@href, '{link_keyword}')]")
            )
        )
        link.click()
        _wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//a"))
        )
        time.sleep(1.5)
    except TimeoutException:
        raise ScrapeError(f"@{account_name} listesi açılamadı.")
    except NoSuchElementException:
        raise ScrapeError(f"@{account_name} listesine erişilemiyor.")


def _reload_and_open_dialog(driver, account_name, link_keyword):
    """Turlar arası: profili yeniden yükle ve dialogu aç."""
    driver.get(f"https://www.instagram.com/{account_name}/")
    try:
        _wait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, f"//a[contains(@href, '{link_keyword}')]")
            )
        )
    except TimeoutException:
        pass
    _open_dialog(driver, account_name, link_keyword)


def _close_dialog(driver):
    try:
        driver.find_element(
            By.XPATH,
            "//div[@role='dialog']//button[@aria-label='Kapat' or @aria-label='Close']"
        ).click()
        time.sleep(0.5)
    except Exception:
        try:
            from selenium.webdriver.common.keys import Keys
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except Exception:
            pass


DIALOG_XPATH = "//div[@role='dialog']//a"


def _collect_pass(driver, found, target_count, notify, pct_start, pct_end,
                  stop_flag=None, collected_ref=None):
    last_count = len(found)

    while True:
        if stop_flag and stop_flag():
            break

        links = driver.find_elements(By.XPATH, DIALOG_XPATH)

        for el in links:
            user = _safe_href(el)
            if user:
                found.add(user)

        if collected_ref is not None:
            collected_ref.clear()
            collected_ref.extend(sorted(found))

        current = len(found)
        if current > last_count:
            last_count = current
            ratio = min((current / target_count) if target_count else 0.5, 0.98)
            pct   = int(pct_start + ratio * (pct_end - pct_start))
            notify(f"{current} kişi bulundu...", pct)

            if target_count and current >= target_count:
                break

        if links:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView(true);",
                    links[random.randint(max(0, len(links) - 3), len(links) - 1)]
                )
            except StaleElementReferenceException:
                pass

        prev_len = len(links)
        for _ in range(5):
            time.sleep(random.uniform(0.4, 0.7))
            if stop_flag and stop_flag():
                return found
            if len(driver.find_elements(By.XPATH, DIALOG_XPATH)) > prev_len:
                break
        else:
            break

    return found


def _scrape(driver, account_name, link_keyword, progress_callback=None,
            stop_flag=None, collected_ref=None):
    def notify(msg, pct):
        print(msg)
        if progress_callback:
            progress_callback(msg, pct)

    # Profil zaten analiz aşamasında yüklendi, sayfa hâlâ açık
    # Direkt dialog aç
    target = None
    try:
        from scraper import _parse_count
    except ImportError:
        pass

    # Sayfa hâlâ profilde — sayıyı tekrar almaya gerek yok, dialog aç
    try:
        _open_dialog(driver, account_name, link_keyword)
    except WebDriverException as e:
        raise ScrapeError(f"Tarayıcı hatası: {str(e)[:80]}")

    # Hedef sayıyı profil linkinden oku
    try:
        from selenium.webdriver.common.by import By as _By
        link_el = driver.find_elements(_By.XPATH, f"//a[contains(@href, '{link_keyword}')]")
        if link_el:
            for xpath in [".//span[@title]", ".//span/span", ".//span"]:
                try:
                    el   = link_el[0].find_element(_By.XPATH, xpath)
                    text = el.get_attribute("title") or el.text
                    c    = _parse_count(text)
                    if c:
                        target = c
                        break
                except Exception:
                    continue
    except Exception:
        pass

    found   = set()
    MAX_TUR = 10

    for tur in range(MAX_TUR):
        if stop_flag and stop_flag():
            notify("⛔ Durdurma sinyali alındı...", 90)
            break

        tur_basi = 10 + int((tur / MAX_TUR) * 75)
        tur_sonu = 10 + int(((tur + 1) / MAX_TUR) * 75)
        onceki   = len(found)

        try:
            found = _collect_pass(
                driver, found, target, notify,
                pct_start=tur_basi,
                pct_end=tur_sonu,
                stop_flag=stop_flag,
                collected_ref=collected_ref,
            )
        except WebDriverException as e:
            raise ScrapeError(f"Bağlantı kesildi: {str(e)[:80]}")

        yeni = len(found) - onceki
        notify(f"Tur {tur + 1}: {yeni} yeni, toplam {len(found)}", tur_sonu)

        if target and len(found) >= target:
            notify(f"✓ Hedef {target}'e ulaşıldı!", tur_sonu)
            break

        if stop_flag and stop_flag():
            notify("⛔ Durdurma sinyali alındı...", 90)
            break

        if tur < MAX_TUR - 1:
            _close_dialog(driver)
            time.sleep(random.uniform(1.5, 3.0))
            try:
                _reload_and_open_dialog(driver, account_name, link_keyword)
            except ScrapeError:
                break

    notify(f"✓ Toplam {len(found)} kişi bulundu!", 92)
    notify("Kaydediliyor...", 95)
    return sorted(found)


def scrape_following(driver, account_name, progress_callback=None,
                     stop_flag=None, collected_ref=None):
    return _scrape(driver, account_name, "/following/", progress_callback,
                   stop_flag=stop_flag, collected_ref=collected_ref)


def scrape_followers(driver, account_name, progress_callback=None,
                     stop_flag=None, collected_ref=None):
    return _scrape(driver, account_name, "/followers/", progress_callback,
                   stop_flag=stop_flag, collected_ref=collected_ref)