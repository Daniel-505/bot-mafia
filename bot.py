import random
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
from collections import defaultdict

# Cargar variables de entorno
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# Configurar los intents del bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionario de partidas
games = {}

# Roles para 4 jugadores
ROLES = ['Mafioso', 'Ciudadano', 'Doctor', 'Detective']

@bot.command()
async def mafia(ctx, action, *args):
    if ctx.guild is None:
        await ctx.send("⚠️ Este comando solo puede usarse en un servidor.")
        return
    
    game_id = f"game_{ctx.guild.id}"

    if action == "crear":
        if game_id in games:
            await ctx.send("⚠️ Ya hay una partida en curso.")
            return
        
        num_players = 4  
        games[game_id] = {
            'host': ctx.channel.id,
            'players': [ctx.author.id],
            'max_players': num_players,
            'roles': {},
            'state': 'waiting',
            'votes': defaultdict(int),
            'night': False,
            'mafioso_target': None,
            'doctor_target': None
        }
        
        await ctx.send(f"✅ Se ha creado una partida de Mafia para {num_players} jugadores. Usa `!mafia unirme` para participar.")

    elif action == "unirme":
        if game_id not in games:
            await ctx.send("⚠️ No hay ninguna partida en curso. Usa `!mafia crear` para iniciar una.")
            return

        game = games[game_id]
        
        if game['state'] != 'waiting':
            await ctx.send("⏳ La partida ya ha comenzado. No puedes unirte ahora.")
            return

        if len(game['players']) >= game['max_players']:
            await ctx.send(f"⚠️ La partida ya está llena con {game['max_players']} jugadores.")
            return

        if ctx.author.id in game['players']:
            await ctx.send("⚠️ Ya estás en la partida.")
            return

        game['players'].append(ctx.author.id)
        await ctx.send(f"✅ {ctx.author.mention} se ha unido. Jugadores actuales: {len(game['players'])}/{game['max_players']}.")

        if len(game['players']) == game['max_players']:
            await assign_roles(ctx, game_id)
            cambiar_fase_automatica.start(game_id)

async def assign_roles(ctx, game_id):
    game = games[game_id]
    players = game['players']
    random.shuffle(players)
    
    roles = ROLES.copy()
    random.shuffle(roles)
    
    game['roles'] = dict(zip(players, roles))
    game['state'] = 'started'
    
    for player_id in players:
        role = game['roles'][player_id]
        user = await bot.fetch_user(player_id)
        
        if user:
            try:
                await user.send(f"🔎 Tu rol es **{role}**. Usa los comandos adecuados para tu rol durante la partida.")
            except discord.Forbidden:
                await ctx.send(f"🚫 No pude enviar un mensaje privado a {user.mention}. Asegúrate de permitir DMs del servidor.")
    
    await ctx.send("🎭 La partida ha comenzado. Los roles han sido asignados. ¡Buena suerte a todos!")

@tasks.loop(seconds=60)
async def cambiar_fase_automatica(game_id):
    if game_id in games:
        game = games[game_id]
        game['night'] = not game['night']
        fase = 'noche' if game['night'] else 'día'
        
        for player_id in game['players']:
            user = await bot.fetch_user(player_id)
            if user:
                try:
                    await user.send(f"🌙 Ha comenzado la **{fase}**.")
                except discord.Forbidden:
                    pass
        
        channel = bot.get_channel(games[game_id]['host'])
        if channel:
            await channel.send(f"🌙 Ahora es {fase}.")

@bot.command()
async def matar(ctx, target: discord.Member):
    game_id = f"game_{ctx.guild.id}"

    if game_id not in games or games[game_id]['state'] != 'started':
        await ctx.send("⚠️ No hay una partida en curso.")
        return
    
    game = games[game_id]

    if not game['night']:
        await ctx.send("⚠️ Solo puedes matar durante la noche.")
        return

    if ctx.author.id not in game['players'] or game['roles'][ctx.author.id] != 'Mafioso':
        await ctx.send("⚠️ Solo el Mafioso puede matar.")
        return

    if target.id not in game['players']:
        await ctx.send("⚠️ Este jugador no está en la partida.")
        return

    game['mafioso_target'] = target.id
    await ctx.author.send(f"✅ Has seleccionado a un objetivo. Esperando el resultado de la noche...")

@bot.command()
async def salvar(ctx, target: discord.Member):
    game_id = f"game_{ctx.guild.id}"

    if game_id not in games or games[game_id]['state'] != 'started':
        await ctx.send("⚠️ No hay una partida en curso.")
        return
    
    game = games[game_id]

    if not game['night']:
        await ctx.send("⚠️ Solo puedes salvar durante la noche.")
        return

    if ctx.author.id not in game['players'] or game['roles'][ctx.author.id] != 'Doctor':
        await ctx.send("⚠️ Solo el Doctor puede salvar.")
        return

    if target.id not in game['players']:
        await ctx.send("⚠️ Este jugador no está en la partida.")
        return

    game['doctor_target'] = target.id
    await ctx.author.send(f"✅ Has seleccionado a un objetivo para salvar esta noche.")

# Iniciar el bot
bot.run(token)
