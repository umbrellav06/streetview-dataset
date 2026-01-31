from playwright.sync_api import sync_playwright
import os
from datetime import datetime, timedelta
import random 
import string
import pandas as pd
import time
import re
import argparse

os.makedirs("dataset", exist_ok=True)
os.makedirs("errors", exist_ok=True)
os.makedirs("challenge_urls", exist_ok=True)

def error_csv_path(location):
    return os.path.join("errors", f"{location}_errors.csv")

def challenge_csv_path(location):
    return os.path.join("challenge_urls", f"{location}_challenge_urls.csv")

def dataset_folder(location):
    folder = os.path.join("dataset", location)
    os.makedirs(folder, exist_ok=True)
    return folder


        # roles = [
        #     "button", "link", "textbox", "checkbox", "radio", "combobox",
        #     "listbox", "option", "switch", "slider", "menuitem"
        # ]

        # for role in roles:
        #     elements = page.get_by_role(role)
        #     count = elements.count()
        #     for i in range(count):
        #         print(role, "→", elements.nth(i).inner_text())

def robust_goto(page, url):
    for attempt in range(5):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            return True
        except Exception as e:
            print(f"⚠️ goto failed (attempt {attempt+1}/5): {e}")
            page.wait_for_timeout(2000)
    return False

def log_error(location,message, error=None):
    df = pd.DataFrame([{
        "time": datetime.now().strftime("%Y-%m-%d-%H:%M:%S"),
        "location": location,
        "message": message,
        "error": str(error)[:50]
    }])

    # CSV anhängen (Header nur beim ersten Mal)
    path = error_csv_path(location)
    df.to_csv(
        path, 
        mode="a", 
        header=not pd.io.common.file_exists(path), 
        index=False
    )
    print("LOG_ERROR CALLED:", location, message)


def exists_url(location,url):
    path = challenge_csv_path(location)
    if not os.path.exists(path): 
        return False
    df = pd.read_csv(path)
    return url in df["url"].values

def add_url(location,url):
    path = challenge_csv_path(location)
    df_new = pd.DataFrame([{"url": url}])
    df_new.to_csv(path, 
                  mode="a", 
                  header=not pd.io.common.file_exists(path), 
                  index=False)
    
def getMap(location):
    df = pd.read_csv("maps.csv")
    maps = df[df["country"] == location]["map"].tolist() 
    if not maps: 
        return None # falls Land nicht existiert 
    return random.choice(maps)

def geoguessrchalleng_url(browser,location):
    """
    from geochallenges.me → geoguessr Link
    """
    context = browser.new_context()
    page = context.new_page()
    URL = "https://geochallenges.me/"

    if not robust_goto(page, URL):
        print("❌ geochallenges.me - skip")
        log_error(location=location,message='geochallenges.me')
        return None, None
    
    # page.wait_for_timeout(2000)
    
    map = getMap(location)
    if map is None:
        print('❌ map')
        log_error(location=location,message='map')
        return None, None

    try:
        page.get_by_placeholder("Search for a map").fill(map)
        page.locator("//button[contains(@class, 'Home_searchButton')]").click()
        # print("✔️ search for",location)
    except Exception as e:
        print("❌ searching - skip", e)
        log_error(location=location,message='searching', error=e)
        return None, None
    
    # name = location+'_search.png'
    # folder = 'search'
    # os.makedirs(folder, exist_ok=True)
    # screenshot_path = os.path.join(folder, name)
    # page.screenshot(path=screenshot_path)

    page.wait_for_timeout(1000)
    try:
        # Dynamisch warten 
        page.wait_for_selector(".Home_mapCard__7ad3M", timeout=20000)
        # meisten likes finden
        cards = page.locator(".Home_mapCard__7ad3M")
        count = cards.count()

    except Exception as e:
        print('❌ wait for home - skip')
        print(e)
        log_error(location=location,message='wait for home',error=e)
        return None, None

    max_likes = -1
    best_card = None

    for i in range(count):
        card = cards.nth(i)
        likes_text = card.locator(".Home_likes__netPO").inner_text().strip()
        likes_number = int(likes_text.split()[0].replace(",", ""))

        if likes_number > max_likes:
            max_likes = likes_number
            best_card = card

        if location == 'Oman': break

    # Play-Button in der Karte mit den meisten Likes klicken
    try:
        title = best_card.locator("a").inner_text().strip()
        if title == 'World':
            print('❌ world map -skip')
            log_error(location=location,message='world')
            return None, None

        print('✔️ Chosen map:', title, '(', max_likes,' likes)')
        best_card.locator("button:has-text('Play')").click()
    except Exception as e:
        print('❌ play - skip')
        print(e)
        log_error(location=location,message='play', error=e)
        return None, None
    # print("✔️ play")

    # page.wait_for_timeout(5000)

    # Popup
    try:
        # NMPZ-Button exists
        nm_button = page.get_by_role("button", name="No Move")
        nm_button.wait_for(state="visible", timeout=8000)

        with context.expect_page(timeout=8000) as popup_info:
            nm_button.click()

        page.wait_for_timeout(5000)
        popup = popup_info.value
        popup.wait_for_load_state()
        challenge_url = popup.url
        if exists_url(location,challenge_url):
            print("❌ geoguessr link exists - skip")
            log_error(location=location,message='url exists')
            return None, None
        print("✔️ geoguessr link:", challenge_url)
    except Exception as e:
        print("⚠️ no popup")
        print(e)
        log_error(location=location,message='no popup', error=e)
        return None, None
    
    context.close()
    return challenge_url, title


def process_single(browser, location, index):
    """Ein Screenshot-Durchlauf."""
    print(f"[{location}] Run {index+1}")

    url, map_title = geoguessrchalleng_url(browser, location)
    if not url:
        return False

    context = browser.new_context()
    page = context.new_page()

    if not robust_goto(page, url):
        print("❌ geoguessr")
        log_error(location, "geoguessr")
        context.close()
        return False

    # Cookies
    try:
        page.get_by_text("Akzeptieren").click(timeout=2000)
        # print("✔️ cookies")
    except:
        # print("❌ cookies")
        pass


    # Name
    try:
        page.get_by_placeholder("Name").fill(location)
        # print("✔️ name")
    except Exception as e:
        print("❌ name")
        print(e)
        log_error(location, "name", e)
        # context.close()
        # return False
    
    page.wait_for_timeout(500)

    # Start game
    try:
        page.get_by_role("button", name="Play as Guest").click()
        # print("✔️ start game")
    except Exception as e:
        print("❌ start game")
        print(e)
        log_error(location, "start", e)
        context.close()
        return False

    # UI ausblenden
    page.add_style_tag(content="""
        .game_guessMap__8jK3B,
        .guess-map_guessMap__IP8n_,
        .panorama-compass_compassContainer__VAYam,
        .game_topHud__P_g7z,
        .game_inGameLogos__T9d3L,
        .game_status___YFni,
        .game-reactions_root__TSjX_,
        .styles_friendChatButton__oFztY,
        .styles_control__Pa4Ta,
        .gm-style-cc,
        .gmnoscreen,
        .gmnoprint,
        .gm-style-moc,
        .gm-style button,
        .gm-style .gm-control-active,
        .gm-style .gm-fullscreen-control,
        .gm-style .gm-svpc,
        .gm-style .gm-bundled-control,
        .gm-style .gm-compass,
        .gm-style .gm-sv-marker,
        .gm-style .gm-style-cc,
        .gm-style .gm-style-cc span,
        .gm-style .gm-style-cc div,
        a[href*='google'],
        img[src*='google'] {
            display: none !important;
        }
    """)

    page.add_style_tag(content="""
        .gm-style-cc,
        .gm-style-cc span,
        .gm-style-cc div,
        .gm-style .gm-style-cc,
        .gm-style .gm-style-cc span,
        .gm-style .gm-style-cc div,
        .widget-scene-canvas + div,
        .widget-scene-canvas + div * {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }
    """)

    page.add_init_script("""
        const style = document.createElement('style');
        style.innerHTML = `
            .gm-style-cc,
            .gm-style-cc * {
                display: none !important;
                opacity: 0 !important;
                visibility: hidden !important;
            }
        `;
        document.head.appendChild(style);
    """)
    
    page.add_style_tag(content="""
        button[data-qa="pano-zoom-in"],
        button[data-qa="pano-zoom-out"],
        .guess-map_zoomControls__kF2_G,
        .guess-map_controlIncreaseSize__BPECj,
        .guess-map_controlDecreaseSize__FgaUw {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }
    """)

    page.add_init_script("""
        document.querySelectorAll('button[aria-label*="vergrößern"], button[aria-label*="verkleinern"]').forEach(btn => {
            btn.style.display = 'none';
            btn.style.opacity = '0';
            btn.style.visibility = 'hidden';
        });
    """)
    

    # Streetview Canvas
    try:
        streetview = page.locator("canvas.widget-scene-canvas").first
        streetview.wait_for(state="visible", timeout=8000)
        # print("✔️ streetview")
    except Exception as e:
        print("❌ streetview")
        print(e)
        log_error(location, "streetview", e)
        context.close()
        return False
    
    add_url(location,url)
    page.wait_for_timeout(1000)

    # Screenshot
    folder = dataset_folder(location)
    os.makedirs(folder, exist_ok=True)

    map_title = map_title.encode("ascii", "ignore").decode()
    map_title = re.sub(r"[^A-Za-z0-9_]", "", map_title)

    name = datetime.now().strftime("%Y-%m-%d") +'_'+map_title+'_'+ url[-16:] +".jpg"
    path = os.path.join(folder, name)

    streetview.screenshot(path=path)

    context.close()
    return True


def streetview(location_nr):
    print('start: ',datetime.now().hour,':',datetime.now().minute)
    start = time.perf_counter()


    locations = [
        "Albania","Algeria","Andorra","Argentina","Armenia","Australia","Austria",
        "Bangladesh","Belgium","Bhutan","Bolivia","Bosnia and Herzegovina",
        "Botswana","Brazil","Bulgaria","Cambodia","Canada","Chile","China",
        "Colombia","Croatia","Czech Republic","Denmark",
        "Ecuador","Estonia","Eswatini","Finland","France","Germany",
        "Ghana","Greece","Guatemala","Hong Kong","Hungary","Iceland","India",
        "Indonesia","Ireland","Israel","Italy","Japan","Jordan","Kazakhstan",
        "Kenya","Kyrgyzstan","Laos","Latvia","Lesotho","Lithuania",
        "Luxembourg","Malaysia","Malta","Mexico","Moldova","Montenegro",
        "Nepal","Netherlands","New Zealand","Nigeria","North Macedonia",
        "Norway","Oman","Panama","Paraguay","Peru","Philippines","Poland",
        "Portugal","Qatar","Romania","Russia","Rwanda","San Marino",
        "Saudi Arabia","Senegal","Serbia","Singapore","Slovakia","Slovenia",
        "South Africa","South Korea","Spain","Sri Lanka","Sweden","Switzerland",
        "Taiwan","Thailand","Tunisia","Turkey","Uganda","Ukraine","United Arab Emirates",
        "United Kingdom","United States","Uruguay","Vatican City","Vietnam"
    ]
    # no NoMove
    # "Costa Rica","Dominican Republic"
    location_nr = int(location_nr)
    if location_nr >= len(locations):
        print('invalid location nr')
        return

    location = locations[location_nr]
    # temp -------------------
    df = pd.read_csv("maps.csv")
    location = df.iloc[location_nr]["country"]
    # temp -------------------

    print('##################')
    print(location)
    print('##################')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        success_count = 0
        for i in range(15):
            if process_single(browser, location, i):
                success_count += 1

        browser.close()
    
    print('##################')
    print("Ergebnis:")
    print(f"{location}: {success_count} images")
    if success_count == 0:
        print('❌ no images')
        log_error(location=location,message='no images')
    
    end = time.perf_counter()
    seconds = end - start
    print('##########################')
    td = timedelta(seconds=seconds)
    h, m, s = str(td).split(":")
    print(f"{int(h):02d}:{int(m):02d}:{int(float(s)):02d}")
    print('end: ',datetime.now().hour,':',datetime.now().minute)


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--location")
    args = parser.parse_args()

    streetview(location_nr=args.location)

