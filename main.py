import random
import vectorio
import board
import displayio
import time
import digitalio
import adafruit_imageload

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240

allObjects = displayio.Group()
allSprites = []

class Object:
    PLAYER = 0
    ENEMY = 1
    ENEMY_PROJECTILE = 2
    PASSIVE_PART = 3
    SOT_PART = 4
    CHIP_PART = 5
    PLAYER_PROJECTILE = 6
    
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

class Sprite:
    moveRoutine = None
    collisionRoutine = None
    frame = 0
    velocity = [0, 0]
    
    def __init__(self, spriteSheet, spritePalette, spriteIndex, position):
        global allObjects, allSprites
        self.sprite = displayio.TileGrid(spriteSheet, pixel_shader=spritePalette, width=1, height=1, tile_width=20, tile_height=20)
        self.size = [20, 20]
        self.sprite[0] = spriteIndex
        self.sprite.x = position[0]
        self.sprite.y = position[1]
        self.pos = position
        self.velocity = [0, 0]
        allObjects.append(self.sprite)
        allSprites.append(self)
        
    def move(self, xmove, ymove):
        self.sprite.x += xmove
        self.sprite.y += ymove
        if self.sprite.x > DISPLAY_WIDTH:
            self.sprite.x = 0
        elif self.sprite.x < 0:
            self.sprite.x = DISPLAY_WIDTH
        self.pos = [self.sprite.x, self.sprite.y]
            
    def assignMoveRoutine(self, moveRoutine):
        self.moveRoutine = moveRoutine
        
    def assignCollisionRoutine(self, collisionRoutine):
        self.collisionRoutine = collisionRoutine
        
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
            if sprite.sprite != collisionSprite.sprite and checkOverlap(sprite, collisionSprite):
                if sprite.collisionRoutine:
                    sprite.collisionRoutine(sprite, collisionSprite)
                    
def updateSprites():
    for sprite in allSprites:
        sprite.update()

def createProjectile(position, index, velocity):
    global spriteSheet, spritePalette, allObjects, allSprites
    projectile = Sprite(spriteSheet, spritePalette, index, position)
    projectile.assignMoveRoutine(projectileMoveRoutine)
    projectile.velocity = velocity
    return projectile

def enemyCollisionRoutine(sprite, collisionSprite):
    if collisionSprite.sprite[0] == Object.PLAYER_PROJECTILE:
        allObjects.remove(sprite.sprite)
        allSprites.remove(sprite)
        allObjects.remove(collisionSprite.sprite)
        allSprites.remove(collisionSprite)
        return True
    return False

def enemyMoveRoutine(sprite):
    if random.randint(0, 100) == 0:
       createProjectile([sprite.sprite.x, sprite.sprite.y + 20], Object.ENEMY_PROJECTILE, [0, 2])
    if sprite.frame % 4 < 2:
        return
    if sprite.velocity[0] == 0:
        sprite.velocity[0] = 1
    elif sprite.sprite.x > DISPLAY_WIDTH - sprite.sprite.width:
        sprite.velocity[0] = -1
    elif sprite.sprite.x < sprite.sprite.width:
        sprite.velocity[0] = 1
        
def projectileMoveRoutine(sprite):
    if sprite.sprite.y < 0 or sprite.sprite.y > DISPLAY_HEIGHT:
        allObjects.remove(sprite.sprite)
        allSprites.remove(sprite)

def newEnemy():
    global spriteSheet, spritePalette
    enemy = Sprite(spriteSheet, spritePalette, 1, [random.randint(0, DISPLAY_WIDTH), 0])
    enemy.assignMoveRoutine(enemyMoveRoutine)
    enemy.assignCollisionRoutine(enemyCollisionRoutine)
    return enemy
    
def main():
    global spriteSheet, spritePalette
    input = Input([board.BTN_A, board.BTN_B, board.BTN_C])
    board.DISPLAY.root_group = allObjects
    spriteSheet, spritePalette = adafruit_imageload.load("/main_sprites.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
    player = Sprite(spriteSheet, spritePalette, 0, [DISPLAY_WIDTH // 2, 200])
    enemies = []
    enemyMax = 3
    firing = False
    lastShot = time.monotonic()
    while True:
        if len(enemies) < enemyMax and random.randint(0, 100) == 0:
            enemies.append(newEnemy())
        if input.isPressed(Input.LEFT):
            player.velocity[0] = -2
        elif input.isPressed(Input.RIGHT):
            player.velocity[0] = 2
        else:
            player.velocity[0] = 0
        if input.isPressed(Input.CENTER):
            if firing == False:
                firing = True
                createProjectile([player.sprite.x, player.sprite.y - 25], Object.PLAYER_PROJECTILE, [0, -5])
        else:
            firing = False
                

        updateSprites()
        time.sleep(0.01)

if __name__ == "__main__":
    main()