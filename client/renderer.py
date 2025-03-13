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
                # Draw a light grid across the full game area
                grid_color = (230, 230, 230)  # Very light gray
                outline_color = (200, 200, 200)  # Slightly darker gray for outlines
                outline_width = 3  # Thicker width for outlines
                
                # Draw inner grid lines
                for x in range(self.client.game_screen_padding, self.client.game_width + self.client.game_screen_padding, self.client.grid_size):
                    pygame.draw.line(self.client.screen, grid_color, (x, self.client.game_screen_padding), (x, self.client.game_height + self.client.game_screen_padding), 1)
                for y in range(self.client.game_screen_padding, self.client.game_height + self.client.game_screen_padding, self.client.grid_size):
                    pygame.draw.line(self.client.screen, grid_color, (self.client.game_screen_padding, y), (self.client.game_width + self.client.game_screen_padding, y), 1)
                
                # Draw outer border with thicker lines
                pygame.draw.rect(
                    self.client.screen, 
                    outline_color,
                    (
                        self.client.game_screen_padding-outline_width, 
                        self.client.game_screen_padding-outline_width, 
                        self.client.game_width + 2*outline_width, 
                        self.client.game_height + 2*outline_width
                    ),
                    outline_width
                )
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
            
            # logger.debug(f"Drawing game: agent is dead: {self.client.agent.is_dead}, in waiting room: {self.client.in_waiting_room}")
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

    def draw_passengers(self):
        # Draw passengers and their values
        for passenger in self.client.passengers:
            # logger.debug("Passenger: " + str(passenger))
            try:
                if isinstance(passenger, dict):
                    if "position" in passenger:
                        x, y = passenger["position"]
                        x += self.client.game_screen_padding
                        y += self.client.game_screen_padding
                        value = passenger.get("value", 1)
                    else:
                        logger.warning("Passenger dict without position: " + str(passenger))
                        continue
                else:
                    logger.warning("Unrecognized passenger format: " + str(passenger))
                    continue
                
                # Calculate color intensity based on value (1-10)
                # Higher value = more intense red
                red_intensity = max(100, min(255, 100 + (155 * value / 10)))  # Range from 100-255
                
                # Draw a circle to represent passengers
                pygame.draw.circle(
                    self.client.screen,
                    (red_intensity, 0, 0),  # Red with varying intensity
                    (x + self.client.grid_size // 2, 
                        y + self.client.grid_size // 2),  # Circle center
                    self.client.grid_size // 2 - 2,  # Circle radius slightly smaller
                )
                
                # Draw the value text above the passenger
                font = pygame.font.Font(None, 24)  # Default pygame font, size 24
                text = font.render(str(value), True, (0, 0, 0))  # Black text
                text_rect = text.get_rect(center=(x + self.client.grid_size // 2, y - 5))  # Position above passenger
                self.client.screen.blit(text, text_rect)
                
            except Exception as e:
                logger.error("Error processing passenger: " + str(e) + ", passenger: " + str(passenger))

    def draw_trains(self):
        # Draw trains
        for train_name, train_data in self.client.trains.items():
            # Only draw if train is alive
            if isinstance(train_data, dict) and not train_data.get("alive", True):
                continue
            
            # logger.debug(f"Drawing train: {train_name}, data: {train_data}")

            # Check if train data is in new format (dictionary)
            train_position = train_data.get("position", (0, 0))
            train_x, train_y = train_position
            train_x += self.client.game_screen_padding
            train_y += self.client.game_screen_padding
            train_wagons = train_data.get("wagons", [])
            train_direction = train_data.get("direction", (1, 0))
            train_color = train_data.get("color", (0, 255, 0))
            train_wagon_color = tuple(min(c + 50, 255) for c in train_color)  # Wagons lighter
            
            # Draw main train
            color = train_color
            if train_name == self.client.agent_name:
                color = (0, 0, 255)  # Blue for player's train
            
            # Draw train with more elaborate shape
            pygame.draw.rect(
                self.client.screen,
                color,
                pygame.Rect(
                    train_x + 1,
                    train_y + 1,
                    self.client.grid_size - 2,
                    self.client.grid_size - 2,
                ),
            )
            
            # Add train details (like "eyes")
            if train_direction[0] == 1:  # Right
                eye_x = train_x + 3*self.client.grid_size//4
                eye_y = train_y + self.client.grid_size//4
            elif train_direction[0] == -1:  # Left
                eye_x = train_x + self.client.grid_size//4
                eye_y = train_y + self.client.grid_size//4
            elif train_direction[1] == 1:  # Down
                eye_x = train_x + self.client.grid_size//4
                eye_y = train_y + 3*self.client.grid_size//4
            else:  # Up
                eye_x = train_x + self.client.grid_size//4
                eye_y = train_y + self.client.grid_size//4
            
            # Draw train's "eyes"
            pygame.draw.circle(
                self.client.screen,
                (255, 255, 255),  # White
                (eye_x, eye_y),
                self.client.grid_size//8,
            )
            
            # Draw wagons
            for wagon_pos in train_wagons:
                wagon_x, wagon_y = wagon_pos
                wagon_x += self.client.game_screen_padding
                wagon_y += self.client.game_screen_padding
                wagon_color = train_wagon_color
                if train_name == self.client.agent_name:
                    wagon_color = (50, 50, 200)  # Darker blue for player's wagons
                    
                pygame.draw.rect(
                    self.client.screen,
                    wagon_color,
                    pygame.Rect(
                        wagon_x + 2,
                        wagon_y + 2,
                        self.client.grid_size - 4,
                        self.client.grid_size - 4,
                    ),
                )

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
            title = font_title.render("Waiting for players...", True, (0, 0, 100))
            rect_size = title.get_size()
            title_rect = title.get_rect(center=(rect_size[0]//2+20, rect_size[1]//2+20))
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
                column_width = 150
                players_per_column = 10
                start_y = 160
                
                # List players in two columns
                for i, player in enumerate(players):
                    column = i // players_per_column
                    row = i % players_per_column
                    x = 20 + (column * column_width)
                    y = start_y + (row * 40)
                    
                    player_text = font.render(str(i+1) + ". " + str(player), True, (0, 0, 0))
                    self.client.screen.blit(player_text, (x, y))
            else:
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
            text_rect = text.get_rect(center=(self.client.game_screen_padding + self.client.game_width//2, self.client.game_height/2 + self.client.game_screen_padding))
            self.client.screen.blit(text, text_rect)

        elif self.client.agent.waiting_for_respawn:
            # Display respawn message in center of screen
            font = pygame.font.Font(None, 28)
            text = font.render("Press SPACE to spawn", True, (0, 200, 0))
            text_rect = text.get_rect(center=(self.client.game_screen_padding + self.client.game_width//2, self.client.game_height/2 + self.client.game_screen_padding))
            self.client.screen.blit(text, text_rect)

    def draw_leaderboard(self):
        """Draw leaderboard on right side of screen"""
        
        # Check if screen is available
        if not self.client.is_initialized or self.client.screen is None:
            logger.error("Cannot draw leaderboard: pygame not initialized or screen is None")
            return
            
        try:
            # Define leaderboard area
            leaderboard_rect = pygame.Rect(self.client.game_width + 2*self.client.game_screen_padding, 0, self.client.leaderboard_width, self.client.screen_height)
            
            # Fill leaderboard background with lighter color
            pygame.draw.rect(self.client.screen, (240, 240, 240), leaderboard_rect)
            
            # Draw a line to separate leaderboard from game area
            pygame.draw.line(self.client.screen, (100, 100, 100), (self.client.game_width + 2*self.client.game_screen_padding, 0), (self.client.game_width + 2*self.client.game_screen_padding, self.client.screen_height), 2)
            
            # Add a title with colored background
            title_rect = pygame.Rect(self.client.game_width + 2*self.client.game_screen_padding, 0, self.client.leaderboard_width, 40)
            pygame.draw.rect(self.client.screen, (50, 50, 150), title_rect)
            
            font_title = pygame.font.Font(None, 28)
            title = font_title.render("LEADERBOARD", True, (255, 255, 255))
            title_rect = title.get_rect(center=(self.client.game_width + self.client.leaderboard_width // 2 + 2*self.client.game_screen_padding, 20))
            self.client.screen.blit(title, title_rect)
            
            # Add a header
            header_font = pygame.font.Font(None, 24)
            header_y = 50
            
            # Draw columns with distinct titles
            rank_header = header_font.render("Rank", True, (0, 0, 100))
            self.client.screen.blit(rank_header, (self.client.game_width + 2*self.client.game_screen_padding + 10, header_y))
            
            player_header = header_font.render("Player", True, (0, 0, 100))
            self.client.screen.blit(player_header, (self.client.game_width + 2*self.client.game_screen_padding + 70, header_y)) 
            
            score_header = header_font.render("Score", True, (0, 0, 100))
            self.client.screen.blit(score_header, (self.client.game_width + 2*self.client.game_screen_padding + 140, header_y))
            
            best_score_header = header_font.render("Best", True, (0, 0, 100))
            self.client.screen.blit(best_score_header, (self.client.game_width + 2*self.client.game_screen_padding + 200, header_y))
            
            # Add a line to separate header from player list
            pygame.draw.line(self.client.screen, (200, 200, 200), 
                            (self.client.game_width + 2*self.client.game_screen_padding + 5, header_y + 20), 
                            (self.client.game_width + 2*self.client.game_screen_padding + self.client.leaderboard_width - 5, header_y + 20), 2)
            
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
                                pygame.Rect(self.client.game_width + 2*self.client.game_screen_padding + 5,
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
                self.client.screen.blit(rank_text, (self.client.game_width + 2*self.client.game_screen_padding + 30, y_offset))
                
                # Display player name with train color
                name_text = player_font.render(train_name[:10], True, train_color)
                self.client.screen.blit(name_text, (self.client.game_width + 2*self.client.game_screen_padding + 90, y_offset))
                
                # Display current score
                score_text = player_font.render(str(current_score), True, (0, 0, 0))
                self.client.screen.blit(score_text, (self.client.game_width + 2*self.client.game_screen_padding + 155, y_offset))
                
                # Display best score
                best_score_text = player_font.render(str(best_score), True, (0, 0, 0))
                self.client.screen.blit(best_score_text, (self.client.game_width + 2*self.client.game_screen_padding + 210, y_offset))
                
                y_offset += 25
        except Exception as e:
            logger.error("Error drawing leaderboard: " + str(e))