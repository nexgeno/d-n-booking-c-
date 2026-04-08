import asyncio
import os
import json
import re
import random
import string
import discord
import aiohttp
import io
from discord.ext import commands, tasks
from PyQt5.QtCore import QThread, pyqtSignal
from const.dashboard import format_member_data, clean_text
from datetime import datetime, timezone
from const.autorep import AUTO_REPLIES_CACHE
from const.lang import t
from supabase import create_client

IMAGE_DIR = os.path.join(os.getcwd(), "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

THONG_BAO = False 

ADMIN_TRACK_ROLE_IDS = [1429856203957075978, 1432397672735838218] 
PRINCE_ROLE_ID = 1485595825894850711
PRINCESS_ROLE_ID = 1485595866302775367

SUPPORT_ROLE_IDS_STR = os.getenv('SUPPORT_ROLE_IDS', '1432397672735838218, 1429856203957075978')
SUPPORT_ROLE_IDS = [int(r.strip()) for r in SUPPORT_ROLE_IDS_STR.split(',') if r.strip().isdigit()]
SUPPORT_MENTIONS = " ".join([f"<@&{r_id}>" for r_id in SUPPORT_ROLE_IDS])

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if url and key:
        return create_client(url, key)
    return None

user_drafts = {}

def format_vnd(amount):
    if not amount: return "Chưa cập nhật"
    try:
        num = int(re.sub(r'\D', '', str(amount)))
        return f"{num:,} VNĐ".replace(',', '.')
    except:
        return str(amount)

def generate_mnv():
    nums = [str(random.randint(0, 9)) for _ in range(3)]
    letters = [random.choice(string.ascii_uppercase) for _ in range(2)]
    return f"{nums[0]}{letters[0]}{nums[1]}{letters[1]}{nums[2]}"

def get_env_int(key, default):
    val = os.getenv(key)
    if not val or not str(val).strip(): return default
    try: return int(str(val).strip())
    except: return default

def extract_quote_data(raw_quote):
    if not isinstance(raw_quote, str): raw_quote = ""
    mnv_m = re.search(r'\|MNV:(.*?)(?=\||$)', raw_quote)
    hid_m = re.search(r'\|HIDDEN:(.*?)(?=\||$)', raw_quote)
    t_ts = re.search(r'\|T_TS:(.*?)(?=\||$)', raw_quote)
    t_hh = re.search(r'\|T_HH:(.*?)(?=\||$)', raw_quote)
    t_g = re.search(r'\|T_G:(.*?)(?=\||$)', raw_quote)
    t_tr = re.search(r'\|T_TR:(.*?)(?=\||$)', raw_quote)
    
    c_quote = re.sub(r'\|(MNV|HIDDEN|T_TS|T_HH|T_G|T_TR):.*?(?=\||$)', '', raw_quote).strip()
    return {
        'quote': c_quote,
        'mnv': mnv_m.group(1).strip() if mnv_m else '',
        'hidden': hid_m.group(1).strip() if hid_m else '',
        't_ts': t_ts.group(1).strip().upper() if t_ts else '',
        't_hh': t_hh.group(1).strip().upper() if t_hh else '',
        't_g': t_g.group(1).strip().upper() if t_g else '',
        't_tr': t_tr.group(1).strip().upper() if t_tr else ''
    }

def pack_quote_data(quote, mnv, hidden, t_ts, t_hh, t_g, t_tr):
    res = quote.strip()
    if t_ts: res += f" |T_TS:{t_ts.upper()}"
    if t_hh: res += f" |T_HH:{t_hh.upper()}"
    if t_g: res += f" |T_G:{t_g.upper()}"
    if t_tr: res += f" |T_TR:{t_tr.upper()}"
    if hidden: res += f" |HIDDEN:{hidden}"
    if mnv: res += f" |MNV:{mnv}"
    return res

async def save_log(uid, display_id, draft):
    def _task():
        sb = get_supabase()
        if not sb: return
        try:
            res = sb.table('drafts').select('user_id').eq('user_id', str(uid)).execute()
            if res.data:
                sb.table('drafts').update({'draft_data': draft}).eq('user_id', str(uid)).execute()
            else:
                sb.table('drafts').insert({'user_id': str(uid), 'draft_data': draft}).execute()
        except: pass
    await asyncio.to_thread(_task)

async def load_log(uid):
    def _task():
        sb = get_supabase()
        if not sb: return None
        try:
            res = sb.table('drafts').select('draft_data').eq('user_id', str(uid)).execute()
            if res.data: return res.data[0].get('draft_data')
        except: pass
        return None
    return await asyncio.to_thread(_task)

async def delete_log(uid):
    def _task():
        sb = get_supabase()
        if not sb: return
        try: sb.table('drafts').delete().eq('user_id', str(uid)).execute()
        except: pass
    await asyncio.to_thread(_task)

async def get_next_id():
    def _task():
        sb = get_supabase()
        if not sb: return "01"
        try:
            res = sb.table('drafts').select('draft_data').execute()
            max_id = 0
            for d in res.data:
                try:
                    d_id = int(d['draft_data'].get('display_id', '0'))
                    if d_id > max_id: max_id = d_id
                except: pass
            return f"{max_id + 1:02d}"
        except: return "01"
    return await asyncio.to_thread(_task)

async def ensure_draft(interaction: discord.Interaction):
    uid = interaction.user.id
    if uid in user_drafts: return user_drafts[uid]
    
    draft = await load_log(uid)
    if draft:
        if 'mnv' not in draft or not draft['mnv']: draft['mnv'] = generate_mnv()
        user_drafts[uid] = draft
        return draft
        
    channel_name = interaction.channel.name
    match = re.search(r'#(\w+)', channel_name)
    display_id = match.group(1) if match else "01"
    
    draft = {
        'user_id': uid, 'ho_ten': '', 'tuoi': '', 'noi_o': '', 'role': '', 'dich_vu': '', 'game': '', 'quote': '', 
        'avatar': '', 'display_id': display_id, 'gia_cam': '', 'gia_game': '', 'mnv': generate_mnv(),
        'images_tamsu': [], 'images_hatho': [], 'images_game': [], 'images_tarot': []
    }
    user_drafts[uid] = draft
    await save_log(uid, display_id, draft)
    return draft

async def update_draft(uid, draft):
    user_drafts[uid] = draft
    display_id = draft.get('display_id', '01')
    await save_log(uid, display_id, draft)

def get_current_page(interaction: discord.Interaction, images: list):
    if not images: return 0
    try:
        current_url = interaction.message.embeds[0].image.url
        current_base = current_url.split('?')[0]
        for i, img in enumerate(images):
            if img.split('?')[0] == current_base: return i
    except: pass
    return 0

def build_draft_embed(user_id):
    draft = user_drafts.get(user_id, {})
    embed = discord.Embed(title="HỒ SƠ ĐĂNG KÝ ỨNG TUYỂN", color=0xe74c3c)
    role_display = "Công chúa" if draft.get('role') == 'princess' else ("Hoàng tử" if draft.get('role') == 'prince' else 'Chưa cập nhật')
    
    tuoi_gt = draft.get('tuoi') or 'Chưa cập nhật'
    tuoi_str = gt_str = ""
    if '-' in tuoi_gt:
        parts = tuoi_gt.split('-', 1)
        tuoi_str = parts[0].strip()
        gt_str = parts[1].strip()
    else:
        tuoi_str = tuoi_gt
        gt_str = "Chưa cập nhật"
        
    desc = (
        f"**Họ và tên:** {draft.get('ho_ten') or 'Chưa cập nhật'}\n"
        f"**Tuổi:** {tuoi_str}\n"
        f"**Giới tính:** {gt_str}\n"
        f"**Nơi ở:** {draft.get('noi_o') or 'Chưa cập nhật'}\n"
        f"**Quote:** {draft.get('quote') or 'Chưa cập nhật'}\n"
        f"**Vị trí ứng tuyển:** {role_display}\n"
        f"**Dịch vụ:** {draft.get('dich_vu') or 'Chưa cập nhật'}\n"
    )
    if 'Chơi game' in draft.get('dich_vu', ''): desc += f"**Game:** {draft.get('game') or 'Chưa cập nhật'}\n"
    desc += f"**Giá cam:** {format_vnd(draft.get('gia_cam'))}\n"
    if 'Chơi game' in draft.get('dich_vu', ''): desc += f"**Giá game:** Deal\n"
    embed.description = desc
    
    all_imgs = draft.get('images_tamsu', []) + draft.get('images_hatho', []) + draft.get('images_game', []) + draft.get('images_tarot', [])
    
    if draft.get('avatar'): embed.set_thumbnail(url=draft.get('avatar'))
    if all_imgs: embed.set_image(url=all_imgs[0])
    return embed

class OtherServiceModal(discord.ui.Modal, title='THÊM DỊCH VỤ'):
    service_name = discord.ui.TextInput(label='Dịch vụ', required=True, placeholder='')
    def __init__(self, draft, uid, selected_values):
        super().__init__()
        self.draft = draft
        self.uid = uid
        self.selected_values = [v for v in selected_values if v != 'Khác']
    async def on_submit(self, interaction: discord.Interaction):
        new_srv = self.service_name.value.strip()
        if new_srv and new_srv not in self.selected_values:
            self.selected_values.append(new_srv)
        self.draft['dich_vu'] = ", ".join(self.selected_values)
        if 'Chơi game' not in self.selected_values: self.draft['game'] = ""
        await update_draft(self.uid, self.draft)
        embed = build_draft_embed(self.uid)
        await interaction.response.edit_message(embed=embed, view=create_draft_view(self.uid))

class OtherGameModal(discord.ui.Modal, title='THÊM GAME MỚI'):
    game_name = discord.ui.TextInput(label='Tên Game', required=True, placeholder='')
    def __init__(self, draft, uid, selected_values):
        super().__init__()
        self.draft = draft
        self.uid = uid
        self.selected_values = [v for v in selected_values if v != 'Khác']
    async def on_submit(self, interaction: discord.Interaction):
        new_game = self.game_name.value.strip()
        if new_game and new_game not in self.selected_values:
            self.selected_values.append(new_game)
        self.draft['game'] = ", ".join(self.selected_values)
        await update_draft(self.uid, self.draft)
        embed = build_draft_embed(self.uid)
        await interaction.response.edit_message(embed=embed, view=create_draft_view(self.uid))

class ApplyTextModal(discord.ui.Modal, title='THÔNG TIN CÁ NHÂN & GIÁ'):
    ho_ten = discord.ui.TextInput(label='Họ và tên', required=True)
    tuoi = discord.ui.TextInput(label='Tuổi - Giới tính (VD: 20 - Nữ)', required=True, max_length=25)
    noi_o = discord.ui.TextInput(label='Nơi ở', required=True)
    gia_cam = discord.ui.TextInput(label='Giá cam', required=True)
    quote = discord.ui.TextInput(label='Quote', style=discord.TextStyle.paragraph, required=True)
    
    def __init__(self, draft, uid):
        super().__init__()
        self.draft = draft
        self.uid = uid
        self.ho_ten.default = draft.get('ho_ten', '')
        self.tuoi.default = draft.get('tuoi', '')
        self.noi_o.default = draft.get('noi_o', '')
        self.gia_cam.default = draft.get('gia_cam', '')
        self.quote.default = draft.get('quote', '')
        
    async def on_submit(self, interaction: discord.Interaction):
        self.draft['ho_ten'] = self.ho_ten.value
        self.draft['tuoi'] = self.tuoi.value
        self.draft['noi_o'] = self.noi_o.value
        self.draft['gia_cam'] = self.gia_cam.value
        self.draft['quote'] = self.quote.value
        
        curr_srvs = [s.strip() for s in self.draft.get('dich_vu', '').split(',')] if self.draft.get('dich_vu') else []
        if 'Chơi game' in curr_srvs: self.draft['gia_game'] = 'Deal'
        
        await update_draft(self.uid, self.draft)
        embed = build_draft_embed(self.uid)
        await interaction.response.edit_message(embed=embed, view=create_draft_view(self.uid))

def create_draft_view(user_id, current_page=0):
    draft = user_drafts.get(user_id, {})
    avatar = draft.get('avatar', '')

    curr_srvs = [s.strip() for s in draft.get('dich_vu', '').split(',')] if draft.get('dich_vu') else []
    curr_srvs = [s for s in curr_srvs if s]

    if 'Chơi game' in curr_srvs: view = ApplyDashboardViewWithGame()
    else: view = ApplyDashboardViewWithoutGame()

    role_sel = discord.utils.get(view.children, custom_id="draft_role")
    if role_sel:
        for opt in role_sel.options: opt.default = (opt.value == draft.get('role'))

    srv_sel = discord.utils.get(view.children, custom_id="draft_srv")
    if srv_sel:
        std_srvs = [opt.value for opt in srv_sel.options]
        khac_opt = next((o for o in srv_sel.options if o.value == 'Khác'), None)
        if khac_opt: srv_sel.options.remove(khac_opt)
        for s in curr_srvs:
            if s not in std_srvs and s != 'Khác':
                srv_sel.options.append(discord.SelectOption(label=s, value=s, default=True))
        if khac_opt: srv_sel.options.append(khac_opt)
        for opt in srv_sel.options:
            opt.default = (opt.value in curr_srvs)
            if opt.value == 'Khác': opt.default = False
        srv_sel.max_values = min(25, len(srv_sel.options))

    game_sel = discord.utils.get(view.children, custom_id="draft_game")
    if game_sel:
        curr_games = [g.strip() for g in draft.get('game', '').split(',')] if draft.get('game') else []
        curr_games = [g for g in curr_games if g]
        std_games = [opt.value for opt in game_sel.options]
        khac_opt = next((o for o in game_sel.options if o.value == 'Khác'), None)
        if khac_opt: game_sel.options.remove(khac_opt)
        for g in curr_games:
            if g not in std_games and g != 'Khác':
                game_sel.options.append(discord.SelectOption(label=g, value=g, default=True))
        if khac_opt: game_sel.options.append(khac_opt)
        for opt in game_sel.options:
            opt.default = (opt.value in curr_games)
            if opt.value == 'Khác': opt.default = False
        game_sel.max_values = min(25, len(game_sel.options))

    text_btn = discord.utils.get(view.children, custom_id="draft_text")
    if text_btn and draft.get('ho_ten') and draft.get('tuoi') and draft.get('noi_o') and draft.get('quote') and draft.get('gia_cam'):
        text_btn.style = discord.ButtonStyle.primary

    avatar_btn = discord.utils.get(view.children, custom_id="draft_avatar")
    if avatar_btn and avatar: avatar_btn.style = discord.ButtonStyle.primary

    ts_btn = discord.utils.get(view.children, custom_id="draft_img_ts")
    if ts_btn:
        if 'Tâm sự' not in curr_srvs: view.remove_item(ts_btn)
        elif draft.get('images_tamsu'): ts_btn.style = discord.ButtonStyle.primary

    h_btn = discord.utils.get(view.children, custom_id="draft_img_h")
    if h_btn:
        if 'Hát hò' not in curr_srvs: view.remove_item(h_btn)
        elif draft.get('images_hatho'): h_btn.style = discord.ButtonStyle.primary

    g_btn = discord.utils.get(view.children, custom_id="draft_img_g")
    if g_btn:
        if 'Chơi game' not in curr_srvs: view.remove_item(g_btn)
        elif draft.get('images_game'): g_btn.style = discord.ButtonStyle.primary

    t_btn = discord.utils.get(view.children, custom_id="draft_img_t")
    if t_btn:
        if 'Tarot' not in curr_srvs: view.remove_item(t_btn)
        elif draft.get('images_tarot'): t_btn.style = discord.ButtonStyle.primary

    submit_btn = discord.utils.get(view.children, custom_id="draft_submit")
    if submit_btn:
        can_submit = bool(draft.get('ho_ten') and draft.get('role') and draft.get('dich_vu') and draft.get('tuoi') and avatar and draft.get('gia_cam'))
        if 'Chơi game' in curr_srvs and not draft.get('game'): can_submit = False
        submit_btn.disabled = not can_submit

    return view

class BaseApplyView(discord.ui.View):
    async def request_image_upload(self, interaction, category_key, btn_label):
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        await interaction.response.send_message(f"Vui lòng gửi ảnh cho mục **{btn_label}** vào đây! Không gửi ảnh 18+ dưới mọi hình thức!", ephemeral=True)
        def check(m): return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and len(m.attachments) > 0 and all(att.content_type and att.content_type.startswith('image/') for att in m.attachments)
        try:
            msg = await interaction.client.wait_for('message', timeout=300.0, check=check)
            files = [await att.to_file() for att in msg.attachments]
            storage_msg = await interaction.channel.send(files=files)
            
            if category_key == 'avatar':
                draft['avatar'] = storage_msg.attachments[0].url
            else:
                draft[category_key].extend([a.url for a in storage_msg.attachments])
                
            await update_draft(uid, draft)
            try: await msg.delete()
            except: pass
            try: await interaction.delete_original_response()
            except: pass
            embed = build_draft_embed(uid)
            await interaction.message.edit(embed=embed, view=create_draft_view(uid))
        except asyncio.TimeoutError:
            try: await interaction.delete_original_response()
            except: pass

    async def shift_page(self, interaction, step):
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        all_imgs = draft.get('images_tamsu', []) + draft.get('images_hatho', []) + draft.get('images_game', []) + draft.get('images_tarot', [])
        if not draft or not all_imgs: return await interaction.response.defer()
        
        current_page = get_current_page(interaction, all_imgs)
        next_page = (current_page + step) % len(all_imgs)
        embed = interaction.message.embeds[0]
        embed.set_image(url=all_imgs[next_page])
        await interaction.response.edit_message(embed=embed, view=create_draft_view(uid, next_page))

class ApplyDashboardViewWithGame(BaseApplyView):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.select(placeholder="Lựa chọn Vị trí", options=[discord.SelectOption(label="Công chúa", value="princess"), discord.SelectOption(label="Hoàng tử", value="prince")], custom_id="draft_role", row=0)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.Select):
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        draft['role'] = select.values[0] if select.values else ""
        await update_draft(uid, draft)
        embed = build_draft_embed(uid)
        await interaction.response.edit_message(embed=embed, view=create_draft_view(uid))

    @discord.ui.select(placeholder="Lựa chọn Dịch vụ", min_values=0, max_values=5, options=[discord.SelectOption(label="Tâm sự", value="Tâm sự"), discord.SelectOption(label="Chơi game", value="Chơi game"), discord.SelectOption(label="Tarot", value="Tarot"), discord.SelectOption(label="Hát hò", value="Hát hò"), discord.SelectOption(label="Khác", value="Khác")], custom_id="draft_srv", row=1)
    async def select_service(self, interaction: discord.Interaction, select: discord.ui.Select):
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        normal_values = [v for v in select.values if v != 'Khác']
        draft['dich_vu'] = ", ".join(normal_values)
        if 'Chơi game' not in normal_values: draft['game'] = ""
        await update_draft(uid, draft)
        if "Khác" in select.values:
            await interaction.response.send_modal(OtherServiceModal(draft, uid, normal_values))
            async def reset_view():
                await asyncio.sleep(0.5)
                try: await interaction.message.edit(view=create_draft_view(uid))
                except: pass
            asyncio.create_task(reset_view())
        else:
            embed = build_draft_embed(uid)
            await interaction.response.edit_message(embed=embed, view=create_draft_view(uid))

    @discord.ui.select(placeholder="Lựa chọn Game", min_values=0, max_values=7, options=[discord.SelectOption(label="Liên Minh Huyền Thoại", value="Liên Minh Huyền Thoại"), discord.SelectOption(label="Free Fire", value="Free Fire"), discord.SelectOption(label="Valorant", value="Valorant"), discord.SelectOption(label="PUBG", value="PUBG"), discord.SelectOption(label="Liên Quân", value="Liên Quân"), discord.SelectOption(label="TFT", value="TFT"), discord.SelectOption(label="Khác", value="Khác")], custom_id="draft_game", row=2)
    async def select_game(self, interaction: discord.Interaction, select: discord.ui.Select):
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        normal_values = [v for v in select.values if v != 'Khác']
        draft['game'] = ", ".join(normal_values)
        await update_draft(uid, draft)
        if "Khác" in select.values:
            await interaction.response.send_modal(OtherGameModal(draft, uid, normal_values))
            async def reset_view():
                await asyncio.sleep(0.5)
                try: await interaction.message.edit(view=create_draft_view(uid))
                except: pass
            asyncio.create_task(reset_view())
        else:
            embed = build_draft_embed(uid)
            await interaction.response.edit_message(embed=embed, view=create_draft_view(uid))

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary, row=3, custom_id="draft_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button): await self.shift_page(interaction, -1)
    
    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary, row=3, custom_id="draft_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button): await self.shift_page(interaction, 1)

    @discord.ui.button(label="Thêm Avatar", style=discord.ButtonStyle.secondary, custom_id="draft_avatar", row=3)
    async def add_avatar_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'avatar', 'Ảnh đại diện')

    @discord.ui.button(label="Điền thông tin", style=discord.ButtonStyle.secondary, custom_id="draft_text", row=3)
    async def text_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        draft = await ensure_draft(interaction)
        await interaction.response.send_modal(ApplyTextModal(draft, interaction.user.id))

    @discord.ui.button(label="Tôi cần hỗ trợ", style=discord.ButtonStyle.secondary, custom_id="draft_support", row=3)
    async def support_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.channel.send(f"Vui lòng đợi {SUPPORT_MENTIONS} đến để hỗ trợ!")

    @discord.ui.button(label="Ảnh Tâm Sự", style=discord.ButtonStyle.secondary, custom_id="draft_img_ts", row=4)
    async def add_img_ts_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'images_tamsu', 'Tâm Sự')

    @discord.ui.button(label="Ảnh Hát", style=discord.ButtonStyle.secondary, custom_id="draft_img_h", row=4)
    async def add_img_h_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'images_hatho', 'Hát hò')

    @discord.ui.button(label="Ảnh Game", style=discord.ButtonStyle.secondary, custom_id="draft_img_g", row=4)
    async def add_img_g_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'images_game', 'Chơi game')

    @discord.ui.button(label="Ảnh Tarot", style=discord.ButtonStyle.secondary, custom_id="draft_img_t", row=4)
    async def add_img_t_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'images_tarot', 'Tarot')

    @discord.ui.button(label="Gửi đơn", style=discord.ButtonStyle.success, disabled=True, custom_id="draft_submit", row=4)
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        display_id = draft.get('display_id', '01')
        
        images_data = []
        for url in draft.get('images_tamsu', []): images_data.append({'url': url, 'type': 'tamsu'})
        for url in draft.get('images_hatho', []): images_data.append({'url': url, 'type': 'hatho'})
        for url in draft.get('images_game', []): images_data.append({'url': url, 'type': 'game'})
        for url in draft.get('images_tarot', []): images_data.append({'url': url, 'type': 'tarot'})
        images_str = json.dumps(images_data)
        
        def _save_to_db():
            try:
                sb = get_supabase()
                if not sb: return
                
                db_quote = pack_quote_data(draft.get('quote', ''), draft.get('mnv', ''), '', '', '', '', '')
                
                data = {
                    'user_id': str(uid), 'role': draft.get('role', ''), 'dich_vu': draft.get('dich_vu', ''),
                    'ho_ten': draft.get('ho_ten', ''), 'tuoi': draft.get('tuoi', ''), 'noi_o': draft.get('noi_o', ''),
                    'game': draft.get('game',''), 'quote': db_quote, 'status': 'pending',
                    'images': images_str, 'display_id': display_id, 'avatar': draft.get('avatar', ''),
                    'gia_cam': draft.get('gia_cam', ''), 'gia_game': draft.get('gia_game', '')
                }
                res = sb.table('application').select('user_id').eq('user_id', str(uid)).execute()
                if res.data:
                    sb.table('application').update(data).eq('user_id', str(uid)).execute()
                else:
                    sb.table('application').insert(data).execute()
            except Exception as e: print(e)

        await asyncio.to_thread(_save_to_db)
        await delete_log(uid)
        try: await interaction.channel.edit(name=f"Hồ Sơ Đăng Ký #{display_id}")
        except: pass
        await interaction.channel.send(f"Đơn ứng tuyển đã nộp thành công! Vui lòng đợi <@&1432397672735838218> đến để kiểm tra!")
        
        if uid in user_drafts: del user_drafts[uid]
        await interaction.edit_original_response(view=None)
        if hasattr(interaction.client, 'bot_logic'): interaction.client.bot_logic.new_application_signal.emit()

class ApplyDashboardViewWithoutGame(BaseApplyView):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.select(placeholder="Lựa chọn Vị trí", options=[discord.SelectOption(label="Công chúa", value="princess"), discord.SelectOption(label="Hoàng tử", value="prince")], custom_id="draft_role", row=0)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.Select):
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        draft['role'] = select.values[0] if select.values else ""
        await update_draft(uid, draft)
        embed = build_draft_embed(uid)
        await interaction.response.edit_message(embed=embed, view=create_draft_view(uid))

    @discord.ui.select(placeholder="Lựa chọn Dịch vụ", min_values=0, max_values=5, options=[discord.SelectOption(label="Tâm sự", value="Tâm sự"), discord.SelectOption(label="Chơi game", value="Chơi game"), discord.SelectOption(label="Tarot", value="Tarot"), discord.SelectOption(label="Hát hò", value="Hát hò"), discord.SelectOption(label="Khác", value="Khác")], custom_id="draft_srv", row=1)
    async def select_service(self, interaction: discord.Interaction, select: discord.ui.Select):
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        normal_values = [v for v in select.values if v != 'Khác']
        draft['dich_vu'] = ", ".join(normal_values)
        if 'Chơi game' not in normal_values: draft['game'] = ""
        await update_draft(uid, draft)
        if "Khác" in select.values:
            await interaction.response.send_modal(OtherServiceModal(draft, uid, normal_values))
            async def reset_view():
                await asyncio.sleep(0.5)
                try: await interaction.message.edit(view=create_draft_view(uid))
                except: pass
            asyncio.create_task(reset_view())
        else:
            embed = build_draft_embed(uid)
            await interaction.response.edit_message(embed=embed, view=create_draft_view(uid))

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary, row=2, custom_id="draft_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button): await self.shift_page(interaction, -1)
    
    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary, row=2, custom_id="draft_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button): await self.shift_page(interaction, 1)

    @discord.ui.button(label="Thêm Avatar", style=discord.ButtonStyle.secondary, custom_id="draft_avatar", row=2)
    async def add_avatar_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'avatar', 'Ảnh đại diện')

    @discord.ui.button(label="Điền thông tin", style=discord.ButtonStyle.secondary, custom_id="draft_text", row=2)
    async def text_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        draft = await ensure_draft(interaction)
        await interaction.response.send_modal(ApplyTextModal(draft, interaction.user.id))

    @discord.ui.button(label="Tôi cần hỗ trợ", style=discord.ButtonStyle.secondary, custom_id="draft_support", row=2)
    async def support_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.channel.send(f"Vui lòng đợi {SUPPORT_MENTIONS} đến để hỗ trợ!")

    @discord.ui.button(label="Ảnh Tâm Sự", style=discord.ButtonStyle.secondary, custom_id="draft_img_ts", row=3)
    async def add_img_ts_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'images_tamsu', 'Tâm Sự')

    @discord.ui.button(label="Ảnh Hát", style=discord.ButtonStyle.secondary, custom_id="draft_img_h", row=3)
    async def add_img_h_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'images_hatho', 'Hát hò')

    @discord.ui.button(label="Ảnh Tarot", style=discord.ButtonStyle.secondary, custom_id="draft_img_t", row=3)
    async def add_img_t_btn(self, interaction: discord.Interaction, button: discord.ui.Button): await self.request_image_upload(interaction, 'images_tarot', 'Tarot')

    @discord.ui.button(label="Gửi đơn", style=discord.ButtonStyle.success, disabled=True, custom_id="draft_submit", row=3)
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        draft = await ensure_draft(interaction)
        uid = interaction.user.id
        display_id = draft.get('display_id', '01')
        
        images_data = []
        for url in draft.get('images_tamsu', []): images_data.append({'url': url, 'type': 'tamsu'})
        for url in draft.get('images_hatho', []): images_data.append({'url': url, 'type': 'hatho'})
        for url in draft.get('images_tarot', []): images_data.append({'url': url, 'type': 'tarot'})
        images_str = json.dumps(images_data)
        
        def _save_to_db():
            try:
                sb = get_supabase()
                if not sb: return
                
                db_quote = pack_quote_data(draft.get('quote', ''), draft.get('mnv', ''), '', '', '', '', '')
                
                data = {
                    'user_id': str(uid), 'role': draft.get('role', ''), 'dich_vu': draft.get('dich_vu', ''),
                    'ho_ten': draft.get('ho_ten', ''), 'tuoi': draft.get('tuoi', ''), 'noi_o': draft.get('noi_o', ''),
                    'game': draft.get('game',''), 'quote': db_quote, 'status': 'pending',
                    'images': images_str, 'display_id': display_id, 'avatar': draft.get('avatar', ''),
                    'gia_cam': draft.get('gia_cam', ''), 'gia_game': draft.get('gia_game', '')
                }
                res = sb.table('application').select('user_id').eq('user_id', str(uid)).execute()
                if res.data:
                    sb.table('application').update(data).eq('user_id', str(uid)).execute()
                else:
                    sb.table('application').insert(data).execute()
            except Exception as e: print(e)

        await asyncio.to_thread(_save_to_db)
        await delete_log(uid)
        try: await interaction.channel.edit(name=f"Hồ Sơ Đăng Ký #{display_id}")
        except: pass
        await interaction.channel.send(f"Đơn ứng tuyển đã nộp thành công! Vui lòng đợi <@&1432397672735838218> đến để kiểm tra!")
        
        if uid in user_drafts: del user_drafts[uid]
        await interaction.edit_original_response(view=None)
        if hasattr(interaction.client, 'bot_logic'): interaction.client.bot_logic.new_application_signal.emit()

async def build_profile_embed(bot, user_id, data, is_public=False, channel_type=None):
    display_id = data.get('display_id') or "01"
    EMBED_COLOR = 0xe74c3c 
    
    ext = extract_quote_data(data.get('quote', ''))
    actual_quote = ext['quote']
    hidden_fields_str = ext['hidden']
    mnv = ext['mnv']

    hidden_fields = [f.strip() for f in hidden_fields_str.split(',') if f.strip()]

    role_display = "Công chúa" if data.get('role') == 'princess' else "Hoàng tử"
    embed = discord.Embed(color=EMBED_COLOR)
    
    tuoi_gt = data.get('tuoi', '')
    tuoi = gt = ""
    if '-' in tuoi_gt:
        p = tuoi_gt.split('-', 1)
        tuoi, gt = p[0].strip(), p[1].strip()
    else:
        tuoi = tuoi_gt
    
    if is_public:
        role_title = ""
        if channel_type == 'hatho': role_title = ext['t_hh'] or "NYX"
        elif channel_type == 'game': role_title = ext['t_g'] or "KLAUS"
        elif channel_type == 'tarot': role_title = ext['t_tr'] or "AERIS"
        else: role_title = ext['t_ts'] or ("HELENA" if data.get('role') == 'princess' else "VLADIMIR")
            
        name = data.get('ho_ten', '').upper()
        e_role = "<a:icon:1486384348877029597>"
        e_name = "<:icon:1486721513783820432>"
        e_info = "<:icon:1486739902459805789>"
        
        title_str = ""
        if 'role' not in hidden_fields:
            title_str = f"{e_role} {role_title} #{display_id} {e_role}"
        if title_str: embed.title = title_str
            
        desc = ""
        if 'ho_ten' not in hidden_fields and name: desc += f"{e_name} {name} {e_name}\n"
        if 'noi_o' not in hidden_fields and data.get('noi_o'): desc += f"{e_info} {data.get('noi_o')}\n"
        if 'tuoi' not in hidden_fields:
            if tuoi: desc += f"{e_info} Tuổi: {tuoi}\n"
            if gt: desc += f"{e_info} Giới tính: {gt}\n"
        if 'quote' not in hidden_fields and actual_quote: desc += f"{e_info} {actual_quote}\n"
        if 'dich_vu' not in hidden_fields and data.get('dich_vu'): desc += f"{e_info} {data.get('dich_vu')}\n"
        if 'Chơi game' in data.get('dich_vu', '') and 'game' not in hidden_fields and data.get('game'): 
            desc += f"{e_info} {data.get('game')}\n"
        if 'gia_cam' not in hidden_fields and data.get('gia_cam'): desc += f"{e_info} Giá cam: {format_vnd(data.get('gia_cam'))}\n"
        if 'Chơi game' in data.get('dich_vu', '') and 'gia_game' not in hidden_fields: 
            desc += f"{e_info} Giá game: Deal\n"
            
        if desc.strip(): embed.description = desc.strip()
    else:
        title_str = f"HỒ SƠ ĐĂNG KÝ #{display_id}"
        desc = ""
        if 'ho_ten' not in hidden_fields: desc += f"Họ và tên: {data.get('ho_ten', '')}\n"
        if 'role' not in hidden_fields: desc += f"Vị trí: {role_display}\n"
        
        cd_str = []
        if ext['t_ts']: cd_str.append(f"TS: {ext['t_ts']}")
        if ext['t_hh']: cd_str.append(f"HH: {ext['t_hh']}")
        if ext['t_g']: cd_str.append(f"Game: {ext['t_g']}")
        if ext['t_tr']: cd_str.append(f"Tarot: {ext['t_tr']}")
        if cd_str: desc += f"Chức danh: {' | '.join(cd_str)}\n"

        if 'tuoi' not in hidden_fields: 
            desc += f"Tuổi: {tuoi}\n"
            if gt: desc += f"Giới tính: {gt}\n"
            
        if 'noi_o' not in hidden_fields: desc += f"Nơi ở: {data.get('noi_o', '')}\n"
        if 'quote' not in hidden_fields: desc += f"Quote: {actual_quote}\n"
        if 'dich_vu' not in hidden_fields: desc += f"Dịch vụ: {data.get('dich_vu', '')}\n"
        if 'Chơi game' in data.get('dich_vu', '') and 'game' not in hidden_fields: desc += f"Game: {data.get('game', '')}\n"
        if 'gia_cam' not in hidden_fields: desc += f"Giá cam: {format_vnd(data.get('gia_cam'))}\n"
        if 'Chơi game' in data.get('dich_vu', '') and 'gia_game' not in hidden_fields: desc += f"Giá game: Deal\n"
        
        embed.title = title_str
        if desc.strip(): embed.description = desc.strip()

    try:
        img_list = json.loads(data.get('images', '[]'))
        if not isinstance(img_list, list): img_list = []
    except:
        img_list = [{'url': u.strip(), 'type': 'general'} for u in data.get('images', '').split(',') if u.strip()]
        
    filtered_urls = []
    if channel_type:
        filtered_urls = [img['url'] for img in img_list if img.get('type') == channel_type]
    
    if not filtered_urls:
        filtered_urls = [img['url'] for img in img_list if img.get('type') == 'tamsu']

    if not filtered_urls:
        filtered_urls = [img['url'] for img in img_list]
        
    avatar = data.get('avatar', '')
    if avatar:
        embed.set_thumbnail(url=avatar)
        if filtered_urls: embed.set_image(url=filtered_urls[0])
    elif filtered_urls:
        embed.set_thumbnail(url=filtered_urls[0])
        embed.set_image(url=filtered_urls[1] if len(filtered_urls) > 1 else filtered_urls[0])
    return embed

class PublicProfileView(discord.ui.View):
    def __init__(self, data=None, channel_type=None):
        super().__init__(timeout=None)
        self.data = data or {}
        self.channel_type = channel_type
        self.image_urls = self.get_filtered_urls()
        self.current_index = 0

        if len(self.image_urls) <= 1:
            self.remove_item(discord.utils.get(self.children, custom_id="pub_prev"))
            self.remove_item(discord.utils.get(self.children, custom_id="pub_next"))

    def get_filtered_urls(self):
        try:
            img_list = json.loads(self.data.get('images', '[]'))
            if not isinstance(img_list, list): img_list = []
        except:
            img_list = [{'url': u.strip(), 'type': 'general'} for u in self.data.get('images', '').split(',') if u.strip()]

        filtered_urls = []
        if self.channel_type:
            filtered_urls = [img['url'] for img in img_list if img.get('type') == self.channel_type]

        if not filtered_urls:
            filtered_urls = [img['url'] for img in img_list if img.get('type') == 'tamsu']

        if not filtered_urls:
            filtered_urls = [img['url'] for img in img_list]
            
        return filtered_urls

    async def update_embed(self, interaction):
        embed = interaction.message.embeds[0]
        if self.image_urls:
            embed.set_image(url=self.image_urls[self.current_index])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Book", style=discord.ButtonStyle.secondary, row=0, custom_id="pub_book")
    async def book_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Coming soon...", ephemeral=True)

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary, row=0, custom_id="pub_star")
    async def rating_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Coming soon...", ephemeral=True)

    @discord.ui.button(label="Feedback", style=discord.ButtonStyle.secondary, row=0, custom_id="pub_feed")
    async def feedback_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Coming soon...", ephemeral=True)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary, row=1, custom_id="pub_prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.image_urls:
            self.current_index = (self.current_index - 1) % len(self.image_urls)
            await self.update_embed(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.secondary, row=1, custom_id="pub_next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.image_urls:
            self.current_index = (self.current_index + 1) % len(self.image_urls)
            await self.update_embed(interaction)

class ReceptionMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Booking", style=discord.ButtonStyle.secondary, custom_id="reception_btn_booking")
    async def booking_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Hệ thống Booking đang khởi động, vui lòng thử lại sau!", ephemeral=True)

    @discord.ui.button(label="Apply", style=discord.ButtonStyle.secondary, custom_id="reception_btn_apply")
    async def apply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        sb = get_supabase()
        if sb:
            res = await asyncio.to_thread(lambda: sb.table('application').select('user_id').eq('user_id', str(user.id)).execute())
            if res.data:
                return await interaction.response.send_message("Bạn đã có hồ sơ. Vui lòng không spam Apply!", ephemeral=True)

        noti_channel = interaction.channel
        for thread in noti_channel.threads:
            if thread.name.startswith("Hồ Sơ Đăng Ký #") and str(user.id) in [str(m.id) for m in thread.members]:
                return await interaction.response.send_message("Bạn đang có phiên ứng tuyển mở!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        display_id = await get_next_id()
        
        try:
            ticket_thread = await noti_channel.create_thread(name=f"Hồ Sơ Đăng Ký #{display_id}", type=discord.ChannelType.private_thread, invitable=False)
            await ticket_thread.add_user(user)
            draft = {'user_id': user.id, 'ho_ten': '', 'tuoi': '', 'noi_o': '', 'role': '', 'dich_vu': '', 'game': '', 'quote': '', 'images_tamsu': [], 'images_hatho': [], 'images_game': [], 'images_tarot': [], 'display_id': display_id, 'gia_cam': '', 'gia_game': '', 'avatar': '', 'mnv': generate_mnv()}
            await update_draft(user.id, draft)
            embed = build_draft_embed(user.id)
            
            msg = await ticket_thread.send(content=f"<@{user.id}> {SUPPORT_MENTIONS}", embed=embed, view=create_draft_view(user.id))
            await interaction.followup.send(f"Đã tạo khu vực ứng tuyển riêng cho bạn tại {ticket_thread.mention} !", ephemeral=True)
            
            try:
                if hasattr(interaction.client, 'bot_logic'):
                    local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                    interaction.client.bot_logic.incoming_msg_signal.emit(
                        str(ticket_thread.id), f"#{ticket_thread.name}", "Bot", "Hệ thống đã tạo hồ sơ", local_time, str(msg.id), "", ""
                    )
            except: pass
            
        except Exception as e: print(e)

    @discord.ui.button(label="Support", style=discord.ButtonStyle.secondary, custom_id="reception_btn_support")
    async def support_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Hệ thống Support đang khởi động, vui lòng thử lại sau!", ephemeral=True)

class DiscordBotLogic(QThread):
    incoming_msg_signal = pyqtSignal(str, str, str, str, str, str, str, str) 
    history_signal = pyqtSignal(str, str, str, list) 
    message_sent_signal = pyqtSignal(str, str, str, str, str, str) 
    user_fetched_signal = pyqtSignal(str, str, str) 
    bot_ready_signal = pyqtSignal(str)
    avatar_updated_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, str)
    sync_completed_signal = pyqtSignal()
    members_fetched_signal = pyqtSignal(dict)
    
    new_application_signal = pyqtSignal()
    image_uploaded_to_discord = pyqtSignal(str, str, str) 
    staff_updated_signal = pyqtSignal()
    staff_update_success_signal = pyqtSignal()

    def __init__(self, token):
        super().__init__()
        self.token = token
        self.loop = None
        self.loaded_history = set()
        self._startup_done = False
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True 
        intents.presences = True 
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.bot.bot_logic = self

        @tasks.loop(seconds=10)
        async def auto_refresh_task(): self._refresh_members()

        @self.bot.event
        async def on_ready():
            if not self._startup_done:
                self._startup_done = True
                self.bot.tree.clear_commands(guild=None)
                try: await self.bot.tree.sync()
                except: pass
                
                self.bot_ready_signal.emit(t('BOT_READY', self.bot.user))
                self.bot.add_view(ReceptionMenu())
                if not auto_refresh_task.is_running(): auto_refresh_task.start()
            self._refresh_members()

        @self.bot.event
        async def on_member_join(member): self._refresh_members()
        @self.bot.event
        async def on_member_remove(member): self._refresh_members()
        @self.bot.event
        async def on_member_update(before, after): self._refresh_members()
        @self.bot.event
        async def on_presence_update(before, after): self._refresh_members()

        @self.bot.event
        async def on_message(message):
            try:
                if message.author == self.bot.user: return
                is_channel = message.guild is not None
                chat_id = str(message.channel.id) if is_channel else str(message.author.id)
                
                # Khử icon cho Hộp thoại Inbox
                from const.dashboard import clean_text
                chat_name = f"#{clean_text(message.channel.name)}" if is_channel else clean_text(message.author.name)
                sender_name = clean_text(message.author.name)
                local_time = message.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                
                if not is_channel:
                    content_lower = message.content.lower()
                    for kw, response_text in AUTO_REPLIES_CACHE.items():
                        if kw in content_lower:
                            try:
                                sent_msg = await message.channel.send(response_text)
                                local_time = sent_msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                                self.message_sent_signal.emit(chat_id, response_text, local_time, str(sent_msg.id), "", t('AUTO_REPLY_TAG'))
                            except: pass
                            break 
                
                avatar_path = ""
                if is_channel and message.guild.icon:
                    filepath = os.path.join(IMAGE_DIR, f"guild_{message.guild.id}.png")
                    if not os.path.exists(filepath): await message.guild.icon.save(filepath)
                    avatar_path = filepath
                elif not is_channel:
                    avatar_path = await self.get_avatar_path(message.author)

                image_path = ""
                if message.attachments:
                    for att in message.attachments:
                        if att.content_type and att.content_type.startswith('image/'):
                            filepath = os.path.join(IMAGE_DIR, f"{message.id}_{att.filename}")
                            await att.save(filepath)
                            image_path = filepath
                            break

                if chat_id not in self.loaded_history:
                    self.loaded_history.add(chat_id)
                    history_data = []
                    download_tasks = []

                    try:
                        async for msg in message.channel.history(limit=50, before=message):
                            local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                            is_self = (msg.author == self.bot.user)
                            s_name = "Bot" if is_self else clean_text(msg.author.name)
                            hist_image_path = ""
                            if msg.attachments:
                                for att in msg.attachments:
                                    if att.content_type and att.content_type.startswith('image/'):
                                        hist_filepath = os.path.join(IMAGE_DIR, f"{msg.id}_{att.filename}")
                                        if not os.path.exists(hist_filepath): download_tasks.append(att.save(hist_filepath))
                                        hist_image_path = hist_filepath
                                        break
                            history_data.append({
                                "sender": s_name, "text": msg.content, "time": local_time,
                                "is_self": is_self, "msg_id": str(msg.id), "image_path": hist_image_path,
                                "status": t('SENT') if is_self else t('READ')
                            })
                    except: pass
                    
                    if download_tasks: await asyncio.gather(*download_tasks, return_exceptions=True)
                    history_data.sort(key=lambda x: int(x['msg_id']))
                    self.history_signal.emit(chat_id, chat_name, avatar_path, history_data)
                
                self.incoming_msg_signal.emit(chat_id, chat_name, sender_name, message.content, local_time, str(message.id), image_path, avatar_path)
            except: pass

    # THUẬT TOÁN QUÉT KÊNH ÉP BUỘC CHỐNG SÓT 100%
    def _refresh_members(self):
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        members_data = []
        admin_data = []
        channels_data = []
        staff_prince = []
        staff_princess = []
        role_counts = {}
        
        members_today = admins_today = staff_today = channels_today = 0
        w1 = w2 = w3 = w4 = 0
        
        from const.dashboard import clean_text
        
        for guild in self.bot.guilds:
            # QUÉT MỌI KÊNH CẤP 1 (Voice, Text, Stage, Category, Forum)
            for ch in guild.channels:
                count = 0
                member_names = []
                if hasattr(ch, 'members') and ch.members:
                    try:
                        m_list = ch.members
                        count = len(m_list)
                        member_names = [m.display_name for m in m_list[:100]]
                    except: pass
                
                c_name = clean_text(ch.name) or str(ch.name)
                channels_data.append({
                    'name': c_name, 'id': str(ch.id), 'count': str(count),
                    'members_list': "\n".join(member_names) if member_names else "Danh sách ẩn"
                })
                try:
                    if ch.created_at and ch.created_at >= today_start: channels_today += 1
                except: pass

                # VÉT TẤT CẢ CHỦ ĐỀ BÊN TRONG KÊNH ĐÓ (Tránh sót thread lồng nhau)
                if hasattr(ch, 'threads') and ch.threads:
                    for th in ch.threads:
                        t_count = getattr(th, 'member_count', 0)
                        t_name = clean_text(th.name) or str(th.name)
                        channels_data.append({
                            'name': t_name, 'id': str(th.id), 'count': str(t_count),
                            'members_list': "Chủ đề ẩn"
                        })
                        try:
                            if th.created_at and th.created_at >= today_start: channels_today += 1
                        except: pass

            # QUÉT VÉT ĐÁY TẤT CẢ THREAD CỦA GUILD (Dành cho Thread mồ côi / Active Threads)
            for thread in guild.threads:
                if not any(d['id'] == str(thread.id) for d in channels_data):
                    t_count = getattr(thread, 'member_count', 0)
                    t_name = clean_text(thread.name) or str(thread.name)
                    channels_data.append({
                        'name': t_name, 'id': str(thread.id), 'count': str(t_count),
                        'members_list': "Chủ đề ẩn"
                    })
                    try:
                        if thread.created_at and thread.created_at >= today_start: channels_today += 1
                    except: pass
                        
            # Cập nhật Member
            for member in guild.members:
                m_data = format_member_data(member)
                members_data.append(m_data)
                
                is_admin = any(rid in ADMIN_TRACK_ROLE_IDS for rid in m_data['role_ids'])
                is_prince = PRINCE_ROLE_ID in m_data['role_ids']
                is_princess = PRINCESS_ROLE_ID in m_data['role_ids']
                
                if is_admin: admin_data.append(m_data)
                if is_prince: staff_prince.append(m_data)
                if is_princess: staff_princess.append(m_data)
                    
                joined_today = False
                if member.joined_at and member.joined_at >= today_start:
                    members_today += 1
                    joined_today = True
                    
                if is_admin and joined_today: admins_today += 1
                if (is_prince or is_princess) and joined_today: staff_today += 1
                    
                for r in member.roles:
                    if r.name != '@everyone': 
                        # Khử emoji cho Role Count
                        c_role = clean_text(r.name) or r.name
                        role_counts[c_role] = role_counts.get(c_role, 0) + 1
                        
                if member.joined_at:
                    days = (now - member.joined_at).days
                    if 0 <= days <= 7: w4 += 1
                    elif 7 < days <= 14: w3 += 1
                    elif 14 < days <= 21: w2 += 1
                    elif 21 < days <= 28: w1 += 1

        def format_pct(total, today):
            yesterday_total = total - today
            if yesterday_total <= 0:
                pct = 100.0 if today > 0 else 0.0
            else:
                pct = ((today - yesterday_total) / yesterday_total) * 100.0
                
            if pct > 0: return f"↑ +{round(pct, 1)}% so với hôm qua"
            elif pct < 0: return f"↓ {round(pct, 1)}% so với hôm qua"
            return "0.0% so với hôm qua"

        payload = {
            'members': members_data, 'admins': admin_data, 'staff_prince': staff_prince, 'staff_princess': staff_princess,
            'channels': channels_data, 'roles': role_counts, 'joins': [w1, w2, w3, w4],
            'stats_pct': {
                'members': format_pct(len(members_data), members_today),
                'admins': format_pct(len(admin_data), admins_today),
                'staff': format_pct(len(staff_prince) + len(staff_princess), staff_today),
                'channels': format_pct(len(channels_data), channels_today),
            }
        }
        self.members_fetched_signal.emit(payload)

    async def get_avatar_path(self, user):
        if not user: return ""
        filename = f"avatar_{user.id}.png"
        filepath = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(filepath):
            try: await user.display_avatar.save(filepath)
            except: pass
        return filepath

    def start_initial_sync(self, sync_data, user_ids):
        if self.loop: asyncio.run_coroutine_threadsafe(self._async_initial_sync(sync_data, user_ids), self.loop)

    async def _async_initial_sync(self, sync_data, user_ids):
        total_tasks = len(user_ids) + len(sync_data)
        current_task = 0
        if total_tasks == 0:
            self.progress_signal.emit(100, t('SYNC_DONE'))
            self.sync_completed_signal.emit()
            return
            
        from const.dashboard import clean_text

        for uid in user_ids:
            try:
                channel = self.bot.get_channel(int(uid))
                if not channel:
                    try: channel = await self.bot.fetch_channel(int(uid))
                    except: pass
                if channel:
                    avatar_path = ""
                    if hasattr(channel, 'guild') and channel.guild.icon:
                        filepath = os.path.join(IMAGE_DIR, f"guild_{channel.guild.id}.png")
                        if not os.path.exists(filepath): await channel.guild.icon.save(filepath)
                        avatar_path = filepath
                    self.avatar_updated_signal.emit(str(uid), avatar_path)
                else:
                    user = await self.bot.fetch_user(int(uid))
                    if user:
                        avatar_path = await self.get_avatar_path(user)
                        self.avatar_updated_signal.emit(str(uid), avatar_path)
            except: pass
            current_task += 1
            pct = int((current_task / total_tasks) * 100)
            self.progress_signal.emit(pct, t('SYNC_DL_AVATAR', uid))

        for chat_id_str, last_msg_id_str in sync_data.items():
            try:
                target_id = int(chat_id_str)
                channel = self.bot.get_channel(target_id)
                if not channel:
                    try: channel = await self.bot.fetch_channel(target_id)
                    except: pass
                if channel:
                    avatar_path = ""
                    if hasattr(channel, 'guild') and channel.guild.icon:
                        filepath = os.path.join(IMAGE_DIR, f"guild_{channel.guild.id}.png")
                        if not os.path.exists(filepath): await channel.guild.icon.save(filepath)
                        avatar_path = filepath
                    if last_msg_id_str:
                        after_obj = discord.Object(id=int(last_msg_id_str))
                        try:
                            async for msg in channel.history(limit=20, after=after_obj, oldest_first=True):
                                local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                                image_path = ""
                                if msg.attachments:
                                    for att in msg.attachments:
                                        if att.content_type and att.content_type.startswith('image/'):
                                            filepath = os.path.join(IMAGE_DIR, f"{msg.id}_{att.filename}")
                                            if not os.path.exists(filepath): await att.save(filepath)
                                            image_path = filepath
                                            break
                                is_self = (msg.author == self.bot.user)
                                s_name = "Bot" if is_self else clean_text(msg.author.name)
                                self.incoming_msg_signal.emit(str(channel.id), f"#{clean_text(channel.name)}", s_name, msg.content, local_time, str(msg.id), image_path, avatar_path)
                        except: pass
                    continue
                user = await self.bot.fetch_user(target_id)
                if user:
                    dm_channel = user.dm_channel or await user.create_dm()
                    avatar_path = await self.get_avatar_path(user)
                    if last_msg_id_str:
                        after_obj = discord.Object(id=int(last_msg_id_str))
                        async for msg in dm_channel.history(limit=20, after=after_obj, oldest_first=True):
                            local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                            image_path = ""
                            if msg.attachments:
                                for att in msg.attachments:
                                    if att.content_type and att.content_type.startswith('image/'):
                                        filepath = os.path.join(IMAGE_DIR, f"{msg.id}_{att.filename}")
                                        if not os.path.exists(filepath): await att.save(filepath)
                                        image_path = filepath
                                        break
                            is_self = (msg.author == self.bot.user)
                            s_name = "Bot" if is_self else clean_text(msg.author.name)
                            self.incoming_msg_signal.emit(str(user.id), clean_text(user.name), s_name, msg.content, local_time, str(msg.id), image_path, avatar_path)
            except: pass
            current_task += 1
            pct = int((current_task / total_tasks) * 100)
            self.progress_signal.emit(pct, t('SYNC_UP_MSG'))
        self.progress_signal.emit(100, t('SYNC_DONE'))
        self.sync_completed_signal.emit()

    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.bot.start(self.token))
        except: pass

    def send_message_to_discord(self, target_id, text):
        if self.loop and target_id: asyncio.run_coroutine_threadsafe(self._async_send(target_id, text), self.loop)

    async def _async_send(self, target_id, text):
        try:
            channel = self.bot.get_channel(int(target_id))
            if not channel:
                try: channel = await self.bot.fetch_channel(int(target_id))
                except: pass
            if channel:
                if isinstance(channel, discord.CategoryChannel): return
                try:
                    sent_msg = await channel.send(text)
                    local_time = sent_msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                    self.message_sent_signal.emit(str(target_id), text, local_time, str(sent_msg.id), "", t('SENT'))
                except: pass
                return
            user = await self.bot.fetch_user(int(target_id))
            if user:
                sent_msg = await user.send(text)
                local_time = sent_msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                self.message_sent_signal.emit(str(target_id), text, local_time, str(sent_msg.id), "", t('SENT'))
        except: pass

    def delete_message_on_discord(self, user_id, msg_id):
        if self.loop and user_id and msg_id: asyncio.run_coroutine_threadsafe(self._async_delete_msg(user_id, msg_id), self.loop)

    async def _async_delete_msg(self, target_id, msg_id):
        try:
            channel = self.bot.get_channel(int(target_id))
            if not channel:
                try: channel = await self.bot.fetch_channel(int(target_id))
                except: pass
            if channel:
                msg = await channel.fetch_message(int(msg_id))
                await msg.delete()
                return
            user = await self.bot.fetch_user(int(target_id))
            if user:
                dm_channel = user.dm_channel or await user.create_dm()
                msg = await dm_channel.fetch_message(int(msg_id))
                await msg.delete()
        except: pass

    def search_user_by_id(self, target_id):
        if self.loop and target_id: asyncio.run_coroutine_threadsafe(self._async_fetch_user(target_id), self.loop)

    async def _async_fetch_user(self, target_id):
        try:
            from const.dashboard import clean_text
            channel = self.bot.get_channel(int(target_id))
            if not channel:
                try: channel = await self.bot.fetch_channel(int(target_id))
                except: pass
            if channel:
                avatar_path = ""
                if hasattr(channel, 'guild') and channel.guild.icon:
                    avatar_path = os.path.join(IMAGE_DIR, f"guild_{channel.guild.id}.png")
                    if not os.path.exists(avatar_path): await channel.guild.icon.save(avatar_path)
                chat_name = f"#{clean_text(channel.name)}"
                self.user_fetched_signal.emit(str(channel.id), chat_name, avatar_path)
                if isinstance(channel, discord.CategoryChannel): return
                history_data = []
                try:
                    if hasattr(channel, 'history'):
                        async for msg in channel.history(limit=50):
                            local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                            is_self = (msg.author == self.bot.user)
                            s_name = "Bot" if is_self else clean_text(msg.author.name)
                            hist_image_path = ""
                            if msg.attachments:
                                for att in msg.attachments:
                                    if att.content_type and att.content_type.startswith('image/'):
                                        hist_filepath = os.path.join(IMAGE_DIR, f"{msg.id}_{att.filename}")
                                        if not os.path.exists(hist_filepath): await att.save(hist_filepath)
                                        hist_image_path = hist_filepath
                                        break
                            history_data.append({
                                "sender": s_name, "text": msg.content, "time": local_time,
                                "is_self": is_self, "msg_id": str(msg.id), "image_path": hist_image_path,
                                "status": t('SENT') if is_self else t('READ')
                            })
                except: pass
                history_data.sort(key=lambda x: int(x['msg_id']))
                self.history_signal.emit(str(channel.id), chat_name, avatar_path, history_data)
                return
            user = await self.bot.fetch_user(int(target_id))
            if user:
                avatar_path = await self.get_avatar_path(user)
                self.user_fetched_signal.emit(str(user.id), clean_text(user.name), avatar_path)
                dm_channel = user.dm_channel or await user.create_dm()
                history_data = []
                async for msg in dm_channel.history(limit=50):
                    local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                    is_self = (msg.author == self.bot.user)
                    s_name = "Bot" if is_self else clean_text(msg.author.name)
                    hist_image_path = ""
                    if msg.attachments:
                        for att in msg.attachments:
                            if att.content_type and att.content_type.startswith('image/'):
                                hist_filepath = os.path.join(IMAGE_DIR, f"{msg.id}_{att.filename}")
                                if not os.path.exists(hist_filepath): await att.save(hist_filepath)
                                hist_image_path = hist_filepath
                                break
                    history_data.append({
                        "sender": s_name, "text": msg.content, "time": local_time,
                        "is_self": is_self, "msg_id": str(msg.id), "image_path": hist_image_path,
                        "status": t('SENT') if is_self else t('READ')
                    })
                history_data.sort(key=lambda x: int(x['msg_id']))
                self.history_signal.emit(str(user.id), clean_text(user.name), avatar_path, history_data)
        except: pass

    def handle_upload_local_image(self, file_path, img_type, user_id, old_url=None):
        if self.loop: asyncio.run_coroutine_threadsafe(self._async_upload_img(file_path, img_type, user_id, old_url), self.loop)

    async def _async_upload_img(self, file_path, img_type, user_id, old_url):
        try:
            sb = get_supabase()
            res = await asyncio.to_thread(lambda: sb.table('application').select('quote').eq('user_id', str(user_id)).execute())
            mnv = "UNKNOWN"
            if res.data:
                ext = extract_quote_data(res.data[0].get('quote', ''))
                if ext['mnv']: mnv = ext['mnv']

            storage_channel = self.bot.get_channel(1489211278109970613) 
            if not storage_channel: 
                try: storage_channel = await self.bot.fetch_channel(1489211278109970613)
                except: pass
            
            if storage_channel:
                thread = discord.utils.get(storage_channel.threads, name=mnv)
                if not thread:
                    try: thread = await storage_channel.create_thread(name=mnv, type=discord.ChannelType.private_thread)
                    except: thread = await storage_channel.create_thread(name=mnv, type=discord.ChannelType.public_thread)
                
                if old_url and "attachments/" in old_url:
                    try:
                        msg_id = int(old_url.split('/')[-2])
                        old_msg = await thread.fetch_message(msg_id)
                        if old_msg: await old_msg.delete()
                    except: pass
                    
                msg = await thread.send(content=f"Ảnh {img_type.replace('gallery_', '').upper()}", file=discord.File(file_path))
                url = msg.attachments[0].url
                self.image_uploaded_to_discord.emit(url, img_type, user_id)
        except: pass

    def handle_sync_draft(self, user_id, data):
        if self.loop: asyncio.run_coroutine_threadsafe(self._async_sync_draft(user_id, data), self.loop)

    async def find_application_thread(self, display_id):
        for guild in self.bot.guilds:
            for thread in guild.threads:
                if f"#{display_id}" in thread.name:
                    return thread
        return None

    async def _async_sync_draft(self, user_id_str, data):
        try:
            display_id = data.get('display_id', '01')
            thread = await self.find_application_thread(display_id)
            if thread:
                embed = await build_profile_embed(self.bot, user_id_str, data, is_public=False)
                async for msg in thread.history(limit=50):
                    if msg.author == self.bot.user and msg.embeds:
                        await msg.edit(embed=embed)
                        break
                                
            msg_ids_str = data.get('msg_ids', '')
            if msg_ids_str:
                for pair in msg_ids_str.split(','):
                    try:
                        c_id, m_id = pair.split('-')
                        channel = self.bot.get_channel(int(c_id))
                        if not channel:
                            try: channel = await self.bot.fetch_channel(int(c_id))
                            except: pass
                        if channel:
                            ctype = 'tamsu'
                            c_id_int = int(c_id)
                            if c_id_int == get_env_int('TAROT_CHANNEL_ID', 0): ctype = 'tarot'
                            elif c_id_int == get_env_int('GAME_CHANNEL_ID', 0): ctype = 'game'
                            elif c_id_int == get_env_int('HAT_HO_CHANNEL_ID', 0): ctype = 'hatho'
                            
                            public_embed = await build_profile_embed(self.bot, user_id_str, data, is_public=True, channel_type=ctype)
                            msg = await channel.fetch_message(int(m_id))
                            view = PublicProfileView(data, channel_type=ctype)
                            await msg.edit(embed=public_embed, view=view)
                    except: pass
        except: pass

    def handle_update_staff(self, user_id, data):
        if self.loop: asyncio.run_coroutine_threadsafe(self._async_update_staff(user_id, data), self.loop)

    async def _async_update_staff(self, user_id_str, data):
        try:
            sb = get_supabase()
            old_res = sb.table('application').select('*').eq('user_id', str(user_id_str)).execute()
            if not old_res.data:
                self.staff_update_success_signal.emit()
                return
            old_data = old_res.data[0]

            ext = extract_quote_data(data.get('quote', ''))
            mnv = ext['mnv']

            try:
                old_img_urls = set([img['url'] for img in json.loads(old_data.get('images', '[]')) if isinstance(img, dict)] + [old_data.get('avatar', '')])
            except: old_img_urls = set()
            try:
                new_img_urls = set([img['url'] for img in json.loads(data.get('images', '[]')) if isinstance(img, dict)] + [data.get('avatar', '')])
            except: new_img_urls = set()
            
            deleted_urls = old_img_urls - new_img_urls
            storage_channel = self.bot.get_channel(1489211278109970613)
            if storage_channel:
                thread = discord.utils.get(storage_channel.threads, name=mnv)
                if thread:
                    for u in deleted_urls:
                        if u and "attachments/" in u:
                            try:
                                msg_id = int(u.split('/')[-2])
                                old_msg = await thread.fetch_message(msg_id)
                                if old_msg: await old_msg.delete()
                            except: pass

            role = data.get('role', 'princess')
            old_role = old_data.get('role', 'princess')
            
            new_id = data.get('display_id', '01')
            
            dich_vu = data.get('dich_vu', '')
            if 'Tarot' in dich_vu: prefix = 'A'
            elif 'Chơi game' in dich_vu: prefix = 'K'
            elif 'Hát hò' in dich_vu: prefix = 'N'
            elif role == 'princess': prefix = 'H'
            else: prefix = 'V'
            
            if new_id[0] != prefix:
                res = sb.table('application').select('display_id').like('display_id', f'{prefix}%').execute()
                ids = [int(r['display_id'][1:]) for r in res.data if r['display_id'][1:].isdigit()]
                new_id = f"{prefix}{max(ids) + 1:02d}" if ids else f"{prefix}01"
                data['display_id'] = new_id

            old_dich_vu = old_data.get('dich_vu', '')
            new_dich_vu = data.get('dich_vu', '')
            msg_ids_str = old_data.get('msg_ids', '')
            
            if role != old_role or old_dich_vu != new_dich_vu:
                if msg_ids_str:
                    for pair in msg_ids_str.split(','):
                        try:
                            c_id, m_id = pair.split('-')
                            channel = self.bot.get_channel(int(c_id))
                            if not channel:
                                try: channel = await self.bot.fetch_channel(int(c_id))
                                except: pass
                            if channel:
                                msg = await channel.fetch_message(int(m_id))
                                await msg.delete()
                        except: pass
                
                c_configs = [
                    (get_env_int('PRINCESS_CHANNEL_ID', 1485260539054788628) if role == 'princess' else get_env_int('PRINCE_CHANNEL_ID', 1485260557744607252), 'tamsu'),
                    (get_env_int('TAROT_CHANNEL_ID', 1485294194883956897), 'tarot') if 'Tarot' in new_dich_vu else None,
                    (get_env_int('GAME_CHANNEL_ID', 1485294145990819840), 'game') if 'Chơi game' in new_dich_vu else None,
                    (get_env_int('HAT_HO_CHANNEL_ID', 1486700085986459708), 'hatho') if 'Hát hò' in new_dich_vu else None
                ]

                new_msg_ids = []
                for cfg in c_configs:
                    if not cfg: continue
                    cid, ctype = cfg
                    if cid == 0: continue
                    channel = self.bot.get_channel(cid)
                    if not channel:
                        try: channel = await self.bot.fetch_channel(cid)
                        except: pass
                    if channel:
                        try:
                            public_embed = await build_profile_embed(self.bot, user_id_str, data, is_public=True, channel_type=ctype)
                            view = PublicProfileView(data, channel_type=ctype)
                            msg = await channel.send(embed=public_embed, view=view)
                            new_msg_ids.append(f"{cid}-{msg.id}")
                        except: pass
                data['msg_ids'] = ",".join(new_msg_ids)
            else:
                if msg_ids_str:
                    for pair in msg_ids_str.split(','):
                        try:
                            c_id, m_id = pair.split('-')
                            channel = self.bot.get_channel(int(c_id))
                            if not channel:
                                try: channel = await self.bot.fetch_channel(int(c_id))
                                except: pass
                            if channel:
                                ctype = 'tamsu'
                                c_id_int = int(c_id)
                                if c_id_int == get_env_int('TAROT_CHANNEL_ID', 0): ctype = 'tarot'
                                elif c_id_int == get_env_int('GAME_CHANNEL_ID', 0): ctype = 'game'
                                elif c_id_int == get_env_int('HAT_HO_CHANNEL_ID', 0): ctype = 'hatho'
                                
                                public_embed = await build_profile_embed(self.bot, user_id_str, data, is_public=True, channel_type=ctype)
                                msg = await channel.fetch_message(int(m_id))
                                view = PublicProfileView(data, channel_type=ctype)
                                await msg.edit(embed=public_embed, view=view)
                        except: pass

            update_payload = {
                'ho_ten': data.get('ho_ten', ''), 'role': role, 'tuoi': data.get('tuoi', ''),
                'noi_o': data.get('noi_o', ''), 'dich_vu': new_dich_vu, 'game': data.get('game', ''),
                'gia_cam': data.get('gia_cam', ''), 'quote': data.get('quote', ''), 
                'images': data.get('images', ''), 'avatar': data.get('avatar', ''),
                'display_id': data.get('display_id', '01'), 'msg_ids': data.get('msg_ids', '')
            }
            sb.table('application').update(update_payload).eq('user_id', str(user_id_str)).execute()

            thread_id = old_data.get('display_id', '01') if role == old_role else data.get('display_id')
            thread = await self.find_application_thread(thread_id)
            if not thread: thread = await self.find_application_thread(old_data.get('display_id', '01'))
            if thread:
                try: 
                    if role != old_role: await thread.edit(name=f"Hồ Sơ #{data['display_id']}")
                    internal_embed = await build_profile_embed(self.bot, user_id_str, data, is_public=False)
                    async for msg in thread.history(limit=50):
                        if msg.author == self.bot.user and msg.embeds:
                            await msg.edit(embed=internal_embed)
                            break
                except: pass

            self._refresh_members()
            self.staff_update_success_signal.emit()
        except:
            self.staff_update_success_signal.emit() 

    def handle_delete_staff(self, user_id, data):
        if self.loop: asyncio.run_coroutine_threadsafe(self._async_delete_staff(user_id, data), self.loop)

    async def _async_delete_staff(self, user_id_str, data):
        try:
            sb = get_supabase()
            sb.table('application').delete().eq('user_id', str(user_id_str)).execute()
            sb.table('drafts').delete().eq('user_id', str(user_id_str)).execute()

            ext = extract_quote_data(data.get('quote', ''))
            mnv = ext['mnv']

            msg_ids_str = data.get('msg_ids', '')
            if msg_ids_str:
                for pair in msg_ids_str.split(','):
                    try:
                        c_id, m_id = pair.split('-')
                        channel = self.bot.get_channel(int(c_id))
                        if not channel:
                            try: channel = await self.bot.fetch_channel(int(c_id))
                            except: pass
                        if channel:
                            msg = await channel.fetch_message(int(m_id))
                            await msg.delete()
                    except: pass

            display_id = data.get('display_id', '01')
            thread = await self.find_application_thread(display_id)
            if thread:
                try: await thread.edit(name=f"Đã xóa #{display_id}")
                except: pass

            storage_channel = self.bot.get_channel(1489211278109970613)
            if storage_channel:
                img_thread = discord.utils.get(storage_channel.threads, name=mnv)
                if img_thread:
                    try: await img_thread.delete()
                    except: pass

            self.staff_updated_signal.emit()
        except: pass

    def handle_approve_app(self, user_id, data):
        if self.loop: asyncio.run_coroutine_threadsafe(self._async_approve_app(user_id, data), self.loop)

    async def _async_approve_app(self, user_id_str, data):
        sb = get_supabase()
        if not sb: return
        try:
            sb.table('application').update({'status': 'processing'}).eq('user_id', str(user_id_str)).execute()
            
            ext = extract_quote_data(data.get('quote', ''))
            mnv = ext.get('mnv', f"NV_{random.randint(100,999)}")
            
            final_avatar = data.get('avatar', '')
            final_images = data.get('images', '[]')
            
            storage_channel = self.bot.get_channel(1489211278109970613)
            if not storage_channel:
                try: storage_channel = await self.bot.fetch_channel(1489211278109970613)
                except: pass
                
            if storage_channel:
                thread = discord.utils.get(storage_channel.threads, name=mnv)
                if not thread:
                    try: thread = await storage_channel.create_thread(name=mnv, type=discord.ChannelType.private_thread)
                    except: thread = await storage_channel.create_thread(name=mnv, type=discord.ChannelType.public_thread)
                    
                async def transfer_img(url, label):
                    if not url or "attachments/" in url: return url
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(url) as resp:
                                if resp.status == 200:
                                    img_data = await resp.read()
                                    file = discord.File(io.BytesIO(img_data), filename="image.png")
                                    msg = await thread.send(content=f"Ảnh {label}", file=file)
                                    return msg.attachments[0].url
                    except: pass
                    return url
                    
                try:
                    final_avatar = await transfer_img(data.get('avatar', ''), 'AVATAR')
                    try: img_list = json.loads(data.get('images', '[]'))
                    except: img_list = []
                    
                    new_img_list = []
                    for img in img_list:
                        if isinstance(img, dict) and 'url' in img:
                            new_u = await transfer_img(img['url'], img.get('type', 'general').upper())
                            new_img_list.append({'url': new_u, 'type': img.get('type')})
                    final_images = json.dumps(new_img_list)
                except: pass

            role = data.get('role', 'princess')
            dich_vu = data.get('dich_vu', '')
            
            if 'Tarot' in dich_vu: prefix = 'A'
            elif 'Chơi game' in dich_vu: prefix = 'K'
            elif 'Hát hò' in dich_vu: prefix = 'N'
            elif role == 'princess': prefix = 'H'
            else: prefix = 'V'
            
            res = sb.table('application').select('display_id').like('display_id', f'{prefix}%').execute()
            ids = [int(r['display_id'][1:]) for r in res.data if r['display_id'][1:].isdigit()]
            new_id = f"{prefix}{max(ids) + 1:02d}" if ids else f"{prefix}01"

            sb.table('application').update({
                'display_id': new_id, 
                'status': '',
                'avatar': final_avatar,
                'images': final_images
            }).eq('user_id', str(user_id_str)).execute()

            display_id = data.get('display_id', '01') 
            app_thread = await self.find_application_thread(display_id)
            if app_thread:
                try: await app_thread.edit(name=f"Hồ Sơ #{new_id}")
                except: pass
                msg = await app_thread.send("Chúc mừng bạn đã trúng tuyển!")
                try:
                    if self.loop:
                        local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                        self.incoming_msg_signal.emit(str(app_thread.id), f"#{app_thread.name}", "Bot", msg.content, local_time, str(msg.id), "", "")
                except: pass

            c_configs = [
                (get_env_int('PRINCESS_CHANNEL_ID', 1485260539054788628) if role == 'princess' else get_env_int('PRINCE_CHANNEL_ID', 1485260557744607252), 'tamsu'),
                (get_env_int('TAROT_CHANNEL_ID', 1485294194883956897), 'tarot') if 'Tarot' in data.get('dich_vu', '') else None,
                (get_env_int('GAME_CHANNEL_ID', 1485294145990819840), 'game') if 'Chơi game' in data.get('dich_vu', '') else None,
                (get_env_int('HAT_HO_CHANNEL_ID', 1486700085986459708), 'hatho') if 'Hát hò' in data.get('dich_vu', '') else None
            ]

            msg_ids = []
            for cfg in c_configs:
                if not cfg: continue
                cid, ctype = cfg
                if cid == 0: continue
                channel = self.bot.get_channel(cid)
                if not channel:
                    try: channel = await self.bot.fetch_channel(cid)
                    except: pass
                if channel:
                    try:
                        pub_data = data.copy()
                        pub_data['display_id'] = new_id
                        pub_data['avatar'] = final_avatar
                        pub_data['images'] = final_images
                        public_embed = await build_profile_embed(self.bot, user_id_str, pub_data, is_public=True, channel_type=ctype)
                        view = PublicProfileView(pub_data, channel_type=ctype)
                        msg = await channel.send(embed=public_embed, view=view)
                        msg_ids.append(f"{cid}-{msg.id}")
                    except: pass
            
            if msg_ids:
                sb.table('application').update({'msg_ids': ",".join(msg_ids)}).eq('user_id', str(user_id_str)).execute()

        except:
            try: sb.table('application').update({'status': ''}).eq('user_id', str(user_id_str)).execute()
            except: pass
        finally:
            self._refresh_members()
            self.staff_updated_signal.emit()

    def handle_reject_app(self, user_id, data):
        if self.loop: asyncio.run_coroutine_threadsafe(self._async_reject_app(user_id, data), self.loop)

    async def _async_reject_app(self, user_id_str, data):
        try:
            sb = get_supabase()
            sb.table('application').delete().eq('user_id', str(user_id_str)).execute()
            
            display_id = data.get('display_id', '01')
            thread = await self.find_application_thread(display_id)
            if thread:
                try: await thread.edit(name=f"Hồ Sơ #{display_id}")
                except: pass
                msg = await thread.send("Bạn đã bị loại! Xin cảm ơn!")
                try:
                    if self.loop:
                        local_time = msg.created_at.astimezone().strftime("%d/%m/%Y %H:%M")
                        self.incoming_msg_signal.emit(str(thread.id), f"#{thread.name}", "Bot", msg.content, local_time, str(msg.id), "", "")
                except: pass
        except: pass