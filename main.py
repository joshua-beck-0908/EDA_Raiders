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

gameOver = False
allObjects = displayio.Group()
allSprites = []

class MusicPlayer:
    data = []
    noteNumber = 0
    noteTime = 0
    loop = False
    playing = False

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
        self.setFrequency(self.data[self.noteNumber][0])
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
        if self.playing:
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
    
class UIDisplay:
    score = 0
    lives = 3
    quota = [0, 0, 0]
    objects = displayio.Group()
    palette = displayio.Palette(2)
    palette[0] = 0xFF0000
    palette[1] = 0x000000
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        global allObjects
        self.score = 0
        self.lives = 3
        self.quota = [0, 0, 0]
        allObjects.append(self.objects)
        self.divider = vectorio.Rectangle(pixel_shader=self.palette, x=GAME_EDGE, y=0, width=1, height=240)
        self.objects.append(self.divider)
        self.scoreLabel = label.Label(terminalio.FONT, text="Score: " + str(self.score), color=0xFFFFFF, x=10, y=10)
        self.objects.append(self.scoreLabel)

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
    
    def __init__(self, spriteSheet, spritePalette, spriteIndex, position):
        global allObjects, allSprites
        self.sprite = displayio.TileGrid(spriteSheet, pixel_shader=spritePalette, width=1, height=1, tile_width=20, tile_height=20)
        self.size = [20, 20]
        self.sprite[0] = spriteIndex
        self.sprite.x = position[0]
        self.sprite.y = position[1]
        self.pos = position
        self.velocity = [0, 0]
        self.type = spriteIndex
        allObjects.append(self.sprite)
        allSprites.append(self)
        
    def move(self, xmove, ymove):
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
        self.frame += 1
        self.move(*self.velocity)
        if self.moveRoutine:
            self.moveRoutine(self)
            
def checkOverlap(sprite1, sprite2):
    if sprite1.pos[0] > sprite2.pos[0] + sprite2.size[0] or sprite1.pos[0] + sprite1.size[0] < sprite2.pos[0]:
        return False
    elif sprite1.pos[1] > sprite2.pos[1] + sprite2.size[1] or sprite1.pos[1] + sprite1.size[1] < sprite2.pos[1]:
        return False
    else:
        return True
    
def checkCollisions():
    for sprite in allSprites:
        for collisionSprite in allSprites:
            if sprite != collisionSprite and checkOverlap(sprite, collisionSprite):
                if sprite.collisionRoutine:
                    sprite.collisionRoutine(sprite, collisionSprite)
                    
def updateSprites():
    checkCollisions()
    for sprite in allSprites:
        sprite.update()
    for sprite in allSprites:
        removeIfDead(sprite)
        
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
        return True
    return False

def playerCollisionRoutine(sprite, collisionSprite):
    global gameOver
    if collisionSprite.type == Object.ENEMY:
        sprite.kill()
        gameOver = True
        return True
    elif collisionSprite.type == Object.ENEMY_PROJECTILE:
        sprite.kill()
        collisionSprite.kill()
        gameOver = True
        return True

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
    
buttonPad = Input([board.BTN_A, board.BTN_B, board.BTN_C])
gameMusic = MusicPlayer(backgroundMusic, board.SPEAKER, loop=True, volume=4)
gameUi = UIDisplay()

def main():
    global spriteSheet, spritePalette, gameOver
    board.DISPLAY.root_group = allObjects
    spriteSheet, spritePalette = adafruit_imageload.load("/main_sprites.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
    while True:
        player = Sprite(spriteSheet, spritePalette, 0, [GAME_EDGE // 2, 200])
        player.assignCollisionRoutine(playerCollisionRoutine)
        enemies = []
        enemyMax = 3
        firing = False
        gameUi.reset()
        gameMusic.play()
        while not gameOver:
            if len(enemies) < enemyMax and random.randint(0, 100) == 0:
                enemies.append(newEnemy())
            if buttonPad.isPressed(Input.LEFT):
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
            time.sleep(0.01)
        gameOverScreen()
        

def gameOverScreen():
    global gameOver
    gameMusic.stop()
    gameOverText = label.Label(terminalio.FONT, text="GAME OVER", color=0xFFFFFF)
    gameOverText.x = 100
    gameOverText.y = 100
    allObjects.append(gameOverText)
    while not buttonPad.anyKeyPressed():
        time.sleep(0.01)
    gameOver = False
    deleteAll()

if __name__ == "__main__":
    main()