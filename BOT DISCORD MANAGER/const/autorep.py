# const/autorep.py

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

supabase: Client = None
if url and key:
    supabase = create_client(url, key)

# Bộ nhớ đệm dùng chung cho cả UI và Bot
AUTO_REPLIES_CACHE = {}

def load_auto_replies():
    if not supabase: return
    try:
        res = supabase.table('auto_replies').select('*').execute()
        AUTO_REPLIES_CACHE.clear() 
        for row in res.data:
            AUTO_REPLIES_CACHE[row['keyword'].lower()] = row['response']
            
    except: pass

def add_or_update_reply(keyword, response):
    kw = keyword.lower().strip()
    if not supabase or not kw: return
    try:
        supabase.table('auto_replies').upsert({'keyword': kw, 'response': response}).execute()
        AUTO_REPLIES_CACHE[kw] = response 
    except: pass

def delete_reply(keyword):
    kw = keyword.lower().strip()
    if not supabase: return
    try:
        supabase.table('auto_replies').delete().eq('keyword', kw).execute()
        if kw in AUTO_REPLIES_CACHE:
            del AUTO_REPLIES_CACHE[kw]
    except: pass