import discord
from discord.ext import commands, tasks
import asyncio
import random

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!mafia ', intents=intents)

partida = {
    'jugadores': [],
    'roles': {},
    'vivos': [],
    'fase': 'esperando',
    'canal_mafioso': None,
    'canal_doctor': None,
    'votos': {},
    'votos_recibidos': 0,
    'objetivo_mafia': None,
    'objetivo_doctor': None
}

@bot.event
async def on_ready():
    print(f'Conectado como {bot.user}')

@bot.command()
async def crear(ctx, cantidad: int):
    if partida['fase'] != 'esperando':
        await ctx.send("Ya hay una partida en curso.")
        return

    partida['jugadores'] = []
    partida['roles'] = {}
    partida['vivos'] = []
    partida['votos'] = {}
    partida['votos_recibidos'] = 0
    partida['fase'] = 'reclutando'
    partida['canal_mafioso'] = None
    partida['canal_doctor'] = None
    partida['objetivo_mafia'] = None
    partida['objetivo_doctor'] = None
    partida['cantidad'] = cantidad

    await ctx.send(f"¡Partida creada! Se necesitan {cantidad} jugadores. Usa `!mafia unirme` para participar.")

@bot.command()
async def unirme(ctx):
    if partida['fase'] != 'reclutando':
        await ctx.send("No hay una partida disponible para unirse.")
        return

    if ctx.author in partida['jugadores']:
        await ctx.send("Ya estás en la partida.")
        return

    if len(partida['jugadores']) >= partida['cantidad']:
        await ctx.send("La partida ya está llena.")
        return

    partida['jugadores'].append(ctx.author)
    partida['vivos'].append(ctx.author)

    await ctx.send(f"{ctx.author.mention} se ha unido a la partida.")

    if len(partida['jugadores']) == partida['cantidad']:
        partida['fase'] = 'asignando_roles'
        await asignar_roles(ctx)

async def asignar_roles(ctx):
    random.shuffle(partida['jugadores'])
    
    # Asignación de roles
    for i, jugador in enumerate(partida['jugadores']):
        if i == 0:
            partida['roles'][jugador] = 'mafioso'
        elif i == 1:
            partida['roles'][jugador] = 'doctor'
        elif i == 2:
            partida['roles'][jugador] = 'detective'
        else:
            partida['roles'][jugador] = 'ciudadano'

    # Enviar roles por privado
    for jugador, rol in partida['roles'].items():
        await jugador.send(f"Tu rol en la partida es: {rol}")

    # Crear canales privados para mafioso y doctor
    guild = ctx.guild
    categoria = discord.utils.get(guild.categories, name="Partidas de Mafia")

    if not categoria:
        categoria = await guild.create_category("Partidas de Mafia")

    partida['canal_mafioso'] = await categoria.create_text_channel("canal-mafioso", overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        partida['jugadores'][0]: discord.PermissionOverwrite(read_messages=True)
    })

    partida['canal_doctor'] = await categoria.create_text_channel("canal-doctor", overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        partida['jugadores'][1]: discord.PermissionOverwrite(read_messages=True)
    })

    # Mandar links de los canales privados
    await partida['jugadores'][0].send(f"Tu canal privado para el mafioso: {partida['canal_mafioso'].mention}")
    await partida['jugadores'][1].send(f"Tu canal privado para el doctor: {partida['canal_doctor'].mention}")

    # Iniciar la partida
    partida['fase'] = 'jugando'
    await ctx.send("¡La partida ha comenzado!")

    # Comenzar fase de noche
    await fase_noche(ctx)

async def fase_noche(ctx):
    await ctx.send("La fase de noche ha comenzado. El mafioso puede matar y el doctor puede salvar.")

    # Esperar 1 minuto para la fase de noche
    await asyncio.sleep(60)

    # Fase de día
    await fase_dia(ctx)

async def fase_dia(ctx):
    await ctx.send("La fase de día ha comenzado. Todos los jugadores votan para eliminar a alguien.")
    
    # Implementar lógica de votación...

@bot.command()
async def matar(ctx, miembro: discord.Member):
    if ctx.channel != partida['canal_mafioso']:
        await ctx.send("Este comando solo puede usarse en el canal privado del mafioso.")
        return

    if partida['roles'][ctx.author] != 'mafioso':
        await ctx.send("Solo el mafioso puede matar.")
        return

    if miembro not in partida['vivos']:
        await ctx.send("Este jugador ya está muerto.")
        return

    partida['vivos'].remove(miembro)
    await ctx.send(f"{miembro.mention} ha sido eliminado por el mafioso.")
    await miembro.send("Has sido eliminado del juego.")

@bot.command()
async def salvar(ctx, miembro: discord.Member):
    if ctx.channel != partida['canal_doctor']:
        await ctx.send("Este comando solo puede usarse en el canal privado del doctor.")
        return

    if partida['roles'][ctx.author] != 'doctor':
        await ctx.send("Solo el doctor puede salvar.")
        return

    if miembro not in partida['vivos']:
        await ctx.send("Este jugador ya está muerto.")
        return

    partida['objetivo_doctor'] = miembro
    await ctx.send(f"{miembro.mention} ha sido salvado por el doctor.")

@bot.command()
async def votar(ctx, miembro: discord.Member):
    if miembro not in partida['vivos']:
        await ctx.send("Este jugador ya está muerto.")
        return

    if ctx.author in partida['votos']:
        await ctx.send("Ya has votado.")
        return

    partida['votos'][ctx.author] = miembro
    partida['votos_recibidos'] += 1

    if partida['votos_recibidos'] == len(partida['vivos']):
        await fin_de_votacion(ctx)

async def fin_de_votacion(ctx):
    # Contar votos y eliminar jugador
    votos = {}
    for votante, objetivo in partida['votos'].items():
        if objetivo not in votos:
            votos[objetivo] = 0
        votos[objetivo] += 1

    max_votos = max(votos.values())
    victima = [jugador for jugador, voto in votos.items() if voto == max_votos][0]

    partida['vivos'].remove(victima)
    await ctx.send(f"{victima.mention} ha sido eliminado por votación.")
    await victima.send("Has sido eliminado del juego.")

    if len(partida['vivos']) == 1:
        await ctx.send(f"¡{partida['vivos'][0].mention} ha ganado!")
        partida['fase'] = 'esperando'

bot.run('token')
