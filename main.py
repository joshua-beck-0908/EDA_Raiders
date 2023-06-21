import random
import vectorio
import terminalio
import board
import displayio
import time
import digitalio
import adafruit_imageload
from adafruit_display_text import label
from theme import theme_data as backgroundMusic
import pwmio
import math

DISPLAY_WIDTH = 320
GAME_EDGE = 290
DISPLAY_HEIGHT = 240
FPS = 30

gameOver = False
victory = False
allObjects = displayio.Group()
allSprites = []

class MusicPlayer:
    data = []
    noteNumber = 0
    noteTime = 0
    loop = False
    playing = False
    paused = False

    def __init__(self, data, pwmPin, loop=False, volume=0.3):
        self.data = data
        self.loop = loop
        self.pwmPin = pwmio.PWMOut(pwmPin, duty_cycle=0, frequency=440, variable_frequency=True)
        self.setVolume(volume)
        self.volume = volume
        self.noteNumber = 0
        
    def play(self):
        self.playing = True
        self.noteNumber = 0
        self.playNextNote()
        
    def stop(self):
        self.playing = False
        self.setVolume(-1)
        
    def pause(self):
        self.paused = True
        self.pwmPin.duty_cycle = 0
        
    def resume(self):
        self.paused = False
        self.playNextNote()
        
    def playNextNote(self):
        if len(self.data) == 0:
            self.playing = False
            return
        if self.noteNumber >= len(self.data):
            if self.loop:
                self.noteNumber = 0
            else:
                self.playing = False
                return
        self.noteTime = self.data[self.noteNumber][1] / 1000
        self.currentFreq = self.data[self.noteNumber][0]
        self.setFrequency(self.currentFreq)
        self.noteStartTime = time.monotonic()
        self.noteNumber += 1
        
        
    def setVolume(self, volume):
        if volume < 0:
            self.pwmPin.duty_cycle = 0
        else:
            self.pwmPin.duty_cycle = int(math.pow(2, volume))
            self.volume = volume

    def setFrequency(self, frequency):
        if frequency > 0:
            self.pwmPin.frequency = frequency
            self.setVolume(self.volume)
        else:
            self.setVolume(-1)
        
    def update(self):
        if self.playing and not self.paused:
            if time.monotonic() - self.noteStartTime > self.noteTime:
                self.playNextNote()
        

class Object:
    PLAYER = 0
    ENEMY = 1
    ENEMY_PROJECTILE = 2
    PASSIVE_PART = 3
    SOT_PART = 4
    CHIP_PART = 5
    PLAYER_PROJECTILE = 6
    ENEMY_2 = 7
    ENEMY_3 = 8
    
class UIDisplay:
    score = 0
    lives = 3
    quota = [0, 0, 0]
    objects = displayio.Group()
    palette = displayio.Palette(2)
    palette[0] = 0xFF0000
    palette[1] = 0x000000
    level = 1
    
    def __init__(self):
        self.reset()
        
    def pauseWithText(self, text):
        gameMusic.pause()
        pauseText = self.addCentreText(text)
        board.DISPLAY.refresh()
        while buttonPad.anyKeyPressed():
            time.sleep(0.1)
        while True:
            if buttonPad.anyKeyPressed():
                break
            time.sleep(0.1)
        gameMusic.resume()
        allObjects.remove(pauseText)
        board.DISPLAY.refresh()

    def addCentreText(self, text):
        global allObjects
        text = label.Label(terminalio.FONT, text=text, color=0xFFFFFF)
        text.x = DISPLAY_WIDTH // 2 - text.width // 2
        text.y = DISPLAY_HEIGHT // 2 - text.height // 2
        allObjects.append(text)
        return text

    def spawnPart(self, sprite, bonus):
        if sprite.type == Object.ENEMY:
            partType = Object.PASSIVE_PART
        elif sprite.type == Object.ENEMY_2:
            partType = Object.SOT_PART
        elif sprite.type == Object.ENEMY_3:
            partType = Object.CHIP_PART
        else:
            return
        
        createProjectile(sprite.pos, partType, [0, 2])
        if bonus:
            createProjectile([sprite.pos[0], sprite.pos[1] + 20], partType, [0, 2])
        
        
        
    def reset(self):
        global allObjects, spriteSheet, spritePalette
        self.score = 0
        self.lives = 3
        self.quota = [0, 0, 0]
        allObjects.append(self.objects)
        for i in range(len(self.objects)):
            del self.objects[0]
        self.divider = vectorio.Rectangle(pixel_shader=self.palette, x=GAME_EDGE, y=0, width=1, height=240)
        self.objects.append(self.divider)
        self.scoreLabel = label.Label(terminalio.FONT, text="Score: " + str(self.score), color=0xFFFFFF, x=10, y=10)
        self.objects.append(self.scoreLabel)
        self.livesSprite = Sprite(spriteSheet, spritePalette, Object.PLAYER, [GAME_EDGE + 5, 10], uiPart=True)
        self.livesLabel = label.Label(terminalio.FONT, text=f'x {self.lives}', color=0xFF0000, x=GAME_EDGE + 5, y=40)
        self.objects.append(self.livesLabel)
        self.quoteSprite = []
        self.quoteLabel = []
        for i in range(3):
            self.quoteSprite.append(Sprite(spriteSheet, spritePalette, Object.PASSIVE_PART + i, [GAME_EDGE + 5, 50 + i * 30], uiPart=True))
            self.quoteLabel.append(label.Label(terminalio.FONT, text=f'x{self.quota[i]:03}', color=0xFF0000, x=GAME_EDGE + 5, y=75 + i * 30))
            self.objects.append(self.quoteLabel[i])
        self.scoreUpdate = False
        self.livesUpdate = False
        self.quotaUpdate = False
            
        
    def loseLife(self):
        global gameOver
        self.lives -= 1
        if self.lives <= 0:
            gameOver = True
        self.livesUpdate = True
                
    def setupQuota(self):
        self.quota = gameLevel.quota
        self.quotaUpdate = True
    
    def collectPart(self, part):
        global victory
        if self.quota[part] > 0:
            self.quota[part] -= 1
        self.quotaUpdate = True
            
        victory = True
        for i in range(3):
            if self.quota[i] > 0:
                victory = False

    def startLevel(self):
        self.setupQuota()
        self.pauseWithText(f'Level {self.level}: {gameLevel.name}')
        
    def addPoints(self, number):
        self.score += number
        self.scoreUpdate = True

    def update(self):
        if self.scoreUpdate:
            self.scoreLabel.text = "Score: " + str(self.score)
            self.scoreUpdate = False
        if self.livesUpdate:
            self.livesLabel.text = f'x {self.lives}'
            self.livesUpdate = False
        if self.quotaUpdate:
            for part in range(3):
                self.quoteLabel[part].text = f'x{self.quota[part]:03}'
            self.quotaUpdate = False

class Level:
    data = {
        1: {
            'name': 'Basics',
            'quota': [5, 0, 0],
            'enemyMax': [2, 0, 0],
            'enemyFrequency': [0.5, 0.0, 0.0]
        }, 

        2: {
            'name': 'Balanced Boards',
            'quota': [5, 5, 0],
            'enemyMax': [2, 2, 0],
            'enemyFrequency': [0.5, 0.5, 0.0]
        },

        3: {
            'name': 'Chip Shortage',
            'quota': [0, 0, 5],
            'enemyMax': [0, 2, 2],
            'enemyFrequency': [0.0, 0.5, 0.5]
        },
        4: {
            'name': 'The Full Stack',
            'quota': [3, 3, 3],
            'enemyMax': [2, 2, 2],
            'enemyFrequency': [0.5, 0.5, 0.5]
        },
        5: {
            'name': 'I only need one',
            'quota': [1, 0, 0],
            'enemyMax': [1, 2, 2],
            'enemyFrequency': [0.05, 0.5, 0.5]
        },
        6: {
            'name': 'Gotta Lotta SOT',
            'quota': [0, 25, 0],
            'enemyMax': [0, 2, 2],
            'enemyFrequency': [0.4, 0.7, 0.5]
        },
        7: {
            'name': 'Maximum Capacity',
            'quota': [30, 0, 0],
            'enemyMax': [2, 3, 3],
            'enemyFrequency': [0.5, 0.5, 0.5]
        }
    }
    current = 0


    def reset(self):
        self.current = 0

    def set(self, level):
        self.current = level
        levelData = self.data[level]
        self.name = levelData['name']
        self.quota = levelData['quota']
        self.enemyMax = levelData['enemyMax']
        
    def next(self):
        self.current += 1
        self.set(self.current)
        
        
class Input:
    buttons = []
    LEFT = 0
    CENTER = 1
    RIGHT = 2
    def __init__(self, buttonPins):
        for pin in buttonPins:
            self.buttons.append(digitalio.DigitalInOut(pin))
            self.buttons[-1].direction = digitalio.Direction.INPUT
            
    def isPressed(self, button):
        return self.buttons[button].value == False
    
    def anyKeyPressed(self):
        for button in self.buttons:
            if button.value == False:
                return True
        return False

class Sprite:
    moveRoutine = None
    collisionRoutine = None
    frame = 0
    velocity = [0, 0]
    isDead = False
    
    def __init__(self, spriteSheet, spritePalette, spriteIndex, position, uiPart=False):
        global allObjects, allSprites
        self.sprite = displayio.TileGrid(spriteSheet, pixel_shader=spritePalette, width=1, height=1, tile_width=20, tile_height=20)
        self.size = [20, 20]
        self.sprite[0] = spriteIndex
        self.sprite.x = position[0]
        self.sprite.y = position[1]
        self.delta = [0, 0]
        self.oldpos = position
        self.pos = position
        self.velocity = [0, 0]
        self.type = spriteIndex
        self.uiPart = uiPart
        self.moveRoutine = None
        self.collisionRoutine = None
        allObjects.insert(0, self.sprite)
        allSprites.append(self)
        
    def collide(self, other):
        if self.uiPart or other.uiPart:
            return False
        if self.collisionRoutine:
            return self.collisionRoutine(self, other)
    
    def movement(self):
        if self.moveRoutine:
            self.moveRoutine(self)
    
    def move(self, xmove, ymove):
        if self.uiPart:
            return
        self.sprite.x += xmove
        self.sprite.y += ymove
        if self.sprite.x > GAME_EDGE - self.size[0]:
            self.sprite.x = 0
        elif self.sprite.x < 0:
            self.sprite.x = GAME_EDGE - self.size[0]
        self.pos = [self.sprite.x, self.sprite.y]
            
    def assignMoveRoutine(self, moveRoutine):
        self.moveRoutine = moveRoutine
        
    def assignCollisionRoutine(self, collisionRoutine):
        self.collisionRoutine = collisionRoutine
        
    def kill(self):
        self.isDead = True
        
    def update(self):
        self.oldpos[0] = self.pos[0]
        self.oldpos[1] = self.pos[1]
        self.frame += 1
        self.move(*self.velocity)
        self.movement()
        self.delta[0] = self.pos[0] - self.oldpos[0]
        self.delta[1] = self.pos[1] - self.oldpos[1]
            
def checkOverlap(sprite1, sprite2):
    if sprite1.pos[0] > sprite2.pos[0] + sprite2.size[0] or sprite1.pos[0] + sprite1.size[0] < sprite2.pos[0]:
        return False
    elif sprite1.pos[1] > sprite2.pos[1] + sprite2.size[1] or sprite1.pos[1] + sprite1.size[1] < sprite2.pos[1]:
        return False
    else:
        return True
    
def checkCollisions():
    for sprite in allSprites:
        if sprite.uiPart or sprite.isDead or sprite.delta == [0, 0]:
            continue
        for otherSprite in allSprites:
            if sprite == otherSprite or otherSprite.isDead or otherSprite.collisionRoutine == None:
                continue
            if checkOverlap(sprite, otherSprite):
                sprite.collide(otherSprite)
                otherSprite.collide(sprite)
                    
def updateSprites():
    for sprite in allSprites:
        sprite.update()
    for sprite in allSprites:
        removeIfDead(sprite)
    checkCollisions()
        
def removeIfDead(sprite):
    if sprite.isDead:
        allObjects.remove(sprite.sprite)
        allSprites.remove(sprite)
    
def deleteAll():
    global allObjects, allSprites
    for n in range(len(allObjects)):
        del allObjects[0]
    allSprites.clear()

def createProjectile(position, index, velocity):
    global spriteSheet, spritePalette, allObjects, allSprites
    projectile = Sprite(spriteSheet, spritePalette, index, position)
    projectile.assignMoveRoutine(projectileMoveRoutine)
    projectile.velocity = velocity
    return projectile

def enemyCollisionRoutine(sprite, collisionSprite):
    if collisionSprite.type == Object.PLAYER_PROJECTILE:
        sprite.kill()
        collisionSprite.kill()
        rand = random.random()
            
        if rand > 0.5:
            gameUi.spawnPart(sprite, bonus=False)
        elif rand > 0.9:
            gameUi.spawnPart(sprite, bonus=True)
        
            
    return False

def playerCollisionRoutine(sprite, collisionSprite):
    global gameOver
    if collisionSprite.type == Object.ENEMY:
        gameUi.loseLife()
        return True
    elif collisionSprite.type == Object.ENEMY_PROJECTILE:
        gameUi.loseLife()
        collisionSprite.kill()
        return True
    elif collisionSprite.type == Object.PASSIVE_PART:
        collisionSprite.kill()
        gameUi.collectPart(0)
        gameUi.addPoints(5)
        return True
    elif collisionSprite.type == Object.SOT_PART:
        collisionSprite.kill()
        gameUi.collectPart(1)
        gameUi.addPoints(10)
        return True
    elif collisionSprite.type == Object.CHIP_PART:
        collisionSprite.kill()
        gameUi.collectPart(2)
        gameUi.addPoints(25)
        return True
    else:
        return False

def enemyMoveRoutine(sprite):
    if random.randint(0, 100) == 0:
        createProjectile([sprite.sprite.x, sprite.sprite.y + 20], Object.ENEMY_PROJECTILE, [0, 2])
    if sprite.frame % 4 < 2:
        return
    if sprite.velocity[0] == 0:
        sprite.velocity[0] = 1
    elif sprite.sprite.x > GAME_EDGE - sprite.size[0] - 10:
        sprite.velocity[0] = -1
    elif sprite.sprite.x < sprite.size[0]:
        sprite.velocity[0] = 1
        
def projectileMoveRoutine(sprite):
    if sprite.sprite.y < 0 or sprite.sprite.y > DISPLAY_HEIGHT:
        allObjects.remove(sprite.sprite)
        allSprites.remove(sprite)

def newEnemy():
    global spriteSheet, spritePalette
    enemy = Sprite(spriteSheet, spritePalette, 1, [random.randint(0, GAME_EDGE), 0])
    enemy.assignMoveRoutine(enemyMoveRoutine)
    enemy.assignCollisionRoutine(enemyCollisionRoutine)
    return enemy
    
spriteSheet, spritePalette = adafruit_imageload.load("/main_sprites.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
buttonPad = Input([board.BTN_A, board.BTN_B, board.BTN_C])
gameMusic = MusicPlayer(backgroundMusic, board.SPEAKER, loop=True, volume=4)
gameUi = UIDisplay()
gameLevel = Level()

def main():
    global spriteSheet, spritePalette, gameOver, victory
    board.DISPLAY.root_group = allObjects
    board.DISPLAY.auto_refresh = False
    lastFrame = time.monotonic()
    while True:
        player = Sprite(spriteSheet, spritePalette, 0, [GAME_EDGE // 2, 200])
        player.assignCollisionRoutine(playerCollisionRoutine)
        gameLevel.next()
        enemies = []
        enemyMax = 3
        firing = False
        pressToStart()
        gameMusic.play()
        gameUi.startLevel()
        while not gameOver:
            if len(enemies) < enemyMax and random.randint(0, 100) == 0:
                enemies.append(newEnemy())
            if buttonPad.isPressed(Input.LEFT):
                if buttonPad.isPressed(Input.RIGHT):
                    player.velocity[0] = 0
                    gameUi.pauseWithText("PAUSED")
                player.velocity[0] = -2
            elif buttonPad.isPressed(Input.RIGHT):
                player.velocity[0] = 2
            else:
                player.velocity[0] = 0
            if buttonPad.isPressed(Input.CENTER):
                if firing == False:
                    firing = True
                    createProjectile([player.sprite.x, player.sprite.y - 25], Object.PLAYER_PROJECTILE, [0, -5])
            else:
                firing = False
                    
            for enemy in enemies:
                if enemy.isDead:
                    enemies.remove(enemy)

            updateSprites()
            gameMusic.update()
            gameUi.update()
            board.DISPLAY.refresh()
            frameDelay = 1 / FPS - (time.monotonic() - lastFrame)
            if frameDelay > 0:
                time.sleep(frameDelay)
                
            if victory:
                gameUi.addCentreText("VICTORY")
                deleteAll()
                gameLevel.next()
                victory = False
                gameUi.reset()
                gameMusic.play()
        gameOverScreen()
        

def pressToStart():
    gameUi.pauseWithText("PRESS ANY BUTTON TO START")
    
def gameOverScreen():
    global gameOver
    gameUi.pauseWithText("GAME OVER")
    gameMusic.stop()
    board.DISPLAY.refresh()
    while not buttonPad.anyKeyPressed():
        time.sleep(0.01)
    board.DISPLAY.refresh()
    gameOver = False
    deleteAll()
    gameUi.reset()
    gameLevel.reset()

if __name__ == "__main__":
    main()