"""
Module for the user interface of the I Like Trains client
"""
import pygame
import logging

# Configure the logger
logger = logging.getLogger("client.ui")

class UI:
    """Class responsible for the client's user interface"""
    
    def __init__(self, client):
        """Initialize the UI with a reference to the client"""
        self.client = client
        
    def get_player_name(self):
        logger.info("Requesting player name")
        """Display a screen allowing the player to enter their name"""
        if not self.client.is_initialized or self.client.screen is None:
            logger.error("Cannot show name input screen: pygame not initialized")
            return "Player"  # Default name
            
        # Colors
        WHITE = (255, 255, 255)
        BLACK = (0, 0, 0)
        GRAY = (200, 200, 200)
        BLUE = (0, 0, 255)
        RED = (255, 0, 0)
        
        # Font
        font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)
        
        # Variables for input
        input_box = pygame.Rect(self.client.screen_width // 2 - 100, self.client.screen_height // 2, 200, 32)
        color_inactive = GRAY
        color_active = BLUE
        color = color_inactive
        active = True
        text = ""
        done = False
        error_message = ""
        
        # Input loop
        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.client.running = False
                    return "Player"  # Default name if closed
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Activate/deactivate input box if clicked inside/outside
                    active = input_box.collidepoint(event.pos)
                    color = color_active if active else color_inactive
                    
                if event.type == pygame.KEYDOWN:
                    # logger.debug(f"Key pressed: {event.key}")
                    if active:
                        if event.key == pygame.K_RETURN:
                            # Validate name if not empty
                            if text:
                                # Check if name is available on the server
                                if self.client.network.check_name_availability(text):
                                    done = True
                                else:
                                    error_message = f"The name '{text}' is already in use"
                            else:
                                error_message = "Please enter a name"
                        elif event.key == pygame.K_BACKSPACE:
                            text = text[:-1]
                            error_message = ""
                        else:
                            # Limit name length
                            if len(text) < 15:
                                text += event.unicode
                                error_message = ""
            
            # Draw screen
            self.client.screen.fill(WHITE)
            
            # Title
            title = font.render("Enter your name", True, BLACK)
            title_rect = title.get_rect(center=(self.client.screen_width // 2, self.client.screen_height // 2 - 50))
            self.client.screen.blit(title, title_rect)
            
            # Input box
            pygame.draw.rect(self.client.screen, color, input_box, 2)
            text_surface = font.render(text, True, BLACK)
            width = max(200, text_surface.get_width() + 10)
            input_box.w = width
            input_box.x = self.client.screen_width // 2 - width // 2
            self.client.screen.blit(text_surface, (input_box.x + 5, input_box.y + 5))
            
            # Error message
            if error_message:
                error_surface = small_font.render(error_message, True, RED)
                error_rect = error_surface.get_rect(center=(self.client.screen_width // 2, self.client.screen_height // 2 + 50))
                self.client.screen.blit(error_surface, error_rect)
                
            # Instructions
            instructions = small_font.render("Press Enter to validate", True, BLACK)
            instructions_rect = instructions.get_rect(center=(self.client.screen_width // 2, self.client.screen_height // 2 + 80))
            self.client.screen.blit(instructions, instructions_rect)
            
            pygame.display.flip()
            
        return text
