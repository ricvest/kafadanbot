import discord
from discord import app_commands
from discord.ext import commands, tasks
from easy_pil import Editor, Canvas, Font, load_image, load_image_async
from PIL import Image
from curl_cffi import requests
import io
import re
import datetime
import asyncio
import json
import os
import random

# 1. INTENTS VE BOT AYARI
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True  
intents.reactions = True  

bot = commands.Bot(command_prefix="!", intents=intents)

# --- ID VE TOKEN AYARLARI ---
GUILD_ID = 726562849308147744 
GELEN_KANAL_ID = 1449796266497278104       # #gelen kanalı ID'si
GIDEN_KANAL_ID = 1449796268917260479       # #giden kanalı ID'si

# LOG VE SOHBET KANALLARI
SEVIYE_LOG_KANAL_ID = 1533164941731823707
DOGUM_GUNU_LOG_KANAL_ID = 1533173645449629718  # Doğum günü log kanalı
GENEL_SOHBET_KANAL_ID = 1449796291747119288    # Kutlamanın yapılacağı Genel Sohbet

# ROLLER
KAYITSIZ_ROL_ID = 1449796182619455488      # Kayıtsız Rolü ID'si
KAYITLI_ROL_ID = 1449796181306769610       # Kayıtlı Üye Rolü ID'si
DOGUM_GUNU_ROL_ID = 1511053669301485879    # Özel Doğum Günü Rolü ID'si
YAYINCI_ROL_ID = 1449796176432861214       # 🎥 Yayıncı / İçerik Üreticisi Rolü ID'si

# YETKİLİ ROLLERİ
KAYIT_YETKILISI_ROL_ID = 1449796156686078116
YETKILI_ROL_ID = 1449796152902947014
BAN_HAMMER_ROL_ID = 1511446135204483194
YONETIM_ROL_ID = 1449796148939329607

# KANALLAR
ISIM_ONAY_KANAL_ID = 1533098909377888436    # İsim Onay Kanalı ID'si
KAYIT_KANAL_ID = 1449796274651140157         # /kayitol komutunun çalışacağı kanal
BOT_KULLANIM_KANAL_ID = 1533102671311933460  # /isimdegistir komutunun çalışacağı kanal
ROL_ALMA_KANAL_ID = 1508985526118518814      # Rol alma kanal ID'si

# MODERASYON & İSTİSNA KANALLARI
MOD_LOG_KANAL_ID = 1513938060507742278       # Moderasyon log kanalı ID'si
LINK_KANAL_ID = 1533126837989801994          # Link paylaşım kanalı
YAYIN_DUYURU_KANAL_ID = 1449796294628606043  # 📢 Yayın/İçerik duyuru kanalı

# DESTEK (TICKET) SİSTEMİ ID'LERİ
DESTEK_YETKILI_ROL_ID = 1512073836290642061  # Destek taleplerini görecek yetkili rol ID'si
TICKET_KATEGORI_ID = 1513376651000418304     # Ticket kanallarının açılacağı kategori ID'si
TICKET_LOG_KANAL_ID = 1512069199365799966    # Kapatılan ticket loglarının gideceği ÖZEL kanal ID'si

# ⚽ TAKIM ROL MAPPING
TAKIM_ROLLER = {
    "gs": 1449796162298183790,
    "fb": 1449796164651188289,
    "bjk": 1449796167486410812,
    "ts": 1449796169625501726
}

# 🎮 OYUN ROL MAPPING
OYUN_ROLLER = {
    "valorant": 1511805214192304198,
    "lol": 1511805507063648438,
    "cs2": 1511805507143471215,
    "minecraft": 1511806609674866759
}

# 🏆 SEVİYE ROL MAPPING
LEVEL_ROLES = {
    5: 1511808056369877142,   # ☕ Çaycı
    10: 1511807635660476566,  # 📜 Kadrolu Eleman
    20: 1511807510192062694,  # 🕶️ Mahalle Muhtarı
    50: 1511807213046595665   # 👑 Laz Ziya / Başkan
}

# 🚫 YASAKLI KELİMELER LİSTESİ
YASAKLI_KELIMELER = ["amk", "aq", "oç", "piç", "yarrak", "sik", "orospu", "piç", "orospu evladı"]

# --- 📊 VERİ YÖNETİMİ ---
LEVEL_FILE = "levels.json"
BIRTHDAY_FILE = "birthdays.json"
cooldowns = {}

def load_levels():
    if not os.path.exists(LEVEL_FILE):
        with open(LEVEL_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(LEVEL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_levels(data):
    with open(LEVEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_birthdays():
    if not os.path.exists(BIRTHDAY_FILE):
        with open(BIRTHDAY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(BIRTHDAY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_birthdays(data):
    with open(BIRTHDAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_next_level_xp(level):
    return 5 * (level ** 2) + 50 * level + 100


# --- YETKİ KONTROL YARDIMCILARI ---
def yetkili_mi(user: discord.Member, yetki_seviyesi: str = "kayit"):
    user_roles = [r.id for r in user.roles]
    
    if YONETIM_ROL_ID in user_roles or user.guild_permissions.administrator:
        return True
    if yetki_seviyesi == "banhammer" and BAN_HAMMER_ROL_ID in user_roles:
        return True
    if yetki_seviyesi == "yetkili" and (BAN_HAMMER_ROL_ID in user_roles or YETKILI_ROL_ID in user_roles):
        return True
    if yetki_seviyesi == "kayit" and (BAN_HAMMER_ROL_ID in user_roles or YETKILI_ROL_ID in user_roles or KAYIT_YETKILISI_ROL_ID in user_roles):
        return True
    
    return False


# --- 🎥 YAYIN DUYURU BUTONU ---
class YayinLinkButton(discord.ui.View):
    def __init__(self, url: str, platform_name: str):
        super().__init__(timeout=None)
        label_text = f"Yayına Katıl ({platform_name})" if "Yayın" in platform_name or "Kick" in platform_name or "Twitch" in platform_name else f"İçeriğe Git ({platform_name})"
        emoji_icon = "🟢" if "Kick" in platform_name else "🎬"
        self.add_item(discord.ui.Button(label=label_text, url=url, style=discord.ButtonStyle.link, emoji=emoji_icon))


# --- 🎬 KICK API YARDIMCISI ---
def get_kick_user_data(username: str):
    """Kick API'sinden yayıncının profil fotoğrafını, banner resmini, canlı başlığını ve gösterim adını çeker."""
    url = f"https://kick.com/api/v7/channels/{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome110", timeout=5)
        if response.status_code == 200:
            data = response.json()
            user_info = data.get("user", {})
            avatar_url = user_info.get("profile_pic")
            display_name = user_info.get("username", username)
            banner_url = data.get("banner_image", {}).get("url") if data.get("banner_image") else None
            stream_title = data.get("livestream", {}).get("session_title") if data.get("livestream") else None
            return avatar_url, banner_url, stream_title, display_name
    except Exception as e:
        print(f"[KICK API HATA] {e}")
    return None, None, None, username


import discord
from discord.ui import View, Button, UserSelect

# --- MARPEL TARZI ÖZEL ODA KONTROL MENÜSÜ ---
from discord.ui import View, Button, UserSelect, Select

class OdaLimitSelect(discord.ui.Select):
    def __init__(self):
        # 1'den 10'a kadar limit seçenekleri oluşturuyoruz
        options = [discord.SelectOption(label=f"{i} Kişi", value=str(i), emoji="👥") for i in range(1, 11)]
        super().__init__(placeholder="Oda limitini seç...", min_values=1, max_values=1, options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Önce kendi ses odanda olmalısın!", ephemeral=True)
            return
        
        kanal = interaction.user.voice.channel
        secilen_limit = int(self.values[0])
        await kanal.edit(user_limit=secilen_limit)
        await interaction.response.send_message(f"👥 Oda limiti başarıyla **{secilen_limit}** kişi olarak ayarlandı!", ephemeral=True)

class OdaKontrolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # 1'den 10'a kadar olan limit menüsünü arayüze ekliyoruz
        self.add_item(OdaLimitSelect())

    @discord.ui.select(cls=UserSelect, placeholder="Odana girebilecek üyeleri seç", min_values=1, max_values=5, row=0)
    async def uye_ekle_select(self, interaction: discord.Interaction, select: UserSelect):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Önce kendi ses odanda olmalısın!", ephemeral=True)
            return
        kanal = interaction.user.voice.channel
        secilen_kisi = select.values[0]
        await kanal.set_permissions(secilen_kisi, connect=True)
        await interaction.response.send_message(f"✅ {secilen_kisi.mention} odana eklendi!", ephemeral=True)

    @discord.ui.button(label="Odayı Kilitle!", style=discord.ButtonStyle.secondary, emoji="🔒", row=1)
    async def kilit_buton(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Önce kendi ses odanda olmalısın!", ephemeral=True)
            return
        kanal = interaction.user.voice.channel
        everyone_rolu = interaction.guild.default_role
        
        # Kilidi açıp kapama mantığı (Zaten kilitliyse açar, değilse kilitler)
        su_anki_izin = kanal.permissions_for(everyone_rolu).connect
        yeni_durum = not su_anki_izin
        
        await kanal.set_permissions(everyone_rolu, connect=yeni_durum)
        if yeni_durum:
            await interaction.response.send_message("🔓 Odanın kilidi açıldı!", ephemeral=True)
        else:
            await interaction.response.send_message("🔒 Odan kilitlendi! Artık kimse giremez.", ephemeral=True)

    @discord.ui.button(label="Odayı Gizle!", style=discord.ButtonStyle.secondary, emoji="🐵", row=1)
    async def gizle_buton(self, interaction: discord.Interaction, button: Button):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ Önce kendi ses odanda olmalısın!", ephemeral=True)
            return
        kanal = interaction.user.voice.channel
        everyone_rolu = interaction.guild.default_role
        
        su_anki_gorus = kanal.permissions_for(everyone_rolu).view_channel
        yeni_durum = not su_anki_gorus
        
        await kanal.set_permissions(everyone_rolu, view_channel=yeni_durum)
        if yeni_durum:
            await interaction.response.send_message("🐵 Odan görünür hale getirildi!", ephemeral=True)
        else:
            await interaction.response.send_message("🐵 Odan gizlendi! Dışarıdan görünmüyor.", ephemeral=True)


# --- 🟢 ÖZEL KICK BANNER GÖRSELİ OLUŞTURUCU ---
async def generate_kick_stream_banner(kick_username: str, member: discord.Member):
    loop = asyncio.get_event_loop()
    avatar_url, banner_url, stream_title, display_name = await loop.run_in_executor(None, get_kick_user_data, kick_username)

    # 1. Arka Plan (Banner)
    if banner_url:
        try:
            bg_image = await load_image_async(banner_url)
            background = Editor(bg_image).resize((1000, 360))
        except Exception:
            background = Editor(Canvas((1000, 360), color="#0b0e0f"))
    else:
        background = Editor(Canvas((1000, 360), color="#0b0e0f"))

    # Karartma Filtresi
    dark_overlay = Canvas((1000, 360), color=(0, 0, 0, 150))
    background.paste(Editor(dark_overlay), (0, 0))

    # 2. Yayıncının Kendi Profil Fotoğrafı ve Yeşil Çerçevesi
    if avatar_url:
        try:
            profile_img = await load_image_async(avatar_url)
        except Exception:
            profile_img = Canvas((180, 180), color="#53FC18").image
    else:
        discord_avatar = member.avatar.url if member.avatar else member.default_avatar.url
        profile_img = await load_image_async(str(discord_avatar))

    # Kick Yeşili Çerçeveli Yuvarlak Avatar
    border = Canvas((196, 196), color="#53FC18")
    border_editor = Editor(border).circle_image()
    profile = Editor(profile_img).resize((180, 180)).circle_image()

    background.paste(border_editor, (52, 82))
    background.paste(profile, (60, 90))

    # 3. Yazılar ve Detaylar
    font_title = Font.poppins(size=36, variant="bold")
    font_name = Font.poppins(size=42, variant="bold")
    font_sub = Font.poppins(size=24, variant="regular")

    background.text((280, 60), "🟢 KICK CANLI YAYINI", font=font_title, color="#53FC18")
    background.text((280, 115), str(display_name).upper(), font=font_name, color="#FFFFFF")
    background.text((280, 175), f"@{kick_username}", font=font_sub, color="#AAAAAA")

    if stream_title:
        short_title = stream_title[:42] + "..." if len(stream_title) > 42 else stream_title
        background.text((280, 220), f'"{short_title}"', font=font_sub, color="#DDDDDD")
    else:
        background.text((280, 220), "Kafadan Kontak Ailesi İyi Seyirler Diler!", font=font_sub, color="#CCCCCC")

    file_bytes = io.BytesIO()
    background.image.save(file_bytes, format="PNG")
    file_bytes.seek(0)
    
    file = discord.File(fp=file_bytes, filename="kick_stream.png")
    return file, stream_title, avatar_url, display_name


# --- 🎥 GENEL YAYIN DUYURU BANNER GÖRSELİ (TWITCH, YT, TIKTOK VB.) ---
async def generate_stream_banner(member: discord.Member, platform_name: str):
    background = Editor(Image.new("RGBA", (1000, 360), (20, 20, 25)))
    card_box = Image.new("RGBA", (940, 300), (30, 30, 38))
    background.paste(Editor(card_box), (30, 30))

    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    avatar_image = await load_image_async(str(avatar_url))
    avatar = Editor(avatar_image).resize((180, 180)).circle_image()
    background.paste(avatar, (60, 90))

    font_title = Font.poppins(size=38, variant="bold")
    font_name = Font.poppins(size=42, variant="bold")
    font_sub = Font.poppins(size=26, variant="regular")

    user_display = member.global_name if member.global_name else member.name

    if "Twitch" in platform_name:
        title_color = (145, 70, 255)
    elif "YouTube" in platform_name:
        title_color = (255, 0, 0)
    elif "TikTok" in platform_name:
        title_color = (254, 44, 85)
    else:
        title_color = (255, 170, 0)

    background.text((270, 65), f"🔴 {platform_name.upper()} CANLI / YENİ İÇERİK", font=font_title, color=title_color)
    background.text((270, 125), user_display, font=font_name, color=(255, 255, 255))
    background.text((270, 185), f"@{member.name}", font=font_sub, color=(180, 180, 180))
    background.text((270, 230), "Kafadan Kontak Ailesi İyi Seyirler Diler!", font=font_sub, color=(200, 200, 200))

    file = discord.File(fp=background.image_bytes, filename="stream.png")
    return file


# --- 🎂 DOĞUM GÜNÜ BARKOD GÖRSELİ ---
async def generate_birthday_banner(member: discord.Member):
    background = Editor(Image.new("RGBA", (1000, 400), (45, 20, 50)))
    card_box = Image.new("RGBA", (940, 340), (25, 10, 30))
    background.paste(Editor(card_box), (30, 30))

    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    avatar_image = await load_image_async(str(avatar_url))
    avatar = Editor(avatar_image).resize((200, 200)).circle_image()
    background.paste(avatar, (60, 100))

    font_title = Font.poppins(size=40, variant="bold")
    font_name = Font.poppins(size=45, variant="bold")
    font_sub = Font.poppins(size=26, variant="regular")

    user_display = member.global_name if member.global_name else member.name

    background.text((290, 70), "🎉 İYİ Kİ DOĞDUN! 🎂", font=font_title, color=(255, 215, 0))
    background.text((290, 135), user_display, font=font_name, color=(255, 255, 255))
    background.text((290, 200), f"@{member.name}", font=font_sub, color=(200, 180, 220))
    background.text((290, 250), "Kafadan Kontak Ailesi Mutlu Yıllar Diler!", font=font_sub, color=(255, 105, 180))

    file = discord.File(fp=background.image_bytes, filename="birthday.png")
    return file


# --- 🎂 ARKA PLAN DOĞUM GÜNÜ KONTROLÜ ---
@tasks.loop(hours=24)
async def birthday_checker():
    now = datetime.datetime.now()
    today_str = now.strftime("%d-%m")
    
    birthdays = load_birthdays()
    levels_data = load_levels()

    for guild in bot.guilds:
        sohbet_kanal = guild.get_channel(GENEL_SOHBET_KANAL_ID)
        log_kanal = guild.get_channel(DOGUM_GUNU_LOG_KANAL_ID)
        bday_role = guild.get_role(DOGUM_GUNU_ROL_ID)

        if not sohbet_kanal:
            continue
            
        for user_id, bday in birthdays.items():
            if bday == today_str:
                member = guild.get_member(int(user_id))
                if member:
                    if bday_role and bday_role not in member.roles:
                        try:
                            await member.add_roles(bday_role, reason="Doğum günü hediyesi özel rol.")
                        except discord.Forbidden:
                            print("⚠️ Doğum günü rolü verme yetkisi yetersiz.")

                    if user_id not in levels_data:
                        levels_data[user_id] = {"xp": 500, "level": 1}
                    else:
                        levels_data[user_id]["xp"] += 500
                    save_levels(levels_data)

                    banner = await generate_birthday_banner(member)
                    embed = discord.Embed(
                        title="🎂 BUGÜN BİRİNİN DOĞUM GÜNÜ!",
                        description=f"Bugün sunucumuzun değerli üyesi {member.mention} doğdu! 🎉\n\n🎁 **Doğum Günü Hediyeleri:**\n• Özel {bday_role.mention if bday_role else 'Doğum Günü'} Rolü Verildi!\n• Hesabına **+500 XP** eklendi!\n\nMutlu yıllar dileriz, iyi ki varsın! 🥳🎈",
                        color=discord.Color.magenta()
                    )
                    embed.set_image(url="attachment://birthday.png")
                    
                    # Doğum günü mesajı gönderilir gönderilmez otomatik 🎂 tepkisi ekleniyor
                    gonderilen_mesaj = await sohbet_kanal.send(content=f"🎉 {member.mention}", file=banner, embed=embed)
                    await gonderilen_mesaj.add_reaction("🎂")

                    if log_kanal:
                        log_embed = discord.Embed(
                            title="🎂 Doğum Günü İşlemi Gerçekleşti",
                            description=f"**Kullanıcı:** {member.mention} (`{member.id}`)\n**Tarih:** `{today_str}`\n**Verilen Rol:** {bday_role.mention if bday_role else 'Bulunamadı'}\n**XP Hediyesi:** +500 XP",
                            color=discord.Color.blue(),
                            timestamp=datetime.datetime.now(datetime.timezone.utc)
                        )
                        await log_kanal.send(embed=log_embed)

@birthday_checker.before_loop
async def before_birthday_checker():
    await bot.wait_until_ready()


# --- 🎟️ KALICI DESTEK (TICKET) SİSTEMİ VIEW'LARI ---
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Talebi Kapat", style=discord.ButtonStyle.red, custom_id="ticket_close_btn", emoji="🔒")
    async def ticket_kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_roles = [r.id for r in interaction.user.roles]
        if DESTEK_YETKILI_ROL_ID not in user_roles and YONETIM_ROL_ID not in user_roles and not interaction.guild_permissions.administrator:
            if not interaction.channel.name.startswith("ticket-"):
                await interaction.response.send_message("❌ Bu işlemi yapmaya yetkiniz yok!", ephemeral=True)
                return

        await interaction.response.send_message("🔒 Destek talebi kapatılıyor... Kanal 5 saniye içinde silinecektir.")
        
        log_kanal = interaction.guild.get_channel(TICKET_LOG_KANAL_ID)
        if log_kanal and log_kanal.id != interaction.channel_id:
            log_embed = discord.Embed(
                title="🎟️ Destek Talebi Kapatıldı",
                description=f"**Kanal:** `{interaction.channel.name}`\n**Kapatan Yetkili:** {interaction.user.mention}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            await log_kanal.send(embed=log_embed)

        await asyncio.sleep(5)
        await interaction.channel.delete()


class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="ticket_option_select",
        placeholder="Destek almak istediğiniz konuyu seçin...",
        options=[
            discord.SelectOption(label="Teknik Destek / Hata", description="Sunucu veya bot ile ilgili sorunlar", emoji="🛠️", value="teknik"),
            discord.SelectOption(label="Şikayet / Yetkili Bildirimi", description="Bir üye veya yetkili hakkında şikayet", emoji="🛡️", value="sikayet"),
            discord.SelectOption(label="Genel Soru / Bilgi", description="Sunucu hakkında merak ettikleriniz", emoji="❓", value="genel")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user
        kategori = guild.get_channel(TICKET_KATEGORI_ID)
        destek_rol = guild.get_role(DESTEK_YETKILI_ROL_ID)

        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
        if existing_channel:
            await interaction.followup.send(f"⚠️ Zaten açık bir destek talebiniz bulunuyor: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if destek_rol:
            overwrites[destek_rol] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{member.name}",
            category=kategori,
            overwrites=overwrites
        )

        await interaction.followup.send(f"✅ Destek talebiniz oluşturuldu: {ticket_channel.mention}", ephemeral=True)

        konu_baslik = {
            "teknik": "🛠️ Teknik Destek / Hata Bildirimi",
            "sikayet": "🛡️ Şikayet / Yetkili Bildirimi",
            "genel": "❓ Genel Soru / Bilgi"
        }.get(select.values[0], "Destek Talebi")

        embed = discord.Embed(
            title=f"📩 {konu_baslik}",
            description=f"Hoş geldin {member.mention},\n\nYetkililerimiz seninle ilgilenecektir. Lütfen bu süre zarfında talebini ve detaylarını açıkça yaz.\n\n**Destek Ekibi:** {destek_rol.mention if destek_rol else 'Yetkililer'}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Kafadan Kontak Destek Sistemi", icon_url=guild.icon.url if guild.icon else None)

        await ticket_channel.send(embed=embed, view=TicketControlView())


@bot.event
async def on_ready():
    bot.add_view(TicketSelectView())
    bot.add_view(TicketControlView())
    
    if not birthday_checker.is_running():
        birthday_checker.start()

    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    
    print(f"✅ {bot.user} başarıyla bağlandı!")
    print(f"🔄 {len(synced)} adet komut sunucuya senkronize edildi!")


# --- 🛡️ OTOMATİK KORUMA, LINK & YAYIN DUYURU SİSTEMİ ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    icerek = message.content.lower()
    link_regex = r"(https?://[^\s]+)|(discord\.gg/[^\s]+)|(discord\.com/invite/[^\s]+)"
    found_links = re.findall(link_regex, message.content)
    has_link = bool(found_links)

    # 📢 1. PRO YAYIN & İÇERİK DUYURU SİSTEMİ
    if message.channel.id == YAYIN_DUYURU_KANAL_ID:
        user_roles = [r.id for r in message.author.roles]

        # Yayıncı Rolü veya Yetkili Kontrolü
        if YAYINCI_ROL_ID not in user_roles and not yetkili_mi(message.author, "yetkili"):
            await message.delete()
            yayin_rolu = message.guild.get_role(YAYINCI_ROL_ID)
            rol_adi = yayin_rolu.mention if yayin_rolu else "Yayıncı"
            await message.channel.send(f"⚠️ {message.author.mention}, bu kanalda sadece {rol_adi} rolüne sahip üyeler paylaşım yapabilir!", delete_after=5)
            return

        if not has_link:
            await message.delete()
            await message.channel.send(f"⚠️ {message.author.mention}, bu kanala sadece yayın/video linki paylaşabilirsiniz!", delete_after=5)
            return

        # Linki Algıla
        match = re.search(r"(https?://[^\s]+)", message.content)
        stream_link = match.group(0) if match else message.content

        # 🟢 A) KICK İÇİN ÖZEL API & BANNER SİSTEMİ
        if "kick.com/" in stream_link.lower():
            kick_match = re.search(r"kick\.com/([a-zA-Z0-9_]+)", stream_link)
            if kick_match:
                kick_username = kick_match.group(1)
                
                await message.delete() # Ham link mesajını sil

                # Banner ve Kick Profil/Yayın Bilgilerini Çek
                banner, stream_title, avatar_url, display_name = await generate_kick_stream_banner(kick_username, message.author)

                streamer_title_name = display_name if display_name else kick_username

                desc_text = f"Hey! **{streamer_title_name}** şu an **Kick** üzerinde canlı yayında!\n\n*(Yayıncıya destek olmak için yayına katılmayı ve sohbet etmeyi unutmayın!)*"
                if stream_title:
                    desc_text += f"\n\n📝 **Yayın Başlığı:** {stream_title}"

                embed = discord.Embed(
                    title="🟢 KICK CANLI YAYINI BAŞLADI!",
                    description=desc_text,
                    color=0x53FC18, # Kick Yeşili
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )

                # EMBED YAZAR ALANINA YAYINCININ PROFIL RESMINI KOYUYORUZ
                if avatar_url:
                    embed.set_author(name=streamer_title_name, icon_url=avatar_url)
                else:
                    embed.set_author(name=streamer_title_name)

                embed.set_image(url="attachment://kick_stream.png")
                embed.set_footer(text="Kafadan Kontak Yayın Duyuru Sistemi", icon_url=message.guild.icon.url if message.guild.icon else None)

                # OTOMATİK @everyone ETİKETİ İLE MESAJI AT
                await message.channel.send(
                    content=f"📢 @everyone **{streamer_title_name}** Kick'te canlı yayın açtı!",
                    file=banner,
                    embed=embed,
                    view=YayinLinkButton(url=f"https://kick.com/{kick_username}", platform_name="Kick")
                )
                return

        # 📺 B) DİĞER PLATFORMLAR (TWITCH, YOUTUBE, TIKTOK VB.)
        platform_name = "Yayın / İçerik"
        embed_color = discord.Color.gold()

        if "twitch.tv" in stream_link.lower():
            platform_name = "Twitch Yayını"
            embed_color = discord.Color.purple()
        elif "youtube.com" in stream_link.lower() or "youtu.be" in stream_link.lower():
            platform_name = "YouTube Videosu / Yayın"
            embed_color = discord.Color.red()
        elif "tiktok.com" in stream_link.lower():
            platform_name = "TikTok İçeriği"
            embed_color = discord.Color.from_rgb(254, 44, 85)

        # Orijinal ham mesajı sil
        await message.delete()

        # Banner Afişi Hazırla
        banner = await generate_stream_banner(message.author, platform_name)

        embed = discord.Embed(
            title=f"🔴 {platform_name.upper()} BAŞLADI!",
            description=f"Hey! **{message.author.display_name}** şu an canlı yayında veya yeni bir içerik yükledi!\n\n*(Yayıncıya destek olmak için yayına katılmayı ve sohbet etmeyi unutmayın!)*",
            color=embed_color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.set_image(url="attachment://stream.png")
        embed.set_footer(text="Kafadan Kontak Yayın Duyuru Sistemi", icon_url=message.guild.icon.url if message.guild.icon else None)

        # Butonlu Kartı Gönder (@everyone Etiketi İle)
        await message.channel.send(
            content=f"📢 @everyone **{message.author.display_name}** {platform_name.lower()} başlattı!",
            file=banner,
            embed=embed,
            view=YayinLinkButton(url=stream_link, platform_name=platform_name)
        )
        return

    # 🛡️ 2. GENEL SUNUCU KORUMASI VE DİĞER KANALLAR
    if not yetkili_mi(message.author, "yetkili"):
        if message.channel.id == LINK_KANAL_ID:
            if not has_link:
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}, bu kanala sadece link/bağlantı içeren mesajlar atabilirsiniz!", delete_after=5)
                return
        else:
            if has_link:
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}, bu kanalda link/reklam paylaşımı yasaktır!", delete_after=5)
                log_kanal = message.guild.get_channel(MOD_LOG_KANAL_ID)
                if log_kanal:
                    embed = discord.Embed(title="🛡️ Reklam / Link Engellendi", color=discord.Color.orange())
                    embed.add_field(name="Kullanıcı", value=message.author.mention)
                    embed.add_field(name="Kanal", value=message.channel.mention)
                    embed.add_field(name="Mesaj", value=message.content, inline=False)
                    await log_kanal.send(embed=embed)
                return

        for kelime in YASAKLI_KELIMELER:
            if re.search(r'\b' + re.escape(kelime) + r'\b', icerek):
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}, sunucuda küfür / argo kullanımı yasaktır!", delete_after=5)
                log_kanal = message.guild.get_channel(MOD_LOG_KANAL_ID)
                if log_kanal:
                    embed = discord.Embed(title="🛡️ Küfür Engellendi", color=discord.Color.red())
                    embed.add_field(name="Kullanıcı", value=message.author.mention)
                    embed.add_field(name="Kanal", value=message.channel.mention)
                    embed.add_field(name="Sözcük", value=kelime)
                    await log_kanal.send(embed=embed)
                return

    # 📊 3. SEVİYE SİSTEMİ KONTROLÜ
    user_id = str(message.author.id)
    current_time = datetime.datetime.now().timestamp()

    if user_id not in cooldowns or (current_time - cooldowns[user_id]) > 60:
        cooldowns[user_id] = current_time
        levels_data = load_levels()

        if user_id not in levels_data:
            levels_data[user_id] = {"xp": 0, "level": 1}

        xp_to_add = random.randint(15, 25)
        levels_data[user_id]["xp"] += xp_to_add

        current_xp = levels_data[user_id]["xp"]
        current_level = levels_data[user_id]["level"]
        next_level_xp = get_next_level_xp(current_level)

        if current_xp >= next_level_xp:
            levels_data[user_id]["level"] += 1
            levels_data[user_id]["xp"] = current_xp - next_level_xp
            new_level = levels_data[user_id]["level"]
            
            gained_role_mention = ""
            if new_level in LEVEL_ROLES:
                role_id = LEVEL_ROLES[new_level]
                reward_role = message.guild.get_role(role_id)
                if reward_role and reward_role not in message.author.roles:
                    try:
                        await message.author.add_roles(reward_role)
                        gained_role_mention = f"\n🎖️ **Yeni Rol Kazandın:** {reward_role.mention}"
                    except discord.Forbidden:
                        print(f"⚠️ Botun yetkisi yetersiz: {reward_role.name} rolü verilemedi.")

            seviye_kanal = message.guild.get_channel(SEVIYE_LOG_KANAL_ID) or message.channel
            embed_lvl = discord.Embed(
                title="🎉 SEVİYE ATLADIN!",
                description=f"Tebrikler {message.author.mention}, muhabbetinle coştun ve **Seviye {new_level}** oldun! 🚀{gained_role_mention}",
                color=discord.Color.gold()
            )
            embed_lvl.set_thumbnail(url=message.author.display_avatar.url)
            await seviye_kanal.send(embed=embed_lvl)

        save_levels(levels_data)

    await bot.process_commands(message)


# --- 🖼️ BANNER GÖRSEL OLUŞTURUCU ---
async def generate_banner(member: discord.Member, text_type: str):
    background = Editor(Image.new("RGBA", (1000, 400), (24, 25, 28)))
    card_box = Image.new("RGBA", (940, 340), (15, 15, 17))
    background.paste(Editor(card_box), (30, 30))

    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    avatar_image = await load_image_async(str(avatar_url))
    avatar = Editor(avatar_image).resize((200, 200)).circle_image()
    background.paste(avatar, (60, 100))

    font_title = Font.poppins(size=35, variant="bold")
    font_name = Font.poppins(size=45, variant="bold")
    font_sub = Font.poppins(size=28, variant="regular")

    if text_type == "join":
        title_text = "Kafadan Kontak - Giriş"
        sub_text = "Aramıza Hoş Geldin!"
        title_color = (87, 242, 135)
    else:
        title_text = "Kafadan Kontak - Çıkış"
        sub_text = "Yeniden Bekleriz!"
        title_color = (237, 66, 69)

    user_display = member.global_name if member.global_name else member.name
    username = f"@{member.name}"
    user_id = f"ID: {member.id}"

    background.text((290, 70), title_text, font=font_title, color=title_color)
    background.text((290, 125), user_display, font=font_name, color=(255, 255, 255))
    background.text((290, 185), username, font=font_sub, color=(180, 180, 180))
    background.text((290, 235), user_id, font=font_sub, color=(120, 120, 120))
    background.text((290, 285), sub_text, font=font_sub, color=(200, 200, 200))

    file = discord.File(fp=background.image_bytes, filename="banner.png")
    return file


# --- GELEN / GİDEN ÜYE ---
@bot.event
async def on_member_join(member: discord.Member):
    role = member.guild.get_role(KAYITSIZ_ROL_ID)
    if role:
        try: await member.add_roles(role)
        except: pass

    # --- ÖZEL MESAJ (DM) KISMI ---
    try:
        dm_mesaji = f"Selam {member.mention}, sunucuya hoş geldin!\n\nKurallar kanalını okumayı unutma. Sunucuya tam erişim sağlamak için kayıt kanalına gidip `/kayitol` komutunu kullanarak kayıt olabilirsin. İsmin yetkililer tarafından onaylandıktan sonra giriş yapabileceksin."
        await member.send(dm_mesaji)
    except discord.Forbidden:
        print(f"⚠️ {member.name} adlı kullanıcının DM'leri kapalı olduğu için özel mesaj gönderilemedi.")
    # ------------------------------

    channel = member.guild.get_channel(GELEN_KANAL_ID)
    if channel:
        banner = await generate_banner(member, "join")
        embed = discord.Embed(description=f"{member.mention}\n\n`ID: {member.id}`", color=discord.Color.green())
        embed.set_image(url="attachment://banner.png")
        embed.set_footer(text=f"Seninle birlikte {member.guild.member_count} kişi olduk!")
        await channel.send(file=banner, embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    channel = member.guild.get_channel(GIDEN_KANAL_ID)
    if channel:
        banner = await generate_banner(member, "leave")
        embed = discord.Embed(description=f"**@{member.name}**\n\n`ID: {member.id}`", color=discord.Color.red())
        embed.set_image(url="attachment://banner.png")
        embed.set_footer(text=f"Kalan Üye Sayısı: {member.guild.member_count}")
        await channel.send(file=banner, embed=embed)


# --- 📝 KAYIT & İSİM ONAY SİSTEMİ ---
class OnayView(discord.ui.View):
    def __init__(self, target_member: discord.Member, yeni_isim: str, is_registration: bool = True):
        super().__init__(timeout=None)
        self.target_member = target_member
        self.yeni_isim = yeni_isim
        self.is_registration = is_registration

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.green, custom_id="onay_btn", emoji="✅")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi(interaction.user, "kayit"):
            await interaction.response.send_message("❌ Bu işlemi onaylamak için Kayıt Yetkilisi olmalısın!", ephemeral=True)
            return

        guild = interaction.guild
        kayitsiz_rol = guild.get_role(KAYITSIZ_ROL_ID)
        kayitli_rol = guild.get_role(KAYITLI_ROL_ID)

        try:
            await self.target_member.edit(nick=self.yeni_isim)
            if self.is_registration:
                if kayitsiz_rol and kayitsiz_rol in self.target_member.roles:
                    await self.target_member.remove_roles(kayitsiz_rol)
                if kayitli_rol and kayitli_rol not in self.target_member.roles:
                    await self.target_member.add_roles(kayitli_rol)

            for item in self.children: item.disabled = True
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "✅ İstek Onaylandı"
            embed.add_field(name="Onaylayan Yetkili", value=interaction.user.mention, inline=False)

            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(f"🎉 {self.target_member.mention} talebi onaylandı! Yeni ismi: **{self.yeni_isim}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Bir hata oluştu: {e}", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.red, custom_id="red_btn", emoji="❌")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi(interaction.user, "kayit"):
            await interaction.response.send_message("❌ Bu işlemi reddetmek için Kayıt Yetkilisi olmalısın!", ephemeral=True)
            return

        for item in self.children: item.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ İstek Reddedildi"
        embed.add_field(name="Reddeden Yetkili", value=interaction.user.mention, inline=False)

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"🚫 {self.target_member.mention} talebi reddedildi.", ephemeral=True)


class KayitFormu(discord.ui.Modal, title="Kafadan Kontak - Kayıt Formu"):
    isim = discord.ui.TextInput(label="Adınız", placeholder="Örn: Ahmet", min_length=2, max_length=20, required=True)
    yas = discord.ui.TextInput(label="Yaşınız", placeholder="Örn: 20", min_length=1, max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Kayıt talebin yetkililere iletildi!", ephemeral=True)
        yeni_nick = f"{self.isim.value} | {self.yas.value}"
        onay_kanali = interaction.guild.get_channel(ISIM_ONAY_KANAL_ID)
        if onay_kanali:
            embed = discord.Embed(title="📋 Yeni Kayıt Talebi", description=f"**Kullanıcı:** {interaction.user.mention}\n**ID:** `{interaction.user.id}`\n\n**İsim:** {self.isim.value}\n**Yaş:** {self.yas.value}\n**Yeni İsim:** `{yeni_nick}`", color=discord.Color.gold())
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await onay_kanali.send(embed=embed, view=OnayView(target_member=interaction.user, yeni_isim=yeni_nick, is_registration=True))

class IsimDegistirFormu(discord.ui.Modal, title="Kafadan Kontak - İsim Değiştirme"):
    isim = discord.ui.TextInput(label="Yeni Adınız", placeholder="Örn: Mehmet", min_length=2, max_length=20, required=True)
    yas = discord.ui.TextInput(label="Yaşınız", placeholder="Örn: 20", min_length=1, max_length=2, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ İsim değiştirme talebin yetkililere iletildi!", ephemeral=True)
        yeni_nick = f"{self.isim.value} | {self.yas.value}"
        onay_kanali = interaction.guild.get_channel(ISIM_ONAY_KANAL_ID)
        if onay_kanali:
            embed = discord.Embed(title="✏️ İsim Değişikliği Talebi", description=f"**Kullanıcı:** {interaction.user.mention}\n**Mevcut:** `{interaction.user.display_name}`\n\n**İstenen İsim:** {self.isim.value}\n**İstenen Yaş:** {self.yas.value}\n**Yeni İsim:** `{yeni_nick}`", color=discord.Color.blue())
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await onay_kanali.send(embed=embed, view=OnayView(target_member=interaction.user, yeni_isim=yeni_nick, is_registration=False))


# --- ⚽🎮 MESAJ TEPKİSİ İLE ROL ALMA SİSTEMİ ---
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or payload.channel_id != ROL_ALMA_KANAL_ID:
        return

    emoji_name = payload.emoji.name
    guild = bot.get_guild(payload.guild_id)
    member = payload.member
    if not guild or not member: return

    if emoji_name in TAKIM_ROLLER:
        yeni_rol_id = TAKIM_ROLLER[emoji_name]
        yeni_rol = guild.get_role(yeni_rol_id)
        for key, role_id in TAKIM_ROLLER.items():
            if key != emoji_name:
                eski_rol = guild.get_role(role_id)
                if eski_rol and eski_rol in member.roles: await member.remove_roles(eski_rol)
        if yeni_rol and yeni_rol not in member.roles: await member.add_roles(yeni_rol)

    elif emoji_name in OYUN_ROLLER:
        rol = guild.get_role(OYUN_ROLLER[emoji_name])
        if rol and rol not in member.roles: await member.add_roles(rol)

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.channel_id != ROL_ALMA_KANAL_ID: return
    emoji_name = payload.emoji.name
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None
    if not member: return

    if emoji_name in TAKIM_ROLLER:
        rol = guild.get_role(TAKIM_ROLLER[emoji_name])
        if rol and rol in member.roles: await member.remove_roles(rol)
    elif emoji_name in OYUN_ROLLER:
        rol = guild.get_role(OYUN_ROLLER[emoji_name])
        if rol and rol in member.roles: await member.remove_roles(rol)


# Geçici açılan odaların ID'lerini takip etmek için liste
gecici_odalar = []

@bot.event
async def on_voice_state_update(member, before, after):
    ODA_OLUSTUR_KANAL_ID = 1533261154560905316  # Senin gönderdiğin kanal ID'si
    
    # 1. Kullanıcı "Oda Oluştur" kanalına katıldığında
    if after.channel and after.channel.id == ODA_OLUSTUR_KANAL_ID:
        guild = member.guild
        category = after.channel.category # Kanalın bulunduğu kategoriye açar
        
        # Yeni ses kanalını oluştur
        yeni_kanal = await guild.create_voice_channel(
            name=f"🔊 {member.display_name}'in Odası",
            category=category
        )
        
        gecici_odalar.append(yeni_kanal.id)
        
        # Marpel tarzı yönetim panelini odanın chatine gönder
        embed = discord.Embed(
            title=f"{member.name} Kişisinin özel odası",
            description="Aşağıdaki butonları ve menüleri kullanarak odanı yönetebilirsin.",
            color=discord.Color.dark_theme()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        await yeni_kanal.send(
            content=f"{member.mention} Selamm özel odanı bu menüden yönetebilirsin", 
            embed=embed, 
            view=OdaKontrolView()
        )
        
        # Kullanıcıyı yeni açılan odaya taşı
        try:
            await member.move_to(yeni_kanal)
        except:
            await yeni_kanal.delete()
            gecici_odalar.remove(yeni_kanal.id)

    # 2. Odadan birisi çıktığında ve oda boşaldığında odayı sil
    if before.channel and before.channel.id in gecici_odalar:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                gecici_odalar.remove(before.channel.id)
            except:
                pass


# --- ℹ️ YARDIM KOMUTU ---

@bot.tree.command(name="yardım", description="Botun tüm komutlarını ve kullanım detaylarını gösterir.")
async def yardım(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Kafadan Kontak Botu - Komut Rehberi",
        description="Aşağıda sunucumuzda kullanabileceğin tüm `/` (Slash) komutları kategorilerine göre listelenmiştir:",
        color=discord.Color.blurple()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    embed.add_field(
        name="🎂 Doğum Günü Komutları",
        value=(
            "• `/dogum-gunu-ekle [gün] [ay]` : Doğum gününüzü sisteme kaydeder.\n"
            "• `/dogum-gunu-sil` : Kayıtlı doğum gününüzü siler.\n"
            "• `/dogum-gunu-liste` : Sunucudaki doğum günlerini listeler."
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Seviye & XP Komutları",
        value=(
            "• `/seviye [üye]` : Mevcut seviyenizi ve XP kartınızı gösterir.\n"
            "• `/leaderboard` : En yüksek seviyeli ilk 10 üyeyi sıralar."
        ),
        inline=False
    )

    embed.add_field(
        name="📝 Kayıt & Profil Komutları",
        value=(
            "• `/kayitol` : Sunucuya kayıt olmanı sağlayan formu açar. *(Sadece kayıt kanalında)*\n"
            "• `/isimdegistir` : İsim/yaş değiştirme formu açar. *(Sadece bot kullanım kanalında)*"
        ),
        inline=False
    )

    if yetkili_mi(interaction.user, "kayit"):
        embed.add_field(
            name="🛡️ Yetkili Komutları",
            value=(
                "• `/rol-ver [üye] [rol] [sebep]` : Kullanıcıya rol verir.\n"
                "• `/rol-al [üye] [rol] [sebep]` : Kullanıcıdan rol alır.\n"
                "• `/sustur [üye] [dakika] [sebep]` : Üyeyi süreli susturur.\n"
                "• `/sustur-kaldir [üye]` : Susturmayı kaldırır.\n"
                "• `/sil [miktar]` : Belirtilen sayıda mesajı temizler.\n"
                "• `/ticket-kur` : Destek talebi panelini kurar.\n"
                "• `/rolmesaj` : Takım ve oyun seçme panelini gönderir."
            ),
            inline=False
        )

    embed.set_footer(text=f"Sorgulayan: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- 📊 SEVİYE SİSTEMİ KOMUTLARI ---

@bot.tree.command(name="seviye", description="Mevcut seviyenizi ve XP durumunuzu gösterir.")
@app_commands.describe(uye="Seviyesine bakılacak üye (Opsiyonel)")
async def seviye(interaction: discord.Interaction, uye: discord.Member = None):
    target = uye or interaction.user
    levels_data = load_levels()
    user_id = str(target.id)

    if user_id not in levels_data:
        lvl = 1
        xp = 0
    else:
        lvl = levels_data[user_id]["level"]
        xp = levels_data[user_id]["xp"]

    next_xp = get_next_level_xp(lvl)

    embed = discord.Embed(
        title=f"📊 {target.display_name} - Seviye Kartı",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="Mevcut Seviye", value=f"⭐ **{lvl}**", inline=True)
    embed.add_field(name="XP Durumu", value=f"✨ **{xp} / {next_xp} XP**", inline=True)
    
    percent = min(100, int((xp / next_xp) * 100))
    bar_length = 10
    filled = int(bar_length * percent // 100)
    bar = "🟩" * filled + "⬜" * (bar_length - filled)
    
    embed.add_field(name="İlerleme", value=f"{bar} **%{percent}**", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard", description="Sunucunun en yüksek seviyeli ilk 10 üyesini gösterir.")
async def leaderboard(interaction: discord.Interaction):
    levels_data = load_levels()

    if not levels_data:
        await interaction.response.send_message("⚠️ Henüz kimse XP kazanmadı!", ephemeral=True)
        return

    sorted_users = sorted(levels_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)[:10]

    embed = discord.Embed(
        title="🏆 Kafadan Kontak - Liderlik Tablosu",
        description="Sunucunun en aktif üyeleri:",
        color=discord.Color.gold()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    desc = ""
    for idx, (u_id, data) in enumerate(sorted_users, 1):
        member = interaction.guild.get_member(int(u_id))
        name = member.mention if member else f"Bilinmeyen Kullanıcı (`{u_id}`)"
        
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"**#{idx}**"
        desc += f"{medal} {name} • **Seviye {data['level']}** (`{data['xp']} XP`)\n"

    embed.description = desc
    await interaction.response.send_message(embed=embed)


# --- 🎂 DOĞUM GÜNÜ KOMUTLARI ---

@bot.tree.command(name="dogum-gunu-ekle", description="Doğum gününüzü sisteme kaydeder.")
@app_commands.describe(gun="Doğum gününüz (1-31)", ay="Doğum ayınız (1-12)")
async def dogum_gunu_ekle(interaction: discord.Interaction, gun: int, ay: int):
    if not (1 <= gun <= 31 and 1 <= ay <= 12):
        await interaction.response.send_message("❌ Lütfen geçerli bir gün (1-31) ve ay (1-12) girin!", ephemeral=True)
        return
        
    birthdays = load_birthdays()
    bday_str = f"{gun:02d}-{ay:02d}"
    birthdays[str(interaction.user.id)] = bday_str
    save_birthdays(birthdays)
    
    await interaction.response.send_message(f"✅ Doğum günün başarıyla **{gun:02d}.{ay:02d}** olarak kaydedildi! O gün geldiğinde kutlayıp sana +500 XP hediye edeceğiz! 🎂", ephemeral=True)


@bot.tree.command(name="dogum-gunu-sil", description="Sisteme kayıtlı doğum gününüzü siler.")
async def dogum_gunu_sil(interaction: discord.Interaction):
    birthdays = load_birthdays()
    user_id = str(interaction.user.id)
    
    if user_id in birthdays:
        del birthdays[user_id]
        save_birthdays(birthdays)
        await interaction.response.send_message("🗑️ Doğum günü kaydınız başarıyla silindi.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Zaten kayıtlı bir doğum gününüz bulunmuyor.", ephemeral=True)


@bot.tree.command(name="dogum-gunu-liste", description="Sunucudaki kayıtlı doğum günlerini gösterir.")
async def dogum_gunu_liste(interaction: discord.Interaction):
    birthdays = load_birthdays()
    if not birthdays:
        await interaction.response.send_message("⚠️ Henüz hiç kimse doğum gününü kaydetmedi!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎂 Sunucu Doğum Günü Listesi",
        color=discord.Color.magenta()
    )

    desc = ""
    for u_id, bday in birthdays.items():
        member = interaction.guild.get_member(int(u_id))
        if member:
            desc += f"📅 **{bday.replace('-', '.')}** — {member.mention}\n"

    embed.description = desc if desc else "Kayıtlı kullanıcılar sunucuda bulunamadı."
    await interaction.response.send_message(embed=embed)


# --- 🎟️ DESTEK PANELİ KURMA KOMUTU ---

@bot.tree.command(name="ticket-kur", description="Destek talebi panelini bulunduğunuz kanala kurar.")
async def ticket_kur(interaction: discord.Interaction):
    if not yetkili_mi(interaction.user, "banhammer"):
        await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yetersiz!", ephemeral=True)
        return

    embed = discord.Embed(
        title="📩 Kafadan Kontak - Destek Sistemi",
        description="Sunucuyla ilgili bir sorununuz, şikayetiniz veya talebiniz varsa aşağıdan uygun konuyu seçerek destek talebi açabilirsiniz.\n\n📌 *Gereksiz destek talebi açmak ve yetkilileri gereksiz meşgul etmek yasaktır.*",
        color=discord.Color.blue()
    )
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)

    await interaction.channel.send(embed=embed, view=TicketSelectView())
    await interaction.response.send_message("✅ Destek paneli başarıyla kuruldu!", ephemeral=True)


# --- 🎭 ROL VERME VE ALMA KOMUTLARI ---

@bot.tree.command(name="rol-ver", description="Bir üyeye rol verir.")
@app_commands.describe(uye="Rol verilecek üye", rol="Verilecek rol", sebep="Rol verme sebebi")
async def rol_ver(interaction: discord.Interaction, uye: discord.Member, rol: discord.Role, sebep: str = "Sebep belirtilmedi"):
    if not yetkili_mi(interaction.user, "kayit"):
        await interaction.response.send_message("❌ Bu komutu kullanmak için yetkin yok!", ephemeral=True)
        return

    ephemeral_embed = discord.Embed(title=f"{interaction.user.display_name} - Rol Verme İşlemi", color=discord.Color.blue())
    if interaction.user.avatar:
        ephemeral_embed.set_thumbnail(url=interaction.user.avatar.url)

    basarisizlar = []
    if rol >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        basarisizlar.append(f"• **{uye.display_name}** (Rol seninle aynı veya üst seviyede)")
    elif uye.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        basarisizlar.append(f"• **{uye.display_name}** (Kendinden yüksek veya eşit yetkili)")

    if basarisizlar:
        ephemeral_embed.add_field(name="⚙️ · Verilen Rol", value=rol.mention, inline=False)
        ephemeral_embed.add_field(name="☕ · Sebep", value=sebep, inline=False)
        ephemeral_embed.add_field(name=f"🚫 · Başarısız ({len(basarisizlar)}):", value="\n".join(basarisizlar), inline=False)
        await interaction.response.send_message(embed=ephemeral_embed, ephemeral=True)
        return

    try:
        await uye.add_roles(rol, reason=sebep)
        ephemeral_embed.add_field(name="⚙️ · Verilen Rol", value=rol.mention, inline=False)
        ephemeral_embed.add_field(name="☕ · Sebep", value=sebep, inline=False)
        ephemeral_embed.add_field(name="✅ · Başarılı (1):", value=f"• {uye.mention}", inline=False)
        await interaction.response.send_message(embed=ephemeral_embed, ephemeral=True)

        log_kanal = interaction.guild.get_channel(MOD_LOG_KANAL_ID)
        if log_kanal:
            log_embed = discord.Embed(title="✅ Rol Verildi", description=f"{uye.mention} kullanıcısına {rol.mention} rolü verildi.", color=discord.Color.green())
            log_embed.add_field(name="Yetkili", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Sebep", value=sebep, inline=True)
            await log_kanal.send(embed=log_embed)
    except discord.Forbidden:
        ephemeral_embed.add_field(name="🚫 · Başarısız (1):", value="• Botun yetkisi yetersiz", inline=False)
        await interaction.response.send_message(embed=ephemeral_embed, ephemeral=True)


@bot.tree.command(name="rol-al", description="Bir üyeden rol alır.")
@app_commands.describe(uye="Rol alınacak üye", rol="Alınacak rol", sebep="Rol alma sebebi")
async def rol_al(interaction: discord.Interaction, uye: discord.Member, rol: discord.Role, sebep: str = "Sebep belirtilmedi"):
    if not yetkili_mi(interaction.user, "kayit"):
        await interaction.response.send_message("❌ Bu komutu kullanmak için yetkin yok!", ephemeral=True)
        return

    ephemeral_embed = discord.Embed(title=f"{interaction.user.display_name} - Rol Alma İşlemi", color=discord.Color.orange())
    if interaction.user.avatar:
        ephemeral_embed.set_thumbnail(url=interaction.user.avatar.url)

    basarisizlar = []
    if rol >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
        basarisizlar.append(f"• **{uye.display_name}** (Rol seninle aynı veya üst seviyede)")

    if basarisizlar:
        ephemeral_embed.add_field(name=f"🚫 · Başarısız ({len(basarisizlar)}):", value="\n".join(basarisizlar), inline=False)
        await interaction.response.send_message(embed=ephemeral_embed, ephemeral=True)
        return

    try:
        await uye.remove_roles(rol, reason=sebep)
        ephemeral_embed.add_field(name="⚙️ · Alınan Rol", value=rol.mention, inline=False)
        ephemeral_embed.add_field(name="✅ · Başarılı (1):", value=f"• {uye.mention}", inline=False)
        await interaction.response.send_message(embed=ephemeral_embed, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Botun yetkisi yetersiz!", ephemeral=True)


# --- 🔨 MODERASYON KOMUTLARI ---

@bot.tree.command(name="sustur", description="Belirtilen üyeyi geçici olarak susturur (Timeout).")
@app_commands.describe(uye="Susturulacak üye", dakika="Susturma süresi (Dakika)", sebep="Susturma sebebi")
async def sustur(interaction: discord.Interaction, uye: discord.Member, dakika: int, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, "yetkili"):
        await interaction.response.send_message("❌ Bu komutu kullanmak için yetkiniz yetersiz!", ephemeral=True)
        return

    sure = datetime.timedelta(minutes=dakika)
    await uye.timeout(sure, reason=sebep)
    embed = discord.Embed(title="🔇 Üye Susturuldu", color=discord.Color.red())
    embed.add_field(name="Susturulan", value=uye.mention)
    embed.add_field(name="Süre", value=f"{dakika} Dakika")
    embed.add_field(name="Sebep", value=sebep, inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="sustur-kaldir", description="Üyenin susturmasını kaldırır.")
async def sustur_kaldir(interaction: discord.Interaction, uye: discord.Member):
    if not yetkili_mi(interaction.user, "yetkili"):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return

    await uye.timeout(None)
    await interaction.response.send_message(f"🔊 {uye.mention} kullanıcısının susturması kaldırıldı!")


@bot.tree.command(name="sil", description="Sadece bu kanaldan belirtilen miktarda mesajı siler.")
@app_commands.describe(miktar="Silinecek mesaj sayısı (1-100)")
async def sil(interaction: discord.Interaction, miktar: int):
    if not yetkili_mi(interaction.user, "yetkili"):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return

    if miktar < 1 or miktar > 100:
        await interaction.response.send_message("⚠️ 1 ile 100 arasında bir sayı girin.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=miktar)
    await interaction.followup.send(f"🧹 {len(deleted)} adet mesaj silindi.", ephemeral=True)


# --- SİSTEM KOMUTLARI ---

@bot.tree.command(name="rolmesaj", description="Takım ve Oyun seçme panellerini kanala gönderir.")
async def rolmesaj(interaction: discord.Interaction):
    if not yetkili_mi(interaction.user, "banhammer"):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    msg_takim = await interaction.channel.send("# Tuttuğunuz Takımı Seçin")
    for emoji_name in TAKIM_ROLLER.keys():
        emoji = discord.utils.get(interaction.guild.emojis, name=emoji_name)
        if emoji: await msg_takim.add_reaction(emoji)

    msg_oyun = await interaction.channel.send("# Oynadığınız oyunları seçin")
    for emoji_name in OYUN_ROLLER.keys():
        emoji = discord.utils.get(interaction.guild.emojis, name=emoji_name)
        if emoji: await msg_oyun.add_reaction(emoji)

    await interaction.followup.send("✅ Paneller kuruldu!", ephemeral=True)


@bot.tree.command(name="kayitol", description="Kayıt formu açar.")
async def kayitol(interaction: discord.Interaction):
    if interaction.channel_id != KAYIT_KANAL_ID:
        await interaction.response.send_message("⚠️ Bu kanalda kullanamazsın!", ephemeral=True)
        return
    await interaction.response.send_modal(KayitFormu())


@bot.tree.command(name="isimdegistir", description="İsim değiştirme formu açar.")
async def isimdegistir(interaction: discord.Interaction):
    if interaction.channel_id != BOT_KULLANIM_KANAL_ID:
        await interaction.response.send_message("⚠️ Bu kanalda kullanamazsın!", ephemeral=True)
        return
    await interaction.response.send_modal(IsimDegistirFormu())


# TOKEN
bot.run(os.getenv("DISCORD_TOKEN"))