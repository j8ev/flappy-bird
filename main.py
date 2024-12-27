import pygame
import random
import sys
import math
from collections import deque

# Initialize Pygame and its mixer
pygame.init()
pygame.mixer.init()

# Constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
GRAVITY = 0.25
FLAP_STRENGTH = -7
PIPE_SPEED = 3
PIPE_SPAWN_TIME = 1500
PIPE_GAP = 200
GROUND_HEIGHT = 100
PARALLAX_SPEED = 2
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235)
GREEN = (34, 177, 76)
BROWN = (139, 69, 19)
GOLD = (255, 215, 0)

# Set up the game window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Flappy Bird')
clock = pygame.time.Clock()

class Bird:
    def __init__(self):
        self.x = WINDOW_WIDTH // 3
        self.y = WINDOW_HEIGHT // 2
        self.velocity = 0
        self.angle = 0
        self.size = 30
        self.rect = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (self.x, self.y)
        self.flap_animation = 0
        self.animation_speed = 0.2
        self.alive = True
        # Store previous positions for smoother collision detection
        self.position_history = deque(maxlen=5)

    def flap(self):
        if self.alive:
            self.velocity = FLAP_STRENGTH
            self.flap_animation = 1

    def update(self):
        if not self.alive:
            self.velocity = min(self.velocity + GRAVITY * 2, 15)  # Faster fall when dead
        else:
            self.velocity = min(self.velocity + GRAVITY, 10)  # Cap maximum fall speed
            
        # Store previous position
        self.position_history.append((self.x, self.y))
        
        # Update position
        self.y = max(0, min(self.y + self.velocity, WINDOW_HEIGHT - GROUND_HEIGHT - self.size))
        
        # Update rectangle position
        self.rect.center = (self.x, self.y)
        
        # Update rotation based on velocity
        self.angle = max(-90, min(self.velocity * 5, 90))
        
        # Update flap animation
        if self.flap_animation > 0:
            self.flap_animation = max(0, self.flap_animation - self.animation_speed)

    def draw(self):
        # Draw the bird body
        rotated_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(rotated_surface, (255, 255, 0), (self.size//2, self.size//2), self.size//2)
        
        # Add eye
        pygame.draw.circle(rotated_surface, BLACK, (self.size*3//4, self.size//3), self.size//8)
        
        # Rotate the surface
        rotated_surface = pygame.transform.rotate(rotated_surface, self.angle)
        
        # Get the rect for the rotated surface
        rotated_rect = rotated_surface.get_rect(center=self.rect.center)
        
        # Draw the rotated bird
        screen.blit(rotated_surface, rotated_rect)

class Pipe:
    def __init__(self):
        self.width = 70
        self.gap_y = random.randint(PIPE_GAP + 50, WINDOW_HEIGHT - GROUND_HEIGHT - PIPE_GAP - 50)
        self.x = WINDOW_WIDTH
        self.passed = False
        self.scored = False
        
        # Create pipe rectangles with better gap positioning
        self.upper_height = self.gap_y - PIPE_GAP//2
        self.lower_y = self.gap_y + PIPE_GAP//2
        
        self.upper_rect = pygame.Rect(self.x, 0, self.width, self.upper_height)
        self.lower_rect = pygame.Rect(self.x, self.lower_y, 
                                    self.width, WINDOW_HEIGHT - self.lower_y - GROUND_HEIGHT)

    def update(self):
        self.x -= PIPE_SPEED
        self.upper_rect.x = self.x
        self.lower_rect.x = self.x

    def draw(self):
        # Draw pipes
        pygame.draw.rect(screen, GREEN, self.upper_rect)
        pygame.draw.rect(screen, GREEN, self.lower_rect)
        
        # Draw pipe caps
        cap_extend = 5
        pygame.draw.rect(screen, GREEN, 
                        (self.x - cap_extend, self.upper_height - 20, 
                         self.width + cap_extend*2, 20))
        pygame.draw.rect(screen, GREEN, 
                        (self.x - cap_extend, self.lower_y, 
                         self.width + cap_extend*2, 20))

class Background:
    def __init__(self):
        self.scroll = 0
        self.clouds = [(random.randint(0, WINDOW_WIDTH), 
                       random.randint(50, WINDOW_HEIGHT - 200)) 
                      for _ in range(5)]
        self.ground_scroll = 0

    def update(self):
        self.scroll = (self.scroll + PARALLAX_SPEED * 0.5) % WINDOW_WIDTH
        self.ground_scroll = (self.ground_scroll + PIPE_SPEED) % WINDOW_WIDTH
        
        # Update cloud positions
        for i, (x, y) in enumerate(self.clouds):
            x = (x - PARALLAX_SPEED * 0.2) % WINDOW_WIDTH
            self.clouds[i] = (x, y)

    def draw(self):
        # Fill sky
        screen.fill(SKY_BLUE)
        
        # Draw clouds
        for x, y in self.clouds:
            pygame.draw.ellipse(screen, WHITE, (x, y, 100, 40))
            pygame.draw.ellipse(screen, WHITE, (x + 20, y - 20, 80, 40))
        
        # Draw ground
        ground_rect = pygame.Rect(0, WINDOW_HEIGHT - GROUND_HEIGHT, WINDOW_WIDTH, GROUND_HEIGHT)
        pygame.draw.rect(screen, BROWN, ground_rect)
        
        # Draw scrolling grass
        for i in range(-20, WINDOW_WIDTH + 20, 30):
            offset = (i - self.ground_scroll) % WINDOW_WIDTH
            pygame.draw.polygon(screen, GREEN, [
                (offset, WINDOW_HEIGHT - GROUND_HEIGHT),
                (offset + 15, WINDOW_HEIGHT - GROUND_HEIGHT - 15),
                (offset + 30, WINDOW_HEIGHT - GROUND_HEIGHT)
            ])

class Game:
    def __init__(self):
        self.reset()
        self.high_score = 0
        self.can_score = True
        self.debug_mode = False
        
    def reset(self):
        self.bird = Bird()
        self.pipes = []
        self.score = 0
        self.background = Background()
        self.game_over = False
        self.last_pipe = pygame.time.get_ticks()
        self.can_score = True

    def check_collision(self, bird, pipe):
        # More accurate collision detection using the bird's actual shape
        bird_center = pygame.math.Vector2(bird.rect.center)
        
        # Check collision with upper pipe
        if (bird_center.y - bird.size//2 < pipe.upper_height or 
            bird_center.y + bird.size//2 > pipe.lower_y):
            if (pipe.x < bird_center.x + bird.size//2 and 
                pipe.x + pipe.width > bird_center.x - bird.size//2):
                return True
        return False

    def update(self):
        self.background.update()
        
        if not self.game_over:
            current_time = pygame.time.get_ticks()
            
            # Update bird
            self.bird.update()
            
            # Spawn pipes
            if current_time - self.last_pipe > PIPE_SPAWN_TIME:
                self.pipes.append(Pipe())
                self.last_pipe = current_time
            
            # Update and check pipes
            for pipe in self.pipes[:]:
                pipe.update()
                
                # Score points
                if not pipe.scored and pipe.x + pipe.width < self.bird.x:
                    self.score += 1
                    pipe.scored = True
                
                # Check collisions
                if self.check_collision(self.bird, pipe):
                    self.bird.alive = False
                    self.game_over = True
                    self.high_score = max(self.high_score, self.score)
                
                # Remove off-screen pipes
                if pipe.x < -pipe.width:
                    self.pipes.remove(pipe)
            
            # Check ground collision
            if self.bird.y + self.bird.size//2 >= WINDOW_HEIGHT - GROUND_HEIGHT:
                self.bird.alive = False
                self.game_over = True
                self.high_score = max(self.high_score, self.score)
        else:
            # Update bird falling animation when game is over
            self.bird.update()

    def draw(self):
        # Draw background
        self.background.draw()
        
        # Draw pipes
        for pipe in self.pipes:
            pipe.draw()
        
        # Draw bird
        self.bird.draw()
        
        # Draw score
        font = pygame.font.Font(None, 48)
        
        # Draw current score
        score_text = font.render(str(self.score), True, WHITE)
        score_shadow = font.render(str(self.score), True, BLACK)
        score_pos = (WINDOW_WIDTH//2 - score_text.get_width()//2, 50)
        screen.blit(score_shadow, (score_pos[0] + 2, score_pos[1] + 2))
        screen.blit(score_text, score_pos)
        
        # Draw high score
        high_score_text = font.render(f'Best: {self.high_score}', True, GOLD)
        screen.blit(high_score_text, (10, 10))
        
        # Draw game over screen
        if self.game_over:
            game_over_font = pygame.font.Font(None, 36)
            game_over_text = game_over_font.render('Game Over! Press SPACE to restart', True, WHITE)
            text_pos = (WINDOW_WIDTH//2 - game_over_text.get_width()//2, WINDOW_HEIGHT//2)
            screen.blit(game_over_text, text_pos)

def main():
    game = Game()
    
    while True:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game.game_over:
                        game.reset()
                    else:
                        game.bird.flap()
                elif event.key == pygame.K_d:  # Toggle debug mode
                    game.debug_mode = not game.debug_mode
        
        # Update game state
        game.update()
        
        # Draw everything
        game.draw()
        
        # Update display
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
