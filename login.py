import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def login(driver, username, password):
    wait = WebDriverWait(driver, 20)

    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(2)

    u_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    u_input.send_keys(username)

    p_input = driver.find_element(By.NAME, "pass")
    p_input.send_keys(password)
    p_input.send_keys(Keys.RETURN)

    time.sleep(8)