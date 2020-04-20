import pyglet
import os
import modules.globals as g

from modules.utils import resizeimg

os.chdir('../')


class ThreadPic:

    def __init__(self):
        self.window = pyglet.window.Window(g.screenwidth, g.screenheight)
        self.bg = pyglet.resource.image('data/special/greenscreen.png')
        self.image = pyglet.resource.image('data/special/greenscreen.png')
        self.move = 0
        self.bg.width, self.bg.height = g.screenwidth, g.screenheight
        self.sprite = pyglet.sprite.Sprite(img=pyglet.resource.animation('data/special/sans.gif'))
        self.last = g.drawfile
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)

        @self.window.event
        def on_draw():
            self.window.clear()
            self.bg.blit(0, 0)
            if self.last.endswith('.gif'):
                self.sprite.draw()
            elif self.last.endswith('.png'):
                self.image.blit(0 + self.move, 0)

        pyglet.clock.schedule_interval(self.update, 1.0 / 60)
        pyglet.app.run()

    def update(self, dt):
        if g.drawfile:
            if g.drawfile.endswith('.gif'):
                self.drawgif(g.drawfile)
            elif g.drawfile.endswith('.png'):
                self.drawimg(g.drawfile)
            self.last = g.drawfile
            g.drawfile = ''

    def drawimg(self, selected):
        try:
            self.image = pyglet.resource.image(f'{g.res}{selected}')
        except pyglet.resource.ResourceNotFoundException:
            pyglet.resource.reindex()
            self.image = pyglet.resource.image(f'{g.res}{selected}')
        rs = g.screenwidth / g.screenheight
        ri = self.image.width / self.image.height
        self.image.width, self.image.height = resizeimg(ri, rs, self.image, g.screenwidth, g.screenheight)
        self.move = self.window.width - self.image.width  # move to the right corner

    def drawgif(self, selected):
        try:
            self.sprite = pyglet.sprite.Sprite(img=pyglet.resource.animation(f'{g.res}{selected}'))
        except pyglet.resource.ResourceNotFoundException:
            pyglet.resource.reindex()
            try:
                self.sprite = pyglet.sprite.Sprite(img=pyglet.resource.animation(f'{g.res}{selected}'))
            except pyglet.image.ImageDecodeException:
                pass
        except pyglet.image.ImageDecodeException:
            pass
        sprscale = 1
        screenr = g.screenwidth / g.screenheight
        spriter = self.sprite.width / self.sprite.height
        if screenr > spriter:
            sprscale = g.screenheight / self.sprite.height
        elif screenr < spriter or screenr == spriter:
            sprscale = g.screenwidth / self.sprite.width
        self.sprite.scale = sprscale
        self.move = self.window.width - self.sprite.width
        self.sprite.x += self.move
