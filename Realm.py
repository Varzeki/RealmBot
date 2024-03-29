# realm.py
import os
import time
import re
import pickle5 as pickle
import yaml
import random
import discord
import asyncio
import math
import traceback
import logging
from dotenv import load_dotenv
from discord.ext import commands
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color
from gtts import gTTS
import sox

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(logging.BASIC_FORMAT)
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")
graceful_init = False
graceful_exit = False
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
vc = None
realm = ""
emoji_set = {
    "swords": "⚔️",
    "greenHP": "🟩",
    "redHP": "🟥",
    "thumbsUP": "👍",
    "1": "1️⃣",
    "2": "2️⃣",
    "3": "3️⃣",
    "4": "4️⃣",
    "5": "5️⃣",
    "A": "🅰️",
    "B": "🅱️",
    "moneyBag": "💰",
    "important": ("\u203C" + "\uFE0F"),
    "skull": "💀",
    "door": "🚪",
}
rat_list = ["Rat"]
channels = {}
reactables = {"playerInventories": {}, "vendors": {}}
roles = {}
class_roles = [
    "arcanist",
    "overseer",
    "warden",
    "mender",
    "curator",
    "corsair",
    "arbiter",
]
race_roles = [
    "human",
    "troll",
    "lizardfolk",
    "dwarf",
    "elf",
]
players = {}
active_mobs = {}
active_pets = []
current_tick = 0
tier_levels = {
    "t1": [1],
    "t2": range(1, 11),
    "t3": range(11, 21),
    "t4": range(21, 31),
    "t5": range(31, 41),
    "t6": range(41, 51),
    "t7": range(51, 61),
}


def generateMob(tier):
    fileMap = {
        "t1": "./Data/Levels/T1_THE_ARBORETUM/Mobs",
        "t2": "./Data/Levels/T2_THE_LOWER_CITY/Mobs",
        "t3": "./Data/Levels/T3_THE_WASTELAND/Mobs",
        "t4": "./Data/Levels/T4_THE_PLAGUELANDS/Mobs",
        "t5": "./Data/Levels/T5_THE_EVERDARK/Mobs",
        "t6": "./Data/Levels/T6_THE_STEPPES_OF_CREATION/Mobs",
        "t7": "./Data/Levels/T7_THE_CITADEL/Mobs",
    }
    with open(fileMap[tier] + "/mobTable.yaml", "r") as stream:
        mobTable = yaml.safe_load(stream)
    mobName = random.choices([*mobTable], weights=[*mobTable.values()], k=1)[0]
    with open(fileMap[tier] + "/" + mobName + "/" + mobName + ".yaml", "r") as stream:
        mobStats = yaml.safe_load(stream)
    mobArt = (
        fileMap[tier]
        + "/"
        + mobName
        + "/"
        + "/Art/"
        + random.choice(os.listdir(fileMap[tier] + "/" + mobName + "/Art"))
    )
    logger.debug("Generated new mob from data")
    return [mobStats, mobArt]


def generateLoot(tier, level, lootType="any"):
    fileMap = {
        "t1": "./Data/Levels/T1_THE_ARBORETUM/Loot",
        "t2": "./Data/Levels/T2_THE_LOWER_CITY/Loot",
        "t3": "./Data/Levels/T3_THE_WASTELAND/Loot",
        "t4": "./Data/Levels/T4_THE_PLAGUELANDS/Loot",
        "t5": "./Data/Levels/T5_THE_EVERDARK/Loot",
        "t6": "./Data/Levels/T6_THE_STEPPES_OF_CREATION/Loot",
        "t7": "./Data/Levels/T7_THE_CITADEL/Loot",
    }
    with open(fileMap[tier] + "/dropTable.yaml", "r") as stream:
        dropTable = yaml.safe_load(stream)
    if lootType == "any":
        lootType = random.choices(["equipment", "treasure"], weights=[80, 20], k=1)[0]
    drop = random.choices(
        [*dropTable[lootType]], weights=[*dropTable[lootType].values()], k=1
    )[0]
    with open(fileMap[tier] + "/" + drop + ".yaml", "r") as stream:
        dropData = yaml.safe_load(stream)
    logger.debug("Generated new loot from data")
    return dropData


def generatePet():
    with open("Data/Pets/spawnTable.yaml", "r") as stream:
        spawnTable = yaml.safe_load(stream)
    pet = random.choices([*spawnTable], weights=[*spawnTable.values()], k=1)[0]
    with open("Data/Pets/" + pet + ".yaml", "r") as stream:
        petData = yaml.safe_load(stream)
    logger.debug("Generated new pet from data")
    return petData


async def doPetEvents():
    global active_pets
    logger.debug("Pet event")
    for chan in channels["pet-zones"].values():
        if random.uniform(0, 1) > 0.8:
            logger.debug("Spawn roll success")
            pet = Pet()
            backgroundImage = Image(filename="Data/Resources/Images/petStats.png")
            petTypeImage = Image(
                filename=("Data/Resources/Images/" + pet.petType + "_petType.png")
            )
            maskImage = Image(filename="Data/Resources/Images/mask.png")

            def apply_mask(image, mask, invert=False):
                image.alpha_channel = True
                if invert:
                    mask.negate()
                with Image(
                    width=image.width,
                    height=image.height,
                    background=Color("transparent"),
                ) as alpha_image:
                    alpha_image.composite_channel("alpha", mask, "copy_opacity", 0, 0)
                    image.composite_channel("alpha", alpha_image, "multiply", 0, 0)

            bg = backgroundImage.clone()
            pt = petTypeImage.clone().convert("png")
            m = maskImage.clone()

            commonCol = Color("#B9BBBE")
            uncommonCol = Color("#248224")
            rareCol = Color("#2C4399")
            epicCol = Color("#792482")
            legendaryCol = Color("#BA5318")
            zekiforgedCol = Color("#C54EA5")
            if pet.rarity == "Common":
                rarityCol = commonCol
            elif pet.rarity == "Uncommon":
                rarityCol = uncommonCol
            elif pet.rarity == "Rare":
                rarityCol = rareCol
            elif pet.rarity == "Epic":
                rarityCol = epicCol
            elif pet.rarity == "Legendary":
                rarityCol = legendaryCol
            elif pet.rarity == "Zekiforged":
                rarityCol = zekiforgedCol

            with Drawing() as draw:
                pt.resize(128, 128)
                # g.resize(35, 35)
                # r.resize(35, 35)
                # draw.fill_color = Color("black")
                # draw.rectangle(left=int((bg.width/2)-64),top=30,width=128,height=128,radius=64)  # 30% rounding?
                apply_mask(pt, m)
                draw.font = "Data/Resources/Fonts/whitneybold.otf"
                draw.font_size = 18
                draw.fill_color = Color("white")
                draw.text_alignment = "center"
                draw.font_weight = 700
                draw.text(
                    int(bg.width / 2),
                    180,
                    pet.rarity.capitalize() + " " + pet.name,
                )
                draw.font = "Data/Resources/Fonts/whitneybook.otf"
                draw.fill_color = Color("#B4B6B9")
                draw.text(
                    int(bg.width / 2),
                    205,
                    "Type: " + pet.petType.capitalize(),
                )
                draw.font = "Data/Resources/Fonts/whitneybold.otf"
                draw.fill_color = Color("#B9BBBE")
                draw.text(int(bg.width / 2) - 110, 270, "STATS")
                # draw.text(int(bg.width / 2) - 119, 390, "STATS")
                # draw.text(int(bg.width / 2) - 129, 540, "FACT")
                draw.font = "Data/Resources/Fonts/whitneymedium.otf"
                draw.text(int(bg.width / 2), 310, "Damage: " + str(pet.damage))
                draw.text(
                    int(bg.width / 2),
                    330,
                    "Defence: " + str(pet.defence),
                )
                draw.text(
                    int(bg.width / 2),
                    350,
                    "Gold: " + str(pet.gold),
                )
                draw.fill_color = rarityCol
                draw.circle((int(bg.width / 2), 84), (int(bg.width / 2), 20))
                draw.composite(
                    operator="over",
                    left=int((bg.width / 2) - 64),
                    top=20,
                    width=128,
                    height=128,
                    image=pt,
                )
                draw(bg)

                bg.save(
                    filename=(
                        "Data/Dynamic/"
                        + pet.rarity
                        + "-"
                        + pet.name.replace(" ", "").lower()
                        + "_PetStatsOutput.png"
                    )
                )
            logger.debug("Generated pet image")
            try:
                petMsg = await chan.send(
                    file=discord.File(
                        "Data/Dynamic/"
                        + pet.rarity
                        + "-"
                        + pet.name.replace(" ", "").lower()
                        + "_PetStatsOutput.png"
                    )
                )
                logger.debug("Pet message sent")
                active_pets.append([petMsg, pet, 5])
            except:
                logger.error("Tried to send pet message but failed!")
                logger.error(traceback.format_exc())

        for p in active_pets:
            try:
                p[2] = p[2] - 1
                if p[2] < 1:
                    try:
                        await p[0].delete()
                        logger.debug("Deleted pet message")
                    except:
                        logger.error("Tried to time-out pet message but did not exist!")
                        logger.error(traceback.format_exc())
            except:
                logger.error("Tried to modify pet timer but did not exist!")
                logger.error(traceback.format_exc())
        active_pets = [petData for petData in active_pets if petData[2] > 0]
        logger.debug("Refreshed active pets")


async def doHealthRegen():
    global active_mobs
    global players
    global emoji_set
    logger.debug("Health regen event")
    for p in players.values():
        if not p.inCombat:
            if not p.HP == p.maxHP:
                p.HP = p.HP + round((0.1 * p.maxHP))
                if p.HP > p.maxHP:
                    p.HP = p.maxHP
                hpSlots = round((p.HP / p.maxHP) * 10)
                p.hpBar = (emoji_set["greenHP"] * hpSlots) + (
                    emoji_set["redHP"] * (10 - hpSlots)
                )
                logger.debug(p.name + " regenerated HP")
    for m in active_mobs.values():
        if len(m.playersEngaged) == 0:
            if not m.HP == m.maxHP:
                m.HP = m.HP + round((0.1 * m.maxHP))
                if m.HP > m.maxHP:
                    m.HP = m.maxHP
                hpSlots = round((m.HP / m.maxHP) * 10)
                if not hpSlots > -1:
                    hpSlots = 0
                m.hpBar = (emoji_set["greenHP"] * hpSlots) + (
                    emoji_set["redHP"] * (10 - hpSlots)
                )
                await m.hpMessage.edit(
                    content=m.name
                    + " (LVL: "
                    + str(m.level)
                    + ") - "
                    + str(m.HP)
                    + "/"
                    + str(m.maxHP)
                    + "HP"
                    + "\n"
                    + m.hpBar
                )
                logger.debug(m.name + " regenerated HP and edited message")


async def doPlayerFixup():
    global players
    global active_mobs
    # if current_tick == 5:
    invalidPlayers = [
        i
        for i in [p for p in players.values() if p.inCombat]
        if i
        not in [
            players[p]
            for p in [
                item
                for sublist in [m.playersEngaged for m in active_mobs.values()]
                for item in sublist
            ]
        ]
    ]
    # activeEngagedPlayers = [players[p] for p in [item for sublist in [m.playersEngaged for m in active_mobs.values()] for item in sublist]]
    if len(invalidPlayers) > 0:
        logger.warning("FIXING INVALID PLAYERS:")
        logger.warning([p.name for p in invalidPlayers])
        for i in invalidPlayers:
            i.inCombat = False
            i.HP = i.maxHP
            i.hpBar = emoji_set["greenHP"] * 10


async def doCombat():
    global active_mobs
    global players
    global current_tick
    global vc
    logger.debug("Combat event")
    current_tick = current_tick + 1
    logger.debug("Current tick: " + str(current_tick))
    if current_tick > 10:
        logger.debug("Writing player data to file")
        with open("./Data/Players.pkl", "w+b") as f:
            pickle.dump(players, f, pickle.HIGHEST_PROTOCOL)
        current_tick = 0
    for mob in list(active_mobs.values()):
        logger.debug("MOB - " + mob.name)
        pMessage = "Party:"
        if not mob.playersEngaged == []:
            logger.debug("In combat")
            pMessage = pMessage + "\n"
            attackedPlayer = random.choices(
                mob.playersEngaged,
                weights=[p.threat for p in [players[k] for k in mob.playersEngaged]],
                k=1,
            )[0]
            mob.combatRound = mob.combatRound + 1
            damageLog = "Round " + str(mob.combatRound) + ":\n"
            deathEvent = False
            for p in mob.playersEngaged:
                damage = mob.getDamageTaken(players[p].getDamage(mob.combatRound))
                mob.HP = mob.HP - damage
                damageLog = (
                    damageLog
                    + players[p].name
                    + " deals "
                    + str(damage)
                    + " damage to "
                    + mob.name
                    + "\n"
                )
                if players[p].pClass == "mender":
                    heal = round(random.uniform(0.06, 0.08) * damage)
                    damageLog = (
                        damageLog
                        + players[p].name
                        + " heals "
                        + str(heal)
                        + " health to the party!"
                        + "\n"
                    )
                    for g in mob.playersEngaged:
                        players[g].heal(heal)
                        hpSlots = round((players[g].HP / players[g].maxHP) * 10)
                        if not hpSlots > -1:
                            hpSlots = 0
                        players[g].hpBar = (emoji_set["greenHP"] * hpSlots) + (
                            emoji_set["redHP"] * (10 - hpSlots)
                        )

                if p == attackedPlayer:
                    damage = players[p].getDamageTaken(mob.getDamage())
                    players[p].HP = players[p].HP - damage
                    damageLog = (
                        damageLog
                        + mob.name
                        + " deals "
                        + str(damage)
                        + " damage to "
                        + players[p].name
                        + "\n"
                    )
                    if players[p].HP < 1:
                        logger.debug("Player death event - " + players[p].name)
                        deathEvent = True
                        if mob.tier == "t1":
                            x = "the Arboretum"
                        elif mob.tier == "t2":
                            x = "the Lower City"
                        elif mob.tier == "t3":
                            x = "the Wasteland"
                        elif mob.tier == "t4":
                            x = "the Plaguelands"
                        elif mob.tier == "t5":
                            x = "the Everdark"
                        elif mob.tier == "t6":
                            x = "the Steppes of Creation"
                        elif mob.tier == "t7":
                            x = "the Citadel"
                        else:
                            x = "an unknown location"
                        tts = gTTS(
                            players[p].name
                            + " died and lost "
                            + str(round(0.05 * players[p].gold))
                            + " gold "
                            + " in "
                            + x
                            + "!"
                        )
                        tts.save("Data/Resources/Audio/preProcessVoiceFile.mp3")
                        tfm = sox.Transformer()
                        tfm.pitch(-6)
                        tfm.reverb(reverberance=50)
                        tfm.build_file(
                            "Data/Resources/Audio/preProcessVoiceFile.mp3",
                            "Data/Resources/Audio/postProcessVoiceFile.mp3",
                        )
                        vc.play(
                            discord.FFmpegPCMAudio(
                                "Data/Resources/Audio/postProcessVoiceFile.mp3"
                            )
                        )
                        damageLog = (
                            damageLog
                            + players[p].name
                            + " died and lost "
                            + str(round(0.05 * players[p].gold))
                            + " gold!\n"
                        )
                        players[p].gold = players[p].gold - round(
                            0.05 * players[p].gold
                        )
                        players[p].STAT_timesDied = players[p].STAT_timesDied + 1
                        players[p].HP = math.ceil(0.2 * players[p].maxHP)
                        players[p].inCombat = False
                        hpSlots = round((players[p].HP / players[p].maxHP) * 10)
                        players[p].hpBar = (emoji_set["greenHP"] * hpSlots) + (
                            emoji_set["redHP"] * (10 - hpSlots)
                        )
                        if not mob.HP < 1:
                            mob.playersEngaged.remove(p)
                            logger.debug(
                                "Player removed from combat due to death event"
                            )
                    else:
                        hpSlots = round((players[p].HP / players[p].maxHP) * 10)
                        if not hpSlots > -1:
                            hpSlots = 0
                        players[p].hpBar = (emoji_set["greenHP"] * hpSlots) + (
                            emoji_set["redHP"] * (10 - hpSlots)
                        )

                if mob.HP < 1:
                    break
            for p in mob.playersEngaged:
                pMessage = (
                    pMessage
                    + "\n"
                    + players[p].name
                    + players[p].title
                    + " (LVL: "
                    + str(players[p].level)
                    + ") - "
                    + str(players[p].HP)
                    + "/"
                    + str(players[p].maxHP)
                    + "HP"
                    + "\n"
                    + players[p].hpBar
                    + "\n"
                )
            z = await channels["tiers"][mob.tier + "-log"].send(damageLog)
            logger.debug("Damage log sent")
            if deathEvent:
                await z.add_reaction(emoji_set["skull"])
            if mob.HP < 1:
                logger.debug("Mob death event")
                importantEvent = False
                lootLog = mob.defeatText + "\n"
                for p in mob.playersEngaged:
                    mob.lootBonus = mob.lootBonus + players[p].lootBonus
                for p in mob.playersEngaged:
                    players[p].STAT_mobsKilled = players[p].STAT_mobsKilled + 1
                    if mob.name in rat_list:
                        players[p].STAT_ratsBeaten = players[p].STAT_ratsBeaten + 1
                    players[p].inCombat = False
                    pLoot = mob.getLoot(players[p].lootBonus)
                    pEXP = await players[p].giveEXP(pLoot[1], mob.level)
                    pGold = str(players[p].giveGold(pLoot[0], True))
                    # get loot
                    # give to players
                    lootLog = (
                        lootLog
                        + players[p].name
                        + " receives "
                        + pGold
                        + " gold and "
                        + str(pEXP[0])
                        + " EXP\n"
                        + pEXP[1]
                    )
                    if not pEXP[1] == "":
                        importantEvent = True
                    if not pLoot[2] == "Nothing":
                        importantEvent = True
                        lootLog = lootLog + players[p].addLoot(pLoot[2]) + "\n"
                logger.debug("Player EXP + Loot resolved")
                z = await channels["tiers"][mob.tier + "-log"].send(lootLog)
                logger.debug("Loot log sent")
                if importantEvent:
                    await z.add_reaction(emoji_set["important"])
                tier = mob.tier
                active_mobs.pop(tier, None)
                logger.debug("Mob removed from active list")
                msgs = (
                    await channels["tiers"][tier + "-main"].history(limit=200).flatten()
                )
                for msg in msgs:
                    await msg.delete(delay=0.1)
                logger.debug("Deleted mob messages")
                active_mobs[tier] = Mob(tier)
                try:
                    await channels["tiers"][tier + "-main"].send(
                        file=active_mobs[tier].image
                    )
                except:
                    logger.error("Error sending New Mob Image")
                    logger.error(traceback.format_exc())
                reactables[tier + "-hpBar"] = await channels["tiers"][
                    tier + "-main"
                ].send(
                    active_mobs[tier].name
                    + " (LVL: "
                    + str(active_mobs[tier].level)
                    + ") - "
                    + str(active_mobs[tier].HP)
                    + "/"
                    + str(active_mobs[tier].maxHP)
                    + "HP"
                    + "\n"
                    + active_mobs[tier].hpBar
                )
                await reactables[tier + "-hpBar"].add_reaction(emoji_set["swords"])
                active_mobs[tier].hpMessage = reactables[tier + "-hpBar"]
                try:
                    await channels["tiers"][tier + "-main"].send(
                        file=discord.File("Data/Resources/Images/vs.png")
                    )
                except:
                    logger.error("Error sending New VS Image")
                    logger.error(traceback.format_exc())
                active_mobs[tier].partyMessage = await channels["tiers"][
                    tier + "-main"
                ].send("Party:\n")
                logger.debug("Sent mob messages")
                await channels["tiers"][tier + "-log"].send(
                    active_mobs[tier].encounterText
                )
                logger.debug("Sent mob encounter")
                if "Rat" in active_mobs[tier].name:
                    if tier == "t1":
                        x = "the Arboretum"
                    elif tier == "t2":
                        x = "the Lower City"
                    elif tier == "t3":
                        x = "the Wasteland"
                    elif tier == "t4":
                        x = "the Plaguelands"
                    elif tier == "t5":
                        x = "the Everdark"
                    elif tier == "t6":
                        x = "the Steppes of Creation"
                    elif tier == "t7":
                        x = "the Citadel"
                    else:
                        x = "an unknown location"

                    tts = gTTS("A rat has spawned in " + x)
                    tts.save("Data/Resources/Audio/preProcessVoiceFile.mp3")
                    tfm = sox.Transformer()
                    tfm.pitch(-6)
                    tfm.reverb(reverberance=50)
                    tfm.build_file(
                        "Data/Resources/Audio/preProcessVoiceFile.mp3",
                        "Data/Resources/Audio/postProcessVoiceFile.mp3",
                    )
                    vc.play(
                        discord.FFmpegPCMAudio(
                            "Data/Resources/Audio/postProcessVoiceFile.mp3"
                        )
                    )
                    # vc.play(discord.FFmpegPCMAudio("Data/Resources/Audio/rat.mp3"))
            else:
                hpSlots = round((mob.HP / mob.maxHP) * 10)
                if not hpSlots > -1:
                    hpSlots = 0
                mob.hpBar = (emoji_set["greenHP"] * hpSlots) + (
                    emoji_set["redHP"] * (10 - hpSlots)
                )
                if (
                    not mob.hpMessage.content
                    == mob.name
                    + " (LVL: "
                    + str(mob.level)
                    + ") - "
                    + str(mob.HP)
                    + "/"
                    + str(mob.maxHP)
                    + "HP"
                    + "\n"
                    + mob.hpBar
                ):
                    await mob.hpMessage.edit(
                        content=mob.name
                        + " (LVL: "
                        + str(mob.level)
                        + ") - "
                        + str(mob.HP)
                        + "/"
                        + str(mob.maxHP)
                        + "HP"
                        + "\n"
                        + mob.hpBar
                    )
                    logger.debug("Mob message edited")
                if not pMessage == mob.partyMessage.content:
                    await mob.partyMessage.edit(content=pMessage)
                    logger.debug("Party message edited")
        elif not pMessage == mob.partyMessage.content:
            await mob.partyMessage.edit(content=pMessage)
            logger.debug("Party message edited")


class Player:
    def __init__(self, ID, name, pClass, race):
        self.ID = ID
        self.openInventory = False
        self.name = name
        self.pClass = pClass
        self.race = race
        self.title = ", " + pClass.capitalize()
        self.equipment = ["Empty", "Empty"]
        self.inventory = ["Empty", "Empty", "Empty", "Empty", "Empty"]
        self.level = 1
        self.nextLevelEXP = 100
        self.requiredEXP = 100
        self.prestiges = 0
        self.titles = {
            pClass.capitalize(): ", " + pClass.capitalize(),
            "Early Bird": ", Early Bird",
        }
        self.STAT_timesDied = 0
        self.STAT_mobsKilled = 0
        self.STAT_ratsBeaten = 0
        self.STAT_itemsLooted = 0
        self.STAT_goldLooted = 0
        self.STAT_titlesCollected = len(self.titles)
        self.STAT_damageDealt = 0
        self.STAT_damageReceived = 0
        self.ratTrack = {
            "t1": False,
            "t2": False,
            "t3": False,
            "t4": False,
            "t5": False,
            "t6": False,
            "t7": False,
            "grave": False,
            "tavern": False,
            "class": False,
        }
        self.EXP = 0
        self.gold = 0
        self.goldMult = 1
        self.lootBonus = 0
        self.follower = ""
        self.followerStatBonus = 0
        self.inCombat = False
        if pClass == "arcanist":
            self.threat = 10
            self.maxHP = 30
            self.DMG = 38
            self.DFC = 5
        elif pClass == "overseer":
            self.threat = 10
            self.maxHP = 50
            self.DMG = 25
            self.DFC = 10
            self.followerStatBonus = 0.1
        elif pClass == "warden":
            self.threat = 20
            self.maxHP = 80
            self.DMG = 15
            self.DFC = 12
        elif pClass == "mender":
            self.threat = 10
            self.maxHP = 40
            self.DMG = 26
            self.DFC = 8
        elif pClass == "curator":
            self.threat = 10
            self.maxHP = 60
            self.DMG = 22
            self.DFC = 10
            self.lootBonus = 0.05
            self.goldMult = 1.05
        elif pClass == "corsair":
            self.threat = 5
            self.maxHP = 40
            self.DMG = 32
            self.DFC = 5
        elif pClass == "arbiter":
            self.threat = 10
            self.maxHP = 40
            self.DMG = 28
            self.DFC = 10
        elif pClass == "ambassador":
            self.threat = 10
            self.maxHP = 60
            self.DMG = 26
            self.DFC = 11
        else:
            logger.error("Invalid pClass for new Player constructor!")
        if race == "human":
            self.maxHP = self.maxHP + 2
            self.DMG = self.DMG + 1
            self.DFC = self.DFC + 1
        elif race == "troll":
            self.DFC = self.DFC + 2
        elif race == "dwarf":
            self.maxHP = self.maxHP + 8
        elif race == "lizardfolk":
            self.DMG = self.DMG + 4
        elif race == "elf":
            self.DMG = self.DMG + 2
            self.DFC = self.DFC + 1
        elif race == "ascended":
            self.DMG = self.DMG + 2
            self.DFC = self.DFC + 1
            self.maxHP = self.maxHP + 4
        else:
            logger.error("Invalid race for new Player constructor!")
        self.HP = self.maxHP
        self.hpBar = emoji_set["greenHP"] * 10
        logger.info("New player created of ID: " + str(self.ID))

    def getDamage(self, r):
        d = random.uniform(0.9, 1.1) * float(self.DMG)
        damageTypes = []
        tempEquip = self.equipment
        if not tempEquip[0] == "Empty":
            if tempEquip[0].lootType == "weapon":
                if not tempEquip[0].element == "":
                    damageTypes.append(tempEquip[0].element)
                d = d + tempEquip[0].damage
        if not tempEquip[1] == "Empty":
            if tempEquip[1].lootType == "weapon":
                if not tempEquip[1].element == "":
                    damageTypes.append(tempEquip[1].element)
                d = d + tempEquip[1].damage
        if self.pClass == "arbiter":
            self.STAT_damageDealt = self.STAT_damageDealt + round(d * (r * 0.05))
            return round(d + (d * (r * 0.05))), damageTypes
        else:
            self.STAT_damageDealt = self.STAT_damageDealt + round(d)
            return round(d), damageTypes

    def getFollowerDamage(self, d):
        return math.floor(self.followerStatPerc * d)

    def getDamageTaken(self, d):
        actualDFC = self.DFC
        tempEquip = self.equipment
        if not tempEquip[0] == "Empty":
            actualDFC = actualDFC + tempEquip[0].defence
        if not tempEquip[1] == "Empty":
            actualDFC = actualDFC + tempEquip[1].defence
        if d - actualDFC < 1:
            return 0
        else:
            self.STAT_damageReceived = self.STAT_damageReceived + (d - actualDFC)
            return d - actualDFC

    async def giveEXP(self, x, lvl):
        global realm
        lvlDiff = lvl - self.level
        if lvlDiff < -4:
            lvlDiff = -5
        elif lvlDiff > 4:
            lvlDiff = 5
        x = round((((5 + lvlDiff) * 0.2) * x) * (1 + (self.prestiges * 0.05)))
        maxLevel = 60 + (5 * self.prestiges)
        if self.level < maxLevel:
            self.EXP = self.EXP + x
            if self.EXP >= self.nextLevelEXP:
                gained = 0
                while self.EXP >= self.nextLevelEXP:
                    gained = gained + 1
                    self.level = self.level + 1
                    xpScaleDown = 0
                    if self.level > 39:
                        xpScaleDown = 0.03
                    if self.level > 49:
                        xpScaleDown = 0.06
                    self.requiredEXP = self.requiredEXP * (1.18 - xpScaleDown)
                    self.nextLevelEXP = self.nextLevelEXP + self.requiredEXP
                    self.maxHP = round(self.maxHP * 1.1)
                    self.HP = self.maxHP
                    self.hpBar = emoji_set["greenHP"] * 10
                    self.DMG = round(self.DMG * 1.1)
                    self.DFC = round(self.DFC * 1.1)
                    if self.level == 3:
                        await realm.get_member(self.ID).add_roles(roles["tier-access"])
                    elif self.level == 10:
                        await realm.get_member(self.ID).add_roles(roles["shops-basic"])
                    elif self.level == 45:
                        await realm.get_member(self.ID).add_roles(
                            roles["shops-advanced"]
                        )
                    elif self.level == 60:
                        await realm.get_member(self.ID).add_roles(roles["shops-master"])
                    if self.level == maxLevel:
                        self.nextLevelEXP = "MAX LEVEL"
                        break
                if gained == 1:
                    return [x, self.name + " has gained a level!\n"]
                else:
                    return [x, self.name + " has gained " + str(gained) + " levels!\n"]
            return [x, ""]
        else:
            return [0, ""]

    def prestige(self):
        self.level = 1
        self.EXP = 0
        self.nextLevelEXP = 100
        self.requiredEXP = 100
        self.gold = 0
        try:
            self.prestiges = self.prestiges + 1
        except:
            self.prestiges = 1
        if "The Prestigious" not in self.titles:
            self.titles["The Prestigious"] = ", the Prestigious"
            self.STAT_titlesCollected = len(self.titles)
        if self.pClass == "arcanist":
            self.maxHP = 30
            self.DMG = 38
            self.DFC = 5
        elif self.pClass == "overseer":
            self.maxHP = 50
            self.DMG = 25
            self.DFC = 10
        elif self.pClass == "warden":
            self.threat = 20
            self.maxHP = 80
            self.DMG = 15
            self.DFC = 12
        elif self.pClass == "mender":
            self.maxHP = 40
            self.DMG = 26
            self.DFC = 8
        elif self.pClass == "curator":
            self.maxHP = 60
            self.DMG = 22
            self.DFC = 10
        elif self.pClass == "corsair":
            self.maxHP = 40
            self.DMG = 32
            self.DFC = 5
        elif self.pClass == "arbiter":
            self.maxHP = 40
            self.DMG = 28
            self.DFC = 10
        elif self.pClass == "ambassador":
            self.maxHP = 60
            self.DMG = 26
            self.DFC = 11
        else:
            logger.error("Invalid pClass for new player prestige!")
        if self.race == "human":
            self.maxHP = self.maxHP + 2
            self.DMG = self.DMG + 1
            self.DFC = self.DFC + 1
        elif self.race == "troll":
            self.DFC = self.DFC + 2
        elif self.race == "dwarf":
            self.maxHP = self.maxHP + 8
        elif self.race == "lizardfolk":
            self.DMG = self.DMG + 4
        elif self.race == "elf":
            self.DMG = self.DMG + 2
            self.DFC = self.DFC + 1
        elif self.race == "ascended":
            self.DMG = self.DMG + 2
            self.DFC = self.DFC + 1
            self.maxHP = self.maxHP + 4
        else:
            logger.error("Invalid race for new player prestige!")

    def giveGold(self, g, multiply=True):
        if multiply:
            received = round(g * self.goldMult)
        else:
            received = g
        self.gold = round(self.gold + received)
        self.STAT_goldLooted = round(self.STAT_goldLooted + received)
        return received

    def addLoot(self, loot):
        self.STAT_itemsLooted = self.STAT_itemsLooted + 1
        if "Empty" not in self.inventory:
            g = self.giveGold(loot.value, True)
            return (
                self.name
                + " sold a "
                + loot.fullName
                + " they couldn't carry for "
                + str(g)
                + " gold"
            )
        else:
            self.inventory[self.inventory.index("Empty")] = loot
            return self.name + " received " + loot.fullName

    def getBonusStats(self):
        bonusDFC = 0
        bonusDMG = 0
        if not self.equipment[0] == "Empty":
            bonusDFC = bonusDFC + self.equipment[0].defence
            bonusDMG = bonusDMG + self.equipment[0].damage
        if not self.equipment[1] == "Empty":
            bonusDFC = bonusDFC + self.equipment[1].defence
            bonusDMG = bonusDMG + self.equipment[1].damage
        return [bonusDFC, bonusDMG]

    def heal(self, amount):
        if not self.HP < 1:
            self.HP = self.HP + amount
            if self.HP > self.maxHP:
                self.HP = self.maxHP


class Loot:
    def __init__(self, tier, level, lootType="any"):
        lootData = generateLoot(tier, lootType)
        self.name = lootData["name"]
        self.lootType = lootData["type"]
        self.level = level
        self.value = round(random.uniform(0.9, 1.1) * float(lootData["value"]))
        self.description = lootData["description"]
        if self.level == 1:
            lMult = 1
        else:
            lMult = 1.1 ** self.level - 1
        self.value = round(self.value * lMult)
        if not self.lootType == "treasure":
            self.damage = lootData["damage"]
            self.defence = lootData["defence"]
            self.damage = round(self.damage * lMult)
            self.defence = round(self.defence * lMult)

            rarityRoll = random.uniform(0, 1)
            rarityList = [
                "Common",
                "Uncommon",
                "Rare",
                "Epic",
                "Legendary",
                "Zekiforged",
            ]
            if rarityRoll < 0.6:
                self.rarity = "Common"
            elif rarityRoll < 0.865:
                self.rarity = "Uncommon"
            elif rarityRoll < 0.94:
                self.rarity = "Rare"
            elif rarityRoll < 0.975:
                self.rarity = "Epic"
            elif rarityRoll < 0.995:
                self.rarity = "Legendary"
            else:
                self.rarity = "Zekiforged"

            if lootData["defaultRarity"] in rarityList:
                if not rarityList.index(self.rarity) > rarityList.index(
                    lootData["defaultRarity"]
                ):
                    self.rarity = lootData["defaultRarity"]
            if self.rarity == "Uncommon":
                self.damage = round(self.damage * 1.2)
                self.defence = round(self.defence * 1.2)
                self.value = round(self.value * 1.2)
            elif self.rarity == "Rare":
                self.damage = round(self.damage * 1.4)
                self.defence = round(self.defence * 1.4)
                self.value = round(self.value * 1.4)
            elif self.rarity == "Epic":
                self.damage = round(self.damage * 1.6)
                self.defence = round(self.defence * 1.6)
                self.value = round(self.value * 1.6)
            elif self.rarity == "Legendary":
                self.damage = round(self.damage * 2)
                self.defence = round(self.defence * 2)
                self.value = round(self.value * 4)
            elif self.rarity == "Zekiforged":
                self.damage = round(self.damage * 4)
                self.defence = round(self.defence * 4)
                self.value = round(self.value * 8)
            if self.lootType == "weapon":
                elementRoll = random.uniform(0, 1)
                if elementRoll < 0.2:
                    self.element = random.sample(
                        ["Aer", "Terra", "Fyr", "Alica", "Aques", "Flux"], k=1
                    )[0]
                else:
                    self.element = ""
                if (not lootData["defaultElement"] == "None") and self.element == "":
                    self.element = lootData["defaultElement"]
                if not self.element == "":
                    self.fullName = (
                        self.rarity + " " + self.name + " of " + self.element
                    )
                else:
                    self.fullName = self.rarity + " " + self.name
            else:
                self.fullName = self.rarity + " " + self.name
        else:
            self.fullName = self.name


class Mob:
    def __init__(self, tier):
        mobData = generateMob(tier)
        stats = mobData[0]
        self.tier = tier
        self.level = random.sample(tier_levels[self.tier], k=1)[0]
        self.name = stats["name"]
        self.image = discord.File(mobData[1])
        self.maxHP = round(
            (random.sample(range(stats["healthLow"], stats["healthHigh"]), k=1)[0]) * 3
        )
        self.goldReward = round(
            random.sample(range(stats["rewardLow"], stats["rewardHigh"]), k=1)[0]
        )
        self.EXPReward = round(random.uniform(0.8, 1.3) * float(self.goldReward))
        self.dmgLow = stats["dmgLow"]
        self.dmgHigh = stats["dmgHigh"]
        if not self.level == 1:
            lMult = 1.1 ** self.level - 1
            self.maxHP = round(self.maxHP * lMult)
            self.goldReward = round(self.goldReward * lMult)
            self.EXPReward = round(self.EXPReward * lMult)
            self.dmgLow = round(self.dmgLow * lMult)
            self.dmgHigh = round(self.dmgHigh * lMult)
        self.lootBonus = stats["lootBonus"]
        self.encounterText = stats["encounterText"]
        self.defeatText = stats["defeatText"]
        self.weakness = stats["weakness"]
        self.hpBar = emoji_set["greenHP"] * 10
        self.hpMessage = None
        self.partyMessage = None
        self.playersEngaged = []
        self.combatRound = 0
        self.HP = self.maxHP

    def getDamage(self):
        return random.sample(range(self.dmgLow, self.dmgHigh), k=1)[0]

    def getDamageTaken(self, damage_payload):
        if self.weakness in damage_payload[1]:
            d = math.floor(damage_payload[0] * 1.25)
        else:
            d = damage_payload[0]
        return d

    def getLoot(self, playerBonus):
        roll = random.uniform(0, 1)
        req = self.lootBonus + playerBonus + 0.05
        if roll < req:
            return [
                round(random.uniform(0.9, 1.1) * float(self.goldReward)),
                round(random.uniform(1, 1.3) * float(self.EXPReward)),
                Loot(self.tier, self.level),
            ]
        return [
            round(random.uniform(0.9, 1.1) * float(self.goldReward)),
            round(random.uniform(1, 1.3) * float(self.EXPReward)),
            "Nothing",
        ]


class Pet:
    def __init__(self, minRarity="any"):
        petData = generatePet()
        self.name = petData["name"]
        self.damage = petData["damage"]
        self.defence = petData["defence"]
        self.gold = petData["gold"]
        self.petType = petData["type"]
        rarityRoll = random.uniform(0, 1)
        rarityList = [
            "Common",
            "Uncommon",
            "Rare",
            "Epic",
            "Legendary",
            "Zekiforged",
        ]
        if rarityRoll < 0.6:
            self.rarity = "Common"
        elif rarityRoll < 0.865:
            self.rarity = "Uncommon"

        elif rarityRoll < 0.94:
            self.rarity = "Rare"

        elif rarityRoll < 0.975:
            self.rarity = "Epic"

        elif rarityRoll < 0.995:
            self.rarity = "Legendary"
        else:
            self.rarity = "Zekiforged"

        if minRarity in rarityList:
            if not rarityList.index(self.rarity) > rarityList.index(minRarity):
                self.rarity = minRarity
        if self.rarity == "Uncommon":
            self.damage = round(self.damage * 2)
            self.defence = round(self.defence * 2)
            self.gold = round(self.gold * 2)
        elif self.rarity == "Rare":
            self.damage = round(self.damage * 3)
            self.defence = round(self.defence * 3)
            self.gold = round(self.gold * 3)
        elif self.rarity == "Epic":
            self.damage = round(self.damage * 4)
            self.defence = round(self.defence * 4)
            self.gold = round(self.gold * 4)
        elif self.rarity == "Legendary":
            self.damage = round(self.damage * 7)
            self.defence = round(self.defence * 7)
            self.gold = round(self.gold * 7)
        elif self.rarity == "Zekiforged":
            self.damage = round(self.damage * 11)
            self.defence = round(self.defence * 11)
            self.gold = round(self.gold * 11)


@bot.event
async def on_ready():
    global graceful_exit
    logger.info(f"Connection to discord successful as: {bot.user}")
    global realm
    global channels
    global roles
    global reactables
    global players
    global active_mobs
    global vc
    realm = bot.guilds[0]
    channels = {
        "help": realm.get_channel(763273256839938048),
        "admin": realm.get_channel(770931709846749197),
        "guidebook": realm.get_channel(770931709846749196),
        "registration": {
            "register": realm.get_channel(763269562426064906),
            "class-select": realm.get_channel(763269670857736202),
            "race-select": realm.get_channel(763269718676996146),
            "name-select": realm.get_channel(763269914907639808),
        },
        "tiers": {
            "t1-main": realm.get_channel(769546581405204501),
            "t1-log": realm.get_channel(763272419308732416),
            "t2-main": realm.get_channel(770536914910314497),
            "t2-log": realm.get_channel(770536956521873418),
            "t3-main": realm.get_channel(816623602563809280),
            "t3-log": realm.get_channel(816623758600568833),
            "t4-main": realm.get_channel(816628961295466496),
            "t4-log": realm.get_channel(816629013643919390),
            "t5-main": realm.get_channel(816629061979865130),
            "t5-log": realm.get_channel(816629090802073611),
            "t6-main": realm.get_channel(816629159954219029),
            "t6-log": realm.get_channel(816629210780663808),
            "t7-main": realm.get_channel(816629250102788176),
            "t7-log": realm.get_channel(816629286613549096),
        },
        "havens": {
            "the-tavern": realm.get_channel(763300003095117846),
            "the-travelling-caravan": realm.get_channel(817631855603089439),
            "the-bazaar": realm.get_channel(821259911483621376),
        },
        "pet-zones": {
            "the-menagerie": realm.get_channel(818311959047831552),
        },
        "raids": {
            "the-goblins-lair": realm.get_channel(863058019956162570),
        },
    }
    logger.info("Channel IDs Set")
    roles = {
        "class-select": realm.get_role(763270590109843457),
        "race-select": realm.get_role(763270592869695498),
        "name-select": realm.get_role(763270595948970024),
        "character-creation": realm.get_role(763741517948387348),
        "registered": realm.get_role(763671525819023370),
        "arcanist": realm.get_role(762978560624427019),
        "overseer": realm.get_role(763336492146884629),
        "warden": realm.get_role(763336582840320011),
        "mender": realm.get_role(763336604994895873),
        "curator": realm.get_role(763336699245494273),
        "corsair": realm.get_role(763336774021152789),
        "arbiter": realm.get_role(763336807131381800),
        "human": realm.get_role(763382882784772097),
        "troll": realm.get_role(763382887931314196),
        "lizardfolk": realm.get_role(763382889345450075),
        "dwarf": realm.get_role(763382890733633566),
        "elf": realm.get_role(763382893812121610),
        "tier-access": realm.get_role(770537052454125569),
        "shops-basic": realm.get_role(821536199051182101),
        "shops-advanced": realm.get_role(821536448758022144),
        "shops-master": realm.get_role(821537317947834379),
    }
    logger.info("Role IDs Set")
    channel = discord.utils.get(realm.channels, name="the-discordium")
    vc = await channel.connect()
    logger.debug("VC Connection Success")
    with open("./Data/Players.pkl", "rb") as f:
        players = pickle.load(f)
    logger.info("Players Loaded")
    for p in players.values():
        p.inCombat = False
        p.HP = p.maxHP
        p.hpBar = emoji_set["greenHP"] * 10
        reactables["playerInventories"][p.ID] = None
        p.openInventory = False
        logger.debug(p.name + " state reset")
    c = channels["guidebook"]
    msgs = await c.history(limit=200).flatten()
    for msg in msgs:
        await msg.delete(delay=0.2)
    logger.debug("Deleted Guidebook Messages")
    await c.send(
        "** **\n**Rules**\n"
        "1: No NSFW or obscene content outside of marked channels. This includes text, images, or links featuring nudity, sex, hard violence, or other graphically disturbing content.\n"
        "2: Treat everyone with respect. Absolutely no harassment, witch hunting, sexism, racism, or hate speech will be tolerated.\n"
        "3: If you see something against the rules or something that makes you feel unsafe, let staff know. We want this server to be a welcoming space!"
    )

    await c.send(
        "** **\n"
        "**Registration**\n"
        "To get started in Realm, head down to the registration channels and react.\n"
        "As you react to each prompt, a new channel will become available to you.\n"
        "Once you are done, you can start your adventure in #the-arboretum!"
    )
    await c.send(
        "** **\n"
        "**Combat**\n"
        "Combat in realm is pretty simple - head into a channel with an enemy, and react using the crossed swords.\n"
        "Now that you have engaged the mob, combat will happen automatically.\n"
        "Check the matching log channel for details of your fight!"
    )
    await c.send(
        "** **\n"
        "**Loot**\n"
        "After a couple of fights, you might find yourself in possession of some loot.\n"
        "To check it out, open a DM with Realmkeeper and use the !inventory command.\n"
        "Now that you can see your inventory, you can add to the reactions to choose which gear slot you want to move or sell.\n"
    )
    await c.send(
        "** **\n**Buying Gear**\n"
        "Once you reach a certain level, you will be able to access a shop that can sell you gear of your level, among other items.\n"
        "The extra gear useful if you haven't managed to get any good drops lately!\n"
        "Just react to the item you want to buy, and Realmkeeper will send you an offer with cost appropriate for your level."
    )
    await c.send(
        "** **\n"
        "**Pets**\n"
        "Once you reach a certain level, the menagerie will become available to you.\n"
        "Here, you can react to pets to catch them, but be quick, because they could despawn or be caught by another player!\n"
        "Pets provide you a percentage bonus to your stats."
    )
    await c.send(
        "** **\n"
        "**Stat Cards**\n"
        "!stats will give you a statcard generated just for your character! You can also highlight someone with !stats to get a statcard of their character.\n"
    )
    logger.debug("Sent Guidebook Messages")
    for c in channels["registration"].values():
        msgs = await c.history(limit=200).flatten()
        for msg in msgs:
            await msg.delete(delay=0.2)
        logger.debug("Deleted " + c.name + " Messages")
        if c.name == "register":
            reactables["register"] = await c.send(
                "Welcome to Realm! To get started, hit the thumbs up to create your character."
            )
            await reactables["register"].add_reaction(emoji_set["thumbsUP"])
        if c.name == "class-select":
            reactables["class-select-arcanist"] = await c.send(
                "The Arcanist\n"
                "A magic class based on high damage. Has low base HP and high base DMG.\n"
                "Perk: Very high base DMG."
            )
            await reactables["class-select-arcanist"].add_reaction(
                emoji_set["thumbsUP"]
            )
            reactables["class-select-overseer"] = await c.send(
                "The Overseer\n"
                "A pet based class with balanced stats.\n"
                "Perk: Pets are 10% more effective."
            )
            await reactables["class-select-overseer"].add_reaction(
                emoji_set["thumbsUP"]
            )
            reactables["class-select-warden"] = await c.send(
                "The Warden\n"
                "A tank class with extra DFC and HP, but low damage.\n"
                "Perk: Your threat is doubled."
            )
            await reactables["class-select-warden"].add_reaction(emoji_set["thumbsUP"])
            reactables["class-select-mender"] = await c.send(
                "The Mender\n"
                "A healing class with low DFC.\n"
                "Perk: Heal your party for 6-8 percent of your damage each round."
            )
            await reactables["class-select-mender"].add_reaction(emoji_set["thumbsUP"])
            reactables["class-select-curator"] = await c.send(
                "The Curator\n"
                "A wealth based class with balanced stats.\n"
                "Perk: Double the chance of a drop. 5% bonus gold."
            )
            await reactables["class-select-curator"].add_reaction(emoji_set["thumbsUP"])
            reactables["class-select-corsair"] = await c.send(
                "The Corsair\n"
                "An equipment based class with low defensive stats.\n"
                "Perk: Gain an extra handheld slot instead of an armour slot, and halves your threat."
            )
            await reactables["class-select-corsair"].add_reaction(emoji_set["thumbsUP"])
            reactables["class-select-arbiter"] = await c.send(
                "The Arbiter\n"
                "A ranged class that gains more damage the longer a fight goes on.\n"
                "Perk: Gain 5% bonus DMG per round."
            )
            await reactables["class-select-arbiter"].add_reaction(emoji_set["thumbsUP"])
        if c.name == "race-select":
            reactables["race-select-human"] = await c.send(
                "Human\n" "A regular human.\n" "Stats: DMG +1, DFC +1, HP +2"
            )
            await reactables["race-select-human"].add_reaction(emoji_set["thumbsUP"])
            reactables["race-select-troll"] = await c.send(
                "Troll\n"
                "A large, muscled humanoid with intimidating tusks.\n"
                "Stats: DFC +2"
            )
            await reactables["race-select-troll"].add_reaction(emoji_set["thumbsUP"])
            reactables["race-select-lizardfolk"] = await c.send(
                "Lizardfolk\n"
                "A savage race of scaly and aggressive hunters.\n"
                "Stats: DMG +4"
            )
            await reactables["race-select-lizardfolk"].add_reaction(
                emoji_set["thumbsUP"]
            )
            reactables["race-select-dwarf"] = await c.send(
                "Dwarf\n"
                "A stout and kind people, who are most at home in mountains.\n"
                "Stats: HP +8"
            )
            await reactables["race-select-dwarf"].add_reaction(emoji_set["thumbsUP"])
            reactables["race-select-elf"] = await c.send(
                "Elf\n"
                "A proud race of slender and elegant craftspeople, with pointed ears.\n"
                "Stats: DFC+1, DMG +2"
            )
            await reactables["race-select-elf"].add_reaction(emoji_set["thumbsUP"])
        if c.name == "name-select":
            await c.send(
                "Last step!\n"
                "Type a name for your character below.\n"
                "This should be between 1 and 12 characters long, made of letters and spaces only."
            )
        logger.debug("Sent " + c.name + " Messages")
    for t in channels["tiers"]:
        if "main" in t:
            c = channels["tiers"][t]
            msgs = await c.history(limit=200).flatten()
            for msg in msgs:
                await msg.delete(delay=0.2)
            logger.debug("Deleted " + c.name + " Messages")
            active_mobs[t[:2]] = Mob(t[:2])
            await channels["tiers"][t.replace("main", "log")].send(
                active_mobs[t[:2]].encounterText
            )
            try:
                await c.send(file=active_mobs[t[:2]].image)
            except:
                logger.error("Error sending Initial Mob Image for " & str(t[:2]))
                logger.error(traceback.format_exc())
            reactables[t[:2] + "-hpBar"] = await c.send(
                active_mobs[t[:2]].name
                + " (LVL: "
                + str(active_mobs[t[:2]].level)
                + ") - "
                + str(active_mobs[t[:2]].HP)
                + "/"
                + str(active_mobs[t[:2]].maxHP)
                + "\n"
                + active_mobs[t[:2]].hpBar
            )
            await reactables[t[:2] + "-hpBar"].add_reaction(emoji_set["swords"])
            active_mobs[t[:2]].hpMessage = reactables[t[:2] + "-hpBar"]
            try:
                await c.send(file=discord.File("Data/Resources/Images/vs.png"))
            except:
                logger.error("Error sending Initial VS Image for " & str(t[:2]))
                logger.error(traceback.format_exc())
            active_mobs[t[:2]].partyMessage = await c.send("Party:\n")
            if "Rat" in active_mobs[t[:2]].name:
                if t[:2] == "t1":
                    x = "the Arboretum"
                elif t[:2] == "t2":
                    x = "the Lower City"
                elif t[:2] == "t3":
                    x = "the Wasteland"
                elif t[:2] == "t4":
                    x = "the Plaguelands"
                elif t[:2] == "t5":
                    x = "the Everdark"
                elif t[:2] == "t6":
                    x = "the Steppes of Creation"
                elif t[:2] == "t7":
                    x = "the Citadel"
                else:
                    x = "an unknown location"

                tts = gTTS("A rat has spawned in " + x)
                tts.save("Data/Resources/Audio/preProcessVoiceFile.mp3")
                tfm = sox.Transformer()
                tfm.pitch(-6)
                tfm.reverb(reverberance=50)
                tfm.build_file(
                    "Data/Resources/Audio/preProcessVoiceFile.mp3",
                    "Data/Resources/Audio/postProcessVoiceFile.mp3",
                )
                vc.play(
                    discord.FFmpegPCMAudio(
                        "Data/Resources/Audio/postProcessVoiceFile.mp3"
                    )
                )
                # vc.play(discord.FFmpegPCMAudio("Data/Resources/Audio/rat.mp3"))
            logger.debug("Sent " + c.name + " Messages")
    for c in channels["raids"].values():
        msgs = await c.history(limit=200).flatten()
        for msg in msgs:
            await msg.delete(delay=0.2)
        logger.debug("Deleted " + c.name + " Messages")
        reactables[c.name + "-door"] = await c.send(
            "Form a party to challenge the raid boss!"
        )
        await reactables[c.name + "-door"].add_reaction(emoji_set["door"])
        logger.debug("Sent " + c.name + " Messages")
    c = channels["pet-zones"]["the-menagerie"]
    msgs = await c.history(limit=200).flatten()
    for msg in msgs:
        await msg.delete(delay=0.2)
    logger.debug("Deleted " + c.name + " Messages")
    c = channels["havens"]["the-travelling-caravan"]
    msgs = await c.history(limit=200).flatten()
    for msg in msgs:
        await msg.delete(delay=0.2)
    logger.debug("Deleted " + c.name + " Messages")
    await c.send("Welcome to the Travelling Caravan! The wares are as below:")
    reactables["vendors"]["caravan-weapon-lootbox"] = await c.send(
        "Advanced Weapon Lootbox",
        file=discord.File("Data/Resources/Images/LootBoxWeaponAdvanced.png"),
    )
    await reactables["vendors"]["caravan-weapon-lootbox"].add_reaction(
        emoji_set["moneyBag"]
    )
    reactables["vendors"]["caravan-armour-lootbox"] = await c.send(
        "Advanced Armour Lootbox",
        file=discord.File("Data/Resources/Images/LootBoxArmourAdvanced.png"),
    )
    await reactables["vendors"]["caravan-armour-lootbox"].add_reaction(
        emoji_set["moneyBag"]
    )
    logger.debug("Sent " + c.name + " Messages")
    c = channels["havens"]["the-bazaar"]
    msgs = await c.history(limit=200).flatten()
    for msg in msgs:
        await msg.delete(delay=0.2)
    logger.debug("Deleted " + c.name + " Messages")
    await c.send("Welcome to The Bazaar! The wares are as below:")
    reactables["vendors"]["bazaar-weapon-lootbox"] = await c.send(
        "Basic Weapon Lootbox",
        file=discord.File("Data/Resources/Images/LootBoxWeaponBasic.png"),
    )
    await reactables["vendors"]["bazaar-weapon-lootbox"].add_reaction(
        emoji_set["moneyBag"]
    )
    reactables["vendors"]["bazaar-armour-lootbox"] = await c.send(
        "Basic Armour Lootbox",
        file=discord.File("Data/Resources/Images/LootBoxArmourBasic.png"),
    )
    await reactables["vendors"]["bazaar-armour-lootbox"].add_reaction(
        emoji_set["moneyBag"]
    )
    logger.debug("Sent " + c.name + " Messages")
    logger.info("Channel Initialization Complete")
    logger.info("Commencing Cycle")
    while not graceful_exit:
        try:
            await doCombat()
        except:
            logger.error("Error during combat routine")
            logger.error(traceback.format_exc())
        await doHealthRegen()
        await doPetEvents()
        await doPlayerFixup()
        await asyncio.sleep(3)
    await bot.close()


@bot.event
async def on_message(message):
    global players
    global graceful_init
    global graceful_exit
    logger.debug("Message event")
    if not graceful_init:
        if message.channel == channels["help"]:
            if message.content == "!reset":
                players[message.author.id].inCombat = False
                players[message.author.id].HP = players[message.author.id].maxHP
                players[message.author.id].hpBar = emoji_set["greenHP"] * 10
                await message.channel.send("Player State Reset!")
        else:
            if message.channel == channels["registration"]["name-select"]:
                if message.author.bot:
                    return

                await message.author.remove_roles(roles["name-select"])
                if message.author.id in players:
                    logger.warning(
                        "Player attempted new object construction in name-select but was already present!"
                    )
                else:
                    foundClassRole = False
                    foundRaceRole = False
                    for c in class_roles:
                        if roles[c] in message.author.roles:
                            pClass = c
                            foundClassRole = True
                            break
                    for r in race_roles:
                        if roles[r] in message.author.roles:
                            pRace = r
                            foundRaceRole = True
                            break
                    if not foundClassRole:
                        await message.author.send(
                            "Sorry, I tried to register your character but you don't seem to have a class!\n"
                            "Please reach out in the #help channel to get this fixed up."
                        )
                        logger.warning(
                            "Player attempted new object construction in name-select but no class role was found!"
                        )
                        await message.author.add_roles(roles["name-select"])
                    elif not foundRaceRole:
                        await message.author.send(
                            "Sorry, I tried to register your character but you don't seem to have a race!\n"
                            "Please reach out in the #help channel to get this fixed up."
                        )
                        logger.warning(
                            "Player attempted new object construction in name-select but no race role was found!"
                        )
                        await message.author.add_roles(roles["name-select"])
                    else:
                        if not len(message.content) < 13 and len(message.content) > 0:
                            await message.author.send(
                                "Sorry, that name is an improper length! It should be between 1 and 12 characters."
                            )
                            logger.warning(
                                "Player attempted new object construction in name-select but name length was incorrect!"
                            )
                            await message.author.add_roles(roles["name-select"])
                        elif re.match("^[a-zA-Z ]*$", message.content) is None:
                            await message.author.send(
                                "Sorry, that name includes invalid characters! It should contain only letters and spaces."
                            )
                            logger.warning(
                                "Player attempted new object construction in name-select but name characters were invalid!"
                            )
                            await message.author.add_roles(roles["name-select"])
                        else:
                            players[message.author.id] = Player(
                                message.author.id, message.content, pClass, pRace
                            )
                            reactables["playerInventories"][message.author.id] = None
                            await message.author.edit(
                                nick=(
                                    players[message.author.id].name
                                    + players[message.author.id].title
                                )
                            )
                            await message.author.remove_roles(
                                roles["character-creation"]
                            )
                            await message.author.add_roles(roles["registered"])
                            await message.author.send("Character registered!")
                            await message.author.send(
                                "** **\nName: "
                                + players[message.author.id].name
                                + "\nClass: "
                                + players[message.author.id].pClass
                                + "\nRace: "
                                + players[message.author.id].race
                                + "\nDMG: "
                                + str(players[message.author.id].DMG)
                                + "\nDFC: "
                                + str(players[message.author.id].DFC)
                                + "\nMaxHP: "
                                + str(players[message.author.id].maxHP)
                            )
                            await message.author.send(
                                "** **\nYou awaken in a strange forest, the smell of dew thick in the air.\n"
                                "In the distance, you see a city atop a huge hill, the dense trees between you."
                            )
                            with open("./Data/Players.pkl", "w+b") as f:
                                pickle.dump(players, f, pickle.HIGHEST_PROTOCOL)
                await message.delete()

            elif message.content == "!sell_all":
                currentInv = players[message.author.id].inventory
                for i, v in enumerate(currentInv):
                    if not v == "Empty":
                        players[message.author.id].giveGold(v.value, True)
                        await message.author.send(
                            "You sold a "
                            + v.fullName
                            + " for "
                            + str(v.value)
                            + " gold"
                        )
                        currentInv[i] = "Empty"

            elif message.content == "!sell_1":
                currentInv = players[message.author.id].inventory
                if not currentInv[0] == "Empty":
                    players[message.author.id].giveGold(currentInv[0].value, True)
                    await message.author.send(
                        "You sold a "
                        + currentInv[0].fullName
                        + " for "
                        + str(currentInv[0].value)
                        + " gold"
                    )
                    currentInv[0] = "Empty"

            elif message.content == "!sell_2":
                currentInv = players[message.author.id].inventory
                if not currentInv[1] == "Empty":
                    players[message.author.id].giveGold(currentInv[1].value, True)
                    await message.author.send(
                        "You sold a "
                        + currentInv[1].fullName
                        + " for "
                        + str(currentInv[1].value)
                        + " gold"
                    )
                    currentInv[1] = "Empty"

            elif message.content == "!sell_3":
                currentInv = players[message.author.id].inventory
                if not currentInv[2] == "Empty":
                    players[message.author.id].giveGold(currentInv[2].value, True)
                    await message.author.send(
                        "You sold a "
                        + currentInv[2].fullName
                        + " for "
                        + str(currentInv[2].value)
                        + " gold"
                    )
                    currentInv[2] = "Empty"

            elif message.content == "!sell_4":
                currentInv = players[message.author.id].inventory
                if not currentInv[3] == "Empty":
                    players[message.author.id].giveGold(currentInv[3].value, True)
                    await message.author.send(
                        "You sold a "
                        + currentInv[3].fullName
                        + " for "
                        + str(currentInv[3].value)
                        + " gold"
                    )
                    currentInv[3] = "Empty"

            elif message.content == "!sell_5":
                currentInv = players[message.author.id].inventory
                if not currentInv[4] == "Empty":
                    players[message.author.id].giveGold(currentInv[4].value, True)
                    await message.author.send(
                        "You sold a "
                        + currentInv[4].fullName
                        + " for "
                        + str(currentInv[4].value)
                        + " gold"
                    )
                    currentInv[4] = "Empty"

            elif message.content == "!inventory":
                currentPlayer = players[message.author.id]
                currentInv = currentPlayer.inventory
                currentEquipment = currentPlayer.equipment
                if currentPlayer.openInventory:
                    await message.author.send("Inventory already open!")
                else:
                    currentPlayer.openInventory = True
                    inventoryImage = Image(
                        filename="Data/Resources/Images/inventory.png"
                    )
                    emptySlotImage = Image(
                        filename="Data/Resources/Images/emptySlot.png"
                    )
                    itemHeldImage = Image(filename="Data/Resources/Images/itemHeld.png")
                    itemArmourImage = Image(
                        filename="Data/Resources/Images/itemArmour.png"
                    )
                    itemTreasureImage = Image(
                        filename="Data/Resources/Images/treasure.png"
                    )
                    inv = inventoryImage.clone()
                    es = emptySlotImage.clone()
                    ih = itemHeldImage.clone()
                    ia = itemArmourImage.clone()
                    it = itemTreasureImage.clone()
                    emptyCol = Color("#2E3035")
                    commonCol = Color("#B9BBBE")
                    uncommonCol = Color("#248224")
                    rareCol = Color("#2C4399")
                    epicCol = Color("#792482")
                    legendaryCol = Color("#BA5318")
                    zekiforgedCol = Color("#C54EA5")
                    treasureCol = Color("#CA961D")
                    borderCol = Color("#202225")
                    highlightCol = Color("#C63721")
                    highlightCell = 999
                    loop = True
                    while loop:
                        loop = False

                        async def makeInventoryImage():
                            inv = inventoryImage.clone()
                            with Drawing() as draw:
                                draw.font = "Data/Resources/Fonts/whitneybold.otf"
                                draw.font_size = 28
                                draw.fill_color = Color("white")
                                draw.text_alignment = "center"
                                draw.text(100, 60, "Inventory")
                                draw.font_size = 18
                                draw.font = "Data/Resources/Fonts/whitneybold.otf"
                                draw.fill_color = commonCol
                                draw.text(75, 140, "STORAGE")
                                draw.text(930, 140, "EQUIPMENT")
                                draw.font = "Data/Resources/Fonts/whitneymedium.otf"
                                for i in range(1, 6):
                                    if i == highlightCell:
                                        draw.fill_color = highlightCol
                                    else:
                                        draw.fill_color = borderCol
                                    draw.rectangle(
                                        left=(i * 160) - 128,
                                        top=189,
                                        width=149,
                                        height=149,
                                    )
                                    if currentInv[i - 1] == "Empty":
                                        rarityCol = emptyCol
                                        boxImg = es
                                    else:
                                        if currentInv[i - 1].lootType == "treasure":
                                            boxImg = it
                                            rarityCol = treasureCol
                                        else:
                                            if currentInv[i - 1].lootType == "weapon":
                                                boxImg = ih
                                            else:
                                                boxImg = ia
                                            itemRarity = currentInv[
                                                i - 1
                                            ].fullName.split(" ")[0]
                                            rarityCol = commonCol
                                            if itemRarity == "Common":
                                                pass
                                            elif itemRarity == "Uncommon":
                                                rarityCol = uncommonCol
                                            elif itemRarity == "Rare":
                                                rarityCol = rareCol
                                            elif itemRarity == "Epic":
                                                rarityCol = epicCol
                                            elif itemRarity == "Legendary":
                                                rarityCol = legendaryCol
                                            elif itemRarity == "Zekiforged":
                                                rarityCol = zekiforgedCol
                                    draw.fill_color = rarityCol
                                    draw.rectangle(
                                        left=(i * 160) - 123,
                                        top=194,
                                        width=139,
                                        height=139,
                                    )
                                    draw.composite(
                                        operator="over",
                                        left=(i * 160) - 120,
                                        top=200,
                                        width=128,
                                        height=128,
                                        image=boxImg,
                                    )
                                    if not currentInv[i - 1] == "Empty":
                                        draw.fill_color = Color("#B4B6B9")
                                        leftText = 55
                                        downText = 370
                                        draw.text(
                                            (i * 160) - leftText,
                                            downText,
                                            currentInv[i - 1].name,
                                        )
                                        if not currentInv[i - 1].lootType == "treasure":
                                            draw.text(
                                                (i * 160) - leftText,
                                                downText + 30,
                                                "DMG: " + str(currentInv[i - 1].damage),
                                            )
                                            draw.text(
                                                (i * 160) - leftText,
                                                downText + 50,
                                                "DFC: "
                                                + str(currentInv[i - 1].defence),
                                            )
                                            draw.text(
                                                (i * 160) - leftText,
                                                downText + 70,
                                                "Level: "
                                                + str(currentInv[i - 1].level),
                                            )
                                            draw.text(
                                                (i * 160) - leftText,
                                                downText + 90,
                                                "Value: "
                                                + str(currentInv[i - 1].value),
                                            )
                                            # draw.text((i*160)-leftText, 440, currentInv[i-1].description)
                                            if currentInv[i - 1].lootType == "weapon":
                                                if not currentInv[i - 1].element == "":
                                                    draw.text(
                                                        (i * 160) - leftText,
                                                        downText + 110,
                                                        "Element: "
                                                        + currentInv[i - 1].element,
                                                    )
                                        else:
                                            draw.text(
                                                (i * 160) - leftText,
                                                downText + 30,
                                                "Value: "
                                                + str(currentInv[i - 1].value),
                                            )
                                            # draw.text((i*160)-leftText, 380, currentInv[i-1].description)
                                    else:
                                        draw.fill_color = Color("#B4B6B9")
                                        leftText = 55
                                        downText = 370
                                        draw.text(
                                            (i * 160) - leftText, downText, "Empty"
                                        )
                                for i in range(1, 3):
                                    if i + 5 == highlightCell:
                                        draw.fill_color = highlightCol
                                    else:
                                        draw.fill_color = borderCol
                                    draw.rectangle(
                                        left=(i * 160) + 717,
                                        top=189,
                                        width=149,
                                        height=149,
                                    )
                                    if currentEquipment[i - 1] == "Empty":
                                        rarityCol = emptyCol
                                        boxImg = es
                                    else:
                                        if (
                                            currentEquipment[i - 1].lootType
                                            == "treasure"
                                        ):
                                            boxImg = it
                                            rarityCol = treasureCol
                                        else:
                                            if (
                                                currentEquipment[i - 1].lootType
                                                == "weapon"
                                            ):
                                                boxImg = ih
                                            else:
                                                boxImg = ia
                                            itemRarity = currentEquipment[
                                                i - 1
                                            ].fullName.split(" ")[0]
                                            rarityCol = commonCol
                                            if itemRarity == "Common":
                                                pass
                                            elif itemRarity == "Uncommon":
                                                rarityCol = uncommonCol
                                            elif itemRarity == "Rare":
                                                rarityCol = rareCol
                                            elif itemRarity == "Epic":
                                                rarityCol = epicCol
                                            elif itemRarity == "Legendary":
                                                rarityCol = legendaryCol
                                            elif itemRarity == "Zekiforged":
                                                rarityCol = zekiforgedCol
                                    draw.fill_color = rarityCol
                                    draw.rectangle(
                                        left=(i * 160) + 722,
                                        top=194,
                                        width=139,
                                        height=139,
                                    )
                                    draw.composite(
                                        operator="over",
                                        left=(i * 160) + 730,
                                        top=200,
                                        width=128,
                                        height=128,
                                        image=boxImg,
                                    )
                                    if not currentEquipment[i - 1] == "Empty":
                                        draw.fill_color = Color("#B4B6B9")
                                        leftText = 795
                                        downText = 370
                                        draw.text(
                                            (i * 160) + leftText,
                                            downText,
                                            currentEquipment[i - 1].name,
                                        )
                                        if (
                                            not currentEquipment[i - 1].lootType
                                            == "treasure"
                                        ):
                                            draw.text(
                                                (i * 160) + leftText,
                                                downText + 30,
                                                "DMG: "
                                                + str(currentEquipment[i - 1].damage),
                                            )
                                            draw.text(
                                                (i * 160) + leftText,
                                                downText + 50,
                                                "DFC: "
                                                + str(currentEquipment[i - 1].defence),
                                            )
                                            draw.text(
                                                (i * 160) + leftText,
                                                downText + 70,
                                                "Level: "
                                                + str(currentEquipment[i - 1].level),
                                            )
                                            draw.text(
                                                (i * 160) + leftText,
                                                downText + 90,
                                                "Value: "
                                                + str(currentEquipment[i - 1].value),
                                            )
                                            # draw.text((i*160)-leftText, 440, currentEquipment[i-1].description)
                                            if (
                                                currentEquipment[i - 1].lootType
                                                == "weapon"
                                            ):
                                                if (
                                                    not currentEquipment[i - 1].element
                                                    == ""
                                                ):
                                                    draw.text(
                                                        (i * 160) + leftText,
                                                        downText + 110,
                                                        "Element: "
                                                        + currentEquipment[
                                                            i - 1
                                                        ].element,
                                                    )
                                        else:
                                            draw.text(
                                                (i * 160) + leftText,
                                                downText + 30,
                                                "Value: "
                                                + str(currentEquipment[i - 1].value),
                                            )
                                            # draw.text((i*160)-leftText, 380, currentEquipment[i-1].description)
                                    else:
                                        draw.fill_color = Color("#B4B6B9")
                                        leftText = 795
                                        downText = 370
                                        draw.text(
                                            (i * 160) + leftText, downText, "Empty"
                                        )
                                draw(inv)
                                inv.save(
                                    filename=(
                                        "Data/Dynamic/"
                                        + str(currentPlayer.ID)
                                        + "_InventoryOutput.png"
                                    )
                                )

                        await makeInventoryImage()
                        reactables["playerInventories"][
                            currentPlayer.ID
                        ] = await message.author.send(
                            file=discord.File(
                                "Data/Dynamic/"
                                + str(currentPlayer.ID)
                                + "_InventoryOutput.png"
                            )
                        )
                        emojiResponses = [
                            emoji_set["1"],
                            emoji_set["2"],
                            emoji_set["3"],
                            emoji_set["4"],
                            emoji_set["5"],
                            emoji_set["A"],
                            emoji_set["B"],
                        ]
                        for i in range(7):
                            await reactables["playerInventories"][
                                currentPlayer.ID
                            ].add_reaction(emojiResponses[i])

                        def check(r, u):
                            return (
                                (
                                    r.message
                                    == reactables["playerInventories"][currentPlayer.ID]
                                )
                                and (str(r.emoji) in emojiResponses)
                                and (u.id == message.author.id)
                            )

                        try:
                            try:
                                reactionChoiceOne, usr = await bot.wait_for(
                                    "reaction_add", check=check, timeout=20.0
                                )
                            except asyncio.TimeoutError:
                                await message.author.send(
                                    "Time's up - inventory closed!"
                                )
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].delete()
                                reactables["playerInventories"][currentPlayer.ID] = None
                                currentPlayer.openInventory = False
                                return
                            else:
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].delete()
                                reactables["playerInventories"][currentPlayer.ID] = None
                                highlightCell = (
                                    emojiResponses.index(str(reactionChoiceOne.emoji))
                                    + 1
                                )
                                await makeInventoryImage()
                                reactables["playerInventories"][
                                    currentPlayer.ID
                                ] = await message.author.send(
                                    file=discord.File(
                                        (
                                            "Data/Dynamic/"
                                            + str(currentPlayer.ID)
                                            + "_InventoryOutput.png"
                                        )
                                    )
                                )
                                emojiResponses = [
                                    emoji_set["1"],
                                    emoji_set["2"],
                                    emoji_set["3"],
                                    emoji_set["4"],
                                    emoji_set["5"],
                                    emoji_set["A"],
                                    emoji_set["B"],
                                    emoji_set["moneyBag"],
                                ]
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[0])
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[1])
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[2])
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[3])
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[4])
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[5])
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[6])
                                await reactables["playerInventories"][
                                    currentPlayer.ID
                                ].add_reaction(emojiResponses[7])
                                try:
                                    reactionChoiceTwo, usr = await bot.wait_for(
                                        "reaction_add", check=check, timeout=20.0
                                    )
                                except asyncio.TimeoutError:
                                    await message.author.send(
                                        "Time's up - inventory closed!"
                                    )
                                    await reactables["playerInventories"][
                                        currentPlayer.ID
                                    ].delete()
                                    reactables["playerInventories"][
                                        currentPlayer.ID
                                    ] = None
                                    currentPlayer.openInventory = False
                                    return
                                else:
                                    await reactables["playerInventories"][
                                        currentPlayer.ID
                                    ].delete()
                                    reactables["playerInventories"][
                                        currentPlayer.ID
                                    ] = None
                                    highlightCell = 999
                                    slot1 = emojiResponses.index(
                                        str(reactionChoiceOne.emoji)
                                    )
                                    slot2 = emojiResponses.index(
                                        str(reactionChoiceTwo.emoji)
                                    )
                                    weaponCount = 0
                                    armourCount = 0
                                    if (
                                        not players[message.author.id].equipment[0]
                                        == "Empty"
                                    ):
                                        if (
                                            players[message.author.id]
                                            .equipment[0]
                                            .lootType
                                            == "weapon"
                                        ):
                                            weaponCount = weaponCount + 1
                                        if (
                                            players[message.author.id]
                                            .equipment[0]
                                            .lootType
                                            == "armour"
                                        ):
                                            armourCount = armourCount + 1
                                    if (
                                        not players[message.author.id].equipment[1]
                                        == "Empty"
                                    ):
                                        if (
                                            players[message.author.id]
                                            .equipment[1]
                                            .lootType
                                            == "weapon"
                                        ):
                                            weaponCount = weaponCount + 1
                                        if (
                                            players[message.author.id]
                                            .equipment[1]
                                            .lootType
                                            == "armour"
                                        ):
                                            armourCount = armourCount + 1
                                    if slot2 == 7:
                                        if slot1 < 5:
                                            if (
                                                players[message.author.id].inventory[
                                                    slot1
                                                ]
                                                == "Empty"
                                            ):
                                                await message.author.send(
                                                    "That slot is empty!"
                                                )
                                            else:
                                                players[message.author.id].giveGold(
                                                    players[message.author.id]
                                                    .inventory[slot1]
                                                    .value,
                                                    True,
                                                )
                                                await message.author.send(
                                                    "You sold a "
                                                    + players[message.author.id]
                                                    .inventory[slot1]
                                                    .fullName
                                                    + " for "
                                                    + str(
                                                        players[message.author.id]
                                                        .inventory[slot1]
                                                        .value
                                                    )
                                                    + " gold"
                                                )
                                                players[message.author.id].inventory[
                                                    slot1
                                                ] = "Empty"
                                        else:
                                            if (
                                                players[message.author.id].equipment[
                                                    slot1 - 5
                                                ]
                                                == "Empty"
                                            ):
                                                await message.author.send(
                                                    "That slot is empty!"
                                                )
                                            else:
                                                players[message.author.id].giveGold(
                                                    players[message.author.id]
                                                    .equipment[slot1 - 5]
                                                    .value,
                                                    True,
                                                )
                                                await message.author.send(
                                                    "You sold a "
                                                    + players[message.author.id]
                                                    .equipment[slot1 - 5]
                                                    .fullName
                                                    + " for "
                                                    + str(
                                                        players[message.author.id]
                                                        .equipment[slot1 - 5]
                                                        .value
                                                    )
                                                    + " gold"
                                                )
                                                players[message.author.id].equipment[
                                                    slot1 - 5
                                                ] = "Empty"
                                    else:  # BOTH IN INVENTORY
                                        if slot1 < 5 and slot2 < 5:
                                            (
                                                players[message.author.id].inventory[
                                                    slot1
                                                ],
                                                players[message.author.id].inventory[
                                                    slot2
                                                ],
                                            ) = (
                                                players[message.author.id].inventory[
                                                    slot2
                                                ],
                                                players[message.author.id].inventory[
                                                    slot1
                                                ],
                                            )
                                        elif (
                                            slot1 > 4 and slot2 > 4
                                        ):  # BOTH IN EQUIPMENT
                                            (
                                                players[message.author.id].equipment[
                                                    slot1 - 5
                                                ],
                                                players[message.author.id].equipment[
                                                    slot2 - 5
                                                ],
                                            ) = (
                                                players[message.author.id].equipment[
                                                    slot2 - 5
                                                ],
                                                players[message.author.id].equipment[
                                                    slot1 - 5
                                                ],
                                            )
                                        elif (
                                            slot1 > 4 and slot2 < 5
                                        ):  # FIRSTCLICK IN EQUIPMENT SECONDCLICK IN INVENTORY
                                            if (
                                                not players[
                                                    message.author.id
                                                ].inventory[slot2]
                                                == "Empty"
                                            ):
                                                if (
                                                    not players[message.author.id]
                                                    .inventory[slot2]
                                                    .lootType
                                                    == "treasure"
                                                ):
                                                    if (
                                                        players[
                                                            message.author.id
                                                        ].pClass
                                                        == "corsair"
                                                    ):
                                                        if (
                                                            players[message.author.id]
                                                            .inventory[slot2]
                                                            .lootType
                                                            == "weapon"
                                                        ):
                                                            (
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot1 - 5],
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot2],
                                                            ) = (
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot2],
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot1 - 5],
                                                            )
                                                    else:
                                                        if (
                                                            not players[
                                                                message.author.id
                                                            ].equipment[slot1 - 5]
                                                            == "Empty"
                                                        ):
                                                            swapTo = (
                                                                players[
                                                                    message.author.id
                                                                ]
                                                                .equipment[slot1 - 5]
                                                                .lootType
                                                            )
                                                        else:
                                                            swapTo = "Empty"
                                                        if players[
                                                            message.author.id
                                                        ].inventory[
                                                            slot2
                                                        ].lootType == "weapon" and (
                                                            weaponCount == 0
                                                            or swapTo == "weapon"
                                                        ):
                                                            (
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot1 - 5],
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot2],
                                                            ) = (
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot2],
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot1 - 5],
                                                            )
                                                        elif players[
                                                            message.author.id
                                                        ].inventory[
                                                            slot2
                                                        ].lootType == "armour" and (
                                                            armourCount == 0
                                                            or swapTo == "armour"
                                                        ):
                                                            (
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot1 - 5],
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot2],
                                                            ) = (
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot2],
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot1 - 5],
                                                            )
                                            else:
                                                (
                                                    players[
                                                        message.author.id
                                                    ].equipment[slot1 - 5],
                                                    players[
                                                        message.author.id
                                                    ].inventory[slot2],
                                                ) = (
                                                    players[
                                                        message.author.id
                                                    ].inventory[slot2],
                                                    players[
                                                        message.author.id
                                                    ].equipment[slot1 - 5],
                                                )
                                        else:
                                            if (
                                                not players[
                                                    message.author.id
                                                ].inventory[slot1]
                                                == "Empty"
                                            ):
                                                if (
                                                    not players[message.author.id]
                                                    .inventory[slot1]
                                                    .lootType
                                                    == "treasure"
                                                ):
                                                    if (
                                                        players[
                                                            message.author.id
                                                        ].pClass
                                                        == "corsair"
                                                    ):
                                                        if (
                                                            players[message.author.id]
                                                            .inventory[slot1]
                                                            .lootType
                                                            == "weapon"
                                                        ):
                                                            (
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot1],
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot2 - 5],
                                                            ) = (
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot2 - 5],
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot1],
                                                            )
                                                    else:
                                                        if (
                                                            not players[
                                                                message.author.id
                                                            ].equipment[slot2 - 5]
                                                            == "Empty"
                                                        ):
                                                            swapTo = (
                                                                players[
                                                                    message.author.id
                                                                ]
                                                                .equipment[slot2 - 5]
                                                                .lootType
                                                            )
                                                        else:
                                                            swapTo = "Empty"
                                                        if players[
                                                            message.author.id
                                                        ].inventory[
                                                            slot1
                                                        ].lootType == "weapon" and (
                                                            weaponCount == 0
                                                            or swapTo == "weapon"
                                                        ):
                                                            (
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot1],
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot2 - 5],
                                                            ) = (
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot2 - 5],
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot1],
                                                            )
                                                        elif players[
                                                            message.author.id
                                                        ].inventory[
                                                            slot1
                                                        ].lootType == "armour" and (
                                                            armourCount == 0
                                                            or swapTo == "armour"
                                                        ):
                                                            (
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot1],
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot2 - 5],
                                                            ) = (
                                                                players[
                                                                    message.author.id
                                                                ].equipment[slot2 - 5],
                                                                players[
                                                                    message.author.id
                                                                ].inventory[slot1],
                                                            )
                                            else:
                                                (
                                                    players[
                                                        message.author.id
                                                    ].inventory[slot1],
                                                    players[
                                                        message.author.id
                                                    ].equipment[slot2 - 5],
                                                ) = (
                                                    players[
                                                        message.author.id
                                                    ].equipment[slot2 - 5],
                                                    players[
                                                        message.author.id
                                                    ].inventory[slot1],
                                                )
                                    loop = True
                        except:
                            logger.error("Error in inventory management!")
                            await reactables["playerInventories"][
                                currentPlayer.ID
                            ].delete()
                            currentPlayer.openInventory = False
                            reactables["playerInventories"][currentPlayer.ID] = None
                            logger.error(traceback.format_exc())

            elif message.channel == channels["admin"]:
                if message.author.bot:
                    return
                if message.content == "!makechar":
                    if message.author.id == 137451662817230848:
                        players[message.author.id] = Player(
                            message.author.id, "Varzeki", "ambassador", "ascended"
                        )
                        reactables["playerInventories"][message.author.id] = None

                elif message.content == "!restart":
                    logger.info("Graceful Restart Triggered")
                    graceful_init = True
                    await channels["help"].send("RESTART IN 3 MINUTES")
                    await asyncio.sleep(60)
                    await channels["help"].send("RESTART IN 2 MINUTES")
                    await asyncio.sleep(60)
                    await channels["help"].send("RESTART IN 1 MINUTE")
                    await asyncio.sleep(60)
                    await channels["help"].send("RESTARTING NOW")
                    graceful_exit = True

            if message.channel == channels["havens"]["the-tavern"]:
                if message.content == "!spawn_pet":
                    if players[message.author.id].pClass == "overseer":
                        minRarity = "Epic"
                        pet = Pet(minRarity)
                    else:
                        pet = Pet()
                    backgroundImage = Image(
                        filename="Data/Resources/Images/petStats.png"
                    )
                    petTypeImage = Image(
                        filename=(
                            "Data/Resources/Images/" + pet.petType + "_petType.png"
                        )
                    )
                    maskImage = Image(filename="Data/Resources/Images/mask.png")

                    def apply_mask(image, mask, invert=False):
                        image.alpha_channel = True
                        if invert:
                            mask.negate()
                        with Image(
                            width=image.width,
                            height=image.height,
                            background=Color("transparent"),
                        ) as alpha_image:
                            alpha_image.composite_channel(
                                "alpha", mask, "copy_opacity", 0, 0
                            )
                            image.composite_channel(
                                "alpha", alpha_image, "multiply", 0, 0
                            )

                    bg = backgroundImage.clone()
                    pt = petTypeImage.clone().convert("png")
                    m = maskImage.clone()

                    commonCol = Color("#B9BBBE")
                    uncommonCol = Color("#248224")
                    rareCol = Color("#2C4399")
                    epicCol = Color("#792482")
                    legendaryCol = Color("#BA5318")
                    zekiforgedCol = Color("#C54EA5")
                    if pet.rarity == "Common":
                        rarityCol = commonCol
                    elif pet.rarity == "Uncommon":
                        rarityCol = uncommonCol
                    elif pet.rarity == "Rare":
                        rarityCol = rareCol
                    elif pet.rarity == "Epic":
                        rarityCol = epicCol
                    elif pet.rarity == "Legendary":
                        rarityCol = legendaryCol
                    elif pet.rarity == "Zekiforged":
                        rarityCol = zekiforgedCol

                    with Drawing() as draw:
                        pt.resize(128, 128)
                        # g.resize(35, 35)
                        # r.resize(35, 35)
                        # draw.fill_color = Color("black")
                        # draw.rectangle(left=int((bg.width/2)-64),top=30,width=128,height=128,radius=64)  # 30% rounding?
                        apply_mask(pt, m)
                        draw.font = "Data/Resources/Fonts/whitneybold.otf"
                        draw.font_size = 18
                        draw.fill_color = Color("white")
                        draw.text_alignment = "center"
                        draw.font_weight = 700
                        draw.text(
                            int(bg.width / 2),
                            180,
                            pet.rarity.capitalize() + " " + pet.name,
                        )
                        draw.font = "Data/Resources/Fonts/whitneybook.otf"
                        draw.fill_color = Color("#B4B6B9")
                        draw.text(
                            int(bg.width / 2),
                            205,
                            "Type: " + pet.petType.capitalize(),
                        )
                        draw.font = "Data/Resources/Fonts/whitneybold.otf"
                        draw.fill_color = Color("#B9BBBE")
                        draw.text(int(bg.width / 2) - 110, 270, "STATS")
                        # draw.text(int(bg.width / 2) - 119, 390, "STATS")
                        # draw.text(int(bg.width / 2) - 129, 540, "FACT")
                        draw.font = "Data/Resources/Fonts/whitneymedium.otf"
                        draw.text(int(bg.width / 2), 310, "Damage: " + str(pet.damage))
                        draw.text(
                            int(bg.width / 2),
                            330,
                            "Defence: " + str(pet.defence),
                        )
                        draw.text(
                            int(bg.width / 2),
                            350,
                            "Gold: " + str(pet.gold),
                        )
                        draw.fill_color = rarityCol
                        draw.circle((int(bg.width / 2), 84), (int(bg.width / 2), 20))
                        draw.composite(
                            operator="over",
                            left=int((bg.width / 2) - 64),
                            top=20,
                            width=128,
                            height=128,
                            image=pt,
                        )
                        draw(bg)

                        bg.save(
                            filename=(
                                "Data/Dynamic/"
                                + pet.rarity
                                + "-"
                                + pet.name.replace(" ", "").lower()
                                + "_PetStatsOutput.png"
                            )
                        )
                    try:
                        await message.channel.send(
                            file=discord.File(
                                "Data/Dynamic/"
                                + pet.rarity
                                + "-"
                                + pet.name.replace(" ", "").lower()
                                + "_PetStatsOutput.png"
                            )
                        )
                    except:
                        logger.error("Error sending Pet Image")
                        logger.error(traceback.format_exc())
        await bot.process_commands(message)


@bot.event
async def on_raw_reaction_remove(payload):
    global active_mobs
    global graceful_init
    logger.debug("Raw reaction remove event")
    if not graceful_init:
        channel = await bot.fetch_channel(payload.channel_id)
        user = await bot.fetch_user(payload.user_id)
        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return
        if user.bot:
            return
        for mob in [*active_mobs.values()]:
            if message == mob.hpMessage:
                logger.debug("Reaction removed from Mob")
                if user.id in mob.playersEngaged:
                    mob.playersEngaged.remove(user.id)
                    players[user.id].inCombat = False
                    logger.debug("Player removed from combat")


@bot.event
async def on_reaction_add(reaction, user):
    global active_mobs
    global graceful_init
    logger.debug("Reaction add event")
    found = False
    if not graceful_init:
        message = reaction.message
        e = str(reaction.emoji)

        if user.bot:
            logger.debug("User was bot")
            return
        if message == reactables["register"]:
            found = True
            logger.info("Reaction: register")
            if user.id in players:
                await user.send(
                    "Looks like you've been here before! I'm trying to regenerate your roles now., but if something is missing, please visit the help channel."
                )
                await user.add_roles(roles[players[user.id].race])
                await user.add_roles(roles[players[user.id].pClass])
                await user.add_roles(roles["registered"])
                await user.edit(nick=(players[user.id].name + players[user.id].title))
                await user.send("Roles regenerated! Welcome back.")
            elif not roles["class-select"] in user.roles:
                await user.add_roles(roles["character-creation"])
                await user.add_roles(roles["class-select"])
        elif message in reactables["vendors"].values():
            found = True
            logger.debug("Reaction: vendor")
            if e == emoji_set["moneyBag"]:
                if message == reactables["vendors"]["caravan-weapon-lootbox"]:
                    boxType = "weapon"
                    boxRarity = "advanced"
                elif message == reactables["vendors"]["caravan-armour-lootbox"]:
                    boxType = "armour"
                    boxRarity = "advanced"
                elif message == reactables["vendors"]["bazaar-weapon-lootbox"]:
                    boxType = "weapon"
                    boxRarity = "basic"
                elif message == reactables["vendors"]["bazaar-armour-lootbox"]:
                    boxType = "armour"
                    boxRarity = "basic"
                if boxRarity == "basic":
                    cost = math.ceil(150 * (1.1 ** players[user.id].level))
                elif boxRarity == "advanced":
                    cost = math.ceil(350 * (1.1 ** players[user.id].level))
                buyMessage = await user.send(
                    "This "
                    + boxRarity.capitalize()
                    + " "
                    + boxType.capitalize()
                    + " Lootbox would cost you "
                    + str(cost)
                    + " gold."
                )
                await buyMessage.add_reaction(emoji_set["moneyBag"])

                def check(r, u):
                    return (
                        (r.message == buyMessage)
                        and (str(r.emoji) == emoji_set["moneyBag"])
                        and (u.id == user.id)
                    )

                try:
                    try:
                        react, usr = await bot.wait_for(
                            "reaction_add", check=check, timeout=20.0
                        )
                    except asyncio.TimeoutError:
                        await buyMessage.delete()
                        await user.send("Time's up - no deal!")
                        return
                    else:
                        if players[user.id].gold >= cost:
                            if "Empty" in players[user.id].inventory:
                                players[user.id].gold = players[user.id].gold - cost
                                lootOK = False
                                if boxRarity == "basic":
                                    tier = random.choice(
                                        ["t1", "t2", "t3", "t4", "t5", "t6"]
                                    )
                                    possibleRarities = [
                                        "Common",
                                        "Uncommon",
                                        "Rare",
                                    ]
                                elif boxRarity == "advanced":
                                    tier = "t7"
                                    possibleRarities = [
                                        "Rare",
                                        "Epic",
                                        "Legendary",
                                    ]
                                while not lootOK:
                                    lootGen = Loot(
                                        tier,
                                        players[user.id].level,
                                        "equipment",
                                    )
                                    if (
                                        lootGen.lootType == boxType
                                        and lootGen.rarity in possibleRarities
                                    ):
                                        lootOK = True
                                players[user.id].addLoot(lootGen)
                                await buyMessage.delete()
                                await user.send(
                                    "Sold! You have received a "
                                    + lootGen.fullName
                                    + "."
                                )
                            else:
                                await buyMessage.delete()
                                await user.send("You don't have the space for this!")
                        else:
                            await buyMessage.delete()
                            await user.send("You can't afford this!")
                except:
                    logger.error("Error during lootbox transaction!")
                    logger.error(traceback.format_exc())
        else:
            for cls in class_roles:
                if message == reactables["class-select-" + cls]:
                    found = True
                    logger.debug("Reaction: class-select")
                    await user.remove_roles(roles["class-select"])
                    time.sleep(1)
                    hasRole = False
                    for x in class_roles:
                        if roles[x] in user.roles:
                            hasRole = True
                            break
                    if not hasRole:
                        await user.add_roles(roles[cls])
                        await user.add_roles(roles["race-select"])
                    return
            for rce in race_roles:
                if message == reactables["race-select-" + rce]:
                    found = True
                    logger.debug("Reaction: race-select")
                    await user.remove_roles(roles["race-select"])
                    time.sleep(1)
                    hasRole = False
                    for x in race_roles:
                        if roles[x] in user.roles:
                            hasRole = True
                            break
                    if not hasRole:
                        await user.add_roles(roles[rce])
                        await user.add_roles(roles["name-select"])
                    return
            if e == emoji_set["swords"]:
                for mob in [*active_mobs.values()]:
                    if message == mob.hpMessage:
                        found = True
                        logger.debug("Reaction: combat with " + mob.name)
                        if user.id not in mob.playersEngaged:
                            if not len(mob.playersEngaged) > 3:
                                if not players[user.id].inCombat:
                                    mob.playersEngaged.append(user.id)
                                    if user.id in mob.playersEngaged:
                                        players[user.id].inCombat = True
                                else:
                                    await user.send("You are already in combat!")
                            else:
                                await user.send(
                                    "There is already a full party fighting this mob!"
                                )
                        else:
                            pass
    if not found:
        logger.debug("Reaction target invalid")


@bot.command()
async def addxp(ctx, passedMember: discord.Member, passedXP: int):

    logger.info("ADMIN: XP command used by " + str(ctx.author.name))
    global players
    if ctx.channel == channels["admin"]:
        if passedMember.id in players:
            await players[passedMember.id].giveEXP(
                passedXP, players[passedMember.id].level
            )
            await ctx.send(
                "Gave " + players[passedMember.id].name + " " + str(passedXP) + "XP"
            )
        else:
            await ctx.send("Not a registered player")


@bot.command()
async def test_audio(ctx, *, args):

    logger.info("ADMIN: test_audio command used by " + str(ctx.author.name))
    global players
    if ctx.channel == channels["admin"]:
        logger.debug(args)
        tts = gTTS(args)
        tts.save("Data/Resources/Audio/preProcessVoiceFile.mp3")
        tfm = sox.Transformer()
        tfm.pitch(-6)
        tfm.reverb(reverberance=50)
        tfm.build_file(
            "Data/Resources/Audio/preProcessVoiceFile.mp3",
            "Data/Resources/Audio/postProcessVoiceFile.mp3",
        )
        vc.play(discord.FFmpegPCMAudio("Data/Resources/Audio/postProcessVoiceFile.mp3"))


@bot.command()
async def addgold(ctx, passedMember: discord.Member, passedGold: int):
    logger.info("ADMIN: Gold command used by " + str(ctx.author.name))
    global players
    if ctx.channel == channels["admin"]:
        if passedMember.id in players:

            await ctx.send(
                "Gave "
                + players[passedMember.id].name
                + " "
                + str(players[passedMember.id].giveGold(passedGold))
                + " gold"
            )
        else:
            await ctx.send("Not a registered player")


@bot.command()
async def prestige_fix(ctx):
    global players
    if ctx.channel == channels["admin"]:
        for p in players:
            try:
                logger.debug(str(players[p].prestiges))
            except:
                players[p].prestiges = 0
                logger.warning(players[p].name + " had prestige fixed")


@bot.command()
async def stats(ctx, passedMember: discord.Member = None):
    if passedMember is None:
        passedMember = ctx.author
    if not ctx.channel == channels["help"]:
        if passedMember.id in players:

            def shortFormat(num):
                num = float("{:.3g}".format(num))
                magnitude = 0
                while abs(num) >= 1000:
                    magnitude += 1
                    num /= 1000.0
                return "{}{}".format(
                    "{:f}".format(num).rstrip("0").rstrip("."),
                    ["", "K", "M", "B", "T"][magnitude],
                )

            factList = [
                players[passedMember.id].name
                + " has died "
                + str(players[passedMember.id].STAT_timesDied)
                + " times!",
                players[passedMember.id].name
                + " has killed "
                + str(shortFormat(players[passedMember.id].STAT_mobsKilled))
                + " mobs!",
                players[passedMember.id].name
                + " has bested "
                + str(players[passedMember.id].STAT_ratsBeaten)
                + " rats!",
                players[passedMember.id].name
                + " has received "
                + str(shortFormat(players[passedMember.id].STAT_itemsLooted))
                + " drops!",
                players[passedMember.id].name
                + " has looted "
                + str(shortFormat(players[passedMember.id].STAT_goldLooted))
                + " gold!",
                players[passedMember.id].name
                + " has collected "
                + str(players[passedMember.id].STAT_titlesCollected)
                + " titles!",
                players[passedMember.id].name
                + " has dealt out "
                + str(shortFormat(players[passedMember.id].STAT_damageDealt))
                + " damage!",
                players[passedMember.id].name
                + " has taken "
                + str(shortFormat(players[passedMember.id].STAT_damageReceived))
                + " damage!",
            ]
            await passedMember.avatar_url.save(
                "Data/Dynamic/" + str(passedMember.id) + "_UserImage.png"
            )
            statsImage = Image(filename="Data/Resources/Images/stats.png")
            discordImage = Image(
                filename=("Data/Dynamic/" + str(passedMember.id) + "_UserImage.png")
            )
            maskImage = Image(filename="Data/Resources/Images/mask.png")
            greenHPImage = Image(filename="Data/Resources/Images/greenHP.png")
            redHPImage = Image(filename="Data/Resources/Images/redHP.png")
            dot = Image(
                filename=(
                    "Data/Resources/Images/"
                    + players[passedMember.id].pClass
                    + "Dot.png"
                )
            )

            def apply_mask(image, mask, invert=False):
                image.alpha_channel = True
                if invert:
                    mask.negate()
                with Image(
                    width=image.width,
                    height=image.height,
                    background=Color("transparent"),
                ) as alpha_image:
                    alpha_image.composite_channel("alpha", mask, "copy_opacity", 0, 0)
                    image.composite_channel("alpha", alpha_image, "multiply", 0, 0)

            s = statsImage.clone()
            a = discordImage.clone().convert("png")
            m = maskImage.clone()
            d = dot.clone()
            g = greenHPImage.clone()
            r = redHPImage.clone()
            with Drawing() as draw:
                a.resize(128, 128)
                g.resize(35, 35)
                r.resize(35, 35)
                # draw.fill_color = Color("black")
                # draw.rectangle(left=int((s.width/2)-64),top=30,width=128,height=128,radius=64)  # 30% rounding?
                apply_mask(a, m)
                draw.font = "Data/Resources/Fonts/whitneybold.otf"
                draw.font_size = 18
                draw.fill_color = Color("white")
                draw.text_alignment = "center"
                draw.font_weight = 700
                draw.text(
                    int(s.width / 2),
                    180,
                    players[passedMember.id].name + players[passedMember.id].title,
                )
                draw.font = "Data/Resources/Fonts/whitneybook.otf"
                draw.fill_color = Color("#B4B6B9")
                draw.text(
                    int(s.width / 2),
                    205,
                    "Level: " + str(players[passedMember.id].level),
                )
                draw.font = "Data/Resources/Fonts/whitneybold.otf"
                draw.fill_color = Color("#B9BBBE")
                draw.text(int(s.width / 2) - 110, 270, "HEALTH")
                draw.text(int(s.width / 2) - 119, 390, "STATS")
                draw.text(int(s.width / 2) - 129, 540, "FACT")
                draw.font = "Data/Resources/Fonts/whitneymedium.otf"
                draw.text(
                    int(s.width / 2),
                    350,
                    str(players[passedMember.id].HP)
                    + "/"
                    + str(players[passedMember.id].maxHP)
                    + "HP",
                )
                draw.text(
                    int(s.width / 2),
                    440,
                    "Gold: " + str(players[passedMember.id].gold),
                )
                if players[passedMember.id].nextLevelEXP == "MAX LEVEL":
                    draw.text(
                        int(s.width / 2),
                        420,
                        "Next Level: " + str(players[passedMember.id].nextLevelEXP),
                    )
                else:
                    draw.text(
                        int(s.width / 2),
                        420,
                        "Next Level: "
                        + str(
                            round(
                                players[passedMember.id].nextLevelEXP
                                - players[passedMember.id].EXP
                            )
                        )
                        + "EXP",
                    )
                statBlock = players[passedMember.id].getBonusStats()
                draw.text(
                    int(s.width / 2),
                    460,
                    "DMG: "
                    + str(players[passedMember.id].DMG)
                    + "+"
                    + str(statBlock[1]),
                )
                draw.text(
                    int(s.width / 2),
                    480,
                    "DFC: "
                    + str(players[passedMember.id].DFC)
                    + "+"
                    + str(statBlock[0]),
                )
                draw.text(int(s.width / 2), 580, random.sample(factList, k=1)[0])
                hpSlots = round(
                    (players[passedMember.id].HP / players[passedMember.id].maxHP) * 10
                )
                if not hpSlots == 0:
                    if not hpSlots == 10:
                        for i in range(1, hpSlots + 1):
                            draw.composite(
                                operator="over",
                                left=int(((s.width / 2) - 180) + 33 * i),
                                top=290,
                                width=35,
                                height=35,
                                image=g,
                            )
                    else:
                        for i in range(1, hpSlots):
                            draw.composite(
                                operator="over",
                                left=int(((s.width / 2) - 180) + 33 * i),
                                top=290,
                                width=35,
                                height=35,
                                image=g,
                            )
                if not 10 - hpSlots == 0:
                    for i in range(hpSlots + 1, 10):
                        draw.composite(
                            operator="over",
                            left=int(((s.width / 2) - 180) + 33 * i),
                            top=290,
                            width=35,
                            height=35,
                            image=r,
                        )
                draw.composite(
                    operator="over",
                    left=int((s.width / 2) - 64),
                    top=20,
                    width=128,
                    height=128,
                    image=a,
                )
                draw.composite(
                    operator="over",
                    left=int((s.width / 2) + 22),
                    top=112,
                    width=40,
                    height=40,
                    image=d,
                )
                draw(s)

                s.save(
                    filename=(
                        "Data/Dynamic/" + str(passedMember.id) + "_UserStatsOutput.png"
                    )
                )
            try:
                await ctx.send(
                    file=discord.File(
                        "Data/Dynamic/" + str(passedMember.id) + "_UserStatsOutput.png"
                    )
                )
            except:
                logger.error("Error sending User Stats Image")
                logger.error(traceback.format_exc())
        else:
            await ctx.send("This user doesn't appear to be registered yet!")


@bot.command()
async def prestige(ctx, passedMember: discord.Member):
    logger.info("ADMIN: Prestige command used by " + str(ctx.author.name))
    global players
    if ctx.channel == channels["admin"]:
        if passedMember.id in players:
            players[passedMember.id].prestige()
            await ctx.send("Forced prestige on " + str(players[passedMember.id].name))
        else:
            await ctx.send("Not a registered player")


@bot.command()
async def stop(ctx):
    logger.critical("ADMIN: Stop command used by " + str(ctx.author.name))
    if ctx.channel == channels["admin"]:
        global graceful_exit
        graceful_exit = True


bot.run(TOKEN)
