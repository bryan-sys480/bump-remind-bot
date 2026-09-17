"""
Bot Discord - Rappel de Bump (multi-services)
================================================

Ce bot détecte quand quelqu'un fait un bump réussi (Disboard, et n'importe quel
autre bot de bump que tu ajoutes toi-même), puis programme un rappel automatique
une fois le cooldown terminé.

Installation :
    pip install -r requirements.txt

Configuration :
    1. Crée un fichier ".env" (voir .env.example) avec ton TOKEN de bot
    2. Lance : python bot.py
    3. Dans ton serveur :
       - /setup salon:#ton-salon role:@TonRole   -> choisit où et qui ping
       - /add-bump-service                        -> ajoute un service de bump
         (Disboard est déjà préconfiguré, cooldown 2h)

Auteur : généré avec Claude
"""

import os
import json
import asyncio
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CONFIG_FILE = "config.json"

# Services de bump préconfigurés (tu peux en ajouter d'autres avec /add-bump-service)
DEFAULT_SERVICES = {
    "disboard": {
        "bot_id": 302050872383242240,
        "keywords": ["bump effectué", "bump done", "successfully bumped"],
        "cooldown_hours": 2,
    }
}

# ---------------------------------------------------------------------------
# Gestion de la configuration (persistance simple en JSON)
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


config = load_config()


def get_guild_conf(guild_id: int) -> dict:
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {"channel_id": None, "role_id": None, "services": dict(DEFAULT_SERVICES)}
    # S'assure que les services par défaut existent même sur une config déjà créée
    config[gid].setdefault("services", {})
    for name, data in DEFAULT_SERVICES.items():
        config[gid]["services"].setdefault(name, data)
    return config[gid]


# ---------------------------------------------------------------------------
# Setup du bot
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True  # nécessaire pour lire les embeds des bots de bump

bot = commands.Bot(command_prefix="!", intents=intents)

# Tâches de rappel actives : {(guild_id, service_name): asyncio.Task}
active_reminders: dict[tuple, asyncio.Task] = {}


async def schedule_reminder(guild_id: int, service_name: str, cooldown_hours: float):
    try:
        await asyncio.sleep(cooldown_hours * 3600)
        guild_conf = get_guild_conf(guild_id)
        channel_id = guild_conf.get("channel_id")
        role_id = guild_conf.get("role_id")
        if not channel_id:
            return

        channel = bot.get_channel(channel_id)
        if channel is None:
            return

        mention = f"<@&{role_id}>" if role_id else ""
        embed = discord.Embed(
            title=f"⏰ C'est l'heure du bump ({service_name}) !",
            description="Le cooldown est terminé, tu peux relancer la commande de bump.",
            color=discord.Color.blurple(),
        )
        await channel.send(content=mention, embed=embed)
    except asyncio.CancelledError:
        pass
    finally:
        active_reminders.pop((guild_id, service_name), None)


def start_reminder(guild_id: int, service_name: str, cooldown_hours: float):
    key = (guild_id, service_name)
    existing = active_reminders.get(key)
    if existing and not existing.done():
        existing.cancel()

    task = bot.loop.create_task(schedule_reminder(guild_id, service_name, cooldown_hours))
    active_reminders[key] = task

    guild_conf = get_guild_conf(guild_id)
    guild_conf.setdefault("next_bump_times", {})
    guild_conf["next_bump_times"][service_name] = (
        datetime.utcnow() + timedelta(hours=cooldown_hours)
    ).isoformat()
    save_config(config)


# ---------------------------------------------------------------------------
# Événements
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_message(message: discord.Message):
    if not message.guild or not message.author.bot:
        await bot.process_commands(message)
        return

    guild_conf = get_guild_conf(message.guild.id)
    services = guild_conf.get("services", {})

    for service_name, data in services.items():
        if message.author.id != data["bot_id"]:
            continue

        text_to_check = ""
        if message.embeds:
            text_to_check += (message.embeds[0].description or "").lower()
            text_to_check += (message.embeds[0].title or "").lower()
        text_to_check += message.content.lower()

        if any(kw.lower() in text_to_check for kw in data["keywords"]):
            start_reminder(message.guild.id, service_name, data["cooldown_hours"])
            hrs = data["cooldown_hours"]
            await message.channel.send(
                f"✅ Bump **{service_name}** détecté ! Rappel dans **{hrs}h**.",
                reference=message,
            )
            break

    await bot.process_commands(message)


# ---------------------------------------------------------------------------
# Commandes slash
# ---------------------------------------------------------------------------

@bot.tree.command(name="setup", description="Configure le salon et le rôle pour les rappels de bump")
@app_commands.describe(salon="Salon où envoyer les rappels", role="Rôle à mentionner (optionnel)")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_cmd(interaction: discord.Interaction, salon: discord.TextChannel, role: discord.Role | None = None):
    guild_conf = get_guild_conf(interaction.guild_id)
    guild_conf["channel_id"] = salon.id
    guild_conf["role_id"] = role.id if role else None
    save_config(config)

    msg = f"Configuration enregistrée : rappels envoyés dans {salon.mention}"
    if role:
        msg += f", avec mention de {role.mention}"
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="add-bump-service", description="Ajoute un bot de bump personnalisé (ex: DL Bump)")
@app_commands.describe(
    nom="Nom du service (ex: dlbump)",
    bump_bot="Le bot Discord qui poste la confirmation de bump",
    mot_cle="Un mot présent dans le message de confirmation (ex: 'bump effectué')",
    cooldown_heures="Durée du cooldown en heures (ex: 4)",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def add_bump_service_cmd(
    interaction: discord.Interaction,
    nom: str,
    bump_bot: discord.Member,
    mot_cle: str,
    cooldown_heures: float,
):
    guild_conf = get_guild_conf(interaction.guild_id)
    guild_conf["services"][nom.lower()] = {
        "bot_id": bump_bot.id,
        "keywords": [mot_cle],
        "cooldown_hours": cooldown_heures,
    }
    save_config(config)

    await interaction.response.send_message(
        f"Service **{nom}** ajouté : bot {bump_bot.mention}, "
        f"mot-clé `{mot_cle}`, cooldown **{cooldown_heures}h**.",
        ephemeral=True,
    )


@bot.tree.command(name="list-bump-services", description="Liste les services de bump configurés sur ce serveur")
async def list_services_cmd(interaction: discord.Interaction):
    guild_conf = get_guild_conf(interaction.guild_id)
    services = guild_conf.get("services", {})
    if not services:
        await interaction.response.send_message("Aucun service configuré.", ephemeral=True)
        return

    lines = []
    for name, data in services.items():
        lines.append(f"• **{name}** — <@{data['bot_id']}> — cooldown {data['cooldown_hours']}h")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="bumpstatus", description="Affiche le temps restant avant le prochain bump possible")
async def bumpstatus_cmd(interaction: discord.Interaction):
    guild_conf = get_guild_conf(interaction.guild_id)
    next_times = guild_conf.get("next_bump_times", {})

    if not next_times:
        await interaction.response.send_message(
            "Aucun bump enregistré pour le moment.", ephemeral=True
        )
        return

    lines = []
    now = datetime.utcnow()
    for service_name, iso_time in next_times.items():
        next_time = datetime.fromisoformat(iso_time)
        remaining = next_time - now
        if remaining.total_seconds() <= 0:
            lines.append(f"• **{service_name}** : disponible maintenant 🚀")
        else:
            minutes, seconds = divmod(int(remaining.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)
            lines.append(f"• **{service_name}** : {hours}h {minutes}min restantes")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@setup_cmd.error
@add_bump_service_cmd.error
async def perms_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "Tu dois avoir la permission 'Gérer le serveur' pour utiliser cette commande.",
            ephemeral=True,
        )


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Erreur : la variable DISCORD_TOKEN n'est pas définie (voir .env.example).")
    bot.run(TOKEN)
