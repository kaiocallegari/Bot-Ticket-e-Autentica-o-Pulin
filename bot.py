import os
import asyncio
import discord
from discord.ext import commands


# =========================================================
#  Carregador manual do .env (sem depender do python-dotenv)
# =========================================================
def load_env(path=".env"):
    # Na hospedagem as variáveis vêm do painel (variáveis de ambiente);
    # localmente, o arquivo .env sobrescreve.
    env = dict(os.environ)
    if not os.path.exists(path):
        if not env.get("TOKEN"):
            print(
                f"[ERRO] TOKEN não encontrado. Crie o '{path}' na pasta do bot.py "
                "ou defina TOKEN e os IDs nas variáveis de ambiente da hospedagem."
            )
            raise SystemExit(1)
        return env

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


env = load_env()

TOKEN = env.get("TOKEN")
TICKET_CATEGORY_ID = int(env["TICKET_CATEGORY_ID"]) if env.get("TICKET_CATEGORY_ID") else None
STAFF_ROLE_ID = int(env["STAFF_ROLE_ID"]) if env.get("STAFF_ROLE_ID") else None
LOG_CHANNEL_ID = int(env["LOG_CHANNEL_ID"]) if env.get("LOG_CHANNEL_ID") else None
REGISTER_ROLE_ID = int(env["REGISTER_ROLE_ID"]) if env.get("REGISTER_ROLE_ID") else None

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def send_log(guild: discord.Guild, embed: discord.Embed):
    """Envia um embed para o canal de log configurado no .env, se existir."""
    if not LOG_CHANNEL_ID:
        return
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)


# =========================================================
#  Sistema de Tickets
# =========================================================
TICKET_TYPES = {
    "comprar": {
        "label": "Comprar",
        "emoji": "💰",
        "style": discord.ButtonStyle.success,   # verde
        "topic": "Ticket de Compra",
        "color": discord.Color.green(),
    },
    "duvida": {
        "label": "Dúvida",
        "emoji": "❓",
        "style": discord.ButtonStyle.primary,   # azul
        "topic": "Ticket de Dúvida",
        "color": discord.Color.blue(),
    },
}


async def create_ticket_channel(interaction: discord.Interaction, kind: str):
    guild = interaction.guild
    info = TICKET_TYPES[kind]

    # Evita que o mesmo usuário abra dois tickets do mesmo tipo
    marker = f"{info['topic']} | {interaction.user.id}"
    existing = discord.utils.get(guild.text_channels, topic=marker)
    if existing:
        await interaction.response.send_message(
            f"Você já tem um ticket aberto: {existing.mention}", ephemeral=True
        )
        return

    category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    if STAFF_ROLE_ID:
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

    channel_name = f"{kind}-{interaction.user.name}"[:95]

    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        topic=marker,
    )

    embed = discord.Embed(
        title=f"{info['emoji']} {info['topic']}",
        description=(
            f"Olá {interaction.user.mention}! Descreva sua solicitação com detalhes "
            "e aguarde um membro da equipe."
        ),
        color=info["color"],
    )
    await channel.send(embed=embed, view=CloseTicketView())
    await interaction.response.send_message(f"Ticket criado: {channel.mention}", ephemeral=True)

    log_embed = discord.Embed(
        title="🎫 Ticket Aberto",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )
    log_embed.add_field(name="Tipo", value=info["topic"], inline=True)
    log_embed.add_field(name="Usuário", value=interaction.user.mention, inline=True)
    log_embed.add_field(name="Canal", value=channel.mention, inline=True)
    await send_log(guild, log_embed)


class TicketPanelView(discord.ui.View):
    """Painel fixo com os botões Comprar e Dúvida. custom_id fixo = persiste após restart."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Comprar", emoji="💰", style=discord.ButtonStyle.success, custom_id="ticket_comprar"
    )
    async def comprar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "comprar")

    @discord.ui.button(
        label="Dúvida", emoji="❓", style=discord.ButtonStyle.primary, custom_id="ticket_duvida"
    )
    async def duvida(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "duvida")


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_fechar"
    )
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        await interaction.response.send_message("Fechando o ticket em 5 segundos...")

        log_embed = discord.Embed(
            title="🔒 Ticket Fechado",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        log_embed.add_field(name="Canal", value=channel.name, inline=True)
        log_embed.add_field(name="Fechado por", value=interaction.user.mention, inline=True)
        await send_log(guild, log_embed)

        await asyncio.sleep(5)
        await channel.delete()


# =========================================================
#  Auto-registro (painel que pede o nome e dá o cargo)
# =========================================================
class RegisterModal(discord.ui.Modal, title="Registro"):
    nome = discord.ui.TextInput(
        label="Qual é o seu nome?",
        placeholder="Digite seu nome completo",
        max_length=32,
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        nome_valor = self.nome.value.strip()

        try:
            await member.edit(nick=nome_valor)
        except discord.Forbidden:
            pass  # sem permissão pra mudar apelido (ex: dono do servidor)

        cargo_ok = False
        if REGISTER_ROLE_ID:
            role = guild.get_role(REGISTER_ROLE_ID)
            if role:
                await member.add_roles(role)
                cargo_ok = True

        aviso = "" if cargo_ok else "\n(Aviso: cargo de registro não encontrado — confira o REGISTER_ROLE_ID no .env)"
        await interaction.response.send_message(
            f"Registro concluído! Bem-vindo(a), **{nome_valor}**.{aviso}", ephemeral=True
        )

        log_embed = discord.Embed(
            title="📝 Novo Registro",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        log_embed.add_field(name="Usuário", value=member.mention, inline=True)
        log_embed.add_field(name="Nome registrado", value=nome_valor, inline=True)
        await send_log(guild, log_embed)


class RegisterPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Registrar", emoji="📝", style=discord.ButtonStyle.success, custom_id="registro_botao"
    )
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegisterModal())


# =========================================================
#  Comandos para enviar os painéis
# =========================================================
@bot.command(name="painel")
@commands.has_permissions(administrator=True)
async def painel(ctx):
    embed = discord.Embed(
        title="🎫 Central de Atendimento",
        description=(
            "Selecione uma opção abaixo para abrir um ticket:\n\n"
            "💰 **Comprar** — Dúvidas sobre compras e produtos\n"
            "❓ **Dúvida** — Outras dúvidas gerais"
        ),
        color=discord.Color.gold(),
    )
    await ctx.send(embed=embed, view=TicketPanelView())


@bot.command(name="registro")
@commands.has_permissions(administrator=True)
async def registro(ctx):
    embed = discord.Embed(
        title="📝 Painel de Registro",
        description="Clique no botão abaixo e informe seu nome para se registrar no servidor.",
        color=discord.Color.blurple(),
    )
    await ctx.send(embed=embed, view=RegisterPanelView())


@bot.event
async def on_ready():
    # Reregistra as views com custom_id fixo para que os botões continuem
    # funcionando mesmo depois de reiniciar o bot.
    bot.add_view(TicketPanelView())
    bot.add_view(CloseTicketView())
    bot.add_view(RegisterPanelView())
    print(f"Bot conectado como {bot.user}")


if __name__ == "__main__":
    bot.run(TOKEN)
