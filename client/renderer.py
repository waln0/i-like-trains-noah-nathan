"""
Graphics rendering module for the I Like Trains client
"""
import pygame
import logging
import time

# Configure logger
logger = logging.getLogger("client.renderer")

class Renderer:
    """Class responsible for rendering the game"""
    
    def __init__(self, client):
        """Initialize renderer with a reference to the client"""
        self.client = client
        self.sorted_trains = []
        
    def draw_game(self):
        """Draws the game."""
        # Check if screen is available
        if not self.client.is_initialized or self.client.screen is None:
            logger.error("Cannot draw game: pygame not initialized or screen is None")
            return
            
        try:
            # Fill screen with background color (white)
            self.client.screen.fill((255, 255, 255))
    
            # If in waiting room, display waiting screen
            if self.client.in_waiting_room:
                self.draw_waiting_room()
                # Update display
                pygame.display.flip()
                return
    
            try:
                # Calculate grid size to be square with a small bottom margin
                margin_bottom = 10  # Bottom margin
                grid_area_size = min(self.client.game_width, self.client.game_height)
                
                # Draw a light grid
                grid_color = (230, 230, 230)  # Very light gray
                for x in range(0, grid_area_size, self.client.grid_size):
                    pygame.draw.line(self.client.screen, grid_color, (x, 0), (x, grid_area_size), 1)
                for y in range(0, grid_area_size, self.client.grid_size):
                    pygame.draw.line(self.client.screen, grid_color, (0, y), (grid_area_size, y), 1)
            except Exception as e:
                logger.error("Error drawing grid: " + str(e))

            try:
                self.draw_passengers()
            except Exception as e:
                logger.error("Error drawing passengers: " + str(e))

            try:
                self.draw_trains()
            except Exception as e:
                logger.error("Error drawing trains: " + str(e))

            try:
                # Draw leaderboard on the right
                self.draw_leaderboard()
            except Exception as e:
                logger.error("Error drawing leaderboard: " + str(e))
            
            if self.client.agent.is_dead and not self.client.in_waiting_room:
                try:
                    self.draw_death_screen()
                except Exception as e:
                    logger.error("Error drawing death screen: " + str(e))

            # Update display
            pygame.display.flip()
            
        except Exception as e:
            logger.error("Error drawing game: " + str(e))
            import traceback
            logger.error(traceback.format_exc())

    def draw_passengers(self): # The student has to implement this method
        # Draw passengers
        for passenger in self.client.passengers:
            # Tip: You can access the passenger's position with passenger["position"]  
            continue

    def draw_trains(self): # The student has to implement this method
        # Draw trains
        for train_name, train_data in self.client.trains.items():
            # Tip: You can access the train's position with train_data.get("position", (0, 0))
            continue

    def draw_waiting_room(self):
        """Display the waiting room screen"""
        # Check if screen is available
        if not self.client.is_initialized or self.client.screen is None:
            logger.error("Cannot draw waiting room: pygame not initialized or screen is None")
            return
            
        try:
            # Fill screen with background color
            self.client.screen.fill((240, 240, 255))  # Very light blue
            
            # Waiting room title
            font_title = pygame.font.Font(None, 48)
            title = font_title.render("Waiting Room", True, (0, 0, 100))
            title_rect = title.get_rect(center=(self.client.screen_width // 2, 50))
            self.client.screen.blit(title, title_rect)
            
            # Display waiting room information if available
            if self.client.waiting_room_data and self.client.in_waiting_room:
                # Display players in room
                font = pygame.font.Font(None, 32)
                players = self.client.waiting_room_data.get("players", [])
                
                # Display player count and maximum
                nb_players = self.client.waiting_room_data.get("nb_players", 0)
                players_count = len(players)
                count_text = font.render("Players: " + str(players_count) + "/" + str(nb_players), True, (0, 0, 100))
                self.client.screen.blit(count_text, (50, 80))
                
                # Player list title
                players_title = font.render("Players:", True, (0, 0, 100))
                self.client.screen.blit(players_title, (50, 120))
                
                # Column configuration
                column_width = 250
                players_per_column = 6
                start_y = 160
                
                # List players in two columns
                for i, player in enumerate(players):
                    column = i // players_per_column
                    row = i % players_per_column
                    x = 70 + (column * column_width)
                    y = start_y + (row * 40)
                    
                    player_text = font.render(str(i+1) + ". " + str(player), True, (0, 0, 0))
                    self.client.screen.blit(player_text, (x, y))
                
                # Display message about how to start game
                start_font = pygame.font.Font(None, 36)
                if players_count >= nb_players:  # At least one player to start
                    start_text = start_font.render("Press SPACE to start the game", True, (0, 150, 0))
                else:
                    start_text = start_font.render("Waiting for players...", True, (150, 0, 0))
                start_rect = start_text.get_rect(center=(self.client.screen_width // 2, self.client.screen_height - 100))
                self.client.screen.blit(start_text, start_rect)
            else:
                # Default message if no data available
                font = pygame.font.Font(None, 32)
                message = font.render("Waiting for server data...", True, (0, 0, 100))
                message_rect = message.get_rect(center=(self.client.screen_width // 2, self.client.screen_height // 2))
                self.client.screen.blit(message, message_rect)
                
            # Update display
            pygame.display.flip()
        except Exception as e:
            logger.error("Error drawing waiting room: " + str(e))

    def draw_death_screen(self):
        # If agent is dead, display respawn message with cooldown
        
        elapsed = time.time() - self.client.agent.death_time
        remaining_time = max(0, self.client.agent.respawn_cooldown - elapsed)
        
        if remaining_time > 0:
            # Display cooldown
            font = pygame.font.Font(None, 28)
            text = font.render("Respawn in " + str(int(remaining_time)+1) + " seconds", True, (255, 0, 0))
            text_rect = text.get_rect(left=15, top=self.client.game_height + self.client.game_screen_padding)
            self.client.screen.blit(text, text_rect)
        else:
            if self.client.manual_respawn:
                # Display respawn message in center of screen
                font = pygame.font.Font(None, 28)
                text = font.render("Press SPACE to spawn", True, (0, 200, 0))
                text_rect = text.get_rect(left=15, top=self.client.game_height + self.client.game_screen_padding)
                self.client.screen.blit(text, text_rect)

    def draw_leaderboard(self):
        """Draw leaderboard on right side of screen"""
        
        # Check if screen is available
        if not self.client.is_initialized or self.client.screen is None:
            logger.error("Cannot draw leaderboard: pygame not initialized or screen is None")
            return
            
        try:
            # Define leaderboard area
            leaderboard_rect = pygame.Rect(self.client.game_width + self.client.game_screen_padding, 0, self.client.leaderboard_width, self.client.screen_height)
            
            # Fill leaderboard background with lighter color
            pygame.draw.rect(self.client.screen, (240, 240, 240), leaderboard_rect)
            
            # Draw a line to separate leaderboard from game area
            pygame.draw.line(self.client.screen, (100, 100, 100), (self.client.game_width + self.client.game_screen_padding, 0), (self.client.game_width + self.client.game_screen_padding, self.client.screen_height), 2)
            
            # Add a title with colored background
            title_rect = pygame.Rect(self.client.game_width + self.client.game_screen_padding, 0, self.client.leaderboard_width, 40)
            pygame.draw.rect(self.client.screen, (50, 50, 150), title_rect)
            
            font_title = pygame.font.Font(None, 28)
            title = font_title.render("LEADERBOARD", True, (255, 255, 255))
            title_rect = title.get_rect(center=(self.client.game_width + self.client.leaderboard_width // 2 + self.client.game_screen_padding, 20))
            self.client.screen.blit(title, title_rect)
            
            # Add a header
            header_font = pygame.font.Font(None, 24)
            header_y = 50
            
            # Draw columns with distinct titles
            rank_header = header_font.render("Rank", True, (0, 0, 100))
            self.client.screen.blit(rank_header, (self.client.game_width + self.client.game_screen_padding + 10, header_y))
            
            player_header = header_font.render("Player", True, (0, 0, 100))
            self.client.screen.blit(player_header, (self.client.game_width + 80, header_y)) 
            
            score_header = header_font.render("Score", True, (0, 0, 100))
            self.client.screen.blit(score_header, (self.client.game_width + self.client.game_screen_padding + 140, header_y))
            
            best_score_header = header_font.render("Best", True, (0, 0, 100))
            self.client.screen.blit(best_score_header, (self.client.game_width + self.client.game_screen_padding + 200, header_y))
            
            # Add a line to separate header from player list
            pygame.draw.line(self.client.screen, (200, 200, 200), 
                            (self.client.game_width + self.client.game_screen_padding + 5, header_y + 20), 
                            (self.client.game_width + self.client.leaderboard_width - 5, header_y + 20), 2)
            
            # Get train data for leaderboard
            for train_name, train_data in self.client.trains.items():
                # Check if train is already in sorted_trains
                train_found = False
                current_score = train_data.get("score", 0)  # Get current score
                for i, (existing_name, best_score, _) in enumerate(self.sorted_trains):
                    if existing_name == train_name:
                        # Update best score if current score is higher
                        if current_score > best_score:
                            self.sorted_trains[i] = (train_name, current_score, current_score)
                        else:
                            self.sorted_trains[i] = (train_name, best_score, current_score)
                        train_found = True
                        break
                
                # If train not found, add it
                if not train_found:
                    self.sorted_trains.append((train_name, current_score, current_score))
            
            # Sort by best score in descending order
            self.sorted_trains.sort(key=lambda x: x[1], reverse=True)
            
            # Display players in leaderboard
            player_font = pygame.font.Font(None, 22)
            y_offset = header_y + 30
            
            for i, (train_name, best_score, current_score) in enumerate(self.sorted_trains):
                # Limit to 10 players in leaderboard
                if i >= 10:
                    break
                    
                # Determine color based on rank
                if i == 0:
                    rank_color = (218, 165, 32)  # Gold
                elif i == 1:
                    rank_color = (192, 192, 192)  # Silver
                elif i == 2:
                    rank_color = (205, 127, 50)  # Bronze
                else:
                    rank_color = (100, 100, 100)  # Gray
                
                # Highlight current player's row
                if train_name == self.client.agent_name:
                    pygame.draw.rect(self.client.screen, (220, 220, 255),  # Light blue background
                                pygame.Rect(self.client.game_width + self.client.game_screen_padding + 5,
                                        y_offset - 2,
                                        self.client.leaderboard_width - 10,
                                        20))
                
                # Get train color
                train_color = (0, 0, 0)  # Default color
                if train_name in self.client.trains:
                    train_data = self.client.trains[train_name]
                    if isinstance(train_data, dict) and "color" in train_data:
                        train_color = train_data["color"]
                    if train_name == self.client.agent_name:
                        train_color = (0, 0, 255)  # Blue for player's train
                
                # Display rank
                rank_text = player_font.render(str(i+1), True, rank_color)
                self.client.screen.blit(rank_text, (self.client.game_width + self.client.game_screen_padding + 10, y_offset))
                
                # Display player name with train color
                name_text = player_font.render(train_name[:10], True, train_color)
                self.client.screen.blit(name_text, (self.client.game_width + 80, y_offset))
                
                # Display current score
                score_text = player_font.render(str(current_score), True, (0, 0, 0))
                self.client.screen.blit(score_text, (self.client.game_width + self.client.game_screen_padding + 160, y_offset))
                
                # Display best score
                best_score_text = player_font.render(str(best_score), True, (0, 0, 0))
                self.client.screen.blit(best_score_text, (self.client.game_width + self.client.game_screen_padding + 220, y_offset))
                
                y_offset += 25
        except Exception as e:
            logger.error("Error drawing leaderboard: " + str(e))