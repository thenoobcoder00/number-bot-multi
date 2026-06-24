#!/usr/bin/env python3
"""
🤖 StexSMS Bot Unified Runner
----------------------------------
A highly robust Python combination of the panel monitoring/forwarding system
and the interactive Telegram Bot Controller.

This single file handles:
1. Multi-threaded background panel monitoring (CDRs & Active GetNum/Info numbers) for StexSMS.
2. Dynamic solving of mathematical captchas for logins.
3. Fully functional interactive Telegram Bot matching server.ts exactly.
4. Professional copy and exploration commands: /start, /getnum, /search, and /traffic.
5. Absolute error safety by sanitizing Telegram button schemas to prevent Status 400 errors.

Usage:
    python bot.py
"""

import os
import re
import sys
import time
import json
import random
import logging
import threading
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load env variables
load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DXA_VoltxBot")

# Config Files
PANELS_FILE = "panels.json"
SERVICES_FILE = "services.json"
ADMIN_DB_FILE = "admin_db.json"
OWNER_ID = "1849126202" # Change this ID to your main Admin ID
TELEGRAM_TOKEN = "8761438382:AAETScWJItsru4Shasx59XRkdUch79dADOA"  # আপনার টেলিগ্রাম বট টোকেনটি এখানে দিন

# Admin DB Logic (Tracks Users and Today's Numbers)
def load_admin_db():
    default_db = {"users": [], "today_date": datetime.now().strftime("%Y-%m-%d"), "today_numbers_count": 0, "admins": [OWNER_ID], "force_join_status": False, "force_join_channels": [], "otp_group_link": "", "forward_groups": [], "dxa_config": {"withdraw_group": "", "otp_reward": 0.0, "min_withdraw": 20.0, "methods": [], "max_concurrent": 3, "cooldown": 0}, "user_stats": {}, "active_numbers": {}}
    if os.path.exists(ADMIN_DB_FILE):
        try:
            with open(ADMIN_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "admins" not in data: data["admins"] = [OWNER_ID]
                if "force_join_status" not in data: data["force_join_status"] = False
                if "force_join_channels" not in data: data["force_join_channels"] = []
                if "otp_group_link" not in data: data["otp_group_link"] = ""
                if "forward_groups" not in data: data["forward_groups"] = []
                if "dxa_config" not in data: data["dxa_config"] = {"withdraw_group": "", "otp_reward": 0.0, "min_withdraw": 20.0, "methods": [], "max_concurrent": 3, "cooldown": 0}
                else:
                    data["dxa_config"].setdefault("max_concurrent", 3)
                    data["dxa_config"].setdefault("cooldown", 0)
                if "user_stats" not in data: data["user_stats"] = {}
                if "active_numbers" not in data: data["active_numbers"] = {}
                return data
        except: pass
    return default_db

def check_user_limits(chat_id, update_cooldown=True):
    cfg = admin_db.get("dxa_config", {})
    max_c = int(cfg.get("max_concurrent", 1))
    if max_c < 1: max_c = 1
    
    if str(chat_id) in admin_db.get("admins", [OWNER_ID]):
        return True, "", max_c
        
    cd = int(cfg.get("cooldown", 0))

    stats = admin_db.setdefault("user_stats", {}).setdefault(str(chat_id), {})
    stats.setdefault("otp_count", 0)
    stats.setdefault("balance", 0.0)
    stats.setdefault("last_req", 0)

    now = int(time.time())
    last_req = stats.get("last_req", 0)
    
    if cd > 0 and (now - last_req) < cd:
        rem = cd - (now - last_req)
        return False, f"⏳ Cooldown Active!\nPlease wait {rem} seconds before getting another number.", max_c

    if update_cooldown:
        stats["last_req"] = now
        save_admin_db()
        
    return True, "", max_c

def save_admin_db():
    try:
        with open(ADMIN_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(admin_db, f, indent=2)
    except: pass

admin_db = load_admin_db()

# ----------------------------------------------------
# Firebase Cloud Firestore Setup (Hardcoded)
# ----------------------------------------------------
firebase_cred_dict = {
  "type": "service_acount",
  "project_id": "ffrts-360b5",
  "private_key_id": "911e4a3e1376b8f49723b172fc4460e06",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDV50Loyr4Lzr7F\nVMp6Cz3kQdbMThRbO0XVe8GtBzltqoetpOfrLin4htYFeIDf9xpMRgTiDixqpJhs\nto0N9F06IpvImDnK3t2jc2ZT83WuKUQmhLorC9TBymZNjNVFmM6hsBx5K2ko72Eu\n5XKpytnIbr6+4lRg/yG/MMY8Vq4uvvpyZoBECyk/+KKkD23/l8gGDvpsxdLPt/0t\nmZcS3uG5Yo4K2ZX6D2/QdDQKOwPdRkcQHiWC+comhluVN4lJmrs8CWifcSbnwJED\nLVCIOjyZEkBwTQlqk/KTAoZ2HNtxGSZ8VjbIqot2ClAkXS9OBvbQw/EyGqOg5ZXs\nHcvfkNkHAgMBAAECggEAFZ+AKwo7tfPbYxVUNowmYImrThHiiupt/8u342bkjkp7\n1rjh3OtYwM/YmMr6tClFlkpJuhRWtx0Wb37wuWVnezX+a4O/69slqp1Czd/BmK6B\nPieSrkFO65wrRVGkSZnN4Zhs+G7D/ahdOaFmOvXPmCxhyegVQYzo+2vRzk2w4/ap\nB5XCT0n/c3dQA+7vesp+DKowMpRaxC/3ftjoJeRhTDJ9YgEYMrD4lVhPfj4ybI9W\nNW259rjO3f4+ahCr6CufGTVVOO68WtsqkgZo6uL99j7hRNzoeXVxGnDoF0snJi7f\nc/HxDxxh1VrwnUUwK01FoKxZDmAcpE46bjsAogzA4QKBgQDtiVN6KDJ3v0M2k4+3\n+yq+n+mN618/P+spaQ5DTnHkM2x4TzSAhf+vF50zB6sexD6U/wxk0MUKft0Ht8S2\nkWIkO/dTSI/UkUK3b87xKIXPkhh0zot2CW2ChQzcFbKL+dP5GAM+WPaFD6ufcqgu\nKi88ODzjvsjD77pYtTWiAJjU1wKBgQDmh6rP0MrycPO7dpd1pq7Fp4S4GOSIzGZ6\nZanudP89uSF+24Fy0cyfNSdYjN89Ie1GEp4VYYgJd8fC6Ka4QZwet0DckJLUYd7m\noQxqh5/9iY0xYogkMZXvdcn65dXBXjrL+9J8virFw0XYSyj9QcXXMVEoeLkfjOO5\nUDNJtaVnUQKBgQCAX/Zwj6bu1rxhk5BZs3Gfglc8LxfT3Bygzbk6oPumhDA8OTo7\nt6++ljmMKbnOr+rOpaSyG65SBMw57pRuwtXSlWIObanmDPeMoe2qoebnjqKPBk2S\n5nd70aJok4ViZwurlNGz8WqR8S0kyFeiU4QhvJcT0rk4Q6hnZs/slPwEEwKBgQCq\n8U0LPwNO1c0WZHEZb9lHfdnffa3xdshC2KIyzZT7Ww1oeTK7RrFaGVsswYFEXqUI\nggOxTRpIEwcRE92U4in3aOHy7E3EqTJViHShhiJwKhCF30+erxpEb+6vWsCv28Tz\nv68siwNClHN1WP5zFdOzp8FLpoF30MyIfN0bOlQFkQKBgQDgli7tiMWKu6Zby2T6\nxas+urjnT6bExKfNjofdrxJR7Fo8LkfkyNKuq2EMKYZdH7ywCsugfMAq5cQYen4w\n7rb8LKEBX1S5LDhbhkc0d6HvNV6JGbh36MewGUoOZCko9mNAKriGPKPtm6hZZrmQ\np+lIdCIFnZX5K221LYH0Z/xzsw==\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@ff-esportviceaccount.com",
  "client_id": "111733621782755",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40orts-360b5.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
db_firestore = None

def initialize_firebase():
    global db_firestore
    try:
        cred = credentials.Certificate(firebase_cred_dict)
        if firebase_admin._apps:
            firebase_admin.delete_app(firebase_admin.get_app())
        firebase_admin.initialize_app(cred)
        db_firestore = firestore.client()
        logger.info("Firebase Firestore initialized successfully using hardcoded dict!")
        return True, "Firebase connected successfully!"
    except Exception as e:
        db_firestore = None
        logger.error(f"Firebase initialization failed: {e}")
        return False, str(e)

initialize_firebase()

def restore_from_firestore():
    global admin_db
    if not db_firestore: return
    try:
        # ১. অ্যাডমিন কনফিগ রি-স্টোর
        cfg_doc = db_firestore.collection("DXA_System").document("Bot_Config").get()
        if cfg_doc.exists:
            data = cfg_doc.to_dict()
            if "dxa_config" in data: admin_db["dxa_config"] = data["dxa_config"]
            if "search_cfg" in data: admin_db["search_cfg"] = data["search_cfg"]
            if "admins" in data: admin_db["admins"] = data["admins"]
            if "otp_group_link" in data: admin_db["otp_group_link"] = data["otp_group_link"]
            if "forward_groups" in data: admin_db["forward_groups"] = data["forward_groups"]
            if "force_join_status" in data: admin_db["force_join_status"] = data["force_join_status"]
            if "force_join_channels" in data: admin_db["force_join_channels"] = data["force_join_channels"]
            if "banned_users" in data: admin_db["banned_users"] = data["banned_users"]
        
        # ২. ইউজার ব্যালেন্স ও OTP 리-স্টোর
        users_doc = db_firestore.collection("DXA_System").document("Users_Data").get()
        if users_doc.exists:
            data = users_doc.to_dict()
            if "active_users" in data:
                for uid, udata in data["active_users"].items():
                    stats = admin_db.setdefault("user_stats", {}).setdefault(uid, {})
                    stats["balance"] = udata.get("balance", 0.0)
                    stats["otp_count"] = udata.get("otp_count", 0)
                    if uid not in admin_db.setdefault("users", []): admin_db["users"].append(uid)
        save_admin_db()
        
        # ৩. সার্ভিস (Service Management) রি-স্টোর
        services_doc = db_firestore.collection("DXA_System").document("Services_Data").get()
        if services_doc.exists:
            srv_data = services_doc.to_dict()
            if "services" in srv_data:
                with open(SERVICES_FILE, "w", encoding="utf-8") as f:
                    json.dump(srv_data["services"], f, indent=2, ensure_ascii=False)
                    
        # ৪. প্যানেল (Panel Management) রি-স্টোর
        panels_doc = db_firestore.collection("DXA_System").document("Panels_Data").get()
        if panels_doc.exists:
            pnl_data = panels_doc.to_dict()
            if "panels" in pnl_data:
                with open(PANELS_FILE, "w", encoding="utf-8") as f:
                    json.dump(pnl_data["panels"], f, indent=2, ensure_ascii=False)
                    
        logger.info("Successfully restored essential data from Firestore on boot!")
    except Exception as e:
        logger.error(f"Failed to restore from Firestore: {e}")

# বট স্টার্ট হলেই ডেটা রিস্টোর হবে
restore_from_firestore()

def sync_essential_data_to_firestore():
    """Syncs only essential data: User Balances, Panels, Services, and Config to Firestore"""
    if not db_firestore: 
        return False, "Firebase is not initialized."
    try:
        # 1. User Balances & Stats
        stats = admin_db.get("user_stats", {})
        clean_stats = {}
        for uid, data in stats.items():
            if data.get("balance", 0.0) > 0 or data.get("otp_count", 0) > 0:
                clean_stats[uid] = {
                    "balance": data.get("balance", 0.0),
                    "otp_count": data.get("otp_count", 0)
                }
        
        db_firestore.collection("DXA_System").document("Users_Data").set({
            "total_users": len(admin_db.get("users", [])),
            "active_users": clean_stats,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 2. Panels Config (Cleaned without junk session cookies)
        clean_panels = []
        for p in panels:
            clean_panels.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "status": p.get("status"),
                "url": p.get("url"),
                "getNumberUrl": p.get("getNumberUrl", ""),
                "getMessageUrl": p.get("getMessageUrl", "")
            })
            
        db_firestore.collection("DXA_System").document("Panels_Data").set({
            "panels": clean_panels,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 3. Services & Countries
        services_dict = load_services()
        db_firestore.collection("DXA_System").document("Services_Data").set({
            "services": services_dict,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 4. Admin Config
        db_firestore.collection("DXA_System").document("Bot_Config").set({
            "dxa_config": admin_db.get("dxa_config", {}),
            "search_cfg": admin_db.get("search_cfg", {}),
            "admins": admin_db.get("admins", []),
            "otp_group_link": admin_db.get("otp_group_link", ""),
            "forward_groups": admin_db.get("forward_groups", []),
            "force_join_status": admin_db.get("force_join_status", False),
            "force_join_channels": admin_db.get("force_join_channels", []),
            "banned_users": admin_db.get("banned_users", []),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return True, "Successfully synced Balances, Panels, Services & Config to Firestore!"
    except Exception as e:
        return False, f"Firestore Sync Error: {e}"

# Telegram Secrets moved to the top

# Global variables/caches
user_conversations = {}
user_prompts = {}
sessions = {}
panel_backoff_until = {}  # Dynamic rate limit tracking
local_traffic_stats = {}  # 🚀 Fast Traffic Local Database
local_raw_logs_cache = {} # 🚀 Cumulative logs to prevent data loss

# Mapped country metadata
shortCountryCodes = {
    'CI': {'name': "Côte d'Ivoire (Ivory Coast)", 'flag': '🇨🇮'},
    'CM': {'name': 'Cameroon', 'flag': '🇨🇲'},
    'TG': {'name': 'Togo', 'flag': '🇹🇬'},
    'MG': {'name': 'Madagascar', 'flag': '🇲🇬'},
    'BJ': {'name': 'Benin', 'flag': '🇧🇯'},
    'GN': {'name': 'Guinea', 'flag': '🇬🇳'},
    'GA': {'name': 'Gabon', 'flag': '🇬🇦'},
    'CF': {'name': 'Central African Republic', 'flag': '🇨🇫'},
    'CG': {'name': 'Congo', 'flag': '🇨🇬'},
    'CD': {'name': 'DR Congo', 'flag': '🇨🇩'},
    'SN': {'name': 'Senegal', 'flag': '🇸🇳'},
    'ML': {'name': 'Mali', 'flag': '🇲🇱'},
    'TJ': {'name': 'Tajikistan', 'flag': '🇹🇯'},
    'BF': {'name': 'Burkina Faso', 'flag': '🇧🇫'},
    'NE': {'name': 'Niger', 'flag': '🇳🇪'},
    'TD': {'name': 'Chad', 'flag': '🇹🇩'},
}

prefixCountryMap = {
    '237': 'Cameroon 🇨🇲',
    '225': 'Ivory Coast 🇨🇮',
    '228': 'Togo 🇹🇬',
    '261': 'Madagascar 🇲🇬',
    '229': 'Benin 🇧🇯',
    '224': 'Guinea 🇬🇳',
    '241': 'Gabon 🇬🇦',
    '236': 'Central African Republic 🇨🇫',
    '242': 'Congo 🇨🇬',
    '243': 'DR Congo 🇨🇩',
    '221': 'Senegal 🇸🇳',
    '223': 'Mali 🇲🇱',
    '992': 'Tajikistan 🇹🇯',
    '7992': 'Tajikistan 🇹🇯',
    '226': 'Burkina Faso 🇧🇫',
    '227': 'Niger 🇳🇪',
    '235': 'Chad 🇹🇩',
}

# ----------------------------------------------------
# Utilities
# ----------------------------------------------------

# ----------------------------------------------------
# Premium Emoji Database
# ----------------------------------------------------
PREMIUM_EMOJIS = {
    "dxa": "<tg-emoji emoji-id='5334763399299506604'>😒</tg-emoji>",
    "time": "<tg-emoji emoji-id='5336983442125001376'>🕓</tg-emoji>",
    "otp": "<tg-emoji emoji-id='5337255927735163754'>🔐</tg-emoji>",
    "fire": "<tg-emoji emoji-id='5337267511261960341'>🔥</tg-emoji>",
    "king": "<tg-emoji emoji-id='5353032893096567467'>👑</tg-emoji>",
    "dashboard": "<tg-emoji emoji-id='5352877703043258544'>📊</tg-emoji>",
    "user": "<tg-emoji emoji-id='5352861489541714456'>👤</tg-emoji>",
    "rocket": "<tg-emoji emoji-id='5352597830089347330'>🚀</tg-emoji>",
    "gem": "<tg-emoji emoji-id='5352838545826420397'>💎</tg-emoji>",
    "done": "<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji>",
    "error": "<tg-emoji emoji-id='5420130255174145507'>❌</tg-emoji>",
    "search": "<tg-emoji emoji-id='5463352748751753567'>🔍</tg-emoji>",
    "number": "<tg-emoji emoji-id='5337132498965010628'>🍏</tg-emoji>",
    "phone": "<tg-emoji emoji-id='5355208818017999139'>📱</tg-emoji>",
    "warn": "<tg-emoji emoji-id='5336944168944047463'>⚠️</tg-emoji>",
    "wait": "<tg-emoji emoji-id='5337172996211648018'>⏳</tg-emoji>",
    "note": "<tg-emoji emoji-id='5395444784611480792'>📝</tg-emoji>",
    "world": "<tg-emoji emoji-id='5336972142066047577'>🌐</tg-emoji>",
    "gear": "<tg-emoji emoji-id='5420155432272438703'>⚙️</tg-emoji>",
    "back": "<tg-emoji emoji-id='5267490665117275176'>⬅️</tg-emoji>"
}

RAW_APP_EMOJIS = {
    "facebook": "5334807341109908955", "whatsapp": "5334759662677957452",
    "telegram": "5337010556253543833", "imo": "5337155807752524558",
    "instagram": "5334868205091459431", "apple": "5334637951894722661",
    "google": "5335010201005231986", "microsoft": "5334880948259427772",
    "tiktok": "5339213256001102461", "amazon": "4995019580536524226",
    "twitter": "5215726959056662534", "snapchat": "5359441366554255082",
    "netflix": "6255738712664050133", "linkedin": "6224222994265279792",
    "discord": "5116246243646898866", "viber": "5463060437572528782",
    "wechat": "5782757599560602950", "line": "5399818044866327279",
    "paypal": "5776103539872896061", "uber": "5298715455316303708",
    "bkash": "5348469219761626211", "rocket": "5352597830089347330",
    "binance": "5348212415077064131", "bybit": "5348372939479751825",
    "gmail": "5348494358205207761", "messenger": "5348486915026884464",
    "chrome": "5346311574221000149", "chatgpt": "5296516998996445955",
    "github": "5417836094098007862", "canva": "5111661409008092227"
}

def get_pemoji(key, fallback=""):
    return PREMIUM_EMOJIS.get(key.lower(), fallback)

def load_premium_apps():
    if os.path.exists("premium_apps.json"):
        try:
            with open("premium_apps.json", "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

RAW_FLAG_EMOJIS = {
    "CI": {"phone_code": "225", "flag": "🇨🇮", "name": "Côte d'Ivoire (Ivory Coast)", "id": "5222233374948602940"},
    "SL": {"phone_code": "232", "flag": "🇸🇱", "name": "Sierra Leone", "id": "5911210450657218661"},
    "MG": {"phone_code": "261", "flag": "🇲🇬", "name": "Madagascar", "id": "5913766918271012920"},
    "CM": {"phone_code": "237", "flag": "🇨🇲", "name": "Cameroon", "id": "5911172109484167745"},
    "RO": {"phone_code": "40", "flag": "🇷🇴", "name": "Romania", "id": "5913460373570195273"},
    "KE": {"phone_code": "254", "flag": "🇰🇪", "name": "Kenya", "id": "5911154710571651231"},
    "MR": {"phone_code": "222", "flag": "🇲🇷", "name": "Mauritania", "id": "5433859405898594234"},
    "CF": {"phone_code": "236", "flag": "🇨🇫", "name": "Central African Republic", "id": "5913443245240619222"},
    "TG": {"phone_code": "228", "flag": "🇹🇬", "name": "Togo", "id": "5913423260757790970"},
    "TJ": {"phone_code": "992", "flag": "🇹🇯", "name": "Tajikistan", "id": "5911287639809463107"},
    "TZ": {"phone_code": "255", "flag": "🇹🇿", "name": "Tanzania", "id": "5911418949844603556"},
    "MM": {"phone_code": "95", "flag": "🇲🇲", "name": "Myanmar", "id": "5433666360003540231"},
    "TN": {"phone_code": "216", "flag": "🇹🇳", "name": "Tunisia", "id": "5911332947419468671"},
    "GN": {"phone_code": "224", "flag": "🇬🇳", "name": "Guinea", "id": "5913471858312744319"},
    "BJ": {"phone_code": "229", "flag": "🇧🇯", "name": "Benin", "id": "5913735869952430547"},
    "UA": {"phone_code": "380", "flag": "🇺🇦", "name": "Ukraine", "id": "5222250679371839695"},
    "NG": {"phone_code": "234", "flag": "🇳🇬", "name": "Nigeria", "id": "5911143844304393105"},
    "KG": {"phone_code": "996", "flag": "🇰🇬", "name": "Kyrgyzstan", "id": "5911202161370337549"},
    "RU": {"phone_code": "79", "flag": "🇷🇺", "name": "Russian Federation", "id": "5913274246867456342"},
    "DE": {"phone_code": "49", "flag": "🇩🇪", "name": "Germany", "id": "5911096835887337583"},
    "HT": {"phone_code": "509", "flag": "🇭🇹", "name": "Haiti", "id": "5913459789454643194"},
    "NP": {"phone_code": "977", "flag": "🇳🇵", "name": "Nepal", "id": "5913496520014958723"},
    "ID": {"phone_code": "62", "flag": "🇮🇩", "name": "Indonesia", "id": "5913479361620611038"},
    "PK": {"phone_code": "92", "flag": "🇵🇰", "name": "Pakistan", "id": "5913705895375672082"}
}

def load_premium_flags():
    return RAW_FLAG_EMOJIS

def process_premium_txt(text_content):
    return 0, 0

def get_country_info(short_code):
    dyn_flags = load_premium_flags()
    
    # 🚀 Handle if the admin inputted a dialing code (e.g. 225, 880) instead of short code
    if str(short_code).isdigit() or str(short_code).startswith("+"):
        clean_phone = str(short_code).replace("+", "").strip()
        for code, info in dyn_flags.items():
            if info.get("phone_code") == clean_phone:
                return info
        
        resolved_code = get_country_code(clean_phone)
        if resolved_code != 'Unknown':
            short_code = resolved_code

    if short_code in dyn_flags:
        return dyn_flags[short_code]
    return shortCountryCodes.get(short_code, {"name": short_code, "flag": "🏳️", "id": "5336972142066047577"})

def get_app_raw_id(app_name):
    dyn_apps = load_premium_apps()
    name_lower = app_name.lower()
    
    for key, val in dyn_apps.items():
        if key in name_lower: return val
            
    for key, val in RAW_APP_EMOJIS.items():
        if key in name_lower: return val
    return "5336879280578138635" # Default 🖥 Other Service

def get_app_pemoji(app_name):
    raw_id = get_app_raw_id(app_name)
    return f"<tg-emoji emoji-id='{raw_id}'>🖥</tg-emoji>"

def escape_html(text):
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def mask_number(num):
    if not num:
        return ""
    num_str = str(num).replace("+", "").strip()
    if len(num_str) <= 6:
        return num_str
    first_3 = num_str[:3]
    last_3 = num_str[-3:]
    # এখানে ❖ যোগ করা হলো
    return f"{first_3}❖DXA❖{last_3}"

def extract_otp(text):
    if not text:
        return "No OTP Found"
    
    # ১. হাইফেন বা স্পেস ছাড়া সরাসরি ৪-৮ ডিজিট (যেমন: 123456)
    match = re.search(r'\b\d{4,8}\b', text)
    if match: return match.group(0)
    
    # ২. হাইফেন যুক্ত ওটিপি (যেমন: 123-456)
    match = re.search(r'\b\d{3}-\d{3}\b', text)
    if match: return match.group(0).replace("-", "")

    # ৩. স্পেস যুক্ত ওটিপি যা Instagram এ থাকে (যেমন: 123 456)
    match = re.search(r'\b\d{3}\s\d{3}\b', text)
    if match: return match.group(0).replace(" ", "")

    # ৪. টেক্সটের ভেতরে থাকা ওটিপি খোঁজা
    matches = re.findall(r'(\b\d{3,4}-\d{3,4}\b)|(\b\d{4,8}\b)', text)
    if matches:
        first_match = next((item for item in matches[0] if item), "")
        return first_match.replace("-", "").replace(" ", "")

    return "No OTP Found"

def normalize_base_url(input_url):
    url = input_url.strip()
    if not re.match(r'^https?://', url, re.IGNORECASE):
        url = 'https://' + url
        
    if '/#/' in url:
        url = url.split('/#/')[0]
    elif '/#' in url:
        url = url.split('/#')[0]
        
    while url.endswith('/'):
        url = url[:-1]
        
    changed = True
    while changed:
        changed = False
        lower = url.lower()
        if lower.endswith('/mauth/login'):
            url = url[:-12]
            changed = True
        elif lower.endswith('/mauth'):
            url = url[:-6]
            changed = True
        elif lower.endswith('/auth/login'):
            url = url[:-11]
            changed = True
        elif lower.endswith('/auth'):
            url = url[:-5]
            changed = True
        elif lower.endswith('/login.php'):
            url = url[:-10]
            changed = True
        elif lower.endswith('/login'):
            url = url[:-6]
            changed = True
        elif lower.endswith('/signin'):
            url = url[:-7]
            changed = True
        elif lower.endswith('/client/smscdrstats'):
            url = url[:-19]
            changed = True
        elif lower.endswith('/cdrs'):
            url = url[:-5]
            changed = True
        elif lower.endswith('/app'):
            url = url[:-4]
            changed = True
        elif lower.endswith('/dashboard'):
            url = url[:-10]
            changed = True
            
        while url.endswith('/'):
            url = url[:-1]
            changed = True
            
    return url

# Time Helpers Matching JS CEST timezone logic
def parse_time_to_seconds(time_str):
    if not time_str:
        return 0
    parts = time_str.strip().split(':')
    h = int(parts[0]) if parts[0].isdigit() else 0
    m = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    s = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    return h * 3600 + m * 60 + s

def get_seconds_difference(time1, time2):
    t1 = parse_time_to_seconds(time1)
    t2 = parse_time_to_seconds(time2)
    diff = abs(t1 - t2)
    if diff > 43200:
        diff = 86400 - diff
    return diff

import datetime as dt
def get_current_cest_time():
    # Fetch UTC timezone then add CEST (+2)
    now_utc = dt.datetime.now(dt.timezone.utc)
    # Simple hours addition for CEST
    hour = (now_utc.hour + 2) % 24
    return f"{hour:02d}:{now_utc.minute:02d}:{now_utc.second:02d}"

# ----------------------------------------------------
# DB Load and Save
# ----------------------------------------------------

def load_services():
    default_services = {}
    if os.path.exists(SERVICES_FILE):
        try:
            with open(SERVICES_FILE, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, dict):
                    return content
                elif isinstance(content, list): # Purgatory Migration
                    return {"stexsms": content}
        except Exception as e:
            logger.error(f"Error reading services.json: {e}")
            
    try:
        with open(SERVICES_FILE, "w", encoding="utf-8") as f:
            json.dump(default_services, f, indent=2, ensure_ascii=False)
        return default_services
    except Exception as e:
        logger.error(f"Error saving default services: {e}")
    return default_services

def save_services(services_dict):
    try:
        with open(SERVICES_FILE, "w", encoding="utf-8") as f:
            json.dump(services_dict, f, indent=2, ensure_ascii=False)
        # 🚀 সার্ভিস সেভ হওয়ার সাথে সাথেই ফায়ারবেসে সিঙ্ক করার ব্যাকগ্রাউন্ড থ্রেড
        threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
    except Exception as e:
        logger.error(f"Error saving services.json: {e}")

def load_panels():
    default_panels = [
        {
            "id": "voltx_api", "name": "Voltx API", "url": "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api", 
            "username": "API", "password": "MKJGS2MSZYB", 
            "getNumberUrl": "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/getnum", 
            "getMessageUrl": "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/success-otp", 
            "trafficUrl": "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api/console", 
            "sessionCookie": "MKJGS2MSZYB", "lastSeenCDRId": None, "status": "Initializing...", "lastSeenGetnumIds": []
        }
    ]
    if not os.path.exists(PANELS_FILE):
        save_panels_to_file(default_panels)
        return default_panels
    try:
        with open(PANELS_FILE, "r", encoding="utf-8") as f:
            list_panels = json.load(f)
            if not list_panels:
                list_panels = default_panels
            else:
                existing_ids = [p.get("id", "") for p in list_panels]
                for dp in default_panels:
                    if dp["id"] not in existing_ids:
                        list_panels.append(dp)
            for p in list_panels:
                p.setdefault("id", p.get("name", "panel").lower().replace(" ", "-"))
                p.setdefault("sessionCookie", "")
                p.setdefault("lastSeenCDRId", None)
                p.setdefault("lastSeenGetnumIds", [])
                p.setdefault("status", "Initializing...")
            return list_panels
    except Exception as e:
        logger.error(f"Failed to read panels.json: {e}")
        return default_panels

def save_panels_to_file(panels_list):
    try:
        with open(PANELS_FILE, "w", encoding="utf-8") as f:
            json.dump(panels_list, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save panels.json: {e}")

# Global Active Config List
panels = load_panels()

def get_session(panel_id):
    if panel_id not in sessions:
        try:
            import cloudscraper
            s = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        except ImportError:
            s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        sessions[panel_id] = s
    return sessions[panel_id]

# ----------------------------------------------------
# Telegram API - Sanitized for zero Bad Request 400
# ----------------------------------------------------

def clean_keyboard(reply_markup):
    return reply_markup

def call_telegram(method, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    try:
        if "reply_markup" in payload:
            payload["reply_markup"] = clean_keyboard(payload["reply_markup"])
        # টাইমআউট 15 থেকে বাড়িয়ে 40 করে দেওয়া হলো
        res = requests.post(url, json=payload, timeout=40)
        return res.json()
    except Exception as e:
        logger.error(f"Telegram {method} raw execution exception: {e}")
        return None

def send_bot_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return call_telegram("sendMessage", payload)

def edit_bot_message(chat_id, message_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return call_telegram("editMessageText", payload)

def answer_callback(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        if show_alert:
            payload["show_alert"] = True
    call_telegram("answerCallbackQuery", payload)

def get_otp_group_btn():
    link = admin_db.get("otp_group_link", "").strip()
    if link and link.startswith("http"):
        return {"text": " Otp Group", "url": link, "style": "primary", "icon_custom_emoji_id": "5420145051336485498"}
    return {"text": " Otp Group", "callback_data": "usr_otp_grp", "style": "primary", "icon_custom_emoji_id": "5420145051336485498"}

def get_service_short_code(name, sms_body=""):
    text = (str(name) + " " + str(sms_body)).lower()
    if 'whatsapp' in text or 'wa' in text: return 'WS'
    if 'facebook' in text or 'fb' in text: return 'FB'
    if 'telegram' in text or 'tg' in text: return 'TG'
    if 'instagram' in text or 'ig' in text: return 'IG'
    if 'tiktok' in text or 'tt' in text: return 'TT'
    if 'google' in text: return 'GG'
    if 'microsoft' in text: return 'MS'
    if 'imo' in text: return 'IMO'
    if 'viber' in text: return 'VI'
    if 'snapchat' in text: return 'SC'
    if 'wechat' in text: return 'WC'
    if 'line' in text: return 'LN'
    if 'twitter' in text or ' x ' in text: return 'TW'
    if 'paypal' in text: return 'PP'
    if 'discord' in text: return 'DC'
    if 'amazon' in text: return 'AMZ'
    return 'OTP'

def send_to_telegram(message, otp=None, quick_range=None, full_sms_body=None, svc_em_id=None, buyer_chat_id=None, unmasked_number=None, svc_short=None, flag=None):
    fwd_groups = admin_db.get("forward_groups", [])
        
    base_keyboard = []
    
    # ওটিপি বাটন লজিক: ওটিপি না থাকলে "Copy SMS" আসবে
    if full_sms_body:
        has_otp = otp and otp != "No OTP Found"
        btn_label = f" {otp}" if has_otp else " Copy SMS"
        copy_val = otp if has_otp else full_sms_body
        
        otp_btn = {
            "text": btn_label,
            "copy_text": {"text": copy_val},
            "style": "success",
            "icon_custom_emoji_id": svc_em_id if svc_em_id else "5337255927735163754"
        }
        base_keyboard.append([otp_btn])

    # Full Message button has been removed from inline keyboard

    # --- Send to Inbox (Buyer) ---
    if buyer_chat_id and unmasked_number and svc_short and flag:
        
        # ডেটাবেস থেকে বর্তমান রিওয়ার্ড অ্যামাউন্ট (TK) নেওয়া হচ্ছে
        reward_amount = admin_db.get("dxa_config", {}).get("otp_reward", 0.0)

        inbox_msg = (
            f"━━━━━━━━━━━━━━━\n"
            f"<blockquote><b>{get_pemoji('phone', '📱')} Number :</b> <code>{unmasked_number}</code></blockquote>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<blockquote><b>{get_pemoji('note', '📝')} FULL MESSAGE :</b>\n"
            f"<code><i># {escape_html(full_sms_body)}</i></code></blockquote>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<blockquote><b>{get_pemoji('gem', '💎')} ADDED :</b> <b>{reward_amount} TK</b></blockquote>\n"
            f"━━━━━━━━━━━━━━━"
        )
        
        inbox_payload = {
            "chat_id": buyer_chat_id,
            "text": inbox_msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        if base_keyboard:
            inbox_payload["reply_markup"] = {"inline_keyboard": base_keyboard}
        call_telegram("sendMessage", inbox_payload)

    # --- Send to Groups ---
    for grp in fwd_groups:
        chat_id = grp.get("id")
        custom_btns = grp.get("buttons", [])
        
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        group_keyboard = [row for row in base_keyboard]
        
        if custom_btns:
            btn_row = []
            for btn in custom_btns:
                btn_text = btn.get("text", "")
                btn_url = btn.get("url", "")
                
                btn_obj = {"text": btn_text, "url": btn_url}
                
                # 🚀 Priority 1: Use extracted premium emoji ID from DB
                if btn.get("emoji_id"):
                    btn_obj["icon_custom_emoji_id"] = btn.get("emoji_id")
                    btn_obj["style"] = "primary"
                else:
                    # 🚀 Fallback logic for old buttons or normal text
                    match = re.search(r'^([^\w\s]+)\s*(.*)', btn_text)
                    if match:
                        app_em_id = get_app_raw_id(match.group(2).strip())
                        if app_em_id and app_em_id != "5336879280578138635":
                            btn_obj["icon_custom_emoji_id"] = app_em_id
                            btn_obj["style"] = "primary"
                            btn_obj["text"] = f" {match.group(2).strip()}"
                
                btn_row.append(btn_obj)
                if len(btn_row) == 2:
                    group_keyboard.append(btn_row)
                    btn_row = []
            if btn_row:
                group_keyboard.append(btn_row)
                
        if group_keyboard:
            payload["reply_markup"] = {"inline_keyboard": group_keyboard}

        call_telegram("sendMessage", payload)

def process_and_send_sms(panel_name, raw_number, app_name, msg_body):
    otp = extract_otp(msg_body)
    masked_number = mask_number(raw_number)
    clean_num = str(raw_number).replace("+", "").strip()
    c_code = get_country_code(clean_num)
    c_info = get_country_info(c_code)
    flag = c_info.get('flag', '🏳️')
    
    svc_short = get_service_short_code(app_name, msg_body)
    
    # Smart Service Emoji Finder
    actual_app_name = str(app_name).strip() if app_name else ""
    if not actual_app_name:
        mb_lower = msg_body.lower()
        if "facebook" in mb_lower or "fb" in mb_lower: actual_app_name = "facebook"
        elif "whatsapp" in mb_lower or "wa" in mb_lower: actual_app_name = "whatsapp"
        elif "telegram" in mb_lower: actual_app_name = "telegram"
        elif "instagram" in mb_lower: actual_app_name = "instagram"
        elif "tiktok" in mb_lower: actual_app_name = "tiktok"
        elif "google" in mb_lower: actual_app_name = "google"
        elif "microsoft" in mb_lower: actual_app_name = "microsoft"
        else: actual_app_name = svc_short
        
    svc_em_id = get_app_raw_id(actual_app_name)
    
    # গ্রুপ মেসেজের জন্য প্রিমিয়াম ফ্ল্যাগ তৈরি
    f_id_grp = c_info.get('id', '5336972142066047577')
    premium_flag_grp = f"<tg-emoji emoji-id='{f_id_grp}'>{flag}</tg-emoji>"

    # নতুন মাস্কিং স্টাইল অনুযায়ী স্প্লিট করা হচ্ছে
    parts = masked_number.split("❖DXA❖")
    if len(parts) == 2:
        # ❖SHA❖ দিয়ে নম্বর মাস্কিং করা হলো
        linked_number = f"{parts[0]}❖SHA❖{parts[1]}"
    else:
        linked_number = f"{masked_number}"
    
    # নতুন ডিজাইনের গ্রুপ মেসেজ (সব লাইন quote format)
    group_message = (
        f"━━━━━━━━━━━━━━━\n"
        f"<blockquote><b>{get_pemoji('phone', '📱')} Number :</b> {premium_flag_grp} <code>{linked_number}</code></blockquote>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<blockquote><b>{get_pemoji('otp', '🔑')} OTP :</b> <code>{otp if otp and otp != 'No OTP Found' else 'No OTP Found'}</code></blockquote>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<blockquote><b>{get_pemoji('note', '📩')} FULL MESSAGE :</b> <code><i>\n# {escape_html(msg_body)}</i></code></blockquote>\n"
        f"━━━━━━━━━━━━━━━"
    )
    
    buyer_chat_id = admin_db.get("active_numbers", {}).get(clean_num)
    if otp and otp != "No OTP Found" and buyer_chat_id:
        stats = admin_db.setdefault("user_stats", {}).setdefault(str(buyer_chat_id), {})
        stats.setdefault("otp_count", 0)
        stats.setdefault("balance", 0.0)
        cfg = admin_db.get("dxa_config", {})
        stats["otp_count"] += 1
        stats["balance"] += float(cfg.get("otp_reward", 0.0))
        if stats.get("active_reqs"): stats["active_reqs"].pop(0)
        save_admin_db()
        
    quick_range = get_range_from_number(clean_num)
    send_to_telegram(group_message, otp, quick_range, msg_body, svc_em_id, buyer_chat_id, clean_num, svc_short, flag)

# ----------------------------------------------------
# Math Captcha & Authentication Solvers
# ----------------------------------------------------

def is_voltx_api(panel):
    if not panel or not panel.get("url"): return False
    url_lower = panel["url"].lower()
    id_lower = panel.get("id", "").lower()
    return "@public/api" in url_lower or "voltx_api" in id_lower or "voltx api" in id_lower

def get_clean_base_url(panel, base_url):
    if panel.get("resolvedBaseUrl"): return panel["resolvedBaseUrl"].rstrip('/')
    return base_url.split('#')[0].rstrip('/')

def login_to_panel(panel, force=False):
    panel_id = panel["id"]
    now = time.time()
    if not force and panel_id in panel_backoff_until and now < panel_backoff_until[panel_id]:
        logger.info(f"[{panel['name']}] Login requested skipped due to backoff.")
        return False

    panel["status"] = "Running (API)"
    panel["sessionCookie"] = panel.get("password", "MKJGS2MSZYB")
    save_panels_to_file(panels)
    return True

# ----------------------------------------------------
# Live SMS Real Purchasing
# ----------------------------------------------------

def buy_number(range_val, target_panel_id=None):
    panel = None
    if target_panel_id:
        panel = next((p for p in panels if p.get("id") == target_panel_id), None)
    else:
        services_data = load_services()
        supported_panels = []
        for p_id, s_list in services_data.items():
            for s in s_list:
                for c in s.get("countries", []):
                    clean_target = range_val.replace("X", "").replace("*", "")
                    if any(clean_target in r for r in c.get("ranges", [])):
                        supported_panels.append(p_id)
        if supported_panels:
            chosen_p_id = random.choice(supported_panels)
            panel = next((p for p in panels if p.get("id") == chosen_p_id), None)
            logger.info(f"Randomly selected panel {chosen_p_id} for range {range_val}")
        else:
            panel = panels[0] if panels else None
            
    if not panel:
        return {"success": False, "message": "No suitable panel configuration found."}

    if not panel.get("sessionCookie"):
        login_to_panel(panel, force=True)
        if not panel.get("sessionCookie"):
            return {"success": False, "message": "Stex SMS authentication failed. Credentials check required."}

    try:
        clean_base = get_clean_base_url(panel, panel["url"])
        num_url = panel.get("getNumberUrl") or f"{clean_base}/getnum"
        headers = {
            "Content-Type": "application/json",
            "mauthapi": panel.get("sessionCookie", "MKJGS2MSZYB")
        }
        rid = range_val.replace("X", "").replace("*", "").strip()
        
        res = requests.post(num_url, json={"rid": rid}, headers=headers, timeout=20)
        
        if res.status_code == 200:
            data = res.json()
            if data.get("meta", {}).get("code") == 200 and data.get("data"):
                num_data = data["data"]
                today = datetime.now().strftime("%Y-%m-%d")
                if admin_db.get("today_date") != today:
                    admin_db["today_date"] = today
                    admin_db["today_numbers_count"] = 0
                admin_db["today_numbers_count"] = admin_db.get("today_numbers_count", 0) + 1
                save_admin_db()

                return {
                    "success": True,
                    "message": data.get("message", "Number allocated successfully"),
                    "number": num_data.get("full_number") or num_data.get("no_plus_number") or "",
                    "operator": num_data.get("operator", "Unknown"),
                    "country": num_data.get("country", "Unknown")
                }
            return {"success": False, "message": data.get("message", "Failed to get number from API.")}
        return {"success": False, "message": f"API Error: {res.status_code}"}
    except Exception as e:
        logger.error(f"Error buying number for range: {e}")
        return {"success": False, "message": str(e)}

# ----------------------------------------------------
# Active Traffic Aggregation Compiler
# ----------------------------------------------------

def compile_traffic_stats():
    # 🚀 Returns instant cached data from local database
    global local_traffic_stats
    return local_traffic_stats, get_current_cest_time(), False

def get_country_code(num):
    clean = str(num).replace('+', '').strip()
    
    # স্পেশাল কেস (তাজিকিস্তান)
    if clean.startswith('7992'): return 'TJ'
    
    # আপনার সেট করা নতুন দেশের লিস্ট থেকে স্বয়ংক্রিয়ভাবে চেক করা হবে
    flags = load_premium_flags()
    # ফোন কোডের সাইজ অনুযায়ী সর্ট করা (যাতে বড় কোডগুলো আগে চেক হয়)
    sorted_flags = sorted(flags.items(), key=lambda x: len(x[1].get("phone_code", "")), reverse=True)
    
    for short_code, info in sorted_flags:
        if clean.startswith(info["phone_code"]):
            return short_code
            
    # পুরনো কিছু ফলব্যাক (যদি কোনোটি লিস্টে না থাকে)
    if clean.startswith('241'): return 'GA'
    if clean.startswith('242'): return 'CG'
    if clean.startswith('243'): return 'CD'
    if clean.startswith('221'): return 'SN'
    if clean.startswith('223'): return 'ML'
    if clean.startswith('226'): return 'BF'
    if clean.startswith('227'): return 'NE'
    if clean.startswith('235'): return 'TD'
    
    return 'Unknown'

def get_range_from_number(num):
    clean = str(num).replace('+', '').strip()
    first_x = re.search(r'[Xx*\-]', clean)
    if first_x:
        clean = clean[:first_x.start()]
    if clean.startswith('225') and len(clean) > 7:
        return clean[:7]
    if len(clean) > 8:
        return clean[:8]
    return clean

def get_service_short_code(name, sms_body=""):
    text = (str(name) + " " + str(sms_body)).lower()
    if 'whatsapp' in text or 'wa' in text: return 'WS'
    if 'facebook' in text or 'fb' in text: return 'FB'
    if 'telegram' in text or 'tg' in text: return 'TG'
    if 'instagram' in text or 'ig' in text: return 'IG'
    if 'tiktok' in text or 'tt' in text: return 'TT'
    if 'google' in text: return 'GG'
    if 'microsoft' in text: return 'MS'
    if 'imo' in text: return 'IMO'
    if 'viber' in text: return 'VI'
    if 'snapchat' in text: return 'SC'
    if 'wechat' in text: return 'WC'
    if 'line' in text: return 'LN'
    if 'twitter' in text or ' x ' in text: return 'TW'
    if 'paypal' in text: return 'PP'
    if 'discord' in text: return 'DC'
    if 'amazon' in text: return 'AMZ'
    return 'OTP'

def get_service_display_name(name):
    lower = str(name).strip().lower()
    if 'facebook' in lower or lower == 'fb': return 'Facebook'
    if 'whatsapp' in lower or lower == 'wa': return 'WhatsApp'
    if 'telegram' in lower or lower == 'tg': return 'Telegram'
    if 'instagram' in lower or lower == 'ig': return 'Instagram'
    if 'microsoft' in lower or lower == 'ms': return 'Microsoft'
    if 'google' in lower or lower == 'gg': return 'Google'
    if 'imo' in lower: return 'IMO'
    if 'tiktok' in lower or lower == 'tt': return 'TikTok'
    if 'snapchat' in lower: return 'Snapchat'
    if 'viber' in lower: return 'Viber'
    if 'line' in lower: return 'LINE'
    if 'wechat' in lower: return 'WeChat'
    if 'twitter' in lower or lower == 'x': return 'Twitter'
    if 'postpaid' in lower: return 'PostPaid'
    if 'failed' in lower: return 'Failed Calls'
    return str(name).strip().capitalize()

def find_service_by_slug(stats, slug):
    # একদম হুবহু বা প্রথম ৫০ ক্যারেক্টার ম্যাচ করানো হচ্ছে যাতে কনফ্লিক্ট না হয়
    for service in stats.keys():
        if service[:50] == slug:
            return service
    for service in stats.keys():
        if slug.lower() in service.lower():
            return service
    return None

# ----------------------------------------------------
# Traffic Visualizers Layout
# ----------------------------------------------------

def render_traffic_home(chat_id, message_id=None):
    try:
        stats, ref_time, is_fallback = compile_traffic_stats()
        
        message_text = "╔═══════════════╗\n" \
                       f"║ <tg-emoji emoji-id='5352877703043258544'>📈</tg-emoji> <b>NETWORK TRAFFIC</b>\n" \
                       "╚═══════════════╝\n"

        services_with_counts = []
        for svc, ctrs in stats.items():
            total = sum(ctr_data["success"] for ctr_data in ctrs.values())
            services_with_counts.append((svc, total))

        services_with_counts.sort(key=lambda x: x[1], reverse=True)

        if not services_with_counts:
            message_text += "<i>No active traffic recorded in the last 10 minutes on DXA.</i>"
        else:
            is_first = True
            # ডাইনামিক ইনলাইন বাটনের ইমোজি আইডি
            raw_ids = {
                "Facebook": "5334807341109908955", "WhatsApp": "5334759662677957452",
                "Telegram": "5337010556253543833", "Instagram": "5334868205091459431",
                "Microsoft": "5334880948259427772", "Google": "5463352748751753567",
                "TikTok": "5339213256001102461"
            }
            
            for svc, total in services_with_counts:
                if not is_first:
                    message_text += "\n"
                is_first = False
                p_emoji = get_app_pemoji(svc)
                message_text += f"» {p_emoji} {svc}\n" \
                               f"➥ {total} OTP\n"

        inline_buttons = []
        for svc, total in services_with_counts:
            safe_slug = svc[:50]
            btn_emoji_id = get_app_raw_id(svc)
            inline_buttons.append([{
                "text": f" Explore {svc} Range",
                "callback_data": f"tr_svc:{safe_slug}",
                "style": "primary",
                "icon_custom_emoji_id": btn_emoji_id
            }])

        inline_buttons.append([
            {"text": " Refresh", "callback_data": "tr_refresh", "style": "success", "icon_custom_emoji_id": "5465368548702446780"},
            {"text": " Close", "callback_data": "tr_close", "style": "danger", "icon_custom_emoji_id": "5420130255174145507"}
        ])

        keyboard = {"inline_keyboard": inline_buttons}
        if message_id:
            edit_bot_message(chat_id, message_id, message_text, keyboard)
        else:
            send_bot_message(chat_id, message_text, keyboard)

    except Exception as e:
        error_msg = f"❌ Error fetching traffic stats: <code>{escape_html(str(e))}</code>"
        if message_id:
            edit_bot_message(chat_id, message_id, error_msg, {
                "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
            })
        else:
            send_bot_message(chat_id, error_msg, {
                "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
            })

def render_explore_service(chat_id, message_id, service_slug):
    try:
        stats, _, _ = compile_traffic_stats()
        service_name = find_service_by_slug(stats, service_slug)

        if not service_name or service_name not in stats:
            edit_bot_message(chat_id, message_id, f"❌ Service <code>{escape_html(service_slug)}</code> has no active traffic or has expired.", {
                "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
            })
            return

        text = f"{get_pemoji('king', '👑')} <b>Explore Service:</b> {service_name}\n\nSelect a country to view available ranges:"
        country_buttons = []
        sorted_codes = sorted(stats[service_name].keys(), key=lambda code: stats[service_name][code]["success"], reverse=True)
        
        for idx, code in enumerate(sorted_codes, start=1):
            c_info = get_country_info(code)
            name = c_info.get("name", "Unknown")
            em_id = c_info.get("id", "5336972142066047577") # Default World ID
            success_count = stats[service_name][code]["success"]
            
            country_buttons.append([{
                "text": f"{idx}. {name} ({code}) - {success_count} OTP",
                "callback_data": f"tr_ctr:{service_slug}:{code}",
                "style": "primary",
                "icon_custom_emoji_id": em_id
            }])

        country_buttons.append([{"text": " Back", "callback_data": "tr_refresh", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": country_buttons})

    except Exception as e:
        edit_bot_message(chat_id, message_id, f"❌ Error: <code>{escape_html(str(e))}</code>", {
            "inline_keyboard": [[{"text": "🔙 Back to Traffic Menu", "callback_data": "tr_refresh", "style": "danger"}]]
        })

def render_explore_ranges(chat_id, message_id, service_slug, country_code):
    try:
        stats, _, _ = compile_traffic_stats()
        service_name = find_service_by_slug(stats, service_slug)

        if not service_name or service_name not in stats or country_code not in stats[service_name]:
            edit_bot_message(chat_id, message_id, "❌ No active ranges found for this service and country.", {
                "inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"tr_svc:{service_slug}", "style": "danger"}]]
            })
            return

        c_info = get_country_info(country_code)
        flag_pemoji = f"<tg-emoji emoji-id='{c_info.get('id', '5336972142066047577')}'>{c_info.get('flag', '🏳️')}</tg-emoji>"
        
        text = f"{get_pemoji('king', '👑')} <b>Ranges for</b> {service_name} - {flag_pemoji} {country_code}\n\n" \
               "Click on any range below to get an instant tap-to-copy message!"

        range_buttons = []
        ranges_data = stats[service_name][country_code]["ranges"]
        sorted_ranges = sorted(ranges_data.items(), key=lambda x: x[1], reverse=True)

        for range_val, count in sorted_ranges:
            range_buttons.append([{
                "text": f" {range_val} ({count})",
                "copy_text": {"text": range_val},
                "style": "success",
                "icon_custom_emoji_id": "5192739271886282680" # Notepad/Clipboard emoji
            }])

        range_buttons.append([{"text": " Back", "callback_data": f"tr_svc:{service_slug}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": range_buttons})
        
    except Exception as e:
        edit_bot_message(chat_id, message_id, f"❌ Error: <code>{escape_html(str(e))}</code>", {
            "inline_keyboard": [[{"text": "🔙 Back", "callback_data": f"tr_svc:{service_slug}", "style": "danger"}]]
        })

# ----------------------------------------------------
# Search Engine and allocation routers
# ----------------------------------------------------

def search_number_otp(chat_id, query):
    passed, err_msg, _ = check_user_limits(chat_id, update_cooldown=False)
    if not passed:
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_search_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
        send_bot_message(chat_id, err_msg, kb)
        return

    clean_num = str(query).replace("+", "").strip()
    valid_panels = panels
    if not valid_panels:
        send_bot_message(chat_id, f"{get_pemoji('error', '❌')} No active panels available.")
        return
        
    panel = random.choice(valid_panels)
    if not panel.get("sessionCookie"): login_to_panel(panel, force=True)

    send_bot_message(chat_id, f"{get_pemoji('search', '🔍')} <i>Searching messages on <b>{panel['name']}</b> for <b>{escape_html(clean_num)}</b>...</i>")

    try:
        baseUrl = normalize_base_url(panel["url"])
        domain_match = re.match(r'^(https?://[^/]+)', baseUrl)
        domain = domain_match.group(1) if domain_match else baseUrl
        today_date_str = datetime.now().strftime("%Y-%m-%d")
        session = get_session(panel["id"])

        get_url = panel.get("getMessageUrl") or f"{get_clean_base_url(panel, panel['url'])}/success-otp"
        headers = {"mauthapi": panel.get("sessionCookie", "MKJGS2MSZYB")}
        res = session.get(get_url, headers=headers, timeout=20)
        
        if res.status_code == 200:
            data = res.json()
            otps = data.get("data", {}).get("otps", [])
            numbers = [{"number": i.get("number"), "message": i.get("message"), "app_name": "OTP"} for i in otps]
        else:
            send_bot_message(chat_id, f"❌ Voltx API search error: {res.status_code}")
            return

        if isinstance(numbers, list):
            matched = [num for num in numbers if clean_num in str(num.get("number", ""))]
            if matched:
                send_bot_message(chat_id, f"🔍 Found <b>{len(matched)}</b> match(es) for <code>{clean_num}</code>:")
                for num in matched:
                    raw_msg = num.get("message") or num.get("otp") or num.get("sms") or num.get("smsBody") or num.get("sms_text") or num.get("sms_body") or ""
                    msg = str(raw_msg).strip()
                    number_val = num.get("number", "")
                    
                    c_code = get_country_code(number_val)
                    c_info = get_country_info(c_code)
                    flag_em_id = c_info.get("id", "5336972142066047577")
                    
                    svc_name = num.get("app_name", "OTP")
                    svc_short = get_service_short_code(svc_name, msg)
                    svc_em_id = get_app_raw_id(svc_name)
                    
                    box_design = (
                        f"╔═════════════╗\n"
                        f"║ <tg-emoji emoji-id='{svc_em_id}'>💬</tg-emoji> #{svc_short} <tg-emoji emoji-id='{flag_em_id}'>🚩</tg-emoji> <code>{number_val}</code>\n"
                        f"╚═════════════╝"
                    )

                    inline_keyboard = []
                    if msg:
                        otp_val = extract_otp(msg)
                        has_otp = otp_val != "No OTP Found"
                        inline_keyboard.append([{
                            "text": f" {otp_val}" if has_otp else " Copy SMS",
                            "copy_text": {"text": otp_val if has_otp else msg},
                            "style": "success",
                            "icon_custom_emoji_id": svc_em_id
                        }])
                        inline_keyboard.append([{
                            "text": " Full Message",
                            "copy_text": {"text": msg},
                            "style": "primary",
                            "icon_custom_emoji_id": "5337302974806922068"
                        }])
                    else:
                        inline_keyboard.append([{
                            "text": " Pending (No SMS yet)",
                            "callback_data": "none",
                            "style": "danger",
                            "icon_custom_emoji_id": "5337172996211648018"
                        }])

                    search_range_val = get_range_from_number(number_val)
                    inline_keyboard.extend([
                        [
                            {"text": " Change Number", "callback_data": f"buy_{search_range_val}", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"},
                            get_otp_group_btn()
                        ],
                        [{"text": " Back", "callback_data": "usr_search_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
                    ])
                    send_bot_message(chat_id, box_design, {"inline_keyboard": inline_keyboard})
            else:
                send_bot_message(chat_id, f"❌ No active numbers found matching <code>{clean_num}</code> on {panel['name']} today.")
        else:
            send_bot_message(chat_id, "❌ Failed to retrieve valid numbers format from API.")
    except Exception as e:
        send_bot_message(chat_id, f"❌ Error searching database: <code>{escape_html(str(e))}</code>")

def trigger_buy_number(chat_id, range_val, target_panel_id=None, message_id=None, callback_id=None):
    try:
        passed, err_msg, batch_size = check_user_limits(chat_id)
        if not passed:
            if callback_id:
                answer_callback(callback_id, err_msg, show_alert=True)
            else:
                kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
                if message_id: edit_bot_message(chat_id, message_id, f"⚠️ {err_msg}", kb)
                else: send_bot_message(chat_id, f"⚠️ {err_msg}", kb)
            return

        if callback_id:
            answer_callback(callback_id, f"Requesting {range_val}...")

        initial_text = f"{get_pemoji('wait', '⏳')} <i>Allocating {batch_size} number(s) for range <b>{escape_html(range_val)}</b>... Please wait.</i>"
        
        if message_id:
            edit_bot_message(chat_id, message_id, initial_text)
        else:
            res = send_bot_message(chat_id, initial_text)
            message_id = res.get("result", {}).get("message_id") if res else None

        numbers_fetched = []
        last_err = "Unknown error"
        if "active_numbers" not in admin_db: admin_db["active_numbers"] = {}
        
        for _ in range(batch_size):
            result = buy_number(range_val, target_panel_id)
            if result.get("success"):
                numbers_fetched.append(result)
                number_val = result.get("number") or ""
                clean_num = str(number_val).replace("+", "").strip()
                admin_db["active_numbers"][clean_num] = str(chat_id)
            else:
                last_err = result.get("message", "Failed.")
                break
                
        if numbers_fetched:
            save_admin_db()
            c_code = get_country_code(numbers_fetched[0].get("number", ""))
            c_info = get_country_info(c_code)
            flag_em_id = c_info.get("id", "5336972142066047577")
            
            blank_text = "ㅤ"
            keyboard = {"inline_keyboard": []}
            
            for res in numbers_fetched:
                num = res.get("number", "")
                keyboard["inline_keyboard"].append([{
                    "text": f" +{num.replace('+', '')}",
                    "copy_text": {"text": f"{num}"},
                    "style": "primary",
                    "icon_custom_emoji_id": flag_em_id
                }])
                
            keyboard["inline_keyboard"].extend([
                [
                    {"text": " Change Number", "callback_data": f"buy_{range_val}", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"},
                    get_otp_group_btn()
                ],
                [{"text": " Back", "callback_data": "usr_search_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
            ])
            if message_id:
                edit_bot_message(chat_id, message_id, blank_text, keyboard)
            else:
                send_bot_message(chat_id, blank_text, keyboard)
        else:
            failure_text = f"❌ <b>Get Number Failed!</b>\n\n" \
                           f"<b>Range:</b> <code>{escape_html(range_val)}</code>\n" \
                           f"<b>Error:</b> <code>{escape_html(last_err)}</code>\n\n" \
                           f"<i>Please try again, or confirm you have enough balance.</i>"

            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔁 Retry getting range", "callback_data": f"buy_{range_val}", "style": "danger"}]
                ]
            }
            if message_id:
                edit_bot_message(chat_id, message_id, failure_text, keyboard)
            else:
                send_bot_message(chat_id, failure_text, keyboard)
    except Exception as e:
        logger.error(f"Error buying range: {e}")
        send_bot_message(chat_id, f"❌ <code>Error requesting number: {escape_html(str(e))}</code>")

def render_admin_panel(chat_id, message_id=None):
    if str(chat_id) not in admin_db.get("admins", [OWNER_ID]):
        send_bot_message(chat_id, "❌ You are not authorized to view the Admin Panel.")
        return

    # Check and reset daily count if needed
    today = datetime.now().strftime("%Y-%m-%d")
    if admin_db.get("today_date") != today:
        admin_db["today_date"] = today
        admin_db["today_numbers_count"] = 0
        save_admin_db()

    users_count = len(admin_db.get("users", []))
    numbers_count = admin_db.get("today_numbers_count", 0)

    text = (
        f"{get_pemoji('dashboard', '📊')} <b>ADMIN CONTROL PANEL</b> {get_pemoji('dashboard', '📊')}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{get_pemoji('dashboard', '📊')} <b>DATABASE OVERVIEW</b>\n"
        "— — — — — — — — — —\n"
        f"{get_pemoji('user', '👤')} <b>Users</b>      » {users_count}\n"
        f"{get_pemoji('number', '🔢')} <b>Numbers</b>    » {numbers_count} (Today)\n"
    )

    inline_keyboard = [
        [
            {"text": " Broadcast", "callback_data": "adm_broadcast", "style": "primary", "icon_custom_emoji_id": "5789428375261023681"},
            {"text": " Force Join", "callback_data": "adm_fj_menu", "style": "primary", "icon_custom_emoji_id": "5190447043545438788"}
        ],
        [{"text": " User Management", "callback_data": "adm_user_mgmt_menu", "style": "success", "icon_custom_emoji_id": "5352861489541714456"}],
        [{"text": " Admin Management", "callback_data": "adm_admin_menu", "style": "danger", "icon_custom_emoji_id": "5353032893096567467"}],
        [
            {"text": " System", "callback_data": "adm_system_menu", "style": "primary", "icon_custom_emoji_id": "5420155432272438703"},
            {"text": " Manage Dxa", "callback_data": "adm_dxa_menu", "style": "success", "icon_custom_emoji_id": "5352838545826420397"}
        ],
        [{"text": " Developer Info", "callback_data": "adm_developer", "style": "primary", "icon_custom_emoji_id": "5353032893096567467"}],
        [{"text": " Back to Home", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    
    keyboard = {"inline_keyboard": inline_keyboard}
    if message_id:
        edit_bot_message(chat_id, message_id, text, keyboard)
    else:
        send_bot_message(chat_id, text, keyboard)

def render_admin_developer(chat_id, message_id):
    text = (
        "╔═══════════╗\n"
        f"      {get_pemoji('dxa', '😒')} <b>DEVELOPER</b> {get_pemoji('dxa', '😒')}\n"
        "╚═══════════╝\n"
        f"{get_pemoji('user', '👤')} ➤ 𝐍𝐚𝐦𝐞 : <a href='https://t.me/SH_Official_Admin'>𝗔𝗟𝗜𝗙 𝗦𝗛𝗘𝗜𝗞𝗛</a> {get_pemoji('done', '✅')}\n\n"
        f"{get_pemoji('user', '👤')} ➤ 𝐍𝐢𝐜𝐤𝐍𝐚𝐦𝐞 : Asik\n\n"
        "📍 ➤ 𝐂𝐨𝐮𝐧𝐭𝐫𝐲 : Bangladesh\n\n"
        f"{get_pemoji('world', '🌐')} ➤ 𝐑𝐞𝐥𝐢𝐠𝐢𝐨𝐧 : Islam\n\n"
        "🔹 ➤ 𝐋𝐚𝐧𝐠𝐮𝐚𝐠𝐞 : বাংলা | English | Hindi\n\n"
        f"{get_pemoji('gem', '💎')} ➤ 𝐒𝐤𝐢𝐥𝐥 : Technology • Coding\n\n"
        f"{get_pemoji('fire', '🔥')} ➤ 𝐇𝐨𝐛𝐛𝐢𝐞𝐬 : Music • Anime"
    )
    
    inline_keyboard = [
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def check_force_join(chat_id, message_id=None):
    if str(chat_id) in admin_db.get("admins", [OWNER_ID]) or not admin_db.get("force_join_status", False):
        return True
        
    channels = admin_db.get("force_join_channels", [])
    if not channels:
        return True
        
    not_joined = []
    for ch in channels:
        check_id = ch
        if "t.me/" in ch:
            check_id = "@" + ch.split("t.me/")[1].split("/")[0]
            
        res = call_telegram("getChatMember", {"chat_id": check_id, "user_id": chat_id})
        if res and res.get("ok"):
            status = res.get("result", {}).get("status")
            if status in ["left", "kicked", "restricted"]:
                not_joined.append(ch)
        else:
            not_joined.append(ch)
            
    if not_joined:
        inline_keyboard = []
        for ch in not_joined:
            url = ch if ch.startswith("http") else f"https://t.me/{ch.replace('@', '')}"
            # Join channel buttons with premium 📢 icon
            inline_keyboard.append([{"text": f" Join {ch}", "url": url, "style": "primary", "icon_custom_emoji_id": "5789428375261023681"}])
        
        # Check again button with premium 🔄 icon
        inline_keyboard.append([{"text": " Check Again", "callback_data": "check_fj", "style": "success", "icon_custom_emoji_id": "5465368548702446780"}])
        
        text = (
            "╔═══════════════╗\n"
            "   <tg-emoji emoji-id='5190447043545438788'>🛡</tg-emoji> <b>ACCESS RESTRICTED</b>\n"
            "╚═══════════════╝\n\n"
            "Hello! To use our bot services, you must join our official channels listed below.\n\n"
            "<i>After joining, click the 'Check Again' button to verify.</i>"
        )
        
        if message_id:
            edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
        else:
            send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})
        return False
    return True

def render_force_join_menu(chat_id, message_id):
    status = admin_db.get("force_join_status", False)
    # Status label and style
    status_label = " ACTIVE: ON" if status else " ACTIVE: OFF"
    status_style = "success" if status else "danger"
    # ✅ if ON, ❌ if OFF
    status_emoji_id = "5352694861990501856" if status else "5420130255174145507"
    
    inline_keyboard = [
        [{"text": status_label, "callback_data": "adm_fj_toggle", "style": status_style, "icon_custom_emoji_id": status_emoji_id}]
    ]
    
    channels = admin_db.get("force_join_channels", [])
    if channels:
        for idx, ch in enumerate(channels):
            # Channel list with 🗑 icon and Danger style
            inline_keyboard.append([{"text": f" Remove: {ch}", "callback_data": f"adm_fj_del:{idx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    
    # Add Channel button with ➕ icon
    inline_keyboard.append([{"text": " Add New Channel", "callback_data": "adm_fj_add", "style": "primary", "icon_custom_emoji_id": "5420323438508155202"}])
    # Back button with ⬅️ icon
    inline_keyboard.append([{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    text = (
        f"<tg-emoji emoji-id='5420517437885943844'>🔗</tg-emoji> <b>FORCE JOIN MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Configure the channels users must join before using the bot.\n"
        "<i>Click the toggle to enable/disable the system.</i>"
    )
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_user_mgmt_menu(chat_id, message_id):
    text = (
        f"<tg-emoji emoji-id='5352861489541714456'>👤</tg-emoji> <b>USER MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Search for users to view profiles, manage their balances, or restrict their access."
    )
    inline_keyboard = [
        [{"text": " User Profile", "callback_data": "adm_um_prof", "style": "primary", "icon_custom_emoji_id": "5463352748751753567"}],
        [
            {"text": " Manage Balance", "callback_data": "adm_um_bal", "style": "success", "icon_custom_emoji_id": "5352838545826420397"},
            {"text": " Ban / Unban", "callback_data": "adm_um_ban", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}
        ],
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_um_profile(chat_id, message_id, target_uid):
    stats = admin_db.get("user_stats", {}).get(str(target_uid), {"otp_count": 0, "balance": 0.0})
    is_banned = str(target_uid) in admin_db.get("banned_users", [])
    status_text = "Banned 🚫" if is_banned else "Active ✅"
    
    text = (
        f"╔═══════════════╗\n"
        f"║ <tg-emoji emoji-id='5352861489541714456'>👤</tg-emoji> <b>USER PROFILE</b>\n"
        f"╚═══════════════╝\n\n"
        f"<b>User ID:</b> <code>{target_uid}</code>\n"
        f"<b>Status:</b> <b>{status_text}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5352838545826420397'>💎</tg-emoji> <b>Balance:</b> <code>{stats.get('balance', 0.0)} ৳</code>\n"
        f"<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji> <b>Total OTPs:</b> <code>{stats.get('otp_count', 0)}</code>\n"
    )
    inline_keyboard = [
        [{"text": " Manage Balance", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "success", "icon_custom_emoji_id": "5352838545826420397"}],
        [{"text": " Ban / Unban", "callback_data": f"adm_um_view_ban:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}],
        [{"text": " Back to Menu", "callback_data": "adm_user_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    if message_id: edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else: send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_um_balance(chat_id, message_id, target_uid):
    stats = admin_db.get("user_stats", {}).get(str(target_uid), {"otp_count": 0, "balance": 0.0})
    text = (
        f"<tg-emoji emoji-id='5352838545826420397'>💎</tg-emoji> <b>MANAGE BALANCE</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>User ID:</b> <code>{target_uid}</code>\n"
        f"<b>Current Balance:</b> <code>{stats.get('balance', 0.0)} ৳</code>\n\n"
        f"<i>Choose an action below to add or deduct balance.</i>"
    )
    inline_keyboard = [
        [
            {"text": " Add Balance", "callback_data": f"adm_bal_add:{target_uid}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"},
            {"text": " Deduct Balance", "callback_data": f"adm_bal_sub:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}
        ],
        [{"text": " Back to Profile", "callback_data": f"adm_um_view_prof:{target_uid}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    if message_id: edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else: send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_um_ban(chat_id, message_id, target_uid):
    is_banned = str(target_uid) in admin_db.get("banned_users", [])
    status_text = f"BANNED {get_pemoji('error', '🚫')}" if is_banned else f"ACTIVE {get_pemoji('done', '✅')}"
    
    text = (
        f"<tg-emoji emoji-id='5422557736330106570'>🚫</tg-emoji> <b>BAN / UNBAN USER</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>User ID:</b> <code>{target_uid}</code>\n"
        f"<b>Current Status:</b> <b>{status_text}</b>\n\n"
        f"<i>Banned users cannot use any bot commands or features.</i>"
    )
    
    btn_text = " Unban User" if is_banned else " Ban User"
    btn_icon = "5352694861990501856" if is_banned else "5420130255174145507"
    btn_style = "success" if is_banned else "danger"
    
    inline_keyboard = [
        [{"text": btn_text, "callback_data": f"adm_ban_tog:{target_uid}", "style": btn_style, "icon_custom_emoji_id": btn_icon}],
        [{"text": " Back to Profile", "callback_data": f"adm_um_view_prof:{target_uid}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    if message_id: edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else: send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_management_menu(chat_id, message_id):
    admins = admin_db.get("admins", [OWNER_ID])
    inline_keyboard = []
    
    for adm in admins:
        if adm == OWNER_ID:
            inline_keyboard.append([{"text": f" Owner: {adm}", "callback_data": "none", "style": "primary", "icon_custom_emoji_id": "5353032893096567467"}])
        else:
            inline_keyboard.append([{"text": f" Delete: {adm}", "callback_data": f"adm_admin_del:{adm}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    
    inline_keyboard.append([{"text": " Add Admin", "callback_data": "adm_admin_add", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    text = f"{get_pemoji('user', '👤')} <b>ADMIN MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\nManage your bot admins below:"
    if message_id:
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})
    else:
        send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_system_menu(chat_id, message_id):
    text = (
        f"<tg-emoji emoji-id='5420155432272438703'>⚙️</tg-emoji> <b>SYSTEM CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select an option to manage the core systems:"
    )
    inline_keyboard = [
        [
            {"text": " Panel Management", "callback_data": "adm_panel_mgmt_menu", "style": "primary", "icon_custom_emoji_id": "5420155432272438703"}
        ],
        [{"text": " Manage Otp Group", "callback_data": "adm_otp_grp_menu", "style": "primary", "icon_custom_emoji_id": "5420145051336485498"}],
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_otp_grp_menu(chat_id, message_id):
    link = admin_db.get("otp_group_link", "")
    fwd_groups = admin_db.get("forward_groups", [])
    
    text = f"{get_pemoji('gear', '⚙️')} <b>OTP GROUP MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    text += f"<b>User Button Link:</b>\n<code>{escape_html(link) if link else 'Not Set'}</code>\n\n"
    text += f"<b>Forward Groups ({len(fwd_groups)}):</b>\n"
    
    inline_keyboard = [
        [{"text": " Edit User Button Link", "callback_data": "adm_otp_edit_link", "style": "primary", "icon_custom_emoji_id": "5395444784611480792"}]
    ]
    
    for idx, grp in enumerate(fwd_groups):
        g_id = grp.get("id")
        btns = len(grp.get("buttons", []))
        inline_keyboard.append([{"text": f" FWD: {g_id} ({btns} Btns)", "callback_data": f"adm_fwd_view:{idx}", "style": "success", "icon_custom_emoji_id": "5789428375261023681"}])
        
    inline_keyboard.append([{"text": " Add Forward Group", "callback_data": "adm_fwd_add", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back to System", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_fwd_view(chat_id, message_id, idx):
    fwd_groups = admin_db.get("forward_groups", [])
    if idx >= len(fwd_groups): return
    grp = fwd_groups[idx]
    g_id = grp.get("id")
    btns = grp.get("buttons", [])
    
    text = f"{get_pemoji('gear', '⚙️')} <b>FORWARD GROUP: {g_id}</b>\n━━━━━━━━━━━━━━━━━━\nManage inline buttons for this forward group:\n"
    
    inline_keyboard = []
    for b_idx, btn in enumerate(btns):
        inline_keyboard.append([{"text": f"❌ {btn['text']} - {btn['url'][:15]}...", "callback_data": f"adm_fwd_btn_del:{idx}:{b_idx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
        
    inline_keyboard.append([{"text": " Add Inline Button", "callback_data": f"adm_fwd_btn_add:{idx}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Remove Forward Group", "callback_data": f"adm_fwd_del:{idx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_firebase_menu(chat_id, message_id):
    status = "✅ Connected" if db_firestore else "❌ Not Connected"
    
    text = (
        f"<tg-emoji emoji-id='5337267511261960341'>🔥</tg-emoji> <b>FIREBASE CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Auto-Sync:</b> Every 5 Minutes 🔄\n\n"
        "<i>Syncs: User Balances, Panels, Services & Config.</i>"
    )
    inline_keyboard = [
        [
            {"text": " Force Sync Database", "callback_data": "adm_fb_sync_users", "style": "success", "icon_custom_emoji_id": "5465368548702446780"}
        ],
        [{"text": " Back to System", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_panel_mgmt_menu(chat_id, message_id):
    text = (
        f"{get_pemoji('gear', '⚙️')} <b>PANEL MANAGEMENT</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Configure your API panels and traffic filters:"
    )
    inline_keyboard = [
        [
            {"text": " Manage Panel", "callback_data": "adm_pnl_home", "style": "primary", "icon_custom_emoji_id": "5366231924597604153"},
            {"text": " Manage Traffic", "callback_data": "adm_trf_home", "style": "success", "icon_custom_emoji_id": "5352877703043258544"}
        ],
        [
            {"text": " Manage Service", "callback_data": "adm_svc_home", "style": "success", "icon_custom_emoji_id": "5366231924597604153"}
        ],
        [{"text": " Back to System", "callback_data": "adm_system_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_trf_home(chat_id, message_id):
    text = f"{get_pemoji('dashboard', '📊')} <b>TRAFFIC MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\nSelect a panel to manage its traffic logging:"
    inline_keyboard = []
    
    for p in panels:
        inline_keyboard.append([{"text": f" {p['name']}", "callback_data": f"adm_trf_pnl:{p['id']}", "style": "primary", "icon_custom_emoji_id": "5352877703043258544"}])
        
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_trf_pnl_view(chat_id, message_id, panel_id):
    panel = next((p for p in panels if p["id"] == panel_id), None)
    if not panel: return
    p_name = panel["name"]
    is_active = panel.get("is_traffic_active", True)
    
    status_text = " Traffic Logging: ON" if is_active else " Traffic Logging: OFF"
    status_style = "success" if is_active else "danger"
    status_icon = "5352694861990501856" if is_active else "5420130255174145507"
    
    text = f"{get_pemoji('dashboard', '📊')} <b>TRAFFIC: {p_name}</b>\n━━━━━━━━━━━━━━━━━━\nEnable or disable traffic monitoring for this panel.\n\n<i>If OFF, this panel's logs will not appear in the /traffic menu.</i>"
    inline_keyboard = [
        [{"text": status_text, "callback_data": f"adm_trf_tog_pnl:{panel_id}", "style": status_style, "icon_custom_emoji_id": status_icon}],
        [{"text": " Back to Panels", "callback_data": "adm_trf_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_srch_home(chat_id, message_id):
    text = f"{get_pemoji('search', '🔍')} <b>SEARCH MANAGEMENT</b>\n━━━━━━━━━━━━━━━━━━\nSelect a panel to manage its search routing and allowed country codes:"
    inline_keyboard = []
    for p in panels:
        inline_keyboard.append([{"text": f" {p['name']}", "callback_data": f"adm_srch_pnl:{p['id']}", "style": "primary", "icon_custom_emoji_id": "5463352748751753567"}])
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_srch_pnl_view(chat_id, message_id, panel_id):
    panel = next((p for p in panels if p["id"] == panel_id), None)
    if not panel: return
    p_name = panel["name"]
    
    search_cfg = admin_db.setdefault("search_cfg", {})
    p_cfg = search_cfg.setdefault(panel_id, {"is_active": True, "prefixes": []})
    is_active = p_cfg.get("is_active", True)
    prefixes = p_cfg.get("prefixes", [])
    
    status_text = " Search Status: ON" if is_active else " Search Status: OFF"
    status_style = "success" if is_active else "danger"
    status_icon = "5352694861990501856" if is_active else "5420130255174145507"
    
    text = f"{get_pemoji('search', '🔍')} <b>SEARCH ROUTES: {p_name}</b>\n━━━━━━━━━━━━━━━━━━\nManage allowed country codes for this panel. If a user searches for a number outside these codes, it will be blocked.\n"
    inline_keyboard = [
        [{"text": status_text, "callback_data": f"adm_srch_tog:{panel_id}", "style": status_style, "icon_custom_emoji_id": status_icon}]
    ]
    
    for pfx in prefixes:
        inline_keyboard.append([{"text": f"❌ Prefix: +{pfx}", "callback_data": f"adm_srch_del:{panel_id}:{pfx}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
        
    inline_keyboard.append([{"text": " Add Country Code", "callback_data": f"adm_srch_add:{panel_id}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back to Panels", "callback_data": "adm_srch_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_home(chat_id, message_id):
    text = f"{get_pemoji('gear', '⚙️')} <b>SELECT PANEL</b>\n━━━━━━━━━━━━━━━━━━\nSelect a panel to manage its services:"
    inline_keyboard = []
    
    for p in panels:
        inline_keyboard.append([{"text": f" {p['name']}", "callback_data": f"adm_svc_pnl:{p['id']}", "style": "primary", "icon_custom_emoji_id": "5366231924597604153"}])
        
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_pnl_view(chat_id, message_id, panel_id):
    services_dict = load_services()
    p_services = services_dict.get(panel_id, [])
    
    panel = next((p for p in panels if p["id"] == panel_id), None)
    if not panel: return
    p_name = panel["name"]
    is_active = panel.get("is_active", True)
    
    status_text = " Panel Status: ON" if is_active else " Panel Status: OFF"
    status_style = "success" if is_active else "danger"
    status_icon = "5352694861990501856" if is_active else "5420130255174145507"
    
    text = f"{get_pemoji('gear', '⚙️')} <b>SERVICES: {p_name}</b>\n━━━━━━━━━━━━━━━━━━\nManage services for this panel:"
    inline_keyboard = [
        [{"text": status_text, "callback_data": f"adm_svc_tog_pnl:{panel_id}", "style": status_style, "icon_custom_emoji_id": status_icon}]
    ]
    
    for s in p_services:
        em_id = get_app_raw_id(s['name'])
        inline_keyboard.append([{"text": f" {s['name']} ({len(s.get('countries', []))} Countries)", "callback_data": f"adm_svc_view:{panel_id}:{s['id']}", "style": "primary", "icon_custom_emoji_id": em_id}])
        
    inline_keyboard.append([{"text": " Add New Service", "callback_data": f"adm_svc_add:{panel_id}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Back to Panels", "callback_data": "adm_svc_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_view(chat_id, message_id, panel_id, service_id):
    services_dict = load_services()
    p_services = services_dict.get(panel_id, [])
    service = next((s for s in p_services if s["id"] == service_id), None)
    if not service: return
    
    text = f"{get_pemoji('gear', '⚙️')} <b>SERVICE: {service['name'].upper()}</b>\n━━━━━━━━━━━━━━━━━━\nSelect a country to manage ranges:"
    inline_keyboard = []
    
    for c in service.get("countries", []):
        c_info = get_country_info(c['code'])
        name = c.get("name") or c_info["name"]
        em_id = c_info.get("id", "5336972142066047577")
        inline_keyboard.append([{"text": f" {name} ({c['code']}) - {len(c.get('ranges', []))} Ranges", "callback_data": f"adm_svc_ctr:{panel_id}:{service_id}:{c['code']}", "style": "primary", "icon_custom_emoji_id": em_id}])
        
    inline_keyboard.append([{"text": " Add Country", "callback_data": f"adm_svc_add_ctr:{panel_id}:{service_id}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}])
    inline_keyboard.append([{"text": " Delete Service", "callback_data": f"adm_svc_del:{panel_id}:{service_id}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}])
    inline_keyboard.append([{"text": " Back", "callback_data": f"adm_svc_pnl:{panel_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_svc_ctr_view(chat_id, message_id, panel_id, service_id, country_code):
    services_dict = load_services()
    p_services = services_dict.get(panel_id, [])
    service = next((s for s in p_services if s["id"] == service_id), None)
    if not service: return
    country = next((c for c in service.get("countries", []) if c["code"] == country_code), None)
    if not country: return
    
    c_info = get_country_info(country_code)
    text = f"{get_pemoji('gear', '⚙️')} <b>RANGES: {c_info.get('name', country_code)} ({service['name']})</b>\n━━━━━━━━━━━━━━━━━━\n"
    
    ranges = country.get("ranges", [])
    if not ranges: text += "<i>No ranges added yet.</i>\n"
    for idx, r in enumerate(ranges):
        text += f"{idx+1}. <code>{r}</code>\n"
        
    inline_keyboard = [
        [{"text": " Add Range", "callback_data": f"adm_svc_add_rg:{panel_id}:{service_id}:{country_code}", "style": "success", "icon_custom_emoji_id": "5420323438508155202"}],
        [{"text": " Clear All Ranges", "callback_data": f"adm_svc_clr_rg:{panel_id}:{service_id}:{country_code}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}],
        [{"text": " Remove Country", "callback_data": f"adm_svc_del_ctr:{panel_id}:{service_id}:{country_code}", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}],
        [{"text": " Back", "callback_data": f"adm_svc_view:{panel_id}:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_panel_list(chat_id, message_id):
    text = (
        f"{get_pemoji('gear', '⚙️')} <b>PANEL SELECTION</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Select a panel to configure its API/Login settings:"
    )
    
    # আলাদা আলাদা প্যানেলের জন্য আলাদা আলাদা প্রিমিয়াম ইমোজি আইডি
    panel_emojis = {
        "stexsms": "5336972142066047577", # Chrome
        "xmint": "5336879280578138635",   # Gem
        "mk": "5352552689983067014",      # Proton VPN
        "nexa": "5352838545826420397"     # Express VPN
    }
    
    inline_keyboard = []
    row = []
    for idx, p in enumerate(panels):
        btn_text = f" {p['name']}"
        emoji_id = panel_emojis.get(p.get('id', 'stexsms'), "5366231924597604153") # Default
        
        row.append({"text": btn_text, "callback_data": f"adm_pnl_view:{idx}", "style": "primary", "icon_custom_emoji_id": emoji_id})
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)
        
    inline_keyboard.append([{"text": " Back", "callback_data": "adm_panel_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_panel_details(chat_id, message_id, p_idx):
    if p_idx >= len(panels):
        edit_bot_message(chat_id, message_id, f"{get_pemoji('error', '❌')} Panel not found.", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_pnl_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return
    panel = panels[p_idx]
    
    status = panel.get('status', 'Unknown')
    status_icon = get_pemoji("done", "✅") if "LoggedIn" in status or "API" in status else get_pemoji("error", "❌")
    
    baseUrl = normalize_base_url(panel.get("url", ""))
    clean_base = baseUrl.split('#')[0].rstrip('/')
    
    gn_url = panel.get('getNumberUrl') or f"{clean_base}/mapi/v1/mdashboard/getnum/number"
    gm_url = panel.get('getMessageUrl') or f"{clean_base}/mapi/v1/mdashboard/getnum/info"
    tr_url = panel.get('trafficUrl') or f"{clean_base}/mapi/v1/mdashboard/console/info"

    api_key = panel.get('password', 'MKJGS2MSZYB')
    text = (
        f"<tg-emoji emoji-id='5420155432272438703'>⚙️</tg-emoji> <b>API CONFIGURATION</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5353032893096567467'>👑</tg-emoji> <b>Name:</b> {panel['name']}\n"
        f"<tg-emoji emoji-id='5337267511261960341'>🔥</tg-emoji> <b>Status:</b> <code>{status}</code> {status_icon}\n\n"
        f"<tg-emoji emoji-id='5336972142066047577'>🌐</tg-emoji> <b>1. Base API URL:</b>\n<code>{panel.get('url', '')}</code>\n\n"
        f"<tg-emoji emoji-id='5337255927735163754'>🔐</tg-emoji> <b>2. API Key (Token):</b>\n<code>{api_key}</code>\n\n"
        f"<tg-emoji emoji-id='5352862640592949843'>🔢</tg-emoji> <b>3. Get Number API:</b>\n<code>{gn_url}</code>\n\n"
        f"<tg-emoji emoji-id='5337302974806922068'>💬</tg-emoji> <b>4. Get Message API:</b>\n<code>{gm_url}</code>\n\n"
        f"<tg-emoji emoji-id='5352877703043258544'>📊</tg-emoji> <b>5. Traffic API:</b>\n<code>{tr_url}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<tg-emoji emoji-id='5192739271886282680'>📝</tg-emoji> <i>Edit system configuration:</i>"
    )
    inline_keyboard = [
        [
            {"text": " Edit Base URL", "callback_data": f"adm_pnl_edit:{p_idx}:url", "style": "primary", "icon_custom_emoji_id": "5336972142066047577"},
            {"text": " Edit API Key", "callback_data": f"adm_pnl_edit:{p_idx}:pass", "style": "success", "icon_custom_emoji_id": "5337255927735163754"}
        ],
        [
            {"text": " Edit GetNum URL", "callback_data": f"adm_pnl_edit:{p_idx}:getnum", "style": "primary", "icon_custom_emoji_id": "5337132498965010628"},
            {"text": " Edit GetMsg URL", "callback_data": f"adm_pnl_edit:{p_idx}:getmsg", "style": "primary", "icon_custom_emoji_id": "5395444784611480792"}
        ],
        [
            {"text": " Edit Traffic URL", "callback_data": f"adm_pnl_edit:{p_idx}:traffic", "style": "primary", "icon_custom_emoji_id": "5352877703043258544"}
        ],
        [{"text": " Back", "callback_data": "adm_pnl_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_admin_dxa_menu(chat_id, message_id):
    cfg = admin_db.get("dxa_config", {})
    w_grp = cfg.get("withdraw_group", "")
    rew = cfg.get("otp_reward", 0.0)
    m_wd = cfg.get("min_withdraw", 20.0)
    mth = cfg.get("methods", [])
    max_c = cfg.get("max_concurrent", 3)
    cd = cfg.get("cooldown", 0)
    
    text = f"{get_pemoji('gem', '💎')} <b>MANAGE DXA (Withdrawal System)</b>\n━━━━━━━━━━━━━━━━━━\n"
    text += f"{get_pemoji('dashboard', '📊')} <b>Withdraw Group:</b> <code>{escape_html(w_grp) if w_grp else 'Not Set'}</code>\n"
    text += f"{get_pemoji('fire', '🔥')} <b>OTP Reward:</b> <code>{rew} ৳</code>\n"
    text += f"{get_pemoji('otp', '🔐')} <b>Min Withdraw:</b> <code>{m_wd} ৳</code>\n"
    text += f"{get_pemoji('user', '👤')} <b>Max Numbers/User:</b> <code>{max_c}</code>\n"
    text += f"{get_pemoji('time', '🕓')} <b>Cooldown:</b> <code>{cd} sec</code>\n"
    text += f"{get_pemoji('note', '📝')} <b>Methods ({len(mth)}):</b> {', '.join(mth) if mth else 'None'}\n"
    
    inline_keyboard = [
        [{"text": " Set Withdraw Group", "callback_data": "adm_dxa_grp", "style": "primary", "icon_custom_emoji_id": "5395444784611480792"}],
        [
            {"text": " OTP Reward", "callback_data": "adm_dxa_rew", "style": "primary", "icon_custom_emoji_id": "5352838545826420397"},
            {"text": " Min Withdraw", "callback_data": "adm_dxa_min", "style": "primary", "icon_custom_emoji_id": "5352862640592949843"}
        ],
        [
            {"text": " Max Numbers", "callback_data": "adm_dxa_maxc", "style": "primary", "icon_custom_emoji_id": "5352861489541714456"},
            {"text": " Cooldown", "callback_data": "adm_dxa_cd", "style": "primary", "icon_custom_emoji_id": "5336983442125001376"}
        ],
        [
            {"text": " Add Method", "callback_data": "adm_dxa_mth_add", "style": "success", "icon_custom_emoji_id": "5420323438508155202"},
            {"text": " Clear Methods", "callback_data": "adm_dxa_mth_clr", "style": "danger", "icon_custom_emoji_id": "5422557736330106570"}
        ],
        [{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
    ]
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def render_user_balance(chat_id, message_id=None):
    stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
    cfg = admin_db.get("dxa_config", {})
    min_wd = cfg.get("min_withdraw", 20.0)
    methods = cfg.get("methods", [])
    
    text = f"━━━━━━━━━━━━\n"
    text += f"《 {get_pemoji('dxa', '😒')} <b>Profile</b> 》\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('done', '👋')} <b>Total Otp:</b> {stats.get('otp_count', 0)}\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('user', '👤')} <b>User Id:</b> <code>{chat_id}</code>\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('gem', '📅')} <b>BALANCE:</b> {stats.get('balance', 0.0)} ৳\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"{get_pemoji('otp', '🔐')} <b>MINIMUM:</b> {min_wd} ৳\n"
    text += f"━━━━━━━━━━━━\n"
    text += f"<b>SELECT METHOD:</b>"
    
    inline_keyboard = []
    row = []
    for m in methods:
        row.append({"text": f" {m}", "callback_data": f"usr_wd_{m}", "style": "success", "icon_custom_emoji_id": "5352585194295564660"})
        if len(row) == 2:
            inline_keyboard.append(row)
            row = []
    if row:
        inline_keyboard.append(row)
        
    if message_id:
        edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard} if inline_keyboard else None)
    else:
        send_bot_message(chat_id, text, {"inline_keyboard": inline_keyboard} if inline_keyboard else None)

def get_bot_menu_keyboard(chat_id):
    keyboard = [
        [
            {"text": "GET NUMBER", "style": "primary", "icon_custom_emoji_id": "5337132498965010628"}, 
            {"text": "SEARCH RANGE", "style": "success", "icon_custom_emoji_id": "5463352748751753567"}
        ],
        [
            {"text": "TRAFFIC", "style": "primary", "icon_custom_emoji_id": "5352877703043258544"},
            {"text": "BALANCE", "style": "success", "icon_custom_emoji_id": "5352838545826420397"}
        ],
        [
            {"text": "2FA SETUP", "style": "primary", "icon_custom_emoji_id": "5337255927735163754"}
        ]
    ]
    
    if str(chat_id) in admin_db.get("admins", [OWNER_ID]):
        keyboard.append([{"text": "ADMIN PANEL", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"}])
        
    return {"keyboard": keyboard, "resize_keyboard": True}

# ----------------------------------------------------
# Service selections UI layouts
# ----------------------------------------------------

def render_services_list(chat_id, message_id=None):
    services_dict = load_services()
    merged_services = {}
    
    active_panel_ids = [p["id"] for p in panels if p.get("is_active", True)]
    
    for p_id, s_list in services_dict.items():
        if p_id not in active_panel_ids: continue
        for s in s_list:
            if s["id"] not in merged_services:
                merged_services[s["id"]] = {"id": s["id"], "name": s["name"]}
                
    text = f"{get_pemoji('phone', '📱')} <b>Select a service:</b>"
    
    inline_keyboard = []
    if not merged_services:
        inline_keyboard.append([{"text": " No Services Available", "callback_data": "none", "style": "danger", "icon_custom_emoji_id": "5336944168944047463"}])
    else:
        for s_id, s_data in merged_services.items():
            em_id = get_app_raw_id(s_data['name'])
            inline_keyboard.append([{"text": f" {s_data['name']}", "callback_data": f"usr_srv_sel:{s_id}", "style": "primary", "icon_custom_emoji_id": em_id}])

    keyboard = {"inline_keyboard": inline_keyboard}
    if message_id:
        edit_bot_message(chat_id, message_id, text, keyboard)
    else:
        send_bot_message(chat_id, text, keyboard)

def render_countries_list(chat_id, message_id, service_id):
    services_dict = load_services()
    merged_countries = {}
    service_name = "Unknown"
    
    active_panel_ids = [p["id"] for p in panels if p.get("is_active", True)]
    
    for p_id, s_list in services_dict.items():
        if p_id not in active_panel_ids: continue
        for s in s_list:
            if s["id"] == service_id:
                service_name = s["name"]
                for c in s.get("countries", []):
                    if len(c.get("ranges", [])) > 0:
                        merged_countries[c["code"]] = c

    if not merged_countries:
        edit_bot_message(chat_id, message_id, f"{get_pemoji('error', '❌')} No countries are currently configured for <b>{escape_html(service_name)}</b>.", {
            "inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]
        })
        return

    text = f"{get_pemoji('phone', '📱')} <b>Select a country for {service_name.upper()}:</b>"
    inline_keyboard = []
    
    for code, c in merged_countries.items():
        c_info = get_country_info(code)
        name = c.get("name") or c_info["name"]
        em_id = c_info.get("id", "5336972142066047577")
        inline_keyboard.append([
            {"text": f" {name} ({code})", "callback_data": f"usr_ctr_sel:{service_id}:{code}", "style": "primary", "icon_custom_emoji_id": em_id}
        ])
        
    inline_keyboard.append([{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}])
    edit_bot_message(chat_id, message_id, text, {"inline_keyboard": inline_keyboard})

def allocate_and_show_number_py(chat_id, message_id, service_id, country_code, callback_id=None):
    passed, err_msg, batch_size = check_user_limits(chat_id)
    if not passed:
        if callback_id:
            answer_callback(callback_id, err_msg, show_alert=True)
        else:
            kb = {"inline_keyboard": [[{"text": " Back", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
            edit_bot_message(chat_id, message_id, f"⚠️ {err_msg}", kb)
        return

    if callback_id:
        answer_callback(callback_id, "Allocating number...")

    services_dict = load_services()
    available_panels = []
    service_name = "Unknown"
    
    active_panel_ids = [p["id"] for p in panels if p.get("is_active", True)]
    
    for p_id, s_list in services_dict.items():
        if p_id not in active_panel_ids: continue
        for s in s_list:
            if s["id"] == service_id:
                service_name = s["name"]
                for c in s.get("countries", []):
                    if c["code"] == country_code and len(c.get("ranges", [])) > 0:
                        available_panels.append({"panel_id": p_id, "ranges": c["ranges"]})
                        
    if not available_panels:
        edit_bot_message(chat_id, message_id, f"{get_pemoji('error', '❌')} No ranges configured for this selection.", {
            "inline_keyboard": [[{"text": " Back", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]
        })
        return

    chosen_setup = random.choice(available_panels)
    panel_id = chosen_setup["panel_id"]
    range_val = random.choice(chosen_setup["ranges"]).strip().upper()
    
    if not any(c in range_val for c in ("X", "x", "*")) and range_val.isdigit():
        range_val += "XXX"
        
    wait_emoji = get_pemoji("wait", "⏳")
    edit_bot_message(chat_id, message_id, f"{wait_emoji} <i>Allocating {batch_size} number(s) for <b>{escape_html(service_name)}</b>... Please wait.</i>")
    
    numbers_fetched = []
    last_err = "Unknown error"
    if "active_numbers" not in admin_db: admin_db["active_numbers"] = {}
    
    for _ in range(batch_size):
        result = buy_number(range_val, panel_id)
        if result.get("success"):
            numbers_fetched.append(result)
            number_val = result.get("number") or ""
            clean_num = str(number_val).replace("+", "").strip()
            admin_db["active_numbers"][clean_num] = str(chat_id)
        else:
            last_err = result.get("message", "Failed to retrieve.")
            break
            
    if numbers_fetched:
        save_admin_db()
        blank_text = "ㅤ"
        svc_em_id = get_app_raw_id(service_name)
        
        inline_keyboard = [
            [{"text": f" {service_name}", "callback_data": "none", "style": "success", "icon_custom_emoji_id": svc_em_id}]
        ]
        
        for res in numbers_fetched:
            num = res.get("number", "")
            actual_c_code = get_country_code(num)
            c_info_actual = get_country_info(actual_c_code)
            actual_flag_em_id = c_info_actual.get("id", "5336972142066047577")
            
            inline_keyboard.append([{
                "text": f" +{num.replace('+', '')}",
                "copy_text": {"text": f"{num}"},
                "style": "primary",
                "icon_custom_emoji_id": actual_flag_em_id
            }])
            
        inline_keyboard.extend([
            [
                {"text": " Change Number", "callback_data": f"usr_change_num:{service_id}:{country_code}", "style": "danger", "icon_custom_emoji_id": "5420155432272438703"},
                get_otp_group_btn()
            ],
            [{"text": " Back", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
        ])
        edit_bot_message(chat_id, message_id, blank_text, {"inline_keyboard": inline_keyboard})
    else:
        failure_text = f"{get_pemoji('error', '❌')} <b>Get Number Failed!</b>\n\n" \
                       f"<b>Service:</b> {escape_html(service_name)}\n" \
                       f"<b>Country:</b> {escape_html(country_code)}\n" \
                       f"<b>Range tried:</b> <code>{escape_html(range_val)}</code>\n" \
                       f"<b>Error:</b> <code>{escape_html(last_err)}</code>\n\n" \
                       f"<i>Please try again.</i>"
        
        inline_keyboard = [
            [
                {"text": " Retry Allocating", "callback_data": f"usr_change_num:{service_id}:{country_code}", "style": "success", "icon_custom_emoji_id": "5465368548702446780"},
                {"text": " Back to Countries", "callback_data": f"usr_srv_sel:{service_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}
            ]
        ]
        edit_bot_message(chat_id, message_id, failure_text, {"inline_keyboard": inline_keyboard})

# ----------------------------------------------------
# Telegram Bot Inbound Controllers
# ----------------------------------------------------

def handle_callback_query(callback_query):
    callback_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    message_id = callback_query.get("message", {}).get("message_id")
    data = callback_query.get("data", "")
    
    if not chat_id or not message_id:
        answer_callback(callback_id)
        return

    # 🚫 Check Ban Status
    if str(chat_id) in admin_db.get("banned_users", []):
        answer_callback(callback_id, "🚫 You are banned from using this bot.", show_alert=True)
        return

    # 🔄 গ্লোবাল স্টেট রিসেট: যেকোনো ব্যাক বা হোম বাটনে ক্লিক করলে আগের পেন্ডিং ইনপুট মুছে যাবে
    if data in ["usr_menu_home", "adm_main_menu", "adm_admin_menu", "adm_fj_menu", "adm_system_menu", "adm_firebase_menu", "adm_svc_home", "adm_panel_mgmt_menu", "adm_trf_home", "adm_srch_home"]:
        user_conversations.pop(chat_id, None)
        
    if data.startswith("adm_svc_view:") or data.startswith("adm_svc_ctr:"):
        user_conversations.pop(chat_id, None)

    logger.info(f"Bot Callback Triggered: data='{data}'")

    if data == "usr_menu_home":
        answer_callback(callback_id)
        render_services_list(chat_id, message_id)
        
    elif data == "usr_search_home":
        user_conversations.pop(chat_id, None) # আগের স্টেট ক্লিয়ার
        answer_callback(callback_id, "Opening Search Menu...")
        user_conversations[chat_id] = "waiting_for_search"
        text_help = (
            "╔═══════════╗\n"
            f"     {get_pemoji('search', '🔍')} <b>SEARCH RANGE</b>\n"
            "╚═══════════╝\n"
            f"{get_pemoji('done', '📌')} Enter 3 to 11 digits  \n"
            "to search for a number.\n"
            "━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5395444784611480792'>📝</tg-emoji> Example:\n"
            "➥ 880\n"
            "➥ 9227373\n"
            "━━━━━━━━━━━━━\n"
            f"{get_pemoji('search', '🔍')} Fast Number Lookup System"
        )
        edit_bot_message(chat_id, message_id, text_help, {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        
    elif data.startswith("usr_srv_sel:"):
        service_id = data.split(":")[1]
        answer_callback(callback_id, "Loading countries...")
        render_countries_list(chat_id, message_id, service_id)
        
    elif data.startswith("usr_ctr_sel:"):
        parts = data.split(":")
        service_id = parts[1]
        country_code = parts[2]
        allocate_and_show_number_py(chat_id, message_id, service_id, country_code, callback_id)
        
    elif data.startswith("usr_change_num:"):
        parts = data.split(":")
        service_id = parts[1]
        country_code = parts[2]
        allocate_and_show_number_py(chat_id, message_id, service_id, country_code, callback_id)
        
    elif data.startswith("buy_"):
        range_val = data.split("_")[1]
        trigger_buy_number(chat_id, range_val, message_id=message_id, callback_id=callback_id)

    elif data == "usr_otp_grp":
        # চ্যাটে মেসেজ পাঠানোর অংশটি ডিলিট করা হয়েছে। এখন লিংক না থাকলে শুধু ছোট্ট পপ-আপ দেখাবে।
        answer_callback(callback_id, "OTP Group link is not set by admin yet!", show_alert=True)

    elif data == "tr_refresh":
         answer_callback(callback_id, "Refreshing traffic dashboard...")
         render_traffic_home(chat_id, message_id)

    elif data == "tr_close":
         answer_callback(callback_id, "Closed")
         call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    elif data == "cancel_2fa":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Canceled")
         call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
         
    elif data.startswith("refresh_2fa:"):
         secret = data.split(":")[1]
         code = get_totp_token(secret)
         if code:
             answer_callback(callback_id, f"Refreshed: {code}")
             msg_text = (
                 f"╔═══════════╗\n"
                 f"     {get_pemoji('otp', '🔐')} <b>2FA CODE GENERATED</b>\n"
                 f"╚═══════════╝\n"
                 f"<b>Secret:</b> <code>{secret}</code>\n"
                 f"━━━━━━━━━━━━━\n"
                 f"{get_pemoji('done', '✅')} <b>Code:</b> <code>{code}</code>\n"
                 f"<i>(This code is valid for 30 seconds)</i>"
             )
             kb = {"inline_keyboard": [
                 [{"text": " Refresh Code", "callback_data": f"refresh_2fa:{secret}", "style": "success", "icon_custom_emoji_id": "5465368548702446780"}],
                 [{"text": " Close", "callback_data": "cancel_2fa", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
             ]}
             edit_bot_message(chat_id, message_id, msg_text, kb)
         else:
             answer_callback(callback_id, "Error generating code", show_alert=True)

    elif data == "adm_coming_soon":
         answer_callback(callback_id, "🚧 This feature is coming soon!")

    elif data == "adm_user_mgmt_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Opening User Management...")
         render_admin_user_mgmt_menu(chat_id, message_id)

    elif data in ["adm_um_prof", "adm_um_bal", "adm_um_ban"]:
         action_map = {"adm_um_prof": "Profile", "adm_um_bal": "Balance", "adm_um_ban": "Ban/Unban"}
         action_type = data.split("_")[2]
         answer_callback(callback_id, "Send User ID...")
         user_conversations[chat_id] = f"um_wait_id_{action_type}"
         user_prompts[chat_id] = message_id
         text = f"<tg-emoji emoji-id='5463352748751753567'>🔍</tg-emoji> <b>Search User for {action_map[data]}</b>\n\nPlease send the Telegram User ID (e.g., <code>123456789</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_user_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_um_view_prof:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id)
         render_um_profile(chat_id, message_id, target_uid)

    elif data.startswith("adm_um_view_bal:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id)
         render_um_balance(chat_id, message_id, target_uid)

    elif data.startswith("adm_um_view_ban:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id)
         render_um_ban(chat_id, message_id, target_uid)

    elif data.startswith("adm_bal_add:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id, "Send Amount...")
         user_conversations[chat_id] = f"um_wait_amt_add_{target_uid}"
         user_prompts[chat_id] = message_id
         text = f"<tg-emoji emoji-id='5420323438508155202'>➕</tg-emoji> <b>Add Balance</b>\n\nUser ID: <code>{target_uid}</code>\nSend the amount to add (e.g., <code>50</code>):"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_bal_sub:"):
         target_uid = data.split(":")[1]
         answer_callback(callback_id, "Send Amount...")
         user_conversations[chat_id] = f"um_wait_amt_sub_{target_uid}"
         user_prompts[chat_id] = message_id
         text = f"<tg-emoji emoji-id='5422557736330106570'>➖</tg-emoji> <b>Deduct Balance</b>\n\nUser ID: <code>{target_uid}</code>\nSend the amount to deduct (e.g., <code>50</code>):"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_ban_tog:"):
         target_uid = data.split(":")[1]
         banned_list = admin_db.setdefault("banned_users", [])
         if target_uid in banned_list:
             banned_list.remove(target_uid)
             answer_callback(callback_id, "User Unbanned!")
         else:
             banned_list.append(target_uid)
             answer_callback(callback_id, "User Banned!")
         save_admin_db()
         render_um_ban(chat_id, message_id, target_uid)

    elif data == "check_fj":
         answer_callback(callback_id, "Checking Force Join...")
         if check_force_join(chat_id, message_id):
             call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
             send_bot_message(chat_id, "✅ <b>Verification Successful!</b>\nWelcome to DXA Bot.", get_bot_menu_keyboard(chat_id))

    elif data == "adm_fj_menu":
         user_conversations.pop(chat_id, None) # 🛠️ চ্যানেল লিংক দেওয়ার স্টেট ক্লিয়ার করা হলো
         answer_callback(callback_id, "Opening Force Join Menu...")
         render_force_join_menu(chat_id, message_id)

    elif data == "adm_fj_toggle":
         answer_callback(callback_id, "Toggling status...")
         admin_db["force_join_status"] = not admin_db.get("force_join_status", False)
         save_admin_db()
         render_force_join_menu(chat_id, message_id)

    elif data.startswith("adm_fj_del:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id, "Deleting channel...")
         channels = admin_db.get("force_join_channels", [])
         if 0 <= idx < len(channels):
             channels.pop(idx)
             save_admin_db()
             threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
         render_force_join_menu(chat_id, message_id)

    elif data == "adm_fj_add":
         answer_callback(callback_id, "Send Channel Link...")
         user_conversations[chat_id] = "waiting_fj_channel"
         text = "🔗 <b>Add Force Join Channel</b>\n\nPlease send the channel username (e.g., <code>@dxa_admin</code>) or an invite link."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_fj_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_admin_menu":
         user_conversations.pop(chat_id, None) # 🛠️ আইডি দেওয়ার স্টেট ক্লিয়ার করা হলো
         answer_callback(callback_id, "Opening Admin Management...")
         render_admin_management_menu(chat_id, message_id)

    elif data.startswith("adm_admin_del:"):
         adm_id = data.split(":")[1]
         answer_callback(callback_id, "Deleting admin...")
         admins = admin_db.get("admins", [OWNER_ID])
         if adm_id in admins and adm_id != OWNER_ID:
             admins.remove(adm_id)
             save_admin_db()
             threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
         render_admin_management_menu(chat_id, message_id)

    elif data == "adm_admin_add":
         answer_callback(callback_id, "Send Admin ID...")
         user_conversations[chat_id] = "waiting_admin_id"
         text = "👤 <b>Add New Admin</b>\n\nPlease send the Telegram User ID of the new admin (e.g., <code>123456789</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_admin_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_broadcast":
         answer_callback(callback_id, "Ready for broadcast")
         user_conversations[chat_id] = "waiting_for_broadcast"
         text = f"<tg-emoji emoji-id='5789428375261023681'>📢</tg-emoji> <b>BROADCAST SYSTEM</b>\n\nPlease send the message (Text, Photo, Video, Audio, Document, etc.) you want to broadcast to all users."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_main_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_main_menu":
         answer_callback(callback_id, "Returning to Admin Panel...")
         render_admin_panel(chat_id, message_id)

    elif data == "adm_developer":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Loading Developer Info...")
         render_admin_developer(chat_id, message_id)

    elif data == "adm_system_menu":
         answer_callback(callback_id, "Opening System Menu...")
         render_admin_system_menu(chat_id, message_id)

    elif data == "adm_panel_mgmt_menu":
         answer_callback(callback_id, "Opening Panel Management...")
         render_admin_panel_mgmt_menu(chat_id, message_id)

    elif data == "adm_trf_home":
         answer_callback(callback_id, "Opening Traffic Management...")
         render_admin_trf_home(chat_id, message_id)

    elif data.startswith("adm_trf_pnl:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id)
         render_admin_trf_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_trf_tog_pnl:"):
         pnl_id = data.split(":")[1]
         for p in panels:
             if p["id"] == pnl_id:
                 p["is_traffic_active"] = not p.get("is_traffic_active", True)
                 save_panels_to_file(panels)
                 break
         answer_callback(callback_id, "Toggled Traffic Status!")
         render_admin_trf_pnl_view(chat_id, message_id, pnl_id)

    elif data == "adm_srch_home":
         answer_callback(callback_id)
         render_admin_srch_home(chat_id, message_id)

    elif data.startswith("adm_srch_pnl:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id)
         render_admin_srch_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_srch_tog:"):
         pnl_id = data.split(":")[1]
         search_cfg = admin_db.setdefault("search_cfg", {})
         p_cfg = search_cfg.setdefault(pnl_id, {"is_active": True, "prefixes": []})
         p_cfg["is_active"] = not p_cfg.get("is_active", True)
         save_admin_db()
         answer_callback(callback_id, "Toggled Search Status!")
         render_admin_srch_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_srch_add:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id, "Send Country Code...")
         user_conversations[chat_id] = f"add_srch_pfx:{pnl_id}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('world', '🌐')} <b>Add Country Code</b>\n\nSend the calling code (e.g., <code>880</code>, <code>92</code>) to allow searching for this panel."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_srch_pnl:{pnl_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_srch_del:"):
         parts = data.split(":")
         pnl_id = parts[1]
         pfx = parts[2]
         search_cfg = admin_db.setdefault("search_cfg", {})
         if pnl_id in search_cfg and pfx in search_cfg[pnl_id].get("prefixes", []):
             search_cfg[pnl_id]["prefixes"].remove(pfx)
             save_admin_db()
         answer_callback(callback_id, "Deleted Prefix!")
         render_admin_srch_pnl_view(chat_id, message_id, pnl_id)

    elif data in ["adm_wd_app", "adm_wd_rej"]:
         user_id = callback_query.get("from", {}).get("id")
         
         # 🔒 সিকিউরিটি: শুধুমাত্র অ্যাডমিন ক্লিক করতে পারবে
         if str(user_id) not in admin_db.get("admins", [OWNER_ID]):
             answer_callback(callback_id, "❌ Only Admins can process withdrawals!", show_alert=True)
             return
             
         msg_text = callback_query.get("message", {}).get("text", "")
         
         u_match = re.search(r"User:\s*(\d+)", msg_text)
         m_match = re.search(r"Method:\s*(.+)", msg_text)
         a_match = re.search(r"Account:\s*([\d\+\w]+)", msg_text)
         amt_match = re.search(r"Amount:\s*([\d\.]+)", msg_text)
         
         if not (u_match and a_match and amt_match):
             answer_callback(callback_id, "❌ Error parsing request data!", show_alert=True)
             return
             
         u_id = u_match.group(1)
         meth = m_match.group(1).strip() if m_match else "Unknown"
         acc_num = a_match.group(1)
         amt = amt_match.group(1)
         
         masked_acc = mask_number(acc_num)
         
         if data == "adm_wd_app":
             status_text = f"APPROVED {get_pemoji('done', '✅')}"
             new_msg = (
                 f"╔═══════════════╗\n"
                 f"║ {get_pemoji('gem', '💎')} <b>WITHDRAWAL {status_text}</b>\n"
                 f"╚═══════════════╝\n\n"
                 f"{get_pemoji('user', '👤')} <b>User:</b> <code>{u_id}</code>\n"
                 f"{get_pemoji('dashboard', '💳')} <b>Method:</b> {meth}\n"
                 f"{get_pemoji('phone', '📱')} <b>Account:</b> <code>{masked_acc}</code>\n"
                 f"{get_pemoji('fire', '💰')} <b>Amount:</b> <b>{amt} ৳</b>\n"
                 f"━━━━━━━━━━━━"
             )
             edit_bot_message(chat_id, message_id, new_msg)
             send_bot_message(u_id, f"{get_pemoji('done', '✅')} <b>Withdrawal Approved!</b>\nYour request for {amt} ৳ via {meth} has been processed.")
             answer_callback(callback_id, "Approved!")
         else:
             status_text = f"REJECTED {get_pemoji('error', '❌')}"
             new_msg = (
                 f"╔═══════════════╗\n"
                 f"║ {get_pemoji('gem', '💎')} <b>WITHDRAWAL {status_text}</b>\n"
                 f"╚═══════════════╝\n\n"
                 f"{get_pemoji('user', '👤')} <b>User:</b> <code>{u_id}</code>\n"
                 f"{get_pemoji('dashboard', '💳')} <b>Method:</b> {meth}\n"
                 f"{get_pemoji('phone', '📱')} <b>Account:</b> <code>{masked_acc}</code>\n"
                 f"{get_pemoji('fire', '💰')} <b>Amount:</b> <b>{amt} ৳</b>\n"
                 f"━━━━━━━━━━━━"
             )
             edit_bot_message(chat_id, message_id, new_msg)
             
             stats = admin_db.setdefault("user_stats", {}).setdefault(u_id, {})
             stats["balance"] = stats.get("balance", 0.0) + float(amt)
             save_admin_db()
             
             send_bot_message(u_id, f"❌ <b>Withdrawal Rejected!</b>\nYour request for {amt} ৳ was declined. The amount has been refunded to your balance.")
             answer_callback(callback_id, "Rejected & Refunded!")

    elif data == "adm_pnl_home":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Loading Panels...")
         render_panel_list(chat_id, message_id)

    elif data.startswith("adm_pnl_view:"):
         user_conversations.pop(chat_id, None)
         p_idx = int(data.split(":")[1])
         answer_callback(callback_id, "Loading Details...")
         render_panel_details(chat_id, message_id, p_idx)

    elif data == "adm_panel_mgmt_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id)
         render_admin_panel_mgmt_menu(chat_id, message_id)

    elif data == "adm_svc_home":
         answer_callback(callback_id)
         render_admin_svc_home(chat_id, message_id)

    elif data.startswith("adm_svc_pnl:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id)
         render_admin_svc_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_svc_tog_pnl:"):
         pnl_id = data.split(":")[1]
         for p in panels:
             if p["id"] == pnl_id:
                 p["is_active"] = not p.get("is_active", True)
                 save_panels_to_file(panels)
                 break
         answer_callback(callback_id, "Toggled Panel Status!")
         render_admin_svc_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_svc_view:"):
         parts = data.split(":")
         answer_callback(callback_id)
         render_admin_svc_view(chat_id, message_id, parts[1], parts[2])

    elif data.startswith("adm_svc_ctr:"):
         parts = data.split(":")
         answer_callback(callback_id)
         render_admin_svc_ctr_view(chat_id, message_id, parts[1], parts[2], parts[3])

    elif data.startswith("adm_svc_add:"):
         pnl_id = data.split(":")[1]
         answer_callback(callback_id, "Send service name...")
         user_conversations[chat_id] = f"add_svc_name:{pnl_id}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Add New Service</b>\n\nSend the exact Name of the service (e.g., <code>Facebook</code>, <code>Netflix</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_svc_pnl:{pnl_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_svc_add_ctr:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         answer_callback(callback_id, "Send country code...")
         user_conversations[chat_id] = f"add_svc_ctr:{pnl_id}:{s_id}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('world', '🌐')} <b>Add Country</b>\n\nSend the short Country Code (e.g., <code>CI</code>, <code>CM</code>, <code>SN</code>)."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_svc_view:{pnl_id}:{s_id}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_svc_add_rg:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         c_code = parts[3]
         answer_callback(callback_id, "Send range...")
         user_conversations[chat_id] = f"add_svc_rg:{pnl_id}:{s_id}:{c_code}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('number', '🔢')} <b>Add Range</b>\n\nSend the number range (e.g., <code>225070</code> or <code>225070XXX</code>).\n<i>(If you forget 'XXX', the bot will add it automatically!)</i>"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_svc_ctr:{pnl_id}:{s_id}:{c_code}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_svc_del_rg:"): # Added for completion if needed
         pass

    elif data.startswith("adm_svc_del:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         answer_callback(callback_id, "Deleted Service")
         services_dict = load_services()
         services_dict[pnl_id] = [s for s in services_dict.get(pnl_id, []) if s['id'] != s_id]
         save_services(services_dict)
         render_admin_svc_pnl_view(chat_id, message_id, pnl_id)

    elif data.startswith("adm_svc_del_ctr:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         c_code = parts[3]
         answer_callback(callback_id, "Deleted Country")
         services_dict = load_services()
         p_services = services_dict.get(pnl_id, [])
         for s in p_services:
             if s['id'] == s_id:
                 s['countries'] = [c for c in s.get('countries', []) if c['code'] != c_code]
                 break
         save_services(services_dict)
         render_admin_svc_view(chat_id, message_id, pnl_id, s_id)

    elif data.startswith("adm_svc_clr_rg:"):
         parts = data.split(":")
         pnl_id = parts[1]
         s_id = parts[2]
         c_code = parts[3]
         answer_callback(callback_id, "Cleared Ranges")
         services_dict = load_services()
         p_services = services_dict.get(pnl_id, [])
         for s in p_services:
             if s['id'] == s_id:
                 for c in s.get('countries', []):
                     if c['code'] == c_code:
                         c['ranges'] = []
                         break
                 break
         save_services(services_dict)
         render_admin_svc_ctr_view(chat_id, message_id, pnl_id, s_id, c_code)

    elif data.startswith("adm_pnl_edit:"):
        parts = data.split(":")
        p_idx = int(parts[1])
        field = parts[2]
        answer_callback(callback_id, f"Editing {field}...")
        user_conversations[chat_id] = f"edit_pnl_{p_idx}_{field}"
        user_prompts[chat_id] = message_id
        
        panel = panels[p_idx] if p_idx < len(panels) else {}
        
        if is_voltx_api(panel) and field == "pass":
            field_name = "API Key (Token)"
        elif is_voltx_api(panel) and field == "url":
            field_name = "Base API URL"
        else:
            names = {"url":"Login Link","user":"Gmail","pass":"Password","getnum":"GetNum URL","getmsg":"GetMsg URL","traffic":"Traffic URL"}
            field_name = names.get(field, field)
        
        panel_name = panel.get("name", "Panel")
        text = f"{get_pemoji('note', '📝')} <b>Editing {field_name} for {panel_name}</b>\n\n" \
               f"Please send the new value/URL to update the system."
        
        edit_bot_message(chat_id, message_id, text, {
            "inline_keyboard": [[{"text": " Back", "callback_data": f"adm_pnl_view:{p_idx}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]
        })

    elif data == "adm_firebase_menu":
         answer_callback(callback_id, "Opening Firebase Control...")
         render_admin_firebase_menu(chat_id, message_id)

    elif data in ["adm_fb_upload", "adm_fb_view", "adm_fb_delete"]:
         answer_callback(callback_id, "Feature disabled. Creds are now fixed in code.")

    elif data == "adm_fb_sync_users":
         answer_callback(callback_id, "Syncing entire database to Firestore...")
         success, msg_text = sync_essential_data_to_firestore()
         status_emoji = "✅" if success else "❌"
         text = f"{status_emoji} <b>FIREBASE SYNC STATUS</b>\n\n{msg_text}"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_firebase_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})

    # adm_prem_flag removed as data is hardcoded

    elif data == "adm_otp_grp_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id)
         render_admin_otp_grp_menu(chat_id, message_id)

    elif data == "adm_otp_edit_link":
         answer_callback(callback_id)
         user_conversations[chat_id] = "edit_otp_link"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Edit OTP Group Link</b>\n\nSend the new URL (e.g., https://t.me/...) for the user 'Otp Group' button."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_fwd_add":
         answer_callback(callback_id)
         user_conversations[chat_id] = "add_fwd_grp"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Add Forward Group</b>\n\nSend the Chat ID (e.g., <code>-100123456789</code>) where OTPs should be forwarded."
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_fwd_view:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id)
         render_admin_fwd_view(chat_id, message_id, idx)

    elif data.startswith("adm_fwd_del:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id, "Deleted Group")
         fwd_groups = admin_db.get("forward_groups", [])
         if 0 <= idx < len(fwd_groups):
             fwd_groups.pop(idx)
             save_admin_db()
         render_admin_otp_grp_menu(chat_id, message_id)

    elif data.startswith("adm_fwd_btn_add:"):
         idx = int(data.split(":")[1])
         answer_callback(callback_id)
         user_conversations[chat_id] = f"add_fwd_btn:{idx}"
         user_prompts[chat_id] = message_id
         text = f"{get_pemoji('note', '📝')} <b>Add Custom Button</b>\n\nSend the button Text and URL separated by a pipe (`|`).\nExample:\n<code>Support|https://t.me/admin</code>"
         edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_fwd_view:{idx}", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("adm_fwd_btn_del:"):
         parts = data.split(":")
         idx = int(parts[1])
         b_idx = int(parts[2])
         answer_callback(callback_id, "Deleted Button")
         fwd_groups = admin_db.get("forward_groups", [])
         if 0 <= idx < len(fwd_groups):
             btns = fwd_groups[idx].get("buttons", [])
             if 0 <= b_idx < len(btns):
                 btns.pop(b_idx)
                 save_admin_db()
         render_admin_fwd_view(chat_id, message_id, idx)

    elif data == "adm_dxa_menu":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id)
         render_admin_dxa_menu(chat_id, message_id)

    elif data == "adm_dxa_grp":
         answer_callback(callback_id, "Send group ID")
         user_conversations[chat_id] = "set_dxa_grp"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('note', '📝')} Send the Group ID for Withdrawal Posts (e.g., <code>-100...</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_rew":
         answer_callback(callback_id, "Send OTP reward")
         user_conversations[chat_id] = "set_dxa_rew"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('fire', '💰')} Send the amount user earns per successful OTP (e.g., <code>0.5</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_min":
         answer_callback(callback_id, "Send Min Withdraw")
         user_conversations[chat_id] = "set_dxa_min"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('otp', '🔐')} Send Minimum Withdraw Amount (e.g., <code>20</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_mth_add":
         answer_callback(callback_id, "Send Method Name")
         user_conversations[chat_id] = "add_dxa_mth"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('dashboard', '🏦')} Send New Withdrawal Method Name (e.g., <code>bKash</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_mth_clr":
         answer_callback(callback_id, "Cleared Methods!")
         if "dxa_config" in admin_db:
             admin_db["dxa_config"]["methods"] = []
             save_admin_db()
         render_admin_dxa_menu(chat_id, message_id)

    elif data == "adm_dxa_maxc":
         answer_callback(callback_id, "Send max numbers per user...")
         user_conversations[chat_id] = "set_dxa_maxc"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('number', '🔢')} Send Max Numbers a user can request at a time (e.g., <code>3</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data == "adm_dxa_cd":
         answer_callback(callback_id, "Send cooldown in seconds...")
         user_conversations[chat_id] = "set_dxa_cd"
         user_prompts[chat_id] = message_id
         edit_bot_message(chat_id, message_id, f"{get_pemoji('wait', '⏳')} Send Cooldown Time in seconds (e.g., <code>30</code>):", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})

    elif data.startswith("usr_wd_"):
         method = data.replace("usr_wd_", "")
         stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
         cfg = admin_db.get("dxa_config", {})
         if stats.get("balance", 0.0) < float(cfg.get("min_withdraw", 20.0)):
             answer_callback(callback_id, f"❌ Minimum withdraw is {cfg.get('min_withdraw', 20.0)} ৳", show_alert=True)
         else:
             answer_callback(callback_id)
             user_conversations[chat_id] = f"wd_wait_amt_{method}"
             user_prompts[chat_id] = message_id
             text = (
                 f"{get_pemoji('gem', '💎')} <b>Withdraw via {method}</b>\n"
                 f"━━━━━━━━━━━━\n\n"
                 f"{get_pemoji('note', '📝')} Please send the <b>Amount</b> you want to withdraw:\n"
                 f"<i>(Available Balance: {stats.get('balance', 0.0)} ৳)</i>"
             )
             edit_bot_message(chat_id, message_id, text, {"inline_keyboard": [[{"text": " Cancel", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
         
    elif data == "adm_main_menu":
         answer_callback(callback_id, "Returning to Admin Panel...")
         render_admin_panel(chat_id, message_id)

    elif data == "adm_developer":
         user_conversations.pop(chat_id, None)
         answer_callback(callback_id, "Loading Developer Info...")
         render_admin_developer(chat_id, message_id)

    elif data.startswith("tr_svc:"):
         service_slug = data.split(":")[1]
         answer_callback(callback_id, f"Loading {service_slug} stats...")
         render_explore_service(chat_id, message_id, service_slug)

    elif data.startswith("tr_ctr:"):
         parts = data.split(":")
         service_slug = parts[1]
         c_code = parts[2]
         answer_callback(callback_id, f"Loading {c_code} ranges...")
         render_explore_ranges(chat_id, message_id, service_slug, c_code)

    else:
        answer_callback(callback_id)

import hmac, base64, struct

def get_totp_token(secret):
    try:
        secret = secret.replace(" ", "").upper()
        secret += "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(secret)
        tm = int(time.time() / 30)
        msg = struct.pack(">Q", tm)
        h = hmac.new(key, msg, "sha1").digest()
        o = h[19] & 15
        token = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
        return f"{token:06d}"
    except Exception:
        return None

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    chat_type = msg["chat"].get("type", "private")
    
    # 🚫 গ্রুপে কোনো মেসেজ বা কমান্ডের উত্তর দেবে না (শুধু বাটন কাজ করবে)
    if chat_type in ["group", "supergroup"]:
        return

    # 🚫 Check Ban Status
    if str(chat_id) in admin_db.get("banned_users", []):
        return

    # Allow text or captions for media support
    text = msg.get("text", "").strip() or msg.get("caption", "").strip()

    # --- BROADCAST HANDLER (Supports All Media Types: Photo, Video, Audio, etc.) ---
    if user_conversations.get(chat_id) == "waiting_for_broadcast":
        user_conversations.pop(chat_id, None)
        users = admin_db.get("users", [])
        if not users:
            send_bot_message(chat_id, "❌ No users found in database to broadcast.", {"inline_keyboard": [[{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
            return
            
        send_bot_message(chat_id, f"⏳ Broadcasting to {len(users)} users. Please wait...")
        success_count = 0
        
        for u in users:
            try:
                # Telegram copyMessage API দিয়ে অরিজিনাল মেসেজ ফরওয়ার্ড (Without forwarded tag)
                payload = {
                    "chat_id": u,
                    "from_chat_id": chat_id,
                    "message_id": msg["message_id"]
                }
                res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/copyMessage", json=payload).json()
                if res.get("ok"):
                    success_count += 1
            except Exception:
                pass
                
        send_bot_message(chat_id, f"{get_pemoji('done', '✅')} <b>Broadcast Completed!</b>\n\nSuccessfully sent to {success_count}/{len(users)} users.", {"inline_keyboard": [[{"text": " Back to Admin", "callback_data": "adm_main_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    if user_conversations.get(chat_id) == "waiting_fj_channel":
        channel = text.strip()
        if channel:
            if "force_join_channels" not in admin_db:
                admin_db["force_join_channels"] = []
            if channel not in admin_db["force_join_channels"]:
                admin_db["force_join_channels"].append(channel)
                save_admin_db()
                threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
            user_conversations.pop(chat_id, None)
            send_bot_message(chat_id, f"{get_pemoji('done', '✅')} <b>Channel added successfully!</b>", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_fj_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    if user_conversations.get(chat_id) == "waiting_admin_id":
        adm_id = text.strip()
        if adm_id.isdigit():
            if "admins" not in admin_db:
                admin_db["admins"] = [OWNER_ID]
            if adm_id not in admin_db["admins"]:
                admin_db["admins"].append(adm_id)
                save_admin_db()
                threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
            user_conversations.pop(chat_id, None)
            send_bot_message(chat_id, f"{get_pemoji('done', '✅')} <b>Admin added successfully!</b>", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_admin_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]})
        else:
            send_bot_message(chat_id, f"{get_pemoji('error', '❌')} Please enter a valid numeric User ID.", {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_admin_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    # adm_prem_flag removed as data is hardcoded

    # --- MANAGE OTP & FORWARD GROUPS ---
    state = user_conversations.get(chat_id, "")

    if state == "set_dxa_grp":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        admin_db.setdefault("dxa_config", {})["withdraw_group"] = text.strip()
        save_admin_db()
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        res_text = f"{get_pemoji('done', '✅')} Withdraw Group Updated!"
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_rew":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["otp_reward"] = float(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} OTP Reward Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Amount!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_min":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["min_withdraw"] = float(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} Min Withdraw Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Amount!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_maxc":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["max_concurrent"] = int(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} Max Concurrent Numbers Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Number!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "set_dxa_cd":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        try:
            admin_db.setdefault("dxa_config", {})["cooldown"] = int(text.strip())
            save_admin_db()
            res_text = f"{get_pemoji('done', '✅')} Cooldown Time Updated!"
        except: res_text = f"{get_pemoji('error', '❌')} Invalid Number!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "add_dxa_mth":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        admin_db.setdefault("dxa_config", {}).setdefault("methods", []).append(text.strip())
        save_admin_db()
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_dxa_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        res_text = f"{get_pemoji('done', '✅')} Method {text.strip()} Added!"
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("wd_wait_amt_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        method = state.replace("wd_wait_amt_", "")
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        kb = {"inline_keyboard": [[{"text": " Cancel", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        try:
            amount = float(text.strip())
            stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
            cfg = admin_db.get("dxa_config", {})
            
            if amount < float(cfg.get("min_withdraw", 20.0)):
                res_text = f"{get_pemoji('error', '❌')} <b>Failed:</b> Minimum withdraw is {cfg.get('min_withdraw', 20.0)} ৳"
                if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
                else: send_bot_message(chat_id, res_text, kb)
            elif amount > stats.get("balance", 0.0):
                res_text = f"{get_pemoji('error', '❌')} <b>Failed:</b> Insufficient balance!"
                if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
                else: send_bot_message(chat_id, res_text, kb)
            else:
                user_conversations[chat_id] = f"wd_wait_num_{method}_{amount}"
                user_prompts[chat_id] = prompt_id 
                res_text = (
                    f"{get_pemoji('gem', '💎')} <b>Withdraw via {method}</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"{get_pemoji('done', '✅')} <b>Amount:</b> {amount} ৳\n\n"
                    f"{get_pemoji('phone', '📱')} Now, please send your <b>Account Number</b>:"
                )
                if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
                else: 
                    new_msg = send_bot_message(chat_id, res_text, kb)
                    if new_msg: user_prompts[chat_id] = new_msg.get("result", {}).get("message_id")
        except ValueError:
            res_text = f"{get_pemoji('error', '❌')} Invalid amount format. Please send numbers only."
            if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
            else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("wd_wait_num_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        
        # Method এবং Amount এক্সট্র্যাক্ট করা
        remainder = state.replace("wd_wait_num_", "")
        last_underscore = remainder.rfind("_")
        method = remainder[:last_underscore]
        amount = float(remainder[last_underscore+1:])
        number = text.strip()
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        kb = {"inline_keyboard": [[{"text": " Back to Home", "callback_data": "usr_menu_home", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        stats = admin_db.get("user_stats", {}).get(str(chat_id), {"otp_count": 0, "balance": 0.0})
        if stats["balance"] >= amount:
            admin_db["user_stats"][str(chat_id)]["balance"] -= amount
            save_admin_db()
            
            res_text = (
                f"{get_pemoji('done', '✅')} <b>Withdrawal requested successfully!</b>\n"
                f"━━━━━━━━━━━━\n"
                f"{get_pemoji('gem', '💎')} <b>Amount:</b> {amount} ৳\n"
                f"{get_pemoji('phone', '📱')} <b>Number:</b> <code>{number}</code>\n"
                f"<i>It will be processed soon by the DXA admins.</i>"
            )
            
            cfg = admin_db.get("dxa_config", {})
            w_grp = cfg.get("withdraw_group")
            if w_grp:
                w_msg = (
                    f"╔═══════════════╗\n"
                    f"║ {get_pemoji('gem', '💎')} <b>NEW WITHDRAWAL REQUEST</b>\n"
                    f"╚═══════════════╝\n\n"
                    f"{get_pemoji('user', '👤')} <b>User:</b> <code>{chat_id}</code>\n"
                    f"{get_pemoji('dashboard', '💳')} <b>Method:</b> {method}\n"
                    f"{get_pemoji('phone', '📱')} <b>Account:</b> <code>{number}</code>\n"
                    f"{get_pemoji('fire', '💰')} <b>Amount:</b> <b>{amount} ৳</b>\n"
                    f"━━━━━━━━━━━━"
                )
                wd_kb = {
                    "inline_keyboard": [
                        [
                            {"text": " Approve", "callback_data": "adm_wd_app", "style": "success", "icon_custom_emoji_id": "5352694861990501856"},
                            {"text": " Reject", "callback_data": "adm_wd_rej", "style": "danger", "icon_custom_emoji_id": "5420130255174145507"}
                        ]
                    ]
                }
                call_telegram("sendMessage", {"chat_id": w_grp, "text": w_msg, "parse_mode": "HTML", "reply_markup": wd_kb})
        else:
            res_text = f"{get_pemoji('error', '❌')} Something went wrong with your balance verification!"

        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return
    
    if state.startswith("um_wait_id_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        action_type = state.split("_")[3]
        target_uid = text.strip()
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        
        if not target_uid.isdigit():
            err_txt = "❌ Invalid User ID. Must be numeric."
            kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_user_mgmt_menu", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
            if prompt_id: edit_bot_message(chat_id, prompt_id, err_txt, kb)
            else: send_bot_message(chat_id, err_txt, kb)
            return

        if action_type == "prof":
            render_um_profile(chat_id, prompt_id, target_uid)
        elif action_type == "bal":
            render_um_balance(chat_id, prompt_id, target_uid)
        elif action_type == "ban":
            render_um_ban(chat_id, prompt_id, target_uid)
        return

    if state.startswith("um_wait_amt_"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        parts = state.split("_")
        action = parts[3] # "add" or "sub"
        target_uid = parts[4]
        
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        kb = {"inline_keyboard": [[{"text": " Back to Balance", "callback_data": f"adm_um_view_bal:{target_uid}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        try:
            amount = float(text.strip())
            stats = admin_db.setdefault("user_stats", {}).setdefault(target_uid, {"otp_count": 0, "balance": 0.0})
            
            if action == "add":
                stats["balance"] += amount
                res_txt = f"<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji> Added {amount} ৳ to <code>{target_uid}</code>'s balance."
            else:
                stats["balance"] = max(0.0, stats["balance"] - amount)
                res_txt = f"<tg-emoji emoji-id='5352694861990501856'>✅</tg-emoji> Deducted {amount} ৳ from <code>{target_uid}</code>'s balance."
                
            save_admin_db()
        except ValueError:
            res_txt = "<tg-emoji emoji-id='5420130255174145507'>❌</tg-emoji> Invalid amount! Please send a valid number."
            
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_txt, kb)
        else: send_bot_message(chat_id, res_txt, kb)
        return

    if state == "edit_otp_link":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        link = text.strip()
        admin_db["otp_group_link"] = link
        save_admin_db()
        threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
        res_text = f"{get_pemoji('done', '✅')} User OTP Group Link updated successfully!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state == "add_fwd_grp":
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        g_id = text.strip()
        fwd_groups = admin_db.setdefault("forward_groups", [])
        if not any(g["id"] == g_id for g in fwd_groups):
            fwd_groups.append({"id": g_id, "buttons": []})
            save_admin_db()
            threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
            res_text = f"{get_pemoji('done', '✅')} Forward Group added!"
        else:
            res_text = f"{get_pemoji('error', '❌')} Group already exists!"
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": "adm_otp_grp_menu", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_fwd_btn:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        idx = int(state.split(":")[1])
        
        res_text = f"{get_pemoji('error', '❌')} Invalid format. Use Text|URL"
        if "|" in text:
            b_text, b_url = text.split("|", 1)
            
            # 🚀 Extract Premium Emoji ID directly from the message entities
            em_id = None
            if "entities" in msg:
                for ent in msg["entities"]:
                    if ent.get("type") == "custom_emoji":
                        em_id = ent.get("custom_emoji_id")
                        break
            
            # Remove the fallback emoji character from the text to avoid double emojis
            clean_text = b_text.strip()
            match = re.search(r'^([^\w\s]+)\s*(.*)', clean_text, re.UNICODE)
            if match:
                clean_text = match.group(2).strip()
            
            btn_data = {"text": f" {clean_text}", "url": b_url.strip()}
            if em_id:
                btn_data["emoji_id"] = em_id
            
            fwd_groups = admin_db.get("forward_groups", [])
            if 0 <= idx < len(fwd_groups):
                fwd_groups[idx].setdefault("buttons", []).append(btn_data)
                save_admin_db()
                threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
                res_text = f"{get_pemoji('done', '✅')} Button added successfully!"
                
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_fwd_view:{idx}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_srch_pfx:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        pnl_id = state.split(":")[1]
        pfx = text.strip().replace("+", "")
        
        res_text = f"{get_pemoji('error', '❌')} Invalid format. Only numbers are allowed."
        kb = {"inline_keyboard": [[{"text": " Back", "callback_data": f"adm_srch_pnl:{pnl_id}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        
        if pfx.isdigit():
            search_cfg = admin_db.setdefault("search_cfg", {})
            p_cfg = search_cfg.setdefault(pnl_id, {"is_active": True, "prefixes": []})
            if pfx not in p_cfg["prefixes"]:
                p_cfg["prefixes"].append(pfx)
                save_admin_db()
                res_text = f"{get_pemoji('done', '✅')} Country code <b>+{pfx}</b> added for search!"
            else:
                res_text = f"{get_pemoji('error', '❌')} Country code already exists!"
                
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        if prompt_id: edit_bot_message(chat_id, prompt_id, res_text, kb)
        else: send_bot_message(chat_id, res_text, kb)
        return
    
    if state.startswith("add_svc_name:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        pnl_id = state.split(":")[1]
        svc_name = text.strip()
        svc_id = svc_name.lower().replace(" ", "_")
        services_dict = load_services()
        if pnl_id not in services_dict:
            services_dict[pnl_id] = []
            
        p_services = services_dict[pnl_id]
        kb = {"inline_keyboard": [[{"text": " Back to Services", "callback_data": f"adm_svc_pnl:{pnl_id}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        if not any(s['id'] == svc_id for s in p_services):
            p_services.append({"id": svc_id, "name": svc_name, "countries": []})
            save_services(services_dict)
            res_text = f"{get_pemoji('done', '✅')} Service <b>{svc_name}</b> added to panel!"
        else:
            res_text = f"{get_pemoji('error', '❌')} Service already exists!"
        
        if prompt_id:
            edit_bot_message(chat_id, prompt_id, res_text, kb)
        else:
            send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_svc_ctr:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        parts = state.split(":")
        pnl_id = parts[1]
        s_id = parts[2]
        c_code = text.strip().upper()
        services_dict = load_services()
        p_services = services_dict.get(pnl_id, [])
        
        kb = {"inline_keyboard": [[{"text": " Back to Service", "callback_data": f"adm_svc_view:{pnl_id}:{s_id}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        res_text = f"{get_pemoji('error', '❌')} Error processing country."
        
        for s in p_services:
            if s['id'] == s_id:
                if not any(c['code'] == c_code for c in s.get('countries', [])):
                    s.setdefault('countries', []).append({"code": c_code, "ranges": []})
                    save_services(services_dict)
                    res_text = f"{get_pemoji('done', '✅')} Country <b>{c_code}</b> added to {s['name']}!"
                else:
                    res_text = f"{get_pemoji('error', '❌')} Country already added!"
                break
                
        if prompt_id:
            edit_bot_message(chat_id, prompt_id, res_text, kb)
        else:
            send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("add_svc_rg:"):
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        parts = state.split(":")
        pnl_id = parts[1]
        s_id = parts[2]
        c_code = parts[3]
        
        new_range = text.strip().upper()
        if not any(x in new_range for x in ("X", "*")) and new_range.isdigit():
            new_range += "XXX"
            
        services_dict = load_services()
        p_services = services_dict.get(pnl_id, [])
        kb = {"inline_keyboard": [[{"text": " Back to Ranges", "callback_data": f"adm_svc_ctr:{pnl_id}:{s_id}:{c_code}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
        res_text = f"{get_pemoji('error', '❌')} Error processing range."
        
        for s in p_services:
            if s['id'] == s_id:
                for c in s.get('countries', []):
                    if c['code'] == c_code:
                        if new_range not in c.get('ranges', []):
                            c.setdefault('ranges', []).append(new_range)
                            save_services(services_dict)
                            res_text = f"{get_pemoji('done', '✅')} Range <code>{new_range}</code> added!"
                        else:
                            res_text = f"{get_pemoji('error', '❌')} Range already exists!"
                        break
                break
                
        if prompt_id:
            edit_bot_message(chat_id, prompt_id, res_text, kb)
        else:
            send_bot_message(chat_id, res_text, kb)
        return

    if state.startswith("edit_pnl_"):
        parts = state.split("_")
        if len(parts) >= 4:
            p_idx = int(parts[2])
            field_key = parts[3]
            
            if p_idx < len(panels):
                p = panels[p_idx]
                
                mapping = {
                    "url": "url", 
                    "user": "username", 
                    "pass": "password", 
                    "getnum": "getNumberUrl", 
                    "getmsg": "getMessageUrl", 
                    "traffic": "trafficUrl"
                }
                actual_key = mapping.get(field_key, field_key)
                p[actual_key] = text
                
                if field_key in ["url", "user", "pass"]:
                    p["sessionCookie"] = "" # Reset session for auth changes
                    
                save_panels_to_file(panels)
                user_conversations.pop(chat_id, None)
                
                # ইউজারের ইনপুট মেসেজ ডিলিট করে দেওয়া হচ্ছে
                call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
                prompt_id = user_prompts.pop(chat_id, None)
                
                if field_key in ["url", "user", "pass"]:
                    wait_text = f"{get_pemoji('wait', '⏳')} <b>Configuration Saved!</b>\nChecking authentication status for {p['name']}..."
                    if prompt_id:
                        edit_bot_message(chat_id, prompt_id, wait_text)
                    else:
                        wait_msg = send_bot_message(chat_id, wait_text)
                        prompt_id = wait_msg.get("result", {}).get("message_id")
                        
                    login_result = login_to_panel(p, force=True)
                    
                    if login_result:
                        final_text = f"{get_pemoji('done', '✅')} <b>Success!</b> Login verified with new settings."
                        style = "success"
                    else:
                        final_text = f"{get_pemoji('error', '❌')} <b>Login Failed!</b> Please check your URL/Credentials."
                        style = "danger"
                        
                    edit_bot_message(chat_id, prompt_id, final_text, {
                        "inline_keyboard": [[{"text": " Back to Panel details", "callback_data": f"adm_pnl_view:{p_idx}", "style": style, "icon_custom_emoji_id": "5267490665117275176"}]]
                    })
                else:
                    res_text_edit = f"{get_pemoji('done', '✅')} <b>Configuration Saved!</b>\n\nAPI link updated successfully."
                    kb_edit = {"inline_keyboard": [[{"text": " Back to Panel details", "callback_data": f"adm_pnl_view:{p_idx}", "style": "primary", "icon_custom_emoji_id": "5267490665117275176"}]]}
                    if prompt_id:
                        edit_bot_message(chat_id, prompt_id, res_text_edit, kb_edit)
                    else:
                        send_bot_message(chat_id, res_text_edit, kb_edit)
                return
            
    if not text:
        return

    # 🚀 Track Unique Users for Admin DB
    if chat_id not in admin_db.get("users", []):
        if "users" not in admin_db:
            admin_db["users"] = []
        admin_db["users"].append(chat_id)
        save_admin_db()
        # Background Auto-Sync to Firebase
        threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
        
    lower = text.lower()
    logger.info(f"Inbound chat message [ID={chat_id}]: '{text}'")

    # 🛡️ Force Join Check Middleware
    if not check_force_join(chat_id):
        return

    # Handle Admin Panel Option
    if "admin panel" in lower or lower == "/admin":
        render_admin_panel(chat_id)
        return

    # Handle Start/Menu commands ONLY
    if lower in ["/start", "/help", "/menu"]:
        text_start = (
            "╔═══════════╗\n"
            f"       {get_pemoji('dashboard', '📊')} <b>NUMBER BOT</b>\n"
            "╚═══════════╝\n"
            f"{get_pemoji('rocket', '🚀')} Welcome to Number & OTP Service\n"
            "━━━━━━━━━━━━\n"
            f"{get_pemoji('done', '✅')} Choose an option below\n"
            "to continue using the bot.\n"
            "━━━━━━━━━━━━\n"
            f"{get_pemoji('gem', '💎')} Premium OTP Service"
        )
        # শুধু ওয়েলকাম মেসেজ এবং নিচের কীবোর্ড দেবে
        send_bot_message(chat_id, text_start, get_bot_menu_keyboard(chat_id))
        return

    # Handle Get Number command ONLY
    if "get number" in lower:
        # শুধু Get Number এ চাপ দিলে সার্ভিস লিস্ট দেবে
        render_services_list(chat_id)
        return

    # Handle Master Menu Commands
    if "2fa setup" in lower or lower == "/2fa":
        user_conversations[chat_id] = "waiting_for_2fa"
        text_help = (
            "╔═══════════╗\n"
            f"     {get_pemoji('otp', '🔐')} <b>2FA SETUP</b>\n"
            "╚═══════════╝\n"
            f"{get_pemoji('done', '📌')} Send your 2FA Secret Key\n"
            "to generate the 6-digit code.\n"
            "━━━━━━━━━━━━━\n"
            f"{get_pemoji('note', '📝')} Example: <code>JBSWY3DPEHPK3PXP</code>"
        )
        res = send_bot_message(chat_id, text_help, {"inline_keyboard": [[{"text": " Cancel", "callback_data": "cancel_2fa", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        # প্রম্পট মেসেজের আইডি সেভ করা হলো যাতে পরে এডিট করা যায়
        if res and res.get("result"):
            user_prompts[chat_id] = res["result"]["message_id"]
        return

    if "search range" in lower or "search number" in lower or lower == "/search":
        user_conversations[chat_id] = "waiting_for_search"
        text_help = (
            "╔═══════════╗\n"
            f"     {get_pemoji('search', '🔍')} <b>SEARCH RANGE</b>\n"
            "╚═══════════╝\n"
            f"{get_pemoji('done', '📌')} Enter 3 to 11 digits  \n"
            "to search for a number.\n"
            "━━━━━━━━━━━━━\n"
            f"<tg-emoji emoji-id='5395444784611480792'>📝</tg-emoji> Example:\n"
            "➥ 880\n"
            "➥ 9227373\n"
            "━━━━━━━━━━━━━\n"
            f"{get_pemoji('search', '🔍')} Fast Number Lookup System"
        )
        send_bot_message(chat_id, text_help, {"inline_keyboard": [[{"text": " Back", "callback_data": "usr_menu_home", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]})
        return

    if lower.startswith("/search "):
        query = text[8:].strip()
        if query:
            q_sanit = query.replace("+", "").strip()
            # X বা * মুছে ফেলে শুধু মূল নাম্বার বের করা হচ্ছে
            base_digits = re.sub(r'[Xx*]', '', q_sanit)
            
            valid_panels = panels
            if not valid_panels:
                send_bot_message(chat_id, f"{get_pemoji('error', '❌')} No active panels available.")
                return
            chosen_panel_id = random.choice(valid_panels)["id"]
            
            # ৩ থেকে ১১ ডিজিট হলে XXX যুক্ত করে নতুন নাম্বার আনবে
            if base_digits.isdigit() and 3 <= len(base_digits) <= 11:
                trigger_buy_number(chat_id, base_digits + "XXX", chosen_panel_id)
            else:
                search_number_otp(chat_id, base_digits)
        else:
            send_bot_message(chat_id, "❌ Please specify a number to search. Usage: <code>/search 237620610123</code>")
        return

    if "traffic" in lower or lower == "/traffic":
        render_traffic_home(chat_id)
        return

    if "balance" in lower or lower == "/balance":
        render_user_balance(chat_id)
        return

    # Direct allocation hooks format buy/get/getnum
    if lower.startswith(("/getnum ", "/buy ", "/get ")):
        parts = text.split()
        if len(parts) > 1:
            q_rang = parts[-1].replace("+", "").strip()
            if 'x' in q_rang.lower():
                trigger_buy_number(chat_id, q_rang.upper())
            elif q_rang.isdigit() and len(q_rang) <= 9:
                trigger_buy_number(chat_id, q_rang + "XXX")
            else:
                trigger_buy_number(chat_id, q_rang)
        else:
            send_bot_message(chat_id, "❌ Please specify a range. Usage: <code>/getnum 237620610XXX</code>")
        return

    if user_conversations.get(chat_id) == "waiting_for_2fa":
        secret = text.strip()
        user_conversations.pop(chat_id, None)
        prompt_id = user_prompts.pop(chat_id, None)
        
        # ইউজারের পাঠানো মেসেজটি (Secret Key) ডিলিট করে দেওয়া হচ্ছে
        call_telegram("deleteMessage", {"chat_id": chat_id, "message_id": msg["message_id"]})
        
        code = get_totp_token(secret)
        if code:
            msg_text = (
                f"╔═══════════╗\n"
                f"     {get_pemoji('otp', '🔐')} <b>2FA CODE GENERATED</b>\n"
                f"╚═══════════╝\n"
                f"<b>Secret:</b> <code>{secret}</code>\n"
                f"━━━━━━━━━━━━━\n"
                f"{get_pemoji('done', '✅')} <b>Code:</b> <code>{code}</code>\n"
                f"<i>(This code is valid for 30 seconds)</i>"
            )
            kb = {"inline_keyboard": [
                [{"text": " Refresh Code", "callback_data": f"refresh_2fa:{secret}", "style": "success", "icon_custom_emoji_id": "5465368548702446780"}],
                [{"text": " Close", "callback_data": "cancel_2fa", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]
            ]}
            if prompt_id:
                edit_bot_message(chat_id, prompt_id, msg_text, kb)
            else:
                send_bot_message(chat_id, msg_text, kb)
        else:
            err_text = f"{get_pemoji('error', '❌')} Invalid 2FA Secret Key format. Please ensure you entered the correct key."
            err_kb = {"inline_keyboard": [[{"text": " Close", "callback_data": "cancel_2fa", "style": "danger", "icon_custom_emoji_id": "5267490665117275176"}]]}
            if prompt_id:
                edit_bot_message(chat_id, prompt_id, err_text, err_kb)
            else:
                send_bot_message(chat_id, err_text, err_kb)
        return

    # Process raw numerical values ONLY IF in search state
    if user_conversations.get(chat_id) == "waiting_for_search":
        user_conversations.pop(chat_id, None)  # ইনপুট নেওয়ার পর state ক্লিয়ার করে দেবে
        clean_text = text.replace("+", "").strip()
        # X বা * মুছে ফেলে শুধু মূল নাম্বার বের করা হচ্ছে
        base_digits = re.sub(r'[Xx*]', '', clean_text)

        valid_panels = panels
        if not valid_panels:
            send_bot_message(chat_id, f"{get_pemoji('error', '❌')} No active panels available.")
            return
        chosen_panel_id = random.choice(valid_panels)["id"]

        if base_digits.isdigit():
            # ৩ থেকে ১১ ডিজিট হলে XXX যুক্ত করে নতুন নাম্বার আনবে
            if 3 <= len(base_digits) <= 11:
                trigger_buy_number(chat_id, base_digits + "XXX", chosen_panel_id)
            else:
                search_number_otp(chat_id, base_digits)
            return
        else:
            send_bot_message(chat_id, "❌ Invalid format. Please enter a valid number or range.")
            return

    # General unknown prompt Fallback (Disabled)
    pass

# ----------------------------------------------------
# Background Panel Periodic SMS Forwarder Checks Thread
# ----------------------------------------------------

def check_cdrs_for_panel(panel):
    global local_traffic_stats, local_raw_logs_cache
    session = get_session(panel["id"])
    baseUrl = normalize_base_url(panel["url"])

    try:
        clean_base = get_clean_base_url(panel, baseUrl)
        logs_url = panel.get("trafficUrl") or f"{clean_base}/console"
        otp_url = panel.get("getMessageUrl") or f"{clean_base}/success-otp"
        headers = {"Content-Type": "application/json", "mauthapi": panel.get("sessionCookie", "MKJGS2MSZYB")}
        
        # 1. Traffic Fetch
        res = session.get(logs_url, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            hits = data.get("data", {}).get("hits", [])
            if isinstance(hits, list):
                ref_time = get_current_cest_time()
                if panel.get("is_traffic_active", True):
                    for log in hits:
                        log_id = f"{log.get('time')}_{log.get('range')}_{str(log.get('message', ''))[:5]}"
                        if log_id: local_raw_logs_cache[log_id] = {
                            "time": get_current_cest_time(),
                            "app_name": log.get("sid", "OTP"),
                            "number": log.get("range", ""),
                            "range": log.get("range", "")
                        }
                    
                new_stats = {}
                keys_to_delete = []
                for log_id, log_data in local_raw_logs_cache.items():
                    if get_seconds_difference(log_data.get("time", ""), ref_time) <= 600:
                        display_service = get_service_display_name(log_data.get("app_name") or "Unknown")
                        num = log_data.get("number") or ""
                        c_code = get_country_code(num)
                        range_val = log_data.get("range") or get_range_from_number(num)

                        new_stats.setdefault(display_service, {}).setdefault(c_code, {"success": 0, "ranges": {}})
                        new_stats[display_service][c_code]["success"] += 1
                        new_stats[display_service][c_code]["ranges"][range_val] = new_stats[display_service][c_code]["ranges"].get(range_val, 0) + 1
                    else:
                        keys_to_delete.append(log_id)
                for k in keys_to_delete: del local_raw_logs_cache[k]
                local_traffic_stats = new_stats
        
        # 2. OTP Fetch
        otp_res = session.get(otp_url, headers=headers, timeout=20)
        if otp_res.status_code == 200:
            otp_data = otp_res.json()
            otps = otp_data.get("data", {}).get("otps", [])
            if isinstance(otps, list):
                updated = False
                if "lastSeenGetnumIds" not in panel or not isinstance(panel["lastSeenGetnumIds"], list):
                    panel["lastSeenGetnumIds"] = []
                
                is_initial = len(panel["lastSeenGetnumIds"]) == 0

                for item in otps:
                    unique_key = str(item.get("otp_id", ""))
                    msg = str(item.get("message", "")).strip()
                    num = str(item.get("number", ""))
                    
                    if unique_key and msg and unique_key not in panel["lastSeenGetnumIds"]:
                        if is_initial:
                            panel["lastSeenGetnumIds"].append(unique_key)
                            updated = True
                        else:
                            logger.info(f"[{panel['name']}] Forwarding Voltx API SMS: {num}")
                            process_and_send_sms(panel['name'], f"+{num}", "OTP", msg)
                            panel["lastSeenGetnumIds"].append(unique_key)
                            updated = True

                if len(panel["lastSeenGetnumIds"]) > 200: panel["lastSeenGetnumIds"] = panel["lastSeenGetnumIds"][-200:]
                if updated: save_panels_to_file(panels)

    except Exception as e:
        logger.error(f"[{panel['name']}] Error polling Voltx API: {e}")

def monitor_loop():
    logger.info("Background Panel Monitoring Loop Thread started successfully.")
    sync_counter = 0
    while True:
        try:
            for panel in panels:
                check_cdrs_for_panel(panel)
            
            # 🚀 Auto Sync to Firebase every ~5 minutes (30 loops * 10s)
            sync_counter += 1
            if sync_counter >= 30:
                threading.Thread(target=sync_essential_data_to_firestore, daemon=True).start()
                sync_counter = 0
                
        except Exception as e:
            logger.error(f"Global panel check monitor loop exception: {e}")
        time.sleep(10)

# ----------------------------------------------------
# Main Program Entry Point
# ----------------------------------------------------

def main():
    logger.info("Initializing Voltx API Unified Bot...")
    
    # Run immediate validation of panel logins
    for panel in panels:
        threading.Thread(target=login_to_panel, args=(panel,), daemon=True).start()

    # Start automated background checker thread
    threading.Thread(target=monitor_loop, daemon=True).start()

    # Empty old commands in getUpdates queue to prevent old triggers
    call_telegram("getUpdates", {"offset": -1, "timeout": 0})
    logger.info("DXA Telegram Long-Polling Engine online and watching.")

    offset = None
    while True:
        try:
            payload = {"timeout": 30}
            if offset:
                payload["offset"] = offset

            updates = call_telegram("getUpdates", payload)
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    offset = update["update_id"] + 1

                    # Core processing routers (Multi-threading added for 0 lag)
                    if "message" in update:
                        threading.Thread(target=handle_message, args=(update["message"],)).start()
                    elif "callback_query" in update:
                        threading.Thread(target=handle_callback_query, args=(update["callback_query"],)).start()

            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down bot. Enjoy your day!")
            break
        except Exception as e:
            logger.error(f"Long poll loop iteration error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
